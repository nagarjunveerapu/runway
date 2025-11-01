"""
Transaction API Routes

CRUD operations for transactions
"""

from fastapi import APIRouter, HTTPException, Query, status, Depends
from typing import List, Optional
import sys
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.models.schemas import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionList
)
from storage.database import DatabaseManager
from storage.models import User, TransactionType
from auth.dependencies import get_current_user
from services.transaction_service.unified_transaction_service import UnifiedTransactionService
from schema import CanonicalTransaction, create_transaction
from config import Config

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db():
    """Get database instance"""
    return DatabaseManager(Config.DATABASE_URL)


def get_unified_transaction_service(db: DatabaseManager = Depends(get_db)) -> UnifiedTransactionService:
    """Get unified transaction service instance"""
    return UnifiedTransactionService(db)


# ============================================================================
# GET Endpoints
# ============================================================================

@router.post("/re-categorize")
async def recategorize_transactions(
    current_user: User = Depends(get_current_user)
):
    """
    Re-categorize all user transactions based on detected patterns (salary, EMI, etc.)
    """
    db = get_db()
    session = db.get_session()
    
    try:
        from storage.models import Transaction as TransactionModel
        
        def get_merchant_source(description):
            """Extract merchant/source from transaction description"""
            if not description:
                return 'unknown'
            desc_lower = str(description).lower()
            if 'capital' in desc_lower and 'one' in desc_lower:
                return 'capital one'
            if 'canfin' in desc_lower:
                return 'canfin homes'
            if 'hdfc' in desc_lower:
                return 'hdfc'
            if 'icici' in desc_lower:
                return 'icici'
            if 'sbi' in desc_lower or 'state bank' in desc_lower:
                return 'sbi'
            if 'axis' in desc_lower:
                return 'axis'
            words = description.split()
            if len(words) >= 2:
                return ' '.join(words[:2]).lower()
            return description[:30].lower()
        
        def is_similar_amount(amt1, amt2, variance=0.05):
            """Check if two amounts are similar"""
            if amt1 == 0 or amt2 == 0:
                return False
            diff = abs(amt1 - amt2)
            avg = (amt1 + amt2) / 2
            return diff / avg <= variance
        
        # Get all user transactions
        transactions = session.query(Transaction).filter(
            Transaction.user_id == current_user.user_id
        ).all()
        
        # Detect salary patterns (large recurring credits)
        # Handle ENUM comparison (works for both ENUM and string for backward compatibility)
        credit_txns = [
            t for t in transactions 
            if (t.type.value if hasattr(t.type, 'value') else t.type) == TransactionType.CREDIT.value 
            and float(t.amount) >= 50000
        ]
        credit_groups = {}
        
        for txn in credit_txns:
            source = get_merchant_source(txn.description_raw or '')
            amount = float(txn.amount)
            
            if source not in credit_groups:
                credit_groups[source] = []
            credit_groups[source].append({'txn': txn, 'amount': amount})
        
        # Find recurring salary patterns
        salary_patterns = []
        for source, txns in credit_groups.items():
            amount_groups = {}
            for item in txns:
                amt = item['amount']
                added = False
                for key in list(amount_groups.keys()):
                    base_amount = float(key)
                    if is_similar_amount(amt, base_amount, 0.1):
                        amount_groups[key].append(item)
                        added = True
                        break
                if not added:
                    amount_groups[str(amt)] = [item]
            
            for amt, group in amount_groups.items():
                if len(group) >= 2:
                    avg_amount = sum(x['amount'] for x in group) / len(group)
                    salary_patterns.append({
                        'source': source,
                        'avg_amount': avg_amount,
                        'txns': group
                    })
        
        # Update all transactions in detected salary patterns
        updates = 0
        for pattern in salary_patterns:
            if pattern['avg_amount'] >= 500000:  # Only large amounts
                for item in pattern['txns']:
                    txn = item['txn']
                    if txn.category != 'Salary':
                        txn.category = 'Salary'
                        updates += 1
                        logger.info(f"Marked salary: ₹{item['amount']:,.2f} from {pattern['source']}")
        
        session.commit()
        
        return {
            "status": "success",
            "patterns_detected": len(salary_patterns),
            "transactions_updated": updates,
            "message": f"Re-categorized {updates} transactions based on detected patterns"
        }
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error re-categorizing transactions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to re-categorize transactions: {str(e)}"
        )
    finally:
        session.close()
        db.close()


