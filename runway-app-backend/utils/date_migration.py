"""
Date Migration Utility

This module provides tools to normalize all dates in the database to ISO format (YYYY-MM-DD).
"""

import sqlite3
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.date_parser import parse_date

logger = logging.getLogger(__name__)


def migrate_transaction_dates(db_path='data/finance.db'):
    """
    Migrate all transaction dates to ISO format (YYYY-MM-DD)
    
    Args:
        db_path: Path to SQLite database
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get all transactions
        cursor.execute("SELECT transaction_id, date FROM transactions")
        transactions = cursor.fetchall()
        
        updated_count = 0
        skipped_count = 0
        
        for txn_id, old_date in transactions:
            if not old_date:
                skipped_count += 1
                continue
            
            # Check if already in ISO format
            if old_date.startswith('20') and len(old_date) == 10 and old_date[4] == '-' and old_date[7] == '-':
                skipped_count += 1
                continue
            
            # Parse to ISO format
            new_date = parse_date(old_date)
            
            if new_date and new_date != old_date:
                cursor.execute(
                    "UPDATE transactions SET date = ? WHERE transaction_id = ?",
                    (new_date, txn_id)
                )
                updated_count += 1
                logger.info(f"Migrated transaction {txn_id[:8]}...: {old_date} -> {new_date}")
            elif not new_date:
                logger.warning(f"Could not parse date for transaction {txn_id[:8]}...: {old_date}")
                skipped_count += 1
        
        conn.commit()
        logger.info(f"Migration complete: {updated_count} updated, {skipped_count} skipped")
        
    finally:
        conn.close()


def migrate_liquidation_dates(db_path='data/finance.db'):
    """
    Migrate all liquidation dates to ISO format (YYYY-MM-DD)
    
    Args:
        db_path: Path to SQLite database
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get all liquidations
        cursor.execute("SELECT liquidation_id, date FROM liquidations")
        liquidations = cursor.fetchall()
        
        updated_count = 0
        skipped_count = 0
        
        for liq_id, old_date in liquidations:
            if not old_date:
                skipped_count += 1
                continue
            
            # Check if already in ISO format
            if old_date.startswith('20') and len(old_date) == 10 and old_date[4] == '-' and old_date[7] == '-':
                skipped_count += 1
                continue
            
            # Parse to ISO format
            new_date = parse_date(old_date)
            
            if new_date and new_date != old_date:
                cursor.execute(
                    "UPDATE liquidations SET date = ? WHERE liquidation_id = ?",
                    (new_date, liq_id)
                )
                updated_count += 1
                logger.info(f"Migrated liquidation {liq_id[:8]}...: {old_date} -> {new_date}")
            elif not new_date:
                logger.warning(f"Could not parse date for liquidation {liq_id[:8]}...: {old_date}")
                skipped_count += 1
        
        conn.commit()
        logger.info(f"Migration complete: {updated_count} updated, {skipped_count} skipped")
        
    finally:
        conn.close()


def migrate_all_dates(db_path='data/finance.db'):
    """
    Migrate all dates in the database to ISO format
    
    Args:
        db_path: Path to SQLite database
    """
    logger.info("Starting date migration...")
    migrate_transaction_dates(db_path)
    migrate_liquidation_dates(db_path)
    logger.info("Date migration complete!")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate database dates to ISO format')
    parser.add_argument('--db', default='data/finance.db', help='Database path')
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    migrate_all_dates(args.db)

