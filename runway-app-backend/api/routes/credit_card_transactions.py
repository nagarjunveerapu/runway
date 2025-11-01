"""
Credit Card Transaction API Routes

CRUD operations for credit card transactions.
"""

from fastapi import APIRouter, HTTPException, Query, status, Depends
from typing import List, Optional
import sys
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from storage.database import DatabaseManager
from storage.models import User
from auth.dependencies import get_current_user
from services.credit_card_transaction_service.credit_card_transaction_service import CreditCardTransactionService
from config import Config

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db():
    """Get database instance"""
    return DatabaseManager(Config.DATABASE_URL)


def get_credit_card_transaction_service(db: DatabaseManager = Depends(get_db)) -> CreditCardTransactionService:
    """Get credit card transaction service instance"""
    return CreditCardTransactionService(db)


# ============================================================================
# GET Endpoints
# ============================================================================

@router.get("/", response_model=List[dict])
async def get_credit_card_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    statement_id: Optional[str] = Query(None, description="Filter by statement ID"),
    billing_cycle: Optional[str] = Query(None, description="Filter by billing cycle (e.g., 'Jan 2024')"),
    start_date: Optional[str] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (YYYY-MM-DD)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type ('debit' or 'credit')"),
    current_user: User = Depends(get_current_user),
    service: CreditCardTransactionService = Depends(get_credit_card_transaction_service)
):
    """
    Get paginated list of credit card transactions with optional filters
    
    - **page**: Page number (starts from 1)
    - **page_size**: Number of items per page (max 1000)
    - **account_id**: Filter transactions by account ID
    - **statement_id**: Filter transactions by statement ID
    - **billing_cycle**: Filter transactions by billing cycle (e.g., 'Jan 2024')
    - **start_date**: Filter transactions from this date (YYYY-MM-DD)
    - **end_date**: Filter transactions until this date (YYYY-MM-DD)
    - **category**: Filter by category
    - **transaction_type**: Filter by transaction type ('debit' or 'credit')
    """
    try:
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Get transactions
        transactions = service.get_transactions(
            user_id=current_user.user_id,
            account_id=account_id,
            statement_id=statement_id,
            billing_cycle=billing_cycle,
            start_date=start_date,
            end_date=end_date,
            category=category,
            transaction_type=transaction_type,
            limit=page_size,
            offset=offset
        )
        
        return transactions
        
    except Exception as e:
        logger.error(f"Error getting credit card transactions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve credit card transactions: {str(e)}"
        )


@router.get("/{transaction_id}", response_model=dict)
async def get_credit_card_transaction(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    service: CreditCardTransactionService = Depends(get_credit_card_transaction_service)
):
    """
    Get a single credit card transaction by ID
    
    - **transaction_id**: Transaction ID
    """
    try:
        transaction = service.get_transaction(
            transaction_id=transaction_id,
            user_id=current_user.user_id
        )
        
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Credit card transaction {transaction_id} not found"
            )
        
        return transaction
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting credit card transaction {transaction_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve credit card transaction: {str(e)}"
        )


@router.get("/statistics/summary", response_model=dict)
async def get_credit_card_transaction_statistics(
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    start_date: Optional[str] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    service: CreditCardTransactionService = Depends(get_credit_card_transaction_service)
):
    """
    Get credit card transaction statistics
    
    - **account_id**: Optional account ID filter
    - **start_date**: Optional start date (YYYY-MM-DD)
    - **end_date**: Optional end date (YYYY-MM-DD)
    
    Returns statistics including:
    - total_count: Total number of transactions
    - debit_count: Number of debit transactions
    - credit_count: Number of credit transactions
    - total_debit: Total debit amount
    - total_credit: Total credit amount
    - net_amount: Net amount (credit - debit)
    - total_fees: Total transaction fees
    - total_reward_points: Total reward points
    """
    try:
        statistics = service.get_statistics(
            user_id=current_user.user_id,
            account_id=account_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return statistics
        
    except Exception as e:
        logger.error(f"Error getting credit card transaction statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )


@router.get("/billing-cycle/{billing_cycle}", response_model=List[dict])
async def get_transactions_by_billing_cycle(
    billing_cycle: str,
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    current_user: User = Depends(get_current_user),
    service: CreditCardTransactionService = Depends(get_credit_card_transaction_service)
):
    """
    Get credit card transactions by billing cycle
    
    - **billing_cycle**: Billing cycle (e.g., 'Jan 2024')
    - **account_id**: Optional account ID filter
    """
    try:
        if not account_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="account_id is required for billing cycle queries"
            )
        
        transactions = service.get_transactions_by_billing_cycle(
            account_id=account_id,
            billing_cycle=billing_cycle
        )
        
        return transactions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting transactions by billing cycle: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve transactions: {str(e)}"
        )


# ============================================================================
# POST Endpoints
# ============================================================================

@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_credit_card_transaction(
    transaction_data: dict,
    current_user: User = Depends(get_current_user),
    service: CreditCardTransactionService = Depends(get_credit_card_transaction_service)
):
    """
    Create a new credit card transaction
    
    - **transaction_data**: Transaction data dictionary
      Required fields: date, amount, type
      Optional fields: description_raw, account_id, statement_id, billing_cycle, reward_points, etc.
    """
    try:
        transaction = service.create_transaction(
            transaction_data=transaction_data,
            user_id=current_user.user_id,
            account_id=transaction_data.get('account_id'),
            statement_id=transaction_data.get('statement_id')
        )
        
        return transaction
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating credit card transaction: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create credit card transaction: {str(e)}"
        )


@router.post("/bulk", response_model=List[dict], status_code=status.HTTP_201_CREATED)
async def bulk_create_credit_card_transactions(
    transactions: List[dict],
    current_user: User = Depends(get_current_user),
    service: CreditCardTransactionService = Depends(get_credit_card_transaction_service)
):
    """
    Bulk create credit card transactions
    
    - **transactions**: List of transaction data dictionaries
    """
    try:
        created_transactions = service.bulk_create_transactions(
            transactions=transactions,
            user_id=current_user.user_id
        )
        
        return created_transactions
        
    except Exception as e:
        logger.error(f"Error bulk creating credit card transactions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk create credit card transactions: {str(e)}"
        )


# ============================================================================
# PUT/PATCH Endpoints
# ============================================================================

@router.put("/{transaction_id}", response_model=dict)
async def update_credit_card_transaction(
    transaction_id: str,
    updates: dict,
    current_user: User = Depends(get_current_user),
    service: CreditCardTransactionService = Depends(get_credit_card_transaction_service)
):
    """
    Update a credit card transaction
    
    - **transaction_id**: Transaction ID
    - **updates**: Dictionary of fields to update
    """
    try:
        transaction = service.update_transaction(
            transaction_id=transaction_id,
            updates=updates,
            user_id=current_user.user_id
        )
        
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Credit card transaction {transaction_id} not found"
            )
        
        return transaction
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating credit card transaction {transaction_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update credit card transaction: {str(e)}"
        )


# ============================================================================
# DELETE Endpoints
# ============================================================================

@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credit_card_transaction(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    service: CreditCardTransactionService = Depends(get_credit_card_transaction_service)
):
    """
    Delete a credit card transaction
    
    - **transaction_id**: Transaction ID
    """
    try:
        deleted = service.delete_transaction(
            transaction_id=transaction_id,
            user_id=current_user.user_id
        )
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Credit card transaction {transaction_id} not found"
            )
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting credit card transaction {transaction_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete credit card transaction: {str(e)}"
        )

