"""
Unified Transaction Service - Business Logic Layer

Business logic for unified transaction operations.
Provides unified interface for both bank and credit card transactions.
"""

import logging
from typing import List, Optional, Dict, Any, Literal

from storage.database import DatabaseManager
from .unified_transaction_repository import UnifiedTransactionRepository
from services.bank_transaction_service.bank_transaction_service import BankTransactionService
from services.credit_card_transaction_service.credit_card_transaction_service import CreditCardTransactionService

logger = logging.getLogger(__name__)


class UnifiedTransactionService:
    """
    Unified service for both bank and credit card transactions
    
    Provides unified interface and routes to appropriate services.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize unified service
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db_manager = db_manager
        self.repository = UnifiedTransactionRepository(db_manager)
        self.bank_service = BankTransactionService(db_manager)
        self.credit_card_service = CreditCardTransactionService(db_manager)
    
    def get_transactions(
        self,
        user_id: str,
        account_id: Optional[str] = None,
        transaction_type: Literal['all', 'bank', 'credit_card'] = 'all',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[dict]:
        """Get transactions (bank, credit card, or both)"""
        return self.repository.get_transactions(
            user_id=user_id,
            account_id=account_id,
            transaction_type=transaction_type,
            start_date=start_date,
            end_date=end_date,
            category=category,
            limit=limit,
            offset=offset
        )
    
    def get_transaction(
        self,
        transaction_id: str,
        user_id: str
    ) -> Optional[dict]:
        """Get transaction by ID"""
        return self.repository.get_transaction_by_id(transaction_id, user_id)
    
    def create_transaction(
        self,
        transaction_data: dict,
        user_id: str,
        account_id: Optional[str] = None
    ) -> dict:
        """Create transaction (routes to appropriate service)"""
        return self.repository.create_transaction(
            transaction_data,
            user_id,
            account_id
        )
    
    def update_transaction(
        self,
        transaction_id: str,
        updates: dict,
        user_id: str
    ) -> Optional[dict]:
        """Update transaction"""
        return self.repository.update_transaction(
            transaction_id,
            updates,
            user_id
        )
    
    def delete_transaction(
        self,
        transaction_id: str,
        user_id: str
    ) -> bool:
        """Delete transaction"""
        return self.repository.delete_transaction(
            transaction_id,
            user_id
        )
    
    def get_statistics(
        self,
        user_id: str,
        account_id: Optional[str] = None,
        transaction_type: Literal['all', 'bank', 'credit_card'] = 'all',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get statistics"""
        return self.repository.get_statistics(
            user_id,
            account_id,
            transaction_type,
            start_date,
            end_date
        )
    
    # Convenience methods for accessing specific services
    def get_bank_transactions(self, user_id: str, **kwargs) -> List[dict]:
        """Get bank transactions only"""
        return self.bank_service.get_transactions(user_id, **kwargs)
    
    def get_credit_card_transactions(self, user_id: str, **kwargs) -> List[dict]:
        """Get credit card transactions only"""
        return self.credit_card_service.get_transactions(user_id, **kwargs)

