"""
Unit tests for Salary Sweep route models

Run with: pytest tests/test_salary_sweep_models.py -v
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.routes.salary_sweep import (
    DetectedEMI, DetectedSalary, ConfirmRequest,
    OptimizerScenario, OptimizerResponse
)


class TestDetectedEMI:
    """Test suite for DetectedEMI model"""
    
    def test_detected_emi_valid_data(self):
        """Test DetectedEMI with valid data"""
        emi = DetectedEMI(
            source="HDFC Home Loan",
            amount=50000.0,
            count=12,
            txns=[{"transaction_id": "txn-1"}]
        )
        assert emi.source == "HDFC Home Loan"
        assert emi.amount == 50000.0
    
    def test_detected_emi_empty_txns(self):
        """Test DetectedEMI with empty transactions list"""
        emi = DetectedEMI(
            source="Test",
            amount=10000.0,
            count=3
        )
        assert len(emi.txns) == 0


class TestDetectedSalary:
    """Test suite for DetectedSalary model"""
    
    def test_detected_salary_valid_data(self):
        """Test DetectedSalary with valid data"""
        salary = DetectedSalary(
            source="Company Salary",
            amount=100000.0,
            count=12
        )
        assert salary.source == "Company Salary"
        assert salary.amount == 100000.0


class TestConfirmRequest:
    """Test suite for ConfirmRequest model"""
    
    def test_confirm_request_valid_data(self):
        """Test ConfirmRequest with valid data"""
        request = ConfirmRequest(
            salary_txn_ids=["txn-1", "txn-2"],
            emi_txn_ids=["txn-3", "txn-4", "txn-5"]
        )
        assert len(request.salary_txn_ids) == 2
        assert len(request.emi_txn_ids) == 3


class TestOptimizerScenario:
    """Test suite for OptimizerScenario model (salary_sweep.py)"""
    
    def test_optimizer_scenario_valid_data(self):
        """Test OptimizerScenario with valid data"""
        scenario = OptimizerScenario(
            name="Optimized",
            description="Optimized sweep strategy",
            emi_dates="2024-01-01",
            salary_account_balance=50000.0,
            savings_account_balance=100000.0,
            avg_days_in_savings=15.0,
            monthly_interest_salary=100.0,
            monthly_interest_savings=600.0,
            total_monthly_interest=700.0,
            total_annual_interest=8400.0
        )
        assert scenario.name == "Optimized"
        assert scenario.total_annual_interest == 8400.0
    
    def test_optimizer_scenario_optional_emi_dates(self):
        """Test OptimizerScenario with optional emi_dates"""
        scenario = OptimizerScenario(
            name="Test",
            description="Test scenario",
            emi_dates=None,
            salary_account_balance=0.0,
            savings_account_balance=0.0,
            avg_days_in_savings=0.0,
            monthly_interest_salary=0.0,
            monthly_interest_savings=0.0,
            total_monthly_interest=0.0,
            total_annual_interest=0.0
        )
        assert scenario.emi_dates is None


class TestOptimizerResponse:
    """Test suite for OptimizerResponse model"""
    
    def test_optimizer_response_valid_data(self):
        """Test OptimizerResponse with valid data"""
        salary = DetectedSalary(
            source="Company",
            amount=100000.0,
            count=12
        )
        emi = DetectedEMI(
            source="HDFC",
            amount=50000.0,
            count=12
        )
        scenario = OptimizerScenario(
            name="Current",
            description="Current scenario",
            emi_dates=None,
            salary_account_balance=0.0,
            savings_account_balance=0.0,
            avg_days_in_savings=0.0,
            monthly_interest_salary=0.0,
            monthly_interest_savings=0.0,
            total_monthly_interest=0.0,
            total_annual_interest=0.0
        )
        
        response = OptimizerResponse(
            detected_salary=salary,
            detected_emis=[emi],
            avg_salary=100000.0,
            total_monthly_emi=50000.0,
            sweepable_amount=50000.0,
            current_scenario=scenario,
            optimized_scenario=scenario,
            monthly_interest_gain=500.0,
            annual_interest_gain=6000.0,
            percentage_gain=10.0
        )
        assert response.avg_salary == 100000.0
        assert response.percentage_gain == 10.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

