#!/usr/bin/env python3
"""
Load sample financial data into the database for testing.

This script loads the sample data and properly categorizes it for the dashboard:
- Assets (investments) from investment transactions
- EMIs (loans) from EMI transactions
- Income and expenses
"""

import sys
from pathlib import Path
import uuid
from datetime import datetime
import json

sys.path.insert(0, str(Path(__file__).parent))

from storage.database import DatabaseManager
from storage.models import Transaction, Asset, User
from auth.password import hash_password
from config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample data
SAMPLE_DATA = {
    "transactions": [
        {"id": "T20250101-1", "date": "2025-01-01", "category": "Salary-Primary", "amount": 120000, "notes": "Salary Jan", "user_forced_type": "income"},
        {"id": "T20250105-1", "date": "2025-01-05", "category": "Investments-SIP: Motilal Oswal Midcap", "amount": 5000, "notes": "SIP Jan", "user_forced_type": "investment"},
        {"id": "T20250107-1", "date": "2025-01-07", "category": "Groceries", "amount": 3200, "notes": "Groceries", "user_forced_type": "expense"},
        {"id": "T20250110-1", "date": "2025-01-10", "category": "EMI-Home Loan", "amount": 25000, "notes": "Home loan EMI", "user_forced_type": "emi"},
        {"id": "T20250201-1", "date": "2025-02-01", "category": "Salary-Primary", "amount": 120000, "notes": "Salary Feb", "user_forced_type": "income"},
        {"id": "T20250205-1", "date": "2025-02-05", "category": "Investments-SIP: Motilal Oswal Midcap", "amount": 5000, "notes": "SIP Feb", "user_forced_type": "investment"},
        {"id": "T20250208-1", "date": "2025-02-08", "category": "Dining Out", "amount": 1200, "notes": "Dinner", "user_forced_type": "expense"},
        {"id": "T20250215-1", "date": "2025-02-15", "category": "EMI-Home Loan", "amount": 25000, "notes": "Home loan EMI", "user_forced_type": "emi"},
        {"id": "T20250301-1", "date": "2025-03-01", "category": "Salary-Primary", "amount": 120000, "notes": "Salary Mar", "user_forced_type": "income"},
        {"id": "T20250310-1", "date": "2025-03-10", "category": "EMI-Home Loan", "amount": 25000, "notes": "Home loan EMI", "user_forced_type": "emi"}
    ],
    "assets": [
        {"id": "A001", "name": "Savings Account", "type": "Bank Account", "quantity": 1, "purchase_value": 200000, "current_value": 200000, "liquid": True},
        {"id": "A002", "name": "Motilal Oswal Midcap", "type": "Mutual Fund", "quantity": 100, "purchase_value": 100000, "current_value": 120000, "liquid": True},
        {"id": "A003", "name": "Home - Chennai", "type": "Property", "quantity": 1, "purchase_value": 4500000, "current_value": 6000000, "liquid": False},
        {"id": "A004", "name": "Fixed Deposit", "type": "Fixed Deposit", "quantity": 1, "purchase_value": 500000, "current_value": 515000, "liquid": False}
    ]
}


def format_month(date_str):
    """Extract YYYY-MM from date string"""
    return date_str[:7] if len(date_str) >= 7 else date_str


def load_data_to_db(user_id):
    """Load sample data for a user"""
    db = DatabaseManager(Config.DATABASE_URL)
    session = db.get_session()
    
    try:
        # Load transactions
        for txn_data in SAMPLE_DATA["transactions"]:
            transaction = Transaction(
                transaction_id=txn_data["id"],
                user_id=user_id,
                date=txn_data["date"],
                amount=abs(txn_data["amount"]),
                type="credit" if txn_data["user_forced_type"] == "income" else "debit",
                description_raw=txn_data["notes"],
                merchant_canonical=txn_data.get("category", ""),
                category=txn_data["category"],
                month=format_month(txn_data["date"]),
                source="manual"
            )
            session.add(transaction)
        
        # Load assets
        for asset_data in SAMPLE_DATA["assets"]:
            asset = Asset(
                asset_id=asset_data["id"],
                user_id=user_id,
                name=asset_data["name"],
                asset_type=asset_data["type"],
                quantity=asset_data.get("quantity", 1),
                purchase_price=asset_data.get("purchase_value", 0),
                current_value=asset_data.get("current_value", 0),
                liquid=asset_data.get("liquid", False)
            )
            session.add(asset)
        
        session.commit()
        logger.info(f"✅ Loaded {len(SAMPLE_DATA['transactions'])} transactions and {len(SAMPLE_DATA['assets'])} assets")
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Error loading data: {e}")
        raise
    finally:
        session.close()
        db.close()


def main():
    """Main function"""
    print("\n" + "="*60)
    print("Loading Sample Data to Database")
    print("="*60 + "\n")
    
    db = DatabaseManager(Config.DATABASE_URL)
    session = db.get_session()
    
    try:
        # Get test user
        from storage.models import User
        user = session.query(User).filter(User.username == "testuser").first()
        
        if not user:
            print("❌ Test user 'testuser' not found. Please run reset_and_setup.py first.")
            return
        
        user_id = user.user_id
        
        # Check if data already exists
        existing_count = session.query(Transaction).filter(Transaction.user_id == user_id).count()
        if existing_count > 0:
            print(f"⚠️  User already has {existing_count} transactions.")
            response = input("Clear existing data and reload? (yes/no): ").lower().strip()
            if response == 'yes':
                # Delete existing data
                session.query(Transaction).filter(Transaction.user_id == user_id).delete()
                session.query(Asset).filter(Asset.user_id == user_id).delete()
                session.commit()
                print("✅ Cleared existing data")
            else:
                print("Skipping data load.")
                return
        
        # Load data
        load_data_to_db(user_id)
        
        print("\n" + "="*60)
        print("✅ SAMPLE DATA LOADED SUCCESSFULLY")
        print("="*60)
        print(f"\nUser: {user.username}")
        print(f"Transactions loaded: {len(SAMPLE_DATA['transactions'])}")
        print(f"Assets loaded: {len(SAMPLE_DATA['assets'])}")
        print("\nData Breakdown:")
        print(f"  - Income transactions: 3")
        print(f"  - EMI payments: 3")
        print(f"  - Investment transactions: 2")
        print(f"  - Expenses: 2")
        print("\nAssets:")
        for asset in SAMPLE_DATA['assets']:
            print(f"  - {asset['name']}: ₹{asset['current_value']:,}")
        print("="*60 + "\n")
        
    finally:
        session.close()
        db.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

