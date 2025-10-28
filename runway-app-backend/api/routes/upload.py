"""
File Upload API Routes

Upload and process CSV/PDF bank statements
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends
from typing import List
import sys
from pathlib import Path
import logging
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.models.schemas import FileUploadResponse, BulkImportResponse
from src.csv_parser import parse_csv_file
from ingestion.pdf_parser import PDFParser
from storage.database import DatabaseManager
from storage.models import Transaction, User
from auth.dependencies import get_current_user
from schema import CanonicalTransaction
from deduplication.detector import DeduplicationDetector
from src.merchant_normalizer import MerchantNormalizer
from src.classifier import rule_based_category
from config import Config
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db():
    """Get database instance"""
    return DatabaseManager(Config.DATABASE_URL)


@router.post("/csv", response_model=FileUploadResponse)
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload and process a CSV bank statement

    - **file**: CSV file containing bank transactions

    The endpoint will:
    1. Parse the CSV file
    2. Normalize merchants
    3. Categorize transactions using ML
    4. Detect and handle duplicates
    5. Store in database

    Returns summary of import operation
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported"
        )

    temp_file = None

    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp:
            shutil.copyfileobj(file.file, temp)
            temp_file = temp.name

        logger.info(f"Processing uploaded CSV: {file.filename}")

        # Parse CSV file
        transactions = parse_csv_file(temp_file)

        if not transactions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No transactions found in CSV file"
            )

        logger.info(f"Parsed {len(transactions)} transactions from CSV")

        # Enrich transactions
        merchant_norm = MerchantNormalizer()

        for txn in transactions:
            # Normalize merchant
            merchant_raw = txn.get('merchant_raw') or txn.get('remark', '')
            merchant_canonical, score = merchant_norm.normalize(merchant_raw)
            txn['merchant_canonical'] = merchant_canonical

            # Categorize
            category = rule_based_category(
                txn.get('remark', ''),
                merchant_canonical
            )
            txn['category'] = category

        # Detect duplicates
        dedup = DeduplicationDetector(
            time_window_days=Config.DEDUP_TIME_WINDOW_DAYS,
            fuzzy_threshold=Config.DEDUP_FUZZY_THRESHOLD,
            merge_duplicates=Config.DEDUP_MERGE_DUPLICATES
        )

        clean_transactions = dedup.detect_duplicates(transactions)
        duplicate_stats = dedup.get_duplicate_stats(clean_transactions)

        logger.info(f"Deduplication: {len(transactions)} → {len(clean_transactions)} "
                   f"({duplicate_stats['merged_count']} duplicates merged)")

        # Convert to canonical schema
        canonical_txns = []
        for txn in clean_transactions:
            try:
                canonical = CanonicalTransaction(
                    transaction_id=txn.get('id'),
                    date=txn.get('date', ''),
                    amount=float(txn.get('amount', 0)),
                    type=txn.get('transaction_type', 'debit'),
                    description_raw=txn.get('raw_remark', ''),
                    clean_description=txn.get('remark', ''),
                    merchant_raw=txn.get('merchant_raw'),
                    merchant_canonical=txn.get('merchant_canonical'),
                    category=txn.get('category', 'Unknown'),
                    balance=float(txn.get('balance', 0)) if txn.get('balance') else None,
                    source='csv_upload',
                    is_duplicate=txn.get('is_duplicate', False),
                    duplicate_count=txn.get('duplicate_count', 0)
                )
                canonical_txns.append(canonical)
            except Exception as e:
                logger.warning(f"Failed to convert transaction: {e}")
                continue

        # Insert into database
        db = get_db()
        inserted = db.insert_transactions_batch(canonical_txns)
        db.close()

        logger.info(f"Inserted {inserted}/{len(canonical_txns)} transactions")

        return FileUploadResponse(
            filename=file.filename,
            transactions_found=len(transactions),
            transactions_imported=inserted,
            duplicates_found=duplicate_stats['merged_count'],
            status="success",
            message=f"Successfully imported {inserted} transactions"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing CSV upload: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process CSV: {str(e)}"
        )

    finally:
        # Clean up temporary file
        if temp_file and Path(temp_file).exists():
            Path(temp_file).unlink()


@router.post("/bulk", response_model=BulkImportResponse)
async def upload_bulk_files(files: List[UploadFile] = File(...)):
    """
    Upload and process multiple CSV files in bulk

    - **files**: List of CSV files

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
            if not file.filename.endswith('.csv'):
                errors.append(f"{file.filename}: Not a CSV file")
                continue

            # Process file (reuse single file upload logic)
            result = await upload_csv(file)
            results.append(result)
            total_imported += result.transactions_imported
            total_found += result.transactions_found

        except HTTPException as e:
            errors.append(f"{file.filename}: {e.detail}")
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


