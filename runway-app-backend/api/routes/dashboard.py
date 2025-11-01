"""
Dashboard API Routes

Provides comprehensive financial dashboard data including:
- Financial health score
- Net worth calculation
- Monthly income/expense summary
- Savings rate
- Asset summary
- Top insights
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
import sys
from pathlib import Path
import logging
import math
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from storage.database import DatabaseManager
from storage.models import User, Asset, Liability, TransactionType
from auth.dependencies import get_current_user
from config import Config
from utils.date_parser import parse_month_from_date

logger = logging.getLogger(__name__)

router = APIRouter()


def sanitize_value(val):
    """Convert NaN, inf, or -inf to None for JSON serialization"""
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return None
    return val


# Pydantic models
class DashboardInsight(BaseModel):
    """Single insight card"""
    type: str  # "success", "warning", "info", "tip"
    title: str
    description: str
    icon: str
    action: Optional[str] = None  # Navigation action
    value: Optional[float] = None  # Numeric value if applicable


class MonthlyMetrics(BaseModel):
    """Monthly financial metrics"""
    month: str
    income: float
    expenses: float
    net_savings: float
    savings_rate: float
    emi_payments: float
    transaction_count: int


class AssetSummary(BaseModel):
    """Summary of user's assets"""
    total_value: float
    count: int
    top_assets: List[dict]


class LiabilitySummary(BaseModel):
    """Summary of user's liabilities"""
    total_outstanding: float
    total_monthly_payments: float
    count: int
    top_liabilities: List[dict]


class DashboardSummary(BaseModel):
    """Complete dashboard summary"""
    # Financial health
    health_score: int
    health_message: str

    # Current month metrics
    current_month: MonthlyMetrics

    # Previous month for comparison
    previous_month: Optional[MonthlyMetrics] = None

    # Assets
    assets: AssetSummary

    # Liabilities (NEW)
    liabilities: LiabilitySummary
    
    # Enhanced financial metrics (NEW)
    true_net_worth: float  # Assets - Liabilities
    liquid_assets: float
    runway_months: Optional[float]  # None if monthly_burn is 0
    debt_to_asset_ratio: float

    # Insights and recommendations
    insights: List[DashboardInsight]

    # Quick stats
    net_worth: float
    total_transactions: int


def get_db():
    """Get database instance"""
    return DatabaseManager(Config.DATABASE_URL)


def calculate_health_score(
    savings_rate: float,
    total_assets: float,
    emi_to_income_ratio: float,
    income: float
) -> tuple[int, str]:
    """
    Calculate financial health score (0-100)

    Scoring:
    - Savings rate (40 points): >30% = 40, >20% = 30, >10% = 20
    - Assets (30 points): >10L = 30, >5L = 20, >1L = 10
    - EMI burden (30 points): <40% income = 30, <60% = 20
    """
    score = 0

    # Savings rate score
    if savings_rate > 30:
        score += 40
    elif savings_rate > 20:
        score += 30
    elif savings_rate > 10:
        score += 20

    # Assets score
    if total_assets > 1000000:  # 10L
        score += 30
    elif total_assets > 500000:  # 5L
        score += 20
    elif total_assets > 100000:  # 1L
        score += 10

    # EMI burden score (only if there's income)
    if income > 0:
        if emi_to_income_ratio < 0.4:
            score += 30
        elif emi_to_income_ratio < 0.6:
            score += 20
    else:
        score += 15  # Neutral score if no income data

    # Message based on score
    if score >= 80:
        message = "Excellent! 🎉"
    elif score >= 60:
        message = "Good Progress 👍"
    elif score >= 40:
        message = "Building Up 💪"
    else:
        message = "Getting Started 🌱"

    return score, message


