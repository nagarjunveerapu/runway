"""
Database Manager

Handles database connections, sessions, and common operations.
"""

import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .models import (
    Base, Merchant, Account, User,
    TransactionType, TransactionSource, TransactionCategory, RecurringType,
    BankTransaction, CreditCardTransaction
)
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from schema import CanonicalTransaction

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Database manager for transaction storage

    Supports SQLite (development) and PostgreSQL (production) via SQLAlchemy.
    """

    def __init__(self, database_url: str = "sqlite:///data/finance.db"):
        """
        Initialize database manager

        Args:
            database_url: SQLAlchemy database URL
                         Examples:
                         - sqlite:///data/finance.db
                         - postgresql://user:pass@localhost/financedb
        """
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None

        self._init_database()

    def _init_database(self):
        """Initialize database connection and create tables"""
        logger.info(f"Initializing database: {self.database_url}")

        # Create engine
        if self.database_url.startswith('sqlite'):
            # SQLite specific settings
            self.engine = create_engine(
                self.database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False  # Set to True for SQL debugging
            )

            # Create data directory if needed
            if ':///' in self.database_url:
                db_path = Path(self.database_url.split(':///')[-1])
                db_path.parent.mkdir(parents=True, exist_ok=True)

        else:
            # PostgreSQL or other databases
            self.engine = create_engine(
                self.database_url,
                pool_size=10,
                max_overflow=20,
                echo=False
            )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        # Create all tables
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")
        
        # Create unique constraints for duplicate prevention
        # Includes balance to differentiate same transaction at different times in the day
        # Uses COALESCE to normalize NULL balance to sentinel value (-999999999.99)
        # SQLite UNIQUE constraint treats NULL as distinct, so we normalize NULLs
        session = self.get_session()
        try:
            # Drop existing indexes if they exist
            for idx_name in ['idx_bank_transaction_unique', 'idx_cc_transaction_unique']:
                try:
                    session.execute(text(f"DROP INDEX IF EXISTS {idx_name}"))
                    session.commit()
                except:
                    session.rollback()
                    pass

            # Create unique constraints for bank_transactions table
            try:
                session.execute(text("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_bank_transaction_unique 
                    ON bank_transactions(
                        user_id, 
                        account_id, 
                        date, 
                        amount, 
                        description_raw, 
                        COALESCE(balance, -999999999.99)
                    )
                """))
                logger.info("Unique constraint created for bank_transactions table")
            except Exception as e:
                logger.debug(f"Could not create unique constraint for bank_transactions (table may not exist yet): {e}")
            
            # Create unique constraints for credit_card_transactions table
            # Note: Credit card transactions don't have balance, so we use statement_id instead
            try:
                session.execute(text("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_cc_transaction_unique 
                    ON credit_card_transactions(
                        user_id, 
                        account_id, 
                        COALESCE(statement_id, ''),
                        date, 
                        amount, 
                        description_raw
                    )
                """))
                logger.info("Unique constraint created for credit_card_transactions table")
            except Exception as e:
                logger.debug(f"Could not create unique constraint for credit_card_transactions (table may not exist yet): {e}")
            
            session.commit()
            logger.info("Unique constraints created successfully")
        except Exception as e:
            session.rollback()
            logger.warning(f"Could not create unique constraints: {e}")
        finally:
            session.close()

    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()

    def insert_transaction(self, canonical_txn: CanonicalTransaction, session: Optional[Session] = None):
        """
        DEPRECATED: Insert a canonical transaction into legacy transactions table

        This method is kept for backward compatibility only.
        New code should use BankTransactionRepository or CreditCardTransactionRepository instead.

        Args:
            canonical_txn: CanonicalTransaction object
            session: Existing session (if None, creates new)

        Returns:
            None (deprecated method raises error)
        """
        raise DeprecationWarning(
            "insert_transaction() is DEPRECATED and has been removed. "
            "Use BankTransactionRepository or CreditCardTransactionRepository instead."
        )

    def insert_transactions_batch(self, canonical_txns: List[CanonicalTransaction]) -> int:
        """
        DEPRECATED: Insert multiple transactions into legacy transactions table

        This method is kept for backward compatibility only.
        New code should use BankTransactionRepository or CreditCardTransactionRepository instead.

        Args:
            canonical_txns: List of CanonicalTransaction objects

        Returns:
            None (deprecated method raises error)
        """
        raise DeprecationWarning(
            "insert_transactions_batch() is DEPRECATED and has been removed. "
            "Use BankTransactionRepository or CreditCardTransactionRepository instead."
        )

    def get_transactions(self,
                        user_id: Optional[str] = None,
                        account_id: Optional[str] = None,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None,
                        category: Optional[str] = None,
                        limit: Optional[int] = None,
                        offset: int = 0) -> List:
        """
        Query transactions with filters

        UPDATED: Now fetches from both BankTransaction and CreditCardTransaction tables
        and returns them as Transaction-like objects for backward compatibility.

        Args:
            user_id: Filter by user
            account_id: Filter by account
            start_date: Filter by start date (YYYY-MM-DD)
            end_date: Filter by end date (YYYY-MM-DD)
            category: Filter by category
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of Transaction-like objects (combining bank and credit card transactions)
        """
        session = self.get_session()

        try:
            # Fetch from BankTransaction table
            bank_query = session.query(BankTransaction)
            if user_id:
                bank_query = bank_query.filter(BankTransaction.user_id == user_id)
            if account_id:
                bank_query = bank_query.filter(BankTransaction.account_id == account_id)
            if start_date:
                bank_query = bank_query.filter(BankTransaction.date >= start_date)
            if end_date:
                bank_query = bank_query.filter(BankTransaction.date <= end_date)
            if category:
                bank_query = bank_query.filter(BankTransaction.category == category)
            bank_query = bank_query.filter(BankTransaction.is_duplicate == False)
            bank_transactions = bank_query.all()

            # Fetch from CreditCardTransaction table
            cc_query = session.query(CreditCardTransaction)
            if user_id:
                cc_query = cc_query.filter(CreditCardTransaction.user_id == user_id)
            if account_id:
                cc_query = cc_query.filter(CreditCardTransaction.account_id == account_id)
            if start_date:
                cc_query = cc_query.filter(CreditCardTransaction.date >= start_date)
            if end_date:
                cc_query = cc_query.filter(CreditCardTransaction.date <= end_date)
            if category:
                cc_query = cc_query.filter(CreditCardTransaction.category == category)
            cc_query = cc_query.filter(CreditCardTransaction.is_duplicate == False)
            cc_transactions = cc_query.all()

            # Combine and convert to Transaction-like objects
            combined = []
            for bt in bank_transactions:
                combined.append(bt)
            for ct in cc_transactions:
                combined.append(ct)

            # Sort by date descending
            combined.sort(key=lambda x: x.date if x.date else '', reverse=True)

            # Apply pagination
            if offset or limit:
                start_idx = offset if offset else 0
                end_idx = (start_idx + limit) if limit else None
                combined = combined[start_idx:end_idx]

            return combined

        finally:
            session.close()

    def get_summary_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get summary statistics

        UPDATED: Now fetches from both BankTransaction and CreditCardTransaction tables

        Args:
            user_id: Filter by user

        Returns:
            Dictionary of statistics
        """
        session = self.get_session()

        try:
            # Fetch from BankTransaction table
            bank_query = session.query(BankTransaction)
            if user_id:
                bank_query = bank_query.filter(BankTransaction.user_id == user_id)
            bank_query = bank_query.filter(BankTransaction.is_duplicate == False)
            bank_transactions = bank_query.all()

            # Fetch from CreditCardTransaction table
            cc_query = session.query(CreditCardTransaction)
            if user_id:
                cc_query = cc_query.filter(CreditCardTransaction.user_id == user_id)
            cc_query = cc_query.filter(CreditCardTransaction.is_duplicate == False)
            cc_transactions = cc_query.all()

            # Combine all transactions
            all_transactions = list(bank_transactions) + list(cc_transactions)
            total_count = len(all_transactions)

            # Calculate totals
            total_debit = 0.0
            total_credit = 0.0
            category_merchant_totals = {}
            category_counts = {}
            all_dates = []

            for txn in all_transactions:
                # Handle date tracking
                if txn.date:
                    all_dates.append(txn.date)

                # Handle category
                category = txn.category.value if hasattr(txn.category, 'value') else str(txn.category) if txn.category else 'Unknown'
                merchant = txn.merchant_canonical or 'Unknown'
                key = (category, merchant)

                if key not in category_merchant_totals:
                    category_merchant_totals[key] = {'debit': 0.0, 'credit': 0.0}

                # Handle transaction type
                txn_type_value = txn.type.value if hasattr(txn.type, 'value') else str(txn.type)
                if txn_type_value in [TransactionType.DEBIT.value, 'debit']:
                    total_debit += txn.amount
                    category_merchant_totals[key]['debit'] += txn.amount
                    category_counts[category] = category_counts.get(category, 0) + 1
                elif txn_type_value in [TransactionType.CREDIT.value, 'credit']:
                    total_credit += txn.amount
                    category_merchant_totals[key]['credit'] += txn.amount

            # Calculate net totals per category (debit - credit)
            category_breakdown = {}
            for (category, merchant), amounts in category_merchant_totals.items():
                net_amount = amounts['debit'] - amounts['credit']
                if net_amount > 0:  # Only show if net spending is positive
                    if category not in category_breakdown:
                        category_breakdown[category] = {'count': 0, 'total': 0.0}
                    category_breakdown[category]['total'] += net_amount
                    category_breakdown[category]['count'] = category_counts.get(category, 0)

            # Date range
            date_range = None
            if all_dates:
                all_dates.sort()
                date_range = {
                    'start': all_dates[0],
                    'end': all_dates[-1]
                }

            return {
                'total_transactions': total_count,
                'total_debit': float(total_debit),
                'total_credit': float(total_credit),
                'net': float(total_credit - total_debit),
                'category_breakdown': category_breakdown,
                'date_range': date_range,
            }

        finally:
            session.close()

    def delete_transaction(self, transaction_id: str) -> bool:
        """
        Delete a transaction by ID from either bank_transactions or credit_card_transactions table

        Updated to search in both new tables instead of legacy transactions table
        """
        session = self.get_session()

        try:
            # Try to find in bank_transactions first
            bank_txn = session.query(BankTransaction).filter_by(transaction_id=transaction_id).first()
            if bank_txn:
                session.delete(bank_txn)
                session.commit()
                logger.info(f"Deleted bank transaction: {transaction_id}")
                return True

            # If not found, try credit_card_transactions
            cc_txn = session.query(CreditCardTransaction).filter_by(transaction_id=transaction_id).first()
            if cc_txn:
                session.delete(cc_txn)
                session.commit()
                logger.info(f"Deleted credit card transaction: {transaction_id}")
                return True

            logger.warning(f"Transaction not found in either table: {transaction_id}")
            return False

        finally:
            session.close()

    def close(self):
        """Close database connection"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Initialize database
    db = DatabaseManager()

    # Create sample transaction
    from schema import create_transaction

    txn = create_transaction(
        date="2025-10-26",
        amount=500.00,
        type=TransactionType.DEBIT.value,
        description="SWIGGY BANGALORE",
        merchant_canonical="Swiggy",
        category=TransactionCategory.FOOD_DINING.value,
        source=TransactionSource.MANUAL.value
    )

    # Insert transaction
    db.insert_transaction(txn)

    # Query transactions
    transactions = db.get_transactions(limit=10)
    print(f"\nFound {len(transactions)} transactions")
    for t in transactions[:3]:
        print(f"  {t}")

    # Get summary stats
    stats = db.get_summary_stats()
    print(f"\nSummary stats: {stats}")
