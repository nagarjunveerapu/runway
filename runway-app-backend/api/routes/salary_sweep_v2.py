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
from storage.models import User, Transaction, SalarySweepConfig, DetectedEMIPattern, Asset, Liability, BankTransaction, CreditCardTransaction
from auth.dependencies import get_current_user, get_db
from config import Config
from ml.categorizer import MLCategorizer
from services.investment_detection import InvestmentDetector
from services.salary_sweep_service import SalarySweepService

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

# Helper function wrappers for compatibility - these delegate to the service
# These are kept for backward compatibility with existing route code
def categorize_recurring_payment(merchant: str, description: str) -> tuple[str, str]:
    """Determine category and subcategory for a recurring payment. Delegates to SalarySweepService."""
    db_manager = DatabaseManager()
    service = SalarySweepService(db_manager)
    return service.categorize_recurring_payment(merchant, description)


def _keyword_sets():
    """Central source of keyword lists for categorization."""
    db_manager = DatabaseManager()
    service = SalarySweepService(db_manager)
    return service._keyword_sets()


def _classify_financial_flags(merchant_lower: str, description_lower: str) -> tuple[bool, bool, bool, bool]:
    """Return tuple flags for (is_loan, is_insurance, is_investment, is_govt)."""
    db_manager = DatabaseManager()
    service = SalarySweepService(db_manager)
    return service._classify_financial_flags(merchant_lower, description_lower)


def _should_include_txn(txn: Transaction, min_amount: float = 500) -> bool:
    """Unified filter for selecting candidate debit transactions."""
    db_manager = DatabaseManager()
    service = SalarySweepService(db_manager)
    return service._should_include_txn(txn, min_amount)


def _filter_financial_transactions(transactions: List[Transaction], min_amount: float = 500) -> List[Transaction]:
    """Apply shared filtering to get candidate financial obligation transactions."""
    db_manager = DatabaseManager()
    service = SalarySweepService(db_manager)
    return service._filter_financial_transactions(transactions, min_amount)


def detect_salary_pattern(transactions: List[Transaction]) -> Optional[dict]:
    """Detect recurring salary credits by amount similarity and salary keywords. Delegates to SalarySweepService."""
    db_manager = DatabaseManager()
    service = SalarySweepService(db_manager)
    return service.detect_salary_pattern(transactions)

