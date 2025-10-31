"""
Unit tests for Dashboard route models

Run with: pytest tests/test_dashboard_models.py -v
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.routes.dashboard import (
    DashboardInsight, MonthlyMetrics, AssetSummary,
    LiabilitySummary, DashboardSummary
)


class TestDashboardInsight:
    """Test suite for DashboardInsight model"""
    
    def test_dashboard_insight_valid_data(self):
        """Test DashboardInsight with valid data"""
        insight = DashboardInsight(
            type="success",
            title="Great Savings!",
            description="You're saving 30% of income",
            icon="🏆",
            action="view-details",
            value=30.0
        )
        assert insight.type == "success"
        assert insight.icon == "🏆"
        assert insight.value == 30.0
    
    def test_dashboard_insight_optional_fields(self):
        """Test DashboardInsight with optional fields"""
        insight = DashboardInsight(
            type="info",
            title="Info",
            description="Information message",
            icon="ℹ️"
        )
        assert insight.action is None
        assert insight.value is None


class TestMonthlyMetrics:
    """Test suite for MonthlyMetrics model"""
    
    def test_monthly_metrics_valid_data(self):
        """Test MonthlyMetrics with valid data"""
        metrics = MonthlyMetrics(
            month="2024-01",
            income=100000.0,
            expenses=70000.0,
            net_savings=30000.0,
            savings_rate=30.0,
            emi_payments=20000.0,
            transaction_count=50
        )
        assert metrics.income == 100000.0
        assert metrics.savings_rate == 30.0
        assert metrics.net_savings == metrics.income - metrics.expenses
    
    def test_monthly_metrics_zero_values(self):
        """Test MonthlyMetrics with zero values"""
        metrics = MonthlyMetrics(
            month="2024-01",
            income=0.0,
            expenses=0.0,
            net_savings=0.0,
            savings_rate=0.0,
            emi_payments=0.0,
            transaction_count=0
        )
        assert metrics.net_savings == 0.0


class TestAssetSummary:
    """Test suite for AssetSummary model"""
    
    def test_asset_summary_valid_data(self):
        """Test AssetSummary with valid data"""
        summary = AssetSummary(
            total_value=5000000.0,
            count=3,
            top_assets=[
                {"name": "Home", "type": "property", "value": 4000000.0},
                {"name": "Car", "type": "vehicle", "value": 800000.0}
            ]
        )
        assert summary.total_value == 5000000.0
        assert summary.count == 3
        assert len(summary.top_assets) == 2


class TestLiabilitySummary:
    """Test suite for LiabilitySummary model"""
    
    def test_liability_summary_valid_data(self):
        """Test LiabilitySummary with valid data"""
        summary = LiabilitySummary(
            total_outstanding=2000000.0,
            total_monthly_payments=50000.0,
            count=2,
            top_liabilities=[
                {"name": "Home Loan", "type": "loan", "outstanding_balance": 1500000.0},
                {"name": "Car Loan", "type": "loan", "outstanding_balance": 500000.0}
            ]
        )
        assert summary.total_outstanding == 2000000.0
        assert summary.total_monthly_payments == 50000.0
        assert summary.count == 2


class TestDashboardSummary:
    """Test suite for DashboardSummary model"""
    
    def test_dashboard_summary_valid_data(self):
        """Test DashboardSummary with valid data"""
        current_month = MonthlyMetrics(
            month="2024-01",
            income=100000.0,
            expenses=70000.0,
            net_savings=30000.0,
            savings_rate=30.0,
            emi_payments=20000.0,
            transaction_count=50
        )
        assets = AssetSummary(
            total_value=5000000.0,
            count=3,
            top_assets=[]
        )
        liabilities = LiabilitySummary(
            total_outstanding=2000000.0,
            total_monthly_payments=50000.0,
            count=2,
            top_liabilities=[]
        )
        insight = DashboardInsight(
            type="success",
            title="Test",
            description="Test",
            icon="✓"
        )
        
        summary = DashboardSummary(
            health_score=85,
            health_message="Excellent! 🎉",
            current_month=current_month,
            previous_month=None,
            assets=assets,
            liabilities=liabilities,
            true_net_worth=3000000.0,
            liquid_assets=500000.0,
            runway_months=10.0,
            debt_to_asset_ratio=40.0,
            insights=[insight],
            net_worth=5000000.0,
            total_transactions=100
        )
        assert summary.health_score == 85
        assert summary.true_net_worth == 3000000.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

