"""
Personal Finance CLI

Main command-line interface for the personal finance application.
"""

import click
import logging
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from schema import CanonicalTransaction
from ingestion import PDFParser, CSVParser, Normalizer
from mapping import MerchantMapper
from ml import MLCategorizer
from storage import DatabaseManager
from deduplication import DeduplicationDetector
from logging_config import setup_logging, get_logger

# Setup logging
setup_logging(log_level=Config.LOG_LEVEL)
logger = get_logger(__name__)


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """
    Personal Finance App - Transaction Management System

    Process bank statements, categorize transactions, and analyze spending.
    """
    # Validate configuration on startup
    try:
        Config.validate()
    except ValueError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--source', type=click.Choice(['pdf', 'csv'], case_sensitive=False),
              help='File type (auto-detected if not specified)')
@click.option('--bank', help='Bank name (e.g., "HDFC Bank")')
@click.option('--account-id', help='Account ID for this statement')
@click.option('--skip-dedup', is_flag=True, help='Skip deduplication')
@click.option('--skip-ml', is_flag=True, help='Skip ML categorization')
def ingest(file_path, source, bank, account_id, skip_dedup, skip_ml):
    """
    Ingest bank statement (PDF or CSV)

    Example:
        finance ingest statements/hdfc_oct_2024.pdf --bank="HDFC Bank"
        finance ingest statements/icici_export.csv --account-id="ACC123"
    """
    click.echo(f"Ingesting: {file_path}")

    try:
        # Auto-detect file type
        if not source:
            ext = Path(file_path).suffix.lower()
            if ext == '.pdf':
                source = 'pdf'
            elif ext == '.csv':
                source = 'csv'
            else:
                click.echo(f"Error: Unknown file type: {ext}", err=True)
                return

        # Parse file
        click.echo(f"Parsing {source.upper()} file...")

        if source == 'pdf':
            parser = PDFParser(bank_name=bank)
            raw_txns = parser.parse(file_path)
            click.echo(f"  Strategy used: {parser.success_strategy}")
        else:  # CSV
            parser = CSVParser(bank_name=bank)
            raw_txns = parser.parse(file_path)

        click.echo(f"  Extracted {len(raw_txns)} transactions")

        # Normalize to canonical schema
        click.echo("Normalizing transactions...")
        normalizer = Normalizer(source=source, bank_name=bank)
        canonical_txns = normalizer.normalize(raw_txns)
        click.echo(f"  Normalized {len(canonical_txns)} transactions")

        # Map merchants
        click.echo("Mapping merchants...")
        mapper = MerchantMapper()
        for txn in canonical_txns:
            if txn.merchant_raw:
                canonical, category_suggested, confidence = mapper.map_merchant(txn.merchant_raw)
                txn.merchant_canonical = canonical
                if not txn.category or txn.category == 'Unknown':
                    txn.category = category_suggested or 'Unknown'

        # ML categorization
        if not skip_ml:
            click.echo("Categorizing transactions with ML...")
            categorizer = MLCategorizer()
            if categorizer.load_model():
                for txn in canonical_txns:
                    if txn.category == 'Unknown':
                        category, confidence = categorizer.predict(txn.to_dict())
                        txn.category = category
                        txn.confidence = confidence
                click.echo(f"  Categorized transactions")
            else:
                click.echo("  Warning: ML model not trained, skipping categorization")

        # Deduplication
        if not skip_dedup:
            click.echo("Detecting duplicates...")
            detector = DeduplicationDetector(
                time_window_days=Config.DEDUP_TIME_WINDOW_DAYS,
                fuzzy_threshold=Config.DEDUP_FUZZY_THRESHOLD,
                merge_duplicates=Config.DEDUP_MERGE_DUPLICATES
            )
            txn_dicts = [txn.to_dict() for txn in canonical_txns]
            deduplicated = detector.detect_duplicates(txn_dicts)
            canonical_txns = [CanonicalTransaction.from_dict(d) for d in deduplicated]

            stats = detector.get_duplicate_stats(deduplicated)
            click.echo(f"  Duplicates removed: {stats['merged_count']}")

        # Set account_id if provided
        if account_id:
            for txn in canonical_txns:
                txn.account_id = account_id

        # Save to database
        click.echo("Saving to database...")
        db = DatabaseManager(database_url=Config.DATABASE_URL)
        inserted = db.insert_transactions_batch(canonical_txns)
        click.echo(f"  Inserted {inserted} transactions")

        click.echo(f"\n✅ Successfully ingested {inserted} transactions")

    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        click.echo(f"\n❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--start-date', help='Start date (YYYY-MM-DD)')
@click.option('--end-date', help='End date (YYYY-MM-DD)')
@click.option('--category', help='Filter by category')
@click.option('--limit', type=int, default=20, help='Number of results')
@click.option('--format', type=click.Choice(['table', 'json'], case_sensitive=False),
              default='table', help='Output format')
def list(start_date, end_date, category, limit, format):
    """
    List transactions

    Example:
        finance list --start-date=2024-10-01 --end-date=2024-10-31
        finance list --category="Food & Dining" --limit=10
    """
    try:
        db = DatabaseManager(database_url=Config.DATABASE_URL)

        transactions = db.get_transactions(
            start_date=start_date,
            end_date=end_date,
            category=category,
            limit=limit
        )

        if not transactions:
            click.echo("No transactions found")
            return

        if format == 'json':
            # JSON output
            txns_dict = [txn.to_dict() for txn in transactions]
            click.echo(json.dumps(txns_dict, indent=2, default=str))
        else:
            # Table output
            click.echo(f"\nFound {len(transactions)} transactions:\n")
            click.echo(f"{'Date':<12} {'Amount':>10} {'Type':<7} {'Merchant':<25} {'Category':<20}")
            click.echo("-" * 80)

            for txn in transactions:
                amount_str = f"₹{txn.amount:,.2f}"
                click.echo(
                    f"{txn.date:<12} "
                    f"{amount_str:>10} "
                    f"{txn.type:<7} "
                    f"{(txn.merchant_canonical or txn.description_raw or '')[:25]:<25} "
                    f"{txn.category or 'Unknown':<20}"
                )

    except Exception as e:
        logger.error(f"List failed: {e}", exc_info=True)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--start-date', help='Start date (YYYY-MM-DD)')
@click.option('--end-date', help='End-date (YYYY-MM-DD)')
def summary(start_date, end_date):
    """
    Show transaction summary and statistics

    Example:
        finance summary
        finance summary --start-date=2024-10-01 --end-date=2024-10-31
    """
    try:
        db = DatabaseManager(database_url=Config.DATABASE_URL)

        # Get all transactions for stats
        transactions = db.get_transactions(start_date=start_date, end_date=end_date)

        if not transactions:
            click.echo("No transactions found")
            return

        # Get summary stats
        stats = db.get_summary_stats()

        click.echo("\n" + "=" * 60)
        click.echo("TRANSACTION SUMMARY")
        click.echo("=" * 60)

        if stats.get('date_range'):
            click.echo(f"\nPeriod: {stats['date_range']['start']} to {stats['date_range']['end']}")

        click.echo(f"\nTotal Transactions: {stats['total_transactions']}")
        click.echo(f"Total Credit:       ₹{stats['total_credit']:,.2f}")
        click.echo(f"Total Debit:        ₹{stats['total_debit']:,.2f}")
        click.echo(f"Net:                ₹{stats['net']:,.2f}")

        # Category breakdown
        if stats.get('category_breakdown'):
            click.echo("\n" + "-" * 60)
            click.echo("CATEGORY BREAKDOWN")
            click.echo("-" * 60)
            click.echo(f"{'Category':<30} {'Count':>10} {'Total':>15}")
            click.echo("-" * 60)

            # Sort by total amount
            sorted_categories = sorted(
                stats['category_breakdown'].items(),
                key=lambda x: x[1]['total'],
                reverse=True
            )

            for category, data in sorted_categories:
                click.echo(
                    f"{category:<30} "
                    f"{data['count']:>10} "
                    f"₹{data['total']:>14,.2f}"
                )

        click.echo("\n" + "=" * 60 + "\n")

    except Exception as e:
        logger.error(f"Summary failed: {e}", exc_info=True)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('training_data_file', type=click.Path(exists=True))
@click.option('--test-size', type=float, default=0.2, help='Test set fraction')
@click.option('--cv', is_flag=True, help='Use cross-validation')
def train(training_data_file, test_size, cv):
    """
    Train ML categorizer

    Training data should be JSONL file with labeled transactions.

    Example:
        finance train ml/training_data/labeled_transactions.jsonl --cv
    """
    click.echo(f"Training ML model from: {training_data_file}")

    try:
        # Load training data
        training_data = []
        with open(training_data_file, 'r') as f:
            for line in f:
                if line.strip():
                    training_data.append(json.loads(line))

        click.echo(f"Loaded {len(training_data)} labeled transactions")

        # Train categorizer
        categorizer = MLCategorizer()
        metrics = categorizer.train(
            training_data,
            test_size=test_size,
            use_cross_validation=cv
        )

        click.echo(f"\n✅ Training complete!")
        click.echo(f"  Accuracy: {metrics['accuracy']:.3f}")

        if metrics.get('mean_cv_score'):
            click.echo(f"  Cross-validation: {metrics['mean_cv_score']:.3f}")

        click.echo(f"  Categories: {len(metrics['categories'])}")
        click.echo(f"  Training samples: {metrics['training_samples']}")

    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        click.echo(f"\n❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def config_info():
    """Show current configuration"""
    click.echo("\n" + "=" * 60)
    click.echo("CONFIGURATION")
    click.echo("=" * 60)

    Config.print_config()


@cli.command()
@click.confirmation_option(prompt='Are you sure you want to initialize the database? This will create all tables.')
def init_db():
    """Initialize database (create tables)"""
    try:
        db = DatabaseManager(database_url=Config.DATABASE_URL)
        click.echo("✅ Database initialized successfully")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
