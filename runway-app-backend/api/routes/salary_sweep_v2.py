"""
Salary Sweep Optimizer API v2 - With Database Persistence

Complete redesign with:
- Database persistence for configurations and EMI patterns
- CRUD operations for managing EMIs
- Smart model suggestions (keep/update/delete)
- State management across sessions
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
import sys
from pathlib import Path
import logging
import uuid
import re
from collections import defaultdict
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from storage.database import DatabaseManager
from storage.models import User, Transaction, SalarySweepConfig, DetectedEMIPattern, Asset, Liability
from auth.dependencies import get_current_user, get_db
from config import Config
from ml.categorizer import MLCategorizer

logger = logging.getLogger(__name__)

# Initialize ML categorizer
ml_categorizer = MLCategorizer()

router = APIRouter()

SALARY_ACCOUNT_RATE = 2.5  # Annual interest rate (%)
SAVINGS_ACCOUNT_RATE = 7.0  # Annual interest rate (%)


# ============================================================================
# Pydantic Models
# ============================================================================

class EMIPatternResponse(BaseModel):
    """Detected or saved recurring payment pattern"""
    pattern_id: str
    merchant_source: str
    emi_amount: float
    occurrence_count: int
    category: Optional[str] = None  # 'Loan', 'Insurance', 'Investment', 'Government Scheme'
    subcategory: Optional[str] = None  # 'Home Loan', 'Life Insurance', 'Mutual Fund SIP', etc.
    is_confirmed: bool
    user_label: Optional[str] = None
    suggested_action: Optional[str] = None  # 'keep', 'update', 'delete'
    suggestion_reason: Optional[str] = None
    transaction_ids: List[str]
    first_detected_date: str
    last_detected_date: str
    mapped_as: Optional[str] = None
    mapped_entity_id: Optional[str] = None


class SalaryResponse(BaseModel):
    """Detected or saved salary"""
    source: str
    amount: float
    count: int
    is_confirmed: bool


class DetectPatternsResponse(BaseModel):
    """Response from pattern detection"""
    has_existing_config: bool
    salary: Optional[SalaryResponse]
    emis: List[EMIPatternResponse]
    message: str


class ConfirmConfigRequest(BaseModel):
    """Request to confirm/save salary sweep configuration"""
    salary_source: str
    salary_amount: float
    emi_pattern_ids: List[str]  # Pattern IDs to include
    salary_account_rate: Optional[float] = SALARY_ACCOUNT_RATE
    savings_account_rate: Optional[float] = SAVINGS_ACCOUNT_RATE


class UpdateEMIRequest(BaseModel):
    """Request to update an EMI pattern"""
    pattern_id: str
    user_label: Optional[str] = None
    emi_amount: Optional[float] = None


class OptimizerScenario(BaseModel):
    """Optimization scenario results"""
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


class CalculateResponse(BaseModel):
    """Full optimization calculation results"""
    current_scenario: OptimizerScenario
    uniform_sweep: OptimizerScenario
    optimized_sweep: OptimizerScenario
    recommendation: str
    interest_gain_vs_current: float


class ConfigResponse(BaseModel):
    """Saved configuration response"""
    config_id: str
    salary_source: str
    salary_amount: float
    selected_scenario: Optional[str]
    monthly_interest_saved: Optional[float]
    annual_interest_saved: Optional[float]
    confirmed_emis: List[EMIPatternResponse]
    optimization_results: Optional[CalculateResponse]


# ============================================================================
# Helper Functions
# ============================================================================

def categorize_recurring_payment(merchant: str, description: str) -> tuple[str, str]:
    """
    Determine category and subcategory for a recurring payment

    Returns: (category, subcategory)
    - category: 'Loan', 'Insurance', 'Investment', 'Government Scheme'
    - subcategory: More specific classification
    """
    merchant_lower = (merchant or '').lower()
    description_lower = (description or '').lower()

    # Check LOAN/EMI
    loan_merchants = ['canfin', 'bajaj finserv', 'bajaj finance', 'tata capital', 'fullerton',
                     'iifl', 'mahindra finance', 'cholamandalam', 'l&t finance', 'lic housing',
                     'dhfl', 'indiabulls', 'hdfc bank', 'icici bank', 'sbi']
    loan_keywords = ['emi', 'loan', 'housing', 'mortgage', 'auto loan', 'car loan', 'personal loan',
                    'home loan', 'canfinhomesltd', 'housingloan']

    if any(lender in merchant_lower for lender in loan_merchants):
        # Determine loan type
        if any(kw in description_lower for kw in ['home', 'housing', 'canfin']):
            return ('Loan', 'Home Loan')
        elif any(kw in description_lower for kw in ['car', 'auto', 'vehicle']):
            return ('Loan', 'Auto Loan')
        elif any(kw in description_lower for kw in ['personal', 'pl ']):
            return ('Loan', 'Personal Loan')
        else:
            return ('Loan', 'EMI')

    if any(kw in description_lower for kw in loan_keywords):
        if any(kw in description_lower for kw in ['home', 'housing']):
            return ('Loan', 'Home Loan')
        elif any(kw in description_lower for kw in ['car', 'auto']):
            return ('Loan', 'Auto Loan')
        elif any(kw in description_lower for kw in ['personal']):
            return ('Loan', 'Personal Loan')
        else:
            return ('Loan', 'EMI')

    # Check INSURANCE
    insurance_keywords = ['sbi life', 'lic', 'hdfc life', 'icici prudential', 'max life',
                         'bajaj allianz', 'tata aia', 'birla sun life', 'insurance',
                         'kotak life', 'pnb metlife', 'star health', 'care health',
                         'religare health', 'aditya birla health', 'niva bupa']
    if any(kw in merchant_lower or kw in description_lower for kw in insurance_keywords):
        if any(kw in description_lower for kw in ['health', 'mediclaim']):
            return ('Insurance', 'Health Insurance')
        elif any(kw in description_lower for kw in ['life', 'term']):
            return ('Insurance', 'Life Insurance')
        else:
            return ('Insurance', 'Insurance Premium')

    # Check INVESTMENT (Mutual Funds, SIP)
    investment_keywords = ['mutual fund', 'sip', 'systematic', 'zerodha', 'groww',
                          'paytm money', 'et money', 'kuvera', 'coin dcb',
                          'hdfc mf', 'icici prudential mf', 'sbi mf', 'axis mf',
                          'kotak mf', 'nippon india', 'franklin templeton']
    if any(kw in merchant_lower or kw in description_lower for kw in investment_keywords):
        if any(kw in description_lower for kw in ['sip', 'systematic']):
            return ('Investment', 'Mutual Fund SIP')
        else:
            return ('Investment', 'Investment')

    # Check GOVERNMENT SCHEME
    govt_keywords = ['apy', 'atal pension', 'nps', 'national pension', 'ppf',
                    'public provident', 'epf', 'employee provident', 'esi',
                    'employee state insurance', 'sukanya samriddhi', 'pmjjby',
                    'pmsby', 'pm jeevan', 'pm suraksha']
    if any(kw in merchant_lower or kw in description_lower for kw in govt_keywords):
        if any(kw in description_lower for kw in ['apy', 'atal pension']):
            return ('Government Scheme', 'APY')
        elif any(kw in description_lower for kw in ['nps', 'national pension']):
            return ('Government Scheme', 'NPS')
        elif any(kw in description_lower for kw in ['ppf', 'public provident']):
            return ('Government Scheme', 'PPF')
        elif any(kw in description_lower for kw in ['epf', 'employee provident']):
            return ('Government Scheme', 'EPF')
        else:
            return ('Government Scheme', 'Govt Scheme')

    # Default to Loan if we can't determine (for backward compatibility)
    return ('Loan', 'Recurring Payment')


def detect_salary_pattern(transactions: List[Transaction]) -> Optional[dict]:
    """Detect recurring salary credits by amount similarity and salary keywords"""
    # Filter for credit transactions
    logger.info(f"🧐 SALARY DETECTION INPUT: Received {len(transactions)} total transactions")
    if transactions:
        logger.info(f"🧐 Sample transaction types: {[txn.type for txn in transactions[:5]]}")

    credit_txns = [txn for txn in transactions if txn.type == 'credit']

    logger.info(f"🧐 SALARY DETECTION DEBUG: Analyzing {len(credit_txns)} credit transactions")
    
    if len(credit_txns) == 0:
        logger.info("⚠️  No credit transactions found")
        return None
    
    # COMPREHENSIVE SALARY DETECTION PATTERNS
    # Priority 1: Ultra-High Confidence (98-99%)
    ultra_high_keywords = [
        'salary', 'salary credit', 'salary transfer', 'sal', 'salry', 'salar',
        'payroll', 'payroll salary', 'hr payroll'
    ]
    
    # Priority 3: Special Salary Payments (75-88%)
    special_payments = [
        'advance salary', 'adv salary', 'bonus', 'variable pay', 'variablepay',
        'incentive', 'incent', 'gratuity', 'grat', 'stipend', '13th month', 'thirteenth'
    ]
    
    # Employer patterns (only for repeated patterns or explicit salary keywords)
    employer_patterns = [
        'infy', 'infosys', 'tcs', 'tata consultancy', 'wipro', 'hcl', 'cognizant', 'cts',
        'accenture', 'acn', 'techm', 'tech mahindra', 'capgemini', 'cap', 'ibm', 'syntel',
        'l&t infotech', 'ltim', 'lt tree', 'lt thermal', 'mindtree',
        'paytm', 'flipkart', 'amazon', 'netflix', 'razorpay',
        'capital one', 'capital1', 'capitalone'
    ]
    
    # NEGATIVE INDICATORS - Must exclude these (anti-patterns)
    # NOTE: CMS (Cash Management System) is commonly used for salary credits in Indian banks
    # Only exclude /lpbn which is a loan pattern
    exclude_keywords = [
        'refund', 'reversal', 'cancellation', 'cancel', 'dividend', 'divid',
        'interest', 'int.pd', 'int paid', 'loan', 'emi', 'installment',
        'rent', 'insurance', 'transfer out', 'cashback', 'cash back', 'fee', 'charges',
        '/lpbn'  # Loan code pattern
    ]
    
    # Combine all positive keywords
    salary_keywords = ultra_high_keywords + special_payments
    
    # Look for single transactions with salary keywords and substantial amounts
    single_salary_candidates = []
    for idx, txn in enumerate(credit_txns):
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 Transaction #{idx+1}/{len(credit_txns)}")
        logger.info(f"   Date: {txn.date}, Amount: ₹{txn.amount:,.2f}")
        logger.info(f"   Merchant: {txn.merchant_canonical}")
        logger.info(f"   Description: {txn.description_raw}")
        
        if txn.amount >= 50000:  # Only substantial amounts
            desc = (txn.description_raw or '').lower()
            merch = (txn.merchant_canonical or '').lower()
            combined = f"{desc} {merch}"
            
            logger.info(f"   ✅ Substantial amount (≥₹50K) - Checking salary patterns...")
            logger.info(f"   Combined text: '{combined[:100]}'")
            
            # FIRST: Check for negative indicators - exclude these immediately
            matched_excludes = [exclude for exclude in exclude_keywords if exclude in combined]
            if matched_excludes:
                logger.info(f"   ❌ EXCLUDED - Found negative indicators: {matched_excludes}")
                continue
            
            # THEN: Check for positive salary indicators
            has_salary_keyword = any(keyword in combined for keyword in salary_keywords)
            matched_salary_keywords = [kw for kw in salary_keywords if kw in combined]
            
            # Check for high-confidence patterns (NEFT/RTGS + salary/payroll)
            has_high_confidence_pattern = (
                ('neft' in combined or 'rtgs' in combined) and 
                ('salary' in combined or 'payroll' in combined or 'sal ' in combined)
            )
            
            # Check employer patterns only with explicit salary keywords
            matched_employers = [emp for emp in employer_patterns if emp in combined]
            has_employer_and_salary = (
                any(employer in combined for employer in employer_patterns) and 
                has_salary_keyword
            )
            
            logger.info(f"   Keyword matches: {matched_salary_keywords}")
            logger.info(f"   Employer matches: {matched_employers}")
            logger.info(f"   Has salary keyword: {has_salary_keyword}")
            logger.info(f"   Has high-confidence pattern: {has_high_confidence_pattern}")
            logger.info(f"   Has employer + salary: {has_employer_and_salary}")
            
            if has_salary_keyword or has_high_confidence_pattern or has_employer_and_salary:
                logger.info(f"   ✅ MATCHED - Added to salary candidates")
                single_salary_candidates.append(txn)
            else:
                logger.info(f"   ⏭️  No salary pattern match")
        else:
            logger.info(f"   ⏭️  Amount too small (<₹50K) - Skipping")
    
    # Group by similar amounts (not by merchant, since merchants may vary per transaction)
    amount_groups = []
    
    for txn in credit_txns:
        added = False
        for group in amount_groups:
            # Check if this transaction's amount is similar to the group average (within 20% variation)
            avg_in_group = sum(t['amount'] for t in group) / len(group)
            if abs(txn.amount - avg_in_group) / avg_in_group <= 0.2:
                group.append({'amount': txn.amount, 'txn': txn})
                added = True
                break
        
        if not added:
            amount_groups.append([{'amount': txn.amount, 'txn': txn}])
    
    # Filter groups with at least 2 occurrences
    recurring_patterns = [g for g in amount_groups if len(g) >= 2]
    
    # If we have single salary candidates, prioritize them if no recurring patterns exist
    if single_salary_candidates and not recurring_patterns:
        # Use the largest single salary candidate
        best_single = max(single_salary_candidates, key=lambda t: t.amount)
        logger.info(f"\n{'='*80}")
        logger.info(f"✅ SALARY DETECTED: Single Transaction")
        logger.info(f"   Source: {best_single.merchant_canonical}")
        logger.info(f"   Amount: ₹{best_single.amount:,.2f}")
        logger.info(f"   Date: {best_single.date}")
        logger.info(f"   Reason: No recurring patterns found, using largest single match")
        return {
            'source': best_single.merchant_canonical or "Salary",
            'amount': best_single.amount,
            'count': 1,
            'txns': [best_single]
        }
    
    # If no recurring patterns, return None
    if not recurring_patterns:
        logger.info(f"\n{'='*80}")
        logger.info(f"❌ NO SALARY DETECTED")
        logger.info(f"   Found {len(single_salary_candidates)} salary candidates but no recurring patterns")
        logger.info(f"   Single candidates: {[f'₹{t.amount:,.2f}' for t in single_salary_candidates]}")
        return None
    
    # Find the largest recurring pattern (most likely to be salary)
    best_pattern = max(recurring_patterns, key=lambda g: sum(t['amount'] for t in g) / len(g))

    # Check if the best recurring pattern contains any salary keywords or employer patterns
    has_salary_in_pattern = False
    has_employer_in_pattern = False
    pattern_avg = sum(t['amount'] for t in best_pattern) / len(best_pattern)

    for t in best_pattern:
        txn = t['txn']
        desc = (txn.description_raw or '').lower()
        merch = (txn.merchant_canonical or '').lower()
        combined = f"{desc} {merch}"
        if any(keyword in combined for keyword in salary_keywords):
            has_salary_in_pattern = True
            break
        if any(employer in combined for employer in employer_patterns):
            has_employer_in_pattern = True

    # NEW: If large recurring credit (≥2 occurrences, ≥30K avg) with NEFT/RTGS from employer, consider it salary
    is_large_recurring_credit = (
        len(best_pattern) >= 2 and
        pattern_avg >= 30000 and
        has_employer_in_pattern
    )

    # Also check for NEFT/RTGS patterns which are common for salaries
    has_neft_pattern = False
    for t in best_pattern:
        txn = t['txn']
        desc = (txn.description_raw or '').lower()
        if 'neft' in desc or 'rtgs' in desc:
            has_neft_pattern = True
            break
    
    # If we have single salary candidates that are larger than the recurring pattern AND the pattern doesn't have salary keywords, use the single candidate
    if single_salary_candidates and not has_salary_in_pattern and not is_large_recurring_credit:
        largest_single = max(single_salary_candidates, key=lambda t: t.amount)

        # If the single salary candidate is significantly larger (30% more), use it
        if largest_single.amount > pattern_avg * 1.3:
            logger.info(f"\n{'='*80}")
            logger.info(f"✅ SALARY DETECTED: Single Large Transaction (Higher than recurring pattern)")
            logger.info(f"   Source: {largest_single.merchant_canonical}")
            logger.info(f"   Amount: ₹{largest_single.amount:,.2f}")
            return {
                'source': largest_single.merchant_canonical or "Salary",
                'amount': largest_single.amount,
                'count': 1,
                'txns': [largest_single]
            }

    amounts = [t['amount'] for t in best_pattern]
    txns = [t['txn'] for t in best_pattern]
    avg_amount = sum(amounts) / len(amounts)

    # Determine detection reason for logging
    detection_reason = []
    if has_salary_in_pattern:
        detection_reason.append("Contains salary keywords")
    if is_large_recurring_credit:
        detection_reason.append(f"Large recurring credit (≥₹30K, {len(best_pattern)}x) from employer")
    if has_neft_pattern and has_employer_in_pattern:
        detection_reason.append("NEFT/RTGS from employer")
    if not detection_reason:
        detection_reason.append("Largest recurring pattern")
    
    # Get the most common merchant from this pattern
    merchants = [txn.merchant_canonical for txn in txns if txn.merchant_canonical]
    most_common_merchant = max(set(merchants), key=merchants.count) if merchants else "Recurring Credit"
    
    logger.info(f"\n{'='*80}")
    logger.info(f"✅ SALARY DETECTED: Recurring Pattern")
    logger.info(f"   Reason: {'; '.join(detection_reason)}")
    logger.info(f"   Source: {most_common_merchant}")
    logger.info(f"   Average Amount: ₹{avg_amount:,.2f}")
    logger.info(f"   Occurrences: {len(amounts)}")
    logger.info(f"   Transactions:")
    for i, txn in enumerate(txns[:5], 1):
        logger.info(f"     {i}. {txn.date} | ₹{txn.amount:,.2f} | {txn.merchant_canonical}")
    if len(txns) > 5:
        logger.info(f"     ... and {len(txns)-5} more")
    
    return {
        'source': most_common_merchant,
        'amount': avg_amount,
        'count': len(amounts),
        'txns': txns
    }


def analyze_emi_pattern_changes(
    existing_pattern: DetectedEMIPattern,
    current_transactions: List[Transaction],
    session
) -> tuple[str, str]:
    """
    Analyze if EMI pattern has changed and suggest action

    Returns: (suggested_action, reason)
    """
    # Get current EMI transactions matching this pattern
    merchant = existing_pattern.merchant_source
    current_emis = [t for t in current_transactions
                   if t.merchant_canonical == merchant and t.type == 'debit']

    if not current_emis:
        return ('delete', f'No recent transactions found for {merchant}. EMI may have been closed.')

    # Check if amounts have changed
    current_amounts = [t.amount for t in current_emis]
    avg_current = sum(current_amounts) / len(current_amounts)
    existing_amount = existing_pattern.emi_amount

    # If amount changed by more than 5%
    if abs(avg_current - existing_amount) / existing_amount > 0.05:
        return ('update', f'EMI amount changed from ₹{existing_amount:,.0f} to ₹{avg_current:,.0f}. Consider updating.')

    # Check if frequency changed (e.g., was monthly, now quarterly)
    if len(current_emis) < existing_pattern.occurrence_count / 2:
        return ('delete', f'Payment frequency reduced significantly. May have been closed or restructured.')

    # All good!
    return ('keep', 'Pattern is consistent with historical data.')


def calculate_optimization(
    salary_amount: float,
    confirmed_emis: List[DetectedEMIPattern],
    salary_rate: float = SALARY_ACCOUNT_RATE,
    savings_rate: float = SAVINGS_ACCOUNT_RATE
) -> CalculateResponse:
    """Calculate all three optimization scenarios"""

    total_emi = sum(emi.emi_amount for emi in confirmed_emis)

    # Scenario 1: Current (no sweep)
    current_scenario = OptimizerScenario(
        name='Current Setup (No Sweep)',
        description='Keep all salary in low-interest salary account',
        emi_dates=None,
        salary_account_balance=salary_amount,
        savings_account_balance=0.0,
        avg_days_in_savings=0.0,
        monthly_interest_salary=(salary_amount * salary_rate / 100 / 12),
        monthly_interest_savings=0.0,
        total_monthly_interest=(salary_amount * salary_rate / 100 / 12),
        total_annual_interest=(salary_amount * salary_rate / 100)
    )

    # Scenario 2: Uniform sweep (all EMIs on day 1)
    surplus_after_emis = salary_amount - total_emi
    avg_days_uniform = 15  # Average days in savings for uniform scenario

    monthly_interest_salary_uniform = total_emi * salary_rate / 100 / 12
    monthly_interest_savings_uniform = surplus_after_emis * savings_rate / 100 / 12 * (avg_days_uniform / 30)

    uniform_scenario = OptimizerScenario(
        name='Uniform Sweep (All EMIs Day 1)',
        description='Pay all EMIs on day 1, sweep surplus to savings',
        emi_dates='All on 1st',
        salary_account_balance=total_emi,
        savings_account_balance=surplus_after_emis,
        avg_days_in_savings=avg_days_uniform,
        monthly_interest_salary=monthly_interest_salary_uniform,
        monthly_interest_savings=monthly_interest_savings_uniform,
        total_monthly_interest=monthly_interest_salary_uniform + monthly_interest_savings_uniform,
        total_annual_interest=(monthly_interest_salary_uniform + monthly_interest_savings_uniform) * 12
    )

    # Scenario 3: Optimized (stagger EMIs throughout month)
    # Simulate staggering EMIs to maximize days in savings
    num_emis = len(confirmed_emis)
    if num_emis > 0:
        # Distribute EMIs evenly throughout the month
        avg_days_optimized = 20  # Better than uniform
    else:
        avg_days_optimized = 28  # Almost full month if no EMIs

    monthly_interest_salary_opt = total_emi * salary_rate / 100 / 12
    monthly_interest_savings_opt = surplus_after_emis * savings_rate / 100 / 12 * (avg_days_optimized / 30)

    optimized_scenario = OptimizerScenario(
        name='Optimized Sweep (Staggered EMIs)',
        description='Stagger EMI dates to maximize time in high-interest savings',
        emi_dates='Spread: 5th, 10th, 15th, 20th...',
        salary_account_balance=total_emi,
        savings_account_balance=surplus_after_emis,
        avg_days_in_savings=avg_days_optimized,
        monthly_interest_salary=monthly_interest_salary_opt,
        monthly_interest_savings=monthly_interest_savings_opt,
        total_monthly_interest=monthly_interest_salary_opt + monthly_interest_savings_opt,
        total_annual_interest=(monthly_interest_salary_opt + monthly_interest_savings_opt) * 12
    )

    # Calculate gains
    interest_gain = optimized_scenario.total_annual_interest - current_scenario.total_annual_interest

    # Recommendation
    if interest_gain > 5000:
        recommendation = f"Highly Recommended: Save ₹{interest_gain:,.0f}/year with optimized sweep!"
    elif interest_gain > 2000:
        recommendation = f"Recommended: Save ₹{interest_gain:,.0f}/year with salary sweep"
    else:
        recommendation = f"Marginal benefit: ₹{interest_gain:,.0f}/year gain"

    return CalculateResponse(
        current_scenario=current_scenario,
        uniform_sweep=uniform_scenario,
        optimized_sweep=optimized_scenario,
        recommendation=recommendation,
        interest_gain_vs_current=interest_gain
    )


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/config", response_model=Optional[ConfigResponse])
async def get_saved_config(
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Get user's saved salary sweep configuration (if exists)"""
    session = db.get_session()

    try:
        config = session.query(SalarySweepConfig).filter(
            SalarySweepConfig.user_id == current_user.user_id,
            SalarySweepConfig.is_active == True
        ).first()

        if not config:
            return None

        # Get confirmed EMI patterns
        confirmed_emis = session.query(DetectedEMIPattern).filter(
            DetectedEMIPattern.config_id == config.config_id,
            DetectedEMIPattern.is_confirmed == True
        ).all()

        emi_responses = [
            EMIPatternResponse(
                pattern_id=emi.pattern_id,
                merchant_source=emi.merchant_source,
                emi_amount=emi.emi_amount,
                occurrence_count=emi.occurrence_count,
                is_confirmed=emi.is_confirmed,
                user_label=emi.user_label,
                suggested_action=emi.suggested_action,
                suggestion_reason=emi.suggestion_reason,
                transaction_ids=emi.transaction_ids or [],
                first_detected_date=emi.first_detected_date,
                last_detected_date=emi.last_detected_date
            )
            for emi in confirmed_emis
        ]

        # Parse optimization results if saved
        optimization_results = None
        if config.optimization_data:
            optimization_results = CalculateResponse(**config.optimization_data)

        return ConfigResponse(
            config_id=config.config_id,
            salary_source=config.salary_source,
            salary_amount=config.salary_amount,
            selected_scenario=config.selected_scenario,
            monthly_interest_saved=config.monthly_interest_saved,
            annual_interest_saved=config.annual_interest_saved,
            confirmed_emis=emi_responses,
            optimization_results=optimization_results
        )

    finally:
        session.close()


