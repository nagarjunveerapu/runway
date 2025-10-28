"""
Migration: Add original_tenure_months and end_date to Liability model

This migration adds fields to track the original loan terms:
- original_tenure_months: Total original loan tenure
- end_date: Expected loan end date

Date: 2024-10-27
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from storage.database import DatabaseManager
from datetime import datetime
from dateutil.relativedelta import relativedelta


def migrate():
    """Add original_tenure_months and end_date columns to liabilities table"""

    db = DatabaseManager()
    connection = db.engine.raw_connection()
    cursor = connection.cursor()

    try:
        print("🔄 Adding original_tenure_months column to liabilities...")
        cursor.execute("""
            ALTER TABLE liabilities
            ADD COLUMN original_tenure_months INTEGER
        """)
        print("✅ original_tenure_months column added")

        print("🔄 Adding end_date column to liabilities...")
        cursor.execute("""
            ALTER TABLE liabilities
            ADD COLUMN end_date DATETIME
        """)
        print("✅ end_date column added")

        # Migrate existing data: set original_tenure = remaining_tenure (best guess)
        print("🔄 Migrating existing liability data...")
        cursor.execute("""
            UPDATE liabilities
            SET original_tenure_months = remaining_tenure_months
            WHERE original_tenure_months IS NULL AND remaining_tenure_months IS NOT NULL
        """)

        # Calculate end_date for existing loans
        cursor.execute("""
            SELECT liability_id, start_date, original_tenure_months
            FROM liabilities
            WHERE start_date IS NOT NULL AND original_tenure_months IS NOT NULL
        """)

        rows = cursor.fetchall()
        for row in rows:
            liability_id, start_date_str, tenure = row
            if start_date_str and tenure:
                # Parse start date
                if ' ' in start_date_str:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d %H:%M:%S')
                else:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')

                # Calculate end date
                end_date = start_date + relativedelta(months=tenure)
                end_date_str = end_date.strftime('%Y-%m-%d %H:%M:%S')

                cursor.execute("""
                    UPDATE liabilities
                    SET end_date = ?
                    WHERE liability_id = ?
                """, (end_date_str, liability_id))

        connection.commit()
        print(f"✅ Migrated {len(rows)} existing liabilities")
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
    """Remove original_tenure_months and end_date columns"""

    db = DatabaseManager()
    connection = db.engine.raw_connection()
    cursor = connection.cursor()

    try:
        print("🔄 Rolling back migration...")

        # SQLite doesn't support DROP COLUMN directly, need to recreate table
        # For now, just notify
        print("⚠️  SQLite doesn't support DROP COLUMN.")
        print("   To rollback, you'll need to recreate the table or restore from backup.")

    finally:
        cursor.close()
        connection.close()


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'rollback':
        rollback()
    else:
        migrate()
