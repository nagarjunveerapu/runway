"""
Credit Card Transaction Repository - Data Access Layer

Database operations for credit card transactions.
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
    CreditCardTransaction, Account, User, Merchant, CreditCardStatement,
    TransactionType, TransactionSource, TransactionCategory
)
from schema import CanonicalTransaction

logger = logging.getLogger(__name__)


class CreditCardTransactionRepository:
    """
    Repository pattern for credit card transaction database operations
    
    Encapsulates all database operations related to credit card transactions.
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
        """Convert source value to proper format (ENUM value or string)"""
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
        statement_id: Optional[str] = None,
        session: Optional[Session] = None
    ) -> CreditCardTransaction:
        """
        Create a credit card transaction in database
        
        Args:
            transaction_dict: Transaction data dictionary
            user_id: User ID for the transaction
            account_id: Optional account ID
            statement_id: Optional statement ID
            session: Existing database session (if None, creates new)
            
        Returns:
            Created CreditCardTransaction model instance
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
                    if account_type not in ['credit_card', 'credit']:
                        raise ValueError(
                            f"Account {account_id} is not a credit card account. "
                            "Use BankTransactionRepository instead."
                        )
            
            # Build transaction object
            txn = CreditCardTransaction(
                transaction_id=transaction_dict.get('transaction_id') or str(uuid.uuid4()),
                user_id=user_id,
                account_id=account_id or transaction_dict.get('account_id'),
                statement_id=statement_id or transaction_dict.get('statement_id'),
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
                billing_cycle=transaction_dict.get('billing_cycle'),
                transaction_date=transaction_dict.get('transaction_date') or txn_date,
                posting_date=transaction_dict.get('posting_date'),
                due_date=transaction_dict.get('due_date'),
                reward_points=transaction_dict.get('reward_points'),
                transaction_fee=transaction_dict.get('transaction_fee'),
                foreign_transaction_fee=transaction_dict.get('foreign_transaction_fee'),
                currency_conversion_rate=transaction_dict.get('currency_conversion_rate'),
                currency=transaction_dict.get('currency', 'INR'),
                original_amount=transaction_dict.get('original_amount'),
                original_currency=transaction_dict.get('original_currency'),
                duplicate_of=transaction_dict.get('duplicate_of'),
                duplicate_count=transaction_dict.get('duplicate_count', 0),
                is_duplicate=transaction_dict.get('is_duplicate', False),
                source=self._get_source_value(transaction_dict.get('source')),
                bank_name=transaction_dict.get('bank_name'),
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
            
            logger.debug(f"Created credit card transaction: {txn.transaction_id[:8]}...")
            return txn
            
        except Exception as e:
            if close_session:
                session.rollback()
            logger.error(f"Error creating credit card transaction: {e}")
            raise
        finally:
            if close_session:
                session.close()
    
    def get_transaction_by_id(
        self,
        transaction_id: str,
        user_id: Optional[str] = None,
        session: Optional[Session] = None
    ) -> Optional[CreditCardTransaction]:
        """Get credit card transaction by ID"""
        close_session = session is None
        
        if close_session:
            session = self._get_session()
        
        try:
            query = session.query(CreditCardTransaction).filter(
                CreditCardTransaction.transaction_id == transaction_id
            )
            
            if user_id:
                query = query.filter(CreditCardTransaction.user_id == user_id)
            
            return query.first()
            
        finally:
            if close_session:
                session.close()
    
    def get_transactions(
        self,
        user_id: str,
        account_id: Optional[str] = None,
        statement_id: Optional[str] = None,
        billing_cycle: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None,
        transaction_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        session: Optional[Session] = None
    ) -> List[CreditCardTransaction]:
        """Get credit card transactions with filters"""
        close_session = session is None
        
        if close_session:
            session = self._get_session()
        
        try:
            query = session.query(CreditCardTransaction).filter(
                CreditCardTransaction.user_id == user_id
            )
            
            if account_id:
                query = query.filter(CreditCardTransaction.account_id == account_id)
            
            if statement_id:
                query = query.filter(CreditCardTransaction.statement_id == statement_id)
            
            if billing_cycle:
                query = query.filter(CreditCardTransaction.billing_cycle == billing_cycle)
            
            if start_date:
                query = query.filter(CreditCardTransaction.date >= start_date)
            
            if end_date:
                query = query.filter(CreditCardTransaction.date <= end_date)
            
            if category:
                query = query.filter(CreditCardTransaction.category == category)
            
            if transaction_type:
                query = query.filter(CreditCardTransaction.type == transaction_type)
            
            query = query.order_by(CreditCardTransaction.date.desc(), CreditCardTransaction.timestamp.desc())
            
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
    ) -> Optional[CreditCardTransaction]:
        """Update credit card transaction"""
        close_session = session is None
        
        if close_session:
            session = self._get_session()
        
        try:
            query = session.query(CreditCardTransaction).filter(
                CreditCardTransaction.transaction_id == transaction_id
            )
            
            if user_id:
                query = query.filter(CreditCardTransaction.user_id == user_id)
            
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
            
            logger.debug(f"Updated credit card transaction: {txn.transaction_id[:8]}...")
            return txn
            
        except Exception as e:
            if close_session:
                session.rollback()
            logger.error(f"Error updating credit card transaction: {e}")
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
        """Delete credit card transaction"""
        close_session = session is None
        
        if close_session:
            session = self._get_session()
        
        try:
            query = session.query(CreditCardTransaction).filter(
                CreditCardTransaction.transaction_id == transaction_id
            )
            
            if user_id:
                query = query.filter(CreditCardTransaction.user_id == user_id)
            
            txn = query.first()
            
            if not txn:
                return False
            
            session.delete(txn)
            
            if close_session:
                session.commit()
            
            logger.debug(f"Deleted credit card transaction: {txn.transaction_id[:8]}...")
            return True
            
        except Exception as e:
            if close_session:
                session.rollback()
            logger.error(f"Error deleting credit card transaction: {e}")
            raise
        finally:
            if close_session:
                session.close()
    
    def bulk_insert_transactions(
        self,
        transactions: List[dict],
        user_id: str,
        session: Optional[Session] = None
    ) -> List[CreditCardTransaction]:
        """Bulk insert credit card transactions"""
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
            
            logger.info(f"Bulk inserted {len(created_txns)} credit card transactions")
            return created_txns
            
        except Exception as e:
            if close_session:
                session.rollback()
            logger.error(f"Error bulk inserting credit card transactions: {e}")
            raise
        finally:
            if close_session:
                session.close()
    
    def get_transactions_by_billing_cycle(
        self,
        account_id: str,
        billing_cycle: str,
        session: Optional[Session] = None
    ) -> List[CreditCardTransaction]:
        """Get credit card transactions by billing cycle"""
        return self.get_transactions(
            user_id=None,  # Will be filtered by account_id
            account_id=account_id,
            billing_cycle=billing_cycle,
            session=session
        )
    
    def get_statistics(
        self,
        user_id: str,
        account_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """Get credit card transaction statistics"""
        close_session = session is None
        
        if close_session:
            session = self._get_session()
        
        try:
            query = session.query(CreditCardTransaction).filter(
                CreditCardTransaction.user_id == user_id
            )
            
            if account_id:
                query = query.filter(CreditCardTransaction.account_id == account_id)
            
            if start_date:
                query = query.filter(CreditCardTransaction.date >= start_date)
            
            if end_date:
                query = query.filter(CreditCardTransaction.date <= end_date)
            
            total_count = query.count()
            
            debit_query = query.filter(CreditCardTransaction.type == TransactionType.DEBIT)
            credit_query = query.filter(CreditCardTransaction.type == TransactionType.CREDIT)
            
            total_debit = debit_query.with_entities(func.sum(CreditCardTransaction.amount)).scalar() or 0.0
            total_credit = credit_query.with_entities(func.sum(CreditCardTransaction.amount)).scalar() or 0.0
            
            debit_count = debit_query.count()
            credit_count = credit_query.count()
            
            # Calculate fees
            total_fees = query.with_entities(
                func.sum(CreditCardTransaction.transaction_fee)
            ).scalar() or 0.0
            
            total_reward_points = query.with_entities(
                func.sum(CreditCardTransaction.reward_points)
            ).scalar() or 0.0
            
            return {
                'total_count': total_count,
                'debit_count': debit_count,
                'credit_count': credit_count,
                'total_debit': float(total_debit),
                'total_credit': float(total_credit),
                'net_amount': float(total_credit - total_debit),
                'total_fees': float(total_fees),
                'total_reward_points': float(total_reward_points)
            }
            
        finally:
            if close_session:
                session.close()

