"""
Migration: Add Unique Constraint to Transactions Table

Prevents exact duplicate transactions from being inserted.

Composite unique constraint on:
- user_id
- account_id  
- date
- amount
- description_raw

This ensures the same transaction (same user, account, date, amount, description)
cannot be inserted twice.

Run with: python migrations/add_transaction_unique_constraint.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def cleanup_duplicates():
    """Remove duplicate transactions before adding unique constraint"""
    print("🔍 Scanning for duplicate transactions...")
    
    engine = create_engine(Config.DATABASE_URL)
    
    with engine.connect() as conn:
        # Find duplicates
        result = conn.execute(text("""
            SELECT user_id, account_id, date, amount, description_raw, COUNT(*) as cnt
            FROM transactions
            GROUP BY user_id, account_id, date, amount, description_raw
            HAVING COUNT(*) > 1
        """))
        
        duplicates = result.fetchall()
        
        if not duplicates:
            print("✅ No duplicates found!")
            return 0
        
        print(f"⚠️  Found {len(duplicates)} groups of duplicate transactions")
        
        total_duplicates = 0
        for row in duplicates:
            user_id, account_id, date, amount, desc = row[:5]
            count = row[5]
            duplicates_to_remove = count - 1
            total_duplicates += duplicates_to_remove
            
            print(f"  • {user_id[:8]}... | {date} | ₹{amount} | {desc[:40]}... → {count} duplicates")
        
        # Delete duplicates (keep oldest one based on created_at)
        print("\n🗑️  Removing duplicates (keeping oldest transaction)...")
        
        result = conn.execute(text("""
            DELETE FROM transactions
            WHERE ROWID NOT IN (
                SELECT MIN(ROWID)
                FROM transactions
                GROUP BY user_id, account_id, date, amount, description_raw
            )
        """))
        
        conn.commit()
        deleted = result.rowcount
        print(f"✅ Removed {deleted} duplicate transactions")
        
        return deleted


def run_migration():
    """Add unique constraint to transactions table"""
    print("🔄 Running migration: Add Transaction Unique Constraint")
    
    # Step 1: Clean up existing duplicates
    duplicates_removed = cleanup_duplicates()
    
    if duplicates_removed > 0:
        print(f"\n✅ Database cleaned up: {duplicates_removed} duplicates removed")
    
    # Create engine
    engine = create_engine(Config.DATABASE_URL)
    
    with engine.connect() as conn:
        # Check if constraint already exists
        result = conn.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name='idx_transaction_unique'
        """))
        
        if result.fetchone():
            print("⚠️  Unique constraint already exists. Skipping...")
            return
        
        # Create unique constraint
        print("\n📋 Creating unique constraint on transactions table...")
        print("   Columns: user_id, account_id, date, amount, description_raw")
        
        try:
            conn.execute(text("""
                CREATE UNIQUE INDEX idx_transaction_unique 
                ON transactions(user_id, account_id, date, amount, description_raw)
            """))
            conn.commit()
            
            print("✅ Unique constraint created successfully!")
            print("\nEffect:")
            print("  • Exact duplicate transactions will be rejected")
            print("  • Same user + account + date + amount + description = duplicate")
            print("  • Database will enforce this constraint automatically")
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Error creating unique constraint: {e}")
            raise


def rollback_migration():
    """Remove unique constraint (if needed for debugging)"""
    print("🔄 Rolling back: Remove Transaction Unique Constraint")
    
    engine = create_engine(Config.DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            conn.execute(text("DROP INDEX IF EXISTS idx_transaction_unique"))
            conn.commit()
            print("✅ Unique constraint removed successfully!")
        except Exception as e:
            conn.rollback()
            print(f"❌ Error removing unique constraint: {e}")
            raise


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_migration()
    else:
        run_migration()
