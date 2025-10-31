"""
Credit Card API Routes

Handles credit card-specific operations and analytics.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional
import logging

from storage.database import DatabaseManager
from storage.models import User
from auth.dependencies import get_current_user, get_db
from config import Config
from services.credit_card_service.credit_card_service import CreditCardService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/payments-summary")
async def get_credit_card_payments_summary(
    financial_year: Optional[str] = Query(None, description="Financial year filter (e.g., 2024-25)"),
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """
    Get summary of credit card payments across all cards
    
    Returns aggregated payment data:
    - Total payments made
    - Breakdown by card (last 4 digits)
    - Breakdown by bank
    - Breakdown by financial year
    
    Args:
        financial_year: Optional financial year filter (e.g., "2024-25")
        current_user: Current authenticated user
        db: Database manager
    """
    try:
        credit_card_service = CreditCardService(db)
        summary = credit_card_service.get_credit_card_payments_summary(
            user_id=current_user.user_id,
            financial_year=financial_year
        )
        return summary
        
    except Exception as e:
        logger.error(f"Error fetching credit card payments summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch credit card payments summary: {str(e)}"
        )


@router.get("/statements")
async def get_credit_card_statements(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of statements to return"),
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """
    Get user's credit card statements
    
    Returns list of uploaded credit card statements with metadata
    
    Args:
        limit: Maximum number of statements to return
        current_user: Current authenticated user
        db: Database manager
    """
    try:
        credit_card_service = CreditCardService(db)
        statements = credit_card_service.get_credit_card_statements(
            user_id=current_user.user_id,
            limit=limit
        )
        return statements
        
    except Exception as e:
        logger.error(f"Error fetching credit card statements: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch credit card statements: {str(e)}"
        )


@router.get("/accounts")
async def get_credit_card_accounts(
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """
    Get user's credit card accounts
    
    Returns list of credit card accounts across all banks
    
    Args:
        current_user: Current authenticated user
        db: Database manager
    """
    try:
        credit_card_service = CreditCardService(db)
        accounts = credit_card_service.get_credit_card_accounts(
            user_id=current_user.user_id
        )
        return accounts
        
    except Exception as e:
        logger.error(f"Error fetching credit card accounts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch credit card accounts: {str(e)}"
        )

