"""
FIRE Calculator API

Financial Independence, Retire Early (FIRE) calculations:
- Financial runway (months to FI)
- Target corpus (25x annual expenses)
- Years to FIRE projection
- Current savings rate analysis
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import math

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from storage.database import DatabaseManager
from storage.models import User, Asset, Liability
from auth.dependencies import get_current_user
from config import Config
from utils.date_parser import parse_month_from_date

logger = logging.getLogger(__name__)


def sanitize_value(val):
    """Convert NaN, inf, or -inf to None for JSON serialization"""
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return None
    return val

router = APIRouter()


@router.get("/runway")
async def calculate_fire_runway(current_user: User = Depends(get_current_user)):
    """
    Calculate financial runway and FIRE projections
    
    Returns:
    - Current monthly expenses
    - Current savings rate
    - Months to FIRE at current rate
    - Target FIRE corpus (25x rule)
    - Years to FIRE projection
    - Growth trajectory
    """
    try:
        db = get_db()
        
        # Get all transactions for the user
        all_transactions = db.get_transactions(user_id=current_user.user_id)
        
        # Calculate last 3 months average for more accurate projections
        now = datetime.now()
        monthly_data = {}
        
        for txn in all_transactions:
            txn_month = parse_month_from_date(txn.date) if txn.date else ""
            if not txn_month:
                continue
                
            if txn_month not in monthly_data:
                monthly_data[txn_month] = {'income': 0, 'expenses': 0, 'count': 0}
            
            monthly_data[txn_month]['count'] += 1
            if txn.type == "credit":
                monthly_data[txn_month]['income'] += txn.amount
            else:
                monthly_data[txn_month]['expenses'] += txn.amount
        
        # Get last 3 months (most recent data)
        sorted_months = sorted([m for m in monthly_data.keys() if m])[-3:]
        
        if len(sorted_months) == 0:
            return {
                'current_monthly_expenses': 0,
                'current_monthly_income': 0,
                'savings_rate': 0,
                'fire_corpus_required': 0,
                'months_to_fire': None,
                'years_to_fire': None,
                'current_net_worth': 0,
                'deficit': 0,
                'message': 'Insufficient transaction data'
            }
        
        # Calculate averages from last 3 months
        avg_income = sum(monthly_data[m]['income'] for m in sorted_months) / len(sorted_months)
        avg_expenses = sum(monthly_data[m]['expenses'] for m in sorted_months) / len(sorted_months)
        avg_savings = avg_income - avg_expenses
        savings_rate = (avg_savings / avg_income * 100) if avg_income > 0 else 0
        
        # Get assets and liabilities from dashboard
        session = db.get_session()
        try:
            assets = session.query(Asset).filter(
                Asset.user_id == current_user.user_id
            ).all()
            
            liabilities = session.query(Liability).filter(
                Liability.user_id == current_user.user_id
            ).all()
            
            total_assets = sum(
                (getattr(a, 'current_value', None) or getattr(a, 'purchase_price', 0) or 0)
                for a in assets if not getattr(a, 'disposed', False)
            )
            
            total_liabilities = sum(
                (liability.outstanding_balance or liability.principal_amount or 0)
                for liability in liabilities
            )
            
            current_net_worth = total_assets - total_liabilities
        finally:
            session.close()
        
        # FIRE Calculations (25x rule)
        annual_expenses = avg_expenses * 12
        fire_corpus_required = annual_expenses * 25  # 25x rule
        
        # Calculate time to FIRE
        deficit = fire_corpus_required - current_net_worth
        
        if avg_savings > 0 and deficit > 0:
            months_to_fire = int(deficit / avg_savings)
            years_to_fire = months_to_fire / 12
        else:
            # Use None instead of float('inf') as it's not JSON serializable
            months_to_fire = None
            years_to_fire = None
        
        # Calculate additional metrics
        months_of_expenses_covered = current_net_worth / avg_expenses if avg_expenses > 0 else 0
        
        # Generate insight message
        if months_to_fire is None or years_to_fire is None:
            message = "⚠️ Increase savings rate to reach FIRE"
        elif years_to_fire <= 5:
            message = "🎉 Almost there! Keep going!"
        elif years_to_fire <= 10:
            message = "🚀 Great progress! Stay consistent"
        elif years_to_fire <= 20:
            message = "📈 Good pace! You're on track"
        else:
            message = "💪 Building wealth! Increase savings"
        
        db.close()
        
        # Sanitize all numeric values to ensure JSON compatibility
        return {
            'current_monthly_expenses': sanitize_value(avg_expenses),
            'current_monthly_income': sanitize_value(avg_income),
            'current_monthly_savings': sanitize_value(avg_savings),
            'savings_rate': sanitize_value(savings_rate),
            'fire_corpus_required': sanitize_value(fire_corpus_required),
            'current_net_worth': sanitize_value(current_net_worth),
            'months_to_fire': months_to_fire,  # Already None or int
            'years_to_fire': sanitize_value(years_to_fire),
            'months_of_expenses_covered': sanitize_value(months_of_expenses_covered),
            'deficit': sanitize_value(deficit),
            'progress_percentage': sanitize_value((current_net_worth / fire_corpus_required * 100) if fire_corpus_required > 0 else 0),
            'message': message,
            'data_points': len(all_transactions),
            'analysis_period_months': len(sorted_months)
        }
        
    except Exception as e:
        logger.error(f"Error calculating FIRE runway: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate FIRE metrics: {str(e)}"
        )


def get_db():
    """Get database instance"""
    return DatabaseManager(Config.DATABASE_URL)
