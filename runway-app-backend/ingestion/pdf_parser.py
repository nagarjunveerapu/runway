"""
PDF Parser with Multi-Strategy Fallback

Strategy Chain:
1. pdfplumber text extraction (70-80% success, zero deps)
2. pdfplumber table extraction (moderate success, zero deps)
3. Tabula (requires Java, optional)
4. Camelot (requires Ghostscript, optional)
5. OCR with pytesseract (requires Tesseract, optional, slow)

Realistic Expectations:
- pdfplumber text: 70-80% success rate
- pdfplumber tables: 40-60% success rate
- Camelot: 30-50% success rate (complex PDFs)
- OCR: 30-40% success rate (slow, last resort)
"""

import pdfplumber
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
    parse_amount_string,
    DATE_KEYWORDS,
    DESC_KEYWORDS
)

# Optional imports with graceful degradation
try:
    from config import Config
    ENABLE_TABULA = Config.ENABLE_TABULA
    ENABLE_CAMELOT = Config.ENABLE_CAMELOT
    ENABLE_OCR = Config.ENABLE_PDF_OCR
except ImportError:
    ENABLE_TABULA = False
    ENABLE_CAMELOT = False
    ENABLE_OCR = False

# Optional dependency imports
if ENABLE_TABULA:
    try:
        import tabula
    except ImportError:
        logging.warning("tabula-py not available (requires Java)")
        ENABLE_TABULA = False

if ENABLE_CAMELOT:
    try:
        import camelot
    except ImportError:
        logging.warning("camelot-py not available (requires Ghostscript)")
        ENABLE_CAMELOT = False

if ENABLE_OCR:
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError:
        logging.warning("pytesseract/pdf2image not available (requires Tesseract)")
        ENABLE_OCR = False

logger = logging.getLogger(__name__)


