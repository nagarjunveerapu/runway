"""Rule-based classifier with an optional ML scaffold.

Primary behavior: rule-based keyword-to-category mapping.
Optional behavior: train a simple sklearn pipeline if labeled data is provided.
"""
from typing import Dict, Optional, List, Tuple
import re
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)


KEYWORD_CATEGORY_MAP: Dict[str, str] = {
    'pharmacy': 'Pharmacy',
    'apollo': 'Pharmacy',
    'netflix': 'Subscriptions',
    # Entertainment & Cinema
    'pvr': 'Entertainment',
    'inox': 'Entertainment',
    'carnival': 'Entertainment',
    'cinema': 'Entertainment',
    'movie': 'Entertainment',
    'crown': 'Entertainment',
    'multiplex': 'Entertainment',
    'fun': 'Entertainment',
    'asian': 'Entertainment',
    'spi': 'Entertainment',
    'cinepolis': 'Entertainment',
    'big cinema': 'Entertainment',  # Changed from 'big' to avoid matching Big Bazaar
    'big cinemas': 'Entertainment',
    'sungold': 'Entertainment',
    'regal': 'Entertainment',
    # Education
    'school': 'Education',
    'tutorial': 'Education',
    'tuition': 'Education',
    'academy': 'Education',
    'classes': 'Education',
    'coaching': 'Education',
    'institute': 'Education',
    'university': 'Education',
    'college': 'Education',
    'education': 'Education',
    'online course': 'Education',
    'course': 'Education',
    'training': 'Education',
    'vfs global': 'Education',
    'vfsglobal': 'Education',
    'emeritus': 'Education',
    'coursera': 'Education',
    'udemy': 'Education',
    'edx': 'Education',
    'skillshare': 'Education',
    'masterclass': 'Education',
    'simplilearn': 'Education',
    # Shopping & Retail Stores (India)
    # Apple Authorized Resellers
    'ample technologies': 'Shopping',
    'ample': 'Shopping',
    'aptronix': 'Shopping',
    'iplanet': 'Shopping',
    'imagine': 'Shopping',
    'invent': 'Shopping',
    'ivenus': 'Shopping',
    'maple': 'Shopping',
    'unicorn': 'Shopping',
    'apple': 'Shopping',
    # Major Retail Chains
    'reliance retail': 'Shopping',
    'reliance trends': 'Shopping',
    'reliance digital': 'Shopping',
    'reliance footprint': 'Shopping',
    'reliance': 'Shopping',  # Generic Reliance stores
    'big bazaar': 'Shopping',
    'bigbazaar': 'Shopping',
    'dmart': 'Shopping',
    'd mart': 'Shopping',
    'pantaloons': 'Shopping',
    'shoppers stop': 'Shopping',
    'lifestyle': 'Shopping',
    'central': 'Shopping',
    'lifestyle central': 'Shopping',
    'westside': 'Shopping',
    'max': 'Shopping',
    'more retail': 'Shopping',
    'more supermarket': 'Shopping',
    'spencer': 'Shopping',
    'spencer retail': 'Shopping',
    'hypercity': 'Shopping',
    'croma': 'Shopping',
    'vijay sales': 'Shopping',
    'ezone': 'Shopping',
    'poorvika': 'Shopping',
    'sathya': 'Shopping',
    'vasanth': 'Shopping',
    'jai ganesh': 'Shopping',
    'next': 'Shopping',
    'landmark': 'Shopping',
    'shoppers world': 'Shopping',
    'star bazaar': 'Shopping',
    'easyday': 'Shopping',
    'star market': 'Shopping',
    # E-commerce
    'amazon': 'Shopping',
    'amazon pay': 'Shopping',
    'flipkart': 'Shopping',
    'myntra': 'Shopping',
    'snapdeal': 'Shopping',
    'meesho': 'Shopping',
    'paytm mall': 'Shopping',
    'jiomart': 'Shopping',
    # General Retail Patterns
    'retail': 'Shopping',
    'retail ltd': 'Shopping',
    'retail pvt': 'Shopping',
    'supermarket': 'Shopping',
    'hypermarket': 'Shopping',
    'megastore': 'Shopping',
    'department store': 'Shopping',
    'mall': 'Shopping',
    'shopping center': 'Shopping',
    'swiggy': 'Food',
    'zomato': 'Food',
    'zepto': 'Food',
    'burger': 'Food',
    'coffee': 'Food',
    'chai': 'Food',
    'restaurant': 'Food',
    # Fuel companies
    'oil': 'Fuel',
    'petrol': 'Fuel',
    'diesel': 'Fuel',
    'gas': 'Fuel',
    'gasoline': 'Fuel',
    'hp pay': 'Fuel',
    'hp petrol': 'Fuel',
    'hindustan petroleum': 'Fuel',
    'rpc petrol': 'Fuel',
    'indian oil': 'Fuel',
    'bpcl': 'Fuel',
    'bharat petroleum': 'Fuel',
    'reliance petroleum': 'Fuel',
    'shell': 'Fuel',
    'essar oil': 'Fuel',
    'total oil': 'Fuel',
    'chevron': 'Fuel',
    'castrol': 'Fuel',
    'gulf oil': 'Fuel',
    'ioc': 'Fuel',
    'hpcl': 'Fuel',
    # Investment & Trading Platforms (India)
    'zerodha': 'Mutual Funds & Investments',
    'indmoney': 'Mutual Funds & Investments',
    'groww': 'Mutual Funds & Investments',
    'finzoom': 'Mutual Funds & Investments',
    'upstox': 'Mutual Funds & Investments',
    '5paisa': 'Mutual Funds & Investments',
    'angel one': 'Mutual Funds & Investments',
    'angelone': 'Mutual Funds & Investments',
    'kotak securities': 'Mutual Funds & Investments',
    'kotak sec': 'Mutual Funds & Investments',
    'hdfc securities': 'Mutual Funds & Investments',
    'icici securities': 'Mutual Funds & Investments',
    'sbi securities': 'Mutual Funds & Investments',
    'axis securities': 'Mutual Funds & Investments',
    'morningstar': 'Mutual Funds & Investments',
    'fundsindia': 'Mutual Funds & Investments',
    'kuvera': 'Mutual Funds & Investments',
    'paytm money': 'Mutual Funds & Investments',
    'paytm money': 'Mutual Funds & Investments',
    'et money': 'Mutual Funds & Investments',
    'scripbox': 'Mutual Funds & Investments',
    'smallcase': 'Mutual Funds & Investments',
    'motilal oswal': 'Mutual Funds & Investments',
    'geojit': 'Mutual Funds & Investments',
    'iifl': 'Mutual Funds & Investments',
    'sharekhan': 'Mutual Funds & Investments',
    'india bulls': 'Mutual Funds & Investments',
    'axis direct': 'Mutual Funds & Investments',
    'motilal': 'Mutual Funds & Investments',
    'oswal': 'Mutual Funds & Investments',
    'investment': 'Mutual Funds & Investments',
    'trading': 'Mutual Funds & Investments',
    'stock': 'Mutual Funds & Investments',
    'equity': 'Mutual Funds & Investments',
    'mutual fund': 'Mutual Funds & Investments',
    'mf sip': 'Mutual Funds & Investments',
    'sip': 'Mutual Funds & Investments',
    'investment platform': 'Mutual Funds & Investments',
    'demat': 'Mutual Funds & Investments',
    'broker': 'Mutual Funds & Investments',
    'indian clearing corp': 'Mutual Funds & Investments',
    'clearing corporation': 'Mutual Funds & Investments',
    'icc': 'Mutual Funds & Investments',
    'bse': 'Mutual Funds & Investments',
    'nse': 'Mutual Funds & Investments',
    'cred': 'Bills',
    'sbi life': 'Insurance',
    'life insurance': 'Insurance',
    'insurance': 'Insurance',
    # Highway Toll (India)
    'fastag': 'Transport',
    'toll': 'Transport',
    'highway': 'Transport',
    'nh': 'Transport',
    'nehru': 'Transport',
    'sipg': 'Transport',  # Highway toll gateway
    'credence': 'Transport',
    'nhtr': 'Transport',
    'mytoll': 'Transport',
    'paytm fastag': 'Transport',
    'hdfc fastag': 'Transport',
    'icici fastag': 'Transport',
    'emi': 'EMI/Loan',
    'loan': 'EMI/Loan',
    'canfin': 'EMI/Loan',
    'rent': 'Rent',
    'cash wdl': 'Cash Withdrawal',
    'withdraw': 'Cash Withdrawal',
    'salary': 'Salary',
    'sweep': 'Transfer',
    # Credit Card Payments
    'credit card': 'Credit Card Payment',
    'card payment': 'Credit Card Payment',
    'card pay': 'Credit Card Payment',
    'cc payment': 'Credit Card Payment',
    'card dues': 'Credit Card Payment',
    'card statement': 'Credit Card Payment',
    'infinity payment': 'Credit Card Payment',
    'bbps payment': 'Credit Card Payment',
    # Real Estate
    'realtors': 'Real Estate',
    'realtor': 'Real Estate',
    'real estate': 'Real Estate',
    'property': 'Real Estate',
    'construction': 'Real Estate',
    'seasons katha': 'Real Estate',
    # Person transfers (keep anonymous)
    'upi/payment': 'Person Transfer',
    'payment from': 'Person Transfer',
    'payment to': 'Person Transfer',
}


