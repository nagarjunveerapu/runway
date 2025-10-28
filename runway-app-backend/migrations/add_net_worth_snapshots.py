"""
Database Migration: Add Net Worth Snapshots Table

Run this script to add the net_worth_snapshots table to your database.

Usage:
    python migrations/add_net_worth_snapshots.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.database import DatabaseManager
from storage.models import Base, NetWorthSnapshot
from config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Create net_worth_snapshots table"""
    try:
        logger.info("Starting migration: Add net_worth_snapshots table")
        logger.info(f"Database URL: {Config.get_database_url(mask_password=True)}")

        # Initialize database
        db = DatabaseManager(Config.DATABASE_URL)
        engine = db.engine

        # Create only the NetWorthSnapshot table
        logger.info("Creating net_worth_snapshots table...")
        NetWorthSnapshot.__table__.create(engine, checkfirst=True)

        logger.info("✅ Migration completed successfully!")
        logger.info("Table 'net_worth_snapshots' has been created.")

    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        raise


if __name__ == "__main__":
    run_migration()