def generate_insights(
    current_month: MonthlyMetrics,
    previous_month: Optional[MonthlyMetrics],
    assets: AssetSummary,
    health_score: int
) -> List[DashboardInsight]:
    """Generate actionable insights based on financial data"""
    insights = []

    # High savings rate achievement
    if current_month.savings_rate >= 30:
        insights.append(DashboardInsight(
            type="success",
            title="Super Saver!",
            description=f"You're saving {current_month.savings_rate:.0f}% of your income - that's excellent!",
            icon="🏆",
            value=current_month.savings_rate
        ))

    # Savings improvement
    if previous_month and current_month.net_savings > previous_month.net_savings:
        improvement = current_month.net_savings - previous_month.net_savings
        insights.append(DashboardInsight(
            type="success",
            title="Savings Improved!",
            description=f"You saved ₹{improvement:,.0f} more than last month",
            icon="📈",
            value=improvement
        ))

    # High EMI burden warning
    if current_month.income > 0:
        emi_ratio = (current_month.emi_payments / current_month.income) * 100
        if emi_ratio > 50:
            insights.append(DashboardInsight(
                type="warning",
                title="High EMI Burden",
                description=f"EMIs are {emi_ratio:.0f}% of income. Consider loan prepayment optimizer.",
                icon="⚠️",
                action="loan-prepayment",
                value=emi_ratio
            ))

    # Salary sweep opportunity
    if current_month.income >= 50000:
        insights.append(DashboardInsight(
            type="tip",
            title="Earn More Interest",
            description="Use Salary Sweep to earn ₹6K-10K more per year with zero effort",
            icon="💰",
            action="salary-sweep"
        ))

    # Asset tracking suggestion
    if assets.count == 0 and current_month.emi_payments > 0:
        insights.append(DashboardInsight(
            type="info",
            title="Track Your Assets",
            description="We detected loan EMIs - add assets like property or car to see your net worth",
            icon="🏠",
            action="assets"
        ))

    # Spending increase warning
    if previous_month and current_month.expenses > previous_month.expenses * 1.2:
        increase = ((current_month.expenses - previous_month.expenses) / previous_month.expenses) * 100
        insights.append(DashboardInsight(
            type="warning",
            title="Spending Up",
            description=f"Expenses increased by {increase:.0f}% compared to last month",
            icon="📊",
            action="reports",
            value=increase
        ))

    # Limit to top 4 insights
    return insights[:4]


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(current_user: User = Depends(get_current_user)):
    """
    Get comprehensive dashboard summary

    Returns:
    - Financial health score
    - Current month metrics
    - Previous month comparison
    - Asset summary
    - Personalized insights
    """
    try:
        db = get_db()

        # Get current month date range
        now = datetime.now()
        current_month_str = now.strftime("%Y-%m")
        current_month_start = now.replace(day=1).strftime("%Y-%m-%d")

        # Get previous month date range
        prev_month_date = (now.replace(day=1) - timedelta(days=1))
        prev_month_str = prev_month_date.strftime("%Y-%m")
        prev_month_start = prev_month_date.replace(day=1).strftime("%Y-%m-%d")
        prev_month_end = now.replace(day=1).strftime("%Y-%m-%d")

        # Get all transactions for the user
        all_transactions = db.get_transactions(user_id=current_user.user_id)

        # Calculate current month metrics
        current_income = 0.0
        current_expenses = 0.0
        current_emi = 0.0
        current_count = 0

        for txn in all_transactions:
            txn_month = parse_month_from_date(txn.date) if txn.date else ""
            if txn_month == current_month_str:
                current_count += 1
                # Handle ENUM comparison (works for both ENUM and string for backward compatibility)
                txn_type_value = txn.type.value if hasattr(txn.type, 'value') else txn.type
                if txn_type_value == TransactionType.CREDIT.value:
                    current_income += txn.amount
                else:  # debit
                    current_expenses += txn.amount
                    # Detect EMI payments
                    if txn.category and any(keyword in txn.category.lower() for keyword in ['emi', 'loan', 'mortgage']):
                        current_emi += txn.amount

        current_net_savings = current_income - current_expenses
        current_savings_rate = (current_net_savings / current_income * 100) if current_income > 0 else 0

        current_metrics = MonthlyMetrics(
            month=current_month_str,
            income=current_income,
            expenses=current_expenses,
            net_savings=current_net_savings,
            savings_rate=current_savings_rate,
            emi_payments=current_emi,
            transaction_count=current_count
        )

        # Calculate previous month metrics
        prev_income = 0.0
        prev_expenses = 0.0
        prev_emi = 0.0
        prev_count = 0

        for txn in all_transactions:
            txn_month = parse_month_from_date(txn.date) if txn.date else ""
            if txn_month == prev_month_str:
                prev_count += 1
                # Handle ENUM comparison (works for both ENUM and string for backward compatibility)
                txn_type_value = txn.type.value if hasattr(txn.type, 'value') else txn.type
                if txn_type_value == TransactionType.CREDIT.value:
                    prev_income += txn.amount
                else:
                    prev_expenses += txn.amount
                    if txn.category and any(keyword in txn.category.lower() for keyword in ['emi', 'loan', 'mortgage']):
                        prev_emi += txn.amount

        prev_net_savings = prev_income - prev_expenses
        prev_savings_rate = (prev_net_savings / prev_income * 100) if prev_income > 0 else 0

        previous_metrics = MonthlyMetrics(
            month=prev_month_str,
            income=prev_income,
            expenses=prev_expenses,
            net_savings=prev_net_savings,
            savings_rate=prev_savings_rate,
            emi_payments=prev_emi,
            transaction_count=prev_count
        ) if prev_count > 0 else None

        # Get assets using session
        session = db.get_session()
        try:
            assets = session.query(Asset).filter(
                Asset.user_id == current_user.user_id
            ).all()

            active_assets = [a for a in assets if not getattr(a, 'disposed', False)]

            total_asset_value = sum(
                (getattr(a, 'current_value', None) or getattr(a, 'purchase_price', 0) or 0)
                for a in active_assets
            )

            top_assets = []
            for asset in sorted(active_assets, key=lambda a: (getattr(a, 'current_value', None) or getattr(a, 'purchase_price', 0) or 0), reverse=True)[:3]:
                top_assets.append({
                    'name': getattr(asset, 'name', None) or 'Unknown',
                    'type': getattr(asset, 'asset_type', 'other'),
                    'value': (getattr(asset, 'current_value', None) or getattr(asset, 'purchase_price', 0) or 0),
                    'purchase_date': getattr(asset, 'purchase_date', None)
                })
        finally:
            session.close()

        asset_summary = AssetSummary(
            total_value=total_asset_value,
            count=len(active_assets),
            top_assets=top_assets
        )

        # Get liabilities
        liabilities = session.query(Liability).filter(
            Liability.user_id == current_user.user_id
        ).all()
        
        total_liabilities = sum(
            (liability.outstanding_balance or liability.principal_amount or 0)
            for liability in liabilities
        )
        
        total_monthly_liabilities = sum(
            (liability.emi_amount or 0) for liability in liabilities
        )
        
        top_liabilities = []
        for liability in sorted(liabilities, key=lambda l: (l.outstanding_balance or l.principal_amount or 0), reverse=True)[:3]:
            top_liabilities.append({
                'name': liability.name,
                'type': liability.liability_type,
                'outstanding_balance': liability.outstanding_balance or liability.principal_amount or 0,
                'emi_amount': liability.emi_amount or 0,
                'lender_name': liability.lender_name
            })
        
        liability_summary = LiabilitySummary(
            total_outstanding=total_liabilities,
            total_monthly_payments=total_monthly_liabilities,
            count=len(liabilities),
            top_liabilities=top_liabilities
        )
        
        # Calculate enhanced metrics
        liquid_assets = sum(
            (getattr(a, 'current_value', None) or getattr(a, 'purchase_price', 0) or 0)
            for a in active_assets if getattr(a, 'liquid', False)
        )
        
        true_net_worth = total_asset_value - total_liabilities
        
        # Calculate runway (months of expenses from liquid assets)
        monthly_burn = current_expenses + total_monthly_liabilities  # Total monthly outflow
        runway_months = (liquid_assets / monthly_burn) if monthly_burn > 0 else None
        
        # Sanitize runway_months for JSON serialization
        runway_months = sanitize_value(runway_months)
        
        # Debt-to-asset ratio (in percentage)
        debt_to_asset_ratio = (total_liabilities / total_asset_value * 100) if total_asset_value > 0 else 0

        # Calculate health score
        emi_to_income_ratio = (current_emi / current_income) if current_income > 0 else 0
        health_score, health_message = calculate_health_score(
            current_savings_rate,
            total_asset_value,
            emi_to_income_ratio,
            current_income
        )

        # Generate insights
        insights = generate_insights(
            current_metrics,
            previous_metrics,
            asset_summary,
            health_score
        )

        # Net worth (legacy field for backward compatibility)
        net_worth = total_asset_value

        db.close()

        return DashboardSummary(
            health_score=health_score,
            health_message=health_message,
            current_month=current_metrics,
            previous_month=previous_metrics,
            assets=asset_summary,
            liabilities=liability_summary,
            true_net_worth=sanitize_value(true_net_worth),
            liquid_assets=sanitize_value(liquid_assets),
            runway_months=runway_months,
            debt_to_asset_ratio=sanitize_value(debt_to_asset_ratio),
            insights=insights,
            net_worth=sanitize_value(net_worth),
            total_transactions=len(all_transactions)
        )

    except Exception as e:
        logger.error(f"Error fetching dashboard summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dashboard summary: {str(e)}"
        )