def rule_based_category(remark: str, merchant: Optional[str] = None) -> Tuple[str, Optional[str]]:
    """
    Classify transaction with primary category and optional sub-type.
    
    Returns:
        Tuple of (primary_category, transaction_sub_type)
        - primary_category: Main category (Education, Food, etc.)
        - transaction_sub_type: Additional classification (EMI/Loan, Credit Card Payment, etc.)
    """
    if not remark:
        return ('Other', None)
    s = remark.lower()
    
    # Track EMI and Credit Card Payment status
    has_emi = False
    is_credit_card_payment = False
    
    # Check for EMI/Loan patterns
    emi_keywords = ['emi', 'loan', 'installment', 'amortization', 'canfin', 'principal amount', 'interest amount']
    has_emi = any(keyword in s for keyword in emi_keywords)
    
    # Check for credit card payment patterns
    credit_card_patterns = [
        'cc payment', 'card payment', 'credit card', 'card pay', 'card dues', 
        'card statement', 'card bill', 'cc bill', 'card repayment', 'infinity payment', 'bbps payment'
    ]
    credit_card_banks = ['axis bank', 'hdfc bank', 'icici bank', 'sbi bank', 'kotak bank', 'indusind bank', 
                          'yes bank', 'rbl bank', 'standard chartered', 'hsbc']
    
    has_card_keyword = any(pattern in s for pattern in credit_card_patterns)
    has_card_bank = any(bank in s for bank in credit_card_banks)
    exclude_keywords = ['securities', 'investment', 'sip', 'mutual fund', 'demat', 'school', 'college', 'university',
                       'tutorial', 'tuition', 'academy', 'coaching', 'institute', 'hospital', 'hotel', 'restaurant', 
                       'retail', 'store', 'supermarket', 'mall']
    has_exclude = any(exclude in s for exclude in exclude_keywords)
    
    is_credit_card_payment = has_card_keyword or (has_card_bank and not has_exclude)
    
    # Determine primary category (excluding EMI and card keywords)
    category = None
    
    # FIRST: Check for highway/toll keywords (before generic 'sip' matching)
    highway_keywords = ['fastag', 'sipg', 'toll', 'highway', 'nh', 'nhtr', 'mytoll']
    for keyword in highway_keywords:
        if keyword in s or (merchant and keyword in merchant.lower()):
            category = 'Transport'
            break
    
    # SECOND: Check for retail/shopping patterns (before generic matching)
    if not category:
        # Check merchant name for retail patterns
        if merchant:
            m_lower = merchant.lower()
            retail_patterns = [
                'retail', 'store', 'supermarket', 'hypermarket', 'mall', 
                'shopping', 'department', 'megastore', 'showroom'
            ]
            # Only match if it's clearly a retail store, not excluded contexts
            if any(pattern in m_lower for pattern in retail_patterns):
                # Exclude if it's clearly NOT retail (like "retail securities")
                if 'securities' not in m_lower and 'investment' not in m_lower:
                    category = 'Shopping'
        
        # Check description for retail keywords
        if not category:
            retail_keywords = ['retail ltd', 'retail pvt', 'supermarket', 'hypermarket', 
                             'department store', 'shopping center', 'shopping mall']
            if any(keyword in s for keyword in retail_keywords):
                category = 'Shopping'
    
    # merchant first
    if not category and merchant:
        m = merchant.lower()
        for k, cat in KEYWORD_CATEGORY_MAP.items():
            if k in m:
                category = cat
                break
    if not category:
        for k, cat in KEYWORD_CATEGORY_MAP.items():
            if k in s:
                category = cat
                break
    
    # Special handling for person-to-person transfers
    if not category and merchant and merchant.strip():
        merchant_words = merchant.strip().split()
        if 2 <= len(merchant_words) <= 4:
            if not any(word in ['PVT', 'LTD', 'LIMITED', 'CORP', 'CO', 'INC'] for word in merchant_words):
                if any(indicator in s for indicator in ['payment fr', 'payment to', 'q', '@', 'upi/']):
                    category = 'Person Transfer'
    
    # fallback heuristics
    if not category:
        if 'bill' in s or 'bill' in (merchant or '').lower():
            category = 'Bills'
        elif 'cash wdl' in s or 'withdraw' in s:
            category = 'Cash Withdrawal'
        else:
            category = 'Other'
    
    # Determine transaction sub-type
    sub_type = None
    if has_emi:
        sub_type = 'EMI/Loan'
    elif is_credit_card_payment:
        sub_type = 'Credit Card Payment'
    
    return (category, sub_type)


class MLClassifier:
    """Simple sklearn pipeline scaffold to train if labeled data is provided.

    To use: provide a CSV with columns ['remark','category'] and call `train`.
    This is not used by default in POC.
    """
    def __init__(self):
        self.pipeline: Optional[Pipeline] = None

    def train(self, texts: List[str], labels: List[str]):
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer()),
            ('clf', LogisticRegression(max_iter=1000))
        ])
        self.pipeline.fit(texts, labels)

    def predict(self, texts: List[str]) -> List[str]:
        if not self.pipeline:
            raise RuntimeError('Model not trained')
        return self.pipeline.predict(texts)