@router.post("/pdf", response_model=FileUploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    account_id: str = Form(None),
    current_user = Depends(get_current_user)
):
    """
    Upload and process a PDF bank statement

    - **file**: PDF file containing bank transactions

    The endpoint will:
    1. Parse the PDF file using multi-strategy extraction
    2. Normalize merchants
    3. Categorize transactions using ML
    4. Detect and handle duplicates
    5. Store in database

    Returns summary of import operation
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported"
        )

    temp_file = None

    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp:
            shutil.copyfileobj(file.file, temp)
            temp_file = temp.name

        logger.info(f"Processing uploaded PDF: {file.filename}")

        # Parse PDF file
        pdf_parser = PDFParser()
        transactions = pdf_parser.parse(temp_file)

        if not transactions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No transactions found in PDF file"
            )

        logger.info(f"Parsed {len(transactions)} transactions from PDF")

        # Enrich transactions
        merchant_norm = MerchantNormalizer()

        for txn in transactions:
            # Handle both PDF parser format ('description') and CSV format ('remark')
            description = txn.get('description') or txn.get('remark', '')

            # Normalize merchant
            merchant_raw = txn.get('merchant_raw') or description
            merchant_canonical, score = merchant_norm.normalize(merchant_raw)
            txn['merchant_canonical'] = merchant_canonical

            # Categorize
            category = rule_based_category(
                description,
                merchant_canonical
            )
            txn['category'] = category

        # Detect duplicates
        dedup = DeduplicationDetector(
            time_window_days=Config.DEDUP_TIME_WINDOW_DAYS,
            fuzzy_threshold=Config.DEDUP_FUZZY_THRESHOLD,
            merge_duplicates=Config.DEDUP_MERGE_DUPLICATES
        )

        clean_transactions = dedup.detect_duplicates(transactions)
        duplicate_stats = dedup.get_duplicate_stats(clean_transactions)

        logger.info(f"Deduplication: {len(transactions)} → {len(clean_transactions)} "
                   f"({duplicate_stats['merged_count']} duplicates merged)")

        # Insert transactions into database
        db = get_db()
        session = db.get_session()
        inserted = 0
        
        try:
            for txn in clean_transactions:
                try:
                    # Get date as string (YYYY-MM-DD format)
                    txn_date = txn.get('date', '') if txn.get('date') else datetime.now().strftime('%Y-%m-%d')
                    
                    # Create transaction record
                    # Handle both PDF parser format ('type', 'description') and CSV format ('transaction_type', 'remark')
                    txn_type = txn.get('type') or txn.get('transaction_type', 'debit')
                    description = txn.get('description') or txn.get('remark', '')
                    raw_description = txn.get('raw_remark') or txn.get('description', '')

                    db_transaction = Transaction(
                        transaction_id=str(uuid.uuid4()),
                        user_id=current_user.user_id,
                        account_id=account_id if account_id else None,
                        date=txn_date,
                        timestamp=datetime.now(),
                        amount=float(txn.get('amount', 0)),
                        type=txn_type,
                        description_raw=raw_description[:255] if raw_description else None,
                        clean_description=description[:255] if description else None,
                        merchant_raw=txn.get('merchant_raw', '')[:255] or None,
                        merchant_canonical=txn.get('merchant_canonical', '')[:255] or None,
                        category=txn.get('category', 'Unknown')[:100],
                        balance=float(txn.get('balance', 0)) if txn.get('balance') else None,
                        source='pdf_upload',
                        is_duplicate=txn.get('is_duplicate', False),
                        duplicate_count=txn.get('duplicate_count', 0)
                    )
                    
                    session.add(db_transaction)
                    inserted += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to insert transaction: {e}")
                    logger.exception(e)
                    continue
            
            session.commit()
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
            db.close()

        logger.info(f"Inserted {inserted}/{len(clean_transactions)} transactions")

        return FileUploadResponse(
            filename=file.filename,
            transactions_found=len(transactions),
            transactions_imported=inserted,
            duplicates_found=duplicate_stats['merged_count'],
            status="success",
            message=f"Successfully imported {inserted} transactions from PDF"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing PDF upload: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process PDF: {str(e)}"
        )

    finally:
        # Clean up temporary file
        if temp_file and Path(temp_file).exists():
            Path(temp_file).unlink()