class PDFParser:
    """
    PDF statement parser with multi-strategy fallback

    Tries multiple extraction strategies in order of reliability and performance.
    """

    def __init__(self, bank_name: Optional[str] = None):
        """
        Initialize PDF parser

        Args:
            bank_name: Bank name for bank-specific parsing rules
        """
        self.bank_name = bank_name
        self.strategies_attempted = []
        self.success_strategy = None
        self.metadata = {}  # Store extracted metadata

    def parse(self, pdf_path: str) -> List[Dict]:
        """
        Parse PDF statement using multi-strategy fallback

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of transaction dictionaries

        Raises:
            ValueError: If no strategy succeeds
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Store pdf_path as instance variable for use in helper methods
        self.pdf_path = pdf_path

        logger.info(f"Parsing PDF: {pdf_path}")

        # Step 1: Extract metadata from first page before parsing transactions
        logger.info("🔍 Extracting metadata from PDF...")
        self.metadata = self._extract_metadata(pdf_path)
        if self.metadata:
            logger.info(f"✅ Extracted metadata: Account={self.metadata.get('account_number')}, Bank={self.metadata.get('bank_name')}, Holder={self.metadata.get('account_holder_name')}")
        else:
            logger.info("⚠️  No metadata extracted from PDF")

        # Step 2: Parse transactions using strategies
        strategies = [
            ("pdfplumber_text", self._extract_with_pdfplumber_text),
            ("pdfplumber_tables", self._extract_with_pdfplumber_tables),
        ]

        if ENABLE_TABULA:
            strategies.append(("tabula", self._extract_with_tabula))

        if ENABLE_CAMELOT:
            strategies.append(("camelot", self._extract_with_camelot))

        if ENABLE_OCR:
            strategies.append(("ocr", self._extract_with_ocr))

        transactions = []
        for strategy_name, strategy_func in strategies:
            self.strategies_attempted.append(strategy_name)
            logger.info(f"Trying strategy: {strategy_name}")

            try:
                transactions = strategy_func(str(pdf_path))
                if transactions and len(transactions) > 0:
                    self.success_strategy = strategy_name
                    logger.info(f"✅ Success with {strategy_name}: {len(transactions)} transactions")
                    break
                else:
                    logger.warning(f"Strategy {strategy_name} returned no transactions")
            except Exception as e:
                logger.warning(f"Strategy {strategy_name} failed: {e}")
                continue

        if not transactions:
            raise ValueError(
                f"All extraction strategies failed. "
                f"Tried: {', '.join(self.strategies_attempted)}"
            )

        logger.info(f"Extracted {len(transactions)} transactions using {self.success_strategy}")
        return transactions

    def _extract_with_pdfplumber_text(self, pdf_path: str) -> List[Dict]:
        """
        Strategy 1: pdfplumber text extraction

        Success rate: 70-80%
        Dependencies: pdfplumber only (zero extra deps)
        Best for: Well-formatted PDF statements with clear text
        """
        transactions = []

        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            logger.info(f"Processing {total_pages} pages with pdfplumber text extraction")
            
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if not text:
                    logger.debug(f"Page {page_num}: No text extracted")
                    continue

                # Parse transactions from text
                page_txns = self._parse_text_transactions(text)
                logger.info(f"Page {page_num}: Extracted {len(page_txns)} transactions")
                transactions.extend(page_txns)

        logger.info(f"Total transactions extracted from text: {len(transactions)}")
        return transactions

    def _extract_with_pdfplumber_tables(self, pdf_path: str) -> List[Dict]:
        """
        Strategy 2: pdfplumber table extraction

        Success rate: 40-60%
        Dependencies: pdfplumber only
        Best for: PDFs with clear table structures
        """
        transactions = []

        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            logger.info(f"Processing {total_pages} pages with pdfplumber table extraction")
            
            for page_num, page in enumerate(pdf.pages, 1):
                tables = page.extract_tables()
                if not tables:
                    logger.debug(f"Page {page_num}: No tables found")
                    continue

                logger.info(f"Page {page_num}: Found {len(tables)} table(s)")
                for table_idx, table in enumerate(tables):
                    if not table or len(table) == 0:
                        logger.debug(f"Page {page_num}, Table {table_idx + 1}: Empty table, skipping")
                        continue
                    
                    table_txns = self._parse_table_transactions(table)
                    logger.info(f"Page {page_num}, Table {table_idx + 1}: Extracted {len(table_txns)} transactions")
                    transactions.extend(table_txns)

        logger.info(f"Total transactions extracted from tables: {len(transactions)}")
        return transactions

    def _extract_with_tabula(self, pdf_path: str) -> List[Dict]:
        """
        Strategy 3: Tabula (requires Java)

        Success rate: 50-70%
        Dependencies: tabula-py, Java JRE
        Best for: PDFs with complex table structures
        """
        if not ENABLE_TABULA:
            raise ImportError("Tabula not enabled")

        dfs = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True)
        transactions = []

        for df in dfs:
            if df.empty:
                continue
            table_txns = self._parse_dataframe_transactions(df)
            transactions.extend(table_txns)

        return transactions

    def _extract_with_camelot(self, pdf_path: str) -> List[Dict]:
        """
        Strategy 4: Camelot (requires Ghostscript)

        Success rate: 30-50%
        Dependencies: camelot-py, Ghostscript
        Best for: PDFs where other methods fail
        """
        if not ENABLE_CAMELOT:
            raise ImportError("Camelot not enabled")

        tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream')
        transactions = []

        for table in tables:
            df = table.df
            if df.empty:
                continue
            table_txns = self._parse_dataframe_transactions(df)
            transactions.extend(table_txns)

        return transactions

    def _extract_with_ocr(self, pdf_path: str) -> List[Dict]:
        """
        Strategy 5: OCR (requires Tesseract)

        Success rate: 30-40%
        Dependencies: pytesseract, pdf2image, Tesseract
        Best for: Scanned/image-based PDFs (last resort, slow)
        """
        if not ENABLE_OCR:
            raise ImportError("OCR not enabled")

        images = convert_from_path(pdf_path)
        transactions = []

        for i, image in enumerate(images):
            text = pytesseract.image_to_string(image)
            page_txns = self._parse_text_transactions(text)
            transactions.extend(page_txns)

        return transactions

    def _parse_text_transactions(self, text: str) -> List[Dict]:
        """
        Parse transactions from extracted text

        This is a generic parser. Override for bank-specific logic.
        """
        transactions = []
        lines = text.split('\n')

        # Generic pattern: DD/MM/YYYY or DD-MM-YYYY followed by description and amount
        # Support more date formats: DD/MM/YY, DD-MM-YY, DD.MM.YYYY, etc.
        date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        amount_pattern = r'[\d,]+\.\d{2}'

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for date - try at start first, then anywhere in line
            # Bank statements typically start transaction rows with a date
            date_match = re.match(date_pattern, line)
            if not date_match:
                # Try searching anywhere in the line (for multi-column layouts)
                date_match = re.search(date_pattern, line)
                if not date_match:
                    continue

            date_str = date_match.group(1)

            # Look for amount
            amount_matches = re.findall(amount_pattern, line)
            if not amount_matches:
                continue
            
            # Accept transactions with 1+ amounts
            # Prefer 2+ amounts (amount + balance), but don't skip single amount transactions
            # Some PDF statements may not include balance in every row

            # Extract description (text between date and amount)
            desc_start = date_match.end()
            amount_start = line.find(amount_matches[0], desc_start)
            description = line[desc_start:amount_start].strip()

            # Parse amounts: typically [withdrawal, deposit, balance]
            # or [amount, balance]
            # For most bank statements: withdrawal comes first, then deposit, then balance
            # We need to determine which is the actual transaction amount
            
            # Strategy: Look at all amounts on the line
            # Usually we have: withdrawal, deposit, balance (3 amounts)
            # Or: amount, balance (2 amounts)
            
            if len(amount_matches) >= 3:
                # We have withdrawal, deposit, and balance
                withdrawal = float(amount_matches[0].replace(',', ''))
                deposit = float(amount_matches[1].replace(',', ''))
                balance = float(amount_matches[2].replace(',', ''))
                
                # Determine which transaction occurred
                if withdrawal > 0 and deposit == 0:
                    # Money went out
                    amount = withdrawal
                    txn_type = 'debit'
                elif deposit > 0 and withdrawal == 0:
                    # Money came in
                    amount = deposit
                    txn_type = 'credit'
                else:
                    # Both or neither - take the non-zero one
                    amount = withdrawal if withdrawal > 0 else deposit
                    txn_type = 'debit' if withdrawal > 0 else 'credit'
                    
            elif len(amount_matches) == 2:
                # Usually: amount, balance
                amount = float(amount_matches[0].replace(',', ''))
                balance = float(amount_matches[1].replace(',', ''))
                
                # Try to determine type from context
                # Default to debit if no indication otherwise
                txn_type = 'debit'
                
                # Check for common credit indicators
                if any(indicator in line.upper() for indicator in ['CR', 'CREDIT', 'DEPOSIT', 'RECEIVED', 'CREDIT/CASH']):
                    txn_type = 'credit'
                elif any(indicator in line.upper() for indicator in ['DR', 'DEBIT', 'WITHDRAW', 'PAID']):
                    txn_type = 'debit'
                    
            else:
                # Only one amount - use it
                amount = float(amount_matches[0].replace(',', ''))
                balance = None
                txn_type = 'debit'  # Default
                
                # Try to determine type from context
                if any(indicator in line.upper() for indicator in ['CR', 'CREDIT', 'DEPOSIT', 'RECEIVED']):
                    txn_type = 'credit'
                elif any(indicator in line.upper() for indicator in ['DR', 'DEBIT', 'WITHDRAW', 'PAID']):
                    txn_type = 'debit'
            
            # Validate extracted data before creating transaction
            if not description or description.strip() == '':
                # Try to extract description from the entire line if empty
                logger.debug(f"Empty description for line: {line}")
                # Use full line minus date and amounts as description
                desc_parts = line.split(date_str, 1)
                if len(desc_parts) > 1:
                    description = desc_parts[1]
                    # Remove amounts from description
                    for amt in amount_matches:
                        description = description.replace(amt, '').strip()
                if not description or description.strip() == '':
                    description = 'Transaction from PDF'

            # Create transaction using common formatter
            tx = create_transaction_dict(
                description=description,
                amount=amount,
                txn_type=txn_type,
                date=date_str,
                balance=balance if 'balance' in locals() else None,
                source='PDF'
            )
            # Update notes with filename
            tx['notes'] = f'Parsed from PDF: {self.pdf_path.name}'
            
            transactions.append(tx)

        return transactions

    def _parse_table_transactions(self, table: List[List[str]]) -> List[Dict]:
        """
        Parse transactions from table data
        
        Handles table extraction from PDF, converting to DataFrame for processing.

        Args:
            table: List of rows, each row is a list of cell values

        Returns:
            List of transaction dictionaries
        """
        if not table or len(table) < 1:
            return []

        # Handle header row detection
        # First row is usually header, but might be empty or have metadata
        # Try to find the header row (has column names)
        header_row_idx = 0
        
        # Look for header row (contains keywords like 'date', 'transaction', 'amount', etc.)
        header_keywords = ['date', 'transaction', 'amount', 'description', 'remarks', 'withdrawal', 'deposit', 'balance']
        for idx, row in enumerate(table[:min(5, len(table))]):
            row_text = ' '.join([str(cell).lower() if cell else '' for cell in row])
            keyword_count = sum(1 for keyword in header_keywords if keyword in row_text)
            if keyword_count >= 3:
                header_row_idx = idx
                logger.debug(f"Found header row at index {idx} with {keyword_count} matching keywords")
                break
        
        if len(table) < header_row_idx + 2:
            logger.debug("Table has no data rows after header")
            return []

        # Convert to DataFrame for easier processing
        # Use header row as column names, skip rows before header
        try:
            # Clean header row
            header_row = [str(cell).strip() if cell else f'Unnamed_{i}' for i, cell in enumerate(table[header_row_idx])]
            
            # Convert data rows to DataFrame
            data_rows = table[header_row_idx + 1:]
            df = pd.DataFrame(data_rows, columns=header_row[:len(data_rows[0]) if data_rows else 0])
            
            # Ensure DataFrame has same number of columns as header
            if len(df.columns) != len(header_row):
                # Pad or truncate columns
                if len(df.columns) < len(header_row):
                    for i in range(len(df.columns), len(header_row)):
                        df[f'Unnamed_{i}'] = None
                else:
                    df = df.iloc[:, :len(header_row)]
            
            return self._parse_dataframe_transactions(df)
        except Exception as e:
            logger.warning(f"Failed to convert table to DataFrame: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []

    def _parse_dataframe_transactions(self, df: pd.DataFrame) -> List[Dict]:
        """
        Parse transactions from DataFrame
        
        This matches the CSV parser logic exactly to ensure consistent extraction.

        Args:
            df: DataFrame with transaction rows

        Returns:
            List of transaction dictionaries
        """
        transactions = []

        # Clean data exactly like CSV parser
        # Remove completely empty columns
        df = df.dropna(axis=1, how='all')
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        if df.empty:
            logger.warning("DataFrame is empty after cleaning")
            return []

        # Normalize column names for detection
        df.columns = [str(col).strip() for col in df.columns]
        
        logger.info(f"Processing DataFrame with {len(df)} rows and columns: {list(df.columns)}")
        
        # Detect columns using common utility (same as CSV parser)
        col_map = detect_columns(list(df.columns))

        # Verify required columns detected (same validation as CSV parser)
        if not col_map.get('date') or not col_map.get('description'):
            logger.warning(f"Could not identify required columns in table. Found columns: {list(df.columns)}")
            logger.warning(f"Column map: {col_map}")
            return []

        logger.info(f"Detected columns: {col_map}")

        # Parse rows exactly like CSV parser
        for idx, row in df.iterrows():
            try:
                # Extract raw data exactly like CSV parser
                date_str = str(row[col_map['date']]).strip() if pd.notna(row[col_map['date']]) else ''
                description = str(row[col_map['description']]).strip() if pd.notna(row[col_map['description']]) else ''

                # Skip invalid rows (same validation as CSV parser)
                if not date_str or date_str == 'nan' or not description or description == 'nan':
                    logger.debug(f"Row {idx}: Skipped - empty date or description (date='{date_str}', desc='{description[:30] if description else ''}')")
                    continue

                # Extract amounts using common utility (same as CSV parser)
                amount, txn_type, withdrawal, deposit = extract_amount_and_type(row, col_map)
                if amount is None:
                    logger.debug(f"Row {idx}: Skipped - no valid amount found (date='{date_str}', desc='{description[:30]}')")
                    continue

                # Extract balance using common utility (same as CSV parser)
                balance = extract_balance(row, col_map)

                # Create transaction using common formatter (same as CSV parser)
                tx = create_transaction_dict(
                    description=description,
                    amount=amount,
                    txn_type=txn_type,
                    date=date_str,
                    balance=balance,
                    source='PDF'
                )
                # Update notes with filename
                tx['notes'] = f'Parsed from PDF: {self.pdf_path.name}'
                
                transactions.append(tx)
                
                if len(transactions) % 50 == 0:
                    logger.info(f"Progress: {len(transactions)} transactions parsed")

            except Exception as e:
                logger.debug(f"Failed to parse row {idx}: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                continue

        logger.info(f"Successfully parsed {len(transactions)} transactions from DataFrame")
        return transactions



    def get_metadata(self) -> Dict:
        """Get metadata extracted from PDF file"""
        return self.metadata
    
    def _extract_metadata(self, pdf_path: str) -> Dict:
        """
        Extract metadata from PDF (account number, account holder name, bank name)
        
        Reads the first page of the PDF and searches for:
        - Account number (8+ digits)
        - Account holder name (usually near account number)
        - Bank name (explicit mentions or legends)
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with metadata (account_number, account_holder_name, bank_name)
        """
        metadata = {
            'account_number': None,
            'account_holder_name': None,
            'bank_name': None,
            'account_type': None  # Will be inferred if not found
        }
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if not pdf.pages:
                    return metadata
                
                # Extract text from first page (most likely to contain account metadata)
                first_page = pdf.pages[0]
                text = first_page.extract_text()
                
                if not text:
                    logger.debug("First page has no text, trying second page...")
                    if len(pdf.pages) > 1:
                        text = pdf.pages[1].extract_text()
                
                if not text:
                    logger.warning("No text found in first two pages for metadata extraction")
                    return metadata
                
                lines = text.split('\n')
                text_lower = text.lower()
                
                # Step 1: Extract account number and holder name
                # Pattern 1: "Account Number: 055801511557 - NAGARJUN VEERAPU"
                # Pattern 2: "055801511557 ( INR ) - NAGARJUN VEERAPU"
                account_pattern = r'(\d{8,})\s*[^-]*-\s*([^,\n]+)'
                account_match = re.search(account_pattern, text)
                if account_match:
                    metadata['account_number'] = account_match.group(1)
                    metadata['account_holder_name'] = account_match.group(2).strip()
                    logger.info(f"✅ Extracted account info: Number={metadata['account_number']}, Holder={metadata['account_holder_name']}")
                else:
                    # Fallback: Just find account number (8+ digits)
                    account_num_match = re.search(r'(\d{8,})', text)
                    if account_num_match:
                        metadata['account_number'] = account_num_match.group(1)
                        logger.info(f"✅ Extracted account number only: {metadata['account_number']}")
                
                # Step 2: Extract bank name from HEADER section only (first 20 lines)
                # This avoids false positives from transaction descriptions
                # Many statements have "YES BANK" or "HDFC BANK" in UPI transaction descriptions
                header_text = '\n'.join(lines[:20]).lower()
                
                bank_patterns = {
                    'ICICI Bank': ['icici bank', 'icici direct', 'within icici bank', 'icici bank account'],
                    'HDFC Bank': ['hdfc bank', 'hdfc bank account'],
                    'Axis Bank': ['axis bank', 'axis bank account'],
                    'State Bank of India': ['state bank of india', 'sbi bank'],
                    'Canara Bank': ['canara bank'],
                    'YES Bank': ['yes bank account', 'yes bank ltd'],  # More specific patterns
                    'Kotak Mahindra Bank': ['kotak mahindra', 'kotak bank'],
                }
                
                # First, check header section only (more reliable)
                for bank_name, patterns in bank_patterns.items():
                    if any(pattern in header_text for pattern in patterns):
                        metadata['bank_name'] = bank_name
                        logger.info(f"✅ Extracted bank name from header: {bank_name}")
                        break
                
                # If not found in header, try to infer from account number patterns
                # ICICI account numbers often start with specific patterns (e.g., 055, 006, etc.)
                if not metadata.get('bank_name') and metadata.get('account_number'):
                    account_num = metadata['account_number']
                    # ICICI account numbers are typically 12 digits, often starting with 055, 006, etc.
                    if len(account_num) == 12 and account_num.startswith('055'):
                        metadata['bank_name'] = 'ICICI Bank'
                        logger.info(f"✅ Inferred bank name from account number pattern: ICICI Bank")
                    elif len(account_num) == 12 and account_num.startswith('006'):
                        metadata['bank_name'] = 'ICICI Bank'
                        logger.info(f"✅ Inferred bank name from account number pattern: ICICI Bank")
                    else:
                        logger.info(f"⚠️  Could not detect bank name from header, account number: {account_num}")
                
                # Last resort: Check full text, but only if we still don't have a bank name
                # This is less reliable as transaction descriptions may mention other banks
                if not metadata.get('bank_name'):
                    for bank_name, patterns in bank_patterns.items():
                        # Skip YES Bank in full text check as it's often in UPI transactions
                        if bank_name == 'YES Bank':
                            continue
                        if any(pattern in text_lower for pattern in patterns):
                            metadata['bank_name'] = bank_name
                            logger.info(f"✅ Extracted bank name from full text: {bank_name}")
                            break
                
                # Step 3: Check legends/watermarks in text for bank name
                # Many PDFs have bank name in legends like "Within ICICI Bank", "ICICI Direct", etc.
                for line in lines[:50]:  # Check first 50 lines
                    line_lower = line.lower()
                    if 'within' in line_lower and 'bank' in line_lower:
                        # Try to extract bank name from "Within [BANK NAME] Bank"
                        within_match = re.search(r'within\s+([^,\n]+?)\s+bank', line_lower)
                        if within_match:
                            bank_text = within_match.group(1).strip().title()
                            if bank_text:
                                metadata['bank_name'] = f"{bank_text} Bank"
                                logger.info(f"✅ Extracted bank name from legend: {metadata['bank_name']}")
                                break
                
                # Step 4: Infer account type from text if possible
                # Check if account type is mentioned in first page
                if not metadata.get('account_type'):
                    text_lower = text.lower()
                    if 'credit card' in text_lower or 'credit card account' in text_lower:
                        metadata['account_type'] = 'credit_card'
                        logger.info("✅ Detected account type: credit_card")
                    elif 'current account' in text_lower or 'salary account' in text_lower:
                        metadata['account_type'] = 'current'
                        logger.info("✅ Detected account type: current")
                    elif 'savings account' in text_lower or 'savings' in text_lower:
                        metadata['account_type'] = 'savings'
                        logger.info("✅ Detected account type: savings")
                
                return metadata
                
        except Exception as e:
            logger.warning(f"⚠️  Error extracting metadata from PDF: {e}")
            return metadata
    
    def get_success_info(self) -> Dict:
        """Get information about parsing success"""
        return {
            'strategies_attempted': self.strategies_attempted,
            'success_strategy': self.success_strategy,
            'enabled_strategies': {
                'pdfplumber': True,
                'tabula': ENABLE_TABULA,
                'camelot': ENABLE_CAMELOT,
                'ocr': ENABLE_OCR,
            }
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = PDFParser(bank_name="HDFC Bank")

    # Example: Parse a PDF statement
    # transactions = parser.parse("data/raw/hdfc_statement.pdf")
    # print(f"Extracted {len(transactions)} transactions")
    # print(f"Strategy used: {parser.success_strategy}")

    print("PDF Parser initialized")
    print(f"Available strategies: {list(parser.get_success_info()['enabled_strategies'].keys())}")
