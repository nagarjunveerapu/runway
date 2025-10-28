"""
Authentication Routes

Handles user registration, login, and authentication endpoints.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from datetime import timedelta
from sqlalchemy.orm import Session
import uuid

from api.models.schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token
)
from storage.database import DatabaseManager
from storage.models import User
from auth.password import hash_password, verify_password
from auth.jwt import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from auth.dependencies import get_db, get_current_user
from config import Config


router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: DatabaseManager = Depends(get_db)):
    """
    Register a new user
    
    Args:
        user_data: User registration data (username, email, password)
        db: Database manager
        
    Returns:
        Created user information
        
    Raises:
        HTTPException: If username or email already exists
    """
    session = db.get_session()
    
    try:
        # Check if username already exists
        existing_user = session.query(User).filter(User.username == user_data.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Check if email already exists
        existing_email = session.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        user = User(
            user_id=str(uuid.uuid4()),
            username=user_data.username,
            email=user_data.email,
            password_hash=hash_password(user_data.password),
            is_active=True
        )
        
        session.add(user)
        session.commit()
        session.refresh(user)
        
        return UserResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            created_at=user.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )
    finally:
        session.close()


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: DatabaseManager = Depends(get_db)):
    """
    Login and get JWT access token
    
    Args:
        credentials: Login credentials (username, password)
        db: Database manager
        
    Returns:
        JWT access token
        
    Raises:
        HTTPException: If credentials are invalid
    """
    session = db.get_session()
    
    try:
        # Find user by username
        user = session.query(User).filter(User.username == credentials.username).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Verify password
        if not verify_password(credentials.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"user_id": user.user_id, "username": user.username},
            expires_delta=access_token_expires
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )
    finally:
        session.close()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user information
    """
    return UserResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        created_at=current_user.created_at.isoformat()
    )

