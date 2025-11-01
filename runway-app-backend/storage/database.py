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

from .models import Base, Transaction, Merchant, Account, User, TransactionType, TransactionSource, TransactionCategory, RecurringType
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
        
        # Create unique constraint for duplicate prevention
        # Includes balance to differentiate same transaction at different times in the day
        # Uses COALESCE to normalize NULL balance to sentinel value (-999999999.99)
        # SQLite UNIQUE constraint treats NULL as distinct, so we normalize NULLs
        session = self.get_session()
        try:
            # Drop existing index if it exists (without COALESCE)
            try:
                session.execute(text("DROP INDEX IF EXISTS idx_transaction_unique"))
                session.commit()
            except:
                pass
            
            # Create new unique index with COALESCE to handle NULL balance
            session.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_transaction_unique 
                ON transactions(
                    user_id, 
                    account_id, 
                    date, 
                    amount, 
                    description_raw, 
                    COALESCE(balance, -999999999.99)
                )
            """))
            session.commit()
            logger.info("Unique constraint created successfully (includes balance with NULL normalization)")
        except Exception as e:
            session.rollback()
            logger.warning(f"Could not create unique constraint: {e}")
        finally:
            session.close()

    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()

    def insert_transaction(self, canonical_txn: CanonicalTransaction, session: Optional[Session] = None) -> Transaction:
        """
        Insert a canonical transaction into database

        Args:
            canonical_txn: CanonicalTransaction object
            session: Existing session (if None, creates new)

        Returns:
            Created Transaction model instance
        """
        close_session = session is None
        if session is None:
            session = self.get_session()

        try:
            # Create merchant if doesn't exist
            merchant_db = None
            if canonical_txn.merchant_canonical and canonical_txn.merchant_id:
                merchant_db = session.query(Merchant).filter_by(
                    merchant_id=canonical_txn.merchant_id
                ).first()

                if not merchant_db:
                    merchant_db = Merchant(
                        merchant_id=canonical_txn.merchant_id,
                        merchant_canonical=canonical_txn.merchant_canonical,
                        category=canonical_txn.category,
                    )
                    session.add(merchant_db)

            # Create transaction
            txn_db = Transaction(
                transaction_id=canonical_txn.transaction_id,
                user_id=canonical_txn.metadata.get('user_id'),
                account_id=canonical_txn.account_id,
                merchant_id=canonical_txn.merchant_id,
                date=canonical_txn.date,
                timestamp=datetime.fromisoformat(canonical_txn.timestamp) if canonical_txn.timestamp else None,
                amount=canonical_txn.amount,
                type=canonical_txn.type,
                description_raw=canonical_txn.description_raw,
                clean_description=canonical_txn.clean_description,
                merchant_raw=canonical_txn.merchant_raw,
                merchant_canonical=canonical_txn.merchant_canonical,
                category=canonical_txn.category,
                labels=canonical_txn.labels,
                confidence=canonical_txn.confidence,
                balance=canonical_txn.balance,
                currency=canonical_txn.currency,
                original_amount=canonical_txn.original_amount,
                original_currency=canonical_txn.original_currency,
                duplicate_of=canonical_txn.duplicate_of,
                duplicate_count=canonical_txn.duplicate_count,
                is_duplicate=canonical_txn.is_duplicate,
                source=canonical_txn.source,
                bank_name=canonical_txn.bank_name,
                statement_period=canonical_txn.statement_period,
                ingestion_timestamp=datetime.fromisoformat(canonical_txn.ingestion_timestamp) if canonical_txn.ingestion_timestamp else None,
                extra_metadata=canonical_txn.metadata,
            )

            session.add(txn_db)
            session.commit()

            logger.debug(f"Inserted transaction: {txn_db.transaction_id[:8]}...")

            return txn_db

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to insert transaction: {e}")
            raise

        finally:
            if close_session:
                session.close()

    def insert_transactions_batch(self, canonical_txns: List[CanonicalTransaction]) -> int:
        """
        Insert multiple transactions in a batch

        Args:
            canonical_txns: List of CanonicalTransaction objects

        Returns:
            Number of transactions inserted
        """
        session = self.get_session()
        inserted_count = 0

        try:
            for txn in canonical_txns:
                try:
                    self.insert_transaction(txn, session=session)
                    inserted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to insert transaction {txn.transaction_id}: {e}")
                    continue

            logger.info(f"Inserted {inserted_count}/{len(canonical_txns)} transactions")

            return inserted_count

        finally:
            session.close()

    def get_transactions(self,
                        user_id: Optional[str] = None,
                        account_id: Optional[str] = None,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None,
                        category: Optional[str] = None,
                        limit: Optional[int] = None,
                        offset: int = 0) -> List[Transaction]:
        """
        Query transactions with filters

        Args:
            user_id: Filter by user
            account_id: Filter by account
            start_date: Filter by start date (YYYY-MM-DD)
            end_date: Filter by end date (YYYY-MM-DD)
            category: Filter by category
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of Transaction objects
        """
        session = self.get_session()

        try:
            query = session.query(Transaction)

            # Apply filters
            if user_id:
                query = query.filter(Transaction.user_id == user_id)

            if account_id:
                query = query.filter(Transaction.account_id == account_id)

            if start_date:
                query = query.filter(Transaction.date >= start_date)

            if end_date:
                query = query.filter(Transaction.date <= end_date)

            if category:
                query = query.filter(Transaction.category == category)

            # Exclude duplicates by default
            query = query.filter(Transaction.is_duplicate == False)

            # Order by date descending
            query = query.order_by(Transaction.date.desc())

            # Pagination
            if offset:
                query = query.offset(offset)

            if limit:
                query = query.limit(limit)

            transactions = query.all()

            return transactions

        finally:
            session.close()

    def get_summary_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get summary statistics

        Args:
            user_id: Filter by user

        Returns:
            Dictionary of statistics
        """
        session = self.get_session()

        try:
            query = session.query(Transaction)

            if user_id:
                query = query.filter(Transaction.user_id == user_id)

            # Exclude duplicates
            query = query.filter(Transaction.is_duplicate == False)

            # Total transactions
            total_count = query.count()

            # Total by type
            total_debit = query.filter(Transaction.type == TransactionType.DEBIT).with_entities(
                func.sum(Transaction.amount)
            ).scalar() or 0.0

            total_credit = query.filter(Transaction.type == TransactionType.CREDIT).with_entities(
                func.sum(Transaction.amount)
            ).scalar() or 0.0

            # By category with debit/credit netting
            category_breakdown = {}
            
            # Get all transactions for detailed processing
            transactions = query.all()
            
            # Group by category and merchant for netting
            category_merchant_totals = {}
            category_counts = {}
            
            for txn in transactions:
                # Include all transactions (EMI-converted transactions are now included)
                # Note: EMI-converted transactions are typically large purchases that were
                # converted to EMI, so including them gives a complete picture of spending
                # extra_metadata = txn.extra_metadata or {}
                # if extra_metadata.get('emi_converted'):
                #     continue  # COMMENTED OUT: Now including EMI-converted transactions
                
                category = txn.category or 'Unknown'
                merchant = txn.merchant_canonical or 'Unknown'
                key = (category, merchant)
                
                if key not in category_merchant_totals:
                    category_merchant_totals[key] = {'debit': 0.0, 'credit': 0.0}
                
                # Handle ENUM comparison (works for both ENUM and string for backward compatibility)
                txn_type_value = txn.type.value if hasattr(txn.type, 'value') else txn.type
                if txn_type_value == TransactionType.DEBIT.value:
                    category_merchant_totals[key]['debit'] += txn.amount
                    category_counts[category] = category_counts.get(category, 0) + 1
                elif txn_type_value == TransactionType.CREDIT.value:
                    category_merchant_totals[key]['credit'] += txn.amount
            
            # Calculate net totals per category (debit - credit)
            for (category, merchant), amounts in category_merchant_totals.items():
                net_amount = amounts['debit'] - amounts['credit']
                if net_amount > 0:  # Only show if net spending is positive
                    if category not in category_breakdown:
                        category_breakdown[category] = {'count': 0, 'total': 0.0}
                    category_breakdown[category]['total'] += net_amount
                    category_breakdown[category]['count'] = category_counts.get(category, 0)

            # Date range
            date_range = query.with_entities(
                func.min(Transaction.date),
                func.max(Transaction.date)
            ).first()

            return {
                'total_transactions': total_count,
                'total_debit': float(total_debit),
                'total_credit': float(total_credit),
                'net': float(total_credit - total_debit),
                'category_breakdown': category_breakdown,
                'date_range': {
                    'start': date_range[0],
                    'end': date_range[1]
                } if date_range[0] else None,
            }

        finally:
            session.close()

    def delete_transaction(self, transaction_id: str) -> bool:
        """Delete a transaction by ID"""
        session = self.get_session()

        try:
            txn = session.query(Transaction).filter_by(transaction_id=transaction_id).first()

            if txn:
                session.delete(txn)
                session.commit()
                logger.info(f"Deleted transaction: {transaction_id}")
                return True
            else:
                logger.warning(f"Transaction not found: {transaction_id}")
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
