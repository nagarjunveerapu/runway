"""
Migration: Add Balance to Unique Constraint

Updates the unique constraint to include balance field, allowing transactions
with same date/amount/description but different balances to be stored separately.

This handles the case where the same transaction occurs multiple times in a day
but at different times (indicated by different balances).

Run with: python migrations/add_balance_to_unique_constraint.py
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
    """Update unique constraint to include balance"""
    try:
        logger.info("Starting migration: Add balance to unique constraint")
        
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
        
        # Step 1: Drop old unique index
        logger.info("Dropping old unique index...")
        try:
            cursor.execute("DROP INDEX IF EXISTS idx_transaction_unique")
            conn.commit()
            logger.info("✅ Old index dropped successfully")
        except Exception as e:
            logger.warning(f"⚠️  Could not drop old index (might not exist): {e}")
        
        # Step 2: Check for potential violations
        logger.info("Checking for transactions that would violate new constraint...")
        cursor.execute("""
            SELECT user_id, account_id, date, amount, description_raw, balance, COUNT(*) as cnt
            FROM transactions
            WHERE balance IS NOT NULL
            GROUP BY user_id, account_id, date, amount, description_raw, balance
            HAVING cnt > 1
            LIMIT 10
        """)
        violations = cursor.fetchall()
        
        if violations:
            logger.warning(f"⚠️  Found {len(violations)} groups that would still violate new constraint")
            logger.warning("These are true duplicates with same balance - they will remain duplicates")
        else:
            logger.info("✅ No violations found with new constraint")
        
        # Step 3: Create new unique index with balance
        logger.info("Creating new unique index with balance...")
        try:
            cursor.execute("""
                CREATE UNIQUE INDEX idx_transaction_unique 
                ON transactions(user_id, account_id, date, amount, description_raw, balance)
            """)
            conn.commit()
            logger.info("✅ New unique index created successfully!")
            logger.info("   Now allows same transaction with different balances (different times)")
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Error creating new index: {e}")
            raise
        
        # Step 4: Verify
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
        print("   Unique constraint now includes balance field")
        print("   Transactions with same date/amount/description but different balances are allowed")
        sys.exit(0)
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)

