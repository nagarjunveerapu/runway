"""
Canonical Transaction Schema v2.0

This is the single source of truth for all transaction data in the application.
All parsers (PDF, CSV, AA) must convert to this schema.
"""

from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import uuid
import hashlib
import json


class TransactionType(Enum):
    """Transaction type enumeration"""
    DEBIT = "debit"
    CREDIT = "credit"
    UNKNOWN = "unknown"


class Category(Enum):
    """Transaction category enumeration"""
    FOOD_DINING = "Food & Dining"
    GROCERIES = "Groceries"
    SHOPPING = "Shopping"
    TRANSPORT = "Transport"
    ENTERTAINMENT = "Entertainment"
    BILLS_UTILITIES = "Bills & Utilities"
    HEALTHCARE = "Healthcare"
    EDUCATION = "Education"
    TRAVEL = "Travel"
    INVESTMENT = "Investment"
    TRANSFER = "Transfer"
    SALARY = "Salary"
    REFUND = "Refund"
    OTHER = "Other"
    UNKNOWN = "Unknown"


@dataclass
class CanonicalTransaction:
    """
    Canonical transaction schema - single source of truth

    All transactions from any source (PDF, CSV, AA) are normalized to this schema.
    """

    # Core fields (required)
    transaction_id: str
    date: str  # ISO 8601: YYYY-MM-DD
    amount: float
    type: str  # 'debit' or 'credit'

    # Enhanced timestamp (v2.0)
    timestamp: Optional[str] = None  # ISO 8601 with timezone: 2025-10-26T10:30:00+05:30

    # Description fields
    description_raw: str = ""
    clean_description: str = ""

    # Merchant fields
    merchant_raw: Optional[str] = None
    merchant_canonical: Optional[str] = None
    merchant_id: Optional[str] = None  # SHA256 hash for fast joins

    # Categorization
    category: str = "Unknown"
    labels: List[str] = field(default_factory=list)  # Multi-label support
    confidence: Optional[float] = None  # ML prediction confidence

    # Balance tracking
    balance: Optional[float] = None

    # Multi-currency support (v2.0)
    currency: str = "INR"
    original_amount: Optional[float] = None
    original_currency: Optional[str] = None

    # Account information
    account_id: Optional[str] = None
    account_type: Optional[str] = None  # savings, credit_card, etc.

    # Source tracking
    source: str = "manual"  # pdf, csv, aa, manual
    bank_name: Optional[str] = None
    statement_period: Optional[str] = None

    # Deduplication (v2.0)
    duplicate_of: Optional[str] = None
    duplicate_count: int = 0
    is_duplicate: bool = False

    # Metadata
    ingestion_timestamp: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Post-initialization validation and normalization"""
        # Generate transaction_id if not provided
        if not self.transaction_id:
            self.transaction_id = str(uuid.uuid4())

        # Set ingestion timestamp
        if not self.ingestion_timestamp:
            self.ingestion_timestamp = datetime.now().isoformat()

        # Generate merchant_id from canonical merchant name
        if self.merchant_canonical and not self.merchant_id:
            self.merchant_id = self._generate_merchant_id(self.merchant_canonical)

        # Validate amount
        if self.amount < 0:
            raise ValueError(f"Amount must be positive: {self.amount}")

        # Validate type
        if self.type not in ['debit', 'credit']:
            raise ValueError(f"Type must be 'debit' or 'credit': {self.type}")

        # Normalize category
        if self.category not in [cat.value for cat in Category]:
            self.category = "Unknown"

    @staticmethod
    def _generate_merchant_id(merchant_canonical: str) -> str:
        """Generate deterministic merchant ID from canonical name"""
        return hashlib.sha256(merchant_canonical.lower().encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2, default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CanonicalTransaction':
        """Create from dictionary"""
        # Handle labels field (might be None)
        if 'labels' not in data or data['labels'] is None:
            data['labels'] = []

        # Handle metadata field (might be None)
        if 'metadata' not in data or data['metadata'] is None:
            data['metadata'] = {}

        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> 'CanonicalTransaction':
        """Create from JSON string"""
        return cls.from_dict(json.loads(json_str))

    def validate(self) -> bool:
        """Validate transaction data"""
        errors = []

        # Required fields
        if not self.transaction_id:
            errors.append("transaction_id is required")

        if not self.date:
            errors.append("date is required")

        if self.amount <= 0:
            errors.append(f"amount must be positive: {self.amount}")

        if self.type not in ['debit', 'credit']:
            errors.append(f"type must be 'debit' or 'credit': {self.type}")

        # Date format validation
        try:
            datetime.fromisoformat(self.date.replace('Z', '+00:00'))
        except ValueError:
            errors.append(f"date must be ISO 8601 format: {self.date}")

        if errors:
            raise ValueError(f"Validation errors: {', '.join(errors)}")

        return True

    def __repr__(self) -> str:
        """String representation"""
        return (f"CanonicalTransaction(id={self.transaction_id[:8]}..., "
                f"date={self.date}, amount={self.amount}, "
                f"type={self.type}, merchant={self.merchant_canonical}, "
                f"category={self.category})")


# Utility functions

def create_transaction(
    date: str,
    amount: float,
    type: str,
    description: str,
    **kwargs
) -> CanonicalTransaction:
    """
    Convenience function to create a transaction

    Args:
        date: Transaction date (YYYY-MM-DD)
        amount: Transaction amount (positive)
        type: Transaction type ('debit' or 'credit')
        description: Transaction description
        **kwargs: Additional fields

    Returns:
        CanonicalTransaction instance
    """
    return CanonicalTransaction(
        transaction_id=str(uuid.uuid4()),
        date=date,
        amount=amount,
        type=type,
        description_raw=description,
        clean_description=description,
        **kwargs
    )


def validate_transactions(transactions: List[CanonicalTransaction]) -> List[str]:
    """
    Validate a list of transactions

    Args:
        transactions: List of transactions to validate

    Returns:
        List of error messages (empty if all valid)
    """
    errors = []

    for i, txn in enumerate(transactions):
        try:
            txn.validate()
        except ValueError as e:
            errors.append(f"Transaction {i}: {e}")

    return errors


# Example usage
if __name__ == "__main__":
    # Create a sample transaction
    txn = create_transaction(
        date="2025-10-26",
        amount=500.00,
        type="debit",
        description="SWIGGY BANGALORE",
        merchant_canonical="Swiggy",
        category=Category.FOOD_DINING.value,
        source="pdf",
        bank_name="HDFC Bank"
    )

    print("Sample Transaction:")
    print(txn)
    print("\nJSON representation:")
    print(txn.to_json())

    # Validate
    try:
        txn.validate()
        print("\n✅ Transaction is valid")
    except ValueError as e:
        print(f"\n❌ Validation error: {e}")
