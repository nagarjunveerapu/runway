#!/usr/bin/env python3
"""
Migration: Make user_id NOT NULL in transactions table

This migration:
1. Deletes any transactions with NULL user_id (orphaned data)
2. Adds NOT NULL constraint to user_id column
3. Verifies the constraint is applied

Usage: python3 migrate_database.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.database import DatabaseManager
from storage.models import Transaction
from config import Config
import sqlite3

def migrate_user_id_not_null():
    """Make user_id NOT NULL in transactions table"""
    
    print("=" * 80)
    print("MIGRATION: Make user_id NOT NULL")
    print("=" * 80)
    
    # Get database path
    db_path = Config.DATABASE_URL.replace('sqlite:///', '')
    
    # Connect to SQLite database directly
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Step 1: Check for existing NULL values
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE user_id IS NULL")
    null_count = cursor.fetchone()[0]
    
    if null_count > 0:
        print(f"\n⚠️  Found {null_count} transactions with NULL user_id")
        print("   Deleting orphaned transactions...")
        
        cursor.execute("DELETE FROM transactions WHERE user_id IS NULL")
        deleted = cursor.rowcount
        conn.commit()
        
        print(f"   ✅ Deleted {deleted} orphaned transactions")
    else:
        print("\n✅ No transactions with NULL user_id found")
    
    # Step 2: Check current schema
    cursor.execute("PRAGMA table_info(transactions)")
    columns = cursor.fetchall()
    
    user_id_column = None
    for col in columns:
        if col[1] == 'user_id':
            user_id_column = col
            break
    
    if user_id_column:
        print(f"\nCurrent user_id column info: {user_id_column}")
        not_null = bool(user_id_column[3])  # Column 3 is "notnull" flag
        
        if not_null:
            print("✅ user_id already has NOT NULL constraint")
            conn.close()
            return
    
    # Step 3: Add NOT NULL constraint
    print("\nAdding NOT NULL constraint to user_id...")
    
    # Note: SQLite doesn't support ALTER TABLE MODIFY COLUMN
    # We need to recreate the table with the constraint
    print("   Creating new table with NOT NULL constraint...")
    
    # Drop any leftover table from previous attempts
    try:
        cursor.execute("DROP TABLE IF EXISTS transactions_new")
    except:
        pass
    
    # Get all data
    cursor.execute("SELECT * FROM transactions")
    all_rows = cursor.fetchall()
    cursor.execute("PRAGMA table_info(transactions)")
    all_columns = cursor.fetchall()
    
    # Create new table with NOT NULL constraint
    conn.execute("""
        CREATE TABLE transactions_new (
            transaction_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(user_id),
            account_id TEXT REFERENCES accounts(account_id),
            merchant_id TEXT REFERENCES merchants(merchant_id),
            date TEXT NOT NULL,
            timestamp TEXT,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            description_raw TEXT,
            clean_description TEXT,
            merchant_raw TEXT,
            merchant_canonical TEXT,
            category TEXT,
            labels TEXT,
            confidence REAL,
            balance REAL,
            currency TEXT,
            original_amount REAL,
            original_currency TEXT,
            duplicate_of TEXT,
            duplicate_count INTEGER,
            is_duplicate INTEGER,
            source TEXT,
            bank_name TEXT,
            statement_period TEXT,
            ingestion_timestamp TEXT,
            extra_metadata TEXT,
            linked_asset_id TEXT,
            liquidation_event_id TEXT,
            month TEXT,
            is_recurring INTEGER,
            recurring_type TEXT,
            recurring_group_id TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    
    # Copy data from old table
    if all_rows:
        print(f"   Copying {len(all_rows)} transactions...")
        
        # Use SELECT * FROM to copy all data directly
        cursor.execute("INSERT INTO transactions_new SELECT * FROM transactions")
        rows_copied = cursor.rowcount
        print(f"   ✅ Copied {rows_copied} transactions")
    
    # Replace old table with new one
    print("   Replacing old table...")
    conn.execute("DROP TABLE transactions")
    conn.execute("ALTER TABLE transactions_new RENAME TO transactions")
    
    # Recreate indexes
    print("   Recreating indexes...")
    conn.execute("CREATE INDEX idx_user_id ON transactions(user_id)")
    conn.execute("CREATE INDEX idx_user_date ON transactions(user_id, date)")
    conn.execute("CREATE INDEX idx_date_category ON transactions(date, category)")
    conn.execute("CREATE INDEX idx_merchant_date ON transactions(merchant_canonical, date)")
    conn.execute("CREATE INDEX idx_user_month ON transactions(user_id, month)")
    conn.execute("CREATE INDEX idx_duplicate_of ON transactions(duplicate_of)")
    conn.execute("CREATE INDEX idx_is_recurring ON transactions(is_recurring)")
    conn.execute("CREATE INDEX idx_recurring_group_id ON transactions(recurring_group_id)")
    conn.execute("CREATE INDEX idx_date ON transactions(date)")
    conn.execute("CREATE INDEX idx_category ON transactions(category)")
    conn.execute("CREATE INDEX idx_user_category ON transactions(user_id, category)")
    conn.execute("CREATE INDEX idx_linked_asset_id ON transactions(linked_asset_id)")
    conn.execute("CREATE INDEX idx_liquidation_event_id ON transactions(liquidation_event_id)")
    
    conn.commit()
    
    print("✅ Migration completed successfully")
    
    # Verify
    cursor.execute("PRAGMA table_info(transactions)")
    columns = cursor.fetchall()
    
    for col in columns:
        if col[1] == 'user_id':
            not_null = bool(col[3])
            if not_null:
                print(f"\n✅ VERIFIED: user_id has NOT NULL constraint")
            else:
                print(f"\n❌ ERROR: user_id still allows NULL values")
    
    # Check data integrity
    cursor.execute("SELECT COUNT(*) FROM transactions")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE user_id IS NULL")
    null_count = cursor.fetchone()[0]
    
    print(f"\n📊 Final Statistics:")
    print(f"   Total transactions: {total}")
    print(f"   Transactions with NULL user_id: {null_count}")
    
    if null_count == 0:
        print("   ✅ Data integrity verified")
    else:
        print(f"   ⚠️  Warning: {null_count} transactions still have NULL user_id")
    
    conn.close()
    print("\n" + "=" * 80)


if __name__ == "__main__":
    try:
        migrate_user_id_not_null()
        print("\n🎉 Migration completed successfully!")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

