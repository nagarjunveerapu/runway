"""
Unit tests for Assets route models

Run with: pytest tests/test_assets_models.py -v
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.routes.assets import DetectedAsset, AssetDetectionResponse


class TestDetectedAsset:
    """Test suite for DetectedAsset model"""
    
    def test_detected_asset_valid_data(self):
        """Test DetectedAsset with valid data"""
        asset = DetectedAsset(
            merchant="HDFC Home Loan",
            emi_amount=50000.0,
            transaction_count=12,
            estimated_loan_amount=3000000.0,
            estimated_interest_rate=8.5,
            suggested_asset_type="property",
            confidence="high"
        )
        assert asset.merchant == "HDFC Home Loan"
        assert asset.emi_amount == 50000.0
        assert asset.confidence == "high"
    
    def test_detected_asset_optional_fields(self):
        """Test DetectedAsset with optional fields as None"""
        asset = DetectedAsset(
            merchant="Unknown",
            emi_amount=10000.0,
            transaction_count=3,
            suggested_asset_type="other",
            confidence="low"
        )
        assert asset.estimated_loan_amount is None
        assert asset.estimated_interest_rate is None


class TestAssetDetectionResponse:
    """Test suite for AssetDetectionResponse model"""
    
    def test_asset_detection_response_valid_data(self):
        """Test AssetDetectionResponse with valid data"""
        asset = DetectedAsset(
            merchant="HDFC Home Loan",
            emi_amount=50000.0,
            transaction_count=12,
            suggested_asset_type="property",
            confidence="high"
        )
        response = AssetDetectionResponse(
            detected_assets=[asset],
            message="Found 1 potential asset"
        )
        assert len(response.detected_assets) == 1
        assert response.message == "Found 1 potential asset"
    
    def test_asset_detection_response_empty(self):
        """Test AssetDetectionResponse with empty assets"""
        response = AssetDetectionResponse(
            detected_assets=[],
            message="No assets detected"
        )
        assert len(response.detected_assets) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

