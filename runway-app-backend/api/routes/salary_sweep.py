"""
Salary Sweep Optimizer API
Analyzes recurring salary credits and EMI debits to optimize interest earnings
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
import sys
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from storage.database import DatabaseManager
from storage.models import Transaction, User
from auth.dependencies import get_current_user
from config import Config

logger = logging.getLogger(__name__)

router = APIRouter()

SALARY_ACCOUNT_RATE = 2.5  # Annual interest rate (%)
SAVINGS_ACCOUNT_RATE = 7.0  # Annual interest rate (%)

# Pydantic models
class DetectedEMI(BaseModel):
    source: str
    amount: float
    count: int
    txns: List[dict] = []  # Optional, defaults to empty list (renamed from transactions for consistency)

class DetectedSalary(BaseModel):
    source: str
    amount: float
    count: int

class ConfirmRequest(BaseModel):
    salary_txn_ids: List[str]
    emi_txn_ids: List[str]

class OptimizerScenario(BaseModel):
    name: str
    description: str
    emi_dates: Optional[str]
    salary_account_balance: float
    savings_account_balance: float
    avg_days_in_savings: float
    monthly_interest_salary: float
    monthly_interest_savings: float
    total_monthly_interest: float
    total_annual_interest: float

class OptimizerResponse(BaseModel):
    detected_salary: Optional[DetectedSalary]
    detected_emis: List[DetectedEMI]
    avg_salary: float
    total_monthly_emi: float
    sweepable_amount: float
    current_scenario: OptimizerScenario
    optimized_scenario: OptimizerScenario
    monthly_interest_gain: float
    annual_interest_gain: float
    percentage_gain: float


def get_db():
    """Get database instance"""
    return DatabaseManager(Config.DATABASE_URL)


def parse_date(date_str):
    """Parse DD/MM/YYYY date"""
    if not date_str:
        return None
    parts = str(date_str).split('/')
    if len(parts) == 3:
        return f"{parts[2]}-{parts[1]}-{parts[0]}"
    return date_str


def get_merchant_source(description):
    """Extract merchant/source from transaction description"""
    if not description:
        return 'unknown'
    
    desc_lower = str(description).lower()
    
    # Look for common merchant patterns
    if 'capital' in desc_lower and 'one' in desc_lower:
        return 'capital one'
    if 'canfin' in desc_lower:
        return 'canfin homes'
    if 'hdfc' in desc_lower:
        return 'hdfc'
    if 'icici' in desc_lower:
        return 'icici'
    if 'sbi' in desc_lower or 'state bank' in desc_lower:
        return 'sbi'
    if 'axis' in desc_lower:
        return 'axis'
    
    # Extract first few words as potential merchant
    words = description.split()
    if len(words) >= 2:
        return ' '.join(words[:2]).lower()
    
    return description[:30].lower()


def is_similar_amount(amt1, amt2, variance=0.05):
    """Check if two amounts are similar (within variance)"""
    if amt1 == 0 or amt2 == 0:
        return False
    diff = abs(amt1 - amt2)
    avg = (amt1 + amt2) / 2
    return diff / avg <= variance


@router.post("/detect", response_model=dict)
async def detect_patterns(
    current_user: User = Depends(get_current_user)
):
    """
    Detect recurring salary and EMI patterns from user transactions
    """
    
    db = get_db()
    session = db.get_session()
    
    try:
        # Get all user transactions
        transactions = session.query(Transaction).filter(
            Transaction.user_id == current_user.user_id,
            Transaction.type.in_(['credit', 'debit'])
        ).order_by(Transaction.date).all()
        
        # Detect salary patterns (large recurring credits)
        credit_txns = [t for t in transactions if t.type == 'credit']
        large_credits = [t for t in credit_txns if float(t.amount) >= 50000]
        
        # Group by merchant and find recurring patterns
        credit_groups = {}
        for txn in large_credits:
            source = get_merchant_source(txn.description_raw or '')
            amount = float(txn.amount)
            
            if source not in credit_groups:
                credit_groups[source] = []
            credit_groups[source].append({
                'transaction_id': txn.transaction_id,
                'date': txn.date,
                'description_raw': txn.description_raw,
                'merchant_canonical': txn.merchant_canonical,
                'amount': amount
            })
        
        # Find recurring salary pattern (similar amounts from same source)
        salary_patterns = []
        for source, txns in credit_groups.items():
            # Group by similar amounts
            amount_groups = {}
            for txn in txns:
                amt = txn['amount']
                added = False
                for key in list(amount_groups.keys()):
                    base_amount = float(key)
                    if is_similar_amount(amt, base_amount, 0.1):
                        amount_groups[key].append(txn)
                        added = True
                        break
                if not added:
                    amount_groups[str(amt)] = [txn]
            
            # Find patterns with 2+ occurrences
            for amt, group in amount_groups.items():
                if len(group) >= 2:
                    salary_patterns.append({
                        'source': source,
                        'txns': [t for t in group],
                        'avg_amount': sum(t['amount'] for t in group) / len(group),
                        'count': len(group)
                    })
        
        # Find best salary pattern (largest amount)
        best_salary = max(salary_patterns, key=lambda x: x['avg_amount']) if salary_patterns else None
        
        # Detect EMI patterns (substantial recurring debits)
        debit_txns = [t for t in transactions if t.type == 'debit']
        substantial_debits = [t for t in debit_txns if float(t.amount) >= 10000]
        
        # Group by merchant and find recurring patterns
        debit_groups = {}
        for txn in substantial_debits:
            source = get_merchant_source(txn.description_raw or '')
            amount = float(txn.amount)
            
            if source not in debit_groups:
                debit_groups[source] = []
            debit_groups[source].append({
                'transaction_id': txn.transaction_id,
                'date': txn.date,
                'description_raw': txn.description_raw,
                'merchant_canonical': txn.merchant_canonical,
                'amount': amount
            })
        
        # Find recurring EMI patterns
        emi_patterns = []
        for source, txns in debit_groups.items():
            # Group by similar amounts
            amount_groups = {}
            for txn in txns:
                amt = txn['amount']
                added = False
                for key in list(amount_groups.keys()):
                    base_amount = float(key)
                    if is_similar_amount(amt, base_amount, 0.15):
                        amount_groups[key].append(txn)
                        added = True
                        break
                if not added:
                    amount_groups[str(amt)] = [txn]
            
            # Find patterns with 2+ occurrences
            for amt, group in amount_groups.items():
                if len(group) >= 2:
                    emi_patterns.append({
                        'source': source,
                        'txns': [t for t in group],
                        'avg_amount': sum(t['amount'] for t in group) / len(group),
                        'count': len(group)
                    })
        
        # Sort EMI patterns by amount
        emi_patterns.sort(key=lambda x: x['avg_amount'], reverse=True)
        
        # Return detected patterns
        return {
            'detected_salary': best_salary,
            'detected_emis': emi_patterns
        }
        
    except Exception as e:
        logger.error(f"Error detecting patterns: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect patterns: {str(e)}"
        )
    finally:
        session.close()
        db.close()


@router.post("/calculate", response_model=OptimizerResponse)
async def calculate_optimization(
    confirm_request: ConfirmRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Calculate salary sweep optimization based on confirmed salary and EMI transactions
    """
    
    db = get_db()
    session = db.get_session()
    
    try:
        # Get confirmed transactions
        confirmed_salary_txns = session.query(Transaction).filter(
            Transaction.user_id == current_user.user_id,
            Transaction.transaction_id.in_(confirm_request.salary_txn_ids)
        ).all()
        
        confirmed_emi_txns = session.query(Transaction).filter(
            Transaction.user_id == current_user.user_id,
            Transaction.transaction_id.in_(confirm_request.emi_txn_ids)
        ).all()
        
        # Calculate average salary
        avg_salary = sum(float(t.amount) for t in confirmed_salary_txns) / len(confirmed_salary_txns) if confirmed_salary_txns else 0
        
        # Group EMIs by source and calculate monthly amounts
        emi_by_source = {}
        for txn in confirmed_emi_txns:
            source = get_merchant_source(txn.description_raw or '')
            amount = float(txn.amount)
            
            if source not in emi_by_source:
                emi_by_source[source] = []
            emi_by_source[source].append(amount)
        
        # Calculate average for each EMI source
        emi_amounts = []
        for source, amounts in emi_by_source.items():
            emi_amounts.append({
                'source': source,
                'amount': sum(amounts) / len(amounts),
                'count': len(amounts)
            })
        
        total_monthly_emi = sum(emi['amount'] for emi in emi_amounts)
        
        # Calculate sweepable amount
        buffer_amount = total_monthly_emi * 0.1
        keep_in_salary_account = total_monthly_emi + buffer_amount
        sweepable_amount = avg_salary - keep_in_salary_account
        
        # Current scenario (no sweep)
        current_monthly_interest = avg_salary * SALARY_ACCOUNT_RATE / 100 / 12
        current_scenario = {
            'name': 'Current Setup (No Sweep)',
            'description': 'Keep all salary in 2.5% salary account',
            'emi_dates': None,
            'salary_account_balance': avg_salary,
            'savings_account_balance': 0.0,
            'avg_days_in_savings': 0.0,
            'monthly_interest_salary': current_monthly_interest,
            'monthly_interest_savings': 0.0,
            'total_monthly_interest': current_monthly_interest,
            'total_annual_interest': current_monthly_interest * 12
        }
        
        # Optimized scenario (with sweep)
        # Simplified: assume 15 days average in savings
        avg_days_in_savings = 15
        
        optimized_scenario = {
            'name': 'Optimized Sweep',
            'description': 'Sweep excess to 7% savings, transfer back before EMI',
            'emi_dates': None,
            'salary_account_balance': keep_in_salary_account,
            'savings_account_balance': sweepable_amount,
            'avg_days_in_savings': avg_days_in_savings,
            'monthly_interest_salary': keep_in_salary_account * SALARY_ACCOUNT_RATE / 100 / 12,
            'monthly_interest_savings': (sweepable_amount * avg_days_in_savings / 30 * SAVINGS_ACCOUNT_RATE / 100 / 12) if sweepable_amount > 0 else 0,
            'total_monthly_interest': 0,  # Will calculate below
            'total_annual_interest': 0  # Will calculate below
        }
        
        optimized_scenario['total_monthly_interest'] = (
            optimized_scenario['monthly_interest_salary'] + 
            optimized_scenario['monthly_interest_savings']
        )
        optimized_scenario['total_annual_interest'] = optimized_scenario['total_monthly_interest'] * 12
        
        # Calculate gains
        monthly_interest_gain = optimized_scenario['total_monthly_interest'] - current_scenario['total_monthly_interest']
        annual_interest_gain = optimized_scenario['total_annual_interest'] - current_scenario['total_annual_interest']
        percentage_gain = (annual_interest_gain / current_scenario['total_annual_interest'] * 100) if current_scenario['total_annual_interest'] > 0 else 0
        
        return OptimizerResponse(
            detected_salary={
                'source': confirmed_salary_txns[0].merchant_canonical if confirmed_salary_txns else 'Unknown',
                'amount': avg_salary,
                'count': len(confirmed_salary_txns)
            } if confirmed_salary_txns else None,
            detected_emis=[DetectedEMI(**emi) for emi in emi_amounts],
            avg_salary=avg_salary,
            total_monthly_emi=total_monthly_emi,
            sweepable_amount=sweepable_amount,
            current_scenario=OptimizerScenario(**current_scenario),
            optimized_scenario=OptimizerScenario(**optimized_scenario),
            monthly_interest_gain=monthly_interest_gain,
            annual_interest_gain=annual_interest_gain,
            percentage_gain=percentage_gain
        )
        
    except Exception as e:
        logger.error(f"Error calculating optimization: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate optimization: {str(e)}"
        )
    finally:
        session.close()
        db.close()

