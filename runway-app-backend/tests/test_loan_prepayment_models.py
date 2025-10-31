"""
Unit tests for Loan Prepayment route models

Run with: pytest tests/test_loan_prepayment_models.py -v
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.routes.loan_prepayment import (
    DetectedLoan, LoanInput, PrepaymentScenario,
    LoanPrepaymentResponse, CalculateRequest
)


class TestDetectedLoan:
    """Test suite for DetectedLoan model"""
    
    def test_detected_loan_valid_data(self):
        """Test DetectedLoan with valid data"""
        loan = DetectedLoan(
            source="HDFC Home Loan",
            avg_emi=50000.0,
            count=12,
            txns=[{"transaction_id": "txn-1", "amount": 50000.0}]
        )
        assert loan.source == "HDFC Home Loan"
        assert loan.avg_emi == 50000.0
        assert len(loan.txns) == 1
    
    def test_detected_loan_empty_txns(self):
        """Test DetectedLoan with empty transactions"""
        loan = DetectedLoan(
            source="Test Loan",
            avg_emi=10000.0,
            count=3,
            txns=[]
        )
        assert len(loan.txns) == 0


class TestLoanInput:
    """Test suite for LoanInput model"""
    
    def test_loan_input_valid_data(self):
        """Test LoanInput with valid data"""
        loan = LoanInput(
            loan_id="loan-123",
            name="Home Loan",
            source="HDFC",
            emi=50000.0,
            remaining_principal=3000000.0,
            interest_rate=8.5,
            remaining_tenure_months=120
        )
        assert loan.loan_id == "loan-123"
        assert loan.remaining_tenure_months == 120


class TestPrepaymentScenario:
    """Test suite for PrepaymentScenario model"""
    
    def test_prepayment_scenario_valid_data(self):
        """Test PrepaymentScenario with valid data"""
        scenario = PrepaymentScenario(
            name="Optimized",
            description="Prioritize high interest loans",
            loans=[{"name": "Home Loan", "interest": 100000.0}],
            total_interest=500000.0,
            total_saved=100000.0,
            total_tenure_reduction_months=12
        )
        assert scenario.name == "Optimized"
        assert scenario.total_saved == 100000.0


class TestLoanPrepaymentResponse:
    """Test suite for LoanPrepaymentResponse model"""
    
    def test_loan_prepayment_response_valid_data(self):
        """Test LoanPrepaymentResponse with valid data"""
        loan = DetectedLoan(
            source="HDFC",
            avg_emi=50000.0,
            count=12
        )
        response = LoanPrepaymentResponse(
            detected_loans=[loan],
            monthly_income=200000.0,
            monthly_expenses=100000.0,
            monthly_cash_flow=100000.0,
            scenarios={
                "no_prepayment": {"name": "No Prepayment", "total_interest": 600000.0},
                "optimized": {"name": "Optimized", "total_interest": 500000.0}
            }
        )
        assert response.monthly_income == 200000.0
        assert len(response.scenarios) == 2


class TestCalculateRequest:
    """Test suite for CalculateRequest model"""
    
    def test_calculate_request_valid_data(self):
        """Test CalculateRequest with valid data"""
        loan = LoanInput(
            loan_id="loan-1",
            name="Home Loan",
            source="HDFC",
            emi=50000.0,
            remaining_principal=3000000.0,
            interest_rate=8.5,
            remaining_tenure_months=120
        )
        request = CalculateRequest(
            loans=[loan],
            annual_prepayment=100000.0,
            monthly_income=200000.0,
            monthly_expenses=100000.0
        )
        assert len(request.loans) == 1
        assert request.annual_prepayment == 100000.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

