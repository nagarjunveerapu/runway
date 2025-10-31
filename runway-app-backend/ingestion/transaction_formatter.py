"""
Transaction Formatter - Common Utility for Transaction Formatting and Parsing

Contains shared logic for:
- Column detection (keywords)
- Amount extraction and type determination
- Transaction formatting (legacy format)

Parsers' single responsibility: Extract raw data from files
This module handles: Column detection, amount parsing, transaction formatting
"""

import uuid
import re
import logging
from typing import Dict, Optional, List, Tuple, Any, Union
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# ============================================================================
# COLUMN KEYWORD DEFINITIONS (Common for CSV and PDF)
# ============================================================================

# Column detection keywords - used by both CSV and PDF parsers
DATE_KEYWORDS = ['date', 'txn date', 'transaction date', 'value date', 'posting date', 'tran date']
DESC_KEYWORDS = [
    'transaction remark', 'remark', 'remarks',  # Legacy keywords
    'description', 'particulars', 'narration', 'details'  # New keywords
]
DEBIT_KEYWORDS = ['debit', 'withdrawal', 'dr', 'withdraw', 'withdrawal amount']
CREDIT_KEYWORDS = ['credit', 'deposit', 'cr', 'deposit amount']
AMOUNT_KEYWORDS = ['amount', 'txn amount', 'transaction amount']
BALANCE_KEYWORDS = ['balance', 'closing balance', 'available balance']
REF_KEYWORDS = ['reference', 'ref no', 'txn id', 'transaction id', 'cheque no']

# Try to import legacy utils for merchant/channel extraction
try:
    from src.utils import gen_uuid as _gen_uuid
    from src.parser import detect_channel as _detect_channel_legacy, extract_merchant_raw as _extract_merchant_raw_legacy
    LEGACY_UTILS_AVAILABLE = True
except ImportError:
    logger.warning("Legacy src.utils or src.parser not found. Some features (channel/merchant extraction, UUID) might be limited.")
    LEGACY_UTILS_AVAILABLE = False


def generate_transaction_id() -> str:
    """
    Generate UUID for transaction (uses legacy generator if available)
    
    Returns:
        UUID string
    """
    if LEGACY_UTILS_AVAILABLE:
        try:
            return _gen_uuid()
        except Exception:
            return str(uuid.uuid4())
    else:
        return str(uuid.uuid4())


def detect_channel(description: str) -> str:
    """
    Detect transaction channel from description
    
    Args:
        description: Transaction description
        
    Returns:
        Channel type: 'UPI', 'NEFT', 'ATM', 'OTHER', etc.
    """
    if LEGACY_UTILS_AVAILABLE:
        return _detect_channel_legacy(description)
    
    # Basic fallback
    text_lower = description.lower()
    if any(x in text_lower for x in ['upi', 'qr', 'scan']):
        return 'UPI'
    elif any(x in text_lower for x in ['neft', 'imps', 'rtgs']):
        return 'NEFT'
    elif any(x in text_lower for x in ['atm', 'cash']):
        return 'ATM'
    else:
        return 'OTHER'


def extract_merchant_raw(description: str) -> str:
    """
    Extract merchant name from description
    
    Args:
        description: Transaction description
        
    Returns:
        Merchant name (extracted or first word)
    """
    if LEGACY_UTILS_AVAILABLE:
        return _extract_merchant_raw_legacy(description)
    
    # Basic fallback - return first word or part before '/'
    if not description:
        return ''
    
    # Try to extract merchant name before '/'
    parts = description.split('/')
    if len(parts) > 1:
        return parts[0].strip()
    
    # Otherwise return first word
    words = description.split()
    return words[0] if words else ''