@router.post("/detect", response_model=DetectPatternsResponse)
async def detect_or_refresh_patterns(
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """
    Detect patterns from transactions OR refresh existing patterns with smart suggestions

    If user has existing config:
    - Returns saved salary and EMIs
    - Analyzes if patterns have changed
    - Suggests keep/update/delete actions

    If no existing config:
    - Detects new patterns from transactions
    """
    session = db.get_session()

    try:
        # Check for existing configuration
        existing_config = session.query(SalarySweepConfig).filter(
            SalarySweepConfig.user_id == current_user.user_id,
            SalarySweepConfig.is_active == True
        ).first()

        # Get all user transactions
        all_transactions = db.get_transactions(user_id=current_user.user_id)
        logger.info(f"📊 DEBUG: Retrieved {len(all_transactions)} transactions for user {current_user.user_id}")
        logger.info(f"📊 DEBUG: User email: {current_user.username}")

        if existing_config:
            # USER HAS EXISTING CONFIG - Re-detect ALL patterns (saved + new)
            logger.info(f"Re-detecting all patterns for existing config: {existing_config.config_id}")

            # Get saved EMI patterns for comparison
            saved_emis = session.query(DetectedEMIPattern).filter(
                DetectedEMIPattern.config_id == existing_config.config_id
            ).all()
            saved_merchants = {f"{emi.merchant_source}_{emi.emi_amount}" for emi in saved_emis}

            # Detect ALL patterns (same logic as new detection)
            logger.info("Detecting all recurring financial obligations...")

            # Apply comprehensive filtering
            financial_transactions = []
            for txn in all_transactions:
                if txn.type != 'debit' or txn.amount < 100:  # Lower threshold for investments/schemes
                    continue

                merchant_lower = (txn.merchant_canonical or '').lower()
                description_lower = (txn.description_raw or '').lower()

                # Skip UPI and generic transfers
                if 'upi/' in description_lower or 'paytm' in description_lower:
                    continue
                if any(word in merchant_lower for word in ['sweep', 'transfer', 'ndr fruits']):
                    continue

                # Check if it's a financial obligation (loan, insurance, investment, scheme)
                is_loan = any(lender in merchant_lower for lender in [
                    'canfin', 'bajaj finserv', 'bajaj finance', 'tata capital',
                    'fullerton', 'iifl', 'mahindra finance', 'cholamandalam',
                    'l&t finance', 'lic housing', 'dhfl', 'indiabulls',
                    'personal loan', 'home loan', 'car loan', 'housing finance'
                ])
                has_loan_keywords = any(kw in description_lower for kw in [
                    'emi', 'personal loan', 'home loan', 'car loan', 'auto loan',
                    'housing loan', 'loan emi', 'canfinhomesltd', 'housingloan'
                ])

                is_insurance = any(kw in description_lower for kw in [
                    'sbi life', 'lic', 'hdfc life', 'icici prudential', 'insurance',
                    'bajaj allianz', 'tata aia', 'max life', 'policy', 'premium'
                ])

                is_investment = any(kw in description_lower for kw in [
                    'mutual fund', 'sip', 'systematic', 'zerodha', 'groww',
                    'paytm money', 'et money', 'kuvera', 'investment'
                ])

                is_govt_scheme = any(kw in description_lower for kw in [
                    'apy', 'atal pension', 'nps', 'national pension', 'ppf',
                    'provident fund', 'epf', 'sukanya', 'postal'
                ])

                if is_loan or has_loan_keywords or is_insurance or is_investment or is_govt_scheme:
                    financial_transactions.append(txn)

            # Group by merchant and exact amount
            debit_patterns = defaultdict(lambda: defaultdict(list))
            for txn in financial_transactions:
                merchant = txn.merchant_canonical or txn.description_raw or "Unknown"
                exact_amount = round(txn.amount, 0)
                debit_patterns[merchant][exact_amount].append(txn)

            # Build response with ALL patterns (saved + new)
            emi_responses = []
            for merchant, amount_groups in debit_patterns.items():
                for exact_amount, txns in amount_groups.items():
                    if len(txns) < 2:
                        continue

                    # Check 2+ months criterion
                    dates_with_months = []
                    for txn in txns:
                        if txn.date:
                            try:
                                if isinstance(txn.date, str):
                                    date_obj = None
                                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                                        try:
                                            date_obj = datetime.strptime(txn.date, fmt)
                                            break
                                        except:
                                            continue
                                    if not date_obj:
                                        continue
                                else:
                                    date_obj = txn.date
                                month_key = f"{date_obj.year}-{date_obj.month:02d}"
                                dates_with_months.append((date_obj, month_key))
                            except:
                                pass

                    unique_months = set([m for _, m in dates_with_months])
                    if len(unique_months) < 2:
                        continue

                    dates = [d for d, _ in dates_with_months]
                    txn_ids = [t.transaction_id for t in txns]
                    pattern_key = f"{merchant}_{exact_amount}"

                    # Check if already saved
                    is_saved = pattern_key in saved_merchants
                    suggestion = 'keep' if is_saved else 'keep'
                    reason = 'Already tracked' if is_saved else 'Newly detected recurring payment'

                    # If already saved, get the pattern_id from DB
                    saved_pattern = next((e for e in saved_emis if f"{e.merchant_source}_{e.emi_amount}" == pattern_key), None)
                    pattern_id = saved_pattern.pattern_id if saved_pattern else str(uuid.uuid4())

                    # Determine category and subcategory
                    if saved_pattern and saved_pattern.category:
                        category = saved_pattern.category
                        subcategory = saved_pattern.subcategory
                    else:
                        # Get first transaction for categorization
                        first_txn = txns[0] if txns else None
                        if first_txn:
                            category, subcategory = categorize_recurring_payment(
                                first_txn.merchant_canonical or '',
                                first_txn.description_raw or ''
                            )
                        else:
                            category, subcategory = ('Loan', 'Recurring Payment')

                    emi_responses.append(EMIPatternResponse(
                        pattern_id=pattern_id,
                        merchant_source=merchant,
                        emi_amount=exact_amount,
                        occurrence_count=len(txns),
                        category=category,
                        subcategory=subcategory,
                        is_confirmed=is_saved,
                        user_label=saved_pattern.user_label if saved_pattern else None,
                        suggested_action=suggestion,
                        suggestion_reason=reason,
                        transaction_ids=txn_ids,
                        first_detected_date=min(dates).strftime('%d/%m/%Y') if dates else "",
                        last_detected_date=max(dates).strftime('%d/%m/%Y') if dates else ""
                    ))

            # Sort: saved first, then by amount
            emi_responses.sort(key=lambda x: (not x.is_confirmed, -x.emi_amount))

            salary_response = SalaryResponse(
                source=existing_config.salary_source,
                amount=existing_config.salary_amount,
                count=0,
                is_confirmed=True
            )

            saved_count = sum(1 for e in emi_responses if e.is_confirmed)
            new_count = len(emi_responses) - saved_count

            return DetectPatternsResponse(
                has_existing_config=True,
                salary=salary_response,
                emis=emi_responses,
                message=f"Found {len(emi_responses)} recurring payments: {saved_count} already tracked, {new_count} new patterns detected."
            )

        else:
            # NO EXISTING CONFIG - Detect new patterns
            logger.info("No existing config found, detecting new patterns")

            # Detect salary
            salary_pattern = detect_salary_pattern(all_transactions)
            salary_response = None

            if salary_pattern:
                salary_response = SalaryResponse(
                    source=salary_pattern['source'],
                    amount=salary_pattern['amount'],
                    count=salary_pattern['count'],
                    is_confirmed=False
                )

            # Detect ALL recurring financial obligations (Loans, Insurance, Investments, Government Schemes)
            logger.info("Identifying all recurring financial obligations...")

            # Get all debit transactions
            debit_txns = [t for t in all_transactions if t.type == 'debit']

            # Filter transactions using comprehensive multi-category detection
            financial_transactions = []

            for txn in debit_txns:
                # Minimum amount threshold
                if txn.amount < 500:  # Lower threshold to catch insurance/schemes
                    continue

                merchant_lower = (txn.merchant_canonical or '').lower()
                description_lower = (txn.description_raw or '').lower()

                # Skip UPI transactions
                if 'upi/' in description_lower or 'paytm' in description_lower:
                    continue

                # Skip generic transfers/sweeps
                if any(word in merchant_lower for word in ['sweep', 'transfer', 'ndr fruits']):
                    continue

                # Check if it's a LOAN/EMI
                is_loan = any(lender in merchant_lower for lender in [
                    'canfin', 'bajaj finserv', 'bajaj finance', 'tata capital',
                    'fullerton', 'iifl', 'mahindra finance', 'cholamandalam',
                    'l&t finance', 'lic housing', 'dhfl', 'indiabulls',
                    'personal loan', 'home loan', 'car loan', 'housing finance'
                ]) or any(kw in description_lower for kw in [
                    'emi', 'personal loan', 'home loan', 'car loan', 'auto loan',
                    'housing loan', 'loan emi', 'canfinhomesltd', 'housingloan'
                ])

                # Check if it's INSURANCE
                is_insurance = any(kw in merchant_lower or kw in description_lower for kw in [
                    'sbi life', 'lic', 'hdfc life', 'icici prudential', 'max life',
                    'bajaj allianz', 'tata aia', 'birla sun life', 'insurance',
                    'kotak life', 'pnb metlife', 'star health', 'care health',
                    'religare health', 'aditya birla health', 'niva bupa'
                ])

                # Check if it's INVESTMENT (Mutual Fund SIP)
                is_investment = any(kw in merchant_lower or kw in description_lower for kw in [
                    'mutual fund', 'sip', 'systematic', 'zerodha', 'groww',
                    'paytm money', 'et money', 'kuvera', 'coin dcb',
                    'hdfc mf', 'icici prudential mf', 'sbi mf', 'axis mf',
                    'kotak mf', 'nippon india', 'franklin templeton'
                ])

                # Check if it's GOVERNMENT SCHEME
                is_govt_scheme = any(kw in merchant_lower or kw in description_lower for kw in [
                    'apy', 'atal pension', 'nps', 'national pension', 'ppf',
                    'public provident', 'epf', 'employee provident', 'esi',
                    'employee state insurance', 'sukanya samriddhi', 'pmjjby',
                    'pmsby', 'pm jeevan', 'pm suraksha'
                ])

                # If matches any category, add to financial transactions
                if is_loan or is_insurance or is_investment or is_govt_scheme:
                    financial_transactions.append(txn)
                    category = 'Loan' if is_loan else 'Insurance' if is_insurance else 'Investment' if is_investment else 'Govt Scheme'
                    logger.info(f"Identified {category}: {txn.merchant_canonical} - ₹{txn.amount}")

            logger.info(f"Total identified financial obligation transactions: {len(financial_transactions)}")

            # Step 2: Apply strict criteria - EXACT same amount over 2+ months
            debit_patterns = defaultdict(lambda: defaultdict(list))  # merchant -> amount -> [txns]

            for txn in financial_transactions:
                merchant = txn.merchant_canonical or txn.description_raw or "Unknown"
                # Round to nearest rupee for exact matching
                exact_amount = round(txn.amount, 0)
                debit_patterns[merchant][exact_amount].append(txn)

            # Convert to EMI responses - strict loan criteria
            emi_responses = []
            for merchant, amount_groups in debit_patterns.items():
                for exact_amount, txns in amount_groups.items():
                    # Criteria: Exact same amount, 2+ payments
                    if len(txns) >= 2:
                        # Check if payments span at least 2 different months
                        dates_with_months = []
                        for txn in txns:
                            if txn.date:
                                try:
                                    if isinstance(txn.date, str):
                                        # Try multiple date formats
                                        date_obj = None
                                        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                                            try:
                                                date_obj = datetime.strptime(txn.date, fmt)
                                                break
                                            except:
                                                continue
                                        if not date_obj:
                                            continue
                                    else:
                                        date_obj = txn.date
                                    month_key = f"{date_obj.year}-{date_obj.month:02d}"
                                    dates_with_months.append((date_obj, month_key))
                                except Exception as e:
                                    logger.warning(f"Date parsing error for {txn.date}: {e}")
                                    pass

                        # Check unique months
                        unique_months = set([m for _, m in dates_with_months])
                        if len(unique_months) >= 2:  # At least 2 different months
                            dates = [d for d, _ in dates_with_months]
                            txn_ids = [t.transaction_id for t in txns]

                            # Determine category and subcategory
                            first_txn = txns[0] if txns else None
                            if first_txn:
                                category, subcategory = categorize_recurring_payment(
                                    first_txn.merchant_canonical or '',
                                    first_txn.description_raw or ''
                                )
                            else:
                                category, subcategory = ('Loan', 'Recurring Payment')

                            emi_responses.append(EMIPatternResponse(
                                pattern_id=str(uuid.uuid4()),  # Temporary ID for new patterns
                                merchant_source=merchant,
                                emi_amount=exact_amount,  # Exact amount, not average
                                occurrence_count=len(txns),
                                category=category,
                                subcategory=subcategory,
                                is_confirmed=False,
                                user_label=None,
                                suggested_action='keep',
                                suggestion_reason=f'Recurring payment: {len(unique_months)} monthly payments detected',
                                transaction_ids=txn_ids,
                                first_detected_date=min(dates).strftime('%Y-%m-%d') if dates else "",
                                last_detected_date=max(dates).strftime('%Y-%m-%d') if dates else ""
                            ))

            # Sort by amount (largest first)
            emi_responses.sort(key=lambda x: x.emi_amount, reverse=True)

            return DetectPatternsResponse(
                has_existing_config=False,
                salary=salary_response,
                emis=emi_responses,
                message=f"Detected {len(emi_responses)} recurring payment patterns. Please confirm to proceed."
            )

    except Exception as e:
        logger.error(f"Error detecting patterns: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect patterns: {str(e)}"
        )
    finally:
        session.close()


@router.post("/confirm", response_model=ConfigResponse)
async def confirm_and_save_config(
    request: ConfirmConfigRequest,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """
    Confirm and save salary sweep configuration

    Creates or updates configuration with selected salary and EMIs
    """
    session = db.get_session()

    try:
        # Check if config already exists
        existing_config = session.query(SalarySweepConfig).filter(
            SalarySweepConfig.user_id == current_user.user_id,
            SalarySweepConfig.is_active == True
        ).first()

        if existing_config:
            config_id = existing_config.config_id
            # Update existing
            existing_config.salary_source = request.salary_source
            existing_config.salary_amount = request.salary_amount
            existing_config.salary_account_rate = request.salary_account_rate
            existing_config.savings_account_rate = request.savings_account_rate
            existing_config.updated_at = datetime.now()

            # Delete old EMI patterns not in new selection
            session.query(DetectedEMIPattern).filter(
                DetectedEMIPattern.config_id == config_id,
                DetectedEMIPattern.pattern_id.notin_(request.emi_pattern_ids)
            ).delete(synchronize_session=False)

        else:
            # Create new configuration
            config_id = str(uuid.uuid4())
            new_config = SalarySweepConfig(
                config_id=config_id,
                user_id=current_user.user_id,
                salary_source=request.salary_source,
                salary_amount=request.salary_amount,
                salary_account_rate=request.salary_account_rate,
                savings_account_rate=request.savings_account_rate,
                is_active=True
            )
            session.add(new_config)

        # Get all transactions to get fresh data for selected patterns
        all_transactions = db.get_transactions(user_id=current_user.user_id)

        # Detect ALL recurring financial obligations using the SAME logic as detect endpoint
        logger.info("Re-detecting selected recurring financial obligations with strict filters...")

        # Apply same comprehensive multi-category filtering as detect endpoint
        financial_transactions = []
        for txn in all_transactions:
            if txn.type != 'debit' or txn.amount < 500:
                continue

            merchant_lower = (txn.merchant_canonical or '').lower()
            description_lower = (txn.description_raw or '').lower()

            # Skip UPI, transfers
            if 'upi/' in description_lower or 'paytm' in description_lower:
                continue
            if any(word in merchant_lower for word in ['sweep', 'transfer', 'ndr fruits']):
                continue

            # Check if it's a LOAN/EMI
            is_loan = any(lender in merchant_lower for lender in [
                'canfin', 'bajaj finserv', 'bajaj finance', 'tata capital',
                'fullerton', 'iifl', 'mahindra finance', 'cholamandalam',
                'l&t finance', 'lic housing', 'dhfl', 'indiabulls',
                'personal loan', 'home loan', 'car loan', 'housing finance'
            ]) or any(kw in description_lower for kw in [
                'emi', 'personal loan', 'home loan', 'car loan', 'auto loan',
                'housing loan', 'loan emi', 'canfinhomesltd', 'housingloan'
            ])

            # Check if it's INSURANCE
            is_insurance = any(kw in merchant_lower or kw in description_lower for kw in [
                'sbi life', 'lic', 'hdfc life', 'icici prudential', 'max life',
                'bajaj allianz', 'tata aia', 'birla sun life', 'insurance',
                'kotak life', 'pnb metlife', 'star health', 'care health',
                'religare health', 'aditya birla health', 'niva bupa'
            ])

            # Check if it's INVESTMENT (Mutual Fund SIP)
            is_investment = any(kw in merchant_lower or kw in description_lower for kw in [
                'mutual fund', 'sip', 'systematic', 'zerodha', 'groww',
                'paytm money', 'et money', 'kuvera', 'coin dcb',
                'hdfc mf', 'icici prudential mf', 'sbi mf', 'axis mf',
                'kotak mf', 'nippon india', 'franklin templeton'
            ])

            # Check if it's GOVERNMENT SCHEME
            is_govt_scheme = any(kw in merchant_lower or kw in description_lower for kw in [
                'apy', 'atal pension', 'nps', 'national pension', 'ppf',
                'public provident', 'epf', 'employee provident', 'esi',
                'employee state insurance', 'sukanya samriddhi', 'pmjjby',
                'pmsby', 'pm jeevan', 'pm suraksha'
            ])

            # If matches any category, add to financial transactions
            if is_loan or is_insurance or is_investment or is_govt_scheme:
                financial_transactions.append(txn)

        # Group by merchant and exact amount
        debit_patterns = defaultdict(lambda: defaultdict(list))
        for txn in financial_transactions:
            merchant = txn.merchant_canonical or txn.description_raw or "Unknown"
            exact_amount = round(txn.amount, 0)
            debit_patterns[merchant][exact_amount].append(txn)

        # Build confirmed patterns from detected patterns
        confirmed_emi_patterns = []
        temp_id_map = {}  # Map temp IDs to merchants for matching

        for merchant, amount_groups in debit_patterns.items():
            for exact_amount, txns in amount_groups.items():
                if len(txns) < 2:
                    continue

                # Check 2+ months criterion
                dates_with_months = []
                for txn in txns:
                    if txn.date:
                        try:
                            if isinstance(txn.date, str):
                                date_obj = None
                                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                                    try:
                                        date_obj = datetime.strptime(txn.date, fmt)
                                        break
                                    except:
                                        continue
                                if not date_obj:
                                    continue
                            else:
                                date_obj = txn.date
                            month_key = f"{date_obj.year}-{date_obj.month:02d}"
                            dates_with_months.append((date_obj, month_key))
                        except:
                            pass

                unique_months = set([m for _, m in dates_with_months])
                if len(unique_months) < 2:
                    continue

                dates = [d for d, _ in dates_with_months]
                txn_ids = [t.transaction_id for t in txns]
                pattern_key = f"{merchant}_{exact_amount}"

                # Check if this pattern was selected by user
                # (Frontend sends temp pattern IDs, we need to match by merchant+amount)
                existing_pattern = session.query(DetectedEMIPattern).filter(
                    DetectedEMIPattern.config_id == config_id,
                    DetectedEMIPattern.merchant_source == merchant,
                    DetectedEMIPattern.emi_amount == exact_amount
                ).first()

                # Determine category and subcategory
                first_txn = txns[0] if txns else None
                if first_txn:
                    category, subcategory = categorize_recurring_payment(
                        first_txn.merchant_canonical or '',
                        first_txn.description_raw or ''
                    )
                else:
                    category, subcategory = ('Loan', 'Recurring Payment')

                if existing_pattern:
                    # Update existing pattern
                    existing_pattern.emi_amount = exact_amount
                    existing_pattern.occurrence_count = len(txns)
                    existing_pattern.category = category
                    existing_pattern.subcategory = subcategory
                    existing_pattern.transaction_ids = txn_ids
                    existing_pattern.last_detected_date = max(dates).strftime('%d/%m/%Y') if dates else ""
                    existing_pattern.is_confirmed = True
                    existing_pattern.suggested_action = 'keep'
                    confirmed_emi_patterns.append(existing_pattern)
                else:
                    # Create new pattern
                    new_pattern = DetectedEMIPattern(
                        pattern_id=str(uuid.uuid4()),
                        config_id=config_id,
                        user_id=current_user.user_id,
                        merchant_source=merchant,
                        emi_amount=exact_amount,
                        occurrence_count=len(txns),
                        category=category,
                        subcategory=subcategory,
                        is_confirmed=True,
                        transaction_ids=txn_ids,
                        first_detected_date=min(dates).strftime('%d/%m/%Y') if dates else "",
                        last_detected_date=max(dates).strftime('%d/%m/%Y') if dates else "",
                        suggested_action='keep',
                        suggestion_reason='Confirmed by user'
                    )
                    session.add(new_pattern)
                    confirmed_emi_patterns.append(new_pattern)

        session.commit()

        # Refresh to get IDs
        session.refresh(existing_config if existing_config else new_config)
        for pattern in confirmed_emi_patterns:
            session.refresh(pattern)

        config = existing_config if existing_config else new_config

        # Build response
        emi_responses = [
            EMIPatternResponse(
                pattern_id=emi.pattern_id,
                merchant_source=emi.merchant_source,
                emi_amount=emi.emi_amount,
                occurrence_count=emi.occurrence_count,
                category=emi.category,
                subcategory=emi.subcategory,
                is_confirmed=emi.is_confirmed,
                user_label=emi.user_label,
                suggested_action=emi.suggested_action,
                suggestion_reason=emi.suggestion_reason,
                transaction_ids=emi.transaction_ids or [],
                first_detected_date=emi.first_detected_date,
                last_detected_date=emi.last_detected_date
            )
            for emi in confirmed_emi_patterns
        ]

        return ConfigResponse(
            config_id=config.config_id,
            salary_source=config.salary_source,
            salary_amount=config.salary_amount,
            selected_scenario=config.selected_scenario,
            monthly_interest_saved=config.monthly_interest_saved,
            annual_interest_saved=config.annual_interest_saved,
            confirmed_emis=emi_responses,
            optimization_results=None  # Will be calculated next
        )

    except Exception as e:
        session.rollback()
        logger.error(f"Error confirming config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save configuration: {str(e)}"
        )
    finally:
        session.close()


@router.post("/calculate", response_model=ConfigResponse)
async def calculate_and_save_optimization(
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """
    Calculate optimization scenarios and save results

    Uses the confirmed configuration to calculate all three scenarios
    """
    session = db.get_session()

    try:
        # Get configuration
        config = session.query(SalarySweepConfig).filter(
            SalarySweepConfig.user_id == current_user.user_id,
            SalarySweepConfig.is_active == True
        ).first()

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No salary sweep configuration found. Please confirm your setup first."
            )

        # Get confirmed EMIs
        confirmed_emis = session.query(DetectedEMIPattern).filter(
            DetectedEMIPattern.config_id == config.config_id,
            DetectedEMIPattern.is_confirmed == True
        ).all()

        # Calculate optimization
        optimization_results = calculate_optimization(
            config.salary_amount,
            confirmed_emis,
            config.salary_account_rate,
            config.savings_account_rate
        )

        # Save results to configuration
        config.optimization_data = optimization_results.dict()
        config.selected_scenario = 'optimized_sweep'  # Default to optimized
        config.monthly_interest_saved = (
            optimization_results.optimized_sweep.total_monthly_interest -
            optimization_results.current_scenario.total_monthly_interest
        )
        config.annual_interest_saved = optimization_results.interest_gain_vs_current
        config.updated_at = datetime.now()

        session.commit()
        session.refresh(config)

        # Build response
        emi_responses = [
            EMIPatternResponse(
                pattern_id=emi.pattern_id,
                merchant_source=emi.merchant_source,
                emi_amount=emi.emi_amount,
                occurrence_count=emi.occurrence_count,
                category=emi.category,
                subcategory=emi.subcategory,
                is_confirmed=emi.is_confirmed,
                user_label=emi.user_label,
                suggested_action=emi.suggested_action,
                suggestion_reason=emi.suggestion_reason,
                transaction_ids=emi.transaction_ids or [],
                first_detected_date=emi.first_detected_date,
                last_detected_date=emi.last_detected_date
            )
            for emi in confirmed_emis
        ]

        return ConfigResponse(
            config_id=config.config_id,
            salary_source=config.salary_source,
            salary_amount=config.salary_amount,
            selected_scenario=config.selected_scenario,
            monthly_interest_saved=config.monthly_interest_saved,
            annual_interest_saved=config.annual_interest_saved,
            confirmed_emis=emi_responses,
            optimization_results=optimization_results
        )

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error calculating optimization: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate optimization: {str(e)}"
        )
    finally:
        session.close()


@router.patch("/emi/{pattern_id}", response_model=EMIPatternResponse)
async def update_emi_pattern(
    pattern_id: str,
    request: UpdateEMIRequest,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Update an EMI pattern (label or amount)"""
    session = db.get_session()

    try:
        pattern = session.query(DetectedEMIPattern).filter(
            DetectedEMIPattern.pattern_id == pattern_id,
            DetectedEMIPattern.user_id == current_user.user_id
        ).first()

        if not pattern:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="EMI pattern not found"
            )

        if request.user_label is not None:
            pattern.user_label = request.user_label

        if request.emi_amount is not None:
            pattern.emi_amount = request.emi_amount

        pattern.updated_at = datetime.now()
        session.commit()
        session.refresh(pattern)

        return EMIPatternResponse(
            pattern_id=pattern.pattern_id,
            merchant_source=pattern.merchant_source,
            emi_amount=pattern.emi_amount,
            occurrence_count=pattern.occurrence_count,
            category=pattern.category,
            subcategory=pattern.subcategory,
            is_confirmed=pattern.is_confirmed,
            user_label=pattern.user_label,
            suggested_action=pattern.suggested_action,
            suggestion_reason=pattern.suggestion_reason,
            transaction_ids=pattern.transaction_ids or [],
            first_detected_date=pattern.first_detected_date,
            last_detected_date=pattern.last_detected_date
        )

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating EMI pattern: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update EMI pattern: {str(e)}"
        )
    finally:
        session.close()


@router.delete("/emi/{pattern_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_emi_pattern(
    pattern_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Delete an EMI pattern"""
    session = db.get_session()

    try:
        pattern = session.query(DetectedEMIPattern).filter(
            DetectedEMIPattern.pattern_id == pattern_id,
            DetectedEMIPattern.user_id == current_user.user_id
        ).first()

        if not pattern:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="EMI pattern not found"
            )

        session.delete(pattern)
        session.commit()

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting EMI pattern: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete EMI pattern: {str(e)}"
        )
    finally:
        session.close()


