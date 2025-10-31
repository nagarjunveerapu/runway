"""
Unit tests for ParserFactory

Run with: pytest tests/test_parser_factory.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.parser_service.parser_factory import (
    ParserFactory, ParserInterface, PDFParserAdapter,
    CSVParserAdapter, LegacyCSVParserAdapter
)


class TestParserFactory:
    """Test suite for ParserFactory"""
    
    def test_detect_file_type_pdf_by_extension(self):
        """Test file type detection for PDF by extension"""
        file_type = ParserFactory.detect_file_type("statement.pdf")
        assert file_type == 'pdf'
    
    def test_detect_file_type_csv_by_extension(self):
        """Test file type detection for CSV by extension"""
        file_type = ParserFactory.detect_file_type("statement.csv")
        assert file_type == 'csv'
    
    def test_detect_file_type_pdf_by_content_type(self):
        """Test file type detection for PDF by content type"""
        file_type = ParserFactory.detect_file_type("statement.pdf", "application/pdf")
        assert file_type == 'pdf'
    
    def test_detect_file_type_csv_by_content_type(self):
        """Test file type detection for CSV by content type"""
        file_type = ParserFactory.detect_file_type("statement.csv", "text/csv")
        assert file_type == 'csv'
    
    def test_detect_file_type_unknown(self):
        """Test file type detection for unknown file types"""
        # Use a clearly unsupported file type
        file_type = ParserFactory.detect_file_type("statement.exe")
        assert file_type == 'unknown'
    
    def test_detect_file_type_case_insensitive(self):
        """Test file type detection is case insensitive"""
        assert ParserFactory.detect_file_type("statement.PDF") == 'pdf'
        assert ParserFactory.detect_file_type("statement.CSV") == 'csv'
    
    def test_validate_file_type_pdf(self):
        """Test file type validation for PDF"""
        assert ParserFactory.validate_file_type("statement.pdf") is True
        assert ParserFactory.validate_file_type("statement.pdf", "application/pdf") is True
    
    def test_validate_file_type_csv(self):
        """Test file type validation for CSV"""
        assert ParserFactory.validate_file_type("statement.csv") is True
        assert ParserFactory.validate_file_type("statement.csv", "text/csv") is True
    
    def test_validate_file_type_unsupported(self):
        """Test file type validation for unsupported types"""
        assert ParserFactory.validate_file_type("statement.exe") is False
        assert ParserFactory.validate_file_type("statement.xlsx") is False
    
    @patch('services.parser_service.parser_factory.PDFParser')
    def test_create_parser_pdf(self, mock_pdf_parser_class):
        """Test creating PDF parser via factory"""
        parser = ParserFactory.create_parser(
            file_path="test.pdf",
            filename="test.pdf",
            content_type="application/pdf"
        )
        assert isinstance(parser, PDFParserAdapter)
        mock_pdf_parser_class.assert_called_once()
    
    @patch('services.parser_service.parser_factory.CSVParser')
    def test_create_parser_csv(self, mock_csv_parser_class):
        """Test creating CSV parser via factory"""
        parser = ParserFactory.create_parser(
            file_path="test.csv",
            filename="test.csv",
            content_type="text/csv"
        )
        assert isinstance(parser, CSVParserAdapter)
        mock_csv_parser_class.assert_called_once()
    
    @patch('services.parser_service.parser_factory.parse_csv_file')
    def test_create_parser_csv_legacy(self, mock_legacy_parser):
        """Test creating legacy CSV parser via factory"""
        parser = ParserFactory.create_parser(
            file_path="test.csv",
            filename="test.csv",
            use_legacy_csv=True
        )
        assert isinstance(parser, LegacyCSVParserAdapter)
    
    def test_create_parser_unsupported_file_type(self):
        """Test factory raises ValueError for unsupported file types"""
        with pytest.raises(ValueError, match="Unsupported file type"):
            ParserFactory.create_parser(
                file_path="test.exe",
                filename="test.exe"
            )
    
    def test_create_parser_with_bank_name(self):
        """Test creating parser with bank name"""
        with patch('services.parser_service.parser_factory.PDFParser') as mock_pdf:
            parser = ParserFactory.create_parser(
                file_path="test.pdf",
                filename="test.pdf",
                bank_name="HDFC Bank"
            )
            mock_pdf.assert_called_once_with(bank_name="HDFC Bank")
            assert isinstance(parser, PDFParserAdapter)


class TestParserAdapters:
    """Test suite for parser adapters"""
    
    @patch('services.parser_service.parser_factory.PDFParser')
    def test_pdf_parser_adapter(self, mock_pdf_parser_class):
        """Test PDFParserAdapter wraps PDFParser correctly"""
        mock_parser = MagicMock()
        mock_parser.parse.return_value = [{'date': '2024-01-01', 'amount': 100.0}]
        mock_pdf_parser_class.return_value = mock_parser
        
        adapter = PDFParserAdapter(bank_name="HDFC Bank")
        result = adapter.parse("test.pdf")
        
        assert result == [{'date': '2024-01-01', 'amount': 100.0}]
        mock_parser.parse.assert_called_once_with("test.pdf")
    
    @patch('services.parser_service.parser_factory.CSVParser')
    def test_csv_parser_adapter(self, mock_csv_parser_class):
        """Test CSVParserAdapter wraps CSVParser correctly"""
        mock_parser = MagicMock()
        mock_parser.parse.return_value = [{'date': '2024-01-01', 'amount': 100.0}]
        mock_csv_parser_class.return_value = mock_parser
        
        adapter = CSVParserAdapter(bank_name="HDFC Bank")
        result = adapter.parse("test.csv")
        
        assert result == [{'date': '2024-01-01', 'amount': 100.0}]
        mock_parser.parse.assert_called_once_with("test.csv")
    
    @patch('services.parser_service.parser_factory.parse_csv_file')
    def test_legacy_csv_parser_adapter(self, mock_legacy_parser):
        """Test LegacyCSVParserAdapter uses legacy parser"""
        mock_legacy_parser.return_value = [{'date': '2024-01-01', 'amount': 100.0}]
        
        adapter = LegacyCSVParserAdapter()
        result = adapter.parse("test.csv")
        
        assert result == [{'date': '2024-01-01', 'amount': 100.0}]
        mock_legacy_parser.assert_called_once_with("test.csv")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

