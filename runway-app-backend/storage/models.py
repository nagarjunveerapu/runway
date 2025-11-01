"""
SQLAlchemy Database Models

Defines the database schema for the personal finance app.
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, ForeignKey, Text, JSON, Enum as SQLEnum, TypeDecorator
from sqlalchemy.dialects.postgresql import ENUM as PostgresEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


# ENUM definitions for PostgreSQL compatibility
# These are used both in database schema and Python code
class TransactionType(enum.Enum):
    """Transaction type enumeration"""
    DEBIT = "debit"
    CREDIT = "credit"


class TransactionSource(enum.Enum):
    """Transaction source enumeration"""
    MANUAL = "manual"
    PDF = "pdf"
    CSV = "csv"
    EXCEL = "excel"
    AA = "aa"
    API = "api"


class RecurringType(enum.Enum):
    """Recurring transaction type enumeration"""
    SALARY = "salary"
    EMI = "emi"
    INVESTMENT = "investment"
    EXPENSE = "expense"


class TransactionCategory(enum.Enum):
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


# TypeDecorator to handle PostgreSQL ENUMs that store values, not member names
class PostgresEnumByValue(TypeDecorator):
    """TypeDecorator for PostgreSQL ENUMs that maps by value instead of member name"""
    impl = String
    cache_ok = True
    
    def __init__(self, enum_class, enum_name):
        super().__init__()
        self.enum_class = enum_class
        self.enum_name = enum_name
        # Create a mapping from value to enum member
        self._value_to_enum = {member.value: member for member in enum_class}
        
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            # Use String type and handle conversion manually
            # This bypasses PostgresEnum's member-name-based lookup
            return dialect.type_descriptor(String)
        else:
            return dialect.type_descriptor(String)
    
    def process_bind_param(self, value, dialect):
        """Convert Python enum/string to database value"""
        if value is None:
            return None
        if isinstance(value, self.enum_class):
            return value.value
        if isinstance(value, str):
            # Return string as-is (database will validate)
            return value
        return str(value)
    
    def process_result_value(self, value, dialect):
        """Convert database value to Python enum"""
        if value is None:
            return None
        if isinstance(value, str):
            # Map value to enum member
            enum_member = self._value_to_enum.get(value)
            if enum_member:
                return enum_member
            # If not found, return string as fallback (shouldn't happen with valid data)
            return value
        return value


# Helper function to get the appropriate ENUM column type
def _get_enum_column_type(enum_class, enum_name):
    """
    Returns the appropriate column type based on database.
    For PostgreSQL, returns PostgresEnumByValue (handles value mapping).
    For SQLite and others, returns String.
    """
    from config import Config
    db_url = Config.DATABASE_URL
    
    if db_url and db_url.startswith('postgresql'):
        # Use custom TypeDecorator that maps by value
        return PostgresEnumByValue(enum_class, enum_name)
    else:
        # Use String for SQLite and other databases
        return SQLEnum(enum_class)


class User(Base):
    """User model for multi-user support"""
    __tablename__ = 'users'

    user_id = Column(String(36), primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    accounts = relationship('Account', back_populates='user', cascade='all, delete-orphan')
    bank_transactions = relationship('BankTransaction', back_populates='user', cascade='all, delete-orphan')
    credit_card_transactions = relationship('CreditCardTransaction', back_populates='user', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<User(user_id='{self.user_id}', username='{self.username}')>"


class Account(Base):
    """Bank account model"""
    __tablename__ = 'accounts'

    account_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.user_id'), nullable=False)

    # Account details (PII stored in vault)
    account_number_ref = Column(String(64))  # Reference ID to vault
    account_type = Column(String(50))  # savings, current, credit_card, etc.
    bank_name = Column(String(100))
    account_name = Column(String(255))  # Display name

    # Metadata
    currency = Column(String(10), default='INR')
    current_balance = Column(Float)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    user = relationship('User', back_populates='accounts')
    bank_transactions = relationship('BankTransaction', back_populates='account', cascade='all, delete-orphan')
    credit_card_transactions = relationship('CreditCardTransaction', back_populates='account', cascade='all, delete-orphan')
    credit_card_statements = relationship('CreditCardStatement', back_populates='account', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Account(account_id='{self.account_id}', bank='{self.bank_name}', type='{self.account_type}')>"


class Merchant(Base):
    """Canonical merchant model"""
    __tablename__ = 'merchants'

    merchant_id = Column(String(64), primary_key=True)  # SHA256 hash
    merchant_canonical = Column(String(255), unique=True, nullable=False)
    category = Column(String(100))

    # Statistics
    transaction_count = Column(Integer, default=0)
    total_amount = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    bank_transactions = relationship('BankTransaction', back_populates='merchant')
    credit_card_transactions = relationship('CreditCardTransaction', back_populates='merchant')

    def __repr__(self):
        return f"<Merchant(merchant_id='{self.merchant_id}', name='{self.merchant_canonical}')>"


class Asset(Base):
    """Asset model for FIRE integration"""
    __tablename__ = 'assets'

    asset_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.user_id'), nullable=False)
    
    # Asset details
    name = Column(String(255), nullable=False)
    asset_type = Column(String(100))  # Stock, MutualFund, Property, etc.
    quantity = Column(Float)
    purchase_price = Column(Float)
    current_value = Column(Float)
    purchase_date = Column(DateTime)
    # Link to EMI pattern if created from recurring payment
    recurring_pattern_id = Column(String(36), index=True)
    
    # Metadata
    liquid = Column(Boolean, default=False)
    disposed = Column(Boolean, default=False)
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    user = relationship('User', back_populates='assets')
    
    def __repr__(self):
        return f"<Asset(asset_id='{self.asset_id}', name='{self.name}', type='{self.asset_type}')>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'asset_id': self.asset_id,
            'user_id': self.user_id,
            'name': self.name,
            'asset_type': self.asset_type,
            'quantity': self.quantity,
            'purchase_price': self.purchase_price,
            'current_value': self.current_value,
            'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
            'recurring_pattern_id': self.recurring_pattern_id,
            'liquid': self.liquid,
            'disposed': self.disposed,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Liquidation(Base):
    """Liquidation model for asset liquidation events"""
    __tablename__ = 'liquidations'

    liquidation_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.user_id'), nullable=False)
    asset_id = Column(String(36), nullable=False)
    
    # Liquidation details
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    gross_proceeds = Column(Float)
    fees = Column(Float, default=0.0)
    net_received = Column(Float)
    quantity_sold = Column(Float)
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    user = relationship('User', back_populates='liquidations')
    
    def __repr__(self):
        return f"<Liquidation(liquidation_id='{self.liquidation_id}', asset_id='{self.asset_id}', date='{self.date}')>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'liquidation_id': self.liquidation_id,
            'user_id': self.user_id,
            'asset_id': self.asset_id,
            'date': self.date,
            'gross_proceeds': self.gross_proceeds,
            'fees': self.fees,
            'net_received': self.net_received,
            'quantity_sold': self.quantity_sold,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class SalarySweepConfig(Base):
    """Salary Sweep Optimizer Configuration"""
    __tablename__ = 'salary_sweep_configs'

    config_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.user_id'), nullable=False)

    # Confirmed salary source
    salary_source = Column(String(255))  # Merchant/source name
    salary_amount = Column(Float)

    # Account rates
    salary_account_rate = Column(Float, default=2.5)  # Annual %
    savings_account_rate = Column(Float, default=7.0)  # Annual %

    # Selected scenario
    selected_scenario = Column(String(50))  # 'no_sweep', 'uniform', 'optimized'

    # Calculated results
    monthly_interest_saved = Column(Float)
    annual_interest_saved = Column(Float)
    optimization_data = Column(JSON)  # Store full calculation results

    # Status
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    user = relationship('User', back_populates='salary_sweep_config')
    detected_emis = relationship('DetectedEMIPattern', back_populates='config', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<SalarySweepConfig(config_id='{self.config_id}', user_id='{self.user_id}')>"

    def to_dict(self):
        return {
            'config_id': self.config_id,
            'user_id': self.user_id,
            'salary_source': self.salary_source,
            'salary_amount': self.salary_amount,
            'salary_account_rate': self.salary_account_rate,
            'savings_account_rate': self.savings_account_rate,
            'selected_scenario': self.selected_scenario,
            'monthly_interest_saved': self.monthly_interest_saved,
            'annual_interest_saved': self.annual_interest_saved,
            'optimization_data': self.optimization_data,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class DetectedEMIPattern(Base):
    """Detected recurring payment pattern (EMI/Investment/Insurance/Pension)"""
    __tablename__ = 'detected_emi_patterns'

    pattern_id = Column(String(36), primary_key=True)
    config_id = Column(String(36), ForeignKey('salary_sweep_configs.config_id'), nullable=False)
    user_id = Column(String(36), ForeignKey('users.user_id'), nullable=False)

    # Pattern details
    merchant_source = Column(String(255), nullable=False)
    emi_amount = Column(Float, nullable=False)
    occurrence_count = Column(Integer, default=0)

    # Category mapping (Loan, Insurance, Investment, Government Scheme)
    category = Column(String(50), index=True)  # 'Loan', 'Insurance', 'Investment', 'Government Scheme'
    subcategory = Column(String(100))  # 'Home Loan', 'Life Insurance', 'Mutual Fund SIP', 'APY', etc.

    # User confirmation
    is_confirmed = Column(Boolean, default=False)
    user_label = Column(String(255))  # User-provided name (e.g., "Home Loan EMI")

    # Model suggestions
    suggested_action = Column(String(50))  # 'keep', 'update', 'delete'
    suggestion_reason = Column(Text)  # Why model suggests this action

    # Transaction references
    transaction_ids = Column(JSON)  # List of transaction IDs that match this pattern

    # Metadata
    first_detected_date = Column(String(10))
    last_detected_date = Column(String(10))

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    config = relationship('SalarySweepConfig', back_populates='detected_emis')
    user = relationship('User', back_populates='detected_emi_patterns')

    def __repr__(self):
        return f"<DetectedEMIPattern(pattern_id='{self.pattern_id}', merchant='{self.merchant_source}', amount={self.emi_amount})>"

    def to_dict(self):
        return {
            'pattern_id': self.pattern_id,
            'config_id': self.config_id,
            'user_id': self.user_id,
            'merchant_source': self.merchant_source,
            'emi_amount': self.emi_amount,
            'occurrence_count': self.occurrence_count,
            'category': self.category,
            'subcategory': self.subcategory,
            'is_confirmed': self.is_confirmed,
            'user_label': self.user_label,
            'suggested_action': self.suggested_action,
            'suggestion_reason': self.suggestion_reason,
            'transaction_ids': self.transaction_ids,
            'first_detected_date': self.first_detected_date,
            'last_detected_date': self.last_detected_date,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# Update User model to include asset and liquidation relationships
class Liability(Base):
    """Liability model for tracking loans, EMIs, and debts"""
    __tablename__ = 'liabilities'
    
    liability_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.user_id'), nullable=False)
    
    # Liability details
    name = Column(String(255), nullable=False)  # e.g., "Home Loan", "Personal Loan"
    liability_type = Column(String(100))  # loan, credit_card, mortgage, emi, etc.
    
    # Financial details
    principal_amount = Column(Float)  # Original loan amount
    outstanding_balance = Column(Float)  # Current outstanding balance
    interest_rate = Column(Float)  # Annual interest rate (%)
    emi_amount = Column(Float)  # Monthly EMI payment
    # Rate and fees
    rate_type = Column(String(20))  # fixed | floating
    rate_reset_frequency_months = Column(Integer)  # For floating rates
    processing_fee = Column(Float)  # One-time fee
    prepayment_penalty_pct = Column(Float)  # % of prepaid amount

    # Tenure details
    original_tenure_months = Column(Integer)  # Total original loan tenure in months
    remaining_tenure_months = Column(Integer)  # Months remaining to pay off

    # Link to recurring payment pattern
    recurring_pattern_id = Column(String(36), index=True)  # Links to DetectedEMIPattern if auto-created

    # Metadata
    start_date = Column(DateTime)  # Loan start date
    end_date = Column(DateTime)  # Expected loan end date (start_date + original_tenure_months)
    last_rate_reset_date = Column(DateTime)  # For floating rate last reset
    moratorium_months = Column(Integer)  # Months with no principal payment
    lender_name = Column(String(255))  # Bank/NBFC name
    status = Column(String(20), default='active')  # active | closed
    closure_date = Column(DateTime)
    closure_reason = Column(String(255))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    user = relationship('User', back_populates='liabilities')
    
    def __repr__(self):
        return f"<Liability(liability_id='{self.liability_id}', name='{self.name}', balance={self.outstanding_balance})>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'liability_id': self.liability_id,
            'user_id': self.user_id,
            'name': self.name,
            'liability_type': self.liability_type,
            'principal_amount': self.principal_amount,
            'outstanding_balance': self.outstanding_balance,
            'interest_rate': self.interest_rate,
            'emi_amount': self.emi_amount,
            'original_tenure_months': self.original_tenure_months,
            'remaining_tenure_months': self.remaining_tenure_months,
            'recurring_pattern_id': self.recurring_pattern_id,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'lender_name': self.lender_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class BankTransaction(Base):
    """Bank transaction model (savings, current, checking accounts)"""
    __tablename__ = 'bank_transactions'

    # Primary key
    transaction_id = Column(String(36), primary_key=True)

    # Foreign keys
    user_id = Column(String(36), ForeignKey('users.user_id'), nullable=False, index=True)
    account_id = Column(String(36), ForeignKey('accounts.account_id'), index=True)
    merchant_id = Column(String(64), ForeignKey('merchants.merchant_id'))

    # Core transaction fields
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    timestamp = Column(DateTime)  # Full timestamp if available
    amount = Column(Float, nullable=False)
    type = Column(
        _get_enum_column_type(TransactionType, 'transaction_type'),
        nullable=False,
        default=TransactionType.DEBIT,
        index=True
    )

    # Description
    description_raw = Column(Text)
    clean_description = Column(Text)

    # Merchant (denormalized for performance)
    merchant_raw = Column(String(255))
    merchant_canonical = Column(String(255), index=True)

    # Categorization
    category = Column(
        _get_enum_column_type(TransactionCategory, 'transaction_category'),
        default=TransactionCategory.UNKNOWN,
        index=True
    )
    transaction_sub_type = Column(String(100))  # Sub-type classification (e.g., "EMI/Loan", "NEFT Transfer")
    labels = Column(JSON)  # Multi-label support
    confidence = Column(Float)  # ML prediction confidence

    # Bank-specific fields
    balance = Column(Float)  # Account balance after this transaction
    transaction_reference = Column(String(100))  # Transaction reference number (UTR, NEFT ref, etc.)
    cheque_number = Column(String(50))  # Cheque number if applicable
    branch_code = Column(String(50))  # Branch code for the transaction
    ifsc_code = Column(String(11))  # IFSC code for transfers

    # Multi-currency
    currency = Column(String(10), default='INR')
    original_amount = Column(Float)
    original_currency = Column(String(10))

    # Deduplication
    duplicate_of = Column(String(36), index=True)
    duplicate_count = Column(Integer, default=0)
    is_duplicate = Column(Boolean, default=False)

    # Source tracking
    source = Column(
        _get_enum_column_type(TransactionSource, 'transaction_source'),
        nullable=True
    )
    bank_name = Column(String(100))
    statement_period = Column(String(50))

    # Metadata
    ingestion_timestamp = Column(DateTime, default=datetime.now)
    extra_metadata = Column(JSON)  # Additional flexible metadata
    
    # FIRE integration fields
    linked_asset_id = Column(String(36), index=True)  # Reference to Asset
    liquidation_event_id = Column(String(36), index=True)  # Reference to Liquidation event
    month = Column(String(7), index=True)  # YYYY-MM format
    
    # Recurring pattern detection
    is_recurring = Column(Boolean, default=False, index=True)
    recurring_type = Column(
        _get_enum_column_type(RecurringType, 'recurring_type'),
        nullable=True
    )
    recurring_group_id = Column(String(36), index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    user = relationship('User', back_populates='bank_transactions')
    account = relationship('Account', back_populates='bank_transactions')
    merchant = relationship('Merchant', back_populates='bank_transactions')

    def __repr__(self):
        return (f"<BankTransaction(id='{self.transaction_id[:8]}...', "
                f"date='{self.date}', amount={self.amount}, "
                f"type='{self.type}', merchant='{self.merchant_canonical}')>")

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'transaction_id': self.transaction_id,
            'user_id': self.user_id,
            'account_id': self.account_id,
            'date': self.date,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'amount': self.amount,
            'type': self.type.value if hasattr(self.type, 'value') else str(self.type),
            'description_raw': self.description_raw,
            'clean_description': self.clean_description,
            'merchant_raw': self.merchant_raw,
            'merchant_canonical': self.merchant_canonical,
            'merchant_id': self.merchant_id,
            'category': self.category.value if hasattr(self.category, 'value') else str(self.category) if self.category else None,
            'transaction_sub_type': self.transaction_sub_type,
            'labels': self.labels,
            'confidence': self.confidence,
            'balance': self.balance,
            'transaction_reference': self.transaction_reference,
            'cheque_number': self.cheque_number,
            'branch_code': self.branch_code,
            'ifsc_code': self.ifsc_code,
            'currency': self.currency,
            'original_amount': self.original_amount,
            'original_currency': self.original_currency,
            'duplicate_of': self.duplicate_of,
            'duplicate_count': self.duplicate_count,
            'is_duplicate': self.is_duplicate,
            'source': self.source.value if hasattr(self.source, 'value') else str(self.source) if self.source else None,
            'bank_name': self.bank_name,
            'statement_period': self.statement_period,
            'ingestion_timestamp': self.ingestion_timestamp.isoformat() if self.ingestion_timestamp else None,
            'extra_metadata': self.extra_metadata,
            'linked_asset_id': self.linked_asset_id,
            'liquidation_event_id': self.liquidation_event_id,
            'month': self.month,
            'is_recurring': self.is_recurring,
            'recurring_type': self.recurring_type.value if hasattr(self.recurring_type, 'value') else str(self.recurring_type) if self.recurring_type else None,
            'recurring_group_id': self.recurring_group_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class CreditCardTransaction(Base):
    """Credit card transaction model"""
    __tablename__ = 'credit_card_transactions'

    # Primary key
    transaction_id = Column(String(36), primary_key=True)

    # Foreign keys
    user_id = Column(String(36), ForeignKey('users.user_id'), nullable=False, index=True)
    account_id = Column(String(36), ForeignKey('accounts.account_id'), index=True)
    merchant_id = Column(String(64), ForeignKey('merchants.merchant_id'))
    statement_id = Column(String(36), ForeignKey('credit_card_statements.statement_id'), index=True)

    # Core transaction fields
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD (transaction date)
    timestamp = Column(DateTime)  # Full timestamp if available
    amount = Column(Float, nullable=False)
    type = Column(
        _get_enum_column_type(TransactionType, 'transaction_type'),
        nullable=False,
        default=TransactionType.DEBIT,
        index=True
    )

    # Description
    description_raw = Column(Text)
    clean_description = Column(Text)

    # Merchant (denormalized for performance)
    merchant_raw = Column(String(255))
    merchant_canonical = Column(String(255), index=True)

    # Categorization
    category = Column(
        _get_enum_column_type(TransactionCategory, 'transaction_category'),
        default=TransactionCategory.UNKNOWN,
        index=True
    )
    transaction_sub_type = Column(String(100))  # Sub-type classification (e.g., "Online Purchase", "Cash Advance")
    labels = Column(JSON)  # Multi-label support
    confidence = Column(Float)  # ML prediction confidence

    # Credit card-specific fields
    billing_cycle = Column(String(50))  # Billing cycle (e.g., "Jan 2024")
    transaction_date = Column(String(10))  # Transaction date (may differ from statement date)
    posting_date = Column(String(10))  # Posting date
    due_date = Column(String(10))  # Due date for payment
    reward_points = Column(Float)  # Reward points earned/lost
    transaction_fee = Column(Float)  # Transaction fee charged
    foreign_transaction_fee = Column(Float)  # Foreign transaction fee if applicable
    currency_conversion_rate = Column(Float)  # Exchange rate if foreign transaction

    # Multi-currency
    currency = Column(String(10), default='INR')
    original_amount = Column(Float)  # Original amount in foreign currency
    original_currency = Column(String(10))

    # Deduplication
    duplicate_of = Column(String(36), index=True)
    duplicate_count = Column(Integer, default=0)
    is_duplicate = Column(Boolean, default=False)

    # Source tracking
    source = Column(
        _get_enum_column_type(TransactionSource, 'transaction_source'),
        nullable=True
    )
    bank_name = Column(String(100))

    # Metadata
    ingestion_timestamp = Column(DateTime, default=datetime.now)
    extra_metadata = Column(JSON)  # Additional flexible metadata
    
    # FIRE integration fields
    linked_asset_id = Column(String(36), index=True)  # Reference to Asset
    liquidation_event_id = Column(String(36), index=True)  # Reference to Liquidation event
    month = Column(String(7), index=True)  # YYYY-MM format
    
    # Recurring pattern detection
    is_recurring = Column(Boolean, default=False, index=True)
    recurring_type = Column(
        _get_enum_column_type(RecurringType, 'recurring_type'),
        nullable=True
    )
    recurring_group_id = Column(String(36), index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    user = relationship('User', back_populates='credit_card_transactions')
    account = relationship('Account', back_populates='credit_card_transactions')
    merchant = relationship('Merchant', back_populates='credit_card_transactions')
    statement = relationship('CreditCardStatement', back_populates='transactions')

    def __repr__(self):
        return (f"<CreditCardTransaction(id='{self.transaction_id[:8]}...', "
                f"date='{self.date}', amount={self.amount}, "
                f"type='{self.type}', merchant='{self.merchant_canonical}')>")

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'transaction_id': self.transaction_id,
            'user_id': self.user_id,
            'account_id': self.account_id,
            'statement_id': self.statement_id,
            'date': self.date,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'amount': self.amount,
            'type': self.type.value if hasattr(self.type, 'value') else str(self.type),
            'description_raw': self.description_raw,
            'clean_description': self.clean_description,
            'merchant_raw': self.merchant_raw,
            'merchant_canonical': self.merchant_canonical,
            'merchant_id': self.merchant_id,
            'category': self.category.value if hasattr(self.category, 'value') else str(self.category) if self.category else None,
            'transaction_sub_type': self.transaction_sub_type,
            'labels': self.labels,
            'confidence': self.confidence,
            'billing_cycle': self.billing_cycle,
            'transaction_date': self.transaction_date,
            'posting_date': self.posting_date,
            'due_date': self.due_date,
            'reward_points': self.reward_points,
            'transaction_fee': self.transaction_fee,
            'foreign_transaction_fee': self.foreign_transaction_fee,
            'currency_conversion_rate': self.currency_conversion_rate,
            'currency': self.currency,
            'original_amount': self.original_amount,
            'original_currency': self.original_currency,
            'duplicate_of': self.duplicate_of,
            'duplicate_count': self.duplicate_count,
            'is_duplicate': self.is_duplicate,
            'source': self.source.value if hasattr(self.source, 'value') else str(self.source) if self.source else None,
            'bank_name': self.bank_name,
            'ingestion_timestamp': self.ingestion_timestamp.isoformat() if self.ingestion_timestamp else None,
            'extra_metadata': self.extra_metadata,
            'linked_asset_id': self.linked_asset_id,
            'liquidation_event_id': self.liquidation_event_id,
            'month': self.month,
            'is_recurring': self.is_recurring,
            'recurring_type': self.recurring_type.value if hasattr(self.recurring_type, 'value') else str(self.recurring_type) if self.recurring_type else None,
            'recurring_group_id': self.recurring_group_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class CreditCardStatement(Base):
    """Credit Card Statement metadata tracking"""
    __tablename__ = 'credit_card_statements'

    statement_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.user_id'), nullable=False)
    account_id = Column(String(36), ForeignKey('accounts.account_id'), nullable=True, index=True)

    # Statement metadata
    bank_name = Column(String(100), nullable=False)
    card_number_masked = Column(String(50))  # Last 4 or masked number
    card_last_4_digits = Column(String(4), index=True)
    customer_name = Column(String(255))
    
    # Statement period
    statement_start_date = Column(String(10))  # YYYY-MM-DD
    statement_end_date = Column(String(10))  # YYYY-MM-DD
    billing_period = Column(String(50))  # e.g., "Jan 2024"
    
    # Transaction counts
    total_transactions = Column(Integer, default=0)
    transactions_processed = Column(Integer, default=0)
    
    # Source file tracking
    source_file = Column(String(255))
    source_type = Column(String(20))  # 'csv', 'pdf', 'manual'
    
    # Status
    is_processed = Column(Boolean, default=False)
    processing_status = Column(String(50))  # 'pending', 'processing', 'completed', 'failed'
    error_message = Column(Text)
    
    # Metadata
    extra_metadata = Column(JSON)  # Additional card-specific metadata
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    user = relationship('User', back_populates='credit_card_statements')
    account = relationship('Account', back_populates='credit_card_statements')
    transactions = relationship('CreditCardTransaction', back_populates='statement', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<CreditCardStatement(statement_id='{self.statement_id}', bank='{self.bank_name}', period='{self.billing_period}')>"

    def to_dict(self):
        return {
            'statement_id': self.statement_id,
            'user_id': self.user_id,
            'account_id': self.account_id,
            'bank_name': self.bank_name,
            'card_number_masked': self.card_number_masked,
            'card_last_4_digits': self.card_last_4_digits,
            'customer_name': self.customer_name,
            'statement_start_date': self.statement_start_date,
            'statement_end_date': self.statement_end_date,
            'billing_period': self.billing_period,
            'total_transactions': self.total_transactions,
            'transactions_processed': self.transactions_processed,
            'source_file': self.source_file,
            'source_type': self.source_type,
            'is_processed': self.is_processed,
            'processing_status': self.processing_status,
            'error_message': self.error_message,
            'extra_metadata': self.extra_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class NetWorthSnapshot(Base):
    """Net Worth Snapshot model for timeline tracking"""
    __tablename__ = 'net_worth_snapshots'

    snapshot_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.user_id'), nullable=False)

    # Snapshot date and month
    snapshot_date = Column(String(10), nullable=False)  # YYYY-MM-DD format
    month = Column(String(7), nullable=False, index=True)  # YYYY-MM format for grouping

    # Financial data at snapshot time
    total_assets = Column(Float, default=0.0)
    total_liabilities = Column(Float, default=0.0)
    net_worth = Column(Float, default=0.0)

    # Breakdown (optional, for detailed insights)
    liquid_assets = Column(Float, default=0.0)
    asset_breakdown = Column(JSON)  # {"property": 5000000, "stocks": 1000000, ...}
    liability_breakdown = Column(JSON)  # {"home_loan": 2000000, "car_loan": 500000, ...}

    # Metadata
    created_at = Column(DateTime, default=datetime.now)

    # Relationship
    user = relationship('User', back_populates='net_worth_snapshots')

    def __repr__(self):
        return f"<NetWorthSnapshot(user_id='{self.user_id}', month='{self.month}', net_worth={self.net_worth})>"

    def to_dict(self):
        return {
            'snapshot_id': self.snapshot_id,
            'user_id': self.user_id,
            'snapshot_date': self.snapshot_date,
            'month': self.month,
            'total_assets': self.total_assets,
            'total_liabilities': self.total_liabilities,
            'net_worth': self.net_worth,
            'liquid_assets': self.liquid_assets,
            'asset_breakdown': self.asset_breakdown,
            'liability_breakdown': self.liability_breakdown,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


User.assets = relationship('Asset', back_populates='user', cascade='all, delete-orphan')
User.liquidations = relationship('Liquidation', back_populates='user', cascade='all, delete-orphan')
User.liabilities = relationship('Liability', back_populates='user', cascade='all, delete-orphan')
User.salary_sweep_config = relationship('SalarySweepConfig', back_populates='user', uselist=False, cascade='all, delete-orphan')
User.detected_emi_patterns = relationship('DetectedEMIPattern', back_populates='user', cascade='all, delete-orphan')
User.credit_card_statements = relationship('CreditCardStatement', back_populates='user', cascade='all, delete-orphan')
User.net_worth_snapshots = relationship('NetWorthSnapshot', back_populates='user', cascade='all, delete-orphan')

# Indexes for performance
from sqlalchemy import Index, UniqueConstraint

# Composite indexes for common queries

# BankTransaction table indexes
Index('idx_bank_txn_user_date', BankTransaction.user_id, BankTransaction.date)
Index('idx_bank_txn_user_category', BankTransaction.user_id, BankTransaction.category)
Index('idx_bank_txn_account_date', BankTransaction.account_id, BankTransaction.date)
Index('idx_bank_txn_merchant_date', BankTransaction.merchant_canonical, BankTransaction.date)
Index('idx_bank_txn_user_month', BankTransaction.user_id, BankTransaction.month)
Index('idx_bank_txn_type', BankTransaction.type)

# CreditCardTransaction table indexes
Index('idx_cc_txn_user_date', CreditCardTransaction.user_id, CreditCardTransaction.date)
Index('idx_cc_txn_user_category', CreditCardTransaction.user_id, CreditCardTransaction.category)
Index('idx_cc_txn_account_date', CreditCardTransaction.account_id, CreditCardTransaction.date)
Index('idx_cc_txn_statement', CreditCardTransaction.statement_id, CreditCardTransaction.date)
Index('idx_cc_txn_billing_cycle', CreditCardTransaction.account_id, CreditCardTransaction.billing_cycle)
Index('idx_cc_txn_merchant_date', CreditCardTransaction.merchant_canonical, CreditCardTransaction.date)
Index('idx_cc_txn_user_month', CreditCardTransaction.user_id, CreditCardTransaction.month)
Index('idx_cc_txn_type', CreditCardTransaction.type)

# Other indexes
Index('idx_asset_user', Asset.user_id)
Index('idx_asset_recurring_pattern', Asset.recurring_pattern_id)
Index('idx_liquidation_user', Liquidation.user_id, Liquidation.asset_id)
Index('idx_liability_user', Liability.user_id)
Index('idx_liability_pattern', Liability.recurring_pattern_id)
Index('idx_net_worth_user_month', NetWorthSnapshot.user_id, NetWorthSnapshot.month)

# Unique constraint to prevent exact duplicate transactions
# NOTE: SQLite UNIQUE constraint treats NULL as distinct, so we can't use balance directly
# We need to use COALESCE in raw SQL to normalize NULL values
# This unique index is created via raw SQL in database.py and reset_and_setup.py
# INCLUDES BALANCE: Two transactions with same date/amount/description but different balances 
# are considered different (e.g., same transaction at different times in the day)
# NULL balance is normalized to -999999999.99 to handle NULL comparison correctly
# Index('idx_transaction_unique', ...) - Created via raw SQL instead (see database.py)
