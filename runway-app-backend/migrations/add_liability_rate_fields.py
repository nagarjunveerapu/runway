"""
Migration: Add rate and lifecycle fields to Liability

Fields added:
- rate_type (fixed|floating)
- rate_reset_frequency_months (int)
- processing_fee (float)
- prepayment_penalty_pct (float)
- last_rate_reset_date (datetime)
- moratorium_months (int)
- status (active|closed)
- closure_date (datetime)
- closure_reason (str)

Date: 2025-10-30
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from storage.database import DatabaseManager


def migrate():
    """Add new liability columns for rate handling and lifecycle."""

    db = DatabaseManager()
    connection = db.engine.raw_connection()
    cursor = connection.cursor()

    try:
        # SQLite: ADD COLUMN is supported; columns default to NULL when not specified
        statements = [
            ("rate_type", "ALTER TABLE liabilities ADD COLUMN rate_type VARCHAR(20)"),
            ("rate_reset_frequency_months", "ALTER TABLE liabilities ADD COLUMN rate_reset_frequency_months INTEGER"),
            ("processing_fee", "ALTER TABLE liabilities ADD COLUMN processing_fee FLOAT"),
            ("prepayment_penalty_pct", "ALTER TABLE liabilities ADD COLUMN prepayment_penalty_pct FLOAT"),
            ("last_rate_reset_date", "ALTER TABLE liabilities ADD COLUMN last_rate_reset_date DATETIME"),
            ("moratorium_months", "ALTER TABLE liabilities ADD COLUMN moratorium_months INTEGER"),
            ("status", "ALTER TABLE liabilities ADD COLUMN status VARCHAR(20) DEFAULT 'active'"),
            ("closure_date", "ALTER TABLE liabilities ADD COLUMN closure_date DATETIME"),
            ("closure_reason", "ALTER TABLE liabilities ADD COLUMN closure_reason VARCHAR(255)"),
        ]

        for name, sql in statements:
            print(f"🔄 Adding column {name} to liabilities...")
            try:
                cursor.execute(sql)
                print(f"✅ {name} added")
            except Exception as e:
                # If the column already exists, continue (idempotent when re-run)
                print(f"ℹ️  Skipping {name}: {e}")

        connection.commit()
        print("\n✅ Migration completed successfully!")

    except Exception as e:
        connection.rollback()
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cursor.close()
        connection.close()

    return True


def rollback():
    """Rollback note for SQLite (DROP COLUMN not supported)."""
    print("⚠️  SQLite doesn't support DROP COLUMN; restore from backup if needed.")


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'rollback':
        rollback()
    else:
        migrate()


