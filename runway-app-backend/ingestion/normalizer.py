"""
Normalizer - Converts parsed transactions to canonical schema

Takes raw transaction dictionaries from parsers (PDF, CSV, AA) and
converts them to CanonicalTransaction objects.
"""

import logging
import uuid
from typing import List, Dict, Optional
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path to import schema
sys.path.insert(0, str(Path(__file__).parent.parent))
from schema import CanonicalTransaction, TransactionType

logger = logging.getLogger(__name__)


class Normalizer:
    """
    Normalizes parsed transactions to canonical schema

    Handles data cleaning, type conversion, and schema mapping.
    """

    def __init__(self, source: str = "manual", bank_name: Optional[str] = None):
        """
        Initialize normalizer

        Args:
            source: Data source ('pdf', 'csv', 'aa', 'manual')
            bank_name: Bank name for source tracking
        """
        self.source = source
        self.bank_name = bank_name

    def normalize(self, raw_transactions: List[Dict]) -> List[CanonicalTransaction]:
        """
        Normalize list of raw transactions to canonical schema

        Args:
            raw_transactions: List of transaction dictionaries from parser

        Returns:
            List of CanonicalTransaction objects
        """
        if not raw_transactions:
            return []

        canonical_txns = []
        errors = []

        for idx, raw_txn in enumerate(raw_transactions):
            try:
                canonical = self._normalize_single(raw_txn)
                canonical_txns.append(canonical)
            except Exception as e:
                errors.append(f"Transaction {idx}: {e}")
                logger.warning(f"Failed to normalize transaction {idx}: {e}")
                logger.debug(f"Raw transaction: {raw_txn}")
                continue

        if errors:
            logger.warning(f"Failed to normalize {len(errors)}/{len(raw_transactions)} transactions")

        logger.info(f"Normalized {len(canonical_txns)}/{len(raw_transactions)} transactions")
        return canonical_txns

    def _normalize_single(self, raw_txn: Dict) -> CanonicalTransaction:
        """
        Normalize a single transaction

        Args:
            raw_txn: Raw transaction dictionary

        Returns:
            CanonicalTransaction object
        """
        # Generate transaction ID
        transaction_id = raw_txn.get('transaction_id') or str(uuid.uuid4())

        # Extract and validate date
        date = self._normalize_date(raw_txn.get('date', ''))

        # Extract and validate amount
        amount = self._normalize_amount(raw_txn.get('amount', 0))

        # Extract and validate type
        txn_type = self._normalize_type(raw_txn.get('type', 'unknown'))

        # Extract description
        description_raw = str(raw_txn.get('description', '')).strip()
        clean_description = self._clean_description(description_raw)

        # Extract merchant (if provided by parser)
        merchant_raw = raw_txn.get('merchant_raw')
        merchant_canonical = raw_txn.get('merchant_canonical')

        # Extract balance
        balance = None
        if raw_txn.get('balance') is not None:
            try:
                balance = float(raw_txn['balance'])
            except (ValueError, TypeError):
                pass

        # Extract reference number
        ref_number = raw_txn.get('reference_number')

        # Build metadata
        metadata = {
            'source_file': raw_txn.get('source_file'),
            'reference_number': ref_number,
            'raw_description': description_raw,
        }
        # Remove None values
        metadata = {k: v for k, v in metadata.items() if v is not None}

        # Create canonical transaction
        canonical = CanonicalTransaction(
            transaction_id=transaction_id,
            date=date,
            amount=amount,
            type=txn_type,
            description_raw=description_raw,
            clean_description=clean_description,
            merchant_raw=merchant_raw,
            merchant_canonical=merchant_canonical,
            balance=balance,
            source=self.source,
            bank_name=self.bank_name,
            metadata=metadata,
        )

        return canonical

    @staticmethod
    def _normalize_date(date_str: str) -> str:
        """
        Normalize date to ISO 8601 format (YYYY-MM-DD)

        Args:
            date_str: Date string in various formats

        Returns:
            ISO 8601 date string (YYYY-MM-DD)
        """
        if not date_str:
            raise ValueError("Date is required")

        date_str = str(date_str).strip()

        # If already in ISO format, return as-is
        if len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-':
            return date_str

        # Try to parse various formats
        formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%d-%m-%Y',
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

        # If all formats fail, raise error
        raise ValueError(f"Could not parse date: {date_str}")

    @staticmethod
    def _normalize_amount(amount) -> float:
        """
        Normalize amount to float

        Args:
            amount: Amount (can be string, int, or float)

        Returns:
            Positive float amount
        """
        if amount is None:
            raise ValueError("Amount is required")

        # Convert to string first to handle various types
        amount_str = str(amount).strip()

        # Remove currency symbols and commas
        amount_str = amount_str.replace('₹', '').replace('$', '').replace(',', '')

        # Convert to float
        try:
            amount_float = float(amount_str)
        except ValueError:
            raise ValueError(f"Invalid amount: {amount}")

        # Return absolute value (amounts are always positive in canonical schema)
        return abs(amount_float)

    @staticmethod
    def _normalize_type(txn_type: str) -> str:
        """
        Normalize transaction type

        Args:
            txn_type: Transaction type string

        Returns:
            'debit' or 'credit'
        """
        txn_type = str(txn_type).strip().lower()

        # Map various type strings to canonical types
        debit_keywords = ['debit', 'dr', 'withdrawal', 'withdraw', 'payment', 'paid']
        credit_keywords = ['credit', 'cr', 'deposit']

        if any(keyword in txn_type for keyword in debit_keywords):
            return 'debit'
        elif any(keyword in txn_type for keyword in credit_keywords):
            return 'credit'
        else:
            # Default to debit if unknown
            logger.debug(f"Unknown transaction type: {txn_type}, defaulting to debit")
            return 'debit'

    @staticmethod
    def _clean_description(description: str) -> str:
        """
        Clean transaction description

        Removes excess whitespace, special characters, etc.
        """
        if not description:
            return ""

        # Remove excess whitespace
        cleaned = ' '.join(description.split())

        # Remove common noise
        noise_patterns = [
            r'\s+REF\s+\d+',
            r'\s+IMPS\s+',
            r'\s+NEFT\s+',
            r'\s+UPI\s+',
        ]

        import re
        for pattern in noise_patterns:
            cleaned = re.sub(pattern, ' ', cleaned, flags=re.IGNORECASE)

        # Final cleanup
        cleaned = ' '.join(cleaned.split())

        return cleaned.strip()


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Example raw transactions from parser
    raw_transactions = [
        {
            'date': '26/10/2024',
            'description': 'SWIGGY BANGALORE',
            'amount': 450.00,
            'type': 'debit',
            'balance': 12500.00,
        },
        {
            'date': '25/10/2024',
            'description': 'SALARY CREDIT',
            'amount': '50,000.00',
            'type': 'credit',
            'balance': 62500.00,
        },
    ]

    normalizer = Normalizer(source='pdf', bank_name='HDFC Bank')
    canonical_txns = normalizer.normalize(raw_transactions)

    print(f"\nNormalized {len(canonical_txns)} transactions:")
    for txn in canonical_txns:
        print(f"  {txn}")
