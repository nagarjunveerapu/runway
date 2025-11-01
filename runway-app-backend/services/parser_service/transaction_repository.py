"""
Transaction Repository - Data Access Layer for Transaction Operations

Separates database operations from business logic.
"""

import logging
from typing import List, Optional
from datetime import datetime
import uuid

from storage.database import DatabaseManager
from storage.models import Transaction, User, TransactionType, TransactionSource, TransactionCategory
from schema import CanonicalTransaction

logger = logging.getLogger(__name__)


class TransactionRepository:
    """
    Repository pattern for transaction database operations
    
    Encapsulates all database operations related to transactions.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize repository with database manager
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db_manager = db_manager
    
    def _get_source_value(self, source_value):
        """
        Convert source value to proper format (ENUM value or string)
        
        Args:
            source_value: Source value (string or TransactionSource enum)
            
        Returns:
            String value for source
        """
        if source_value is None:
            return TransactionSource.MANUAL.value
        if isinstance(source_value, TransactionSource):
            return source_value.value
        if isinstance(source_value, str):
            # Map common string values to ENUM values
            source_lower = source_value.lower()
            if source_lower in ['pdf', 'pdf_upload']:
                return TransactionSource.PDF.value
            elif source_lower in ['csv', 'csv_upload']:
                return TransactionSource.CSV.value
            elif source_lower in ['excel', 'excel_upload']:
                return TransactionSource.EXCEL.value
            elif source_lower in ['aa', 'account_aggregator']:
                return TransactionSource.AA.value
            elif source_lower in ['api', 'api_upload']:
                return TransactionSource.API.value
            elif source_lower in ['manual', 'manually']:
                return TransactionSource.MANUAL.value
            else:
                # Unknown source, default to manual
                return TransactionSource.MANUAL.value
        return TransactionSource.MANUAL.value
    
    def insert_transaction(
        self,
        transaction_dict: dict,
        user_id: str,
        account_id: Optional[str] = None,
        session=None
    ) -> Transaction:
        """
        Insert a single transaction into database
        
        Args:
            transaction_dict: Transaction data dictionary
            user_id: User ID for the transaction
            account_id: Optional account ID
            session: Existing database session (if None, creates new)
            
        Returns:
            Created Transaction model instance
        """
        close_session = session is None
        
        if close_session:
            session = self.db_manager.get_session()
        
        try:
            # Normalize date
            txn_date = transaction_dict.get('date', '')
            if not txn_date:
                txn_date = datetime.now().strftime('%Y-%m-%d')
            
            # Handle different field names from parsers (legacy vs new format)
            # Legacy format: 'transaction_type', 'remark', 'raw_remark'
            # New format: 'type', 'description', 'description_raw'
            # Prioritize normalized description_raw for duplicate detection
            txn_type_str = transaction_dict.get('transaction_type') or transaction_dict.get('type', 'debit')
            # Convert string to TransactionType enum
            try:
                if isinstance(txn_type_str, str):
                    txn_type = TransactionType.DEBIT if txn_type_str.lower() == 'debit' else TransactionType.CREDIT
                elif isinstance(txn_type_str, TransactionType):
                    txn_type = txn_type_str
                else:
                    txn_type = TransactionType.DEBIT
            except:
                txn_type = TransactionType.DEBIT
            
            # Use description_raw if available (normalized, without date prefix)
            # Otherwise fall back to description, then remark, then raw_remark
            raw_description = (
                transaction_dict.get('description_raw') or 
                transaction_dict.get('description') or 
                transaction_dict.get('remark') or 
                transaction_dict.get('raw_remark') or 
                ''
            )
            description = (
                transaction_dict.get('description') or 
                transaction_dict.get('remark') or 
                transaction_dict.get('raw_remark') or 
                raw_description or 
                ''
            )
            
            # NOTE: We rely entirely on database unique constraint for duplicate detection
            # No application-level checking needed - database handles it efficiently
            # This approach is simpler, faster, and more reliable
            
            # Handle withdrawal/deposit format (legacy parser)
            if 'withdrawal' in transaction_dict and 'deposit' in transaction_dict:
                # Legacy format: has both withdrawal and deposit fields
                pass  # Already handled above
            
            # Create transaction record
            # Use 'id' from legacy parser or 'transaction_id' if provided
            transaction_id = transaction_dict.get('id') or transaction_dict.get('transaction_id') or str(uuid.uuid4())
            db_transaction = Transaction(
                transaction_id=transaction_id,
                user_id=user_id,
                account_id=account_id,
                date=txn_date,
                timestamp=datetime.now(),
                amount=float(transaction_dict.get('amount', 0)),
                # For PostgreSQL ENUM, pass the ENUM object itself (SQLAlchemy handles conversion)
                # For SQLite, pass the string value  
                type=txn_type if isinstance(txn_type, TransactionType) else TransactionType.DEBIT,
                description_raw=raw_description[:255] if raw_description else None,
                clean_description=description[:255] if description else None,
                merchant_raw=transaction_dict.get('merchant_raw', '')[:255] or None,
                merchant_canonical=transaction_dict.get('merchant_canonical', '')[:255] or None,
                category=self._get_category_value(transaction_dict.get('category', 'Unknown')),
                transaction_sub_type=transaction_dict.get('transaction_sub_type')[:100] if transaction_dict.get('transaction_sub_type') else None,
                # Handle balance: use 0.0 if present (including zero), None only if missing
                # FIX: Check 'is not None' instead of truthiness, as 0.0 is falsy but valid
                balance=float(transaction_dict.get('balance')) if transaction_dict.get('balance') is not None else None,
                source=self._get_source_value(transaction_dict.get('source')),
                is_duplicate=transaction_dict.get('is_duplicate', False),
                duplicate_count=transaction_dict.get('duplicate_count', 0),
                bank_name=transaction_dict.get('bank_name'),
                extra_metadata=transaction_dict.get('extra_metadata')
            )
            
            session.add(db_transaction)
            
            if close_session:
                session.commit()
                session.refresh(db_transaction)
            
            return db_transaction
            
        except Exception as e:
            if close_session:
                session.rollback()
            logger.error(f"Error inserting transaction: {e}", exc_info=True)
            raise
        finally:
            if close_session:
                session.close()
    
    def insert_transactions_batch(
        self,
        transactions: List[dict],
        user_id: str,
        account_id: Optional[str] = None,
        batch_size: int = 100
    ) -> int:
        """
        Insert multiple transactions one by one with individual commit
        
        Args:
            transactions: List of transaction dictionaries
            user_id: User ID for the transactions
            account_id: Optional account ID
            batch_size: NOT USED (kept for compatibility) - all transactions committed individually
            
        Returns:
            Number of successfully inserted transactions
        """
        logger.info("💾 TRANSACTION REPOSITORY: Starting individual insert (row by row)...")
        logger.info(f"💾 TRANSACTION REPOSITORY: Inserting {len(transactions)} transactions")
        logger.info(f"💾 TRANSACTION REPOSITORY: User ID: {user_id}")
        logger.info(f"💾 TRANSACTION REPOSITORY: Account ID: {account_id or 'None'}")
        
        inserted_count = 0
        duplicate_count = 0
        error_count = 0
        
        # Process each transaction individually with its own commit
        for idx, txn_dict in enumerate(transactions):
            session = self.db_manager.get_session()
            
            try:
                try:
                    self.insert_transaction(
                        txn_dict,
                        user_id,
                        account_id,
                        session=session
                    )
                    session.commit()
                    inserted_count += 1
                    
                    # Progress logging
                    if (idx + 1) % 50 == 0:
                        logger.info(f"💾 TRANSACTION REPOSITORY: Progress: {idx + 1}/{len(transactions)} processed")
                    
                except Exception as e:
                    session.rollback()
                    error_msg = str(e)
                    
                    if "UNIQUE constraint" in error_msg or "duplicate" in error_msg.lower():
                        duplicate_count += 1
                        # Log duplicate details for debugging
                        txn_date = txn_dict.get('date') or txn_dict.get('remark') or 'N/A'
                        txn_amount = txn_dict.get('amount', 0)
                        txn_desc = (txn_dict.get('description_raw') or txn_dict.get('raw_remark') or txn_dict.get('description') or txn_dict.get('remark') or 'N/A')[:80]
                        logger.info(f"💾 TRANSACTION REPOSITORY: 🔄 Duplicate #{duplicate_count} detected - Date: {txn_date}, Amount: ₹{txn_amount}, Description: {txn_desc}...")
                        if duplicate_count <= 5:  # Log first 5 duplicates with full details
                            logger.info(f"💾 TRANSACTION REPOSITORY: 🔄 Duplicate details: {error_msg[:200]}")
                    else:
                        error_count += 1
                        logger.warning(f"💾 TRANSACTION REPOSITORY: ⚠️  Failed to insert transaction {idx}: {e}")
                        
            finally:
                session.close()
        
        logger.info(f"💾 TRANSACTION REPOSITORY: ✅ Successfully inserted {inserted_count}/{len(transactions)} transactions")
        if duplicate_count > 0:
            logger.info(f"💾 TRANSACTION REPOSITORY: 🔄 Skipped {duplicate_count} duplicates from database")
        if error_count > 0:
            logger.warning(f"💾 TRANSACTION REPOSITORY: ⚠️  {error_count} transactions failed to insert")
        
        return inserted_count
    
    def insert_from_canonical(
        self,
        canonical_txns: List[CanonicalTransaction],
        user_id: str,
        account_id: Optional[str] = None
    ) -> int:
        """
        Insert transactions from CanonicalTransaction objects
        
        Args:
            canonical_txns: List of CanonicalTransaction objects
            user_id: User ID for the transactions
            account_id: Optional account ID
            
        Returns:
            Number of successfully inserted transactions
        """
        # Convert canonical transactions to dict format
        transaction_dicts = []
        for canonical in canonical_txns:
            txn_dict = {
                'transaction_id': canonical.transaction_id,
                'date': canonical.date,
                'amount': canonical.amount,
                'type': canonical.type,
                'description_raw': canonical.description_raw,
                'clean_description': canonical.clean_description,
                'merchant_raw': canonical.merchant_raw,
                'merchant_canonical': canonical.merchant_canonical,
                'category': canonical.category if hasattr(canonical, 'category') else 'Unknown',
                'balance': canonical.balance,
                'source': canonical.source,
                'is_duplicate': canonical.is_duplicate if hasattr(canonical, 'is_duplicate') else False,
                'duplicate_count': canonical.duplicate_count if hasattr(canonical, 'duplicate_count') else 0
            }
            transaction_dicts.append(txn_dict)
        
        return self.insert_transactions_batch(transaction_dicts, user_id, account_id)

