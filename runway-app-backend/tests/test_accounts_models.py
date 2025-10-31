"""
Unit tests for Accounts route models

Run with: pytest tests/test_accounts_models.py -v
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.routes.accounts import AccountCreate, AccountResponse


class TestAccountCreate:
    """Test suite for AccountCreate model"""
    
    def test_account_create_valid_data(self, sample_account_data):
        """Test AccountCreate with valid data using shared fixture"""
        account = AccountCreate(**sample_account_data)
        assert account.account_name == sample_account_data["account_name"]
        assert account.bank_name == sample_account_data["bank_name"]
        assert account.account_type == sample_account_data["account_type"]
    
    def test_account_create_with_fixture(self, sample_account_id, sample_bank_names):
        """Test AccountCreate using multiple fixtures"""
        # Use fixtures from conftest.py
        account = AccountCreate(
            account_name="Test Account",
            bank_name=sample_bank_names[0],  # Use fixture data
            account_type="savings"
        )
        assert account.bank_name in sample_bank_names
        assert account.account_type == "savings"
    
    def test_account_create_defaults(self):
        """Test AccountCreate with default values"""
        account = AccountCreate(
            account_name="Test Account",
            bank_name="Test Bank"
        )
        assert account.account_type == "savings"
        assert account.currency == "INR"
        assert account.account_number is None


class TestAccountResponse:
    """Test suite for AccountResponse model"""
    
    def test_account_response_valid_data(self, sample_account_id, sample_user_id, sample_account_data):
        """Test AccountResponse with valid data using shared fixtures"""
        response = AccountResponse(
            account_id=sample_account_id,
            user_id=sample_user_id,
            account_name=sample_account_data["account_name"],
            bank_name=sample_account_data["bank_name"],
            account_type=sample_account_data["account_type"],
            currency=sample_account_data["currency"],
            is_active=True,
            created_at="2024-01-01T00:00:00"
        )
        assert response.account_id == sample_account_id
        assert response.user_id == sample_user_id
        assert response.is_active is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