@router.get("/", response_model=TransactionList)
async def get_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    start_date: Optional[str] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (YYYY-MM-DD)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    transaction_type: Optional[str] = Query('all', description="Filter by transaction type ('all', 'bank', 'credit_card')"),
    min_amount: Optional[float] = Query(None, description="Minimum amount"),
    max_amount: Optional[float] = Query(None, description="Maximum amount"),
    current_user: User = Depends(get_current_user),
    service: UnifiedTransactionService = Depends(get_unified_transaction_service)
):
    """
    Get paginated list of transactions with optional filters

    - **page**: Page number (starts from 1)
    - **page_size**: Number of items per page (max 100)
    - **start_date**: Filter transactions from this date (YYYY-MM-DD)
    - **end_date**: Filter transactions until this date (YYYY-MM-DD)
    - **category**: Filter by category
    - **min_amount**: Minimum transaction amount
    - **max_amount**: Maximum transaction amount
    """
    try:
        # Validate transaction_type parameter
        if transaction_type not in ['all', 'bank', 'credit_card']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="transaction_type must be 'all', 'bank', or 'credit_card'"
            )

        # Calculate offset
        offset = (page - 1) * page_size

        # Get transactions using unified service
        transactions = service.get_transactions(
            user_id=current_user.user_id,
            transaction_type=transaction_type,
            start_date=start_date,
            end_date=end_date,
            category=category,
            limit=page_size,
            offset=offset
        )

        # Filter by amount if specified
        if min_amount is not None:
            transactions = [t for t in transactions if (t.get('amount') if isinstance(t, dict) else t.amount) >= min_amount]
        if max_amount is not None:
            transactions = [t for t in transactions if (t.get('amount') if isinstance(t, dict) else t.amount) <= max_amount]

        # Get total count (for pagination metadata)
        all_transactions = service.get_transactions(
            user_id=current_user.user_id,
            transaction_type=transaction_type,
            start_date=start_date,
            end_date=end_date,
            category=category
        )
        total = len(all_transactions)

        # Convert to response models (handle both dict and model objects)
        transaction_responses = []
        for t in transactions:
            if isinstance(t, dict):
                transaction_responses.append(
                    TransactionResponse(
                        transaction_id=t.get('transaction_id', ''),
                        date=t.get('date', ''),
                        amount=t.get('amount', 0),
                        type=t.get('type', 'debit'),
                        description_raw=t.get('description_raw') or "",
                        clean_description=t.get('clean_description'),
                        merchant_raw=t.get('merchant_raw'),
                        merchant_canonical=t.get('merchant_canonical'),
                        merchant_id=t.get('merchant_id'),
                        category=t.get('category') or "Unknown",
                        confidence=t.get('confidence'),
                        balance=t.get('balance'),
                        currency=t.get('currency') or "INR",
                        is_duplicate=t.get('is_duplicate') or False,
                        duplicate_count=t.get('duplicate_count') or 0,
                        source=t.get('source') or "unknown",
                        bank_name=t.get('bank_name'),
                        created_at=t.get('created_at')
                    )
                )
            else:
                # Legacy Transaction model object
                transaction_responses.append(
                    TransactionResponse(
                        transaction_id=t.transaction_id,
                        date=t.date,
                        amount=t.amount,
                        type=t.type,
                        description_raw=t.description_raw or "",
                        clean_description=t.clean_description,
                        merchant_raw=t.merchant_raw,
                        merchant_canonical=t.merchant_canonical,
                        merchant_id=t.merchant_id,
                        category=t.category or "Unknown",
                        confidence=t.confidence,
                        balance=t.balance,
                        currency=t.currency or "INR",
                        is_duplicate=t.is_duplicate or False,
                        duplicate_count=t.duplicate_count or 0,
                        source=t.source or "unknown",
                        bank_name=t.bank_name,
                        created_at=t.created_at.isoformat() if t.created_at else None
                    )
                )

        total_pages = (total + page_size - 1) // page_size

        return TransactionList(
            transactions=transaction_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error(f"Error fetching transactions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch transactions: {str(e)}"
        )


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(transaction_id: str):
    """
    Get a single transaction by ID

    - **transaction_id**: Unique transaction identifier
    """
    try:
        db = get_db()
        session = db.get_session()

        from storage.models import Transaction
        transaction = session.query(Transaction).filter_by(
            transaction_id=transaction_id
        ).first()

        if not transaction:
            session.close()
            db.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction {transaction_id} not found"
            )

        response = TransactionResponse(
            transaction_id=transaction.transaction_id,
            date=transaction.date,
            amount=transaction.amount,
            type=transaction.type,
            description_raw=transaction.description_raw or "",
            clean_description=transaction.clean_description,
            merchant_raw=transaction.merchant_raw,
            merchant_canonical=transaction.merchant_canonical,
            merchant_id=transaction.merchant_id,
            category=transaction.category or "Unknown",
            confidence=transaction.confidence,
            balance=transaction.balance,
            currency=transaction.currency or "INR",
            is_duplicate=transaction.is_duplicate or False,
            duplicate_count=transaction.duplicate_count or 0,
            source=transaction.source or "unknown",
            bank_name=transaction.bank_name,
            created_at=transaction.created_at.isoformat() if transaction.created_at else None
        )

        session.close()
        db.close()

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching transaction {transaction_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch transaction: {str(e)}"
        )


