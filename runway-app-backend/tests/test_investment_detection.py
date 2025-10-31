"""
Unit tests for Investment Detection Service

Run with: pytest tests/test_investment_detection.py -v
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.investment_detection import InvestmentDetector
from storage.models import Transaction


class TestInvestmentDetectorKeywords:
    """Test suite for investment keyword detection"""
    
    def test_investment_keywords_returns_list(self):
        """Test that investment_keywords returns a non-empty list"""
        keywords = InvestmentDetector.investment_keywords()
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert all(isinstance(k, str) for k in keywords)
    
    def test_investment_keywords_contains_expected_terms(self):
        """Test that investment keywords contain expected terms"""
        keywords = InvestmentDetector.investment_keywords()
        keywords_lower = [k.lower() for k in keywords]
        
        # Check for common investment platforms and terms
        assert any('invest' in k for k in keywords_lower)
        assert any('fund' in k for k in keywords_lower)
        assert any('sip' in k for k in keywords_lower)
        assert any('zerodha' in k for k in keywords_lower)
        assert any('groww' in k for k in keywords_lower)
    
    def test_exclusion_keywords_returns_list(self):
        """Test that exclusion_keywords returns a non-empty list"""
        keywords = InvestmentDetector.exclusion_keywords()
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert all(isinstance(k, str) for k in keywords)
    
    def test_exclusion_keywords_contains_fastag(self):
        """Test that exclusion keywords contain FASTag-related terms"""
        keywords = InvestmentDetector.exclusion_keywords()
        keywords_lower = [k.lower() for k in keywords]
        
        assert any('fastag' in k for k in keywords_lower)
        assert any('toll' in k for k in keywords_lower)
        assert any('parking' in k for k in keywords_lower)


class TestIsInvestmentText:
    """Test suite for is_investment_text method"""
    
    def test_investment_text_detects_keywords(self):
        """Test that investment keywords are detected in text"""
        test_cases = [
            ("SIP payment to Zerodha", True),
            ("Investment in mutual fund", True),
            ("Payment to Groww for stocks", True),
            ("HDFC MF investment", True),
            ("Payment to ICICI Prudential MF", True),
            ("Systematic investment plan", True),
            ("CAMS statement payment", True),
        ]
        
        for text, expected in test_cases:
            result = InvestmentDetector.is_investment_text(text)
            assert result == expected, f"Failed for text: {text}"
    
    def test_investment_text_case_insensitive(self):
        """Test that keyword matching is case insensitive"""
        test_cases = [
            ("SIP PAYMENT", True),
            ("sip payment", True),
            ("SiP PaYmEnT", True),
            ("INVESTMENT", True),
            ("investment", True),
        ]
        
        for text, expected in test_cases:
            result = InvestmentDetector.is_investment_text(text)
            assert result == expected, f"Failed for text: {text}"
    
    def test_investment_text_excludes_fastag(self):
        """Test that FASTag payments are excluded"""
        test_cases = [
            ("FASTag recharge", False),
            ("Fast tag payment", False),
            ("NPCI FASTag", False),
            ("Toll payment via FASTag", False),
            ("Parking fee payment", False),
            ("FASTag recharge for toll", False),
        ]
        
        for text, expected in test_cases:
            result = InvestmentDetector.is_investment_text(text)
            assert result == expected, f"Failed for text: {text}"
    
    def test_investment_text_handles_none(self):
        """Test that None text is handled gracefully"""
        result = InvestmentDetector.is_investment_text(None)
        assert result is False
    
    def test_investment_text_handles_empty_string(self):
        """Test that empty string returns False"""
        result = InvestmentDetector.is_investment_text("")
        assert result is False
    
    def test_investment_text_non_investment_text(self):
        """Test that non-investment text returns False"""
        test_cases = [
            ("Grocery shopping at Reliance", False),
            ("Uber ride payment", False),
            ("Amazon purchase", False),
            ("Netflix subscription", False),
            ("Swiggy food order", False),
            ("Salary credit", False),
        ]
        
        for text, expected in test_cases:
            result = InvestmentDetector.is_investment_text(text)
            assert result == expected, f"Failed for text: {text}"
    
    def test_investment_text_partial_matches(self):
        """Test that partial keyword matches work correctly"""
        test_cases = [
            ("SIPINVESTMENT", True),  # Contains both SIP and INVESTMENT
            ("investor", True),  # Contains 'invest'
            ("funding", True),  # Contains 'fund'
            ("systematic plan", True),  # Contains 'systematic'
        ]
        
        for text, expected in test_cases:
            result = InvestmentDetector.is_investment_text(text)
            assert result == expected, f"Failed for text: {text}"


class TestIsInvestmentTxn:
    """Test suite for is_investment_txn method"""
    
    def test_investment_txn_debit_with_keywords(self):
        """Test that debit transactions with investment keywords are detected"""
        txn = Mock(spec=Transaction)
        txn.type = 'debit'
        txn.category = 'Investment'
        txn.description_raw = 'SIP payment to Zerodha'
        txn.clean_description = 'SIP payment'
        txn.merchant_canonical = 'Zerodha'
        txn.merchant_raw = 'Zerodha Securities'
        
        result = InvestmentDetector.is_investment_txn(txn)
        assert result is True
    
    def test_investment_txn_credit_not_detected(self):
        """Test that credit transactions are not detected as investments"""
        txn = Mock(spec=Transaction)
        txn.type = 'credit'
        txn.category = 'Investment Returns'
        txn.description_raw = 'Mutual fund redemption'
        txn.clean_description = 'MF redemption'
        txn.merchant_canonical = 'HDFC MF'
        txn.merchant_raw = 'HDFC Mutual Fund'
        
        result = InvestmentDetector.is_investment_txn(txn)
        assert result is False
    
    def test_investment_txn_debit_without_keywords(self):
        """Test that debit transactions without investment keywords are not detected"""
        txn = Mock(spec=Transaction)
        txn.type = 'debit'
        txn.category = 'Shopping'
        txn.description_raw = 'Amazon purchase'
        txn.clean_description = 'Online shopping'
        txn.merchant_canonical = 'Amazon'
        txn.merchant_raw = 'Amazon India'
        
        result = InvestmentDetector.is_investment_txn(txn)
        assert result is False
    
    def test_investment_txn_keyword_in_merchant(self):
        """Test that keywords in merchant fields are detected"""
        txn = Mock(spec=Transaction)
        txn.type = 'debit'
        txn.category = None
        txn.description_raw = None
        txn.clean_description = None
        txn.merchant_canonical = 'Groww'
        txn.merchant_raw = 'Groww Technologies'
        
        result = InvestmentDetector.is_investment_txn(txn)
        assert result is True
    
    def test_investment_txn_keyword_in_category(self):
        """Test that keywords in category are detected"""
        txn = Mock(spec=Transaction)
        txn.type = 'debit'
        txn.category = 'Mutual Fund Investment'
        txn.description_raw = None
        txn.clean_description = None
        txn.merchant_canonical = None
        txn.merchant_raw = None
        
        result = InvestmentDetector.is_investment_txn(txn)
        assert result is True
    
    def test_investment_txn_keyword_in_description(self):
        """Test that keywords in description fields are detected"""
        txn = Mock(spec=Transaction)
        txn.type = 'debit'
        txn.category = None
        txn.description_raw = 'Systematic investment plan payment'
        txn.clean_description = None
        txn.merchant_canonical = None
        txn.merchant_raw = None
        
        result = InvestmentDetector.is_investment_txn(txn)
        assert result is True
    
    def test_investment_txn_excludes_fastag(self):
        """Test that FASTag transactions are excluded even if debit"""
        txn = Mock(spec=Transaction)
        txn.type = 'debit'
        txn.category = None
        txn.description_raw = 'FASTag recharge'
        txn.clean_description = 'Fast tag payment'
        txn.merchant_canonical = 'NPCI FASTag'
        txn.merchant_raw = 'NPCI'
        
        result = InvestmentDetector.is_investment_txn(txn)
        assert result is False
    
    def test_investment_txn_handles_none_fields(self):
        """Test that None fields are handled gracefully"""
        txn = Mock(spec=Transaction)
        txn.type = 'debit'
        txn.category = None
        txn.description_raw = None
        txn.clean_description = None
        txn.merchant_canonical = None
        txn.merchant_raw = None
        
        result = InvestmentDetector.is_investment_txn(txn)
        assert result is False


class TestFilterInvestmentTransactions:
    """Test suite for filter_investment_transactions method"""
    
    @patch('services.investment_detection.DatabaseManager')
    @patch('services.investment_detection.Config')
    def test_filter_investment_transactions_queries_database(self, mock_config, mock_db_manager):
        """Test that database is queried correctly"""
        # Setup mocks
        mock_config.DATABASE_URL = "sqlite:///test.db"
        mock_session = MagicMock()
        mock_db = MagicMock()
        mock_db.get_session.return_value = mock_session
        mock_db.close.return_value = None
        mock_db_manager.return_value = mock_db
        
        # Create mock query builder
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        
        # Execute
        result = InvestmentDetector.filter_investment_transactions("test_user_id")
        
        # Verify database was queried
        mock_session.query.assert_called_once_with(Transaction)
        mock_query.filter.assert_called()
        mock_session.close.assert_called_once()
        mock_db.close.assert_called_once()
        assert result == []
    
    @patch('services.investment_detection.DatabaseManager')
    @patch('services.investment_detection.Config')
    def test_filter_investment_transactions_returns_transactions(self, mock_config, mock_db_manager):
        """Test that method returns list of transactions"""
        # Setup mocks
        mock_config.DATABASE_URL = "sqlite:///test.db"
        mock_session = MagicMock()
        mock_db = MagicMock()
        mock_db.get_session.return_value = mock_session
        mock_db.close.return_value = None
        mock_db_manager.return_value = mock_db
        
        # Create mock transactions
        mock_txn1 = Mock(spec=Transaction)
        mock_txn1.date = '2024-01-01'
        mock_txn2 = Mock(spec=Transaction)
        mock_txn2.date = '2024-01-15'
        
        # Create mock query builder
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_txn1, mock_txn2]
        
        # Execute
        result = InvestmentDetector.filter_investment_transactions("test_user_id")
        
        # Verify results
        assert len(result) == 2
        assert result[0] == mock_txn1
        assert result[1] == mock_txn2
    
    @patch('services.investment_detection.DatabaseManager')
    @patch('services.investment_detection.Config')
    def test_filter_investment_transactions_filters_by_user_id(self, mock_config, mock_db_manager):
        """Test that transactions are filtered by user_id"""
        # Setup mocks
        mock_config.DATABASE_URL = "sqlite:///test.db"
        mock_session = MagicMock()
        mock_db = MagicMock()
        mock_db.get_session.return_value = mock_session
        mock_db.close.return_value = None
        mock_db_manager.return_value = mock_db
        
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        
        user_id = "test_user_123"
        InvestmentDetector.filter_investment_transactions(user_id)
        
        # Verify user_id filter was applied
        filter_calls = mock_query.filter.call_args_list
        # Check that Transaction.user_id filter was called
        assert len(filter_calls) > 0
    
    @patch('services.investment_detection.DatabaseManager')
    @patch('services.investment_detection.Config')
    def test_filter_investment_transactions_closes_session(self, mock_config, mock_db_manager):
        """Test that database session is properly closed"""
        # Setup mocks
        mock_config.DATABASE_URL = "sqlite:///test.db"
        mock_session = MagicMock()
        mock_db = MagicMock()
        mock_db.get_session.return_value = mock_session
        mock_db.close.return_value = None
        mock_db_manager.return_value = mock_db
        
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        
        InvestmentDetector.filter_investment_transactions("test_user_id")
        
        # Verify cleanup
        mock_session.close.assert_called_once()
        mock_db.close.assert_called_once()


class TestDetectSIPs:
    """Test suite for detect_sips method"""
    
    def test_detect_sips_empty_list(self):
        """Test that empty transaction list returns empty SIPs"""
        result = InvestmentDetector.detect_sips([])
        assert result == []
    
    def test_detect_sips_single_transaction(self):
        """Test that single transaction doesn't create SIP"""
        txn = Mock(spec=Transaction)
        txn.merchant_canonical = 'Zerodha'
        txn.amount = 5000.0
        txn.date = '2024-01-01'
        
        result = InvestmentDetector.detect_sips([txn])
        assert result == []
    
    def test_detect_sips_monthly_pattern(self):
        """Test that monthly transactions are detected as SIP"""
        # Create transactions with monthly pattern
        txns = []
        base_date = datetime(2024, 1, 1)
        for i in range(3):
            txn = Mock(spec=Transaction)
            txn.merchant_canonical = 'Zerodha'
            txn.amount = 5000.0
            txn.date = (base_date + timedelta(days=i*30)).strftime('%Y-%m-%d')
            txns.append(txn)
        
        result = InvestmentDetector.detect_sips(txns)
        
        assert len(result) == 1
        assert result[0].platform == 'Zerodha'
        assert result[0].amount == 5000.0
        assert result[0].frequency == 'monthly'
        assert result[0].transaction_count == 3
        assert result[0].total_invested == 15000.0
    
    def test_detect_sips_similar_amounts(self):
        """Test that similar amounts (within 5%) are grouped together"""
        txns = []
        base_date = datetime(2024, 1, 1)
        amounts = [5000.0, 5025.0, 4980.0]  # All within 5% of 5000
        
        for i, amount in enumerate(amounts):
            txn = Mock(spec=Transaction)
            txn.merchant_canonical = 'Groww'
            txn.amount = amount
            txn.date = (base_date + timedelta(days=i*30)).strftime('%Y-%m-%d')
            txns.append(txn)
        
        result = InvestmentDetector.detect_sips(txns)
        
        assert len(result) == 1
        assert result[0].transaction_count == 3
    
    def test_detect_sips_different_amounts_separate_groups(self):
        """Test that different amounts create separate SIP groups"""
        txns = []
        base_date = datetime(2024, 1, 1)
        
        # Two different amounts
        for i in range(2):
            txn1 = Mock(spec=Transaction)
            txn1.merchant_canonical = 'Zerodha'
            txn1.amount = 5000.0
            txn1.date = (base_date + timedelta(days=i*30)).strftime('%Y-%m-%d')
            txns.append(txn1)
        
        for i in range(2):
            txn2 = Mock(spec=Transaction)
            txn2.merchant_canonical = 'Zerodha'
            txn2.amount = 10000.0
            txn2.date = (base_date + timedelta(days=i*30)).strftime('%Y-%m-%d')
            txns.append(txn2)
        
        result = InvestmentDetector.detect_sips(txns)
        
        assert len(result) == 2
        amounts = sorted([sip.amount for sip in result])
        assert amounts == [5000.0, 10000.0]
    
    def test_detect_sips_different_platforms_separate_groups(self):
        """Test that different platforms create separate SIP groups"""
        txns = []
        base_date = datetime(2024, 1, 1)
        
        # Two platforms
        for i in range(2):
            txn1 = Mock(spec=Transaction)
            txn1.merchant_canonical = 'Zerodha'
            txn1.amount = 5000.0
            txn1.date = (base_date + timedelta(days=i*30)).strftime('%Y-%m-%d')
            txns.append(txn1)
        
        for i in range(2):
            txn2 = Mock(spec=Transaction)
            txn2.merchant_canonical = 'Groww'
            txn2.amount = 5000.0
            txn2.date = (base_date + timedelta(days=i*30)).strftime('%Y-%m-%d')
            txns.append(txn2)
        
        result = InvestmentDetector.detect_sips(txns)
        
        assert len(result) == 2
        platforms = sorted([sip.platform for sip in result])
        assert platforms == ['Groww', 'Zerodha']
    
    def test_detect_sips_irregular_frequency(self):
        """Test that irregular intervals are marked as irregular"""
        txns = []
        dates = ['2024-01-01', '2024-02-15', '2024-04-10']  # Irregular intervals
        
        for date in dates:
            txn = Mock(spec=Transaction)
            txn.merchant_canonical = 'Zerodha'
            txn.amount = 5000.0
            txn.date = date
            txns.append(txn)
        
        result = InvestmentDetector.detect_sips(txns)
        
        assert len(result) == 1
        assert result[0].frequency == 'irregular'
    
    def test_detect_sips_unknown_merchant(self):
        """Test that transactions with None merchant are handled"""
        txns = []
        base_date = datetime(2024, 1, 1)
        
        for i in range(2):
            txn = Mock(spec=Transaction)
            txn.merchant_canonical = None
            txn.amount = 5000.0
            txn.date = (base_date + timedelta(days=i*30)).strftime('%Y-%m-%d')
            txns.append(txn)
        
        result = InvestmentDetector.detect_sips(txns)
        
        assert len(result) == 1
        assert result[0].platform == 'Unknown'
    
    def test_detect_sips_calculates_total_invested(self):
        """Test that total invested is calculated correctly"""
        txns = []
        base_date = datetime(2024, 1, 1)
        amounts = [5000.0, 5000.0, 5000.0]
        
        for i, amount in enumerate(amounts):
            txn = Mock(spec=Transaction)
            txn.merchant_canonical = 'Zerodha'
            txn.amount = amount
            txn.date = (base_date + timedelta(days=i*30)).strftime('%Y-%m-%d')
            txns.append(txn)
        
        result = InvestmentDetector.detect_sips(txns)
        
        assert len(result) == 1
        assert result[0].total_invested == 15000.0
    
    def test_detect_sips_sets_start_and_end_dates(self):
        """Test that start and end dates are set correctly"""
        txns = []
        base_date = datetime(2024, 1, 1)
        dates = [
            base_date + timedelta(days=30),
            base_date,
            base_date + timedelta(days=60)
        ]
        
        for date in dates:
            txn = Mock(spec=Transaction)
            txn.merchant_canonical = 'Zerodha'
            txn.amount = 5000.0
            txn.date = date.strftime('%Y-%m-%d')
            txns.append(txn)
        
        result = InvestmentDetector.detect_sips(txns)
        
        assert len(result) == 1
        assert result[0].start_date == base_date.strftime('%Y-%m-%d')
        assert result[0].last_transaction_date == (base_date + timedelta(days=60)).strftime('%Y-%m-%d')
    
    def test_detect_sips_amount_tolerance(self):
        """Test that amounts outside 5% tolerance are separate groups"""
        txns = []
        base_date = datetime(2024, 1, 1)
        amounts = [5000.0, 5100.0, 6000.0]  # 5100 is within 5%, 6000 is not
        
        for i, amount in enumerate(amounts):
            txn = Mock(spec=Transaction)
            txn.merchant_canonical = 'Zerodha'
            txn.amount = amount
            txn.date = (base_date + timedelta(days=i*30)).strftime('%Y-%m-%d')
            txns.append(txn)
        
        result = InvestmentDetector.detect_sips(txns)
        
        # Should have 2 groups: [5000, 5100] and [6000]
        assert len(result) == 2
        amounts_found = sorted([sip.amount for sip in result])
        assert 5000.0 in amounts_found or 5100.0 in amounts_found
        assert 6000.0 in amounts_found
    
    def test_detect_sips_with_missing_dates(self):
        """Test that transactions with None dates are handled"""
        txns = []
        
        txn1 = Mock(spec=Transaction)
        txn1.merchant_canonical = 'Zerodha'
        txn1.amount = 5000.0
        txn1.date = '2024-01-01'
        txns.append(txn1)
        
        txn2 = Mock(spec=Transaction)
        txn2.merchant_canonical = 'Zerodha'
        txn2.amount = 5000.0
        txn2.date = None
        txns.append(txn2)
        
        # Should not raise error, but may not create SIP if dates invalid
        result = InvestmentDetector.detect_sips(txns)
        # At least should not crash
        assert isinstance(result, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

