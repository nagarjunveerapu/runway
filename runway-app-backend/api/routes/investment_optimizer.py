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
import logging

from storage.database import DatabaseManager
from storage.models import User
from auth.dependencies import get_current_user, get_db
from config import Config
from services.investment_service.investment_service import InvestmentService

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
# Helper Functions - Service Layer Access
# ============================================================================

def get_investment_service(db: DatabaseManager = Depends(get_db)) -> InvestmentService:
    """Dependency injection for InvestmentService"""
    return InvestmentService(db)


# ============================================================================
# API Routes
# ============================================================================

@router.get("/analyze", response_model=InvestmentOptimizerResponse)
async def analyze_investments(
    current_user: User = Depends(get_current_user),
    investment_service: InvestmentService = Depends(get_investment_service)
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
        # Use service layer for all business logic
        result = investment_service.analyze_investments(current_user.user_id)
        
        # Convert service layer results to Pydantic models
        summary = InvestmentSummary(**result['summary'])
        
        sips = [SIPPattern(**sip) for sip in result['sips']]
        
        portfolio = PortfolioAllocation(**result['portfolio_allocation'])
        
        insights = [InvestmentInsight(**insight) for insight in result['insights']]
        
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
    current_user: User = Depends(get_current_user),
    investment_service: InvestmentService = Depends(get_investment_service)
):
    """Get detected SIP patterns"""
    try:
        # Use service layer
        sips_data = investment_service.get_sips(current_user.user_id)
        return [SIPPattern(**sip) for sip in sips_data]
    except Exception as e:
        logger.error(f"Error fetching SIPs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/portfolio", response_model=PortfolioAllocation)
async def get_portfolio_allocation(
    current_user: User = Depends(get_current_user),
    investment_service: InvestmentService = Depends(get_investment_service)
):
    """Get portfolio allocation breakdown"""
    try:
        # Use service layer
        portfolio_data = investment_service.get_portfolio_allocation(current_user.user_id)
        return PortfolioAllocation(**portfolio_data)
    except Exception as e:
        logger.error(f"Error analyzing portfolio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

