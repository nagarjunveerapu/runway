"""
CSV Statement Parser (Enhanced)

Combines best features from legacy and new parsers:
- Multiple encoding support (from new parser)
- Better date normalization (from new parser)
- Flexible column detection (from new parser)
- UUID generation (from legacy parser)
- Merchant/channel extraction (from legacy parser)
- Legacy-compatible output format (for compatibility)

Output format matches legacy parser:
- 'id', 'raw_remark', 'remark', 'transaction_type', 'withdrawal', 'deposit', etc.
"""

import pandas as pd
import re
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path

# Import common transaction formatting and parsing utilities
from ingestion.transaction_formatter import (
    create_transaction_dict,
    detect_columns,
    extract_amount_and_type,
    extract_balance,
    DATE_KEYWORDS,
    DESC_KEYWORDS,
    DEBIT_KEYWORDS,
    CREDIT_KEYWORDS,
    AMOUNT_KEYWORDS,
    BALANCE_KEYWORDS,
    REF_KEYWORDS
)

logger = logging.getLogger(__name__)


class CSVParser:
    """
    Enhanced CSV statement parser combining best features from both parsers
    
    Features:
    - Multiple encoding support (utf-8, latin-1, cp1252, iso-8859-1)
    - Flexible column detection (keyword matching)
    - Date normalization (multiple formats)
    - UUID generation
    - Merchant/channel extraction
    - Legacy-compatible output format
    """

    def __init__(self, bank_name: Optional[str] = None):
        """
        Initialize CSV parser

        Args:
            bank_name: Bank name for bank-specific parsing rules
        """
        self.bank_name = bank_name

    def parse(self, csv_path: str, encoding: str = 'utf-8') -> Tuple[List[Dict], Dict]:
        """
        Parse CSV statement

        Args:
            csv_path: Path to CSV file
            encoding: File encoding (default: utf-8, tries multiple encodings)

        Returns:
            Tuple of (transactions list, metadata dict)
            - transactions: List of transaction dictionaries (legacy format)
            - metadata: Dictionary with account_number, account_holder_name, bank_name, etc.

        Raises:
            ValueError: If CSV cannot be parsed
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV not found: {csv_path}")

        logger.info(f"Parsing CSV: {csv_path}")

        # Try different encodings (feature from new parser)
        encodings = ['utf-8-sig', encoding, 'utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        df = None

        for enc in encodings:
            try:
                df = pd.read_csv(csv_path, encoding=enc, header=None)  # Read without header first
                logger.info(f"Successfully read CSV with encoding: {enc}")
                break
            except Exception as e:
                logger.debug(f"Failed with encoding {enc}: {e}")
                continue

        if df is None:
            raise ValueError(f"Could not read CSV: {csv_path} - All encoding attempts failed")
        
        if df.empty:
            raise ValueError(f"CSV file is empty: {csv_path}")
        
        logger.info(f"CSV read successfully: {len(df)} rows, {len(df.columns)} columns")

        # Extract metadata from header rows (typically rows 0-12)
        metadata = self._extract_metadata(df)
        
        # Find the actual header row (row with column names like "Value Date", "Transaction Date", etc.)
        header_row_idx = self._find_header_row(df)
        
        if header_row_idx is None:
            # Fallback: try to detect columns from first few rows
            logger.warning("Could not find header row, attempting column detection from first rows")
            df.columns = [str(col).strip() for col in df.columns]
        else:
            # Use the found header row
            logger.info(f"Found header row at index {header_row_idx}")
            # Set column names from header row
            # Filter out 'nan' column names (from empty cells in header row)
            column_names = []
            for cell in df.iloc[header_row_idx]:
                cell_str = str(cell).strip() if pd.notna(cell) else ''
                # Skip empty cells and 'nan' strings - use placeholder for empty columns
                if cell_str and cell_str.lower() != 'nan':
                    column_names.append(cell_str)
                else:
                    column_names.append(None)  # Mark for later removal
            
            # Set column names (including None for empty columns)
            df.columns = column_names
            # Skip all rows before header (metadata rows)
            df = df.iloc[header_row_idx + 1:].reset_index(drop=True)
            
            # Remove columns with None names (empty columns)
            df = df[[col for col in df.columns if col is not None]]
        
        # Clean column names (handle remaining None values and 'nan' strings)
        cleaned_cols = []
        for i, col in enumerate(df.columns):
            if col is None:
                cleaned_cols.append(f'_col_{i}')
            else:
                col_str = str(col).strip()
                if col_str.lower() == 'nan':
                    cleaned_cols.append(f'_col_{i}')
                else:
                    cleaned_cols.append(col_str)
        df.columns = cleaned_cols

        # Clean data (feature from legacy parser)
        df = df.dropna(axis=1, how='all')  # Remove empty columns
        df = df.dropna(how='all')  # Remove empty rows

        # Parse transactions
        transactions = self._parse_dataframe(df, csv_path)

        logger.info(f"Extracted {len(transactions)} transactions from CSV")
        logger.info(f"Extracted metadata: {metadata}")
        return transactions, metadata

    def _parse_dataframe(self, df: pd.DataFrame, csv_path: Path) -> List[Dict]:
        """
        Parse transactions from DataFrame (returns legacy format)

        Args:
            df: DataFrame with CSV data
            csv_path: Path to CSV file (for notes)

        Returns:
            List of transaction dictionaries (legacy format)
        """
        # Detect columns (feature from new parser - more flexible)
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
                date_str = str(row[col_map['date']]).strip() if pd.notna(row[col_map['date']]) else ''
                description = str(row[col_map['description']]).strip() if pd.notna(row[col_map['description']]) else ''

                # Skip invalid rows (same as legacy parser)
                if not date_str or date_str == 'nan' or not description or description == 'nan':
                    continue

                # Extract amounts using common utility
                # Parser's responsibility: Pass row data, column map
                # Amount extraction logic: In transaction_formatter
                amount, txn_type, withdrawal, deposit = extract_amount_and_type(row, col_map)
                if amount is None:
                    continue

                # Extract balance using common utility
                balance = extract_balance(row, col_map)

                # Create transaction using common formatter
                tx = create_transaction_dict(
                    description=description,
                    amount=amount,
                    txn_type=txn_type,
                    date=date_str,
                    balance=balance,
                    source='CSV'
                )
                # Update notes with filename
                tx['notes'] = f'Parsed from CSV: {csv_path.name}'

                transactions.append(tx)

            except Exception as e:
                logger.debug(f"Failed to parse row {idx}: {e}")
                continue

        return transactions

    def _extract_metadata(self, df: pd.DataFrame) -> Dict[str, Optional[str]]:
        """
        Extract metadata from header rows (account number, account holder name, etc.)
        
        Args:
            df: DataFrame with all rows (including metadata rows)

        Returns:
            Dictionary with metadata (account_number, account_holder_name, bank_name)
        """
        metadata = {
            'account_number': None,
            'account_holder_name': None,
            'bank_name': None,
            'account_type': None  # Will be inferred if not found
        }
        
        # Step 1: Search header rows (first 20 rows) for metadata - HIGH PRIORITY
        # Check legends section at the bottom for bank name - VERY HIGH PRIORITY
        header_end = min(20, len(df))
        legends_start = max(0, len(df) - 10)  # Last 10 rows often contain legends
        
        # Step 1a: Check legends section first (most reliable for bank name)
        for idx in range(legends_start, len(df)):
            row_values = [str(val).strip() if pd.notna(val) else '' for val in df.iloc[idx]]
            row_text = ' '.join(row_values).lower()
            
            # Look for explicit bank name in legends (e.g., "Within ICICI Bank", "ICICI Direct")
            if 'within icici bank' in row_text or 'icici direct' in row_text:
                metadata['bank_name'] = 'ICICI Bank'
                break
        
        # Step 1b: Search header rows for account number and bank name
        for idx in range(header_end):
            # Get all row values, handling NaN and converting to strings
            row_values = []
            for val in df.iloc[idx]:
                if pd.notna(val):
                    row_values.append(str(val).strip())
                else:
                    row_values.append('')
            
            row_text = ' '.join(row_values).lower()
            
            # Look for account number line (e.g., "Account Number,,055801511557 ( INR )  - NAGARJUN VEERAPU")
            if 'account number' in row_text:
                # Method 1: Extract from individual cell values
                for i, val in enumerate(row_values):
                    if val and 'account number' not in val.lower():
                        # Try to extract account number and name from this cell
                        # Pattern: "055801511557 ( INR )  - NAGARJUN VEERAPU"
                        # Look for digits followed by name after dash
                        account_match = re.search(r'(\d{8,})\s*[^-]*-\s*([^,\n]+)', val)
                        if account_match:
                            metadata['account_number'] = account_match.group(1)
                            metadata['account_holder_name'] = account_match.group(2).strip()
                            logger.info(f"✅ Extracted from cell {i}: Account={metadata['account_number']}, Holder={metadata['account_holder_name']}")
                            break
                
                # Method 2: If not found in individual cells, extract from full row text
                if not metadata['account_number']:
                    full_text = ' '.join(row_values)
                    # Pattern: "Account Number,,055801511557 ( INR )  - NAGARJUN VEERAPU"
                    # More flexible pattern: account number anywhere, then dash, then name
                    account_match = re.search(r'(\d{8,})\s*[^-]*-\s*([^,\n]+)', full_text)
                    if account_match:
                        metadata['account_number'] = account_match.group(1)
                        metadata['account_holder_name'] = account_match.group(2).strip()
                        logger.info(f"✅ Extracted from full row: Account={metadata['account_number']}, Holder={metadata['account_holder_name']}")
                
                # Method 3: If still not found, try simpler pattern (just account number)
                if not metadata['account_number']:
                    full_text = ' '.join(row_values)
                    # Just find account number (8+ digits)
                    account_match = re.search(r'(\d{8,})', full_text)
                    if account_match:
                        metadata['account_number'] = account_match.group(1)
                        logger.info(f"✅ Extracted account number only: {metadata['account_number']}")
            
            # Look for bank name in header rows only (not transaction rows)
            # Check for explicit bank name mentions in header section
            # Priority: More specific patterns first to avoid false positives
            if not metadata['bank_name']:  # Only check if not already found from legends
                full_row_text = ' '.join(row_values).lower()
                
                # Look for bank name patterns in header section
                # Check ICICI first with specific patterns (most common)
                if 'icici bank' in full_row_text or 'icici bank account' in full_row_text or 'icici direct' in full_row_text:
                    metadata['bank_name'] = 'ICICI Bank'
                elif 'hdfc bank' in full_row_text or 'hdfc bank account' in full_row_text:
                    metadata['bank_name'] = 'HDFC Bank'
                elif 'axis bank' in full_row_text or 'axis bank account' in full_row_text:
                    metadata['bank_name'] = 'Axis Bank'
                elif ('sbi' in full_row_text or 'state bank of india' in full_row_text) and 'state bank' in full_row_text:
                    metadata['bank_name'] = 'State Bank of India'
                elif 'canara bank' in full_row_text:
                    metadata['bank_name'] = 'Canara Bank'
                # YES Bank only if explicitly mentioned in account context (not transaction descriptions)
                elif ('yes bank account' in full_row_text or 'yes bank ltd' in full_row_text) and 'account' in full_row_text:
                    metadata['bank_name'] = 'YES Bank'
                elif 'kotak' in full_row_text or 'kotak mahindra' in full_row_text:
                    metadata['bank_name'] = 'Kotak Mahindra Bank'
        
        # Step 2: Infer account type from metadata if possible
        # Check if account type is mentioned in header rows
        if not metadata.get('account_type'):
            for idx in range(min(20, len(df))):
                row_values = [str(val).strip().lower() if pd.notna(val) else '' for val in df.iloc[idx]]
                row_text = ' '.join(row_values)
                
                # Check for account type indicators
                if 'credit card' in row_text or 'credit card account' in row_text:
                    metadata['account_type'] = 'credit_card'
                    break
                elif 'current account' in row_text or 'salary account' in row_text:
                    metadata['account_type'] = 'current'
                    break
                elif 'savings account' in row_text or 'savings' in row_text:
                    metadata['account_type'] = 'savings'
                    break
        
        # Step 3: If bank name not found in header/legends, try to infer from account number patterns
        # ICICI account numbers are typically 12 digits, often starting with 055, 006, etc.
        if not metadata.get('bank_name') and metadata.get('account_number'):
            account_num = metadata['account_number']
            if len(account_num) == 12 and account_num.startswith('055'):
                metadata['bank_name'] = 'ICICI Bank'
                logger.info(f"✅ Inferred bank name from account number pattern: ICICI Bank")
            elif len(account_num) == 12 and account_num.startswith('006'):
                metadata['bank_name'] = 'ICICI Bank'
                logger.info(f"✅ Inferred bank name from account number pattern: ICICI Bank")
        
        # Step 4: If bank name not found, check filename or default to None
        # Don't infer from transaction descriptions (too unreliable)
        
        return metadata
    
    def _find_header_row(self, df: pd.DataFrame) -> Optional[int]:
        """
        Find the row index containing actual column headers
        
        Looks for rows containing typical transaction column names like:
        "Value Date", "Transaction Date", "Transaction Remarks", etc.
        
        Args:
            df: DataFrame with all rows

        Returns:
            Row index of header row, or None if not found
        """
        header_keywords = [
            'value date', 'transaction date', 'transaction remarks',
            'withdrawal amount', 'deposit amount', 'balance',
            'cheque number', 's no', 'sno', 'serial number'
        ]
        
        # Check first 20 rows for header
        for idx in range(min(20, len(df))):
            row_values = [str(val).strip().lower() if pd.notna(val) else '' for val in df.iloc[idx]]
            row_text = ' '.join(row_values)
            
            # Count how many header keywords are found in this row
            keyword_count = sum(1 for keyword in header_keywords if keyword in row_text)
            
            # If we find 3+ header keywords, this is likely the header row
            if keyword_count >= 3:
                logger.info(f"Found header row at index {idx} with {keyword_count} matching keywords")
                return idx
        
        return None

    def _detect_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Detect column mapping from CSV using common utilities
        
        Parser's responsibility: Extract column names from DataFrame
        Column detection logic: In transaction_formatter
        """
        # Use common column detection utility
        return detect_columns(list(df.columns))



# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = CSVParser(bank_name="HDFC Bank")

    # Example: Parse a CSV statement
    # transactions = parser.parse("data/raw/hdfc_statement.csv")
    # print(f"Extracted {len(transactions)} transactions")
    # for txn in transactions[:3]:
    #     print(txn)

    print("Enhanced CSV Parser initialized")
