"""
Unit tests for TransactionRepository

Run with: pytest tests/test_transaction_repository.py -v
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import uuid
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.parser_service.transaction_repository import TransactionRepository
from storage.database import DatabaseManager
from storage.models import Transaction


class TestTransactionRepository:
    """Test suite for TransactionRepository"""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Mock DatabaseManager"""
        db_manager = MagicMock(spec=DatabaseManager)
        mock_session = MagicMock()
        db_manager.get_session.return_value = mock_session
        return db_manager, mock_session
    
    def test_repository_initialization(self, mock_db_manager):
        """Test TransactionRepository initialization"""
        db_manager, _ = mock_db_manager
        repository = TransactionRepository(db_manager)
        assert repository.db_manager == db_manager
    
    def test_insert_transaction_success(self, mock_db_manager):
        """Test inserting a single transaction"""
        db_manager, mock_session = mock_db_manager
        
        repository = TransactionRepository(db_manager)
        txn_dict = {
            'date': '2024-01-01',
            'amount': 5000.0,
            'type': 'debit',
            'description': 'SWIGGY',
            'merchant_canonical': 'Swiggy',
            'category': 'Food & Dining'
        }
        
        mock_transaction = Mock(spec=Transaction)
        mock_transaction.transaction_id = str(uuid.uuid4())
        mock_session.add.return_value = None
        mock_session.commit.return_value = None
        mock_session.refresh.return_value = None
        
        with patch('services.parser_service.transaction_repository.Transaction') as mock_txn_class:
            mock_txn_class.return_value = mock_transaction
            result = repository.insert_transaction(
                txn_dict,
                user_id="test-user-123"
            )
            
            assert mock_session.add.called
            assert mock_session.commit.called
    
    def test_insert_transaction_with_existing_session(self, mock_db_manager):
        """Test inserting transaction with existing session"""
        db_manager, mock_session = mock_db_manager
        
        repository = TransactionRepository(db_manager)
        txn_dict = {
            'date': '2024-01-01',
            'amount': 5000.0,
            'type': 'debit',
            'description': 'SWIGGY'
        }
        
        with patch('services.parser_service.transaction_repository.Transaction'):
            # Should not close session if provided
            result = repository.insert_transaction(
                txn_dict,
                user_id="test-user-123",
                session=mock_session
            )
            
            # Should not call get_session if session is provided
            assert db_manager.get_session.call_count == 0
    
    def test_insert_transaction_handles_different_field_names(self, mock_db_manager):
        """Test that repository handles different field names from parsers"""
        db_manager, mock_session = mock_db_manager
        
        repository = TransactionRepository(db_manager)
        
        # Test with PDF parser format
        txn_dict_pdf = {
            'date': '2024-01-01',
            'amount': 5000.0,
            'type': 'debit',
            'description': 'SWIGGY'
        }
        
        # Test with CSV parser format
        txn_dict_csv = {
            'date': '2024-01-01',
            'amount': 5000.0,
            'transaction_type': 'debit',
            'remark': 'SWIGGY',
            'raw_remark': 'SWIGGY BANGALORE'
        }
        
        with patch('services.parser_service.transaction_repository.Transaction'):
            # Both should work
            repository.insert_transaction(txn_dict_pdf, "test-user-123", session=mock_session)
            repository.insert_transaction(txn_dict_csv, "test-user-123", session=mock_session)
            
            # Should have been added twice
            assert mock_session.add.call_count == 2
    
    def test_insert_transactions_batch(self, mock_db_manager):
        """Test inserting multiple transactions in batch"""
        db_manager, mock_session = mock_db_manager
        
        repository = TransactionRepository(db_manager)
        
        transactions = [
            {'date': '2024-01-01', 'amount': 1000.0, 'type': 'debit', 'description': 'Txn 1'},
            {'date': '2024-01-02', 'amount': 2000.0, 'type': 'debit', 'description': 'Txn 2'},
            {'date': '2024-01-03', 'amount': 3000.0, 'type': 'credit', 'description': 'Txn 3'}
        ]
        
        with patch.object(repository, 'insert_transaction') as mock_insert:
            mock_insert.return_value = Mock(spec=Transaction)
            
            result = repository.insert_transactions_batch(
                transactions,
                user_id="test-user-123",
                batch_size=2
            )
            
            # Should insert all transactions
            assert mock_insert.call_count == 3
            # Should commit in batches (2 + 1 = 2 commits)
            assert mock_session.commit.call_count >= 1
    
    def test_insert_transactions_batch_handles_errors(self, mock_db_manager):
        """Test that batch insert handles errors gracefully"""
        db_manager, mock_session = mock_db_manager
        
        repository = TransactionRepository(db_manager)
        
        transactions = [
            {'date': '2024-01-01', 'amount': 1000.0, 'type': 'debit', 'description': 'Txn 1'},
            {'date': 'invalid', 'amount': 'invalid', 'type': 'debit'},  # Invalid transaction
            {'date': '2024-01-03', 'amount': 3000.0, 'type': 'credit', 'description': 'Txn 3'}
        ]
        
        with patch.object(repository, 'insert_transaction') as mock_insert:
            # First succeeds, second fails, third succeeds
            mock_insert.side_effect = [
                Mock(spec=Transaction),
                Exception("Invalid data"),
                Mock(spec=Transaction)
            ]
            
            result = repository.insert_transactions_batch(
                transactions,
                user_id="test-user-123"
            )
            
            # Should insert 2 out of 3 transactions
            assert result == 2
    
    def test_insert_from_canonical(self, mock_db_manager):
        """Test inserting from CanonicalTransaction objects"""
        from schema import CanonicalTransaction
        
        db_manager, mock_session = mock_db_manager
        
        repository = TransactionRepository(db_manager)
        
        canonical_txns = [
            CanonicalTransaction(
                transaction_id=str(uuid.uuid4()),
                date='2024-01-01',
                amount=5000.0,
                type='debit',
                description_raw='SWIGGY',
                clean_description='SWIGGY',
                source='csv_upload'
            )
        ]
        
        with patch.object(repository, 'insert_transactions_batch') as mock_batch:
            mock_batch.return_value = 1
            
            result = repository.insert_from_canonical(
                canonical_txns,
                user_id="test-user-123"
            )
            
            # Should convert and insert
            assert mock_batch.called
            call_args = mock_batch.call_args[0]
            assert len(call_args[0]) == 1  # One transaction dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

