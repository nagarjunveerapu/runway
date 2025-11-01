"""
Credit Card Service - Business Logic Layer

Handles credit card-specific operations:
- Statement metadata tracking
- Credit card account management
- Statement processing workflow
"""

import logging
import uuid
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from storage.database import DatabaseManager
from storage.models import (
    Account, CreditCardStatement, Transaction, TransactionType, TransactionSource
)

logger = logging.getLogger(__name__)


class CreditCardService:
    """
    Business logic for credit card operations
    
    Handles credit card statement metadata and account management
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize credit card service
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db_manager = db_manager
    
    def create_or_update_credit_card_account(
        self,
        user_id: str,
        metadata: Dict
    ) -> Optional[str]:
        """
        Create or update credit card account from parsed metadata
        
        Args:
            user_id: User ID
            metadata: Metadata with card_number, card_last_4_digits, bank_name, etc.
            
        Returns:
            Account ID if created/updated, None otherwise
        """
        session = self.db_manager.get_session()
        
        try:
            card_last_4 = metadata.get('card_last_4_digits')
            bank_name = metadata.get('bank_name')
            customer_name = metadata.get('customer_name')
            
            if not bank_name:
                logger.warning("No bank name in metadata, skipping account creation")
                return None
            
            # Try to find existing credit card account
            existing_account = session.query(Account).filter(
                Account.user_id == user_id,
                Account.account_type == 'credit_card',
                Account.bank_name == bank_name
            ).first()
            
            if card_last_4:
                # More specific search if we have last 4 digits
                existing_account = session.query(Account).filter(
                    Account.user_id == user_id,
                    Account.account_type == 'credit_card',
                    Account.account_number_ref == card_last_4
                ).first()
            
            if existing_account:
                # Update existing account
                logger.info(f"Updating existing credit card account: {existing_account.account_id}")
                if not existing_account.account_name and customer_name:
                    existing_account.account_name = customer_name
                if not existing_account.account_number_ref and card_last_4:
                    existing_account.account_number_ref = card_last_4
                session.commit()
                return existing_account.account_id
            else:
                # Create new credit card account
                logger.info("Creating new credit card account")
                new_account_id = str(uuid.uuid4())
                
                account_name = customer_name or f"{bank_name} Credit Card"
                
                new_account = Account(
                    account_id=new_account_id,
                    user_id=user_id,
                    account_name=account_name,
                    bank_name=bank_name,
                    account_type='credit_card',
                    account_number_ref=card_last_4,
                    currency='INR',
                    current_balance=0.0,
                    is_active=True
                )
                
                session.add(new_account)
                session.commit()
                session.refresh(new_account)
                
                logger.info(f"Created credit card account: {new_account_id}")
                return new_account_id
                
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating/updating credit card account: {e}", exc_info=True)
            return None
        finally:
            session.close()
    
    def create_credit_card_statement_record(
        self,
        user_id: str,
        account_id: str,
        metadata: Dict,
        filename: str,
        source_type: str
    ) -> Optional[str]:
        """
        Create credit card statement record
        
        Args:
            user_id: User ID
            account_id: Account ID
            metadata: Statement metadata
            filename: Source filename
            source_type: 'csv', 'pdf', or 'manual'
            
        Returns:
            Statement ID if created, None otherwise
        """
        session = self.db_manager.get_session()
        
        try:
            statement_id = str(uuid.uuid4())
            
            # Extract statement dates from metadata if available
            statement_start = metadata.get('statement_start_date')
            statement_end = metadata.get('statement_end_date')
            billing_period = metadata.get('billing_period')
            
            # Try to infer from transactions if not in metadata
            if not (statement_start and statement_end):
                first_txn = session.query(Transaction).filter(
                    Transaction.user_id == user_id,
                    Transaction.account_id == account_id
                ).order_by(Transaction.date.asc()).first()
                
                last_txn = session.query(Transaction).filter(
                    Transaction.user_id == user_id,
                    Transaction.account_id == account_id
                ).order_by(Transaction.date.desc()).first()
                
                if first_txn and last_txn:
                    statement_start = first_txn.date
                    statement_end = last_txn.date
            
            new_statement = CreditCardStatement(
                statement_id=statement_id,
                user_id=user_id,
                account_id=account_id,
                bank_name=metadata.get('bank_name', 'Unknown'),
                card_number_masked=metadata.get('card_number'),
                card_last_4_digits=metadata.get('card_last_4_digits'),
                customer_name=metadata.get('customer_name'),
                statement_start_date=statement_start,
                statement_end_date=statement_end,
                billing_period=billing_period,
                total_transactions=metadata.get('transaction_count', 0),
                source_file=filename,
                source_type=source_type,
                is_processed=True,
                processing_status='completed',
                extra_metadata={
                    'card_holder_address': metadata.get('card_holder_address'),
                    'rewards_info': metadata.get('rewards_info')
                },
                transactions_processed=metadata.get('transaction_count', 0)
            )
            
            session.add(new_statement)
            session.commit()
            session.refresh(new_statement)
            
            logger.info(f"Created credit card statement record: {statement_id}")
            return statement_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating credit card statement: {e}", exc_info=True)
            return None
        finally:
            session.close()
    
    def get_credit_card_statements(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get user's credit card statements
        
        Args:
            user_id: User ID
            limit: Maximum number of statements to return
            
        Returns:
            List of statement dictionaries
        """
        session = self.db_manager.get_session()
        
        try:
            statements = session.query(CreditCardStatement).filter(
                CreditCardStatement.user_id == user_id
            ).order_by(
                CreditCardStatement.created_at.desc()
            ).limit(limit).all()
            
            return [stmt.to_dict() for stmt in statements]
            
        except Exception as e:
            logger.error(f"Error fetching credit card statements: {e}", exc_info=True)
            return []
        finally:
            session.close()
    
    def get_credit_card_accounts(
        self,
        user_id: str
    ) -> List[Dict]:
        """
        Get user's credit card accounts
        
        Args:
            user_id: User ID
            
        Returns:
            List of account dictionaries
        """
        session = self.db_manager.get_session()
        
        try:
            accounts = session.query(Account).filter(
                Account.user_id == user_id,
                Account.account_type == 'credit_card'
            ).order_by(Account.created_at.desc()).all()
            
            return [acc.to_dict() for acc in accounts]
            
        except Exception as e:
            logger.error(f"Error fetching credit card accounts: {e}", exc_info=True)
            return []
        finally:
            session.close()
    
    def get_credit_card_payments_summary(
        self,
        user_id: str,
        financial_year: Optional[str] = None
    ) -> Dict:
        """
        Get summary of credit card payments across all cards
        
        Aggregates all "Credit Card Payment" category transactions:
        - By individual card (last 4 digits)
        - By bank
        - By financial year
        
        Args:
            user_id: User ID
            financial_year: Optional financial year (e.g., "2024-25")
            
        Returns:
            Dictionary with aggregated payment data
        """
        session = self.db_manager.get_session()
        
        try:
            # Query all Credit Card Payment transactions
            query = session.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.category == 'Credit Card Payment',
                Transaction.type == TransactionType.CREDIT  # Only payments (credits)
            )
            
            transactions = query.order_by(Transaction.date.desc()).all()
            
            # Group by card, bank, and financial year
            from collections import defaultdict
            by_card = defaultdict(float)
            by_bank = defaultdict(float)
            by_fy = defaultdict(float)
            total_payments = 0.0
            
            for txn in transactions:
                # Extract card last 4 from extra_metadata
                card_last_4 = "Unknown"
                if txn.extra_metadata:
                    card_last_4 = txn.extra_metadata.get('card_last_4', 'Unknown')
                
                # Determine financial year (Apr-Mar)
                txn_date = datetime.strptime(txn.date, '%Y-%m-%d')
                if txn_date.month >= 4:
                    fy = f"{txn_date.year}-{txn_date.year + 1}"
                else:
                    fy = f"{txn_date.year - 1}-{txn_date.year}"
                
                # Apply financial year filter if specified
                if financial_year and fy != financial_year:
                    continue
                
                # Aggregate
                by_card[card_last_4] += txn.amount
                by_bank[txn.bank_name or 'Unknown'] += txn.amount
                by_fy[fy] += txn.amount
                total_payments += txn.amount
            
            return {
                'total_payments': total_payments,
                'by_card': dict(by_card),
                'by_bank': dict(by_bank),
                'by_financial_year': dict(by_fy),
                'total_transactions': len(transactions),
                'financial_year_filter': financial_year
            }
            
        except Exception as e:
            logger.error(f"Error fetching credit card payments summary: {e}", exc_info=True)
            return {
                'total_payments': 0.0,
                'by_card': {},
                'by_bank': {},
                'by_financial_year': {},
                'total_transactions': 0,
                'financial_year_filter': financial_year
            }
        finally:
            session.close()

