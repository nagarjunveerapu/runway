#!/usr/bin/env python3
"""
Create a second test user in the database
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage.database import DatabaseManager
from storage.models import User
from auth.password import hash_password
from config import Config

def create_user():
    """Create a new test user"""
    # Initialize database
    db = DatabaseManager(Config.DATABASE_URL)
    session = db.get_session()
    
    try:
        # Check if user already exists
        existing_user = session.query(User).filter(User.username == "test2@example.com").first()
        if existing_user:
            print(f"User 'test2@example.com' already exists!")
            return
        
        # Create new user
        new_user = User(
            user_id=str(uuid.uuid4()),
            username="test2@example.com",
            email="test2@example.com",
            password_hash=hash_password("password123"),
            is_active=True
        )
        
        session.add(new_user)
        session.commit()
        
        print(f"✅ User created successfully!")
        print(f"   Username: test2@example.com")
        print(f"   Password: password123")
        
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        session.rollback()
    finally:
        session.close()
        db.close()

if __name__ == "__main__":
    import uuid
    create_user()
