"""
Authentication Dependencies

Provides dependency functions for FastAPI route authentication.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from storage.database import DatabaseManager
from storage.models import User
from config import Config
from .jwt import verify_token


security = HTTPBearer()


def get_db():
    """Get database session"""
    db = DatabaseManager(Config.DATABASE_URL)
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: DatabaseManager = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token
    
    Args:
        credentials: HTTP authorization credentials
        db: Database manager
        
    Returns:
        User object
        
    Raises:
        HTTPException: If user is not authenticated or not found
    """
    token = credentials.credentials
    payload = verify_token(token)
    
    user_id = payload.get('user_id')
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    session = db.get_session()
    try:
        user = session.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        return user
    finally:
        session.close()

