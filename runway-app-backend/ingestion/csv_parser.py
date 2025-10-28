"""
CSV Statement Parser

Handles CSV exports from various banks with automatic column detection.
"""

import pandas as pd
import re
import logging
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class CSVParser:
    """
    CSV statement parser with automatic column detection

    Supports various CSV formats from different banks.
    """

    def __init__(self, bank_name: Optional[str] = None):
        """
        Initialize CSV parser

        Args:
            bank_name: Bank name for bank-specific parsing rules
        """
        self.bank_name = bank_name

    def parse(self, csv_path: str, encoding: str = 'utf-8') -> List[Dict]:
        """
        Parse CSV statement

        Args:
            csv_path: Path to CSV file
            encoding: File encoding (default: utf-8, try: latin-1, cp1252)

        Returns:
            List of transaction dictionaries

        Raises:
            ValueError: If CSV cannot be parsed
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV not found: {csv_path}")

        logger.info(f"Parsing CSV: {csv_path}")

        # Try different encodings
        encodings = [encoding, 'utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        df = None

        for enc in encodings:
            try:
                df = pd.read_csv(csv_path, encoding=enc)
                logger.info(f"Successfully read CSV with encoding: {enc}")
                break
            except Exception as e:
                logger.debug(f"Failed with encoding {enc}: {e}")
                continue

        if df is None or df.empty:
            raise ValueError(f"Could not read CSV: {csv_path}")

        # Clean column names
        df.columns = [str(col).strip() for col in df.columns]

        # Parse transactions
        transactions = self._parse_dataframe(df)

        logger.info(f"Extracted {len(transactions)} transactions from CSV")
        return transactions

    def _parse_dataframe(self, df: pd.DataFrame) -> List[Dict]:
        """
        Parse transactions from DataFrame

        Automatically detects column mapping.
        """
        # Normalize column names for matching
        col_map = self._detect_columns(df)

        if not col_map.get('date') or not col_map.get('description'):
            raise ValueError(
                f"Could not detect required columns. "
                f"Found columns: {list(df.columns)}"
            )

        transactions = []

        for idx, row in df.iterrows():
            try:
                # Extract fields
                date = str(row[col_map['date']]).strip()
                description = str(row[col_map['description']]).strip()

                # Skip invalid rows
                if not date or date == 'nan' or not description or description == 'nan':
                    continue

                # Extract amount (handle debit/credit columns)
                amount, txn_type = self._extract_amount_and_type(row, col_map)
                if amount is None:
                    continue

                # Extract balance if available
                balance = None
                if col_map.get('balance'):
                    balance_str = str(row[col_map['balance']]).strip()
                    balance_str = re.sub(r'[^\d.-]', '', balance_str)
                    if balance_str and balance_str != 'nan':
                        try:
                            balance = float(balance_str)
                        except ValueError:
                            pass

                # Extract reference number if available
                ref_number = None
                if col_map.get('reference'):
                    ref_number = str(row[col_map['reference']]).strip()
                    if ref_number == 'nan':
                        ref_number = None

                transactions.append({
                    'date': self._normalize_date(date),
                    'description': description,
                    'amount': amount,
                    'type': txn_type,
                    'balance': balance,
                    'reference_number': ref_number,
                })

            except Exception as e:
                logger.debug(f"Failed to parse row {idx}: {e}")
                continue

        return transactions

    def _detect_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Detect column mapping from CSV

        Returns:
            Dictionary mapping field names to column names
        """
        col_map = {}

        # Normalize column names for matching
        columns_lower = {col: col.lower().strip() for col in df.columns}

        # Date column
        date_keywords = ['date', 'txn date', 'transaction date', 'value date', 'posting date']
        col_map['date'] = self._find_column_by_keywords(columns_lower, date_keywords)

        # Description column
        desc_keywords = ['description', 'particulars', 'narration', 'details', 'remarks']
        col_map['description'] = self._find_column_by_keywords(columns_lower, desc_keywords)

        # Amount columns (debit/credit or single amount)
        debit_keywords = ['debit', 'withdrawal', 'dr', 'withdraw']
        credit_keywords = ['credit', 'deposit', 'cr']
        amount_keywords = ['amount', 'txn amount', 'transaction amount']

        col_map['debit'] = self._find_column_by_keywords(columns_lower, debit_keywords)
        col_map['credit'] = self._find_column_by_keywords(columns_lower, credit_keywords)
        col_map['amount'] = self._find_column_by_keywords(columns_lower, amount_keywords)

        # Balance column
        balance_keywords = ['balance', 'closing balance', 'available balance']
        col_map['balance'] = self._find_column_by_keywords(columns_lower, balance_keywords)

        # Reference number
        ref_keywords = ['reference', 'ref no', 'txn id', 'transaction id', 'cheque no']
        col_map['reference'] = self._find_column_by_keywords(columns_lower, ref_keywords)

        return {k: v for k, v in col_map.items() if v is not None}

    @staticmethod
    def _find_column_by_keywords(columns_lower: Dict[str, str], keywords: List[str]) -> Optional[str]:
        """Find column by matching keywords"""
        for original_col, lower_col in columns_lower.items():
            for keyword in keywords:
                if keyword in lower_col:
                    return original_col
        return None

    def _extract_amount_and_type(self, row: pd.Series, col_map: Dict[str, str]) -> tuple[Optional[float], str]:
        """
        Extract amount and transaction type from row

        Returns:
            (amount, type) tuple
        """
        # Case 1: Separate debit/credit columns
        if col_map.get('debit') and col_map.get('credit'):
            debit_val = str(row[col_map['debit']]).strip()
            credit_val = str(row[col_map['credit']]).strip()

            # Clean amount strings
            debit_val = re.sub(r'[^\d.-]', '', debit_val)
            credit_val = re.sub(r'[^\d.-]', '', credit_val)

            # Try debit first
            if debit_val and debit_val != 'nan' and debit_val != '':
                try:
                    return abs(float(debit_val)), 'debit'
                except ValueError:
                    pass

            # Try credit
            if credit_val and credit_val != 'nan' and credit_val != '':
                try:
                    return abs(float(credit_val)), 'credit'
                except ValueError:
                    pass

            return None, 'unknown'

        # Case 2: Single amount column
        elif col_map.get('amount'):
            amount_val = str(row[col_map['amount']]).strip()
            amount_val = re.sub(r'[^\d.-]', '', amount_val)

            if amount_val and amount_val != 'nan' and amount_val != '':
                try:
                    amount = float(amount_val)
                    # Determine type by sign
                    if amount < 0:
                        return abs(amount), 'debit'
                    else:
                        return abs(amount), 'credit'
                except ValueError:
                    pass

            return None, 'unknown'

        else:
            # No amount column found
            return None, 'unknown'

    @staticmethod
    def _normalize_date(date_str: str) -> str:
        """
        Normalize date to ISO format (YYYY-MM-DD)

        Handles formats: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, etc.
        """
        date_str = date_str.strip()

        # Try different formats
        formats = [
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y-%m-%d',
            '%d %b %Y',
            '%d-%b-%Y',
            '%d %B %Y',
            '%d-%B-%Y',
            '%m/%d/%Y',  # US format
            '%Y/%m/%d',
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        # If all fail, return as-is
        logger.warning(f"Could not parse date: {date_str}")
        return date_str


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = CSVParser(bank_name="HDFC Bank")

    # Example: Parse a CSV statement
    # transactions = parser.parse("data/raw/hdfc_statement.csv")
    # print(f"Extracted {len(transactions)} transactions")
    # for txn in transactions[:3]:
    #     print(txn)

    print("CSV Parser initialized")
