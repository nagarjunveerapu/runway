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
from storage.models import User, Base
from auth.password import hash_password
from config import Config
import uuid
import logging
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def reset_and_setup():
    """Reset database and create test user"""
    
    db_path = Path("data/finance.db")
    
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
    Path("data").mkdir(exist_ok=True)
    
    # Initialize new database
    db = DatabaseManager(Config.DATABASE_URL)
    
    try:
        # Create all tables with new schema
        Base.metadata.create_all(bind=db.engine)
        
        print("✅ Database created successfully!")
        
        # Now create test user
        print("\n👤 Creating test user...")
        
        username = "testuser"
        email = "test@example.com"
        password = "testpassword123"
        
        session = db.get_session()
        
        try:
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
            
        except Exception as e:
            session.rollback()
            print(f"❌ Failed to create test user: {e}")
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

