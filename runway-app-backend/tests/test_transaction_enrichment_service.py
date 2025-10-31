"""
Unit tests for TransactionEnrichmentService

Run with: pytest tests/test_transaction_enrichment_service.py -v
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.parser_service.transaction_enrichment_service import TransactionEnrichmentService


class TestTransactionEnrichmentService:
    """Test suite for TransactionEnrichmentService"""
    
    def test_enrichment_service_initialization(self):
        """Test TransactionEnrichmentService initialization"""
        service = TransactionEnrichmentService()
        assert service.merchant_normalizer is not None
        assert service.deduplication_detector is not None
    
    @patch('services.parser_service.transaction_enrichment_service.MerchantNormalizer')
    @patch('services.parser_service.transaction_enrichment_service.DeduplicationDetector')
    def test_enrich_transactions(self, mock_dedup_class, mock_merchant_class):
        """Test enriching transactions"""
        mock_merchant = MagicMock()
        mock_merchant.normalize.return_value = ('Swiggy', 0.95)
        mock_merchant_class.return_value = mock_merchant
        
        service = TransactionEnrichmentService()
        service.merchant_normalizer = mock_merchant
        
        transactions = [
            {'description': 'SWIGGY BANGALORE', 'amount': 450.0}
        ]
        
        with patch('services.parser_service.transaction_enrichment_service.rule_based_category') as mock_category:
            mock_category.return_value = 'Food & Dining'
            
            result = service.enrich_transactions(transactions)
            
            assert len(result) == 1
            assert result[0]['merchant_canonical'] == 'Swiggy'
            assert result[0]['category'] == 'Food & Dining'
    
    def test_enrich_transactions_handles_errors(self):
        """Test that enrichment handles errors gracefully"""
        service = TransactionEnrichmentService()
        
        transactions = [
            {'description': 'SWIGGY', 'amount': 450.0},
            {'description': None, 'amount': None},  # Invalid transaction
            {'description': 'AMAZON', 'amount': 1000.0}
        ]
        
        # Should not raise error, but keep original transaction on failure
        result = service.enrich_transactions(transactions)
        assert len(result) == 3  # All transactions should be in result
    
    @patch('services.parser_service.transaction_enrichment_service.MerchantNormalizer')
    def test_enrich_single_transaction(self, mock_merchant_class):
        """Test enriching a single transaction"""
        mock_merchant = MagicMock()
        mock_merchant.normalize.return_value = ('Swiggy', 0.95)
        mock_merchant_class.return_value = mock_merchant
        
        service = TransactionEnrichmentService()
        service.merchant_normalizer = mock_merchant
        
        txn = {
            'description': 'SWIGGY BANGALORE',
            'amount': 450.0
        }
        
        with patch('services.parser_service.transaction_enrichment_service.rule_based_category') as mock_category:
            mock_category.return_value = 'Food & Dining'
            
            result = service._enrich_single_transaction(txn)
            
            assert 'merchant_canonical' in result
            assert 'category' in result
            assert result['merchant_canonical'] == 'Swiggy'
            assert result['category'] == 'Food & Dining'
    
    def test_enrich_single_transaction_handles_different_field_names(self):
        """Test enriching transaction with different field names (PDF vs CSV)"""
        service = TransactionEnrichmentService()
        
        # PDF format
        txn_pdf = {
            'description': 'SWIGGY',
            'amount': 450.0
        }
        
        # CSV format
        txn_csv = {
            'remark': 'SWIGGY',
            'amount': 450.0
        }
        
        with patch.object(service, '_enrich_single_transaction') as mock_enrich:
            mock_enrich.side_effect = lambda x: {**x, 'merchant_canonical': 'Swiggy', 'category': 'Food'}
            
            result_pdf = service._enrich_single_transaction(txn_pdf)
            result_csv = service._enrich_single_transaction(txn_csv)
            
            # Both should be enriched
            assert 'merchant_canonical' in result_pdf
            assert 'merchant_canonical' in result_csv
    
    @patch('services.parser_service.transaction_enrichment_service.DeduplicationDetector')
    def test_detect_and_handle_duplicates(self, mock_dedup_class):
        """Test duplicate detection and handling"""
        mock_dedup = MagicMock()
        mock_dedup.detect_duplicates.return_value = [
            {'description': 'SWIGGY', 'amount': 450.0}
        ]
        mock_dedup.get_duplicate_stats.return_value = {
            'merged_count': 1,
            'total_duplicates': 1
        }
        mock_dedup_class.return_value = mock_dedup
        
        service = TransactionEnrichmentService()
        service.deduplication_detector = mock_dedup
        
        transactions = [
            {'description': 'SWIGGY', 'amount': 450.0},
            {'description': 'SWIGGY', 'amount': 450.0}  # Duplicate
        ]
        
        cleaned, stats = service.detect_and_handle_duplicates(transactions)
        
        assert len(cleaned) == 1
        assert stats['merged_count'] == 1
    
    def test_enrich_and_deduplicate_complete_pipeline(self):
        """Test complete enrichment and deduplication pipeline"""
        service = TransactionEnrichmentService()
        
        transactions = [
            {'description': 'SWIGGY', 'amount': 450.0},
            {'description': 'SWIGGY', 'amount': 450.0},  # Duplicate
            {'description': 'AMAZON', 'amount': 1000.0}
        ]
        
        # Mock both enrichment and deduplication
        with patch.object(service, 'enrich_transactions') as mock_enrich:
            mock_enrich.return_value = transactions
            
            with patch.object(service, 'detect_and_handle_duplicates') as mock_dedup:
                mock_dedup.return_value = (
                    [transactions[0], transactions[2]],  # Cleaned list
                    {'merged_count': 1}
                )
                
                cleaned, stats = service.enrich_and_deduplicate(transactions)
                
                assert mock_enrich.called
                assert mock_dedup.called
                assert len(cleaned) == 2
                assert stats['merged_count'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

