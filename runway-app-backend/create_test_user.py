#!/usr/bin/env python3
"""
Script to create a test user in the database for testing authentication.

Usage: python create_test_user.py
"""

import sys
from pathlib import Path
import uuid
from sqlalchemy.orm import Session

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from storage.database import DatabaseManager
from storage.models import User
from auth.password import hash_password
from config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_user():
    """Create a test user in the database"""
    
    # Test user credentials
    username = "testuser"
    email = "test@example.com"
    password = "testpassword123"
    
    # Initialize database
    db = DatabaseManager(Config.DATABASE_URL)
    session = db.get_session()
    
    try:
        # Check if user already exists
        existing_user = session.query(User).filter(User.username == username).first()
        if existing_user:
            logger.info(f"User '{username}' already exists. Updating password...")
            existing_user.password_hash = hash_password(password)
            existing_user.is_active = True
            session.commit()
            logger.info(f"✅ Password updated for user '{username}'")
            return username, password
        
        # Create new user
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
        
        logger.info(f"✅ Test user created successfully!")
        logger.info(f"   Username: {username}")
        logger.info(f"   Email: {email}")
        logger.info(f"   Password: {password}")
        logger.info(f"   User ID: {user.user_id}")
        
        return username, password
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Failed to create test user: {e}")
        raise
    finally:
        session.close()
        db.close()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Creating Test User for Runway Finance")
    print("="*60 + "\n")
    
    try:
        username, password = create_test_user()
        
        print("\n" + "="*60)
        print("✅ TEST USER CREATED SUCCESSFULLY")
        print("="*60)
        print(f"\nLogin Credentials:")
        print(f"  Username: {username}")
        print(f"  Password: {password}")
        print(f"\nYou can now use these credentials to log in to the app.")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

