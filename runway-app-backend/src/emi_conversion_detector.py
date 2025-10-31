"""
EMI Conversion Detector

Detects when a credit card purchase is converted to EMI:
1. Initial purchase (debit): e.g., ₹40,050
2. Refund/credit (credit): same amount on same merchant
3. EMI begins: amortization starts with EMI installments

The initial purchase should be excluded from "Spend by Category" analysis
since it was converted to EMI.
"""

import re
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def detect_emi_conversions(transactions: List[Dict]) -> List[Dict]:
    """
    Detect and mark EMI conversion patterns in transactions
    
    Args:
        transactions: List of transaction dictionaries with fields:
            - date, amount, type (debit/credit), merchant_raw, description_raw
    
    Returns:
        List of transactions with EMI conversion patterns detected
    """
    # Sort transactions by date
    sorted_txns = sorted(transactions, key=lambda t: t.get('date', ''))
    
    # Find EMI conversion patterns
    conversion_pairs = []
    emi_txns = []
    
    # First pass: identify EMI transactions and potential conversion patterns
    for i, txn in enumerate(sorted_txns):
        description = txn.get('description_raw', '') or txn.get('description', '')
        merchant = txn.get('merchant_raw', '') or txn.get('merchant_canonical', '')
        amount = abs(txn.get('amount', 0))
        txn_type = txn.get('type', '').lower()
        
        # Check if transaction is EMI-related
        desc_lower = description.lower()
        is_emi = any(kw in desc_lower for kw in ['emi', 'amortization', 'principal amount', 'interest amount', 'installment'])
        
        if is_emi:
            emi_txns.append({
                'index': i,
                'txn': txn,
                'merchant': merchant,
                'amount': amount,
                'date': txn.get('date', '')
            })
    
    # Second pass: for each EMI transaction, look for matching purchase + refund
    for emi_info in emi_txns:
        emi_date = emi_info['date']
        emi_merchant = emi_info['merchant']
        emi_amount = emi_info['amount']
        emi_idx = emi_info['index']
        
        # Look for purchase (debit) and refund (credit) pattern within 30 days before EMI
        # Try to match by merchant and amount (with some tolerance)
        conversion_candidates = []
        
        for i, txn in enumerate(sorted_txns):
            if i >= emi_idx:
                break  # Only check transactions before EMI
            
            description = txn.get('description_raw', '') or txn.get('description', '')
            merchant = txn.get('merchant_raw', '') or txn.get('merchant_canonical', '')
            amount = abs(txn.get('amount', 0))
            txn_type = txn.get('type', '').lower()
            txn_date = txn.get('date', '')
            
            # Skip if not the same merchant (with fuzzy matching)
            if not _merchants_match(merchant, emi_merchant):
                continue
            
            # Check if this is a substantial purchase (debit) that could have been converted
            if txn_type == 'debit' and amount >= 5000:  # Only substantial purchases
                # Look for matching refund/credit within 7 days
                for j in range(i + 1, min(i + 20, len(sorted_txns))):
                    if j >= emi_idx:
                        break
                    
                    ref_txn = sorted_txns[j]
                    ref_description = ref_txn.get('description_raw', '') or ref_txn.get('description', '')
                    ref_merchant = ref_txn.get('merchant_raw', '') or ref_txn.get('merchant_canonical', '')
                    ref_amount = abs(ref_txn.get('amount', 0))
                    ref_type = ref_txn.get('type', '').lower()
                    ref_date = ref_txn.get('date', '')
                    
                    # Check if this is a matching credit transaction
                    if (ref_type == 'credit' and 
                        _amounts_match(amount, ref_amount) and
                        _merchants_match(merchant, ref_merchant)):
                        
                        # Check if dates are close (within 7 days)
                        if _dates_within_days(txn_date, ref_date, 7):
                            conversion_candidates.append({
                                'purchase': txn,
                                'refund': ref_txn,
                                'emi': emi_info['txn'],
                                'purchase_idx': i,
                                'refund_idx': j,
                                'emi_idx': emi_idx
                            })
                            break
        
        # Add the best conversion candidate
        if conversion_candidates:
            # Take the most recent conversion (closest to EMI start)
            best_conversion = min(conversion_candidates, key=lambda c: abs(_days_between(c['refund'].get('date', ''), emi_date)))
            conversion_pairs.append(best_conversion)
    
    # Mark transactions in conversion pairs
    converted_purchase_indices = set()
    refund_indices = set()
    
    for conversion in conversion_pairs:
        converted_purchase_indices.add(conversion['purchase_idx'])
        refund_indices.add(conversion['refund_idx'])
    
    # Add metadata to converted transactions
    for conversion in conversion_pairs:
        conversion['purchase']['extra_metadata'] = conversion['purchase'].get('extra_metadata', {})
        conversion['purchase']['extra_metadata']['emi_converted'] = True
        conversion['purchase']['extra_metadata']['converted_to_emi_on'] = conversion['refund'].get('date')
        conversion['purchase']['extra_metadata']['emi_amount'] = conversion['emi'].get('amount')
        
        logger.info(f"✅ EMI Conversion detected: Purchase ₹{conversion['purchase'].get('amount')} on {conversion['purchase'].get('date')} → "
                   f"EMI starts on {conversion['emi'].get('date')}")
    
    return sorted_txns


