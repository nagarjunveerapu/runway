"""
Account Management Routes

Handles CRUD operations for bank accounts.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from sqlalchemy.orm import Session
import uuid
import logging
from pydantic import BaseModel

from storage.database import DatabaseManager
from storage.models import Account, User, Transaction
from auth.dependencies import get_current_user
from config import Config

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db():
    """Get database instance"""
    return DatabaseManager(Config.DATABASE_URL)


# Pydantic schemas
class AccountCreate(BaseModel):
    account_name: str
    bank_name: str
    account_type: str = "savings"
    account_number: Optional[str] = None
    currency: str = "INR"


class AccountResponse(BaseModel):
    account_id: str
    user_id: str
    account_name: str
    bank_name: str
    account_type: str
    currency: str
    is_active: bool
    created_at: str
    account_number_ref: Optional[str] = None  # Account number reference
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[AccountResponse])
async def get_accounts(
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Get all accounts for the current user"""
    session = db.get_session()
    
    try:
        accounts = session.query(Account).filter(
            Account.user_id == current_user.user_id,
            Account.is_active == True
        ).all()
        
        return [AccountResponse(
            account_id=a.account_id,
            user_id=a.user_id,
            account_name=a.account_name or "Unnamed Account",  # Handle None values
            bank_name=a.bank_name or "Unknown Bank",  # Handle None values
            account_type=a.account_type or "savings",  # Handle None values
            currency=a.currency or "INR",  # Handle None values
            is_active=a.is_active if a.is_active is not None else True,
            created_at=a.created_at.isoformat() if a.created_at else "",
            account_number_ref=a.account_number_ref  # Include account number reference
        ) for a in accounts]
    
    except Exception as e:
        logger.error(f"Error fetching accounts: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
    
    finally:
        session.close()


@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    account_data: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Create a new account"""
    session = db.get_session()
    
    try:
        new_account = Account(
            account_id=str(uuid.uuid4()),
            user_id=current_user.user_id,
            account_name=account_data.account_name,
            bank_name=account_data.bank_name,
            account_type=account_data.account_type,
            current_balance=0.0,  # Default balance to 0.0
            account_number_ref=account_data.account_number,
            currency=account_data.currency,
            is_active=True
        )
        
        session.add(new_account)
        session.commit()
        session.refresh(new_account)
        
        return AccountResponse(
            account_id=new_account.account_id,
            user_id=new_account.user_id,
            account_name=new_account.account_name,
            bank_name=new_account.bank_name,
            account_type=new_account.account_type,
            currency=new_account.currency,
            is_active=new_account.is_active,
            created_at=new_account.created_at.isoformat(),
            account_number_ref=new_account.account_number_ref  # Include account number reference
        )
    
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating account: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create account")
    
    finally:
        session.close()


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Soft delete an account (set is_active=False)"""
    session = db.get_session()
    
    try:
        account = session.query(Account).filter(
            Account.account_id == account_id,
            Account.user_id == current_user.user_id
        ).first()
        
        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
        
        account.is_active = False
        session.commit()
    
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting account: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete account")
    
    finally:
        session.close()


@router.delete("/{account_id}/data", status_code=status.HTTP_200_OK)
async def reset_account_data(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Delete all transactions and related data for an account"""
    from storage.models import SalarySweepConfig, DetectedEMIPattern
    
    session = db.get_session()
    
    try:
        # Verify account belongs to user
        account = session.query(Account).filter(
            Account.account_id == account_id,
            Account.user_id == current_user.user_id
        ).first()
        
        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
        
        # Delete all transactions for this user (not just this account)
        # This ensures Investment Optimizer and other features see clean data
        transactions_deleted = session.query(Transaction).filter(
            Transaction.user_id == current_user.user_id
        ).delete(synchronize_session=False)
        
        # Also delete Salary Sweep configuration
        configs_deleted = session.query(SalarySweepConfig).filter(
            SalarySweepConfig.user_id == current_user.user_id
        ).delete(synchronize_session=False)
        
        # Delete EMI patterns (these are related to recurring payments)
        emi_patterns_deleted = session.query(DetectedEMIPattern).filter(
            DetectedEMIPattern.user_id == current_user.user_id
        ).delete(synchronize_session=False)
        
        logger.info(f"Deleted {transactions_deleted} transactions, {configs_deleted} configs, {emi_patterns_deleted} EMI patterns for user {current_user.user_id}")
        
        session.commit()
        
        return {
            "message": "Account data reset successfully",
            "transactions_deleted": transactions_deleted,
            "configs_deleted": configs_deleted,
            "emi_patterns_deleted": emi_patterns_deleted
        }
    
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error resetting account data: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to reset account data")
    
    finally:
        session.close()

