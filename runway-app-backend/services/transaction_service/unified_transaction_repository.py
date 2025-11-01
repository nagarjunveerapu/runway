"""
Unified Transaction Repository - Data Access Layer

Unified interface for accessing both bank and credit card transactions.
Routes queries to appropriate repositories based on account type or transaction type.
"""

import logging
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from sqlalchemy.orm import Session

from storage.database import DatabaseManager
from storage.models import Account
from services.bank_transaction_service.bank_transaction_repository import BankTransactionRepository
from services.credit_card_transaction_service.credit_card_transaction_repository import CreditCardTransactionRepository

logger = logging.getLogger(__name__)


class UnifiedTransactionRepository:
    """
    Unified repository for accessing both bank and credit card transactions
    
    Routes queries to appropriate repositories based on account type or transaction type.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize unified repository
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db_manager = db_manager
        self.bank_repo = BankTransactionRepository(db_manager)
        self.credit_card_repo = CreditCardTransactionRepository(db_manager)
    
    def _get_account_type(self, account_id: Optional[str], session: Optional[Session] = None) -> Optional[str]:
        """Get account type from account_id"""
        if not account_id:
            return None
        
        close_session = session is None
        if close_session:
            session = self.db_manager.get_session()
        
        try:
            account = session.query(Account).filter(
                Account.account_id == account_id
            ).first()
            
            if account and account.account_type:
                return account.account_type.lower()
            
            return None
        finally:
            if close_session:
                session.close()
    
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
        """
        Get transactions (bank, credit card, or both)
        
        Args:
            user_id: User ID (required)
            account_id: Optional account ID filter
            transaction_type: 'all', 'bank', or 'credit_card'
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            category: Optional category filter
            limit: Optional limit for pagination
            offset: Optional offset for pagination
            
        Returns:
            List of transaction dictionaries (from both tables)
        """
        results = []
        
        # Determine which repositories to query
        if transaction_type == 'bank':
            txns = self.bank_repo.get_transactions(
                user_id=user_id,
                account_id=account_id,
                start_date=start_date,
                end_date=end_date,
                category=category,
                limit=limit,
                offset=offset
            )
            results.extend([txn.to_dict() for txn in txns])
        
        elif transaction_type == 'credit_card':
            txns = self.credit_card_repo.get_transactions(
                user_id=user_id,
                account_id=account_id,
                start_date=start_date,
                end_date=end_date,
                category=category,
                limit=limit,
                offset=offset
            )
            results.extend([txn.to_dict() for txn in txns])
        
        else:  # 'all'
            # Get from both repositories
            bank_txns = self.bank_repo.get_transactions(
                user_id=user_id,
                account_id=account_id,
                start_date=start_date,
                end_date=end_date,
                category=category,
                limit=None,  # Get all, will merge and sort
                offset=None
            )
            
            cc_txns = self.credit_card_repo.get_transactions(
                user_id=user_id,
                account_id=account_id,
                start_date=start_date,
                end_date=end_date,
                category=category,
                limit=None,
                offset=None
            )
            
            # Merge and sort by date
            all_txns = [txn.to_dict() for txn in bank_txns] + [txn.to_dict() for txn in cc_txns]
            all_txns.sort(key=lambda x: (x.get('date', ''), x.get('timestamp', '')), reverse=True)
            
            # Apply pagination after sorting
            if offset:
                all_txns = all_txns[offset:]
            if limit:
                all_txns = all_txns[:limit]
            
            results = all_txns
        
        return results
    
    def get_transaction_by_id(
        self,
        transaction_id: str,
        user_id: str
    ) -> Optional[dict]:
        """
        Get transaction by ID (searches both tables)
        
        Args:
            transaction_id: Transaction ID
            user_id: User ID for authorization
            
        Returns:
            Transaction dictionary or None
        """
        # Try bank transactions first
        txn = self.bank_repo.get_transaction_by_id(transaction_id, user_id)
        if txn:
            return txn.to_dict()
        
        # Try credit card transactions
        txn = self.credit_card_repo.get_transaction_by_id(transaction_id, user_id)
        if txn:
            return txn.to_dict()
        
        return None
    
    def create_transaction(
        self,
        transaction_data: dict,
        user_id: str,
        account_id: Optional[str] = None
    ) -> dict:
        """
        Create transaction (routes to appropriate repository based on account type)
        
        Args:
            transaction_data: Transaction data dictionary
            user_id: User ID for the transaction
            account_id: Optional account ID
            
        Returns:
            Created transaction dictionary
        """
        # Determine account type
        account_type = self._get_account_type(account_id)
        
        # Route to appropriate repository
        if account_type in ['credit_card', 'credit']:
            return self.credit_card_repo.create_transaction(
                transaction_data,
                user_id,
                account_id
            ).to_dict()
        else:
            # Default to bank transaction
            return self.bank_repo.create_transaction(
                transaction_data,
                user_id,
                account_id
            ).to_dict()
    
    def update_transaction(
        self,
        transaction_id: str,
        updates: dict,
        user_id: str
    ) -> Optional[dict]:
        """Update transaction (searches both tables)"""
        # Try bank transactions first
        txn = self.bank_repo.update_transaction(transaction_id, updates, user_id)
        if txn:
            return txn.to_dict()
        
        # Try credit card transactions
        txn = self.credit_card_repo.update_transaction(transaction_id, updates, user_id)
        if txn:
            return txn.to_dict()
        
        return None
    
    def delete_transaction(
        self,
        transaction_id: str,
        user_id: str
    ) -> bool:
        """Delete transaction (searches both tables)"""
        # Try bank transactions first
        if self.bank_repo.delete_transaction(transaction_id, user_id):
            return True
        
        # Try credit card transactions
        if self.credit_card_repo.delete_transaction(transaction_id, user_id):
            return True
        
        return False
    
    def get_statistics(
        self,
        user_id: str,
        account_id: Optional[str] = None,
        transaction_type: Literal['all', 'bank', 'credit_card'] = 'all',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get statistics (bank, credit card, or combined)
        
        Args:
            user_id: User ID
            account_id: Optional account ID filter
            transaction_type: 'all', 'bank', or 'credit_card'
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            Dictionary with statistics
        """
        if transaction_type == 'bank':
            return self.bank_repo.get_statistics(
                user_id,
                account_id,
                start_date,
                end_date
            )
        elif transaction_type == 'credit_card':
            return self.credit_card_repo.get_statistics(
                user_id,
                account_id,
                start_date,
                end_date
            )
        else:  # 'all'
            bank_stats = self.bank_repo.get_statistics(
                user_id,
                account_id,
                start_date,
                end_date
            )
            cc_stats = self.credit_card_repo.get_statistics(
                user_id,
                account_id,
                start_date,
                end_date
            )
            
            # Merge statistics
            return {
                'total_count': bank_stats['total_count'] + cc_stats['total_count'],
                'debit_count': bank_stats['debit_count'] + cc_stats['debit_count'],
                'credit_count': bank_stats['credit_count'] + cc_stats['credit_count'],
                'total_debit': bank_stats['total_debit'] + cc_stats['total_debit'],
                'total_credit': bank_stats['total_credit'] + cc_stats['total_credit'],
                'net_amount': bank_stats['net_amount'] + cc_stats['net_amount'],
                'bank_transactions': bank_stats,
                'credit_card_transactions': cc_stats
            }

