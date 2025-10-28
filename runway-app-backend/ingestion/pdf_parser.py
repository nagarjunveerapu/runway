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
from datetime import datetime

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

        logger.info(f"Parsing PDF: {pdf_path}")

        # Try strategies in order
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
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if not text:
                    continue

                # Parse transactions from text
                page_txns = self._parse_text_transactions(text)
                transactions.extend(page_txns)

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
            for page_num, page in enumerate(pdf.pages, 1):
                tables = page.extract_tables()
                if not tables:
                    continue

                for table in tables:
                    table_txns = self._parse_table_transactions(table)
                    transactions.extend(table_txns)

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
        date_pattern = r'(\d{2}[/-]\d{2}[/-]\d{4})'
        amount_pattern = r'[\d,]+\.\d{2}'

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for date at the START of the line (skip continuation lines)
            # Bank statements typically start transaction rows with a date
            date_match = re.match(date_pattern, line)
            if not date_match:
                continue

            date_str = date_match.group(1)

            # Look for amount
            amount_matches = re.findall(amount_pattern, line)
            if not amount_matches:
                continue
            
            # A complete transaction should have at least 2 amounts (amount + balance)
            # Skip if we only have 1 amount - likely a continuation line
            if len(amount_matches) < 2:
                continue

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

            transactions.append({
                'date': self._normalize_date(date_str),
                'description': description,
                'amount': amount,
                'type': txn_type,
                'balance': balance if 'balance' in locals() else None,
            })

        return transactions

    def _parse_table_transactions(self, table: List[List[str]]) -> List[Dict]:
        """
        Parse transactions from table data

        Args:
            table: List of rows, each row is a list of cell values

        Returns:
            List of transaction dictionaries
        """
        if not table or len(table) < 2:
            return []

        # Convert to DataFrame for easier processing
        df = pd.DataFrame(table[1:], columns=table[0])
        return self._parse_dataframe_transactions(df)

    def _parse_dataframe_transactions(self, df: pd.DataFrame) -> List[Dict]:
        """
        Parse transactions from DataFrame

        This is a generic parser. Override for bank-specific logic.
        """
        transactions = []

        # Normalize column names
        df.columns = [str(col).strip().lower() for col in df.columns]

        # Try to identify columns
        date_col = self._find_column(df, ['date', 'txn date', 'transaction date', 'tran date'])
        desc_col = self._find_column(df, ['description', 'particulars', 'narration', 'details'])
        amount_col = self._find_column(df, ['amount', 'debit', 'credit', 'withdrawal', 'deposit'])
        balance_col = self._find_column(df, ['balance', 'closing balance'])

        if not date_col or not desc_col or not amount_col:
            logger.warning("Could not identify required columns in table")
            return []

        for _, row in df.iterrows():
            try:
                date = str(row[date_col]).strip()
                description = str(row[desc_col]).strip()
                amount_str = str(row[amount_col]).strip()

                # Skip empty rows
                if not date or date == 'nan' or not amount_str or amount_str == 'nan':
                    continue

                # Parse amount
                amount_str = re.sub(r'[^\d.]', '', amount_str)
                if not amount_str:
                    continue
                amount = float(amount_str)

                # Parse balance if available
                balance = None
                if balance_col:
                    balance_str = str(row[balance_col]).strip()
                    balance_str = re.sub(r'[^\d.]', '', balance_str)
                    if balance_str:
                        balance = float(balance_str)

                # Determine type
                txn_type = 'debit'  # Default
                # Check if there are separate debit/credit columns
                if 'credit' in df.columns and pd.notna(row.get('credit')):
                    txn_type = 'credit'

                transactions.append({
                    'date': self._normalize_date(date),
                    'description': description,
                    'amount': amount,
                    'type': txn_type,
                    'balance': balance,
                })

            except Exception as e:
                logger.debug(f"Failed to parse row: {e}")
                continue

        return transactions

    @staticmethod
    def _find_column(df: pd.DataFrame, possible_names: List[str]) -> Optional[str]:
        """Find column by possible names"""
        for name in possible_names:
            for col in df.columns:
                if name in str(col).lower():
                    return col
        return None

    @staticmethod
    def _normalize_date(date_str: str) -> str:
        """
        Normalize date to ISO format (YYYY-MM-DD)

        Handles formats: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD
        """
        date_str = date_str.strip()

        # Try different formats
        formats = [
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y-%m-%d',
            '%d %b %Y',
            '%d-%b-%Y',
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
