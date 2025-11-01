from fastapi import APIRouter, Depends, HTTPException
from auth.dependencies import get_current_user
from storage.models import User, Asset, Transaction, TransactionType
from storage.database import DatabaseManager
from config import Config
from datetime import datetime
from typing import Dict, Any

router = APIRouter()

def get_db():
    """Get database instance"""
    return DatabaseManager(Config.DATABASE_URL)


@router.get("/emergency-fund")
async def get_emergency_fund_health(
    current_user: User = Depends(get_current_user)
):
    """
    Calculate Emergency Fund Health Check
    
    Returns:
    - Liquid assets (cash, savings, FDs < 1 year)
    - Recommended emergency fund (6-12 months expenses)
    - Health score (percentage)
    - Status (Excellent/Good/Needs Improvement/Critical)
    - Recommendations
    """
    try:
        db = get_db()
        
        # Get user's liquid assets
        session = db.get_session()
        try:
            liquid_assets_query = session.query(Asset).filter(
                Asset.user_id == current_user.user_id,
                Asset.asset_type.in_(['savings', 'current', 'fd'])
            )
            liquid_assets = liquid_assets_query.all()
            
            # Calculate total liquid assets (cash + savings + short-term FDs)
            liquid_value = sum(asset.current_value or 0 for asset in liquid_assets)
            
            # Calculate monthly expenses from last 6 months of transactions
            six_months_ago = datetime.now().replace(day=1)
            
            expenses = session.query(Transaction).filter(
                Transaction.user_id == current_user.user_id,
                Transaction.type == TransactionType.DEBIT,
                Transaction.date >= six_months_ago
            ).all()
        finally:
            session.close()
        
        total_expenses = sum(t.amount for t in expenses)
        avg_monthly_expenses = total_expenses / 6 if len(expenses) > 0 else 0
        
        # Calculate recommended emergency fund
        # Conservative: 12 months expenses
        # Moderate: 6 months expenses
        # Aggressive: 3 months expenses
        
        recommended_12m = avg_monthly_expenses * 12
        recommended_6m = avg_monthly_expenses * 6
        recommended_3m = avg_monthly_expenses * 3
        
        # Calculate health score
        # Score: liquid_assets / recommended_6m * 100
        if recommended_6m > 0:
            health_score = min((liquid_value / recommended_6m) * 100, 150)  # Cap at 150%
        else:
            health_score = 0
        
        # Determine status
        if health_score >= 100:
            status = "Excellent"
            status_color = "green"
            recommendation = f"✅ You have {health_score:.0f}% of recommended emergency fund. You're well protected!"
        elif health_score >= 75:
            status = "Good"
            status_color = "blue"
            recommended_amount = (recommended_12m - liquid_value)
            recommendation = f"👍 You have {health_score:.0f}% coverage. Consider adding ₹{recommended_amount:,.0f} for full safety."
        elif health_score >= 50:
            status = "Needs Improvement"
            status_color = "yellow"
            recommended_amount = (recommended_6m - liquid_value)
            recommendation = f"⚠️ You have {health_score:.0f}% coverage. Add ₹{recommended_amount:,.0f} to reach 6-month target."
        elif health_score >= 25:
            status = "Low"
            status_color = "orange"
            recommended_amount = (recommended_3m - liquid_value)
            recommendation = f"⚠️ You have {health_score:.0f}% coverage. Priority: Build ₹{recommended_amount:,.0f} for minimum 3-month safety."
        else:
            status = "Critical"
            status_color = "red"
            recommended_amount = (recommended_3m - liquid_value)
            recommendation = f"🚨 Critical: Only {health_score:.0f}% coverage! Urgently build ₹{recommended_amount:,.0f} emergency fund."
        
        # Calculate months covered
        months_covered = (liquid_value / avg_monthly_expenses) if avg_monthly_expenses > 0 else 0
        
        # Calculate liquidity ratio
        session2 = db.get_session()
        try:
            total_assets = session2.query(Asset).filter(Asset.user_id == current_user.user_id).all()
            total_assets_value = sum(asset.current_value or 0 for asset in total_assets)
            liquidity_ratio = (liquid_value / total_assets_value * 100) if total_assets_value > 0 else 0
        finally:
            session2.close()
        
        return {
            'liquid_assets': liquid_value,
            'avg_monthly_expenses': avg_monthly_expenses,
            'months_covered': round(months_covered, 1),
            'recommended_3m': recommended_3m,
            'recommended_6m': recommended_6m,
            'recommended_12m': recommended_12m,
            'health_score': round(health_score, 1),
            'status': status,
            'status_color': status_color,
            'recommendation': recommendation,
            'liquidity_ratio': round(liquidity_ratio, 1),
            'shortfall_3m': max(0, recommended_3m - liquid_value),
            'shortfall_6m': max(0, recommended_6m - liquid_value),
            'shortfall_12m': max(0, recommended_12m - liquid_value),
            'data_points': len(expenses),
            'analysis_period_months': 6
        }
        
        db.close()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating emergency fund health: {str(e)}")
