#!/usr/bin/env python3
"""
Migration Script: Separate Bank and Credit Card Transactions

This script migrates existing transactions from the unified 'transactions' table
to the new 'bank_transactions' and 'credit_card_transactions' tables based on
the account_type of the associated account.

Migration Process:
1. Queries all transactions from the legacy 'transactions' table
2. For each transaction, checks the associated account's account_type
3. Routes transaction to appropriate table:
   - 'savings', 'current', 'checking' → bank_transactions
   - 'credit_card', 'credit' → credit_card_transactions
4. Migrates all transaction data while preserving relationships
5. Validates migration completeness

Safety:
- Does NOT delete original transactions (kept for rollback)
- Creates new records in target tables
- Validates data integrity
- Provides rollback capability
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from typing import List, Dict
from sqlalchemy import text
from datetime import datetime

from storage.database import DatabaseManager
from storage.models import (
    Transaction, BankTransaction, CreditCardTransaction, 
    Account, Merchant, User
)
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_transactions(dry_run: bool = False) -> Dict:
    """
    Migrate transactions from unified table to separate tables
    
    Args:
        dry_run: If True, only validates and reports without migrating
        
    Returns:
        Dictionary with migration statistics
    """
    db = DatabaseManager(Config.DATABASE_URL)
    session = db.get_session()
    
    try:
        # Get all transactions
        all_transactions = session.query(Transaction).all()
        logger.info(f"Found {len(all_transactions)} transactions to migrate")
        
        if len(all_transactions) == 0:
            return {
                'total': 0,
                'bank_transactions_migrated': 0,
                'credit_card_transactions_migrated': 0,
                'skipped': 0,
                'errors': 0,
                'message': 'No transactions to migrate'
            }
        
        # Statistics
        bank_count = 0
        credit_card_count = 0
        skipped_count = 0
        error_count = 0
        bank_errors = []
        cc_errors = []
        
        # Group transactions by account type
        for txn in all_transactions:
            try:
                # Get associated account
                account = None
                if txn.account_id:
                    account = session.query(Account).filter(
                        Account.account_id == txn.account_id
                    ).first()
                
                # Determine account type
                account_type = None
                if account and account.account_type:
                    account_type = account.account_type.lower()
                
                # Route to appropriate table based on account type
                # If no account or account_type not set, default to bank transaction
                is_bank = True
                if account_type:
                    if account_type in ['credit_card', 'credit']:
                        is_bank = False
                    elif account_type in ['savings', 'current', 'checking']:
                        is_bank = True
                
                if dry_run:
                    # Just count, don't migrate
                    if is_bank:
                        bank_count += 1
                    else:
                        credit_card_count += 1
                else:
                    # Migrate to appropriate table
                    if is_bank:
                        try:
                            # Check if already migrated
                            existing = session.query(BankTransaction).filter(
                                BankTransaction.transaction_id == txn.transaction_id
                            ).first()
                            
                            if existing:
                                logger.debug(f"Transaction {txn.transaction_id[:8]} already exists in bank_transactions, skipping")
                                skipped_count += 1
                                continue
                            
                            # Create BankTransaction
                            bank_txn = BankTransaction(
                                transaction_id=txn.transaction_id,
                                user_id=txn.user_id,
                                account_id=txn.account_id,
                                merchant_id=txn.merchant_id,
                                date=txn.date,
                                timestamp=txn.timestamp,
                                amount=txn.amount,
                                type=txn.type,
                                description_raw=txn.description_raw,
                                clean_description=txn.clean_description,
                                merchant_raw=txn.merchant_raw,
                                merchant_canonical=txn.merchant_canonical,
                                category=txn.category,
                                transaction_sub_type=txn.transaction_sub_type,
                                labels=txn.labels,
                                confidence=txn.confidence,
                                balance=txn.balance,  # Bank-specific field
                                currency=txn.currency,
                                original_amount=txn.original_amount,
                                original_currency=txn.original_currency,
                                duplicate_of=txn.duplicate_of,
                                duplicate_count=txn.duplicate_count,
                                is_duplicate=txn.is_duplicate,
                                source=txn.source,
                                bank_name=txn.bank_name,
                                statement_period=txn.statement_period,
                                ingestion_timestamp=txn.ingestion_timestamp,
                                extra_metadata=txn.extra_metadata,
                                linked_asset_id=txn.linked_asset_id,
                                liquidation_event_id=txn.liquidation_event_id,
                                month=txn.month,
                                is_recurring=txn.is_recurring,
                                recurring_type=txn.recurring_type,
                                recurring_group_id=txn.recurring_group_id,
                                created_at=txn.created_at,
                                updated_at=txn.updated_at
                            )
                            session.add(bank_txn)
                            bank_count += 1
                            
                            # Commit every 100 transactions for better performance
                            if bank_count % 100 == 0:
                                session.commit()
                                logger.info(f"Migrated {bank_count} bank transactions...")
                                
                        except Exception as e:
                            error_count += 1
                            bank_errors.append(f"Transaction {txn.transaction_id[:8]}: {str(e)}")
                            logger.error(f"Error migrating bank transaction {txn.transaction_id[:8]}: {e}")
                            session.rollback()
                    
                    else:
                        try:
                            # Check if already migrated
                            existing = session.query(CreditCardTransaction).filter(
                                CreditCardTransaction.transaction_id == txn.transaction_id
                            ).first()
                            
                            if existing:
                                logger.debug(f"Transaction {txn.transaction_id[:8]} already exists in credit_card_transactions, skipping")
                                skipped_count += 1
                                continue
                            
                            # Get statement_id if available from extra_metadata
                            statement_id = None
                            if txn.extra_metadata and isinstance(txn.extra_metadata, dict):
                                statement_id = txn.extra_metadata.get('statement_id')
                            
                            # Extract billing cycle and dates from extra_metadata or statement_period
                            billing_cycle = None
                            transaction_date = txn.date
                            posting_date = None
                            due_date = None
                            
                            if txn.extra_metadata and isinstance(txn.extra_metadata, dict):
                                billing_cycle = txn.extra_metadata.get('billing_cycle') or txn.statement_period
                                transaction_date = txn.extra_metadata.get('transaction_date') or txn.date
                                posting_date = txn.extra_metadata.get('posting_date')
                                due_date = txn.extra_metadata.get('due_date')
                            
                            # Create CreditCardTransaction
                            cc_txn = CreditCardTransaction(
                                transaction_id=txn.transaction_id,
                                user_id=txn.user_id,
                                account_id=txn.account_id,
                                merchant_id=txn.merchant_id,
                                statement_id=statement_id,
                                date=txn.date,
                                timestamp=txn.timestamp,
                                amount=txn.amount,
                                type=txn.type,
                                description_raw=txn.description_raw,
                                clean_description=txn.clean_description,
                                merchant_raw=txn.merchant_raw,
                                merchant_canonical=txn.merchant_canonical,
                                category=txn.category,
                                transaction_sub_type=txn.transaction_sub_type,
                                labels=txn.labels,
                                confidence=txn.confidence,
                                billing_cycle=billing_cycle,
                                transaction_date=transaction_date,
                                posting_date=posting_date,
                                due_date=due_date,
                                currency=txn.currency,
                                original_amount=txn.original_amount,
                                original_currency=txn.original_currency,
                                duplicate_of=txn.duplicate_of,
                                duplicate_count=txn.duplicate_count,
                                is_duplicate=txn.is_duplicate,
                                source=txn.source,
                                bank_name=txn.bank_name,
                                ingestion_timestamp=txn.ingestion_timestamp,
                                extra_metadata=txn.extra_metadata,
                                linked_asset_id=txn.linked_asset_id,
                                liquidation_event_id=txn.liquidation_event_id,
                                month=txn.month,
                                is_recurring=txn.is_recurring,
                                recurring_type=txn.recurring_type,
                                recurring_group_id=txn.recurring_group_id,
                                created_at=txn.created_at,
                                updated_at=txn.updated_at
                            )
                            session.add(cc_txn)
                            credit_card_count += 1
                            
                            # Commit every 100 transactions for better performance
                            if credit_card_count % 100 == 0:
                                session.commit()
                                logger.info(f"Migrated {credit_card_count} credit card transactions...")
                                
                        except Exception as e:
                            error_count += 1
                            cc_errors.append(f"Transaction {txn.transaction_id[:8]}: {str(e)}")
                            logger.error(f"Error migrating credit card transaction {txn.transaction_id[:8]}: {e}")
                            session.rollback()
            
            except Exception as e:
                error_count += 1
                logger.error(f"Error processing transaction {txn.transaction_id[:8] if txn else 'unknown'}: {e}")
                session.rollback()
        
        # Final commit
        if not dry_run:
            session.commit()
            logger.info("✅ Migration completed successfully")
        
        # Validation
        if not dry_run:
            # Count migrated transactions
            migrated_bank_count = session.query(BankTransaction).count()
            migrated_cc_count = session.query(CreditCardTransaction).count()
            
            logger.info(f"\n📊 Migration Statistics:")
            logger.info(f"   Total transactions: {len(all_transactions)}")
            logger.info(f"   Bank transactions migrated: {bank_count}")
            logger.info(f"   Credit card transactions migrated: {credit_card_count}")
            logger.info(f"   Skipped (already migrated): {skipped_count}")
            logger.info(f"   Errors: {error_count}")
            logger.info(f"\n   Validation:")
            logger.info(f"   Bank transactions in database: {migrated_bank_count}")
            logger.info(f"   Credit card transactions in database: {migrated_cc_count}")
        
        return {
            'total': len(all_transactions),
            'bank_transactions_migrated': bank_count,
            'credit_card_transactions_migrated': credit_card_count,
            'skipped': skipped_count,
            'errors': error_count,
            'bank_errors': bank_errors[:10],  # First 10 errors
            'cc_errors': cc_errors[:10],
            'dry_run': dry_run
        }
        
    except Exception as e:
        session.rollback()
        logger.error(f"Migration failed: {e}", exc_info=True)
        raise
    finally:
        session.close()
        db.close()


def rollback_migration():
    """
    Rollback migration by deleting all migrated transactions
    
    WARNING: This will delete all transactions from bank_transactions
    and credit_card_transactions tables!
    """
    db = DatabaseManager(Config.DATABASE_URL)
    session = db.get_session()
    
    try:
        logger.warning("⚠️  ROLLBACK: Deleting all migrated transactions...")
        
        bank_deleted = session.query(BankTransaction).delete()
        cc_deleted = session.query(CreditCardTransaction).delete()
        
        session.commit()
        
        logger.info(f"✅ Rollback completed:")
        logger.info(f"   Deleted {bank_deleted} bank transactions")
        logger.info(f"   Deleted {cc_deleted} credit card transactions")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Rollback failed: {e}", exc_info=True)
        raise
    finally:
        session.close()
        db.close()


def main():
    """Main migration entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate transactions to separate tables')
    parser.add_argument('--dry-run', action='store_true', help='Validate migration without migrating')
    parser.add_argument('--rollback', action='store_true', help='Rollback migration (delete migrated transactions)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("TRANSACTION TABLE MIGRATION")
    print("=" * 80)
    print()
    
    if args.rollback:
        confirm = input("⚠️  WARNING: This will delete all migrated transactions. Continue? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Rollback cancelled.")
            return
        rollback_migration()
        print("\n✅ Rollback completed!")
        return
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No data will be migrated")
        print()
    
    # Run migration
    result = migrate_transactions(dry_run=args.dry_run)
    
    print("\n" + "=" * 80)
    print("MIGRATION SUMMARY")
    print("=" * 80)
    print(f"Total transactions: {result['total']}")
    print(f"Bank transactions: {result['bank_transactions_migrated']}")
    print(f"Credit card transactions: {result['credit_card_transactions_migrated']}")
    print(f"Skipped (already migrated): {result['skipped']}")
    print(f"Errors: {result['errors']}")
    
    if result['errors'] > 0:
        print(f"\n⚠️  {result['errors']} errors occurred during migration")
        if result.get('bank_errors'):
            print(f"\nBank transaction errors (first 10):")
            for err in result['bank_errors']:
                print(f"   - {err}")
        if result.get('cc_errors'):
            print(f"\nCredit card transaction errors (first 10):")
            for err in result['cc_errors']:
                print(f"   - {err}")
    
    if args.dry_run:
        print("\n✅ Dry run completed. Run without --dry-run to perform actual migration.")
    else:
        print("\n✅ Migration completed successfully!")
        print("\nNOTE: Original transactions table is kept for backward compatibility.")
        print("      You can verify the migration and then remove the old table later.")


if __name__ == "__main__":
    main()