def _detect_salary_pattern_old(transactions: List[Transaction]) -> Optional[dict]:
    """OLD IMPLEMENTATION - Kept for reference. Use detect_salary_pattern() instead."""
    # Filter for credit transactions
    logger.info(f"🧐 SALARY DETECTION INPUT: Received {len(transactions)} total transactions")
    if transactions:
        logger.info(f"🧐 Sample transaction types: {[txn.type for txn in transactions[:5]]}")

    # Normalize transaction types: handle both 'deposit'/'withdrawal' and 'credit'/'debit'
    credit_txns = [
        txn for txn in transactions 
        if txn.type and txn.type.lower() in ['credit', 'deposit']
    ]

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
    
    def extract_merchant_from_description(description: str, merchant: str) -> str:
        """Extract merchant/employer name from description if merchant is generic.
        
        Uses intelligent pattern matching to extract company names from transaction descriptions.
        Works with NEFT/RTGS formats, UPI formats, and various other transaction formats.
        """
        import re
        
        if merchant and merchant.lower() not in ['other', 'unknown', '']:
            return merchant
        
        if not description:
            return "Salary"
        
        desc = description.strip()
        desc_lower = desc.lower()
        
        # Pattern 1: NEFT/RTGS format - "NEFT-...-COMPANY NAME PVT LTD-..." or "RTGS-...-COMPANY NAME-..."
        # Example: "NEFT-CITIN52025102945632523-CAPITAL ONE SERVICES I PVT LTD--0035493018-CITI00000"
        neft_rtgs_patterns = [
            r'(?:NEFT|RTGS)[-:]\s*\w+\s*[-:]\s*([A-Z][A-Z\s&]+?(?:PVT|LTD|INC|LLC|CORP|LLP|SERVICES|TECHNOLOGIES|SOLUTIONS)[^\s-]*)',
            r'(?:NEFT|RTGS)[-:]\s*\w+\s*[-:]\s*([A-Z][A-Z\s&]+?)\s*[-:]',
            r'(?:NEFT|RTGS)[-:]\s*([A-Z][A-Z\s&]+?)\s*PVT',
            r'(?:NEFT|RTGS)[-:]\s*([A-Z][A-Z\s&]+?)\s*LTD',
        ]
        
        for pattern in neft_rtgs_patterns:
            match = re.search(pattern, desc, re.IGNORECASE)
            if match:
                company_name = match.group(1).strip()
                # Clean up: remove trailing dashes, extra spaces
                company_name = re.sub(r'\s+[-]+\s*$', '', company_name)
                company_name = re.sub(r'\s+', ' ', company_name)
                
                # Extract meaningful part (before PVT/LTD/etc if present)
                # "CAPITAL ONE SERVICES I PVT LTD" -> "CAPITAL ONE SERVICES"
                company_match = re.search(r'^([A-Z][A-Z\s&]+?)\s+(?:PVT|LTD|INC|LLC|CORP|LLP)', company_name, re.IGNORECASE)
                if company_match:
                    company_name = company_match.group(1).strip()
                
                # Properly capitalize: "CAPITAL ONE" -> "Capital One"
                words = company_name.split()
                # Handle special cases like "I" in "SERVICES I PVT LTD"
                capitalized_words = []
                for word in words:
                    # Skip single letter words that are likely part of legal entity names
                    if len(word) == 1 and word.upper() in ['I', 'A']:
                        continue
                    # Capitalize properly
                    if word.isupper():
                        capitalized_words.append(word.capitalize())
                    else:
                        capitalized_words.append(word.title())
                
                if capitalized_words:
                    result = ' '.join(capitalized_words)
                    # Remove common suffixes that shouldn't be in the name
                    result = re.sub(r'\s+(Services|Technologies|Solutions|Systems)\s*$', '', result, flags=re.IGNORECASE)
                    if result and len(result) > 2:
                        return result
        
        # Pattern 2: Look for employer patterns from known list (for normalization)
        for employer in employer_patterns:
            if employer in desc_lower:
                # Extract the employer name from description with proper case
                employer_pattern = r'\b(' + re.escape(employer) + r'[^\s-]*)'
                match = re.search(employer_pattern, desc, re.IGNORECASE)
                if match:
                    found_text = match.group(1)
                    # Properly capitalize
                    words = found_text.split()
                    if len(words) >= 2:
                        # Multi-word: capitalize each word
                        return ' '.join(word.capitalize() for word in words[:2])
                    else:
                        # Single word
                        return found_text.capitalize()
        
        # Pattern 3: Look for company-like patterns in uppercase
        # Match sequences of 2+ uppercase words that look like company names
        company_pattern = r'\b([A-Z]{2,}(?:\s+[A-Z]{2,}){1,3})(?:\s+(?:PVT|LTD|INC|LLC|CORP|LLP|SERVICES))?'
        match = re.search(company_pattern, desc)
        if match:
            company_name = match.group(1).strip()
            # Skip if it looks like a bank name or transaction code
            skip_patterns = ['NEFT', 'RTGS', 'UPI', 'IMPS', 'CITI', 'HDFC', 'ICICI', 'SBI', 'AXIS']
            if not any(skip in company_name.upper() for skip in skip_patterns):
                # Properly capitalize
                words = company_name.split()
                if len(words) >= 2 and len(words) <= 4:  # Reasonable company name length
                    capitalized = ' '.join(word.capitalize() for word in words)
                    if len(capitalized) >= 4:  # At least 4 chars
                        return capitalized
        
        # Pattern 4: Extract from INF/INFT format - "INF/INFT/COMPANY"
        inf_match = re.search(r'INF[/-]\s*\w+\s*[/-]\s*([A-Z][A-Z\s&]+)', desc, re.IGNORECASE)
        if inf_match:
            company_name = inf_match.group(1).strip()
            words = company_name.split()
            if len(words) >= 1 and len(words) <= 3:
                return ' '.join(word.capitalize() for word in words[:2])  # Take first 2 words max
        
        # Fallback: return original merchant or "Salary"
        return merchant or "Salary"
    
    # If we have single salary candidates, prioritize them if no recurring patterns exist
    if single_salary_candidates and not recurring_patterns:
        # Use the largest single salary candidate
        best_single = max(single_salary_candidates, key=lambda t: t.amount)
        
        # Extract merchant name from description if merchant is generic
        detected_source = extract_merchant_from_description(
            best_single.description_raw or '',
            best_single.merchant_canonical or ''
        )
        
        logger.info(f"\n{'='*80}")
        logger.info(f"✅ SALARY DETECTED: Single Transaction")
        logger.info(f"   Original Merchant: {best_single.merchant_canonical}")
        logger.info(f"   Detected Source: {detected_source}")
        logger.info(f"   Amount: ₹{best_single.amount:,.2f}")
        logger.info(f"   Date: {best_single.date}")
        logger.info(f"   Reason: No recurring patterns found, using largest single match")
        return {
            'source': detected_source,
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
            # Extract merchant name from description if merchant is generic
            detected_source = extract_merchant_from_description(
                largest_single.description_raw or '',
                largest_single.merchant_canonical or ''
            )
            
            logger.info(f"\n{'='*80}")
            logger.info(f"✅ SALARY DETECTED: Single Large Transaction (Higher than recurring pattern)")
            logger.info(f"   Original Merchant: {largest_single.merchant_canonical}")
            logger.info(f"   Detected Source: {detected_source}")
            logger.info(f"   Amount: ₹{largest_single.amount:,.2f}")
            return {
                'source': detected_source,
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
    
    # Extract merchant name from description if merchant is generic
    # Try to find a transaction with a description that has employer info
    detected_source = most_common_merchant
    for txn in txns:
        if txn.description_raw:
            extracted = extract_merchant_from_description(
                txn.description_raw,
                txn.merchant_canonical or ''
            )
            if extracted.lower() not in ['other', 'unknown', 'salary', 'recurring credit']:
                detected_source = extracted
                break
    
    logger.info(f"\n{'='*80}")
    logger.info(f"✅ SALARY DETECTED: Recurring Pattern")
    logger.info(f"   Reason: {'; '.join(detection_reason)}")
    logger.info(f"   Original Merchant: {most_common_merchant}")
    logger.info(f"   Detected Source: {detected_source}")
    logger.info(f"   Average Amount: ₹{avg_amount:,.2f}")
    logger.info(f"   Occurrences: {len(amounts)}")
    logger.info(f"   Transactions:")
    for i, txn in enumerate(txns[:5], 1):
        logger.info(f"     {i}. {txn.date} | ₹{txn.amount:,.2f} | {txn.merchant_canonical}")
    if len(txns) > 5:
        logger.info(f"     ... and {len(txns)-5} more")
    
    return {
        'source': detected_source,
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
                   if t.merchant_canonical == merchant and (t.type or '').lower() in ['debit', 'withdrawal']]

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
    """Calculate all three optimization scenarios. Delegates to SalarySweepService."""
    db_manager = DatabaseManager()
    service = SalarySweepService(db_manager)
    result = service.calculate_optimization(salary_amount, confirmed_emis, salary_rate, savings_rate)
    
    # Convert dict response to Pydantic models
    return CalculateResponse(
        current_scenario=OptimizerScenario(**result['current_scenario']),
        uniform_sweep=OptimizerScenario(**result['uniform_sweep']),
        optimized_sweep=OptimizerScenario(**result['optimized_sweep']),
        recommendation=result['recommendation'],
        interest_gain_vs_current=result['interest_gain_vs_current']
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

        # Get transactions from BOTH bank and credit card
        # - For SALARY detection: use only bank transactions
        # - For EMI/Loan detection: use BOTH bank AND credit card transactions (important for credit card EMIs!)
        bank_transactions = session.query(BankTransaction).filter(
            BankTransaction.user_id == current_user.user_id
        ).all()

        cc_transactions = session.query(CreditCardTransaction).filter(
            CreditCardTransaction.user_id == current_user.user_id
        ).all()

        # Convert to Transaction-like objects for compatibility with existing detection logic
        all_transactions = []  # Combined: bank + credit card (for EMI detection)
        bank_only_transactions = []  # Bank only (for salary detection)

        # Add bank transactions
        for bt in bank_transactions:
            txn_type = bt.type.value if hasattr(bt.type, 'value') else str(bt.type)
            if isinstance(txn_type, str):
                txn_type = txn_type.lower()
            else:
                txn_type = 'debit' if 'debit' in str(txn_type).lower() else 'credit'

            adapter = type('Transaction', (), {
                'transaction_id': bt.transaction_id,
                'user_id': bt.user_id,
                'account_id': bt.account_id,
                'date': bt.date,
                'amount': bt.amount,
                'type': txn_type,
                'description_raw': bt.description_raw,
                'merchant_canonical': bt.merchant_canonical,
                'category': bt.category.value if hasattr(bt.category, 'value') else str(bt.category),
                'balance': bt.balance
            })()
            all_transactions.append(adapter)
            bank_only_transactions.append(adapter)  # Also add to bank-only list

        # Add credit card transactions (for EMI detection)
        for ct in cc_transactions:
            txn_type = ct.type.value if hasattr(ct.type, 'value') else str(ct.type)
            if isinstance(txn_type, str):
                txn_type = txn_type.lower()
            else:
                txn_type = 'debit' if 'debit' in str(txn_type).lower() else 'credit'

            adapter = type('Transaction', (), {
                'transaction_id': ct.transaction_id,
                'user_id': ct.user_id,
                'account_id': ct.account_id,
                'date': ct.date,
                'amount': ct.amount,
                'type': txn_type,
                'description_raw': ct.description_raw,
                'merchant_canonical': ct.merchant_canonical,
                'category': ct.category.value if hasattr(ct.category, 'value') else str(ct.category),
                'balance': getattr(ct, 'balance', None)
            })()
            all_transactions.append(adapter)

        logger.info(f"📊 DEBUG: Retrieved {len(bank_transactions)} bank + {len(cc_transactions)} credit card transactions for user {current_user.user_id}")
        logger.info(f"📊 DEBUG: Converted {len(all_transactions)} transactions to adapter objects")

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
            logger.info(f"📊 DEBUG: About to filter {len(all_transactions)} transactions for financial obligations...")

            # Apply comprehensive filtering (shared helper)
            financial_transactions = _filter_financial_transactions(all_transactions, min_amount=100)
            logger.info(f"📊 DEBUG: Filtered to {len(financial_transactions)} financial obligation transactions")

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

            # Detect salary - use ONLY bank transactions (salary doesn't come from credit cards!)
            salary_pattern = detect_salary_pattern(bank_only_transactions)
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
            # Normalize transaction types: handle both 'withdrawal'/'deposit' and 'debit'/'credit'
            debit_txns = [t for t in all_transactions if (t.type or '').lower() in ['debit', 'withdrawal']]
            logger.info(f"📊 DEBUG: Found {len(debit_txns)} debit transactions out of {len(all_transactions)} total")

            # Filter transactions using comprehensive multi-category detection (shared helper)
            logger.info(f"📊 DEBUG: About to filter {len(debit_txns)} debit transactions for financial obligations...")
            financial_transactions = _filter_financial_transactions(debit_txns, min_amount=500)
            logger.info(f"📊 DEBUG: Filtered to {len(financial_transactions)} financial obligation transactions")
            for txn in financial_transactions:
                merchant_lower = (txn.merchant_canonical or '').lower()
                description_lower = (txn.description_raw or '').lower()
                is_loan, is_insurance, is_investment, is_govt = _classify_financial_flags(merchant_lower, description_lower)
                category = 'Loan' if is_loan else 'Insurance' if is_insurance else 'Investment' if is_investment else 'Govt Scheme'
                logger.info(f"Identified {category}: {txn.merchant_canonical} - ₹{txn.amount}")

            logger.info(f"Total identified financial obligation transactions: {len(financial_transactions)}")

            # Step 2: Apply flexible criteria - group by merchant first, then detect similar amounts
            # This handles both exact-amount EMIs and reducing-balance EMIs (where amount decreases slightly)
            merchant_transactions = defaultdict(list)  # merchant -> [txns]

            for txn in financial_transactions:
                merchant = txn.merchant_canonical or txn.description_raw or "Unknown"
                merchant_transactions[merchant].append(txn)

            # Convert to EMI responses - detect patterns with similar amounts
            emi_responses = []
            for merchant, all_txns in merchant_transactions.items():
                # Group transactions by similar amounts (within 5% variance for reducing EMIs)
                # First try exact match, then fuzzy match
                amount_groups = defaultdict(list)  # rounded_amount -> [txns]

                for txn in all_txns:
                    # Round to nearest rupee for exact matching
                    exact_amount = round(txn.amount, 0)
                    amount_groups[exact_amount].append(txn)

                # Process exact matches first
                processed_txn_ids = set()
                for exact_amount, txns in amount_groups.items():
                    # Criteria: Exact same amount, 2+ payments
                    if len(txns) >= 2 and not any(t.transaction_id in processed_txn_ids for t in txns):
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

                            # Format dates correctly
                            first_date_str = ""
                            last_date_str = ""
                            if dates:
                                try:
                                    first_date_obj = min(dates)
                                    last_date_obj = max(dates)
                                    if isinstance(first_date_obj, datetime):
                                        first_date_str = first_date_obj.strftime('%Y-%m-%d')
                                    elif isinstance(first_date_obj, str):
                                        first_date_str = first_date_obj
                                    else:
                                        first_date_str = str(first_date_obj)
                                    
                                    if isinstance(last_date_obj, datetime):
                                        last_date_str = last_date_obj.strftime('%Y-%m-%d')
                                    elif isinstance(last_date_obj, str):
                                        last_date_str = last_date_obj
                                    else:
                                        last_date_str = str(last_date_obj)
                                except Exception as e:
                                    logger.warning(f"Error formatting dates: {e}")
                                    first_date_str = dates[0].strftime('%Y-%m-%d') if dates and isinstance(dates[0], datetime) else str(dates[0]) if dates else ""
                                    last_date_str = dates[-1].strftime('%Y-%m-%d') if dates and isinstance(dates[-1], datetime) else str(dates[-1]) if dates else ""
                            
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
                                first_detected_date=first_date_str,
                                last_detected_date=last_date_str
                            ))
                            
                            logger.info(f"✅ EMI Pattern detected: {merchant} - ₹{exact_amount:,.0f} ({len(txns)} transactions, {len(unique_months)} months)")

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

        # Get transactions from BOTH bank and credit card (for EMI detection)
        bank_transactions = session.query(BankTransaction).filter(
            BankTransaction.user_id == current_user.user_id
        ).all()

        cc_transactions = session.query(CreditCardTransaction).filter(
            CreditCardTransaction.user_id == current_user.user_id
        ).all()

        # Convert to Transaction-like objects for compatibility with existing detection logic
        all_transactions = []

        # Add bank transactions
        for bt in bank_transactions:
            txn_type = bt.type.value if hasattr(bt.type, 'value') else str(bt.type)
            if isinstance(txn_type, str):
                txn_type = txn_type.lower()
            else:
                txn_type = 'debit' if 'debit' in str(txn_type).lower() else 'credit'

            adapter = type('Transaction', (), {
                'transaction_id': bt.transaction_id,
                'user_id': bt.user_id,
                'account_id': bt.account_id,
                'date': bt.date,
                'amount': bt.amount,
                'type': txn_type,
                'description_raw': bt.description_raw,
                'merchant_canonical': bt.merchant_canonical,
                'category': bt.category.value if hasattr(bt.category, 'value') else str(bt.category),
                'balance': bt.balance
            })()
            all_transactions.append(adapter)

        # Add credit card transactions (for EMI detection)
        for ct in cc_transactions:
            txn_type = ct.type.value if hasattr(ct.type, 'value') else str(ct.type)
            if isinstance(txn_type, str):
                txn_type = txn_type.lower()
            else:
                txn_type = 'debit' if 'debit' in str(txn_type).lower() else 'credit'

            adapter = type('Transaction', (), {
                'transaction_id': ct.transaction_id,
                'user_id': ct.user_id,
                'account_id': ct.account_id,
                'date': ct.date,
                'amount': ct.amount,
                'type': txn_type,
                'description_raw': ct.description_raw,
                'merchant_canonical': ct.merchant_canonical,
                'category': ct.category.value if hasattr(ct.category, 'value') else str(ct.category),
                'balance': getattr(ct, 'balance', None)
            })()
            all_transactions.append(adapter)

        logger.info(f"📊 DEBUG: Retrieved {len(bank_transactions)} bank + {len(cc_transactions)} credit card transactions for /confirm endpoint")

        # Detect ALL recurring financial obligations using the SAME logic as detect endpoint
        logger.info("Re-detecting selected recurring financial obligations with strict filters...")

        # Apply same comprehensive multi-category filtering as detect endpoint (using shared helper)
        financial_transactions = _filter_financial_transactions(all_transactions, min_amount=100)

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
        # Get the config first
        config = session.query(SalarySweepConfig).filter(
            SalarySweepConfig.user_id == current_user.user_id,
            SalarySweepConfig.is_active == True
        ).first()

        if not config:
            # No config to delete
            session.commit()
            return

        # Get all EMI patterns for this config
        emi_patterns = session.query(DetectedEMIPattern).filter(
            DetectedEMIPattern.config_id == config.config_id
        ).all()

        # Delete liabilities that reference these patterns
        for pattern in emi_patterns:
            session.query(Liability).filter(
                Liability.recurring_pattern_id == pattern.pattern_id
            ).delete()

        # Delete the EMI patterns
        session.query(DetectedEMIPattern).filter(
            DetectedEMIPattern.config_id == config.config_id
        ).delete()

        # Delete the config
        session.delete(config)

        session.commit()
        logger.info(f"Deleted salary sweep configuration for user {current_user.user_id}")

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
                # Prefer direct asset link via recurring_pattern_id
                a = session.query(Asset).filter(
                    Asset.user_id == current_user.user_id,
                    Asset.recurring_pattern_id == pattern.pattern_id
                ).first()
                if a:
                    mapped_as = 'asset'
                    mapped_entity_id = a.asset_id
                else:
                    # Fallback: Asset notes contains pattern_id
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
