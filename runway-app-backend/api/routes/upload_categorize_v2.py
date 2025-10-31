"""
Enhanced CSV Upload with Service Layer

This endpoint now uses the service layer architecture:
- ParserService for file parsing
- TransactionEnrichmentService for enrichment
- TransactionRepository for database operations

Still maintains custom logic for:
- EMI detection and tracking
- Investment detection
- Account creation
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, status
import sys
import uuid
from pathlib import Path
import logging
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from storage.database import DatabaseManager
from storage.models import Transaction, Asset, User, Account
from auth.dependencies import get_current_user
from config import Config
from utils.date_parser import parse_date, parse_month_from_date

# Import service layer components
from services.parser_service import ParserService
from services.parser_service.transaction_enrichment_service import TransactionEnrichmentService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db():
    """Get database instance"""
    return DatabaseManager(Config.DATABASE_URL)


def get_parser_service(db: DatabaseManager = Depends(get_db)) -> ParserService:
    """Get parser service instance"""
    return ParserService(db_manager=db)


def is_emi_transaction(description: str) -> bool:
    """Check if transaction is an EMI payment"""
    desc_lower = description.lower()
    emi_patterns = ['emi', 'loan', 'installment', 'repayment', 'principal', 'interest payment']
    return any(pattern in desc_lower for pattern in emi_patterns)


def is_investment_transaction(description: str) -> bool:
    """Check if transaction is an investment"""
    desc_lower = description.lower()
    investment_patterns = ['sip', 'mutual fund', 'investment', 'stock', 'equity', 'mf', 'ppf', 'nps', 'elss']
    return any(pattern in desc_lower for pattern in investment_patterns)


@router.post("/csv-smart")
async def upload_csv_smart(
    file: UploadFile = File(...),
    account_id: str = Form(None),
    current_user: User = Depends(get_current_user),
    parser_service: ParserService = Depends(get_parser_service)
):
    """
    Upload and process CSV file using Service Layer
    
    Uses complete service layer architecture:
    - ParserService for file parsing (via ParserFactory)
    - TransactionEnrichmentService for merchant normalization, categorization, deduplication
    - TransactionRepository for database operations
    
    Still tracks EMIs and investments for additional features.
    """
    
    logger.info("=" * 80)
    logger.info("📡 API ROUTE: /api/v1/upload/csv-smart (Using Service Layer) - Request received")
    logger.info(f"📡 API ROUTE: User: {current_user.username} ({current_user.user_id})")
    logger.info(f"📡 API ROUTE: File: {file.filename}")
    logger.info(f"📡 API ROUTE: Account ID: {account_id or 'None'}")
    logger.info("📡 API ROUTE: Delegating to ParserService...")
    logger.info("=" * 80)
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported"
        )
    
    db = get_db()
    session = db.get_session()
    
    try:
        # USE SERVICE LAYER: Process file end-to-end
        # The service layer handles file saving internally
        logger.info(f"📡 API ROUTE: Using SERVICE LAYER to process CSV: {file.filename}")
        
        # Reset file pointer in case it was read elsewhere
        file.file.seek(0)
        
        result = parser_service.process_uploaded_file(
            file=file,
            user_id=current_user.user_id,
            account_id=account_id,
            use_legacy_csv=False,  # Use enhanced parser (combines best of both)
            auto_create_account=True  # Auto-create account from CSV metadata if needed
        )
        
        # Get account_id from result if it was auto-created from metadata
        if not account_id and 'account_id' in result:
            account_id = result['account_id']
            logger.info(f"📡 API ROUTE: Account auto-created from CSV metadata: {account_id}")
        
        logger.info("=" * 80)
        logger.info("📡 API ROUTE: ✅ Service Layer processed file successfully")
        logger.info(f"📡 API ROUTE: Transactions imported: {result['transactions_imported']}")
        logger.info(f"📡 API ROUTE: Account ID: {account_id or 'None (will be created if metadata available)'}")
        logger.info("=" * 80)
        
        # Additional tracking: Count EMIs and Investments from imported transactions
        # Note: The service layer already enriched and inserted transactions
        # We're just doing additional analysis for reporting
        emis_count = 0
        investments_count = 0
        
        # Get imported transactions to count EMIs/Investments
        # This is optional - just for the response statistics
        imported_transactions = session.query(Transaction).filter(
            Transaction.user_id == current_user.user_id,
            Transaction.source == 'csv_upload'
        ).order_by(Transaction.created_at.desc()).limit(result['transactions_imported']).all()
        
        for txn in imported_transactions:
            description = (txn.description_raw or txn.clean_description or '').lower()
            if is_emi_transaction(description):
                emis_count += 1
            elif is_investment_transaction(description):
                investments_count += 1
        
        logger.info(f"📡 API ROUTE: Analysis - EMIs: {emis_count}, Investments: {investments_count}")
        
        return {
            "filename": file.filename,
            "transactions_created": result['transactions_imported'],
            "transactions_found": result['transactions_found'],
            "assets_created": 0,  # Not auto-creating assets
            "emis_identified": emis_count,
            "duplicates_found": result['duplicates_found'],
            "status": "success",
            "message": f"Successfully imported {result['transactions_imported']} transactions"
        }
        
    except ValueError as e:
        logger.error("=" * 80)
        logger.error(f"📡 API ROUTE: ❌ Validation error: {e}")
        logger.error("=" * 80)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error("=" * 80)
        logger.error(f"📡 API ROUTE: ❌ Error processing CSV: {e}", exc_info=True)
        logger.error("=" * 80)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process CSV: {str(e)}"
        )
    finally:
        session.close()
        db.close()


@router.post("/pdf-smart")
async def upload_pdf_smart(
    file: UploadFile = File(...),
    account_id: str = Form(None),
    current_user: User = Depends(get_current_user),
    parser_service: ParserService = Depends(get_parser_service)
):
    """
    Upload and process PDF file using Service Layer
    
    Uses complete service layer architecture:
    - ParserService for file parsing (via ParserFactory)
    - TransactionEnrichmentService for merchant normalization, categorization, deduplication
    - TransactionRepository for database operations
    
    Still tracks EMIs and investments for additional features.
    """
    
    logger.info("=" * 80)
    logger.info("📡 API ROUTE: /api/v1/upload/pdf-smart (Using Service Layer) - Request received")
    logger.info(f"📡 API ROUTE: User: {current_user.username} ({current_user.user_id})")
    logger.info(f"📡 API ROUTE: File: {file.filename}")
    logger.info(f"📡 API ROUTE: Account ID: {account_id or 'None'}")
    logger.info("📡 API ROUTE: Delegating to ParserService...")
    logger.info("=" * 80)
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported"
        )
    
    db = get_db()
    session = db.get_session()
    
    try:
        # USE SERVICE LAYER: Process file end-to-end
        # The service layer handles file saving internally
        logger.info(f"📡 API ROUTE: Using SERVICE LAYER to process PDF: {file.filename}")
        
        # Reset file pointer in case it was read elsewhere
        file.file.seek(0)
        
        result = parser_service.process_uploaded_file(
            file=file,
            user_id=current_user.user_id,
            account_id=account_id,
            use_legacy_csv=False,  # Not applicable for PDF, but keep for consistency
            auto_create_account=True  # Auto-create account from PDF metadata if needed
        )
        
        # Get account_id from result if it was auto-created from metadata
        if not account_id and 'account_id' in result:
            account_id = result['account_id']
            logger.info(f"📡 API ROUTE: Account auto-created from PDF metadata: {account_id}")
        
        logger.info("=" * 80)
        logger.info("📡 API ROUTE: ✅ Service Layer processed file successfully")
        logger.info(f"📡 API ROUTE: Transactions imported: {result['transactions_imported']}")
        logger.info("=" * 80)
        
        # Handle account creation if account_id not provided
        if not account_id:
            account_id = str(uuid.uuid4())
            default_account = Account(
                account_id=account_id,
                user_id=current_user.user_id,
                account_name='Uploaded Bank Account',  # Ensure account_name is set
                account_type='current',
                bank_name='Uploaded Bank Account',
                current_balance=0.0,  # Default balance to 0.0
                is_active=True
            )
            session.add(default_account)
            session.commit()
            logger.info(f"📡 API ROUTE: Created default account: {account_id}")
        
        # Additional tracking: Count EMIs and Investments from imported transactions
        # Note: The service layer already enriched and inserted transactions
        # We're just doing additional analysis for reporting
        emis_count = 0
        investments_count = 0
        
        # Get imported transactions to count EMIs/Investments
        # This is optional - just for the response statistics
        imported_transactions = session.query(Transaction).filter(
            Transaction.user_id == current_user.user_id,
            Transaction.source == 'pdf_upload'
        ).order_by(Transaction.created_at.desc()).limit(result['transactions_imported']).all()
        
        for txn in imported_transactions:
            description = (txn.description_raw or txn.clean_description or '').lower()
            if is_emi_transaction(description):
                emis_count += 1
            elif is_investment_transaction(description):
                investments_count += 1
        
        logger.info(f"📡 API ROUTE: Analysis - EMIs: {emis_count}, Investments: {investments_count}")
        
        return {
            "filename": file.filename,
            "transactions_created": result['transactions_imported'],
            "transactions_found": result['transactions_found'],
            "assets_created": 0,  # Not auto-creating assets
            "emis_identified": emis_count,
            "duplicates_found": result['duplicates_found'],
            "status": "success",
            "message": f"Successfully imported {result['transactions_imported']} transactions"
        }
        
    except ValueError as e:
        logger.error("=" * 80)
        logger.error(f"📡 API ROUTE: ❌ Validation error: {e}")
        logger.error("=" * 80)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error("=" * 80)
        logger.error(f"📡 API ROUTE: ❌ Error processing PDF: {e}", exc_info=True)
        logger.error("=" * 80)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process PDF: {str(e)}"
        )
    finally:
        session.close()
        db.close()
