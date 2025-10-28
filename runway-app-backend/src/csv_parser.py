"""Parser for structured CSV bank statement files.

Handles CSV files with columns like Transaction Date, Transaction Remarks,
Withdrawal Amount, Deposit Amount, Balance, etc.
"""
from typing import List, Dict, Any
import pandas as pd
import logging
from pathlib import Path
from .utils import gen_uuid
from . import parser  # Import text parser for channel/merchant extraction

logger = logging.getLogger(__name__)


def detect_csv_format(df: pd.DataFrame) -> str:
    """Detect the format of the CSV file based on column names."""
    columns_lower = [str(col).lower() for col in df.columns]

    # Check for standard bank statement format
    if any('transaction remarks' in col for col in columns_lower):
        return 'bank_statement'
    elif any('description' in col or 'narration' in col for col in columns_lower):
        return 'generic_statement'
    else:
        return 'unknown'


def parse_bank_statement_csv(file_path: str) -> List[Dict[str, Any]]:
    """Parse a bank statement CSV file.

    Expected columns:
    - Transaction Date or Value Date
    - Transaction Remarks
    - Withdrawal Amount (INR) or Debit
    - Deposit Amount (INR) or Credit
    - Balance (INR)
    """
    logger.info(f"Parsing bank statement CSV: {file_path}")

    try:
        # Read CSV, handling BOM and extra commas
        df = pd.read_csv(file_path, encoding='utf-8-sig')

        # Remove completely empty columns
        df = df.dropna(axis=1, how='all')

        # Remove rows where all values are NaN
        df = df.dropna(how='all')

        # Identify key columns (case-insensitive)
        column_mapping = {}
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if 'transaction date' in col_lower:
                column_mapping['transaction_date'] = col
            elif 'value date' in col_lower:
                column_mapping['value_date'] = col
            elif 'transaction remark' in col_lower or 'remark' in col_lower:
                column_mapping['remarks'] = col
            elif 'withdrawal' in col_lower or 'debit' in col_lower:
                column_mapping['withdrawal'] = col
            elif 'deposit' in col_lower or 'credit' in col_lower:
                column_mapping['deposit'] = col
            elif 'balance' in col_lower:
                column_mapping['balance'] = col

        transactions = []

        for idx, row in df.iterrows():
            try:
                # Extract transaction remarks
                remarks = ''
                if 'remarks' in column_mapping:
                    remarks = str(row[column_mapping['remarks']]) if pd.notna(row[column_mapping['remarks']]) else ''

                # Skip if no remarks
                if not remarks or remarks == 'nan':
                    continue

                # Extract amounts
                withdrawal = 0.0
                deposit = 0.0

                if 'withdrawal' in column_mapping:
                    wd_val = row[column_mapping['withdrawal']]
                    if pd.notna(wd_val):
                        withdrawal = float(wd_val)

                if 'deposit' in column_mapping:
                    dep_val = row[column_mapping['deposit']]
                    if pd.notna(dep_val):
                        deposit = float(dep_val)

                # Determine transaction amount (negative for withdrawal, positive for deposit)
                amount = deposit - withdrawal

                # Extract date
                transaction_date = None
                if 'transaction_date' in column_mapping:
                    transaction_date = str(row[column_mapping['transaction_date']]) if pd.notna(row[column_mapping['transaction_date']]) else None
                elif 'value_date' in column_mapping:
                    transaction_date = str(row[column_mapping['value_date']]) if pd.notna(row[column_mapping['value_date']]) else None

                # Extract balance
                balance = None
                if 'balance' in column_mapping:
                    bal_val = row[column_mapping['balance']]
                    if pd.notna(bal_val):
                        balance = float(bal_val)

                # Detect channel and merchant from remarks using text parser logic
                channel = parser.detect_channel(remarks)
                merchant_raw = parser.extract_merchant_raw(remarks)

                # Create transaction dictionary
                tx = {
                    'id': gen_uuid(),
                    'raw_remark': remarks,
                    'remark': remarks,
                    'amount': abs(amount),  # Store absolute amount
                    'transaction_type': 'withdrawal' if withdrawal > 0 else 'deposit',
                    'withdrawal': withdrawal,
                    'deposit': deposit,
                    'balance': balance,
                    'date': transaction_date,
                    'channel': channel,  # Now properly detected
                    'merchant_raw': merchant_raw,  # Now properly extracted
                    'merchant': None,
                    'category': None,
                    'recurring': False,
                    'recurrence_count': 0,
                    'notes': f'Parsed from CSV: {Path(file_path).name}',
                }

                transactions.append(tx)

            except Exception as e:
                logger.warning(f"Failed to parse row {idx}: {e}")
                continue

        logger.info(f"Successfully parsed {len(transactions)} transactions from {file_path}")
        return transactions

    except Exception as e:
        logger.error(f"Failed to parse CSV file {file_path}: {e}")
        return []


def parse_csv_file(file_path: str) -> List[Dict[str, Any]]:
    """Parse a CSV file and return transactions.

    Auto-detects the CSV format and applies appropriate parsing logic.
    """
    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig', nrows=5)
        csv_format = detect_csv_format(df)

        if csv_format == 'bank_statement':
            return parse_bank_statement_csv(file_path)
        elif csv_format == 'generic_statement':
            return parse_bank_statement_csv(file_path)  # Use same parser for now
        else:
            logger.warning(f"Unknown CSV format for {file_path}. Attempting bank statement parser.")
            return parse_bank_statement_csv(file_path)

    except Exception as e:
        logger.error(f"Failed to parse CSV file {file_path}: {e}")
        return []
