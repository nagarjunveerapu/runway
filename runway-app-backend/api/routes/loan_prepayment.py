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
from storage.models import Transaction, User, TransactionType
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
    original_principal: Optional[float] = None
    remaining_principal: Optional[float] = None
    is_completed: bool = False
    total_paid: Optional[float] = None

class LoanInput(BaseModel):
    loan_id: str
    name: str
    source: str
    emi: float
    remaining_principal: float
    interest_rate: float
    remaining_tenure_months: int
    is_completed: bool = False
    original_principal: Optional[float] = None
    total_paid: Optional[float] = None

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
    
    # Remove EMI keywords for better matching
    desc_clean = desc_lower.replace('emi', '').strip()
    
    # Extract merchant name (first 2-3 words, excluding common suffixes)
    words = desc_clean.split()
    # Remove common suffixes
    filtered_words = []
    skip_words = ['ltd', 'limited', 'pvt', 'private', 'p', 'lt', 'ltd.', 'private.', 'bangal', 'gurgaon', 'bangalore', 'in']
    for word in words:
        if word not in skip_words:
            filtered_words.append(word)
        if len(filtered_words) >= 3:
            break
    
    if filtered_words:
        return ' '.join(filtered_words[:3]).title()  # Title case for consistency
    
    # Fallback: extract first few words
    words = description.split()
    if len(words) >= 2:
        return ' '.join(words[:2]).title()

    return description[:30].title()


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
            Transaction.type == TransactionType.DEBIT
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

        # Find EMI-converted transactions (original purchases)
        emi_converted_txns = {}
        for txn in transactions:
            extra_metadata = txn.extra_metadata or {}
            if extra_metadata.get('emi_converted', False):
                merchant = txn.merchant_canonical or get_merchant_source(txn.description_raw or '')
                if merchant not in emi_converted_txns:
                    emi_converted_txns[merchant] = txn
        
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
                    # Check if this merchant has an EMI-converted transaction
                    # Try multiple matching strategies
                    merchant = group[0].get('merchant_canonical') or source
                    
                    # First try exact merchant match
                    original_txn = emi_converted_txns.get(merchant)
                    
                    # If no exact match, try fuzzy matching
                    if not original_txn:
                        merchant_lower = merchant.lower()
                        # Extract key words from merchant (words longer than 3 chars)
                        merchant_keywords = [w for w in merchant_lower.split() if len(w) > 3]
                        
                        # Check each EMI-converted transaction
                        for emi_merchant, emi_txn in emi_converted_txns.items():
                            emi_merchant_lower = emi_merchant.lower()
                            emi_keywords = [w for w in emi_merchant_lower.split() if len(w) > 3]
                            
                            # Check if key words match
                            if merchant_keywords and emi_keywords:
                                # Check if significant keywords match (e.g., "HDFC", "School", "Ample", "Technologies")
                                matching_keywords = [k for k in merchant_keywords if k in emi_keywords or any(k in e for e in emi_keywords)]
                                if len(matching_keywords) >= min(len(merchant_keywords), len(emi_keywords)) - 1:
                                    original_txn = emi_txn
                                    break
                        
                        # Last resort: check if merchant name is contained in EMI merchant name or vice versa
                        if not original_txn:
                            for emi_merchant, emi_txn in emi_converted_txns.items():
                                emi_merchant_lower = emi_merchant.lower()
                                # Check if one contains the other (for cases like "HDFC" vs "HDFC School")
                                if merchant_lower in emi_merchant_lower or emi_merchant_lower in merchant_lower:
                                    original_txn = emi_txn
                                    break
                    
                    # Calculate principal and remaining balance
                    original_principal = None
                    remaining_principal = None
                    total_paid = None
                    is_completed = False
                    
                    if original_txn:
                        original_principal = float(original_txn.amount)
                        # Only count EMI payments (transactions with "EMI" in description)
                        emi_payments = [
                            t for t in group 
                            if 'emi' in str(t.get('description_raw', '')).lower() or 
                               'emi' in str(merchant).lower()
                        ]
                        if not emi_payments:
                            # If no explicit EMI keyword, assume all are EMI payments
                            emi_payments = group
                        
                        total_paid = sum(t['amount'] for t in emi_payments)
                        remaining_principal = original_principal - total_paid
                        is_completed = remaining_principal <= 0
                    
                    loan_patterns.append({
                        'source': source,
                        'txns': [t for t in group],
                        'avg_emi': sum(t['amount'] for t in group) / len(group),
                        'count': len(group),
                        'original_principal': original_principal,
                        'remaining_principal': remaining_principal if remaining_principal is not None else None,
                        'total_paid': total_paid,
                        'is_completed': is_completed
                    })

        # Sort by EMI amount (highest first)
        loan_patterns.sort(key=lambda x: x['avg_emi'], reverse=True)

        # Calculate income and expenses for cash flow
        all_txns = session.query(Transaction).filter(
            Transaction.user_id == current_user.user_id
        ).all()

        # Handle ENUM comparison (works for both ENUM and string for backward compatibility)
        income = sum(
            float(t.amount) for t in all_txns 
            if (t.type.value if hasattr(t.type, 'value') else t.type) == TransactionType.CREDIT.value
        )
        expenses = sum(
            float(t.amount) for t in all_txns 
            if (t.type.value if hasattr(t.type, 'value') else t.type) == TransactionType.DEBIT.value
                      and not any(p['source'] in str(t.description_raw or '').lower()
                                for p in loan_patterns))

        # Average over 3 months (rough estimate)
        monthly_income = income / 3 if income > 0 else 100000
        monthly_expenses = expenses / 3 if expenses > 0 else 50000

        # Convert loan_patterns to DetectedLoan models to ensure proper serialization
        detected_loans = [
            DetectedLoan(
                source=p['source'],
                avg_emi=p['avg_emi'],
                count=p['count'],
                txns=p.get('txns', []),
                original_principal=p.get('original_principal'),
                remaining_principal=p.get('remaining_principal'),
                is_completed=p.get('is_completed', False),
                total_paid=p.get('total_paid')
            )
            for p in loan_patterns
        ]
        
        return {
            'detected_loans': [loan.model_dump() if hasattr(loan, 'model_dump') else loan.dict() for loan in detected_loans],
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

        # Calculate cash flow (exclude completed loans)
        active_loans = [loan for loan in loans if not loan.is_completed]
        total_monthly_emi = sum(loan.emi for loan in active_loans)
        monthly_cash_flow = monthly_income - monthly_expenses - total_monthly_emi

        # Scenario 1: No prepayment (only active loans)
        no_prepayment_loans = []
        total_interest_no_prepayment = 0

        for loan in active_loans:
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

        # Scenario 2: Equal distribution (only active loans)
        equal_prepayment_per_loan = annual_prepayment / len(active_loans) if active_loans else 0
        uniform_loans = []
        total_interest_uniform = 0

        for loan in active_loans:
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

        # Scenario 3: Optimized (prioritize high interest loans, only active loans)
        sorted_loans = sorted(active_loans, key=lambda x: x.interest_rate, reverse=True)
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
        optimized_loans.sort(key=lambda x: next(i for i, l in enumerate(active_loans) if l.name == x['name']))

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