def normalize_date(date_str: str) -> str:
    """
    Normalize date to ISO format (YYYY-MM-DD)
    
    Handles formats: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, DD MMM YYYY, etc.
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        Date string in ISO format (YYYY-MM-DD)
    """
    date_str = date_str.strip()
    
    # Try different formats
    formats = [
        '%d/%m/%Y',
        '%d-%m-%Y',
        '%Y-%m-%d',
        '%d %b %Y',
        '%d-%b-%Y',
        '%d %B %Y',
        '%d-%B-%Y',
        '%m/%d/%Y',
        '%Y/%m/%d',
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    logger.warning(f"Could not parse date: {date_str}")
    return date_str


def normalize_description(description: str, date: Optional[str] = None) -> str:
    """
    Normalize transaction description by removing date prefixes and bank suffixes
    
    PDF parsers often include dates at the start: "01/08/2025 UPI/Manjunath/..."
    CSV parsers often include bank references at the end: "UPI/Manjunath/... fr/YES BANK L/344176360"
    
    This function removes:
    - Date prefixes (for PDF)
    - Bank references and transaction IDs (for CSV)
    to ensure consistent descriptions across PDF and CSV parsers for duplicate detection.
    
    Args:
        description: Raw transaction description
        date: Optional date string that might be prefixed
        
    Returns:
        Normalized description without date prefix or bank suffixes
    """
    if not description:
        return description
    
    desc = description.strip()
    
    # Step 1: Remove date patterns at the start of description
    # Pattern 1: "01/08/2025 " or "01-08-2025 " or "01/08/25 "
    date_prefix_pattern = r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s+'
    desc = re.sub(date_prefix_pattern, '', desc)
    
    # Pattern 2: If date is provided and matches at start, remove it
    if date:
        date_formats = [
            r'^\d{1,2}/\d{1,2}/\d{2,4}\s+',
            r'^\d{1,2}-\d{1,2}-\d{2,4}\s+',
            r'^\d{1,2}\.\d{1,2}\.\d{2,4}\s+',
        ]
        for pattern in date_formats:
            if re.match(pattern, desc):
                desc = re.sub(pattern, '', desc)
                break
    
    # Step 2: Remove bank references and transaction IDs at the end
    # Pattern: " fr/YES BANK L/344176360" or " fr/AXIS BANK/825123439649/IBL"
    # These appear in CSV files but not in PDF files
    # Handle both "/Payment fr/..." and " Payment fr/..." patterns
    bank_suffix_patterns = [
        # Match "/Payment fr/..." or " Payment fr/..." with complex suffixes
        r'[/\s]+Payment\s+fr/\s*[A-Z\s]+BANK[^/]*(?:/\d+[^/]*)*(?:/[A-Z0-9]+[^/]*)*/?\s*$',
        # Match "/Payment fr/..." or " Payment fr/..." with simpler patterns
        r'[/\s]+Payment\s+fr/\s*[A-Z\s]+BANK[^/]*(?:/\d+[^/]*)*/?\s*$',
        # Match "for 20 fr/..." patterns
        r'\s+for\s+\d+\s+fr/\s*[A-Z\s]+BANK[^/]*(?:/\d+[^/]*)*/?\s*$',
        # Match " fr/YES BANK L/344176360..." with complex suffixes
        r'\s+fr/\s*[A-Z\s]+BANK[^/]*(?:/\d+[^/]*)*(?:/[A-Z0-9]+[^/]*)*/?\s*$',
        # Match " fr/YES BANK L/344176360" (simpler)
        r'\s+fr/\s*[A-Z\s]+BANK[^/]*(?:/\d+[^/]*)*/?\s*$',
        # Match " fr/AXIS BANK/825123439649/IBL"
        r'\s+fr/\s*[A-Z\s]+/[^/]+/[^/]+/?\s*$',
        # Match " fr/AXIS BANK/825123"
        r'\s+fr/\s*[A-Z\s]+/[^/]+/?\s*$',
    ]
    
    for pattern in bank_suffix_patterns:
        desc = re.sub(pattern, '', desc, flags=re.IGNORECASE)
    
    # Step 3: Remove email-like patterns that differ between PDF and CSV
    # Pattern: "paytmqr6cdfqd@" or "swiggyupi@axb" or "9513314643@axl"
    # Remove these anywhere in the description (not just at end)
    desc = re.sub(r'/[a-z0-9]+@[a-z]+', '', desc, flags=re.IGNORECASE)
    
    # Step 4: Remove phone numbers and IDs (like "/9513314643" or "/266553694203")
    desc = re.sub(r'/\d{10,}', '', desc)
    
    # Step 5: Remove complex transaction IDs and hashes
    # Pattern: "/IBL103b5b9d25624dfabb31df2263a56f82" or "/AXBde924dfaa7ab4464bcbbcb5f4837244b"
    desc = re.sub(r'/[A-Z0-9]{20,}', '', desc)  # Remove long alphanumeric hashes
    
    # Step 6: Remove "Ltd", "Limited", "L" from anywhere (company name variations)
    # PDF has "UPI/Swiggy", CSV has "UPI/Swiggy Ltd/..."
    desc = re.sub(r'\b(Ltd|Limited|L)\s*/', '', desc, flags=re.IGNORECASE)
    
    # Step 7: Remove "Pay20for20" or similar patterns
    desc = re.sub(r'Pay\d+for\d+', '', desc, flags=re.IGNORECASE)
    
    # Step 8: Remove "Payment", "Pay", "Paym" variants at the end (common difference between PDF and CSV)
    desc = re.sub(r'\b(Payment|Pay|Paym)\s*$', '', desc, flags=re.IGNORECASE)
    
    # Step 9: Remove remaining bank references (more aggressive)
    # Handle patterns like "/AXIS BANK/266553694203" or "/YES BANK L/..."
    desc = re.sub(r'/[A-Z\s]+BANK[^/]*', '', desc, flags=re.IGNORECASE)
    
    # Step 10: Remove trailing name initials (like "/Mr MANJU M" or "/ADARSHA KU")
    # PDF has "UPI/Mr MANJU", CSV has "UPI/Mr MANJU M/..."
    desc = re.sub(r'/\s*[A-Z]+\s+[A-Z]\s*$', '', desc)
    
    # Step 11: Remove standalone single letter/short words after slash (like "/M" or "/KU")
    desc = re.sub(r'/[A-Z]{1,2}\s*$', '', desc)
    
    # Step 12: Clean up multiple consecutive slashes
    desc = re.sub(r'/+', '/', desc)
    
    # Step 13: Clean up trailing slashes and extra spaces
    desc = re.sub(r'[\/\s]+$', '', desc)
    
    # Step 14: Clean up any remaining extra whitespace
    desc = ' '.join(desc.split())
    
    return desc.strip()


def create_transaction_dict(
    description: str,
    amount: float,
    txn_type: str,  # 'debit' or 'credit'
    date: str,
    balance: Optional[float] = None,
    source: str = 'upload'
) -> Dict:
    """
    Create transaction dictionary in legacy format
    
    This function standardizes the transaction format used by both CSV and PDF parsers.
    Ensures consistent output format regardless of source.
    
    Args:
        description: Transaction description
        amount: Transaction amount (absolute value)
        txn_type: 'debit' or 'credit'
        date: Transaction date (will be normalized to ISO format)
        balance: Optional balance after transaction
        source: Source of transaction ('csv', 'pdf', etc.)
        
    Returns:
        Transaction dictionary in legacy format
    """
    # Normalize date
    transaction_date = normalize_date(date)
    
    # Normalize description - remove date prefixes for consistency
    # This ensures PDF and CSV produce same description_raw for duplicate detection
    normalized_description = normalize_description(description, date)
    
    # Extract merchant and channel (use normalized description)
    channel = detect_channel(normalized_description)
    merchant_raw = extract_merchant_raw(normalized_description)
    
    # Generate UUID
    transaction_id = generate_transaction_id()
    
    # Calculate withdrawal and deposit
    withdrawal = abs(amount) if txn_type == 'debit' else 0.0
    deposit = abs(amount) if txn_type == 'credit' else 0.0
    
    # Create transaction in legacy format (for compatibility)
    # Use normalized description for duplicate detection
    tx = {
        'id': transaction_id,
        'raw_remark': normalized_description,  # Use normalized description
        'remark': normalized_description,  # Use normalized description
        'description': normalized_description,  # New format field
        'description_raw': normalized_description,  # For database storage (unique constraint)
        'amount': abs(amount),  # Store absolute amount (same as legacy)
        'transaction_type': 'withdrawal' if txn_type == 'debit' else 'deposit',  # Legacy format
        'type': txn_type,  # New format field ('debit' or 'credit')
        'withdrawal': withdrawal,  # Legacy format
        'deposit': deposit,  # Legacy format
        'balance': balance,
        'date': transaction_date,
        'channel': channel,  # Legacy format
        'merchant_raw': merchant_raw,  # Legacy format
        'merchant': None,
        'category': None,
        'recurring': False,
        'recurrence_count': 0,
        'notes': f'Parsed from {source}',
    }
    
    return tx


# ============================================================================
# COLUMN DETECTION UTILITIES (Common for CSV and PDF)
# ============================================================================

def find_column_by_keywords(
    columns_lower: Dict[str, str], 
    keywords: List[str]
) -> Optional[str]:
    """
    Find column by matching keywords (common for CSV and PDF)
    
    Args:
        columns_lower: Dictionary mapping original column names to lowercased versions
        keywords: List of keywords to search for
        
    Returns:
        Original column name if found, None otherwise
    """
    for original_col, lower_col in columns_lower.items():
        for keyword in keywords:
            if keyword in lower_col:
                return original_col
    return None


def detect_columns(columns: List[str]) -> Dict[str, Optional[str]]:
    """
    Detect column mapping from column names (common for CSV and PDF)
    
    Args:
        columns: List of column names
        
    Returns:
        Dictionary mapping field names to column names
    """
    col_map = {}
    
    # Normalize column names for matching
    columns_lower = {col: col.lower().strip() for col in columns}
    
    # Detect each column type
    col_map['date'] = find_column_by_keywords(columns_lower, DATE_KEYWORDS)
    col_map['description'] = find_column_by_keywords(columns_lower, DESC_KEYWORDS)
    col_map['debit'] = find_column_by_keywords(columns_lower, DEBIT_KEYWORDS)
    col_map['credit'] = find_column_by_keywords(columns_lower, CREDIT_KEYWORDS)
    col_map['amount'] = find_column_by_keywords(columns_lower, AMOUNT_KEYWORDS)
    col_map['balance'] = find_column_by_keywords(columns_lower, BALANCE_KEYWORDS)
    col_map['reference'] = find_column_by_keywords(columns_lower, REF_KEYWORDS)
    
    # Return only detected columns
    return {k: v for k, v in col_map.items() if v is not None}


# ============================================================================
# AMOUNT EXTRACTION AND PARSING UTILITIES (Common for CSV and PDF)
# ============================================================================

def parse_amount_string(amount_str: str) -> Optional[float]:
    """
    Parse amount string to float (common for CSV and PDF)
    
    Removes non-numeric characters and converts to float.
    
    Args:
        amount_str: Amount string (may contain commas, currency symbols, etc.)
        
    Returns:
        Float amount if valid, None otherwise
    """
    if not amount_str or amount_str == 'nan':
        return None
    
    # Clean amount string (remove non-numeric except decimal point and minus)
    amount_str = str(amount_str).strip()
    amount_str = re.sub(r'[^\d.-]', '', amount_str)
    
    if not amount_str or amount_str == '':
        return None
    
    try:
        return float(amount_str)
    except ValueError:
        return None


def _get_row_value(row_data: Any, column: str) -> str:
    """
    Get value from row data (handles pandas Series, dict, etc.)
    
    Args:
        row_data: Row data (pandas Series, dict, etc.)
        column: Column name or key
        
    Returns:
        Value as string
    """
    try:
        # Try dictionary-like access
        if hasattr(row_data, 'get'):
            val = row_data.get(column, '')
        else:
            val = row_data[column]
        return str(val) if val is not None else ''
    except (KeyError, IndexError, AttributeError):
        return ''


def extract_amount_and_type(
    row_data: Union[Dict, Any],
    col_map: Dict[str, str]
) -> Tuple[Optional[float], str, float, float]:
    """
    Extract amount and transaction type from row data (common for CSV and PDF)
    
    Handles two formats:
    1. Separate debit/credit columns
    2. Single amount column (with sign or separate type column)
    
    Args:
        row_data: Row data (pandas Series or dict-like)
        col_map: Column mapping dictionary
        
    Returns:
        (amount, type, withdrawal, deposit) tuple
        - amount: Signed amount (deposit - withdrawal) or absolute amount
        - type: 'debit' or 'credit'
        - withdrawal: Withdrawal amount (or 0)
        - deposit: Deposit amount (or 0)
    """
    withdrawal = 0.0
    deposit = 0.0
    
    # Case 1: Separate debit/credit columns (preferred format)
    if col_map.get('debit') and col_map.get('credit'):
        debit_val = _get_row_value(row_data, col_map['debit']).strip()
        credit_val = _get_row_value(row_data, col_map['credit']).strip()
        
        # Parse amounts
        debit_amount = parse_amount_string(debit_val)
        credit_amount = parse_amount_string(credit_val)
        
        if debit_amount is not None:
            withdrawal = abs(debit_amount)
        
        if credit_amount is not None:
            deposit = abs(credit_amount)
        
        # Calculate signed amount (deposit - withdrawal)
        amount = deposit - withdrawal
        
        # Determine type
        if withdrawal > 0:
            txn_type = 'debit'
        elif deposit > 0:
            txn_type = 'credit'
        else:
            return None, 'unknown', 0.0, 0.0
        
        return amount, txn_type, withdrawal, deposit
    
    # Case 2: Single amount column
    elif col_map.get('amount'):
        amount_val = _get_row_value(row_data, col_map['amount']).strip()
        amount = parse_amount_string(amount_val)
        
        if amount is None:
            return None, 'unknown', 0.0, 0.0
        
        # Determine type by sign
        if amount < 0:
            withdrawal = abs(amount)
            deposit = 0.0
            txn_type = 'debit'
        else:
            withdrawal = 0.0
            deposit = abs(amount)
            txn_type = 'credit'
        
        return amount, txn_type, withdrawal, deposit
    
    else:
        # No amount column found
        return None, 'unknown', 0.0, 0.0


def extract_balance(row_data: Union[Dict, Any], col_map: Dict[str, str]) -> Optional[float]:
    """
    Extract balance from row data (common for CSV and PDF)
    
    Args:
        row_data: Row data (pandas Series or dict-like)
        col_map: Column mapping dictionary
        
    Returns:
        Balance float if found, None otherwise
    """
    if not col_map.get('balance'):
        return None
    
    balance_val = _get_row_value(row_data, col_map['balance']).strip()
    return parse_amount_string(balance_val)

