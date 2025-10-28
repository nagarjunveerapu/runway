"""
Loan Prepayment Optimizer API
Analyzes recurring EMI patterns and calculates optimal prepayment strategies
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

# Pydantic models
class DetectedLoan(BaseModel):
    source: str
    avg_emi: float
    count: int
    txns: List[dict] = []

class LoanInput(BaseModel):
    loan_id: str
    name: str
    source: str
    emi: float
    remaining_principal: float
    interest_rate: float
    remaining_tenure_months: int

class PrepaymentScenario(BaseModel):
    name: str
    description: str
    loans: List[dict]
    total_interest: float
    total_saved: float
    total_tenure_reduction_months: int

class LoanPrepaymentResponse(BaseModel):
    detected_loans: List[DetectedLoan]
    monthly_income: float
    monthly_expenses: float
    monthly_cash_flow: float
    scenarios: dict  # {no_prepayment, uniform, optimized}


def get_db():
    """Get database instance"""
    return DatabaseManager(Config.DATABASE_URL)


def get_merchant_source(description):
    """Extract merchant/source from transaction description"""
    if not description:
        return 'unknown'

    desc_lower = str(description).lower()

    # Common loan/EMI patterns
    if 'canfin' in desc_lower or 'home loan' in desc_lower:
        return 'canfin homes'
    if 'personal loan' in desc_lower or 'bil/personal' in desc_lower:
        return 'personal loan'
    if 'hdfc' in desc_lower:
        return 'hdfc'
    if 'icici' in desc_lower:
        return 'icici'
    if 'sbi' in desc_lower or 'state bank' in desc_lower:
        return 'sbi'
    if 'axis' in desc_lower:
        return 'axis'

    # Extract first few words
    words = description.split()
    if len(words) >= 2:
        return ' '.join(words[:2]).lower()

    return description[:30].lower()


def is_similar_amount(amt1, amt2, variance=0.15):
    """Check if two amounts are similar (within variance)"""
    if amt1 == 0 or amt2 == 0:
        return False
    diff = abs(amt1 - amt2)
    avg = (amt1 + amt2) / 2
    return diff / avg <= variance


def calculate_emi(principal, rate_percent, tenure_months):
    """Calculate EMI using reducing balance method"""
    monthly_rate = rate_percent / 100 / 12
    if monthly_rate == 0:
        return principal / tenure_months

    emi = principal * monthly_rate * pow(1 + monthly_rate, tenure_months) / (pow(1 + monthly_rate, tenure_months) - 1)
    return emi


def calculate_loan_with_prepayment(principal, rate_percent, tenure_months, annual_prepayment=0):
    """Calculate loan details with optional prepayment"""
    monthly_rate = rate_percent / 100 / 12
    emi = calculate_emi(principal, rate_percent, tenure_months)

    balance = principal
    total_interest = 0
    months_paid = 0
    monthly_prepayment = annual_prepayment / 12

    for month in range(1, tenure_months + 1):
        if balance <= 0.01:
            break

        interest_portion = balance * monthly_rate
        principal_portion = emi - interest_portion

        total_interest += interest_portion
        balance -= principal_portion

        # Apply prepayment
        if monthly_prepayment > 0 and balance > 0:
            balance -= monthly_prepayment
            if balance < 0:
                balance = 0

        months_paid = month

        if balance <= 0.01:
            break

    return {
        'emi': emi,
        'total_interest': total_interest,
        'actual_tenure': months_paid,
        'tenure_reduction': tenure_months - months_paid,
        'interest_saved': 0  # Will be calculated by comparing scenarios
    }


@router.post("/detect", response_model=dict)
async def detect_loan_patterns(
    current_user: User = Depends(get_current_user)
):
    """
    Detect recurring loan/EMI patterns from user transactions
    """

    db = get_db()
    session = db.get_session()

    try:
        # Get all debit transactions
        transactions = session.query(Transaction).filter(
            Transaction.user_id == current_user.user_id,
            Transaction.type == 'debit'
        ).order_by(Transaction.date).all()

        # Filter substantial debits (potential EMIs)
        substantial_debits = [t for t in transactions if float(t.amount) >= 10000]

        # Group by merchant/source
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

        # Find recurring patterns (3+ occurrences)
        loan_patterns = []
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

            # Find patterns with 3+ occurrences
            for amt, group in amount_groups.items():
                if len(group) >= 3:
                    loan_patterns.append({
                        'source': source,
                        'txns': [t for t in group],
                        'avg_emi': sum(t['amount'] for t in group) / len(group),
                        'count': len(group)
                    })

        # Sort by EMI amount (highest first)
        loan_patterns.sort(key=lambda x: x['avg_emi'], reverse=True)

        # Calculate income and expenses for cash flow
        all_txns = session.query(Transaction).filter(
            Transaction.user_id == current_user.user_id
        ).all()

        income = sum(float(t.amount) for t in all_txns if t.type == 'credit')
        expenses = sum(float(t.amount) for t in all_txns if t.type == 'debit'
                      and not any(p['source'] in str(t.description_raw or '').lower()
                                for p in loan_patterns))

        # Average over 3 months (rough estimate)
        monthly_income = income / 3 if income > 0 else 100000
        monthly_expenses = expenses / 3 if expenses > 0 else 50000

        return {
            'detected_loans': loan_patterns,
            'monthly_income': monthly_income,
            'monthly_expenses': monthly_expenses
        }

    except Exception as e:
        logger.error(f"Error detecting loan patterns: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect loan patterns: {str(e)}"
        )
    finally:
        session.close()
        db.close()


class CalculateRequest(BaseModel):
    loans: List[LoanInput]
    annual_prepayment: float
    monthly_income: float
    monthly_expenses: float


@router.post("/calculate", response_model=LoanPrepaymentResponse)
async def calculate_prepayment_optimization(
    request: CalculateRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Calculate loan prepayment optimization with different scenarios
    """

    try:
        loans = request.loans
        annual_prepayment = request.annual_prepayment
        monthly_income = request.monthly_income
        monthly_expenses = request.monthly_expenses

        # Calculate cash flow
        total_monthly_emi = sum(loan.emi for loan in loans)
        monthly_cash_flow = monthly_income - monthly_expenses - total_monthly_emi

        # Scenario 1: No prepayment
        no_prepayment_loans = []
        total_interest_no_prepayment = 0

        for loan in loans:
            result = calculate_loan_with_prepayment(
                loan.remaining_principal,
                loan.interest_rate,
                loan.remaining_tenure_months,
                0
            )
            no_prepayment_loans.append({
                'name': loan.name,
                'emi': result['emi'],
                'interest': result['total_interest'],
                'tenure': result['actual_tenure'],
                'prepayment_annual': 0
            })
            total_interest_no_prepayment += result['total_interest']

        # Scenario 2: Equal distribution
        equal_prepayment_per_loan = annual_prepayment / len(loans) if loans else 0
        uniform_loans = []
        total_interest_uniform = 0

        for loan in loans:
            result = calculate_loan_with_prepayment(
                loan.remaining_principal,
                loan.interest_rate,
                loan.remaining_tenure_months,
                equal_prepayment_per_loan
            )
            result['interest_saved'] = (
                next(l['interest'] for l in no_prepayment_loans if l['name'] == loan.name) -
                result['total_interest']
            )
            uniform_loans.append({
                'name': loan.name,
                'emi': result['emi'],
                'interest': result['total_interest'],
                'tenure': result['actual_tenure'],
                'tenure_reduction': result['tenure_reduction'],
                'interest_saved': result['interest_saved'],
                'prepayment_annual': equal_prepayment_per_loan
            })
            total_interest_uniform += result['total_interest']

        # Scenario 3: Optimized (prioritize high interest loans)
        sorted_loans = sorted(loans, key=lambda x: x.interest_rate, reverse=True)
        optimized_loans = []
        total_interest_optimized = 0
        remaining_prepayment = annual_prepayment

        for loan in sorted_loans:
            # Allocate prepayment to this loan
            loan_prepayment = min(remaining_prepayment, loan.remaining_principal * 0.5)  # Max 50% per year
            remaining_prepayment -= loan_prepayment

            result = calculate_loan_with_prepayment(
                loan.remaining_principal,
                loan.interest_rate,
                loan.remaining_tenure_months,
                loan_prepayment
            )
            result['interest_saved'] = (
                next(l['interest'] for l in no_prepayment_loans if l['name'] == loan.name) -
                result['total_interest']
            )
            optimized_loans.append({
                'name': loan.name,
                'emi': result['emi'],
                'interest': result['total_interest'],
                'tenure': result['actual_tenure'],
                'tenure_reduction': result['tenure_reduction'],
                'interest_saved': result['interest_saved'],
                'prepayment_annual': loan_prepayment,
                'priority': sorted_loans.index(loan) + 1
            })
            total_interest_optimized += result['total_interest']

        # Sort back to original order
        optimized_loans.sort(key=lambda x: next(i for i, l in enumerate(loans) if l.name == x['name']))

        # Calculate total tenure reduction
        total_tenure_reduction_uniform = sum(l['tenure_reduction'] for l in uniform_loans)
        total_tenure_reduction_optimized = sum(l['tenure_reduction'] for l in optimized_loans)

        scenarios = {
            'no_prepayment': {
                'name': 'No Prepayment',
                'description': 'Continue with regular EMI payments',
                'loans': no_prepayment_loans,
                'total_interest': total_interest_no_prepayment,
                'total_saved': 0,
                'total_tenure_reduction_months': 0
            },
            'uniform': {
                'name': 'Equal Distribution',
                'description': f'Split ₹{annual_prepayment:,.0f}/year equally across all loans',
                'loans': uniform_loans,
                'total_interest': total_interest_uniform,
                'total_saved': total_interest_no_prepayment - total_interest_uniform,
                'total_tenure_reduction_months': total_tenure_reduction_uniform
            },
            'optimized': {
                'name': 'Optimized (High Interest First)',
                'description': f'Prioritize ₹{annual_prepayment:,.0f}/year to highest interest loans',
                'loans': optimized_loans,
                'total_interest': total_interest_optimized,
                'total_saved': total_interest_no_prepayment - total_interest_optimized,
                'total_tenure_reduction_months': total_tenure_reduction_optimized
            }
        }

        return LoanPrepaymentResponse(
            detected_loans=[],  # Already detected in /detect endpoint
            monthly_income=monthly_income,
            monthly_expenses=monthly_expenses,
            monthly_cash_flow=monthly_cash_flow,
            scenarios=scenarios
        )

    except Exception as e:
        logger.error(f"Error calculating prepayment optimization: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate optimization: {str(e)}"
        )
