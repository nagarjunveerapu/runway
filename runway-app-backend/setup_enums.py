#!/usr/bin/env python3
"""
Setup ENUM types in PostgreSQL database for transactions table.

This script:
1. Creates ENUM types
2. Standardizes existing data
3. Alters columns to use ENUM types
"""

import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_enums():
    """Create ENUM types and update columns"""
    
    db_url = Config.DATABASE_URL
    
    # Only run for PostgreSQL
    if not db_url.startswith('postgresql'):
        logger.info("This script is for PostgreSQL only. Skipping...")
        return
    
    logger.info("Setting up ENUM types for transactions table...")
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        try:
            # Start transaction
            trans = conn.begin()
            
            logger.info("1. Creating ENUM types...")
            
            # Create transaction_type ENUM
            conn.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE transaction_type AS ENUM ('debit', 'credit');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            
            # Create transaction_source ENUM
            conn.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE transaction_source AS ENUM (
                        'manual', 'pdf', 'csv', 'excel', 'aa', 'api'
                    );
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            
            # Create recurring_type ENUM
            conn.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE recurring_type AS ENUM ('salary', 'emi', 'investment', 'expense');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            
            # Create transaction_category ENUM
            conn.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE transaction_category AS ENUM (
                        'Food & Dining',
                        'Groceries',
                        'Shopping',
                        'Transport',
                        'Entertainment',
                        'Bills & Utilities',
                        'Healthcare',
                        'Education',
                        'Travel',
                        'Investment',
                        'Transfer',
                        'Salary',
                        'Refund',
                        'Other',
                        'Unknown'
                    );
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            
            logger.info("2. Standardizing source values...")
            
            # Standardize source values
            conn.execute(text("""
                UPDATE transactions 
                SET source = CASE
                    WHEN source IN ('pdf_upload', 'PDF', 'pdf') THEN 'pdf'
                    WHEN source IN ('csv_upload', 'CSV', 'csv') THEN 'csv'
                    WHEN source IN ('excel', 'EXCEL') THEN 'excel'
                    WHEN source = 'api' THEN 'api'
                    WHEN source = 'aa' THEN 'aa'
                    WHEN source = 'manual' THEN 'manual'
                    WHEN source IS NULL THEN 'manual'
                    ELSE 'manual'  -- Default for unknown values
                END
                WHERE source IS NOT NULL;
            """))
            
            logger.info("3. Altering columns to use ENUM types...")
            
            # Alter type column
            conn.execute(text("""
                DO $$ 
                BEGIN
                    -- Add new column with ENUM type
                    ALTER TABLE transactions 
                    ADD COLUMN IF NOT EXISTS type_new transaction_type;
                    
                    -- Copy and convert data
                    UPDATE transactions 
                    SET type_new = CASE 
                        WHEN type = 'debit' THEN 'debit'::transaction_type
                        WHEN type = 'credit' THEN 'credit'::transaction_type
                        ELSE 'debit'::transaction_type
                    END;
                    
                    -- Drop old column and rename
                    ALTER TABLE transactions DROP COLUMN IF EXISTS type;
                    ALTER TABLE transactions RENAME COLUMN type_new TO type;
                    ALTER TABLE transactions ALTER COLUMN type SET NOT NULL;
                EXCEPTION
                    WHEN OTHERS THEN
                        RAISE NOTICE 'Error altering type column: %', SQLERRM;
                END $$;
            """))
            
            # Alter source column
            conn.execute(text("""
                DO $$ 
                BEGIN
                    -- Add new column with ENUM type
                    ALTER TABLE transactions 
                    ADD COLUMN IF NOT EXISTS source_new transaction_source;
                    
                    -- Copy and convert data
                    UPDATE transactions 
                    SET source_new = source::transaction_source;
                    
                    -- Drop old column and rename
                    ALTER TABLE transactions DROP COLUMN IF EXISTS source;
                    ALTER TABLE transactions RENAME COLUMN source_new TO source;
                EXCEPTION
                    WHEN OTHERS THEN
                        RAISE NOTICE 'Error altering source column: %', SQLERRM;
                END $$;
            """))
            
            # Alter recurring_type column
            conn.execute(text("""
                DO $$ 
                BEGIN
                    -- Add new column with ENUM type
                    ALTER TABLE transactions 
                    ADD COLUMN IF NOT EXISTS recurring_type_new recurring_type;
                    
                    -- Copy and convert data (only non-null values)
                    UPDATE transactions 
                    SET recurring_type_new = recurring_type::recurring_type
                    WHERE recurring_type IS NOT NULL;
                    
                    -- Drop old column and rename
                    ALTER TABLE transactions DROP COLUMN IF EXISTS recurring_type;
                    ALTER TABLE transactions RENAME COLUMN recurring_type_new TO recurring_type;
                EXCEPTION
                    WHEN OTHERS THEN
                        RAISE NOTICE 'Error altering recurring_type column: %', SQLERRM;
                END $$;
            """))
            
            # Alter category column
            conn.execute(text("""
                DO $$ 
                BEGIN
                    -- Add new column with ENUM type
                    ALTER TABLE transactions 
                    ADD COLUMN IF NOT EXISTS category_new transaction_category;
                    
                    -- Copy and convert data, default to 'Unknown' if not in enum
                    UPDATE transactions 
                    SET category_new = CASE
                        WHEN category IN (
                            'Food & Dining', 'Groceries', 'Shopping', 'Transport',
                            'Entertainment', 'Bills & Utilities', 'Healthcare',
                            'Education', 'Travel', 'Investment', 'Transfer',
                            'Salary', 'Refund', 'Other', 'Unknown'
                        ) THEN category::transaction_category
                        ELSE 'Unknown'::transaction_category
                    END
                    WHERE category IS NOT NULL;
                    
                    -- Set default for NULL values
                    UPDATE transactions 
                    SET category_new = 'Unknown'::transaction_category
                    WHERE category IS NULL;
                    
                    -- Drop old column and rename
                    ALTER TABLE transactions DROP COLUMN IF EXISTS category;
                    ALTER TABLE transactions RENAME COLUMN category_new TO category;
                    ALTER TABLE transactions ALTER COLUMN category SET DEFAULT 'Unknown'::transaction_category;
                EXCEPTION
                    WHEN OTHERS THEN
                        RAISE NOTICE 'Error altering category column: %', SQLERRM;
                END $$;
            """))
            
            # Commit transaction
            trans.commit()
            
            logger.info("✅ ENUM types setup completed successfully!")
            
        except Exception as e:
            trans.rollback()
            logger.error(f"❌ Error setting up ENUMs: {e}")
            raise


if __name__ == "__main__":
    try:
        setup_enums()
    except Exception as e:
        logger.error(f"Failed: {e}")
        sys.exit(1)

