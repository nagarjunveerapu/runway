#!/usr/bin/env python3
"""
Quick setup script: Reset database and create test user.
Run this to get everything ready for testing.

Usage: python3 reset_and_setup.py
"""

import sys
from pathlib import Path
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from storage.database import DatabaseManager
from storage.models import User, Account, Base
from auth.password import hash_password
from config import Config
from sqlalchemy import text
import uuid
import logging
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def reset_and_setup():
    """Reset database and create test user"""
    
    script_dir = Path(__file__).parent
    db_path = script_dir / "data/finance.db"
    
    print("\n" + "="*60)
    print("Runway Finance: Database Reset and Test User Setup")
    print("="*60)
    
    # Remove old database if exists
    if db_path.exists():
        print("\n🗑️  Removing old database...")
        try:
            backup_path = db_path.with_suffix('.db.backup')
            if backup_path.exists():
                backup_path.unlink()
            db_path.rename(backup_path)
            print(f"✅ Old database backed up to: {backup_path}")
        except Exception as e:
            print(f"⚠️  Could not backup database: {e}")
            db_path.unlink()
    
    print("\n📊 Creating new database with authentication support...")
    
    # Create data directory if it doesn't exist
    (script_dir / "data").mkdir(exist_ok=True)
    
    # Initialize new database
    db = DatabaseManager(Config.DATABASE_URL)
    
    try:
        # Create all tables with new schema
        Base.metadata.create_all(bind=db.engine)
        
        # Create unique constraint for transactions (for duplicate prevention)
        # Includes balance to differentiate same transaction at different times in the day
        # Uses COALESCE to normalize NULL balance to sentinel value (-999999999.99)
        # SQLite UNIQUE constraint treats NULL as distinct, so we normalize NULLs
        session = db.get_session()
        try:
            # Drop existing index if it exists (without COALESCE)
            try:
                session.execute(text("DROP INDEX IF EXISTS idx_transaction_unique"))
                session.commit()
            except:
                pass
            
            # Create new unique index with COALESCE to handle NULL balance
            session.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_transaction_unique 
                ON transactions(
                    user_id, 
                    account_id, 
                    date, 
                    amount, 
                    description_raw, 
                    COALESCE(balance, -999999999.99)
                )
            """))
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"⚠️  Warning: Could not create unique constraint: {e}")
        finally:
            session.close()
        
        print("✅ Database created successfully!")
        
        # Now create test user
        print("\n👤 Creating test user...")
        
        email = "test@example.com"
        username = email  # allow login using either username or email
        password = "testpassword123"
        created_accounts = []  # Initialize outside try block for scope
        
        session = db.get_session()
        
        try:
            # Ensure no duplicate test user
            session.query(User).filter(User.email == email).delete()

            user = User(
                user_id=str(uuid.uuid4()),
                username=username,
                email=email,
                password_hash=hash_password(password),
                is_active=True
            )
            
            session.add(user)
            session.commit()
            session.refresh(user)
            
            print("✅ Test user created successfully!")
            
            # Create sample accounts for testing
            print("\n🏦 Creating sample accounts...")
            
            sample_accounts = [
                {
                    "account_name": "HDFC Savings Account",
                    "bank_name": "HDFC Bank",
                    "account_type": "savings",
                    "account_number_ref": f"SAV-{uuid.uuid4().hex[:8].upper()}"
                },
                {
                    "account_name": "ICICI Current Account",
                    "bank_name": "ICICI Bank",
                    "account_type": "current",
                    "account_number_ref": f"CUR-{uuid.uuid4().hex[:8].upper()}"
                },
                {
                    "account_name": "SBI Credit Card",
                    "bank_name": "State Bank of India",
                    "account_type": "credit_card",
                    "account_number_ref": f"CC-{uuid.uuid4().hex[:8].upper()}"
                },
                {
                    "account_name": "Axis Salary Account",
                    "bank_name": "Axis Bank",
                    "account_type": "savings",
                    "account_number_ref": f"SAL-{uuid.uuid4().hex[:8].upper()}"
                }
            ]
            
            created_accounts = []
            for acc_data in sample_accounts:
                try:
                    # Get current_balance if provided, otherwise use 0.0 as default
                    current_balance = acc_data.get("current_balance", 0.0)
                    
                    account = Account(
                        account_id=str(uuid.uuid4()),
                        user_id=user.user_id,  # Link account to test user
                        account_name=acc_data["account_name"],
                        bank_name=acc_data["bank_name"],
                        account_type=acc_data["account_type"],
                        current_balance=current_balance,  # Default to 0.0 if not provided
                        account_number_ref=acc_data["account_number_ref"],
                        currency="INR",
                        is_active=True
                    )
                    session.add(account)
                    created_accounts.append(account)
                    
                    # Format balance for display
                    balance_str = f"₹{current_balance:,.2f}"
                    print(f"   ✅ {acc_data['bank_name']} - {acc_data['account_name']} ({balance_str})")
                except Exception as e:
                    print(f"   ⚠️  Failed to create {acc_data['account_name']}: {e}")
                    import traceback
                    traceback.print_exc()
            
            session.commit()
            
            # Refresh accounts to get IDs
            for account in created_accounts:
                session.refresh(account)
            
            print(f"✅ Created {len(created_accounts)} sample accounts!")
            
        except Exception as e:
            session.rollback()
            print(f"❌ Failed to create test user/accounts: {e}")
            raise
        finally:
            session.close()
        
        print("\n" + "="*60)
        print("✅ SETUP COMPLETE!")
        print("="*60)
        print("\n📝 Test Credentials:")
        print(f"   Username: {username}")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"\n🏦 Sample Accounts Created: {len(created_accounts)}")
        print("   • HDFC Savings Account")
        print("   • ICICI Current Account")
        print("   • SBI Credit Card")
        print("   • Axis Salary Account")
        print("\n💡 Next Steps:")
        print("   1. Start backend: cd runway/run_poc && python3 -m uvicorn api.main:app --reload")
        print("   2. Start frontend: cd FIRE/runway-app && npm start")
        print("   3. Login at http://localhost:3000/login")
        print("="*60 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        logger.error(f"Error details: {e}", exc_info=True)
        return False
    finally:
        db.close()


if __name__ == "__main__":
    try:
        success = reset_and_setup()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

