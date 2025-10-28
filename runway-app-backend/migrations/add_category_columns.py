"""
Migration: Add Category Columns to DetectedEMIPattern

Adds category and subcategory columns to support multi-category recurring payments:
- Loans/EMIs
- Insurance
- Investments (Mutual Funds, SIP)
- Government Schemes (APY, NPS, PPF, etc.)

Run with: python3 migrations/add_category_columns.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from config import Config

def run_migration():
    """Add category and subcategory columns to detected_emi_patterns table"""
    print("🔄 Running migration: Add Category Columns")

    # Create engine
    engine = create_engine(Config.DATABASE_URL)

    with engine.connect() as conn:
        try:
            # Check if columns already exist
            result = conn.execute(text("PRAGMA table_info(detected_emi_patterns)"))
            columns = [row[1] for row in result]

            if 'category' in columns and 'subcategory' in columns:
                print("✅ Columns already exist, skipping migration")
                return

            # Add category column
            if 'category' not in columns:
                print("📋 Adding 'category' column to detected_emi_patterns")
                conn.execute(text("""
                    ALTER TABLE detected_emi_patterns
                    ADD COLUMN category VARCHAR(50)
                """))
                conn.commit()
                print("  ✓ Added 'category' column")

            # Add subcategory column
            if 'subcategory' not in columns:
                print("📋 Adding 'subcategory' column to detected_emi_patterns")
                conn.execute(text("""
                    ALTER TABLE detected_emi_patterns
                    ADD COLUMN subcategory VARCHAR(100)
                """))
                conn.commit()
                print("  ✓ Added 'subcategory' column")

            # Create index on category
            print("📋 Creating index on category column")
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_emi_category
                    ON detected_emi_patterns(category)
                """))
                conn.commit()
                print("  ✓ Created index on category")
            except Exception as e:
                print(f"  ⚠️  Index may already exist: {e}")

            print("\n✅ Migration completed successfully!")
            print("\nNew columns:")
            print("  • category - Categorizes payment (Loan, Insurance, Investment, Government Scheme)")
            print("  • subcategory - More specific type (Home Loan, Life Insurance, Mutual Fund SIP, etc.)")

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            conn.rollback()
            raise

if __name__ == "__main__":
    run_migration()
