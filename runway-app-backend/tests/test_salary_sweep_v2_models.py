"""
Unit tests for Salary Sweep V2 route models

Run with: pytest tests/test_salary_sweep_v2_models.py -v
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.routes.salary_sweep_v2 import (
    EMIPatternResponse, SalaryResponse, DetectPatternsResponse,
    ConfirmConfigRequest, UpdateEMIRequest, OptimizerScenario,
    CalculateResponse, ConfigResponse, RecurringPaymentsByCategoryResponse
)


class TestEMIPatternResponse:
    """Test suite for EMIPatternResponse model"""
    
    def test_emi_pattern_response_valid_data(self):
        """Test EMIPatternResponse with valid data"""
        pattern = EMIPatternResponse(
            pattern_id="pattern-123",
            merchant_source="HDFC Home Loan",
            emi_amount=50000.0,
            occurrence_count=12,
            category="Loan",
            subcategory="Home Loan",
            is_confirmed=True,
            user_label="My Home Loan",
            suggested_action="keep"
        )
        assert pattern.pattern_id == "pattern-123"
        assert pattern.is_confirmed is True
        assert pattern.category == "Loan"
    
    def test_emi_pattern_response_optional_fields(self):
        """Test EMIPatternResponse with optional fields"""
        pattern = EMIPatternResponse(
            pattern_id="pattern-456",
            merchant_source="Unknown",
            emi_amount=10000.0,
            occurrence_count=3,
            is_confirmed=False
        )
        assert pattern.category is None
        assert pattern.user_label is None


class TestSalaryResponse:
    """Test suite for SalaryResponse model"""
    
    def test_salary_response_valid_data(self):
        """Test SalaryResponse with valid data"""
        salary = SalaryResponse(
            source="Company Salary",
            amount=100000.0,
            count=12,
            is_confirmed=True
        )
        assert salary.source == "Company Salary"
        assert salary.is_confirmed is True


class TestDetectPatternsResponse:
    """Test suite for DetectPatternsResponse model"""
    
    def test_detect_patterns_response_valid_data(self):
        """Test DetectPatternsResponse with valid data"""
        pattern = EMIPatternResponse(
            pattern_id="pattern-1",
            merchant_source="HDFC",
            emi_amount=50000.0,
            occurrence_count=12,
            is_confirmed=False
        )
        salary = SalaryResponse(
            source="Company",
            amount=100000.0,
            count=12,
            is_confirmed=False
        )
        
        response = DetectPatternsResponse(
            has_existing_config=False,
            salary=salary,
            emis=[pattern],
            message="Patterns detected"
        )
        assert response.has_existing_config is False
        assert len(response.emis) == 1
        assert response.salary == salary


class TestConfirmConfigRequest:
    """Test suite for ConfirmConfigRequest model"""
    
    def test_confirm_config_request_valid_data(self):
        """Test ConfirmConfigRequest with valid data"""
        request = ConfirmConfigRequest(
            salary_source="Company Salary",
            salary_amount=100000.0,
            emi_pattern_ids=["pattern-1", "pattern-2"],
            salary_account_rate=2.5,
            savings_account_rate=7.0
        )
        assert request.salary_amount == 100000.0
        assert len(request.emi_pattern_ids) == 2
    
    def test_confirm_config_request_optional_rates(self):
        """Test ConfirmConfigRequest with optional rates"""
        request = ConfirmConfigRequest(
            salary_source="Company",
            salary_amount=100000.0,
            emi_pattern_ids=[]
        )
        # Rates should use defaults from module
        assert request.salary_source == "Company"


class TestUpdateEMIRequest:
    """Test suite for UpdateEMIRequest model"""
    
    def test_update_emi_request_valid_data(self):
        """Test UpdateEMIRequest with valid data"""
        request = UpdateEMIRequest(
            pattern_id="pattern-123",
            user_label="My Home Loan",
            emi_amount=55000.0
        )
        assert request.pattern_id == "pattern-123"
        assert request.user_label == "My Home Loan"
        assert request.emi_amount == 55000.0
    
    def test_update_emi_request_optional_fields(self):
        """Test UpdateEMIRequest with optional fields"""
        request = UpdateEMIRequest(
            pattern_id="pattern-456"
        )
        assert request.user_label is None
        assert request.emi_amount is None


class TestOptimizerScenario:
    """Test suite for OptimizerScenario model (salary_sweep_v2)"""
    
    def test_optimizer_scenario_valid_data(self):
        """Test OptimizerScenario with valid data"""
        scenario = OptimizerScenario(
            name="Current",
            description="Current",
            emi_dates=None,
            salary_account_balance=0.0,
            savings_account_balance=0.0,
            avg_days_in_savings=0.0,
            monthly_interest_salary=0.0,
            monthly_interest_savings=0.0,
            total_monthly_interest=0.0,
            total_annual_interest=0.0
        )
        assert scenario.name == "Current"
        assert scenario.total_annual_interest == 0.0


class TestCalculateResponse:
    """Test suite for CalculateResponse model (salary_sweep_v2)"""
    
    def test_calculate_response_valid_data(self):
        """Test CalculateResponse with valid data"""
        scenario = OptimizerScenario(
            name="Current",
            description="Current",
            emi_dates=None,
            salary_account_balance=0.0,
            savings_account_balance=0.0,
            avg_days_in_savings=0.0,
            monthly_interest_salary=0.0,
            monthly_interest_savings=0.0,
            total_monthly_interest=0.0,
            total_annual_interest=0.0
        )
        
        response = CalculateResponse(
            current_scenario=scenario,
            uniform_sweep=scenario,
            optimized_sweep=scenario,
            recommendation="Use optimized sweep",
            interest_gain_vs_current=6000.0
        )
        assert response.recommendation == "Use optimized sweep"
        assert response.interest_gain_vs_current == 6000.0


class TestConfigResponse:
    """Test suite for ConfigResponse model"""
    
    def test_config_response_valid_data(self):
        """Test ConfigResponse with valid data"""
        pattern = EMIPatternResponse(
            pattern_id="pattern-1",
            merchant_source="HDFC",
            emi_amount=50000.0,
            occurrence_count=12,
            is_confirmed=True
        )
        calculate_response = CalculateResponse(
            current_scenario=OptimizerScenario(
                name="Current",
                description="Current",
                emi_dates=None,
                salary_account_balance=0.0,
                savings_account_balance=0.0,
                avg_days_in_savings=0.0,
                monthly_interest_salary=0.0,
                monthly_interest_savings=0.0,
                total_monthly_interest=0.0,
                total_annual_interest=0.0
            ),
            uniform_sweep=OptimizerScenario(
                name="Uniform",
                description="Uniform",
                emi_dates=None,
                salary_account_balance=0.0,
                savings_account_balance=0.0,
                avg_days_in_savings=0.0,
                monthly_interest_salary=0.0,
                monthly_interest_savings=0.0,
                total_monthly_interest=0.0,
                total_annual_interest=0.0
            ),
            optimized_sweep=OptimizerScenario(
                name="Optimized",
                description="Optimized",
                emi_dates=None,
                salary_account_balance=0.0,
                savings_account_balance=0.0,
                avg_days_in_savings=0.0,
                monthly_interest_salary=0.0,
                monthly_interest_savings=0.0,
                total_monthly_interest=0.0,
                total_annual_interest=0.0
            ),
            recommendation="Optimized",
            interest_gain_vs_current=6000.0
        )
        
        response = ConfigResponse(
            config_id="config-123",
            salary_source="Company",
            salary_amount=100000.0,
            selected_scenario="optimized",
            monthly_interest_saved=500.0,
            annual_interest_saved=6000.0,
            confirmed_emis=[pattern],
            optimization_results=calculate_response
        )
        assert response.config_id == "config-123"
        assert response.selected_scenario == "optimized"
        assert len(response.confirmed_emis) == 1
    
    def test_config_response_optional_fields(self):
        """Test ConfigResponse with optional fields"""
        response = ConfigResponse(
            config_id="config-456",
            salary_source="Company",
            salary_amount=100000.0,
            confirmed_emis=[]
        )
        assert response.selected_scenario is None
        assert response.optimization_results is None


class TestRecurringPaymentsByCategoryResponse:
    """Test suite for RecurringPaymentsByCategoryResponse model"""
    
    def test_recurring_payments_by_category_response_valid_data(self):
        """Test RecurringPaymentsByCategoryResponse with valid data"""
        loan_pattern = EMIPatternResponse(
            pattern_id="loan-1",
            merchant_source="HDFC Home Loan",
            emi_amount=50000.0,
            occurrence_count=12,
            category="Loan",
            is_confirmed=True
        )
        insurance_pattern = EMIPatternResponse(
            pattern_id="insurance-1",
            merchant_source="LIC",
            emi_amount=5000.0,
            occurrence_count=12,
            category="Insurance",
            is_confirmed=True
        )
        
        response = RecurringPaymentsByCategoryResponse(
            loans=[loan_pattern],
            insurance=[insurance_pattern],
            investments=[],
            government_schemes=[]
        )
        assert len(response.loans) == 1
        assert len(response.insurance) == 1
        assert len(response.investments) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

