"""
Credit Card Transaction Service - Business Logic Layer

Business logic for credit card transaction operations.
Handles validation, business rules, and orchestrates repository calls.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from storage.database import DatabaseManager
from .credit_card_transaction_repository import CreditCardTransactionRepository
from storage.models import Account

logger = logging.getLogger(__name__)


class CreditCardTransactionService:
    """
    Business logic for credit card transaction operations
    
    Handles validation, business rules, and orchestrates repository calls.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize service with database manager
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db_manager = db_manager
        self.repository = CreditCardTransactionRepository(db_manager)
    
    def create_transaction(
        self,
        transaction_data: dict,
        user_id: str,
        account_id: Optional[str] = None,
        statement_id: Optional[str] = None
    ) -> dict:
        """Create a credit card transaction"""
        # Validate account type if account_id provided
        if account_id:
            session = self.db_manager.get_session()
            try:
                account = session.query(Account).filter(
                    Account.account_id == account_id
                ).first()
                
                if account:
                    account_type = account.account_type.lower() if account.account_type else None
                    if account_type not in ['credit_card', 'credit']:
                        raise ValueError(
                            f"Cannot create credit card transaction for non-credit card account: {account_id}"
                        )
            finally:
                session.close()
        
        # Create transaction via repository
        txn = self.repository.create_transaction(
            transaction_data,
            user_id,
            account_id,
            statement_id
        )
        
        return txn.to_dict()
    
    def get_transaction(
        self,
        transaction_id: str,
        user_id: str
    ) -> Optional[dict]:
        """Get credit card transaction by ID"""
        txn = self.repository.get_transaction_by_id(
            transaction_id,
            user_id
        )
        
        return txn.to_dict() if txn else None
    
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
        offset: Optional[int] = None
    ) -> List[dict]:
        """Get credit card transactions with filters"""
        txns = self.repository.get_transactions(
            user_id=user_id,
            account_id=account_id,
            statement_id=statement_id,
            billing_cycle=billing_cycle,
            start_date=start_date,
            end_date=end_date,
            category=category,
            transaction_type=transaction_type,
            limit=limit,
            offset=offset
        )
        
        return [txn.to_dict() for txn in txns]
    
    def get_transactions_by_billing_cycle(
        self,
        account_id: str,
        billing_cycle: str
    ) -> List[dict]:
        """Get credit card transactions by billing cycle"""
        txns = self.repository.get_transactions_by_billing_cycle(
            account_id,
            billing_cycle
        )
        
        return [txn.to_dict() for txn in txns]
    
    def update_transaction(
        self,
        transaction_id: str,
        updates: dict,
        user_id: str
    ) -> Optional[dict]:
        """Update credit card transaction"""
        txn = self.repository.update_transaction(
            transaction_id,
            updates,
            user_id
        )
        
        return txn.to_dict() if txn else None
    
    def delete_transaction(
        self,
        transaction_id: str,
        user_id: str
    ) -> bool:
        """Delete credit card transaction"""
        return self.repository.delete_transaction(
            transaction_id,
            user_id
        )
    
    def bulk_create_transactions(
        self,
        transactions: List[dict],
        user_id: str
    ) -> List[dict]:
        """Bulk create credit card transactions"""
        created_txns = self.repository.bulk_insert_transactions(
            transactions,
            user_id
        )
        
        return [txn.to_dict() for txn in created_txns]
    
    def get_statistics(
        self,
        user_id: str,
        account_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get credit card transaction statistics"""
        return self.repository.get_statistics(
            user_id,
            account_id,
            start_date,
            end_date
        )

