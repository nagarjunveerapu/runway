"""
Migration: Add Salary Sweep Configuration Tables

Creates tables for:
- salary_sweep_configs: Store user's confirmed salary and configuration
- detected_emi_patterns: Store detected EMI patterns with user confirmations and model suggestions

Run with: python migrations/add_salary_sweep_tables.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from storage.models import Base, SalarySweepConfig, DetectedEMIPattern
from config import Config

def run_migration():
    """Create salary sweep tables"""
    print("🔄 Running migration: Add Salary Sweep Tables")

    # Create engine
    engine = create_engine(Config.DATABASE_URL)

    # Create only the new tables (won't affect existing tables)
    print("📋 Creating tables:")
    print("  - salary_sweep_configs")
    print("  - detected_emi_patterns")

    # Create the tables
    SalarySweepConfig.__table__.create(engine, checkfirst=True)
    DetectedEMIPattern.__table__.create(engine, checkfirst=True)

    print("✅ Migration completed successfully!")
    print("\nNew tables:")
    print("  • salary_sweep_configs - Stores user's salary sweep configuration")
    print("  • detected_emi_patterns - Stores detected EMI patterns with confirmations")

if __name__ == "__main__":
    run_migration()
