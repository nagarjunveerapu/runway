"""Main orchestrator for the pipeline.

The dashboard automatically launches in your browser after processing!

Usage:
    python3 main.py                          # Process default file & launch dashboard
    python3 main.py file1.csv file2.txt      # Process specific files & launch dashboard
    python3 main.py --no-dashboard           # Process without launching dashboard
    python3 main.py --dashboard-only         # Just launch dashboard (skip processing)
    python3 main.py --all                    # Process all .txt and .csv files in data/
    python3 main.py --csv-only               # Process only CSV files
    ./run.sh                                 # Process default file & launch dashboard
"""
from pathlib import Path
import logging
import pandas as pd
import argparse
import sys
import subprocess
import time
import shutil
from typing import List

from src import parser, cleaner, merchant_normalizer, classifier, summary as summary_mod, csv_parser

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


DATA_DIR = Path('data')
DEFAULT_FILE = DATA_DIR / 'Transactions.csv'  # Default input file
OUT_DIR = DATA_DIR / 'cleaned'
SUMMARY_DIR = Path('reports')


def cleanup_previous_outputs():
    """Clean up previous output directories to ensure fresh processing."""
    logger.info('Cleaning up previous outputs...')

    # Remove cleaned directory
    if OUT_DIR.exists():
        try:
            shutil.rmtree(OUT_DIR)
            logger.info(f'Removed directory: {OUT_DIR}')
        except Exception as e:
            logger.warning(f'Failed to remove {OUT_DIR}: {e}')

    # Remove reports directory
    if SUMMARY_DIR.exists():
        try:
            shutil.rmtree(SUMMARY_DIR)
            logger.info(f'Removed directory: {SUMMARY_DIR}')
        except Exception as e:
            logger.warning(f'Failed to remove {SUMMARY_DIR}: {e}')


def detect_recurring(transactions: pd.DataFrame, threshold_pct: float = 0.05) -> pd.DataFrame:
    # heuristic: same merchant and similar amounts repeating
    df = transactions.copy()
    df['amount_round'] = df['amount'].round(2)
    # count occurrences by merchant and rounded amount
    grp = df.groupby(['merchant', 'amount_round']).size().reset_index(name='count')
    # merge counts back
    df = df.merge(grp, on=['merchant', 'amount_round'], how='left')
    df['recurring'] = df['count'] >= 2
    df['recurrence_count'] = df['count']
    return df


def process_file(file_path: Path) -> List[dict]:
    """Process a single file and return transactions."""
    logger.info('=' * 80)
    logger.info(f'Processing file: {file_path}')

    file_ext = file_path.suffix.lower()
    txs = []

    try:
        if file_ext == '.csv':
            # Use CSV parser for structured CSV files
            txs = csv_parser.parse_csv_file(str(file_path))
        elif file_ext == '.txt':
            # Use text parser for unstructured text files
            txs = parser.parse_file(str(file_path))
        else:
            logger.warning(f"Unsupported file type: {file_ext}. Skipping {file_path}")
            return []

        if not txs:
            logger.warning(f"No transactions found in {file_path}")
            return []

        logger.info(f'Found {len(txs)} transactions in {file_path.name}')
        return txs

    except Exception as e:
        logger.error(f"Failed to process {file_path}: {e}")
        return []


def enrich_transactions(txs: List[dict]) -> List[dict]:
    """Enrich transactions with merchant normalization, categorization, etc."""
    logger.info(f'Enriching {len(txs)} transactions...')

    # Clean and enrich
    enriched_txs = [cleaner.enrich_transaction(t) for t in txs]

    # Normalize merchants
    norm = merchant_normalizer.MerchantNormalizer()
    for t in enriched_txs:
        m_raw = t.get('merchant_raw') or t.get('remark')
        merchant, score = norm.normalize(m_raw)
        t['merchant'] = merchant
        t['notes'] = (t.get('notes', '') + f"; merchant_score={score}").lstrip('; ')

    # Classify
    for t in enriched_txs:
        t['category'] = classifier.rule_based_category(t.get('remark', ''), t.get('merchant'))
        
        # Post-classification: Group person-to-person transfers to protect PII
        # Check if this looks like a personal transfer
        merchant_raw = t.get('merchant_raw', '')
        remark = t.get('remark', '').lower()
        
        # If merchant normalized to "Other" and has personal name pattern, categorize as Person Transfer
        if t.get('merchant') == 'Other' and merchant_raw and len(merchant_raw.split()) <= 5:
            # Check for personal name indicators
            merchant_upper = merchant_raw.upper()
            has_pvt_ltd = any(word in merchant_upper for word in ['PVT', 'LTD', 'LIMITED', 'CORP', 'CO', 'INC'])
            
            # If it doesn't look like a company and has UPI patterns, it's likely a person
            if not has_pvt_ltd and (any(x in remark for x in ['payment fr', 'payment to', 'upi/', '@ybl', '@paytm', '@axl'])):
                t['category'] = 'Person Transfer'
    
    return enriched_txs


def get_files_to_process(args) -> List[Path]:
    """Determine which files to process based on arguments."""
    files = []

    if args.all:
        # Process all .txt and .csv files in data directory
        logger.info("Processing all transaction files in data directory...")
        files.extend(DATA_DIR.rglob('*.txt'))
        files.extend(DATA_DIR.rglob('*.csv'))
    elif args.csv_only:
        # Process only CSV files
        logger.info("Processing CSV files only...")
        files.extend(DATA_DIR.rglob('*.csv'))
    elif args.files:
        # Process specific files provided as arguments
        for file_arg in args.files:
            file_path = Path(file_arg)
            if not file_path.exists():
                logger.warning(f"File not found: {file_arg}")
                continue
            files.append(file_path)
    else:
        # Default: process the default file (Transactions.csv)
        logger.info("Processing default file...")
        if DEFAULT_FILE.exists():
            files.append(DEFAULT_FILE)
        else:
            logger.warning(f"Default file not found: {DEFAULT_FILE}")

    return files


