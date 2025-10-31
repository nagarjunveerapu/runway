"""
File Upload API Routes (Service Layer Version)

This version uses the new service layer architecture with:
- ParserFactory for file type detection
- ParserService for business logic
- TransactionRepository for database operations
- TransactionEnrichmentService for enrichment

Maintains backward compatibility with existing upload endpoints.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends
from typing import List, Optional
import sys
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.models.schemas import FileUploadResponse, BulkImportResponse
from services.parser_service import ParserService
from storage.database import DatabaseManager
from auth.dependencies import get_current_user
from config import Config

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db():
    """Get database instance"""
    return DatabaseManager(Config.DATABASE_URL)


def get_parser_service(db: DatabaseManager = Depends(get_db)) -> ParserService:
    """Get parser service instance"""
    return ParserService(db_manager=db)


@router.post("/csv", response_model=FileUploadResponse)
async def upload_csv(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    parser_service: ParserService = Depends(get_parser_service)
):
    """
    Upload and process a CSV bank statement (Service Layer Version)
    
    Uses the new service layer architecture:
    - ParserFactory detects file type
    - ParserService handles complete workflow
    - TransactionRepository handles database operations
    - TransactionEnrichmentService handles enrichment
    
    - **file**: CSV file containing bank transactions
    
    Returns summary of import operation
    """
    logger.info("=" * 80)
    logger.info("📡 API ROUTE: /api/v1/upload/csv (Service Layer) - Request received")
    logger.info(f"📡 API ROUTE: User: {current_user.username} ({current_user.user_id})")
    logger.info(f"📡 API ROUTE: File: {file.filename}")
    logger.info("📡 API ROUTE: Delegating to ParserService...")
    logger.info("=" * 80)
    
    try:
        result = parser_service.process_uploaded_file(
            file=file,
            user_id=current_user.user_id,
            account_id=None,
            use_legacy_csv=True  # Use legacy parser for backward compatibility
        )
        
        logger.info("=" * 80)
        logger.info("📡 API ROUTE: ✅ Request completed successfully")
        logger.info("=" * 80)
        
        return FileUploadResponse(
            filename=file.filename,
            transactions_found=result['transactions_found'],
            transactions_imported=result['transactions_imported'],
            duplicates_found=result['duplicates_found'],
            status=result['status'],
            message=result['message']
        )
        
    except ValueError as e:
        logger.error("=" * 80)
        logger.error(f"📡 API ROUTE: ❌ Validation error: {e}")
        logger.error("=" * 80)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"📡 API ROUTE: ❌ Error processing CSV upload: {e}", exc_info=True)
        logger.error("=" * 80)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process CSV: {str(e)}"
        )


@router.post("/pdf", response_model=FileUploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    account_id: Optional[str] = Form(None),
    current_user = Depends(get_current_user),
    parser_service: ParserService = Depends(get_parser_service)
):
    """
    Upload and process a PDF bank statement (Service Layer Version)
    
    Uses the new service layer architecture for complete workflow orchestration.
    
    - **file**: PDF file containing bank transactions
    - **account_id**: Optional account ID
    
    Returns summary of import operation
    """
    logger.info("=" * 80)
    logger.info("📡 API ROUTE: /api/v1/upload/pdf (Service Layer) - Request received")
    logger.info(f"📡 API ROUTE: User: {current_user.username} ({current_user.user_id})")
    logger.info(f"📡 API ROUTE: File: {file.filename}")
    logger.info(f"📡 API ROUTE: Account ID: {account_id or 'None'}")
    logger.info("📡 API ROUTE: Delegating to ParserService...")
    logger.info("=" * 80)
    
    try:
        result = parser_service.process_uploaded_file(
            file=file,
            user_id=current_user.user_id,
            account_id=account_id
        )
        
        logger.info("=" * 80)
        logger.info("📡 API ROUTE: ✅ Request completed successfully")
        logger.info("=" * 80)
        
        return FileUploadResponse(
            filename=file.filename,
            transactions_found=result['transactions_found'],
            transactions_imported=result['transactions_imported'],
            duplicates_found=result['duplicates_found'],
            status=result['status'],
            message=result['message']
        )
        
    except ValueError as e:
        logger.error("=" * 80)
        logger.error(f"📡 API ROUTE: ❌ Validation error: {e}")
        logger.error("=" * 80)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"📡 API ROUTE: ❌ Error processing PDF upload: {e}", exc_info=True)
        logger.error("=" * 80)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process PDF: {str(e)}"
        )


@router.post("/bulk", response_model=BulkImportResponse)
async def upload_bulk_files(
    files: List[UploadFile] = File(...),
    current_user = Depends(get_current_user),
    parser_service: ParserService = Depends(get_parser_service)
):
    """
    Upload and process multiple files in bulk (Service Layer Version)
    
    - **files**: List of CSV or PDF files
    
    Processes all files and returns aggregated results
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided"
        )
    
    results = []
    errors = []
    total_imported = 0
    total_found = 0
    
    for file in files:
        try:
            result = parser_service.process_uploaded_file(
                file=file,
                user_id=current_user.user_id,
                account_id=None,
                use_legacy_csv=file.filename.lower().endswith('.csv')
            )
            results.append(result)
            total_imported += result['transactions_imported']
            total_found += result['transactions_found']
            
        except HTTPException as e:
            errors.append(f"{file.filename}: {e.detail}")
        except ValueError as e:
            errors.append(f"{file.filename}: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing {file.filename}: {e}")
            errors.append(f"{file.filename}: {str(e)}")
    
    return BulkImportResponse(
        files_processed=len(results),
        total_transactions=total_found,
        successful_imports=total_imported,
        failed_imports=len(errors),
        errors=errors
    )

