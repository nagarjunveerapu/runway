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


def rule_based_category(remark: str, merchant: Optional[str] = None) -> str:
    if not remark:
        return 'Other'
    s = remark.lower()
    
    # FIRST: Check for highway/toll keywords (before generic 'sip' matching)
    highway_keywords = ['fastag', 'sipg', 'toll', 'highway', 'nh', 'nhtr', 'mytoll']
    for keyword in highway_keywords:
        if keyword in s or (merchant and keyword in merchant.lower()):
            return 'Transport'
    
    # SECOND: Check for credit card payment patterns (before generic bank matching)
    # Detect bank names with credit card context
    credit_card_patterns = [
        'cc payment', 'card payment', 'credit card', 'card pay', 'card dues', 
        'card statement', 'card bill', 'cc bill', 'card repayment'
    ]
    
    # Indian banks that issue credit cards
    credit_card_banks = ['axis', 'hdfc', 'icici', 'sbi', 'kotak', 'indusind', 
                          'yes bank', 'rbl', 'standard chartered', 'hsbc']
    
    # Check if remark contains credit card keywords
    has_card_keyword = any(pattern in s for pattern in credit_card_patterns)
    has_card_bank = any(bank in s for bank in credit_card_banks)
    
    # If it's a debit transaction to a bank and has no investment/securities context,
    # likely a credit card payment
    if has_card_keyword or (has_card_bank and not any(x in s for x in ['securities', 'investment', 'sip', 'mutual fund', 'demat'])):
        return 'Credit Card Payment'
    
    # merchant first
    if merchant:
        m = merchant.lower()
        for k, cat in KEYWORD_CATEGORY_MAP.items():
            if k in m:
                return cat
    for k, cat in KEYWORD_CATEGORY_MAP.items():
        if k in s:
            return cat
    # Special handling for person-to-person transfers
    # Check if merchant looks like a person name (all caps, usually 3-5 words)
    if merchant and merchant.strip():
        merchant_words = merchant.strip().split()
        # If merchant has 2-4 words and all are uppercase/lowercase, likely a person name
        if 2 <= len(merchant_words) <= 4:
            # Check if all words are alphanumeric (not company names with "/", "PVT", "LTD", etc.)
            if not any(word in ['PVT', 'LTD', 'LIMITED', 'CORP', 'CO', 'INC'] for word in merchant_words):
                # Check if it contains common person name indicators or UPI patterns
                if any(indicator in s for indicator in ['payment fr', 'payment to', 'q', '@', 'upi/']):
                    return 'Person Transfer'
    # fallback heuristics
    if 'bill' in s or 'bill' in (merchant or '').lower():
        return 'Bills'
    if 'cash wdl' in s or 'withdraw' in s:
        return 'Cash Withdrawal'
    return 'Other'


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