def _merchants_match(merchant1: str, merchant2: str) -> bool:
    """
    Check if two merchant names match (fuzzy matching)
    
    Args:
        merchant1: First merchant name
        merchant2: Second merchant name
    
    Returns:
        True if merchants match
    """
    if not merchant1 or not merchant2:
        return False
    
    m1_lower = merchant1.lower().strip()
    m2_lower = merchant2.lower().strip()
    
    # Exact match
    if m1_lower == m2_lower:
        return True
    
    # Check if one is a substring of the other (for cases like "HDFC SCHOOL" vs "HDFC SCHOOL BANGAL")
    if m1_lower in m2_lower or m2_lower in m1_lower:
        # Extract meaningful words (exclude common suffixes)
        m1_words = set(re.findall(r'\b\w{3,}\b', m1_lower))
        m2_words = set(re.findall(r'\b\w{3,}\b', m2_lower))
        
        # If at least 2 words match, consider it a match
        common_words = m1_words & m2_words
        if len(common_words) >= 2:
            return True
    
    return False


def _amounts_match(amount1: float, amount2: float, tolerance: float = 0.05) -> bool:
    """
    Check if two amounts match within tolerance
    
    Args:
        amount1: First amount
        amount2: Second amount
        tolerance: Maximum relative difference (default 5%)
    
    Returns:
        True if amounts match within tolerance
    """
    if amount1 == 0 or amount2 == 0:
        return False
    
    diff = abs(amount1 - amount2)
    avg = (amount1 + amount2) / 2
    
    return diff / avg <= tolerance


def _dates_within_days(date1_str: str, date2_str: str, max_days: int) -> bool:
    """
    Check if two dates are within max_days of each other
    
    Args:
        date1_str: First date string (YYYY-MM-DD)
        date2_str: Second date string (YYYY-MM-DD)
        max_days: Maximum number of days between dates
    
    Returns:
        True if dates are within max_days
    """
    try:
        date1 = datetime.strptime(date1_str, '%Y-%m-%d')
        date2 = datetime.strptime(date2_str, '%Y-%m-%d')
        diff = abs((date2 - date1).days)
        return diff <= max_days
    except:
        return False


def _days_between(date1_str: str, date2_str: str) -> int:
    """
    Calculate number of days between two dates
    
    Args:
        date1_str: First date string (YYYY-MM-DD)
        date2_str: Second date string (YYYY-MM-DD)
    
    Returns:
        Number of days between dates
    """
    try:
        date1 = datetime.strptime(date1_str, '%Y-%m-%d')
        date2 = datetime.strptime(date2_str, '%Y-%m-%d')
        return abs((date2 - date1).days)
    except:
        return 999999