@router.delete("/config", status_code=status.HTTP_204_NO_CONTENT)
async def delete_configuration(
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Delete entire salary sweep configuration (start fresh)"""
    session = db.get_session()

    try:
        # Delete will cascade to EMI patterns
        session.query(SalarySweepConfig).filter(
            SalarySweepConfig.user_id == current_user.user_id
        ).delete()

        session.commit()

    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting configuration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete configuration: {str(e)}"
        )
    finally:
        session.close()


# ============================================================================
# Centralized Recurring Payments Endpoint
# ============================================================================

class RecurringPaymentsByCategoryResponse(BaseModel):
    """Recurring payments grouped by category"""
    loans: List[EMIPatternResponse]
    insurance: List[EMIPatternResponse]
    investments: List[EMIPatternResponse]
    government_schemes: List[EMIPatternResponse]


@router.get("/recurring-payments", response_model=RecurringPaymentsByCategoryResponse)
async def get_recurring_payments_by_category(
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """
    Get all saved recurring payments grouped by category

    This is a centralized endpoint that can be used by:
    - Salary Sweep Optimizer (uses all categories)
    - Loan Optimizer (uses only 'Loan' category)
    - Investment Dashboard (uses 'Investment' category)
    - Insurance Tracker (uses 'Insurance' category)
    - Government Schemes Tracker (uses 'Government Scheme' category)
    """
    session = db.get_session()

    try:
        # Check if user has saved configuration
        config = session.query(SalarySweepConfig).filter(
            SalarySweepConfig.user_id == current_user.user_id,
            SalarySweepConfig.is_active == True
        ).first()

        if not config:
            # Return empty lists if no configuration
            return RecurringPaymentsByCategoryResponse(
                loans=[],
                insurance=[],
                investments=[],
                government_schemes=[]
            )

        # Get all confirmed recurring payments
        all_patterns = session.query(DetectedEMIPattern).filter(
            DetectedEMIPattern.config_id == config.config_id,
            DetectedEMIPattern.is_confirmed == True
        ).all()

        # Group by category
        loans = []
        insurance = []
        investments = []
        government_schemes = []

        for pattern in all_patterns:
            # Determine mapping status from liabilities/assets
            mapped_as = None
            mapped_entity_id = None
            # Liability mapping via recurring_pattern_id
            mapped_liability = session.query(Liability).filter(
                Liability.user_id == current_user.user_id,
                Liability.recurring_pattern_id == pattern.pattern_id
            ).first()
            if mapped_liability:
                mapped_as = 'liability'
                mapped_entity_id = mapped_liability.liability_id
            else:
                # Asset mapping via notes contains pattern_id
                mapped_asset = session.query(Asset).filter(
                    Asset.user_id == current_user.user_id,
                    Asset.notes.isnot(None)
                ).all()
                for a in mapped_asset:
                    if a.notes and pattern.pattern_id in str(a.notes):
                        mapped_as = 'asset'
                        mapped_entity_id = a.asset_id
                        break

            emi_response = EMIPatternResponse(
                pattern_id=pattern.pattern_id,
                merchant_source=pattern.merchant_source,
                emi_amount=pattern.emi_amount,
                occurrence_count=pattern.occurrence_count,
                category=pattern.category,
                subcategory=pattern.subcategory,
                is_confirmed=pattern.is_confirmed,
                user_label=pattern.user_label,
                suggested_action=pattern.suggested_action,
                suggestion_reason=pattern.suggestion_reason,
                transaction_ids=pattern.transaction_ids or [],
                first_detected_date=pattern.first_detected_date,
                last_detected_date=pattern.last_detected_date,
                mapped_as=mapped_as,
                mapped_entity_id=mapped_entity_id
            )

            if pattern.category == 'Loan':
                loans.append(emi_response)
            elif pattern.category == 'Insurance':
                insurance.append(emi_response)
            elif pattern.category == 'Investment':
                investments.append(emi_response)
            elif pattern.category == 'Government Scheme':
                government_schemes.append(emi_response)

        # Sort each category by amount (largest first)
        loans.sort(key=lambda x: x.emi_amount, reverse=True)
        insurance.sort(key=lambda x: x.emi_amount, reverse=True)
        investments.sort(key=lambda x: x.emi_amount, reverse=True)
        government_schemes.sort(key=lambda x: x.emi_amount, reverse=True)

        return RecurringPaymentsByCategoryResponse(
            loans=loans,
            insurance=insurance,
            investments=investments,
            government_schemes=government_schemes
        )

    except Exception as e:
        logger.error(f"Error fetching recurring payments: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch recurring payments: {str(e)}"
        )
    finally:
        session.close()
