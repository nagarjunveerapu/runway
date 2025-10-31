"""
Unit tests for Investment Optimizer route models

Run with: pytest tests/test_investment_optimizer_models.py -v
"""

import pytest
from pydantic import ValidationError
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.routes.investment_optimizer import (
    SIPPattern, InvestmentSummary, PortfolioAllocation,
    InvestmentInsight, InvestmentOptimizerResponse
)


class TestSIPPattern:
    """Test suite for SIPPattern model"""
    
    def test_sip_pattern_valid_data(self):
        """Test SIPPattern with valid data"""
        sip = SIPPattern(
            sip_id="sip_zerodha_5000",
            platform="Zerodha",
            amount=5000.0,
            frequency="monthly",
            transaction_count=12,
            total_invested=60000.0,
            start_date="2024-01-01",
            last_transaction_date="2024-12-01",
            category="equity"
        )
        assert sip.sip_id == "sip_zerodha_5000"
        assert sip.platform == "Zerodha"
        assert sip.amount == 5000.0
        assert sip.frequency == "monthly"
        assert sip.category == "equity"
    
    def test_sip_pattern_optional_category(self):
        """Test SIPPattern with optional category"""
        sip = SIPPattern(
            sip_id="sip_groww_3000",
            platform="Groww",
            amount=3000.0,
            frequency="monthly",
            transaction_count=6,
            total_invested=18000.0,
            start_date="2024-06-01",
            last_transaction_date="2024-11-01"
        )
        assert sip.category is None
    
    def test_sip_pattern_all_fields_required(self):
        """Test that all required fields are validated"""
        with pytest.raises(ValidationError):
            SIPPattern(
                sip_id="sip_1",
                # Missing required fields
            )


class TestInvestmentSummary:
    """Test suite for InvestmentSummary model"""
    
    def test_investment_summary_valid_data(self):
        """Test InvestmentSummary with valid data"""
        summary = InvestmentSummary(
            total_invested=100000.0,
            total_transactions=20,
            platforms=[{"name": "Zerodha", "transaction_count": 10, "total_invested": 50000.0}],
            sip_count=2,
            total_sip_investment=60000.0
        )
        assert summary.total_invested == 100000.0
        assert summary.sip_count == 2
        assert len(summary.platforms) == 1
    
    def test_investment_summary_zero_values(self):
        """Test InvestmentSummary with zero values"""
        summary = InvestmentSummary(
            total_invested=0.0,
            total_transactions=0,
            platforms=[],
            sip_count=0,
            total_sip_investment=0.0
        )
        assert summary.total_invested == 0.0
        assert summary.total_transactions == 0


class TestPortfolioAllocation:
    """Test suite for PortfolioAllocation model"""
    
    def test_portfolio_allocation_valid_data(self):
        """Test PortfolioAllocation with valid data"""
        allocation = PortfolioAllocation(
            equity=60000.0,
            debt=20000.0,
            hybrid=10000.0,
            unknown=10000.0,
            total=100000.0
        )
        assert allocation.equity == 60000.0
        assert allocation.total == 100000.0
        assert allocation.equity + allocation.debt + allocation.hybrid + allocation.unknown == allocation.total
    
    def test_portfolio_allocation_zero_values(self):
        """Test PortfolioAllocation with zero values"""
        allocation = PortfolioAllocation(
            equity=0.0,
            debt=0.0,
            hybrid=0.0,
            unknown=0.0,
            total=0.0
        )
        assert allocation.total == 0.0


class TestInvestmentInsight:
    """Test suite for InvestmentInsight model"""
    
    def test_investment_insight_valid_data(self):
        """Test InvestmentInsight with valid data"""
        insight = InvestmentInsight(
            type="opportunity",
            title="Start SIP",
            message="Consider starting a SIP for disciplined investing",
            action="Start SIP"
        )
        assert insight.type == "opportunity"
        assert insight.title == "Start SIP"
        assert insight.action == "Start SIP"
    
    def test_investment_insight_optional_action(self):
        """Test InvestmentInsight with optional action"""
        insight = InvestmentInsight(
            type="info",
            title="Information",
            message="This is an informational message"
        )
        assert insight.action is None


class TestInvestmentOptimizerResponse:
    """Test suite for InvestmentOptimizerResponse model"""
    
    def test_investment_optimizer_response_valid_data(self):
        """Test InvestmentOptimizerResponse with valid data"""
        summary = InvestmentSummary(
            total_invested=100000.0,
            total_transactions=20,
            platforms=[],
            sip_count=2,
            total_sip_investment=60000.0
        )
        portfolio = PortfolioAllocation(
            equity=60000.0,
            debt=20000.0,
            hybrid=10000.0,
            unknown=10000.0,
            total=100000.0
        )
        insight = InvestmentInsight(
            type="info",
            title="Test",
            message="Test message"
        )
        
        response = InvestmentOptimizerResponse(
            summary=summary,
            sips=[],
            portfolio_allocation=portfolio,
            insights=[insight]
        )
        assert response.summary == summary
        assert response.portfolio_allocation == portfolio
        assert len(response.insights) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

