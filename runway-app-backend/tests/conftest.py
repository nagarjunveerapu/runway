"""
Pytest configuration and shared fixtures for all tests

This file provides common test fixtures, mock data, and utilities
that are shared across all test files in the test suite.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import uuid

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_user_id():
    """Sample user ID for testing"""
    return "test-user-123"


@pytest.fixture
def sample_account_id():
    """Sample account ID for testing"""
    return "test-account-123"


@pytest.fixture
def sample_transaction_id():
    """Sample transaction ID for testing"""
    return str(uuid.uuid4())


@pytest.fixture
def sample_date():
    """Sample date string in ISO format"""
    return "2024-01-01"


@pytest.fixture
def sample_dates():
    """List of sample dates for testing"""
    base_date = datetime(2024, 1, 1)
    return [
        (base_date + timedelta(days=i*30)).strftime('%Y-%m-%d')
        for i in range(6)
    ]


@pytest.fixture
def sample_user_data():
    """Sample user registration data"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPassword123"
    }


@pytest.fixture
def sample_account_data():
    """Sample account creation data"""
    return {
        "account_name": "Salary Account",
        "bank_name": "HDFC Bank",
        "account_type": "savings",
        "account_number": "1234567890",
        "currency": "INR"
    }


@pytest.fixture
def sample_transaction_data():
    """Sample transaction data"""
    return {
        "transaction_id": str(uuid.uuid4()),
        "user_id": "test-user-123",
        "date": "2024-01-01",
        "amount": 5000.0,
        "type": "debit",
        "description_raw": "SWIGGY BANGALORE",
        "clean_description": "SWIGGY BANGALORE",
        "merchant_canonical": "Swiggy",
        "merchant_raw": "Swiggy",
        "category": "Food & Dining",
        "balance": 10000.0
    }


@pytest.fixture
def sample_investment_transaction_data():
    """Sample investment transaction data"""
    return {
        "transaction_id": str(uuid.uuid4()),
        "user_id": "test-user-123",
        "date": "2024-01-01",
        "amount": 5000.0,
        "type": "debit",
        "description_raw": "SIP payment to Zerodha",
        "clean_description": "SIP payment",
        "merchant_canonical": "Zerodha",
        "merchant_raw": "Zerodha Securities",
        "category": "Investment"
    }


@pytest.fixture
def sample_emi_transaction_data():
    """Sample EMI/loan transaction data"""
    return {
        "transaction_id": str(uuid.uuid4()),
        "user_id": "test-user-123",
        "date": "2024-01-01",
        "amount": 50000.0,
        "type": "debit",
        "description_raw": "HDFC Home Loan EMI",
        "clean_description": "Home Loan EMI",
        "merchant_canonical": "HDFC Home Loan",
        "merchant_raw": "HDFC Bank",
        "category": "EMI & Loans",
        "balance": 500000.0
    }


@pytest.fixture
def sample_salary_transaction_data():
    """Sample salary/credit transaction data"""
    return {
        "transaction_id": str(uuid.uuid4()),
        "user_id": "test-user-123",
        "date": "2024-01-01",
        "amount": 100000.0,
        "type": "credit",
        "description_raw": "SALARY CREDIT",
        "clean_description": "SALARY CREDIT",
        "merchant_canonical": "Company Salary",
        "merchant_raw": "Company Name",
        "category": "Salary",
        "balance": 150000.0
    }


@pytest.fixture
def sample_transactions_list(sample_transaction_data):
    """List of sample transactions"""
    transactions = []
    base_date = datetime(2024, 1, 1)
    
    for i in range(5):
        txn = sample_transaction_data.copy()
        txn["transaction_id"] = str(uuid.uuid4())
        txn["date"] = (base_date + timedelta(days=i*30)).strftime('%Y-%m-%d')
        txn["amount"] = 5000.0 + (i * 100)
        transactions.append(txn)
    
    return transactions


@pytest.fixture
def sample_investment_transactions_list(sample_investment_transaction_data):
    """List of sample investment transactions"""
    transactions = []
    base_date = datetime(2024, 1, 1)
    
    for i in range(6):
        txn = sample_investment_transaction_data.copy()
        txn["transaction_id"] = str(uuid.uuid4())
        txn["date"] = (base_date + timedelta(days=i*30)).strftime('%Y-%m-%d')
        txn["amount"] = 5000.0  # Same amount for SIP
        transactions.append(txn)
    
    return transactions


@pytest.fixture
def sample_emi_transactions_list(sample_emi_transaction_data):
    """List of sample EMI transactions"""
    transactions = []
    base_date = datetime(2024, 1, 1)
    
    for i in range(6):
        txn = sample_emi_transaction_data.copy()
        txn["transaction_id"] = str(uuid.uuid4())
        txn["date"] = (base_date + timedelta(days=i*30)).strftime('%Y-%m-%d')
        txn["amount"] = 50000.0  # Same amount for EMI
        transactions.append(txn)
    
    return transactions


