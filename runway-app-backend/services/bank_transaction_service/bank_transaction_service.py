"""
Bank Transaction Service - Business Logic Layer

Business logic for bank transaction operations.
Handles validation, business rules, and orchestrates repository calls.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from storage.database import DatabaseManager
from .bank_transaction_repository import BankTransactionRepository
from storage.models import Account

logger = logging.getLogger(__name__)


class BankTransactionService:
    """
    Business logic for bank transaction operations
    
    Handles validation, business rules, and orchestrates repository calls.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize service with database manager
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db_manager = db_manager
        self.repository = BankTransactionRepository(db_manager)
    
    def create_transaction(
        self,
        transaction_data: dict,
        user_id: str,
        account_id: Optional[str] = None
    ) -> dict:
        """
        Create a bank transaction
        
        Args:
            transaction_data: Transaction data dictionary
            user_id: User ID for the transaction
            account_id: Optional account ID
            
        Returns:
            Created transaction dictionary
        """
        # Validate account type if account_id provided
        if account_id:
            session = self.db_manager.get_session()
            try:
                account = session.query(Account).filter(
                    Account.account_id == account_id
                ).first()
                
                if account:
                    account_type = account.account_type.lower() if account.account_type else None
                    if account_type in ['credit_card', 'credit']:
                        raise ValueError(
                            f"Cannot create bank transaction for credit card account: {account_id}"
                        )
            finally:
                session.close()
        
        # Create transaction via repository
        txn = self.repository.create_transaction(
            transaction_data,
            user_id,
            account_id
        )
        
        return txn.to_dict()
    
    def get_transaction(
        self,
        transaction_id: str,
        user_id: str
    ) -> Optional[dict]:
        """
        Get bank transaction by ID
        
        Args:
            transaction_id: Transaction ID
            user_id: User ID for authorization
            
        Returns:
            Transaction dictionary or None
        """
        txn = self.repository.get_transaction_by_id(
            transaction_id,
            user_id
        )
        
        return txn.to_dict() if txn else None
    
    def get_transactions(
        self,
        user_id: str,
        account_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None,
        transaction_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[dict]:
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
            
        Returns:
            List of transaction dictionaries
        """
        txns = self.repository.get_transactions(
            user_id=user_id,
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
            category=category,
            transaction_type=transaction_type,
            limit=limit,
            offset=offset
        )
        
        return [txn.to_dict() for txn in txns]
    
    def update_transaction(
        self,
        transaction_id: str,
        updates: dict,
        user_id: str
    ) -> Optional[dict]:
        """
        Update bank transaction
        
        Args:
            transaction_id: Transaction ID
            updates: Dictionary of fields to update
            user_id: User ID for authorization
            
        Returns:
            Updated transaction dictionary or None
        """
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
        """
        Delete bank transaction
        
        Args:
            transaction_id: Transaction ID
            user_id: User ID for authorization
            
        Returns:
            True if deleted, False otherwise
        """
        return self.repository.delete_transaction(
            transaction_id,
            user_id
        )
    
    def bulk_create_transactions(
        self,
        transactions: List[dict],
        user_id: str
    ) -> List[dict]:
        """
        Bulk create bank transactions
        
        Args:
            transactions: List of transaction dictionaries
            user_id: User ID for all transactions
            
        Returns:
            List of created transaction dictionaries
        """
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
        """
        Get bank transaction statistics
        
        Args:
            user_id: User ID
            account_id: Optional account ID filter
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            Dictionary with statistics
        """
        return self.repository.get_statistics(
            user_id,
            account_id,
            start_date,
            end_date
        )

