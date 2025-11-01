"""
Bank Transaction Repository - Data Access Layer

Database operations for bank transactions (savings, current, checking accounts).
Separates database operations from business logic.
"""

import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from storage.database import DatabaseManager
from storage.models import (
    BankTransaction, Account, User, Merchant,
    TransactionType, TransactionSource, TransactionCategory
)
from schema import CanonicalTransaction

logger = logging.getLogger(__name__)


class BankTransactionRepository:
    """
    Repository pattern for bank transaction database operations
    
    Encapsulates all database operations related to bank transactions.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize repository with database manager
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db_manager = db_manager
    
    def _get_session(self) -> Session:
        """Get database session"""
        return self.db_manager.get_session()
    
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
                return TransactionSource.MANUAL.value
        return TransactionSource.MANUAL.value
    
    def create_transaction(
        self,
        transaction_dict: dict,
        user_id: str,
        account_id: Optional[str] = None,
        session: Optional[Session] = None
    ) -> BankTransaction:
        """
        Create a bank transaction in database
        
        Args:
            transaction_dict: Transaction data dictionary
            user_id: User ID for the transaction
            account_id: Optional account ID
            session: Existing database session (if None, creates new)
            
        Returns:
            Created BankTransaction model instance
        """
        close_session = session is None
        
        if close_session:
            session = self._get_session()
        
        try:
            # Normalize date
            txn_date = transaction_dict.get('date', '')
            if not txn_date:
                txn_date = datetime.now().strftime('%Y-%m-%d')
            
            # Validate account type if account_id provided
            if account_id:
                account = session.query(Account).filter(
                    Account.account_id == account_id
                ).first()
                
                if account and account.account_type:
                    account_type = account.account_type.lower()
                    if account_type in ['credit_card', 'credit']:
                        raise ValueError(
                            f"Account {account_id} is a credit card account. "
                            "Use CreditCardTransactionRepository instead."
                        )
            
            # Build transaction object
            txn = BankTransaction(
                transaction_id=transaction_dict.get('transaction_id') or str(uuid.uuid4()),
                user_id=user_id,
                account_id=account_id or transaction_dict.get('account_id'),
                date=txn_date,
                timestamp=transaction_dict.get('timestamp'),
                amount=transaction_dict.get('amount', 0.0),
                type=transaction_dict.get('type', TransactionType.DEBIT),
                description_raw=transaction_dict.get('description_raw') or transaction_dict.get('remark') or transaction_dict.get('raw_remark'),
                clean_description=transaction_dict.get('clean_description') or transaction_dict.get('description'),
                merchant_raw=transaction_dict.get('merchant_raw') or transaction_dict.get('merchant'),
                merchant_canonical=transaction_dict.get('merchant_canonical'),
                merchant_id=transaction_dict.get('merchant_id'),
                category=transaction_dict.get('category', TransactionCategory.UNKNOWN),
                transaction_sub_type=transaction_dict.get('transaction_sub_type') or transaction_dict.get('sub_type'),
                labels=transaction_dict.get('labels'),
                confidence=transaction_dict.get('confidence'),
                balance=transaction_dict.get('balance'),
                transaction_reference=transaction_dict.get('transaction_reference') or transaction_dict.get('reference'),
                cheque_number=transaction_dict.get('cheque_number'),
                branch_code=transaction_dict.get('branch_code'),
                ifsc_code=transaction_dict.get('ifsc_code'),
                currency=transaction_dict.get('currency', 'INR'),
                original_amount=transaction_dict.get('original_amount'),
                original_currency=transaction_dict.get('original_currency'),
                duplicate_of=transaction_dict.get('duplicate_of'),
                duplicate_count=transaction_dict.get('duplicate_count', 0),
                is_duplicate=transaction_dict.get('is_duplicate', False),
                source=self._get_source_value(transaction_dict.get('source')),
                bank_name=transaction_dict.get('bank_name'),
                statement_period=transaction_dict.get('statement_period'),
                ingestion_timestamp=transaction_dict.get('ingestion_timestamp', datetime.now()),
                extra_metadata=transaction_dict.get('extra_metadata'),
                linked_asset_id=transaction_dict.get('linked_asset_id'),
                liquidation_event_id=transaction_dict.get('liquidation_event_id'),
                month=transaction_dict.get('month') or txn_date[:7],  # YYYY-MM
                is_recurring=transaction_dict.get('is_recurring', False),
                recurring_type=transaction_dict.get('recurring_type'),
                recurring_group_id=transaction_dict.get('recurring_group_id')
            )
            
            session.add(txn)
            
            if close_session:
                session.commit()
                session.refresh(txn)
            
            logger.debug(f"Created bank transaction: {txn.transaction_id[:8]}...")
            return txn
            
        except Exception as e:
            if close_session:
                session.rollback()
            logger.error(f"Error creating bank transaction: {e}")
            raise
        finally:
            if close_session:
                session.close()
    
    def get_transaction_by_id(
        self,
        transaction_id: str,
        user_id: Optional[str] = None,
        session: Optional[Session] = None
    ) -> Optional[BankTransaction]:
        """
        Get bank transaction by ID
        
        Args:
            transaction_id: Transaction ID
            user_id: Optional user ID for authorization check
            session: Existing database session
            
        Returns:
            BankTransaction instance or None
        """
        close_session = session is None
        
        if close_session:
            session = self._get_session()
        
        try:
            query = session.query(BankTransaction).filter(
                BankTransaction.transaction_id == transaction_id
            )
            
            if user_id:
                query = query.filter(BankTransaction.user_id == user_id)
            
            return query.first()
            
        finally:
            if close_session:
                session.close()
    
    def get_transactions(
        self,
        user_id: str,
        account_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None,
        transaction_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        session: Optional[Session] = None
    ) -> List[BankTransaction]:
        """
        Get bank transactions with filters
        
        Args:
            user_id: User ID (required)
            account_id: Optional account ID filter
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            category: Optional category filter
            transaction_type: Optional type filter ('debit' or 'credit')
            limit: Optional limit for pagination
            offset: Optional offset for pagination
            session: Existing database session
            
        Returns:
            List of BankTransaction instances
        """
        close_session = session is None
        
        if close_session:
            session = self._get_session()
        
        try:
            query = session.query(BankTransaction).filter(
                BankTransaction.user_id == user_id
            )
            
            if account_id:
                query = query.filter(BankTransaction.account_id == account_id)
            
            if start_date:
                query = query.filter(BankTransaction.date >= start_date)
            
            if end_date:
                query = query.filter(BankTransaction.date <= end_date)
            
            if category:
                query = query.filter(BankTransaction.category == category)
            
            if transaction_type:
                query = query.filter(BankTransaction.type == transaction_type)
            
            query = query.order_by(BankTransaction.date.desc(), BankTransaction.timestamp.desc())
            
            if offset:
                query = query.offset(offset)
            
            if limit:
                query = query.limit(limit)
            
            return query.all()
            
        finally:
            if close_session:
                session.close()
    
    def update_transaction(
        self,
        transaction_id: str,
        updates: dict,
        user_id: Optional[str] = None,
        session: Optional[Session] = None
    ) -> Optional[BankTransaction]:
        """
        Update bank transaction
        
        Args:
            transaction_id: Transaction ID
            updates: Dictionary of fields to update
            user_id: Optional user ID for authorization
            session: Existing database session
            
        Returns:
            Updated BankTransaction instance or None
        """
        close_session = session is None
        
        if close_session:
            session = self._get_session()
        
        try:
            query = session.query(BankTransaction).filter(
                BankTransaction.transaction_id == transaction_id
            )
            
            if user_id:
                query = query.filter(BankTransaction.user_id == user_id)
            
            txn = query.first()
            
            if not txn:
                return None
            
            # Update fields
            for key, value in updates.items():
                if hasattr(txn, key):
                    setattr(txn, key, value)
            
            txn.updated_at = datetime.now()
            
            if close_session:
                session.commit()
                session.refresh(txn)
            
            logger.debug(f"Updated bank transaction: {txn.transaction_id[:8]}...")
            return txn
            
        except Exception as e:
            if close_session:
                session.rollback()
            logger.error(f"Error updating bank transaction: {e}")
            raise
        finally:
            if close_session:
                session.close()
    
    def delete_transaction(
        self,
        transaction_id: str,
        user_id: Optional[str] = None,
        session: Optional[Session] = None
    ) -> bool:
        """
        Delete bank transaction
        
        Args:
            transaction_id: Transaction ID
            user_id: Optional user ID for authorization
            session: Existing database session
            
        Returns:
            True if deleted, False otherwise
        """
        close_session = session is None
        
        if close_session:
            session = self._get_session()
        
        try:
            query = session.query(BankTransaction).filter(
                BankTransaction.transaction_id == transaction_id
            )
            
            if user_id:
                query = query.filter(BankTransaction.user_id == user_id)
            
            txn = query.first()
            
            if not txn:
                return False
            
            session.delete(txn)
            
            if close_session:
                session.commit()
            
            logger.debug(f"Deleted bank transaction: {txn.transaction_id[:8]}...")
            return True
            
        except Exception as e:
            if close_session:
                session.rollback()
            logger.error(f"Error deleting bank transaction: {e}")
            raise
        finally:
            if close_session:
                session.close()
    
    def bulk_insert_transactions(
        self,
        transactions: List[dict],
        user_id: str,
        session: Optional[Session] = None
    ) -> List[BankTransaction]:
        """
        Bulk insert bank transactions
        
        Args:
            transactions: List of transaction dictionaries
            user_id: User ID for all transactions
            session: Existing database session
            
        Returns:
            List of created BankTransaction instances
        """
        close_session = session is None
        
        if close_session:
            session = self._get_session()
        
        try:
            created_txns = []
            
            for txn_dict in transactions:
                txn = self.create_transaction(
                    txn_dict,
                    user_id,
                    session=session
                )
                created_txns.append(txn)
            
            if close_session:
                session.commit()
            
            logger.info(f"Bulk inserted {len(created_txns)} bank transactions")
            return created_txns
            
        except Exception as e:
            if close_session:
                session.rollback()
            logger.error(f"Error bulk inserting bank transactions: {e}")
            raise
        finally:
            if close_session:
                session.close()
    
    def get_statistics(
        self,
        user_id: str,
        account_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Get bank transaction statistics
        
        Args:
            user_id: User ID
            account_id: Optional account ID filter
            start_date: Optional start date
            end_date: Optional end date
            session: Existing database session
            
        Returns:
            Dictionary with statistics
        """
        close_session = session is None
        
        if close_session:
            session = self._get_session()
        
        try:
            query = session.query(BankTransaction).filter(
                BankTransaction.user_id == user_id
            )
            
            if account_id:
                query = query.filter(BankTransaction.account_id == account_id)
            
            if start_date:
                query = query.filter(BankTransaction.date >= start_date)
            
            if end_date:
                query = query.filter(BankTransaction.date <= end_date)
            
            total_count = query.count()
            
            debit_query = query.filter(BankTransaction.type == TransactionType.DEBIT)
            credit_query = query.filter(BankTransaction.type == TransactionType.CREDIT)
            
            total_debit = debit_query.with_entities(func.sum(BankTransaction.amount)).scalar() or 0.0
            total_credit = credit_query.with_entities(func.sum(BankTransaction.amount)).scalar() or 0.0
            
            debit_count = debit_query.count()
            credit_count = credit_query.count()
            
            return {
                'total_count': total_count,
                'debit_count': debit_count,
                'credit_count': credit_count,
                'total_debit': float(total_debit),
                'total_credit': float(total_credit),
                'net_amount': float(total_credit - total_debit)
            }
            
        finally:
            if close_session:
                session.close()