# ============================================================================
# Mock Database Fixtures
# ============================================================================

@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = MagicMock()
    return session


@pytest.fixture
def mock_database_manager(mock_db_session):
    """Mock DatabaseManager"""
    db_manager = MagicMock()
    db_manager.get_session.return_value = mock_db_session
    db_manager.close.return_value = None
    return db_manager


@pytest.fixture
def mock_user():
    """Mock User object"""
    user = Mock()
    user.user_id = "test-user-123"
    user.username = "testuser"
    user.email = "test@example.com"
    user.is_active = True
    user.created_at = datetime.now()
    return user


@pytest.fixture
def mock_transaction():
    """Mock Transaction object"""
    txn = Mock()
    txn.transaction_id = str(uuid.uuid4())
    txn.user_id = "test-user-123"
    txn.date = "2024-01-01"
    txn.amount = 5000.0
    txn.type = "debit"
    txn.description_raw = "SWIGGY BANGALORE"
    txn.clean_description = "SWIGGY BANGALORE"
    txn.merchant_canonical = "Swiggy"
    txn.merchant_raw = "Swiggy"
    txn.category = "Food & Dining"
    txn.balance = 10000.0
    return txn


@pytest.fixture
def mock_investment_transaction():
    """Mock investment Transaction object"""
    txn = Mock()
    txn.transaction_id = str(uuid.uuid4())
    txn.user_id = "test-user-123"
    txn.date = "2024-01-01"
    txn.amount = 5000.0
    txn.type = "debit"
    txn.description_raw = "SIP payment to Zerodha"
    txn.clean_description = "SIP payment"
    txn.merchant_canonical = "Zerodha"
    txn.merchant_raw = "Zerodha Securities"
    txn.category = "Investment"
    return txn


@pytest.fixture
def mock_account():
    """Mock Account object"""
    account = Mock()
    account.account_id = "test-account-123"
    account.user_id = "test-user-123"
    account.account_name = "Salary Account"
    account.bank_name = "HDFC Bank"
    account.account_type = "savings"
    account.currency = "INR"
    account.is_active = True
    account.created_at = datetime.now()
    return account


@pytest.fixture
def mock_asset():
    """Mock Asset object"""
    asset = Mock()
    asset.asset_id = str(uuid.uuid4())
    asset.user_id = "test-user-123"
    asset.name = "Home"
    asset.asset_type = "property"
    asset.current_value = 5000000.0
    asset.purchase_price = 4000000.0
    asset.liquid = False
    asset.disposed = False
    return asset


@pytest.fixture
def mock_liability():
    """Mock Liability object"""
    liability = Mock()
    liability.liability_id = str(uuid.uuid4())
    liability.user_id = "test-user-123"
    liability.name = "Home Loan"
    liability.liability_type = "loan"
    liability.outstanding_balance = 2000000.0
    liability.emi_amount = 50000.0
    liability.interest_rate = 8.5
    return liability


# ============================================================================
# Test Data Generators
# ============================================================================

@pytest.fixture
def generate_transactions():
    """Helper function to generate multiple transactions"""
    def _generate(count: int, base_date: datetime = datetime(2024, 1, 1), 
                  base_amount: float = 5000.0, txn_type: str = "debit"):
        transactions = []
        for i in range(count):
            txn = Mock()
            txn.transaction_id = str(uuid.uuid4())
            txn.user_id = "test-user-123"
            txn.date = (base_date + timedelta(days=i*30)).strftime('%Y-%m-%d')
            txn.amount = base_amount
            txn.type = txn_type
            txn.description_raw = f"Transaction {i+1}"
            txn.clean_description = f"Transaction {i+1}"
            txn.merchant_canonical = f"Merchant {i+1}"
            txn.merchant_raw = f"Merchant {i+1}"
            txn.category = "Unknown"
            transactions.append(txn)
        return transactions
    return _generate


@pytest.fixture
def generate_investment_transactions():
    """Helper function to generate investment transactions"""
    def _generate(count: int, platform: str = "Zerodha", 
                  base_amount: float = 5000.0):
        transactions = []
        base_date = datetime(2024, 1, 1)
        for i in range(count):
            txn = Mock()
            txn.transaction_id = str(uuid.uuid4())
            txn.user_id = "test-user-123"
            txn.date = (base_date + timedelta(days=i*30)).strftime('%Y-%m-%d')
            txn.amount = base_amount
            txn.type = "debit"
            txn.description_raw = f"SIP payment to {platform}"
            txn.clean_description = f"SIP payment"
            txn.merchant_canonical = platform
            txn.merchant_raw = f"{platform} Securities"
            txn.category = "Investment"
            transactions.append(txn)
        return transactions
    return _generate