def run(files_to_process: List[Path] = None):
    """Main processing pipeline."""
    if files_to_process is None:
        files_to_process = [DEFAULT_FILE]

    # Clean up previous outputs for fresh processing
    cleanup_previous_outputs()

    all_transactions = []

    # Process each file
    for file_path in files_to_process:
        txs = process_file(file_path)
        if txs:
            all_transactions.extend(txs)

    if not all_transactions:
        logger.error("No transactions found in any files!")
        return

    logger.info('=' * 80)
    logger.info(f'Total transactions collected: {len(all_transactions)}')

    # Enrich all transactions
    enriched_txs = enrich_transactions(all_transactions)

    # Convert to DataFrame
    df = pd.DataFrame(enriched_txs)

    # Detect recurring transactions
    df = detect_recurring(df)

    # Ensure output directories exist
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

    # Generate output filename with timestamp
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_out = OUT_DIR / f'parsed_transactions_{timestamp}.csv'
    summary_out = SUMMARY_DIR / f'summary_{timestamp}.json'

    # Save CSV
    df.to_csv(csv_out, index=False)
    logger.info(f'Wrote cleaned CSV: {csv_out}')

    # Generate summary
    summary = summary_mod.compute_summary(df.to_dict(orient='records'), str(summary_out))
    logger.info(f'Wrote summary JSON: {summary_out}')

    # Also save a "latest" version for convenience
    latest_csv = OUT_DIR / 'parsed_transactions_latest.csv'
    latest_summary = SUMMARY_DIR / 'summary_latest.json'
    df.to_csv(latest_csv, index=False)
    summary_mod.compute_summary(df.to_dict(orient='records'), str(latest_summary))
    logger.info(f'Wrote latest CSV: {latest_csv}')
    logger.info(f'Wrote latest summary: {latest_summary}')

    logger.info('=' * 80)
    logger.info('Processing complete!')
    logger.info(f'Total files processed: {len(files_to_process)}')
    logger.info(f'Total transactions: {len(df)}')
    logger.info(f'Recurring transactions: {df["recurring"].sum()}')

    return latest_csv


def launch_dashboard(csv_path: Path):
    """Launch the Streamlit dashboard with the processed data."""
    logger.info('=' * 80)
    logger.info('Launching dashboard...')
    logger.info(f'Dashboard will open in your browser shortly.')
    logger.info('Press Ctrl+C to stop the dashboard server.')
    logger.info('=' * 80)

    # Give user a moment to see the message
    time.sleep(1)

    # Launch Streamlit
    try:
        subprocess.run([
            'streamlit', 'run', 'dashboard.py',
            '--', '--csv', str(csv_path)
        ], check=True)
    except KeyboardInterrupt:
        logger.info('\nDashboard stopped by user.')
    except subprocess.CalledProcessError as e:
        logger.error(f'Failed to launch dashboard: {e}')
    except FileNotFoundError:
        logger.error('Streamlit not found. Install it with: pip3 install streamlit')


if __name__ == '__main__':
    parser_cli = argparse.ArgumentParser(
        description='Transaction analysis pipeline - processes bank statements from text or CSV files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 main.py                                    # Process default file & launch dashboard
  python3 main.py data/Transactions.csv              # Process single CSV & launch dashboard
  python3 main.py --no-dashboard                     # Process without launching dashboard
  python3 main.py --dashboard-only                   # Just launch dashboard with latest data
  python3 main.py file1.csv file2.txt file3.csv      # Process multiple files
  python3 main.py --all                              # Process all files in data/
  python3 main.py --csv-only                         # Process only CSV files
        """
    )

    parser_cli.add_argument('files', nargs='*', help='Specific files to process')
    parser_cli.add_argument('--all', action='store_true', help='Process all .txt and .csv files in data directory')
    parser_cli.add_argument('--csv-only', action='store_true', help='Process only CSV files in data directory')
    parser_cli.add_argument('--no-dashboard', action='store_true', help='Skip launching the dashboard after processing')
    parser_cli.add_argument('--dashboard-only', action='store_true', help='Only launch dashboard with latest data (skip processing)')

    args = parser_cli.parse_args()

    # Handle dashboard-only mode
    if args.dashboard_only:
        latest_csv = OUT_DIR / 'parsed_transactions_latest.csv'
        if not latest_csv.exists():
            logger.error(f"No processed data found at {latest_csv}")
            logger.error("Run without --dashboard-only to process files first.")
            sys.exit(1)
        launch_dashboard(latest_csv)
        sys.exit(0)

    # Get files to process
    files = get_files_to_process(args)

    if not files:
        logger.error("No files to process!")
        sys.exit(1)

    logger.info(f"Files to process: {len(files)}")
    for f in files:
        logger.info(f"  - {f}")

    # Run the pipeline
    output_csv = run(files)

    # Launch dashboard unless disabled
    if not args.no_dashboard:
        launch_dashboard(output_csv)
    else:
        logger.info('=' * 80)
        logger.info('Dashboard launch skipped (--no-dashboard flag used)')
        logger.info(f'To view dashboard later, run:')
        logger.info(f'  streamlit run dashboard.py -- --csv {output_csv}')
        logger.info('Or run: python3 main.py --dashboard-only')
