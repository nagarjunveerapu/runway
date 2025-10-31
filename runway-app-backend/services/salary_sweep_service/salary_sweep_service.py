"""
Salary Sweep Service - Service Layer for Salary Sweep Analysis

Provides business logic for:
- Salary pattern detection
- EMI/recurring payment pattern detection
- Optimization scenario calculations
- Configuration management

This service layer separates business logic from route handlers and database operations.
"""

import logging
import uuid
import re
from typing import List, Optional, Dict, Tuple
from datetime import datetime
from collections import defaultdict

from storage.database import DatabaseManager
from storage.models import Transaction, SalarySweepConfig, DetectedEMIPattern, Asset, Liability
from services.investment_detection import InvestmentDetector

logger = logging.getLogger(__name__)

# Constants
SALARY_ACCOUNT_RATE = 2.5  # Annual interest rate (%)
SAVINGS_ACCOUNT_RATE = 7.0  # Annual interest rate (%)


class SalarySweepService:
    """
    Service layer for salary sweep analysis
    
    Coordinates between:
    - Transaction filtering and pattern detection
    - Database operations (config retrieval)
    - Business logic (optimization calculations)
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize salary sweep service
        
        Args:
            db_manager: DatabaseManager instance for database operations
        """
        self.db_manager = db_manager
    
    def _keyword_sets(self) -> Dict[str, List[str]]:
        """Central source of keyword lists for categorization."""
        return {
            'exclude_merchant': ['sweep', 'transfer', 'ndr fruits'],
            'exclude_desc': ['upi/', 'paytm'],
            # Domain-specific exclusions that frequently cause false positives
            'exclude_investment_desc': ['fastag', 'fast tag', 'toll', 'parking', 'metro card', 'recharge fastag', 'npci fastag', 'hdfc fastag', 'icici fastag', 'sbi fastag'],
            'loan_merchants': [
                'canfin', 'bajaj finserv', 'bajaj finance', 'tata capital', 'fullerton',
                'iifl', 'mahindra finance', 'cholamandalam', 'l&t finance', 'lic housing',
                'dhfl', 'indiabulls', 'housing finance'
            ],
            'loan_desc': [
                'emi', 'personal loan', 'home loan', 'car loan', 'auto loan',
                'housing loan', 'loan emi', 'canfinhomesltd', 'housingloan'
            ],
            'insurance': [
                'sbi life', 'lic', 'hdfc life', 'icici prudential', 'max life',
                'bajaj allianz', 'tata aia', 'birla sun life', 'insurance',
                'kotak life', 'pnb metlife', 'star health', 'care health',
                'religare health', 'aditya birla health', 'niva bupa'
            ],
            'investment': [
                'mutual fund', 'sip', 'systematic', 'zerodha', 'groww', 'paytm money',
                'et money', 'kuvera', 'coin dcb', 'hdfc mf', 'icici prudential mf',
                'sbi mf', 'axis mf', 'kotak mf', 'nippon india', 'franklin templeton'
            ],
            'govt': [
                'apy', 'atal pension', 'nps', 'national pension', 'ppf', 'public provident',
                'epf', 'employee provident', 'esi', 'employee state insurance',
                'sukanya samriddhi', 'pmjjby', 'pmsby', 'pm jeevan', 'pm suraksha'
            ],
        }
    
    def categorize_recurring_payment(self, merchant: str, description: str) -> Tuple[str, str]:
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
        if InvestmentDetector.is_investment_text(f"{merchant_lower} {description_lower}"):
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
    
    def _classify_financial_flags(self, merchant_lower: str, description_lower: str) -> Tuple[bool, bool, bool, bool]:
        """Return tuple flags for (is_loan, is_insurance, is_investment, is_govt)."""
        ks = self._keyword_sets()
        is_loan = (
            any(l in merchant_lower for l in ks['loan_merchants']) or
            any(k in description_lower for k in ks['loan_desc'])
        )
        is_insurance = any(k in merchant_lower or k in description_lower for k in ks['insurance'])
        # Investment with guardrails: avoid common FASTag/toll false positives that include 'SIP' substrings
        investment_candidate = any(k in merchant_lower or k in description_lower for k in ks['investment'])
        has_investment_exclusions = any(k in merchant_lower or k in description_lower for k in ks['exclude_investment_desc'])
        is_investment = investment_candidate and not has_investment_exclusions
        is_govt = any(k in merchant_lower or k in description_lower for k in ks['govt'])
        return is_loan, is_insurance, is_investment, is_govt
    
    def _should_include_txn(self, txn: Transaction, min_amount: float = 500) -> bool:
        """Unified filter used across detection flows for selecting candidate debit transactions."""
        # Normalize transaction type: handle both 'withdrawal'/'deposit' and 'debit'/'credit'
        txn_type = txn.type.lower() if txn.type else ''
        is_debit = txn_type in ['debit', 'withdrawal']
        
        if not is_debit or txn.amount < min_amount:
            return False
        merchant_lower = (txn.merchant_canonical or '').lower()
        description_lower = (txn.description_raw or '').lower()
        ks = self._keyword_sets()
        # Hard exclude FASTag/toll-like items from recurring obligation detection
        if any(ex in merchant_lower or ex in description_lower for ex in ks['exclude_investment_desc']):
            return False
        if any(ex in description_lower for ex in ks['exclude_desc']):
            return False
        if any(ex in merchant_lower for ex in ks['exclude_merchant']):
            return False
        is_loan, is_insurance, is_investment, is_govt = self._classify_financial_flags(merchant_lower, description_lower)
        return is_loan or is_insurance or is_investment or is_govt
    
    def _filter_financial_transactions(self, transactions: List[Transaction], min_amount: float = 500) -> List[Transaction]:
        """Apply shared filtering to get candidate financial obligation transactions."""
        results: List[Transaction] = []
        for txn in transactions:
            if self._should_include_txn(txn, min_amount=min_amount):
                results.append(txn)
        return results
    
    def _extract_merchant_from_description(self, description: str, merchant: str) -> str:
        """Extract merchant/employer name from description if merchant is generic.
        
        Uses intelligent pattern matching to extract company names from transaction descriptions.
        Works with NEFT/RTGS formats, UPI formats, and various other transaction formats.
        """
        if merchant and merchant.lower() not in ['other', 'unknown', '']:
            return merchant
        
        if not description:
            return "Salary"
        
        desc = description.strip()
        desc_lower = desc.lower()
        
        # Employer patterns (for normalization)
        employer_patterns = [
            'infy', 'infosys', 'tcs', 'tata consultancy', 'wipro', 'hcl', 'cognizant', 'cts',
            'accenture', 'acn', 'techm', 'tech mahindra', 'capgemini', 'cap', 'ibm', 'syntel',
            'l&t infotech', 'ltim', 'lt tree', 'lt thermal', 'mindtree',
            'paytm', 'flipkart', 'amazon', 'netflix', 'razorpay',
            'capital one', 'capital1', 'capitalone'
        ]
        
        # Pattern 1: NEFT/RTGS format
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
                company_name = re.sub(r'\s+[-]+\s*$', '', company_name)
                company_name = re.sub(r'\s+', ' ', company_name)
                
                company_match = re.search(r'^([A-Z][A-Z\s&]+?)\s+(?:PVT|LTD|INC|LLC|CORP|LLP)', company_name, re.IGNORECASE)
                if company_match:
                    company_name = company_match.group(1).strip()
                
                words = company_name.split()
                capitalized_words = []
                for word in words:
                    if len(word) == 1 and word.upper() in ['I', 'A']:
                        continue
                    if word.isupper():
                        capitalized_words.append(word.capitalize())
                    else:
                        capitalized_words.append(word.title())
                
                if capitalized_words:
                    result = ' '.join(capitalized_words)
                    result = re.sub(r'\s+(Services|Technologies|Solutions|Systems)\s*$', '', result, flags=re.IGNORECASE)
                    if result and len(result) > 2:
                        return result
        
        # Pattern 2: Look for employer patterns
        for employer in employer_patterns:
            if employer in desc_lower:
                employer_pattern = r'\b(' + re.escape(employer) + r'[^\s-]*)'
                match = re.search(employer_pattern, desc, re.IGNORECASE)
                if match:
                    found_text = match.group(1)
                    words = found_text.split()
                    if len(words) >= 2:
                        return ' '.join(word.capitalize() for word in words[:2])
                    else:
                        return found_text.capitalize()
        
        # Pattern 3: Look for company-like patterns in uppercase
        company_pattern = r'\b([A-Z]{2,}(?:\s+[A-Z]{2,}){1,3})(?:\s+(?:PVT|LTD|INC|LLC|CORP|LLP|SERVICES))?'
        match = re.search(company_pattern, desc)
        if match:
            company_name = match.group(1).strip()
            skip_patterns = ['NEFT', 'RTGS', 'UPI', 'IMPS', 'CITI', 'HDFC', 'ICICI', 'SBI', 'AXIS']
            if not any(skip in company_name.upper() for skip in skip_patterns):
                words = company_name.split()
                if len(words) >= 2 and len(words) <= 4:
                    capitalized = ' '.join(word.capitalize() for word in words)
                    if len(capitalized) >= 4:
                        return capitalized
        
        # Pattern 4: Extract from INF/INFT format
        inf_match = re.search(r'INF[/-]\s*\w+\s*[/-]\s*([A-Z][A-Z\s&]+)', desc, re.IGNORECASE)
        if inf_match:
            company_name = inf_match.group(1).strip()
            words = company_name.split()
            if len(words) >= 1 and len(words) <= 3:
                return ' '.join(word.capitalize() for word in words[:2])
        
        # Fallback
        return merchant or "Salary"
    
    def detect_salary_pattern(self, transactions: List[Transaction]) -> Optional[Dict]:
        """Detect recurring salary credits by amount similarity and salary keywords"""
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
        ultra_high_keywords = [
            'salary', 'salary credit', 'salary transfer', 'sal', 'salry', 'salar',
            'payroll', 'payroll salary', 'hr payroll'
        ]
        
        special_payments = [
            'advance salary', 'adv salary', 'bonus', 'variable pay', 'variablepay',
            'incentive', 'incent', 'gratuity', 'grat', 'stipend', '13th month', 'thirteenth'
        ]
        
        employer_patterns = [
            'infy', 'infosys', 'tcs', 'tata consultancy', 'wipro', 'hcl', 'cognizant', 'cts',
            'accenture', 'acn', 'techm', 'tech mahindra', 'capgemini', 'cap', 'ibm', 'syntel',
            'l&t infotech', 'ltim', 'lt tree', 'lt thermal', 'mindtree',
            'paytm', 'flipkart', 'amazon', 'netflix', 'razorpay',
            'capital one', 'capital1', 'capitalone'
        ]
        
        exclude_keywords = [
            'refund', 'reversal', 'cancellation', 'cancel', 'dividend', 'divid',
            'interest', 'int.pd', 'int paid', 'loan', 'emi', 'installment',
            'rent', 'insurance', 'transfer out', 'cashback', 'cash back', 'fee', 'charges',
            '/lpbn'
        ]
        
        salary_keywords = ultra_high_keywords + special_payments
        
        # Look for single transactions with salary keywords and substantial amounts
        single_salary_candidates = []
        for idx, txn in enumerate(credit_txns):
            logger.info(f"\n{'='*80}")
            logger.info(f"📊 Transaction #{idx+1}/{len(credit_txns)}")
            logger.info(f"   Date: {txn.date}, Amount: ₹{txn.amount:,.2f}")
            logger.info(f"   Merchant: {txn.merchant_canonical}")
            logger.info(f"   Description: {txn.description_raw}")
            
            if txn.amount >= 50000:
                desc = (txn.description_raw or '').lower()
                merch = (txn.merchant_canonical or '').lower()
                combined = f"{desc} {merch}"
                
                logger.info(f"   ✅ Substantial amount (≥₹50K) - Checking salary patterns...")
                logger.info(f"   Combined text: '{combined[:100]}'")
                
                # Check negative indicators
                matched_excludes = [exclude for exclude in exclude_keywords if exclude in combined]
                if matched_excludes:
                    logger.info(f"   ❌ EXCLUDED - Found negative indicators: {matched_excludes}")
                    continue
                
                # Check positive salary indicators
                has_salary_keyword = any(keyword in combined for keyword in salary_keywords)
                matched_salary_keywords = [kw for kw in salary_keywords if kw in combined]
                
                has_high_confidence_pattern = (
                    ('neft' in combined or 'rtgs' in combined) and 
                    ('salary' in combined or 'payroll' in combined or 'sal ' in combined)
                )
                
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
        
        # Group by similar amounts
        amount_groups = []
        
        for txn in credit_txns:
            added = False
            for group in amount_groups:
                avg_in_group = sum(t['amount'] for t in group) / len(group)
                if abs(txn.amount - avg_in_group) / avg_in_group <= 0.2:
                    group.append({'amount': txn.amount, 'txn': txn})
                    added = True
                    break
            
            if not added:
                amount_groups.append([{'amount': txn.amount, 'txn': txn}])
        
        recurring_patterns = [g for g in amount_groups if len(g) >= 2]
        
        # Return single large transaction if exists and no recurring patterns
        if single_salary_candidates and not recurring_patterns:
            best_single = max(single_salary_candidates, key=lambda t: t.amount)
            detected_source = self._extract_merchant_from_description(
                best_single.description_raw or '',
                best_single.merchant_canonical or ''
            )
            
            logger.info(f"\n{'='*80}")
            logger.info(f"✅ SALARY DETECTED: Single Transaction")
            logger.info(f"   Amount: ₹{best_single.amount:,.2f}")
            logger.info(f"   Source: {detected_source}")
            
            return {
                'source': detected_source,
                'amount': best_single.amount,
                'count': 1,
                'txns': [best_single]
            }
        
        if not recurring_patterns:
            logger.info(f"\n{'='*80}")
            logger.info(f"❌ NO SALARY DETECTED")
            logger.info(f"   Found {len(single_salary_candidates)} salary candidates but no recurring patterns")
            return None
        
        # Find largest recurring pattern
        best_pattern = max(recurring_patterns, key=lambda g: sum(t['amount'] for t in g) / len(g))
        
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
        
        is_large_recurring_credit = (
            len(best_pattern) >= 2 and
            pattern_avg >= 30000 and
            has_employer_in_pattern
        )
        
        has_neft_pattern = False
        for t in best_pattern:
            txn = t['txn']
            desc = (txn.description_raw or '').lower()
            if 'neft' in desc or 'rtgs' in desc:
                has_neft_pattern = True
                break
        
        if single_salary_candidates and not has_salary_in_pattern and not is_large_recurring_credit:
            largest_single = max(single_salary_candidates, key=lambda t: t.amount)
            if largest_single.amount > pattern_avg * 1.3:
                detected_source = self._extract_merchant_from_description(
                    largest_single.description_raw or '',
                    largest_single.merchant_canonical or ''
                )
                
                logger.info(f"\n{'='*80}")
                logger.info(f"✅ SALARY DETECTED: Single Large Transaction (Higher than recurring)")
                logger.info(f"   Amount: ₹{largest_single.amount:,.2f}")
                logger.info(f"   Source: {detected_source}")
                
                return {
                    'source': detected_source,
                    'amount': largest_single.amount,
                    'count': 1,
                    'txns': [largest_single]
                }

        amounts = [t['amount'] for t in best_pattern]
        txns = [t['txn'] for t in best_pattern]
        avg_amount = sum(amounts) / len(amounts)
        
        detection_reason = []
        if has_salary_in_pattern:
            detection_reason.append("Contains salary keywords")
        if is_large_recurring_credit:
            detection_reason.append(f"Large recurring credit (≥₹30K, {len(best_pattern)}x) from employer")
        if has_neft_pattern and has_employer_in_pattern:
            detection_reason.append("NEFT/RTGS from employer")
        if not detection_reason:
            detection_reason.append("Largest recurring pattern")
        
        merchants = [txn.merchant_canonical for txn in txns if txn.merchant_canonical]
        most_common_merchant = max(set(merchants), key=merchants.count) if merchants else "Recurring Credit"
        
        detected_source = most_common_merchant
        for txn in txns:
            if txn.description_raw:
                extracted = self._extract_merchant_from_description(
                    txn.description_raw,
                    txn.merchant_canonical or ''
                )
                if extracted.lower() not in ['other', 'unknown', 'salary', 'recurring credit']:
                    detected_source = extracted
                    break
        
        logger.info(f"\n{'='*80}")
        logger.info(f"✅ SALARY DETECTED: Recurring Pattern")
        logger.info(f"   Reason: {'; '.join(detection_reason)}")
        logger.info(f"   Source: {detected_source}")
        logger.info(f"   Average: ₹{avg_amount:,.2f}, Occurrences: {len(amounts)}")
        
        return {
            'source': detected_source,
            'amount': avg_amount,
            'count': len(amounts),
            'txns': txns
        }
    
    def calculate_optimization(
        self,
        salary_amount: float,
        confirmed_emis: List[DetectedEMIPattern],
        salary_rate: float = SALARY_ACCOUNT_RATE,
        savings_rate: float = SAVINGS_ACCOUNT_RATE
    ) -> Dict:
        """Calculate all three optimization scenarios"""
        total_emi = sum(emi.emi_amount for emi in confirmed_emis)

        # Scenario 1: Current (no sweep)
        current_scenario = {
            'name': 'Current Setup (No Sweep)',
            'description': 'Keep all salary in low-interest salary account',
            'emi_dates': None,
            'salary_account_balance': salary_amount,
            'savings_account_balance': 0.0,
            'avg_days_in_savings': 0.0,
            'monthly_interest_salary': (salary_amount * salary_rate / 100 / 12),
            'monthly_interest_savings': 0.0,
            'total_monthly_interest': (salary_amount * salary_rate / 100 / 12),
            'total_annual_interest': (salary_amount * salary_rate / 100)
        }

        # Scenario 2: Uniform sweep
        surplus_after_emis = salary_amount - total_emi
        avg_days_uniform = 15

        monthly_interest_salary_uniform = total_emi * salary_rate / 100 / 12
        monthly_interest_savings_uniform = surplus_after_emis * savings_rate / 100 / 12 * (avg_days_uniform / 30)

        uniform_scenario = {
            'name': 'Uniform Sweep (All EMIs Day 1)',
            'description': 'Pay all EMIs on day 1, sweep surplus to savings',
            'emi_dates': 'All on 1st',
            'salary_account_balance': total_emi,
            'savings_account_balance': surplus_after_emis,
            'avg_days_in_savings': avg_days_uniform,
            'monthly_interest_salary': monthly_interest_salary_uniform,
            'monthly_interest_savings': monthly_interest_savings_uniform,
            'total_monthly_interest': monthly_interest_salary_uniform + monthly_interest_savings_uniform,
            'total_annual_interest': (monthly_interest_salary_uniform + monthly_interest_savings_uniform) * 12
        }

        # Scenario 3: Optimized (stagger EMIs)
        num_emis = len(confirmed_emis)
        avg_days_optimized = 20 if num_emis > 0 else 28

        monthly_interest_salary_opt = total_emi * salary_rate / 100 / 12
        monthly_interest_savings_opt = surplus_after_emis * savings_rate / 100 / 12 * (avg_days_optimized / 30)

        optimized_scenario = {
            'name': 'Optimized Sweep (Staggered EMIs)',
            'description': 'Stagger EMI dates to maximize time in high-interest savings',
            'emi_dates': 'Spread: 5th, 10th, 15th, 20th...',
            'salary_account_balance': total_emi,
            'savings_account_balance': surplus_after_emis,
            'avg_days_in_savings': avg_days_optimized,
            'monthly_interest_salary': monthly_interest_salary_opt,
            'monthly_interest_savings': monthly_interest_savings_opt,
            'total_monthly_interest': monthly_interest_salary_opt + monthly_interest_savings_opt,
            'total_annual_interest': (monthly_interest_salary_opt + monthly_interest_savings_opt) * 12
        }

        # Calculate gains
        interest_gain = optimized_scenario['total_annual_interest'] - current_scenario['total_annual_interest']

        # Recommendation
        if interest_gain > 5000:
            recommendation = f"Highly Recommended: Save ₹{interest_gain:,.0f}/year with optimized sweep!"
        elif interest_gain > 2000:
            recommendation = f"Recommended: Save ₹{interest_gain:,.0f}/year with salary sweep"
        else:
            recommendation = f"Marginal benefit: ₹{interest_gain:,.0f}/year gain"

        return {
            'current_scenario': current_scenario,
            'uniform_sweep': uniform_scenario,
            'optimized_sweep': optimized_scenario,
            'recommendation': recommendation,
            'interest_gain_vs_current': interest_gain
        }
    
    def get_config(self, user_id: str) -> Optional[SalarySweepConfig]:
        """Get user's saved configuration"""
        session = self.db_manager.get_session()
        try:
            config = session.query(SalarySweepConfig).filter(
                SalarySweepConfig.user_id == user_id,
                SalarySweepConfig.is_active == True
            ).first()
            return config
        finally:
            session.close()
    
    def get_confirmed_emis(self, config_id: str) -> List[DetectedEMIPattern]:
        """Get confirmed EMI patterns for a configuration"""
        session = self.db_manager.get_session()
        try:
            patterns = session.query(DetectedEMIPattern).filter(
                DetectedEMIPattern.config_id == config_id,
                DetectedEMIPattern.is_confirmed == True
            ).all()
            return patterns
        finally:
            session.close()

