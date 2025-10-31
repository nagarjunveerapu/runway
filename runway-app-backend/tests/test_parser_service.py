"""
Unit tests for ParserService (Main Service Layer)

Run with: pytest tests/test_parser_service.py -v
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.parser_service.parser_service import ParserService
from services.parser_service.parser_factory import ParserFactory, PDFParserAdapter
from services.parser_service.transaction_repository import TransactionRepository
from services.parser_service.transaction_enrichment_service import TransactionEnrichmentService
from storage.database import DatabaseManager
from fastapi import UploadFile


class TestParserService:
    """Test suite for ParserService"""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Mock DatabaseManager"""
        db_manager = MagicMock(spec=DatabaseManager)
        db_manager.get_session.return_value = MagicMock()
        return db_manager
    
    @pytest.fixture
    def parser_service(self, mock_db_manager):
        """Create ParserService instance"""
        return ParserService(db_manager=mock_db_manager)
    
    def test_parser_service_initialization(self, mock_db_manager):
        """Test ParserService initialization"""
        service = ParserService(db_manager=mock_db_manager)
        assert service.db_manager == mock_db_manager
        assert isinstance(service.transaction_repository, TransactionRepository)
        assert isinstance(service.enrichment_service, TransactionEnrichmentService)
    
    @patch('services.parser_service.parser_service.ParserFactory')
    @patch('services.parser_service.parser_service.TransactionRepository')
    @patch('services.parser_service.parser_service.TransactionEnrichmentService')
    def test_process_uploaded_file_success(self, mock_enrichment, mock_repo, mock_factory, parser_service, mock_db_manager):
        """Test processing uploaded file successfully"""
        # Mock file
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.file = MagicMock()
        
        # Mock parser factory
        mock_parser = MagicMock()
        mock_parser.parse.return_value = [
            {'date': '2024-01-01', 'amount': 5000.0, 'type': 'debit', 'description': 'SWIGGY'}
        ]
        mock_factory.validate_file_type.return_value = True
        mock_factory.create_parser.return_value = mock_parser
        
        # Mock enrichment service
        mock_enrichment_service = MagicMock()
        mock_enrichment_service.enrich_and_deduplicate.return_value = (
            [{'date': '2024-01-01', 'amount': 5000.0, 'type': 'debit', 'description': 'SWIGGY', 
              'merchant_canonical': 'Swiggy', 'category': 'Food', 'source': 'pdf_upload'}],
            {'merged_count': 0}
        )
        parser_service.enrichment_service = mock_enrichment_service
        
        # Mock repository
        mock_repository = MagicMock()
        mock_repository.insert_transactions_batch.return_value = 1
        parser_service.transaction_repository = mock_repository
        
        # Mock tempfile operations
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            with patch('shutil.copyfileobj') as mock_copy:
                with patch('pathlib.Path.exists', return_value=True):
                    with patch('pathlib.Path.unlink'):
                        mock_temp.return_value.__enter__.return_value.name = "/tmp/test.pdf"
                        
                        result = parser_service.process_uploaded_file(
                            file=mock_file,
                            user_id="test-user-123"
                        )
                        
                        assert result['status'] == 'success'
                        assert result['transactions_found'] == 1
                        assert result['transactions_imported'] == 1
    
    def test_process_uploaded_file_invalid_file_type(self, parser_service):
        """Test processing file with invalid file type"""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.txt"
        mock_file.content_type = "text/plain"
        
        with patch.object(ParserFactory, 'validate_file_type', return_value=False):
            with pytest.raises(ValueError, match="Unsupported file type"):
                parser_service.process_uploaded_file(
                    file=mock_file,
                    user_id="test-user-123"
                )
    
    @patch('services.parser_service.parser_service.ParserFactory')
    def test_process_uploaded_file_no_transactions(self, mock_factory, parser_service):
        """Test processing file with no transactions"""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.file = MagicMock()
        
        mock_factory.validate_file_type.return_value = True
        
        mock_parser = MagicMock()
        mock_parser.parse.return_value = []
        mock_factory.create_parser.return_value = mock_parser
        
        with patch('tempfile.NamedTemporaryFile'):
            with patch('shutil.copyfileobj'):
                with pytest.raises(ValueError, match="No transactions found"):
                    parser_service.process_uploaded_file(
                        file=mock_file,
                        user_id="test-user-123"
                    )
    
    def test_parse_file_only(self, parser_service):
        """Test parsing file without enrichment or database operations"""
        mock_parser = MagicMock()
        mock_parser.parse.return_value = [
            {'date': '2024-01-01', 'amount': 5000.0, 'type': 'debit'}
        ]
        
        with patch.object(ParserFactory, 'create_parser', return_value=mock_parser):
            result = parser_service.parse_file_only(
                file_path="/tmp/test.pdf",
                filename="test.pdf",
                content_type="application/pdf"
            )
            
            assert len(result) == 1
            assert result[0]['amount'] == 5000.0
    
    @patch('services.parser_service.parser_service.ParserFactory')
    @patch('services.parser_service.parser_service.TransactionRepository')
    @patch('services.parser_service.parser_service.TransactionEnrichmentService')
    def test_process_uploaded_file_csv_with_legacy(self, mock_enrichment, mock_repo, mock_factory, parser_service):
        """Test processing CSV file with legacy parser"""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.csv"
        mock_file.content_type = "text/csv"
        mock_file.file = MagicMock()
        
        mock_factory.validate_file_type.return_value = True
        
        mock_parser = MagicMock()
        mock_parser.parse.return_value = [
            {'date': '2024-01-01', 'amount': 5000.0, 'transaction_type': 'debit', 'remark': 'SWIGGY'}
        ]
        mock_factory.create_parser.return_value = mock_parser
        
        mock_enrichment_service = MagicMock()
        mock_enrichment_service.enrich_and_deduplicate.return_value = (
            [{'date': '2024-01-01', 'amount': 5000.0, 'type': 'debit', 'remark': 'SWIGGY',
              'merchant_canonical': 'Swiggy', 'category': 'Food', 'source': 'csv_upload'}],
            {'merged_count': 0}
        )
        parser_service.enrichment_service = mock_enrichment_service
        
        mock_repository = MagicMock()
        mock_repository.insert_transactions_batch.return_value = 1
        parser_service.transaction_repository = mock_repository
        
        with patch('tempfile.NamedTemporaryFile'):
            with patch('shutil.copyfileobj'):
                with patch('pathlib.Path.exists', return_value=True):
                    with patch('pathlib.Path.unlink'):
                        result = parser_service.process_uploaded_file(
                            file=mock_file,
                            user_id="test-user-123",
                            use_legacy_csv=True
                        )
                        
                        assert result['status'] == 'success'
                        # Verify legacy parser was requested
                        mock_factory.create_parser.assert_called()
                        call_kwargs = mock_factory.create_parser.call_args[1]
                        assert call_kwargs['use_legacy_csv'] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

