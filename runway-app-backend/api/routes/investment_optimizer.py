"""
Investment Optimizer API Routes

Features:
- SIP detection and tracking
- Portfolio allocation analysis
- Investment insights and recommendations
- Rebalancing suggestions
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
import sys
from pathlib import Path
import logging
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from storage.database import DatabaseManager
from storage.models import User, Transaction
from auth.dependencies import get_current_user, get_db
from config import Config

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Pydantic Models
# ============================================================================

class SIPPattern(BaseModel):
    """Detected SIP (Systematic Investment Plan)"""
    sip_id: str
    platform: str
    amount: float
    frequency: str  # 'monthly', 'quarterly', etc.
    transaction_count: int
    total_invested: float
    start_date: str
    last_transaction_date: str
    category: Optional[str] = None  # equity, debt, hybrid, unknown


class InvestmentSummary(BaseModel):
    """Investment summary statistics"""
    total_invested: float
    total_transactions: int
    platforms: List[dict]
    sip_count: int
    total_sip_investment: float


class PortfolioAllocation(BaseModel):
    """Portfolio allocation breakdown"""
    equity: float
    debt: float
    hybrid: float
    unknown: float
    total: float


class InvestmentInsight(BaseModel):
    """Investment insight/recommendation"""
    type: str  # 'opportunity', 'warning', 'info'
    title: str
    message: str
    action: Optional[str] = None


class InvestmentOptimizerResponse(BaseModel):
    """Complete investment optimizer response"""
    summary: InvestmentSummary
    sips: List[SIPPattern]
    portfolio_allocation: PortfolioAllocation
    insights: List[InvestmentInsight]


# ============================================================================
# Helper Functions
# ============================================================================

def get_investment_transactions(user_id: str) -> List[Transaction]:
    """Get all investment transactions for a user"""
    db = DatabaseManager(Config.DATABASE_URL)
    session = db.get_session()
    try:
        transactions = session.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.category == 'Mutual Funds & Investments',
            Transaction.type == 'debit'  # Only count money going out as investments
        ).order_by(Transaction.date).all()
        return transactions
    finally:
        session.close()
        db.close()


def detect_sips(transactions: List[Transaction]) -> List[SIPPattern]:
    """
    Detect SIP patterns from transactions
    
    Logic:
    1. Group by platform
    2. Group by similar amounts
    3. Check for recurring patterns (monthly, quarterly, etc.)
    4. Identify SIPs based on frequency and consistency
    """
    sips = []
    
    # Group by platform
    platform_groups = defaultdict(list)
    for txn in transactions:
        platform = txn.merchant_canonical or 'Unknown'
        platform_groups[platform].append(txn)
    
    # Detect SIPs per platform
    for platform, txns in platform_groups.items():
        if len(txns) < 2:  # Need at least 2 transactions for a pattern
            continue
        
        # Group by similar amounts (±5% variance)
        amount_groups = defaultdict(list)
        for txn in txns:
            added = False
            for amount_key in list(amount_groups.keys()):
                base_amount = float(amount_key)
                variance = abs(txn.amount - base_amount) / base_amount
                if variance <= 0.05:  # Within 5%
                    amount_groups[amount_key].append(txn)
                    added = True
                    break
            if not added:
                amount_groups[str(txn.amount)] = [txn]
        
        # Check each amount group for SIP pattern
        for amount_key, group in amount_groups.items():
            if len(group) >= 2:  # At least 2 occurrences
                # Try to detect frequency
                sorted_txns = sorted(group, key=lambda x: x.date)
                dates = [datetime.strptime(txn.date, '%Y-%m-%d') for txn in sorted_txns]
                
                # Check if they're roughly monthly
                is_monthly = True
                for i in range(1, len(dates)):
                    days_diff = (dates[i] - dates[i-1]).days
                    # Monthly should be ~28-35 days
                    if not (25 <= days_diff <= 40):
                        is_monthly = False
                        break
                
                frequency = 'monthly' if is_monthly else 'irregular'
                
                sip = SIPPattern(
                    sip_id=f"sip_{platform}_{amount_key}".replace('.', '_'),
                    platform=platform,
                    amount=float(amount_key),
                    frequency=frequency,
                    transaction_count=len(group),
                    total_invested=sum(txn.amount for txn in group),
                    start_date=sorted_txns[0].date,
                    last_transaction_date=sorted_txns[-1].date
                )
                sips.append(sip)
    
    return sips


def analyze_portfolio_allocation(transactions: List[Transaction]) -> PortfolioAllocation:
    """Analyze portfolio allocation (this is simplified - real analysis would need more data)"""
    total = sum(txn.amount for txn in transactions)
    
    # For now, categorize based on platform names
    equity = 0
    debt = 0
    hybrid = 0
    unknown = 0
    
    for txn in transactions:
        platform = (txn.merchant_canonical or '').lower()
        
        # Known equity platforms
        if any(p in platform for p in ['zerodha', 'groww', 'upstox', 'angel', '5paisa']):
            equity += txn.amount  # Likely equities by default
        else:
            unknown += txn.amount
    
    return PortfolioAllocation(
        equity=equity,
        debt=debt,
        hybrid=hybrid,
        unknown=unknown,
        total=total
    )


def generate_insights(transactions: List[Transaction], sips: List[SIPPattern]) -> List[InvestmentInsight]:
    """Generate investment insights and recommendations"""
    insights = []
    
    if not transactions:
        insights.append(InvestmentInsight(
            type='info',
            title='No Investments Detected',
            message='Start building wealth with SIPs in equity mutual funds. Consider platforms like Zerodha or Groww for low-cost investing.',
            action='Explore Investment Platforms'
        ))
        return insights
    
    total_invested = sum(txn.amount for txn in transactions)
    
    # Check for SIPs
    if not sips:
        insights.append(InvestmentInsight(
            type='opportunity',
            title='No SIPs Detected',
            message=f'You have ₹{total_invested:,.0f} in investments. Consider setting up SIPs (₹2,000-5,000/month) for disciplined investing.',
            action='Start SIP'
        ))
    
    # Portfolio allocation
    if len([sip for sip in sips if 'equity' in (sip.category or '')]) > 0:
        equity_sips = [sip for sip in sips if 'equity' in (sip.category or '')]
        total_equity = sum(sip.total_invested for sip in equity_sips)
        percentage = (total_equity / total_invested * 100) if total_invested > 0 else 0
        
        if percentage < 50:
            insights.append(InvestmentInsight(
                type='opportunity',
                title='Low Equity Exposure',
                message=f'Only {percentage:.0f}% of your investments are in equity. For long-term wealth building, aim for 60-80% equity allocation.',
                action='Rebalance Portfolio'
            ))
    
    return insights


# ============================================================================
# API Routes
# ============================================================================

@router.get("/analyze", response_model=InvestmentOptimizerResponse)
async def analyze_investments(
    current_user: User = Depends(get_current_user)
):
    """
    Analyze user's investment portfolio
    
    Returns:
    - Investment summary
    - Detected SIPs
    - Portfolio allocation
    - Insights and recommendations
    """
    try:
        # Get investment transactions
        transactions = get_investment_transactions(current_user.user_id)
        
        # Detect SIPs
        sips = detect_sips(transactions)
        
        # Analyze portfolio
        portfolio = analyze_portfolio_allocation(transactions)
        
        # Generate insights
        insights = generate_insights(transactions, sips)
        
        # Group by platform
        platform_summary = defaultdict(lambda: {'count': 0, 'total': 0.0})
        for txn in transactions:
            platform = txn.merchant_canonical or 'Unknown'
            platform_summary[platform]['count'] += 1
            platform_summary[platform]['total'] += txn.amount
        
        platforms_list = [
            {'name': name, 'transaction_count': data['count'], 'total_invested': data['total']}
            for name, data in platform_summary.items()
        ]
        
        summary = InvestmentSummary(
            total_invested=sum(txn.amount for txn in transactions),
            total_transactions=len(transactions),
            platforms=platforms_list,
            sip_count=len(sips),
            total_sip_investment=sum(sip.total_invested for sip in sips)
        )
        
        return InvestmentOptimizerResponse(
            summary=summary,
            sips=sips,
            portfolio_allocation=portfolio,
            insights=insights
        )
        
    except Exception as e:
        logger.error(f"Error analyzing investments: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze investments: {str(e)}"
        )


@router.get("/sips", response_model=List[SIPPattern])
async def get_sips(
    current_user: User = Depends(get_current_user)
):
    """Get detected SIP patterns"""
    try:
        transactions = get_investment_transactions(current_user.user_id)
        sips = detect_sips(transactions)
        return sips
    except Exception as e:
        logger.error(f"Error fetching SIPs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/portfolio", response_model=PortfolioAllocation)
async def get_portfolio_allocation(
    current_user: User = Depends(get_current_user)
):
    """Get portfolio allocation breakdown"""
    try:
        transactions = get_investment_transactions(current_user.user_id)
        portfolio = analyze_portfolio_allocation(transactions)
        return portfolio
    except Exception as e:
        logger.error(f"Error analyzing portfolio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