# ============================================================================
# Common Test Utilities
# ============================================================================

@pytest.fixture
def sample_bank_names():
    """List of common bank names for testing"""
    return [
        "HDFC Bank",
        "ICICI Bank",
        "SBI Bank",
        "Axis Bank",
        "Kotak Mahindra Bank"
    ]


@pytest.fixture
def sample_merchants():
    """List of common merchant names for testing"""
    return [
        "Swiggy",
        "Zomato",
        "Amazon",
        "Flipkart",
        "Uber",
        "Ola",
        "Netflix",
        "Zerodha",
        "Groww"
    ]


@pytest.fixture
def sample_categories():
    """List of common transaction categories"""
    return [
        "Food & Dining",
        "Shopping",
        "Transport",
        "Entertainment",
        "Bills & Utilities",
        "Investment",
        "EMI & Loans",
        "Salary",
        "Transfer"
    ]


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (may use database)"
    )
    config.addinivalue_line(
        "markers", "slow: Slow running tests"
    )


# ============================================================================
# CSV/PDF Test Data
# ============================================================================

@pytest.fixture
def sample_csv_data():
    """Sample CSV data for testing parsers"""
    return """Date,Description,Debit,Credit,Balance
01/01/2024,SWIGGY BANGALORE,450.00,,12500.00
02/01/2024,SALARY CREDIT,,50000.00,62500.00
03/01/2024,AMAZON PURCHASE,2000.00,,60500.00"""


@pytest.fixture
def sample_pdf_text():
    """Sample PDF text content for testing"""
    return """01/01/2024 SWIGGY BANGALORE 450.00 12500.00
02/01/2024 SALARY CREDIT 50000.00 62500.00
03/01/2024 AMAZON PURCHASE 2000.00 60500.00"""


@pytest.fixture
def sample_raw_transaction_dicts():
    """Sample raw transaction dictionaries from parsers"""
    return [
        {
            'date': '01/01/2024',
            'description': 'SWIGGY BANGALORE',
            'amount': 450.00,
            'type': 'debit',
            'balance': 12500.00
        },
        {
            'date': '02/01/2024',
            'description': 'SALARY CREDIT',
            'amount': 50000.00,
            'type': 'credit',
            'balance': 62500.00
        }
    ]


# ============================================================================
# Investment Test Data
# ============================================================================

@pytest.fixture
def sample_sip_patterns():
    """Sample SIP pattern data"""
    return [
        {
            "sip_id": "sip_zerodha_5000",
            "platform": "Zerodha",
            "amount": 5000.0,
            "frequency": "monthly",
            "transaction_count": 12,
            "total_invested": 60000.0,
            "start_date": "2024-01-01",
            "last_transaction_date": "2024-12-01",
            "category": "equity"
        },
        {
            "sip_id": "sip_groww_3000",
            "platform": "Groww",
            "amount": 3000.0,
            "frequency": "monthly",
            "transaction_count": 6,
            "total_invested": 18000.0,
            "start_date": "2024-06-01",
            "last_transaction_date": "2024-11-01",
            "category": "equity"
        }
    ]


@pytest.fixture
def sample_loan_data():
    """Sample loan/EMI data"""
    return {
        "loan_id": "loan-123",
        "name": "Home Loan",
        "source": "HDFC",
        "emi": 50000.0,
        "remaining_principal": 3000000.0,
        "interest_rate": 8.5,
        "remaining_tenure_months": 120
    }


# ============================================================================
# Dashboard Test Data
# ============================================================================

@pytest.fixture
def sample_monthly_metrics():
    """Sample monthly metrics data"""
    return {
        "month": "2024-01",
        "income": 100000.0,
        "expenses": 70000.0,
        "net_savings": 30000.0,
        "savings_rate": 30.0,
        "emi_payments": 20000.0,
        "transaction_count": 50
    }


@pytest.fixture
def sample_asset_summary():
    """Sample asset summary data"""
    return {
        "total_value": 5000000.0,
        "count": 3,
        "top_assets": [
            {"name": "Home", "type": "property", "value": 4000000.0},
            {"name": "Car", "type": "vehicle", "value": 800000.0},
            {"name": "Savings", "type": "other", "value": 200000.0}
        ]
    }


@pytest.fixture
def sample_liability_summary():
    """Sample liability summary data"""
    return {
        "total_outstanding": 2000000.0,
        "total_monthly_payments": 50000.0,
        "count": 2,
        "top_liabilities": [
            {"name": "Home Loan", "type": "loan", "outstanding_balance": 1500000.0},
            {"name": "Car Loan", "type": "loan", "outstanding_balance": 500000.0}
        ]
    }

