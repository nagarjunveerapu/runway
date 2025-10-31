"""
Migration: Fix NULL Balance Unique Constraint

SQLite UNIQUE constraint treats NULL as distinct, meaning:
- (user_id, account_id, date, amount, desc, NULL) ≠ (user_id, account_id, date, amount, desc, NULL)

This allows duplicate transactions with NULL balance to be inserted.

Solution: Use COALESCE in unique index to normalize NULL balance to a sentinel value.

Run with: python migrations/fix_null_balance_unique_constraint.py
"""

import sys
from pathlib import Path
import sqlite3
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Fix unique constraint to handle NULL balance correctly"""
    try:
        logger.info("Starting migration: Fix NULL balance unique constraint")
        
        # Get database path
        db_url = Config.DATABASE_URL
        if db_url.startswith('sqlite:///'):
            db_path = Path(db_url.split('sqlite:///')[-1])
        else:
            logger.error(f"Unsupported database URL: {db_url}")
            return False
        
        if not db_path.exists():
            logger.error(f"Database not found: {db_path}")
            return False
        
        logger.info(f"Database path: {db_path}")
        
        # Connect to database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Step 1: Find duplicate transactions with NULL balance
        logger.info("Scanning for duplicate transactions with NULL balance...")
        cursor.execute("""
            SELECT user_id, account_id, date, amount, description_raw, COUNT(*) as cnt
            FROM transactions
            WHERE balance IS NULL
            GROUP BY user_id, account_id, date, amount, description_raw
            HAVING cnt > 1
        """)
        duplicates = cursor.fetchall()
        
        if duplicates:
            logger.warning(f"⚠️  Found {len(duplicates)} groups of duplicate transactions with NULL balance")
            total_duplicates = sum(cnt for _, _, _, _, _, cnt in duplicates)
            logger.warning(f"   Total duplicate transactions: {total_duplicates}")
            logger.info("   Will remove duplicates (keeping oldest) before creating new index")
        else:
            logger.info("✅ No duplicate transactions with NULL balance found")
            total_duplicates = 0
        
        # Step 2: Remove duplicate transactions with NULL balance (keep oldest)
        if duplicates:
            logger.info(f"Removing {total_duplicates} duplicate transactions (keeping oldest)...")
            removed_count = 0
            
            for user_id, account_id, date, amount, desc, cnt in duplicates:
                # Keep the oldest transaction (lowest transaction_id or earliest created_at)
                # Delete others
                if account_id:
                    cursor.execute("""
                        DELETE FROM transactions
                        WHERE transaction_id NOT IN (
                            SELECT transaction_id
                            FROM transactions
                            WHERE user_id = ? AND account_id = ? AND date = ? 
                              AND amount = ? AND description_raw = ? AND balance IS NULL
                            ORDER BY created_at ASC, transaction_id ASC
                            LIMIT 1
                        )
                        AND user_id = ? AND account_id = ? AND date = ? 
                          AND amount = ? AND description_raw = ? AND balance IS NULL
                    """, (user_id, account_id, date, amount, desc, 
                          user_id, account_id, date, amount, desc))
                else:
                    # Handle NULL account_id
                    cursor.execute("""
                        DELETE FROM transactions
                        WHERE transaction_id NOT IN (
                            SELECT transaction_id
                            FROM transactions
                            WHERE user_id = ? AND account_id IS NULL AND date = ? 
                              AND amount = ? AND description_raw = ? AND balance IS NULL
                            ORDER BY created_at ASC, transaction_id ASC
                            LIMIT 1
                        )
                        AND user_id = ? AND account_id IS NULL AND date = ? 
                          AND amount = ? AND description_raw = ? AND balance IS NULL
                    """, (user_id, date, amount, desc,
                          user_id, date, amount, desc))
                
                removed_count += cursor.rowcount
            
            conn.commit()
            logger.info(f"✅ Removed {removed_count} duplicate transactions")
        
        # Step 3: Drop old unique index
        logger.info("Dropping old unique index...")
        try:
            cursor.execute("DROP INDEX IF EXISTS idx_transaction_unique")
            conn.commit()
            logger.info("✅ Old index dropped successfully")
        except Exception as e:
            logger.warning(f"⚠️  Could not drop old index (might not exist): {e}")
        
        # Step 4: Create new unique index with COALESCE
        logger.info("Creating new unique index with NULL normalization...")
        try:
            cursor.execute("""
                CREATE UNIQUE INDEX idx_transaction_unique 
                ON transactions(
                    user_id, 
                    account_id, 
                    date, 
                    amount, 
                    description_raw, 
                    COALESCE(balance, -999999999.99)
                )
            """)
            conn.commit()
            logger.info("✅ New unique index created successfully!")
            logger.info("   NULL balance normalized to -999999999.99 for comparison")
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Error creating new index: {e}")
            raise
        
        # Step 5: Verify
        logger.info("Verifying new constraint...")
        cursor.execute("""
            SELECT name, sql FROM sqlite_master 
            WHERE type='index' AND name='idx_transaction_unique'
        """)
        result = cursor.fetchone()
        
        if result:
            logger.info(f"✅ Index verified: {result[0]}")
            logger.info(f"   SQL: {result[1]}")
        else:
            logger.warning("⚠️  Could not verify index creation")
        
        conn.close()
        logger.info("✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = run_migration()
    if success:
        print("\n✅ Migration completed successfully!")
        print("   Unique constraint now handles NULL balance correctly")
        print("   Duplicate transactions with NULL balance will be prevented")
        sys.exit(0)
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)

