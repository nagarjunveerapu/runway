"""
Parser Service - Main Service Layer for File Parsing

Orchestrates the complete parsing workflow:
1. File type detection (factory pattern)
2. File parsing
3. Transaction enrichment
4. Duplicate detection
5. Database persistence

This service layer separates business logic from route handlers and database operations.
"""

import logging
import tempfile
import shutil
import os
from pathlib import Path
from typing import Tuple, Optional, Dict
from fastapi import UploadFile

from services.parser_service.parser_factory import ParserFactory
from services.parser_service.transaction_repository import TransactionRepository  # DEPRECATED - kept for backward compatibility
from services.parser_service.transaction_enrichment_service import TransactionEnrichmentService
from services.credit_card_service import CreditCardService
from services.bank_transaction_service.bank_transaction_repository import BankTransactionRepository
from services.credit_card_transaction_service.credit_card_transaction_repository import CreditCardTransactionRepository
from storage.database import DatabaseManager
from storage.models import Account
import uuid

logger = logging.getLogger(__name__)


class ParserService:
    """
    Main service for file parsing workflow
    
    Coordinates between:
    - ParserFactory (file type detection & parser creation)
    - ParserInterface implementations (actual parsing)
    - TransactionEnrichmentService (merchant normalization, categorization, deduplication)
    - TransactionRepository (database operations)
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize parser service
        
        Args:
            db_manager: DatabaseManager instance for database operations
        """
        self.db_manager = db_manager
        self.transaction_repository = TransactionRepository(db_manager)  # DEPRECATED - kept for backward compatibility
        self.bank_transaction_repository = BankTransactionRepository(db_manager)
        self.credit_card_transaction_repository = CreditCardTransactionRepository(db_manager)
        self.enrichment_service = TransactionEnrichmentService()
        self.credit_card_service = CreditCardService(db_manager)
    
    def process_uploaded_file(
        self,
        file: UploadFile,
        user_id: str,
        account_id: Optional[str] = None,
        bank_name: Optional[str] = None,
        use_legacy_csv: bool = False,
        auto_create_account: bool = True
    ) -> dict:
        """
        Process uploaded file end-to-end
        
        This is the main entry point for processing uploaded files.
        It handles the complete workflow:
        1. Validate file type
        2. Save file temporarily
        3. Detect file type and create parser (factory pattern)
        4. Parse transactions
        5. Enrich transactions (merchant normalization, categorization)
        6. Detect and handle duplicates
        7. Persist to database
        8. Cleanup temporary file
        
        Args:
            file: FastAPI UploadFile object
            user_id: User ID for the transactions
            account_id: Optional account ID
            bank_name: Optional bank name for bank-specific parsing
            use_legacy_csv: Whether to use legacy CSV parser
            
        Returns:
            Dictionary with processing results:
            - transactions_found: Number of transactions parsed
            - transactions_imported: Number successfully inserted
            - duplicates_found: Number of duplicates detected
            - status: 'success' or 'error'
            - message: Status message
            
        Raises:
            ValueError: If file type is unsupported
            Exception: If parsing or database operations fail
        """
        logger.info("=" * 80)
        logger.info("🚀 PARSER SERVICE: Starting file processing workflow")
        logger.info("=" * 80)
        logger.info(f"📄 File: {file.filename}")
        logger.info(f"👤 User ID: {user_id}")
        logger.info(f"🏦 Account ID: {account_id or 'None'}")
        logger.info(f"🏪 Bank Name: {bank_name or 'None'}")
        logger.info(f"📜 Use Legacy CSV: {use_legacy_csv}")
        
        temp_file = None
        
        try:
            # Step 1: Validate file type
            logger.info("\n[STEP 1] 🔍 Validating file type...")
            if not ParserFactory.validate_file_type(file.filename, file.content_type):
                logger.error(f"❌ Unsupported file type: {file.filename}")
                raise ValueError(
                    f"Unsupported file type. Supported: PDF (.pdf), CSV (.csv)"
                )
            logger.info(f"✅ File type validated: {file.filename}")
            
            # Step 2: Save uploaded file temporarily
            logger.info("\n[STEP 2] 💾 Saving file temporarily...")
            file_extension = Path(file.filename).suffix
            
            # Reset file pointer to beginning in case it was read before
            file.file.seek(0)
            
            # Get file size before saving for verification
            file.file.seek(0, 2)  # Seek to end
            original_size = file.file.tell()
            file.file.seek(0)  # Reset to beginning
            
            logger.info(f"📊 Original file size: {original_size} bytes")
            
            if original_size == 0:
                raise ValueError("Uploaded file is empty")
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp:
                bytes_written = shutil.copyfileobj(file.file, temp)
                temp_file = temp.name
                temp.flush()  # Ensure data is written to disk
                os.fsync(temp.fileno())  # Force write to disk
            
            # Verify file was saved correctly
            if not Path(temp_file).exists():
                raise ValueError(f"Failed to save temporary file: {temp_file}")
            
            file_size = Path(temp_file).stat().st_size
            logger.info(f"📊 Saved file size: {file_size} bytes")
            
            if file_size == 0:
                raise ValueError(f"Saved file is empty: {temp_file}")
            
            if file_size != original_size:
                logger.warning(f"⚠️  File size mismatch: original={original_size}, saved={file_size}")
            
            logger.info(f"✅ File saved to: {temp_file} (size: {file_size} bytes)")
            
            # Step 3: Detect file type and create parser (factory pattern)
            logger.info("\n[STEP 3] 🏭 PARSER FACTORY: Detecting file type and creating parser...")
            parser = ParserFactory.create_parser(
                file_path=temp_file,
                filename=file.filename,
                content_type=file.content_type,
                bank_name=bank_name,
                use_legacy_csv=use_legacy_csv
            )
            logger.info(f"✅ Parser created: {type(parser).__name__}")
            
            # Step 4: Parse transactions
            logger.info("\n[STEP 4] 📊 Parsing transactions from file...")
            transactions = parser.parse(temp_file)
            
            # Extract metadata if available (CSV parser returns metadata)
            metadata = {}
            if hasattr(parser, 'get_metadata'):
                metadata = parser.get_metadata()
                if metadata:
                    logger.info(f"✅ Extracted metadata: Account={metadata.get('account_number')}, Bank={metadata.get('bank_name')}, Holder={metadata.get('account_holder_name')}")
            
            # Handle account creation/update from metadata if account_id not provided
            # Check if metadata has any useful information (account_number, bank_name, or account_holder_name)
            metadata_has_info = (
                metadata.get('account_number') or 
                metadata.get('bank_name') or 
                metadata.get('account_holder_name') or
                metadata.get('card_last_4_digits')
            )
            
            if not account_id and auto_create_account:
                # Check if this is a credit card statement
                is_credit_card = metadata.get('account_type') == 'credit_card'
                
                if metadata_has_info:
                    if is_credit_card:
                        logger.info(f"💳 Creating/updating credit card account from metadata...")
                        account_id = self.credit_card_service.create_or_update_credit_card_account(
                            user_id=user_id,
                            metadata=metadata
                        )
                        if account_id:
                            logger.info(f"✅ Created/updated credit card account: {account_id}")
                    else:
                        logger.info(f"🔄 Creating/updating account from metadata...")
                        account_id = self._create_or_update_account_from_metadata(
                            user_id=user_id,
                            metadata=metadata,
                            bank_name=bank_name
                        )
                        if account_id:
                            logger.info(f"✅ Created/updated account from metadata: {account_id}")
                else:
                    # If no metadata but auto_create_account is True, create a default account
                    logger.info(f"⚠️  No metadata found, creating default account...")
                    account_id = self._create_default_account(user_id=user_id, bank_name=bank_name)
                    if account_id:
                        logger.info(f"✅ Created default account: {account_id}")
            
            if not transactions:
                logger.error("❌ No transactions found in file")
                raise ValueError("No transactions found in file")
            
            logger.info(f"✅ Parsed {len(transactions)} transactions from {file.filename}")
            
            # Step 5: Enrich transactions
            logger.info("\n[STEP 5] ✨ ENRICHMENT SERVICE: Enriching transactions...")
            # Add source information
            from storage.models import TransactionSource
            source = TransactionSource.PDF.value if file.filename.lower().endswith('.pdf') else TransactionSource.CSV.value
            for txn in transactions:
                txn['source'] = source
            
            # Enrich transactions (merchant normalization, categorization)
            # NOTE: Duplicate detection is NOT done within the same file - bank statements don't have duplicates
            # Duplicate detection only happens at database level via unique constraint when:
            # - Same CSV is uploaded again
            # - Another CSV with overlapping transactions is uploaded
            # Use enrich_and_deduplicate to get EMI conversion detection
            enriched_transactions, dedup_stats = self.enrichment_service.enrich_and_deduplicate(transactions, check_against_database=False)
            emi_converted_count = dedup_stats.get('emi_converted_count', 0)
            logger.info(f"✅ Enriched {len(enriched_transactions)} transactions (EMI conversions: {emi_converted_count})")
            
            # Step 6: Persist to database
            logger.info("\n[STEP 6] 💾 TRANSACTION REPOSITORY: Persisting to database...")
            
            # Determine account type to route to appropriate repository
            account_type = None
            if account_id:
                session = self.db_manager.get_session()
                try:
                    account = session.query(Account).filter(
                        Account.account_id == account_id
                    ).first()
                    if account and account.account_type:
                        account_type = account.account_type.lower()
                finally:
                    session.close()
            
            # Route to appropriate repository based on account type
            if account_type in ['credit_card', 'credit']:
                logger.info(f"💳 Routing to CreditCardTransactionRepository (account_type: {account_type})")
                # Use credit card repository
                session = self.db_manager.get_session()
                try:
                    inserted_count = 0
                    statement_id = None
                    if metadata.get('statement_id'):
                        statement_id = metadata.get('statement_id')
                    
                    for txn_dict in enriched_transactions:
                        try:
                            self.credit_card_transaction_repository.create_transaction(
                                txn_dict,
                                user_id,
                                account_id,
                                statement_id,
                                session=session
                            )
                            inserted_count += 1
                            if inserted_count % 100 == 0:
                                session.commit()
                                logger.info(f"   Progress: {inserted_count}/{len(enriched_transactions)} transactions inserted...")
                        except Exception as e:
                            # Handle duplicates and other errors
                            error_msg = str(e)
                            if "UNIQUE constraint" in error_msg or "duplicate" in error_msg.lower():
                                logger.debug(f"   Duplicate transaction skipped: {txn_dict.get('date')} - {txn_dict.get('description_raw', '')[:50]}")
                            else:
                                logger.warning(f"   Error inserting transaction: {e}")
                            session.rollback()
                    
                    session.commit()
                    logger.info(f"✅ Successfully imported {inserted_count}/{len(enriched_transactions)} credit card transactions")
                except Exception as e:
                    session.rollback()
                    logger.error(f"❌ Error inserting credit card transactions: {e}")
                    raise
                finally:
                    session.close()
            else:
                # Use bank repository (default)
                logger.info(f"🏦 Routing to BankTransactionRepository (account_type: {account_type or 'default'})")
                session = self.db_manager.get_session()
                try:
                    inserted_count = 0
                    duplicate_count = 0
                    for txn_dict in enriched_transactions:
                        try:
                            self.bank_transaction_repository.create_transaction(
                                txn_dict,
                                user_id,
                                account_id,
                                session=session
                            )
                            session.commit()  # Commit each transaction individually
                            inserted_count += 1
                            if inserted_count % 100 == 0:
                                logger.info(f"   Progress: {inserted_count}/{len(enriched_transactions)} transactions inserted...")
                        except Exception as e:
                            # Handle duplicates and other errors - rollback only this transaction
                            session.rollback()
                            error_msg = str(e)
                            if "UNIQUE constraint" in error_msg or "duplicate" in error_msg.lower() or "UniqueViolation" in error_msg:
                                duplicate_count += 1
                                logger.debug(f"   Duplicate transaction skipped: {txn_dict.get('date')} - {txn_dict.get('description_raw', '')[:50]}")
                            else:
                                logger.warning(f"   Error inserting transaction: {e}")
                    
                    logger.info(f"✅ Successfully imported {inserted_count}/{len(enriched_transactions)} bank transactions ({duplicate_count} duplicates skipped)")
                except Exception as e:
                    session.rollback()
                    logger.error(f"❌ Error inserting bank transactions: {e}")
                    raise
                finally:
                    session.close()
            
            # Create credit card statement record if this is a credit card statement
            if metadata.get('account_type') == 'credit_card' and account_id:
                logger.info("\n💳 Creating credit card statement record...")
                source_type = 'csv' if file.filename.lower().endswith('.csv') else 'pdf'
                
                # Add transaction count to metadata
                metadata_with_count = {**metadata, 'transaction_count': len(transactions)}
                
                statement_id = self.credit_card_service.create_credit_card_statement_record(
                    user_id=user_id,
                    account_id=account_id,
                    metadata=metadata_with_count,
                    filename=file.filename,
                    source_type=source_type
                )
                if statement_id:
                    logger.info(f"✅ Created credit card statement record: {statement_id}")
            
            logger.info("\n" + "=" * 80)
            logger.info("✅ PARSER SERVICE: File processing completed successfully!")
            logger.info("=" * 80)
            
            # Duplicates found = transactions skipped due to unique constraint violations
            # This happens when the same CSV is uploaded again or another CSV has overlapping transactions
            duplicates_found = len(enriched_transactions) - inserted_count
            
            result = {
                'transactions_found': len(transactions),
                'transactions_imported': inserted_count,
                'duplicates_found': duplicates_found,
                'status': 'success',
                'account_id': account_id,  # Include account_id in result (may be newly created)
                'message': f"Successfully imported {inserted_count} transactions"
            }
            
            return result
            
        except ValueError as e:
            logger.error("=" * 80)
            logger.error(f"❌ PARSER SERVICE: Validation error processing {file.filename}: {e}")
            logger.error("=" * 80)
            raise
        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"❌ PARSER SERVICE: Error processing file {file.filename}: {e}", exc_info=True)
            logger.error("=" * 80)
            raise
        finally:
            # Step 7: Cleanup temporary file
            logger.info("\n[STEP 7] 🧹 Cleaning up temporary file...")
            if temp_file and Path(temp_file).exists():
                try:
                    Path(temp_file).unlink()
                    logger.info(f"✅ Temporary file deleted: {temp_file}")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to delete temp file {temp_file}: {e}")
    
    def _create_or_update_account_from_metadata(
        self,
        user_id: str,
        metadata: Dict,
        bank_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Create or update account from CSV metadata
        
        Args:
            user_id: User ID
            metadata: Metadata dictionary with account_number, account_holder_name, bank_name
            bank_name: Optional bank name override
            
        Returns:
            Account ID if created/updated, None otherwise
        """
        session = self.db_manager.get_session()
        
        try:
            account_number = metadata.get('account_number')
            account_holder_name = metadata.get('account_holder_name')
            detected_bank_name = metadata.get('bank_name') or bank_name
            
            if not account_number and not detected_bank_name:
                logger.info("⚠️  No account number or bank name in metadata, skipping account creation")
                return None
            
            # Try to find existing account by account_number
            existing_account = None
            if account_number:
                existing_account = session.query(Account).filter(
                    Account.user_id == user_id,
                    Account.account_number_ref == account_number
                ).first()
            
            if existing_account:
                # Update existing account with metadata
                logger.info(f"🔄 Updating existing account: {existing_account.account_id}")
                if account_holder_name and not existing_account.account_name:
                    existing_account.account_name = account_holder_name
                if detected_bank_name and not existing_account.bank_name:
                    existing_account.bank_name = detected_bank_name
                session.commit()
                return existing_account.account_id
            else:
                # Create new account
                logger.info(f"🆕 Creating new account from metadata")
                new_account_id = str(uuid.uuid4())
                
                # Determine account name
                if account_holder_name:
                    account_name = account_holder_name
                elif detected_bank_name:
                    account_name = f"{detected_bank_name} Account"
                else:
                    account_name = "Uploaded Bank Account"
                
                # Determine account type from metadata or defaults
                # Check if metadata has account_type hint, otherwise infer from bank_name/context
                account_type = metadata.get('account_type', 'savings')  # Default to savings
                
                # Infer account type from bank name or account number patterns if not explicitly set
                if account_type == 'savings' and detected_bank_name:
                    bank_lower = detected_bank_name.lower()
                    if 'credit' in bank_lower or 'card' in bank_lower:
                        account_type = 'credit_card'
                    elif 'current' in bank_lower or 'salary' in bank_lower:
                        account_type = 'current'
                
                new_account = Account(
                    account_id=new_account_id,
                    user_id=user_id,
                    account_name=account_name,
                    bank_name=detected_bank_name or "Unknown Bank",
                    account_type=account_type,
                    account_number_ref=account_number,  # Store account number in reference
                    currency='INR',
                    current_balance=0.0,  # Default to 0.0
                    is_active=True
                )
                
                session.add(new_account)
                session.commit()
                session.refresh(new_account)
                
                logger.info(f"✅ Created account: {new_account_id} - {account_name} ({detected_bank_name})")
                return new_account_id
                
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Error creating/updating account from metadata: {e}", exc_info=True)
            return None
        finally:
            session.close()
    
    def _create_default_account(self, user_id: str, bank_name: Optional[str] = None) -> Optional[str]:
        """
        Create a default account when metadata is not available
        
        Args:
            user_id: User ID
            bank_name: Optional bank name from route
            
        Returns:
            Account ID if created successfully, None otherwise
        """
        session = self.db_manager.get_session()
        try:
            new_account_id = str(uuid.uuid4())
            
            account_name = f"{bank_name} Account" if bank_name else "Uploaded Bank Account"
            
            new_account = Account(
                account_id=new_account_id,
                user_id=user_id,
                account_name=account_name,
                bank_name=bank_name or "Unknown Bank",
                account_type='savings',
                account_number_ref=None,
                currency='INR',
                current_balance=0.0,
                is_active=True
            )
            
            session.add(new_account)
            session.commit()
            session.refresh(new_account)
            
            logger.info(f"✅ Created default account: {new_account_id} - {account_name}")
            return new_account_id
                
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Error creating default account: {e}", exc_info=True)
            return None
        finally:
            session.close()
    
    def parse_file_only(
        self,
        file_path: str,
        filename: str,
        content_type: Optional[str] = None,
        bank_name: Optional[str] = None
    ) -> list:
        """
        Parse file without enrichment or database operations
        
        Useful for testing or when you only need parsed data.
        
        Args:
            file_path: Path to the file
            filename: Original filename
            content_type: MIME type if available
            bank_name: Optional bank name for bank-specific parsing
            
        Returns:
            List of raw transaction dictionaries
        """
        parser = ParserFactory.create_parser(
            file_path=file_path,
            filename=filename,
            content_type=content_type,
            bank_name=bank_name
        )
        
        return parser.parse(file_path)

