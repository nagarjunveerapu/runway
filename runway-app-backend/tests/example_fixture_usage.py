"""
Example test file demonstrating how to use shared fixtures from conftest.py

This file serves as a reference for using the shared test fixtures
across all test files in the test suite.
"""

import pytest
from datetime import datetime


# ============================================================================
# Example: Using Basic Fixtures
# ============================================================================

def test_using_basic_fixtures(sample_user_id, sample_account_id, sample_date):
    """Example of using basic ID and date fixtures"""
    assert sample_user_id == "test-user-123"
    assert sample_account_id == "test-account-123"
    assert sample_date == "2024-01-01"


# ============================================================================
# Example: Using Data Fixtures
# ============================================================================

def test_using_account_data_fixture(sample_account_data):
    """Example of using account data fixture"""
    assert sample_account_data["account_name"] == "Salary Account"
    assert sample_account_data["bank_name"] == "HDFC Bank"
    assert sample_account_data["account_type"] == "savings"


def test_using_transaction_data_fixture(sample_transaction_data):
    """Example of using transaction data fixture"""
    assert sample_transaction_data["type"] == "debit"
    assert sample_transaction_data["amount"] == 5000.0
    assert "SWIGGY" in sample_transaction_data["description_raw"]


def test_using_investment_data_fixture(sample_investment_transaction_data):
    """Example of using investment transaction fixture"""
    assert sample_investment_transaction_data["merchant_canonical"] == "Zerodha"
    assert sample_investment_transaction_data["type"] == "debit"


# ============================================================================
# Example: Using List Fixtures
# ============================================================================

def test_using_transactions_list(sample_transactions_list):
    """Example of using transactions list fixture"""
    assert len(sample_transactions_list) == 5
    assert all(txn["type"] == "debit" for txn in sample_transactions_list)


def test_using_investment_transactions_list(sample_investment_transactions_list):
    """Example of using investment transactions list fixture"""
    assert len(sample_investment_transactions_list) == 6
    # All should have same amount for SIP pattern
    amounts = [txn["amount"] for txn in sample_investment_transactions_list]
    assert all(amt == 5000.0 for amt in amounts)


# ============================================================================
# Example: Using Mock Fixtures
# ============================================================================

def test_using_mock_transaction(mock_transaction):
    """Example of using mock transaction fixture"""
    assert mock_transaction.type == "debit"
    assert mock_transaction.amount == 5000.0
    assert mock_transaction.merchant_canonical == "Swiggy"


def test_using_mock_user(mock_user):
    """Example of using mock user fixture"""
    assert mock_user.username == "testuser"
    assert mock_user.is_active is True


def test_using_mock_account(mock_account):
    """Example of using mock account fixture"""
    assert mock_account.account_type == "savings"
    assert mock_account.is_active is True


# ============================================================================
# Example: Using Database Mock Fixtures
# ============================================================================

def test_using_mock_database(mock_database_manager, mock_db_session):
    """Example of using mock database fixtures"""
    session = mock_database_manager.get_session()
    assert session == mock_db_session
    
    # Verify session was retrieved
    mock_database_manager.get_session.assert_called_once()


# ============================================================================
# Example: Using Generator Fixtures
# ============================================================================

def test_using_transaction_generator(generate_transactions):
    """Example of using transaction generator fixture"""
    transactions = generate_transactions(count=3, base_amount=1000.0)
    
    assert len(transactions) == 3
    assert all(txn.amount == 1000.0 for txn in transactions)


def test_using_investment_generator(generate_investment_transactions):
    """Example of using investment transaction generator"""
    transactions = generate_investment_transactions(
        count=5,
        platform="Groww",
        base_amount=3000.0
    )
    
    assert len(transactions) == 5
    assert all(txn.merchant_canonical == "Groww" for txn in transactions)


# ============================================================================
# Example: Using Utility Fixtures
# ============================================================================

def test_using_bank_names_fixture(sample_bank_names):
    """Example of using bank names fixture"""
    assert "HDFC Bank" in sample_bank_names
    assert "ICICI Bank" in sample_bank_names
    assert len(sample_bank_names) == 5


def test_using_merchants_fixture(sample_merchants):
    """Example of using merchants fixture"""
    assert "Swiggy" in sample_merchants
    assert "Zerodha" in sample_merchants


def test_using_categories_fixture(sample_categories):
    """Example of using categories fixture"""
    assert "Food & Dining" in sample_categories
    assert "Investment" in sample_categories


# ============================================================================
# Example: Using Combined Fixtures
# ============================================================================

def test_combined_fixtures(sample_user_id, sample_account_data, mock_transaction):
    """Example of combining multiple fixtures in one test"""
    # Use user_id fixture
    assert sample_user_id == "test-user-123"
    
    # Use account_data fixture
    account_name = sample_account_data["account_name"]
    assert account_name == "Salary Account"
    
    # Use mock_transaction fixture
    assert mock_transaction.user_id == sample_user_id


# ============================================================================
# Example: Using Parser Test Data Fixtures
# ============================================================================

def test_using_csv_data_fixture(sample_csv_data):
    """Example of using CSV data fixture"""
    lines = sample_csv_data.split('\n')
    assert len(lines) > 0
    assert "SWIGGY" in sample_csv_data


def test_using_raw_transaction_dicts(sample_raw_transaction_dicts):
    """Example of using raw transaction dictionaries fixture"""
    assert len(sample_raw_transaction_dicts) == 2
    assert sample_raw_transaction_dicts[0]["type"] == "debit"
    assert sample_raw_transaction_dicts[1]["type"] == "credit"


# ============================================================================
# Example: Using Investment Data Fixtures
# ============================================================================

def test_using_sip_patterns_fixture(sample_sip_patterns):
    """Example of using SIP patterns fixture"""
    assert len(sample_sip_patterns) == 2
    assert sample_sip_patterns[0]["platform"] == "Zerodha"
    assert sample_sip_patterns[0]["frequency"] == "monthly"


def test_using_loan_data_fixture(sample_loan_data):
    """Example of using loan data fixture"""
    assert sample_loan_data["emi"] == 50000.0
    assert sample_loan_data["interest_rate"] == 8.5


# ============================================================================
# Example: Using Dashboard Data Fixtures
# ============================================================================

def test_using_monthly_metrics_fixture(sample_monthly_metrics):
    """Example of using monthly metrics fixture"""
    assert sample_monthly_metrics["income"] == 100000.0
    assert sample_monthly_metrics["savings_rate"] == 30.0


def test_using_asset_summary_fixture(sample_asset_summary):
    """Example of using asset summary fixture"""
    assert sample_asset_summary["total_value"] == 5000000.0
    assert len(sample_asset_summary["top_assets"]) == 3


def test_using_liability_summary_fixture(sample_liability_summary):
    """Example of using liability summary fixture"""
    assert sample_liability_summary["total_outstanding"] == 2000000.0
    assert sample_liability_summary["count"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

