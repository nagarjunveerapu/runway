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


class ParserFactory:
    """
    Factory for creating parsers based on file type
    
    Uses factory pattern to detect file type and return appropriate parser instance.
    """
    
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

