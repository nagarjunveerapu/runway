"""
Bank Transaction API Routes

CRUD operations for bank transactions (savings, current, checking accounts).
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
from services.bank_transaction_service.bank_transaction_service import BankTransactionService
from config import Config

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db():
    """Get database instance"""
    return DatabaseManager(Config.DATABASE_URL)


def get_bank_transaction_service(db: DatabaseManager = Depends(get_db)) -> BankTransactionService:
    """Get bank transaction service instance"""
    return BankTransactionService(db)


# ============================================================================
# GET Endpoints
# ============================================================================

@router.get("/", response_model=List[dict])
async def get_bank_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    start_date: Optional[str] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (YYYY-MM-DD)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type ('debit' or 'credit')"),
    current_user: User = Depends(get_current_user),
    service: BankTransactionService = Depends(get_bank_transaction_service)
):
    """
    Get paginated list of bank transactions with optional filters
    
    - **page**: Page number (starts from 1)
    - **page_size**: Number of items per page (max 1000)
    - **account_id**: Filter transactions by account ID
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
            start_date=start_date,
            end_date=end_date,
            category=category,
            transaction_type=transaction_type,
            limit=page_size,
            offset=offset
        )
        
        return transactions
        
    except Exception as e:
        logger.error(f"Error getting bank transactions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve bank transactions: {str(e)}"
        )


@router.get("/{transaction_id}", response_model=dict)
async def get_bank_transaction(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    service: BankTransactionService = Depends(get_bank_transaction_service)
):
    """
    Get a single bank transaction by ID
    
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
                detail=f"Bank transaction {transaction_id} not found"
            )
        
        return transaction
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bank transaction {transaction_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve bank transaction: {str(e)}"
        )


@router.get("/statistics/summary", response_model=dict)
async def get_bank_transaction_statistics(
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    start_date: Optional[str] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    service: BankTransactionService = Depends(get_bank_transaction_service)
):
    """
    Get bank transaction statistics
    
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
        logger.error(f"Error getting bank transaction statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )


# ============================================================================
# POST Endpoints
# ============================================================================

@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_bank_transaction(
    transaction_data: dict,
    current_user: User = Depends(get_current_user),
    service: BankTransactionService = Depends(get_bank_transaction_service)
):
    """
    Create a new bank transaction
    
    - **transaction_data**: Transaction data dictionary
      Required fields: date, amount, type
      Optional fields: description_raw, account_id, category, balance, etc.
    """
    try:
        transaction = service.create_transaction(
            transaction_data=transaction_data,
            user_id=current_user.user_id,
            account_id=transaction_data.get('account_id')
        )
        
        return transaction
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating bank transaction: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create bank transaction: {str(e)}"
        )


@router.post("/bulk", response_model=List[dict], status_code=status.HTTP_201_CREATED)
async def bulk_create_bank_transactions(
    transactions: List[dict],
    current_user: User = Depends(get_current_user),
    service: BankTransactionService = Depends(get_bank_transaction_service)
):
    """
    Bulk create bank transactions
    
    - **transactions**: List of transaction data dictionaries
    """
    try:
        created_transactions = service.bulk_create_transactions(
            transactions=transactions,
            user_id=current_user.user_id
        )
        
        return created_transactions
        
    except Exception as e:
        logger.error(f"Error bulk creating bank transactions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk create bank transactions: {str(e)}"
        )


# ============================================================================
# PUT/PATCH Endpoints
# ============================================================================

@router.put("/{transaction_id}", response_model=dict)
async def update_bank_transaction(
    transaction_id: str,
    updates: dict,
    current_user: User = Depends(get_current_user),
    service: BankTransactionService = Depends(get_bank_transaction_service)
):
    """
    Update a bank transaction
    
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
                detail=f"Bank transaction {transaction_id} not found"
            )
        
        return transaction
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating bank transaction {transaction_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update bank transaction: {str(e)}"
        )


# ============================================================================
# DELETE Endpoints
# ============================================================================

@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bank_transaction(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    service: BankTransactionService = Depends(get_bank_transaction_service)
):
    """
    Delete a bank transaction
    
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
                detail=f"Bank transaction {transaction_id} not found"
            )
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting bank transaction {transaction_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete bank transaction: {str(e)}"
        )

