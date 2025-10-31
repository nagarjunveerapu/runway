"""
Parser Factory - Factory Pattern for File Type Detection and Parser Creation

Uses factory pattern to detect file type and return appropriate parser instance.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Optional
import mimetypes

from ingestion.pdf_parser import PDFParser
from ingestion.csv_parser import CSVParser
from src.csv_parser import parse_csv_file  # Legacy CSV parser
from ingestion.credit_card import ICICICreditCardParser

logger = logging.getLogger(__name__)


class ParserInterface(ABC):
    """Interface for all parsers"""
    
    @abstractmethod
    def parse(self, file_path: str) -> List[Dict]:
        """Parse file and return list of transaction dictionaries"""
        pass


class PDFParserAdapter(ParserInterface):
    """Adapter for PDFParser to implement ParserInterface"""
    
    def __init__(self, bank_name: Optional[str] = None):
        self.parser = PDFParser(bank_name=bank_name)
        self.metadata = {}  # Store metadata from parsing
    
    def parse(self, file_path: str) -> List[Dict]:
        """Parse PDF file"""
        transactions = self.parser.parse(file_path)
        # Store metadata from parser
        self.metadata = self.parser.get_metadata() if hasattr(self.parser, 'get_metadata') else {}
        return transactions
    
    def get_metadata(self) -> Dict:
        """Get metadata extracted from PDF file"""
        return self.metadata


class CSVParserAdapter(ParserInterface):
    """Adapter for CSVParser to implement ParserInterface"""
    
    def __init__(self, bank_name: Optional[str] = None):
        self.parser = CSVParser(bank_name=bank_name)
        self.metadata = {}  # Store metadata from parsing
    
    def parse(self, file_path: str) -> List[Dict]:
        """Parse CSV file"""
        # Enhanced parser now returns (transactions, metadata) tuple
        transactions, metadata = self.parser.parse(file_path)
        self.metadata = metadata  # Store metadata for later use
        return transactions
    
    def get_metadata(self) -> Dict:
        """Get metadata extracted from CSV file"""
        return self.metadata


class LegacyCSVParserAdapter(ParserInterface):
    """Adapter for legacy CSV parser to implement ParserInterface"""
    
    def parse(self, file_path: str) -> List[Dict]:
        """Parse CSV file using legacy parser"""
        return parse_csv_file(file_path)


class CreditCardParserAdapter(ParserInterface):
    """Adapter for Credit Card parsers to implement ParserInterface"""
    
    def __init__(self, credit_card_parser):
        self.parser = credit_card_parser
        self.metadata = {}
    
    def parse(self, file_path: str) -> List[Dict]:
        """Parse credit card file"""
        # Credit card parsers return (transactions, metadata) tuple
        transactions, metadata = self.parser.parse(file_path)
        self.metadata = metadata
        return transactions
    
    def get_metadata(self) -> Dict:
        """Get metadata extracted from credit card file"""
        return self.metadata


class ParserFactory:
    """
    Factory for creating parsers based on file type
    
    Uses factory pattern to detect file type and return appropriate parser instance.
    Supports two dimensions:
    1. File format: CSV, PDF
    2. Statement type: Regular account, Credit Card
    3. Bank: ICICI, HDFC, Axis, etc.
    """
    
    @staticmethod
    def is_credit_card_statement(filename: str, file_path: Optional[str] = None) -> bool:
        """
        Detect if file is a credit card statement
        
        Checks filename and optionally file content for credit card indicators
        
        Args:
            filename: Name of the file
            file_path: Optional path to read first few lines
            
        Returns:
            True if credit card statement, False otherwise
        """
        filename_lower = filename.lower()
        
        # Check filename for credit card keywords
        credit_card_keywords = [
            'credit card', 'creditcard', 'cc statement',
            'card statement', 'cardstmt'
        ]
        
        if any(keyword in filename_lower for keyword in credit_card_keywords):
            logger.info(f"Credit card statement detected by filename: {filename}")
            return True
        
        # Optionally check file content (peek at first few lines)
        if file_path:
            try:
                import csv
                # Read first 10 lines to check for credit card indicators
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    reader = csv.reader(f)
                    rows = [row for row in reader]
                
                for idx in range(min(10, len(rows))):
                    row_text = ' '.join([str(val).lower() for val in rows[idx] if val])
                    # Check for credit card metadata keywords
                    if any(kw in row_text for kw in ['accountno', 'customer name', 'reward point', 'billingamount']):
                        logger.info(f"Credit card statement detected by content: {filename}")
                        return True
            except Exception as e:
                logger.debug(f"Could not check file content: {e}")
        
        return False
    
    @staticmethod
    def detect_bank_name(filename: str, file_path: Optional[str] = None) -> Optional[str]:
        """
        Detect bank name from filename or content
        
        Args:
            filename: Name of the file
            file_path: Optional path to read first few lines
            
        Returns:
            Bank name or None
        """
        filename_lower = filename.lower()
        
        # Check filename first
        if 'icici' in filename_lower:
            return 'ICICI Bank'
        elif 'hdfc' in filename_lower:
            return 'HDFC Bank'
        elif 'axis' in filename_lower and 'bank' in filename_lower:
            return 'Axis Bank'
        elif 'sbi' in filename_lower or 'state bank' in filename_lower:
            return 'State Bank of India'
        
        # Check file content if path provided
        if file_path:
            try:
                import csv
                
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    reader = csv.reader(f)
                    rows = [row for row in reader]
                
                # Check first 20 rows and last 20 rows (where bank info often appears)
                rows_to_check = list(rows[:20]) + list(rows[-20:]) if len(rows) > 40 else rows
                
                for row in rows_to_check:
                    row_text = ' '.join([str(val).lower() for val in row if val])
                    
                    if 'icici bank' in row_text or 'icici credit card' in row_text:
                        return 'ICICI Bank'
                    elif 'hdfc bank' in row_text or 'hdfc credit card' in row_text:
                        return 'HDFC Bank'
                    elif 'axis bank' in row_text:
                        return 'Axis Bank'
                    elif 'state bank of india' in row_text:
                        return 'State Bank of India'
            except Exception as e:
                logger.debug(f"Could not check file content for bank: {e}")
        
        return None
    
    @staticmethod
    def detect_file_type(filename: str, content_type: Optional[str] = None) -> str:
        """
        Detect file type from filename and/or content type
        
        Args:
            filename: Name of the uploaded file
            content_type: MIME type if available
            
        Returns:
            File type: 'pdf', 'csv', or 'unknown'
        """
        # Check content type first (more reliable)
        if content_type:
            if 'application/pdf' in content_type.lower():
                return 'pdf'
            elif 'text/csv' in content_type.lower() or 'text/plain' in content_type.lower():
                return 'csv'
            elif 'application/vnd.ms-excel' in content_type.lower():
                return 'csv'
        
        # Fallback to file extension
        filename_lower = filename.lower()
        
        if filename_lower.endswith('.pdf'):
            return 'pdf'
        elif filename_lower.endswith('.csv'):
            return 'csv'
        elif filename_lower.endswith('.xlsx') or filename_lower.endswith('.xls'):
            # Could add Excel parser later
            return 'unknown'
        else:
            # Try MIME type detection
            mime_type, _ = mimetypes.guess_type(filename)
            if mime_type:
                if 'pdf' in mime_type:
                    return 'pdf'
                elif 'csv' in mime_type or 'text' in mime_type:
                    return 'csv'
            
            return 'unknown'
    
    @staticmethod
    def create_parser(
        file_path: str, 
        filename: str,
        content_type: Optional[str] = None,
        bank_name: Optional[str] = None,
        use_legacy_csv: bool = False
    ) -> ParserInterface:
        """
        Factory method to create appropriate parser
        
        Args:
            file_path: Path to the file
            filename: Original filename
            content_type: MIME type if available
            bank_name: Bank name for bank-specific parsing
            use_legacy_csv: Whether to use legacy CSV parser (for backward compatibility)
            
        Returns:
            ParserInterface instance
            
        Raises:
            ValueError: If file type is unknown or unsupported
        """
        logger.info("🏭 PARSER FACTORY: Detecting file type...")
        file_type = ParserFactory.detect_file_type(filename, content_type)
        logger.info(f"🏭 PARSER FACTORY: Detected file type: {file_type}")
        
        # First check if this is a credit card statement
        is_credit_card = ParserFactory.is_credit_card_statement(filename, file_path)
        
        if is_credit_card:
            logger.info(f"🏭 PARSER FACTORY: Credit card statement detected for {filename}")
            
            # Detect bank for credit card
            detected_bank = bank_name or ParserFactory.detect_bank_name(filename, file_path)
            if not detected_bank:
                # Default to ICICI if can't detect
                detected_bank = 'ICICI Bank'
                logger.warning(f"Could not detect bank, defaulting to ICICI Bank")
            
            logger.info(f"🏭 PARSER FACTORY: Creating credit card parser for {detected_bank}")
            
            # Create bank-specific credit card parser
            if 'ICICI' in detected_bank.upper():
                credit_card_parser = ICICICreditCardParser()
            else:
                # For now, default to ICICI for unknown banks
                # TODO: Add other bank parsers (HDFC, Axis, etc.)
                logger.warning(f"No specific parser for {detected_bank}, using ICICI parser")
                credit_card_parser = ICICICreditCardParser()
            
            parser = CreditCardParserAdapter(credit_card_parser)
            logger.info(f"🏭 PARSER FACTORY: ✅ Credit card parser created for {detected_bank}")
            return parser
        
        # Regular account statements
        if file_type == 'pdf':
            logger.info(f"🏭 PARSER FACTORY: Creating PDF parser for {filename}")
            parser = PDFParserAdapter(bank_name=bank_name)
            logger.info(f"🏭 PARSER FACTORY: ✅ PDF parser created")
            return parser
        
        elif file_type == 'csv':
            logger.info(f"🏭 PARSER FACTORY: Creating CSV parser for {filename}")
            if use_legacy_csv:
                logger.info(f"🏭 PARSER FACTORY: Using legacy CSV parser")
                parser = LegacyCSVParserAdapter()
            else:
                logger.info(f"🏭 PARSER FACTORY: Using new CSV parser")
                parser = CSVParserAdapter(bank_name=bank_name)
            logger.info(f"🏭 PARSER FACTORY: ✅ CSV parser created")
            return parser
        
        else:
            logger.error(f"🏭 PARSER FACTORY: ❌ Unsupported file type: {file_type}")
            raise ValueError(
                f"Unsupported file type: {file_type}. "
                f"Supported types: PDF (.pdf), CSV (.csv)"
            )
    
    @staticmethod
    def validate_file_type(filename: str, content_type: Optional[str] = None) -> bool:
        """
        Validate if file type is supported
        
        Args:
            filename: Name of the file
            content_type: MIME type if available
            
        Returns:
            True if file type is supported, False otherwise
        """
        file_type = ParserFactory.detect_file_type(filename, content_type)
        return file_type in ['pdf', 'csv']