# ============================================================================
# POST Endpoints
# ============================================================================

@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction_endpoint(transaction: TransactionCreate):
    """
    Create a new transaction

    - **date**: Transaction date (YYYY-MM-DD)
    - **amount**: Transaction amount (must be positive)
    - **type**: Transaction type (debit or credit)
    - **description_raw**: Transaction description
    - **merchant_canonical**: Canonical merchant name (optional)
    - **category**: Transaction category (optional)
    - **balance**: Account balance after transaction (optional)
    - **source**: Data source (default: api)
    """
    try:
        db = get_db()

        # Create canonical transaction
        canonical_txn = create_transaction(
            date=transaction.date,
            amount=transaction.amount,
            type=transaction.type.value,
            description=transaction.description_raw,
            merchant_canonical=transaction.merchant_canonical,
            category=transaction.category,
            balance=transaction.balance,
            source=transaction.source,
            bank_name=transaction.bank_name,
            account_id=transaction.account_id
        )

        # Insert into database
        db_txn = db.insert_transaction(canonical_txn)

        response = TransactionResponse(
            transaction_id=db_txn.transaction_id,
            date=db_txn.date,
            amount=db_txn.amount,
            type=db_txn.type,
            description_raw=db_txn.description_raw or "",
            clean_description=db_txn.clean_description,
            merchant_raw=db_txn.merchant_raw,
            merchant_canonical=db_txn.merchant_canonical,
            merchant_id=db_txn.merchant_id,
            category=db_txn.category or "Unknown",
            confidence=db_txn.confidence,
            balance=db_txn.balance,
            currency=db_txn.currency or "INR",
            is_duplicate=db_txn.is_duplicate or False,
            duplicate_count=db_txn.duplicate_count or 0,
            source=db_txn.source or "api",
            bank_name=db_txn.bank_name,
            created_at=db_txn.created_at.isoformat() if db_txn.created_at else None
        )

        db.close()
        logger.info(f"Created transaction: {response.transaction_id}")

        return response

    except Exception as e:
        logger.error(f"Error creating transaction: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create transaction: {str(e)}"
        )


# ============================================================================
# PUT/PATCH Endpoints
# ============================================================================

@router.patch("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(transaction_id: str, update_data: TransactionUpdate):
    """
    Update a transaction

    - **transaction_id**: Transaction to update
    - **category**: New category (optional)
    - **merchant_canonical**: New merchant name (optional)
    - **description_raw**: New description (optional)
    """
    try:
        db = get_db()
        session = db.get_session()

        from storage.models import Transaction
        transaction = session.query(Transaction).filter_by(
            transaction_id=transaction_id
        ).first()

        if not transaction:
            session.close()
            db.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction {transaction_id} not found"
            )

        # Update fields
        if update_data.category is not None:
            transaction.category = update_data.category

        if update_data.merchant_canonical is not None:
            transaction.merchant_canonical = update_data.merchant_canonical

        if update_data.description_raw is not None:
            transaction.description_raw = update_data.description_raw

        session.commit()
        session.refresh(transaction)

        response = TransactionResponse(
            transaction_id=transaction.transaction_id,
            date=transaction.date,
            amount=transaction.amount,
            type=transaction.type,
            description_raw=transaction.description_raw or "",
            clean_description=transaction.clean_description,
            merchant_raw=transaction.merchant_raw,
            merchant_canonical=transaction.merchant_canonical,
            merchant_id=transaction.merchant_id,
            category=transaction.category or "Unknown",
            confidence=transaction.confidence,
            balance=transaction.balance,
            currency=transaction.currency or "INR",
            is_duplicate=transaction.is_duplicate or False,
            duplicate_count=transaction.duplicate_count or 0,
            source=transaction.source or "unknown",
            bank_name=transaction.bank_name,
            created_at=transaction.created_at.isoformat() if transaction.created_at else None
        )

        session.close()
        db.close()

        logger.info(f"Updated transaction: {transaction_id}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating transaction {transaction_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update transaction: {str(e)}"
        )


# ============================================================================
# DELETE Endpoints
# ============================================================================

@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(transaction_id: str):
    """
    Delete a transaction

    - **transaction_id**: Transaction to delete
    """
    try:
        db = get_db()

        success = db.delete_transaction(transaction_id)

        if not success:
            db.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction {transaction_id} not found"
            )

        db.close()
        logger.info(f"Deleted transaction: {transaction_id}")

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting transaction {transaction_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete transaction: {str(e)}"
        )
