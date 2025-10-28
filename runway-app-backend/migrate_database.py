#!/usr/bin/env python3
"""
Script to migrate database schema for authentication support.

This will update the existing database or create a new one.
"""

import sys
from pathlib import Path
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from storage.database import DatabaseManager
from storage.models import Base
from config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_database():
    """Migrate database to include password_hash column"""
    
    db_path = Path("data/finance.db")
    
    print("\n" + "="*60)
    print("Database Migration: Adding Authentication Fields")
    print("="*60)
    
    # Check if database exists
    if db_path.exists():
        print("\n⚠️  Existing database found.")
        print("This will update the schema to include authentication fields.")
        print("User data will be preserved where possible.\n")
        
        # Ask for confirmation
        response = input("Continue? (yes/no): ").lower().strip()
        if response not in ['yes', 'y']:
            print("Migration cancelled.")
            return
    
    print("\n📊 Migrating database...")
    
    # Initialize database - this will create/update tables
    db = DatabaseManager(Config.DATABASE_URL)
    
    try:
        # Create all tables with updated schema
        Base.metadata.create_all(bind=db.engine)
        
        print("✅ Database migration completed successfully!")
        print(f"   Database location: {db_path.absolute()}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    try:
        success = migrate_database()
        
        if success:
            print("\n" + "="*60)
            print("Next step: Create test user")
            print("Run: python3 create_test_user.py")
            print("="*60 + "\n")
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nMigration cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

