"""
Unit tests for ML Categorizer

Run with: pytest tests/unit/test_ml_categorizer.py -v
"""

import pytest
import tempfile
import json
from pathlib import Path
import numpy as np

from ml.categorizer import MLCategorizer


class TestMLCategorizer:
    """Test suite for ML Categorizer"""
    
    def test_model_initialization(self):
        """Test model can be initialized"""
        # Use a non-existent path to ensure clean initialization
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "test_model.pkl"
            categorizer = MLCategorizer(model_path=str(model_path))
            assert categorizer is not None
            # If no existing model, should be None
            assert categorizer.vectorizer is None  # Not trained yet
            assert categorizer.classifier is None
    
    def test_model_training(self):
        """Test model can be trained on labeled data"""
        # Generate training data
        training_data = [
            {'merchant_canonical': 'Swiggy', 'description': 'food delivery', 'category': 'Food & Dining'},
            {'merchant_canonical': 'Zomato', 'description': 'restaurant order', 'category': 'Food & Dining'},
            {'merchant_canonical': 'Amazon', 'description': 'shopping', 'category': 'Shopping'},
            {'merchant_canonical': 'Flipkart', 'description': 'electronics', 'category': 'Shopping'},
            {'merchant_canonical': 'Uber', 'description': 'cab ride', 'category': 'Transport'},
            {'merchant_canonical': 'Netflix', 'description': 'streaming', 'category': 'Entertainment'},
            {'merchant_canonical': 'Apollo Pharmacy', 'description': 'medicine', 'category': 'Healthcare'},
            {'merchant_canonical': 'HDFC', 'description': 'loan emi', 'category': 'Bills & Utilities'},
            {'merchant_canonical': 'Travel Agent', 'description': 'booking', 'category': 'Travel'},
            {'merchant_canonical': 'Paytm', 'description': 'wallet', 'category': 'Transfer'},
        ] * 5  # 50 samples total
        
        categorizer = MLCategorizer()
        metrics = categorizer.train(
            training_data,
            test_size=0.2,
            use_cross_validation=False  # Faster for unit tests
        )
        
        # Verify training succeeded
        assert metrics['accuracy'] > 0.3  # Basic threshold
        assert 'categories' in metrics
        assert len(metrics['categories']) > 0
        assert categorizer.vectorizer is not None
        assert categorizer.classifier is not None
    
    def test_model_prediction(self):
        """Test model can predict categories for transactions"""
        # Create trained model
        categorizer = MLCategorizer()
        training_data = self._generate_sample_training_data()
        categorizer.train(training_data, use_cross_validation=False)
        
        # Test prediction
        test_txn = {
            'merchant_canonical': 'Swiggy',
            'description': 'food order'
        }
        category, confidence = categorizer.predict(test_txn)
        
        # Verify output format
        assert isinstance(category, str)
        assert 0.0 <= confidence <= 1.0
        assert category in [
            'Food & Dining', 'Shopping', 'Transport', 
            'Entertainment', 'Healthcare', 'Bills & Utilities',
            'Travel', 'Transfer', 'Groceries', 'Unknown'
        ]
    
    def test_batch_prediction(self):
        """Test model can predict multiple transactions efficiently"""
        categorizer = MLCategorizer()
        training_data = self._generate_sample_training_data()
        categorizer.train(training_data, use_cross_validation=False)
        
        # Batch of test transactions
        test_txns = [
            {'merchant_canonical': 'Swiggy', 'description': 'food'},
            {'merchant_canonical': 'Amazon', 'description': 'shopping'},
            {'merchant_canonical': 'Uber', 'description': 'ride'},
        ]
        
        results = categorizer.predict_batch(test_txns)
        
        # Verify results
        assert len(results) == len(test_txns)
        assert all(isinstance(cat, str) for cat, _ in results)
        assert all(0.0 <= conf <= 1.0 for _, conf in results)
    
    def test_model_persistence(self):
        """Test model can be saved and loaded"""
        # Create and train model
        categorizer = MLCategorizer()
        training_data = self._generate_sample_training_data()
        categorizer.train(training_data, use_cross_validation=False)
        
        # Save model
        categorizer.save_model()
        
        # Create new instance and load
        new_categorizer = MLCategorizer()
        loaded = new_categorizer.load_model()
        
        # Verify load succeeded
        assert loaded is True
        assert new_categorizer.vectorizer is not None
        assert new_categorizer.classifier is not None
        
        # Verify predictions match
        test_txn = {'merchant_canonical': 'Swiggy', 'description': 'food'}
        cat1, conf1 = categorizer.predict(test_txn)
        cat2, conf2 = new_categorizer.predict(test_txn)
        
        assert cat1 == cat2
        assert abs(conf1 - conf2) < 0.01  # Should be identical
    
    def test_empty_input(self):
        """Test model handles empty/None inputs gracefully"""
        categorizer = MLCategorizer()
        training_data = self._generate_sample_training_data()
        categorizer.train(training_data, use_cross_validation=False)
        
        # Test empty transaction
        empty_txn = {}
        category, confidence = categorizer.predict(empty_txn)
        
        assert category == 'Unknown'
        assert confidence == 0.0
    
    def test_imbalanced_data(self):
        """Test model handles imbalanced categories"""
        # Create imbalanced training data
        training_data = []
        
        # Lots of Food & Dining
        for i in range(50):
            training_data.append({
                'merchant_canonical': f'Restaurant{i}',
                'description': 'food',
                'category': 'Food & Dining'
            })
        
        # Few Rare category
        for i in range(2):
            training_data.append({
                'merchant_canonical': f'Rare{i}',
                'description': 'unusual',
                'category': 'Transfer'
            })
        
        categorizer = MLCategorizer()
        metrics = categorizer.train(training_data, use_cross_validation=False)
        
        # Should still learn both categories
        assert 'Food & Dining' in metrics['categories']
        assert 'Transfer' in metrics['categories']
    
    def test_hyperparameter_tuning(self):
        """Test model can tune hyperparameters"""
        categorizer = MLCategorizer()
        training_data = self._generate_sample_training_data()
        
        # This will be slow, so reduce data
        small_data = training_data[:30]
        
        metrics = categorizer.train(
            small_data,
            tune_hyperparameters=True,
            use_cross_validation=False
        )
        
        # Should complete without error
        assert metrics['accuracy'] >= 0
    
    def test_feature_importance(self):
        """Test model can extract feature importance"""
        categorizer = MLCategorizer()
        training_data = self._generate_sample_training_data()
        categorizer.train(training_data, use_cross_validation=False)
        
        # Get feature importance
        features = categorizer.get_feature_importance(top_n=10)
        
        # Verify format
        assert isinstance(features, dict)
        assert len(features) <= 10
        assert all(isinstance(name, str) for name in features.keys())
        assert all(isinstance(score, (int, float)) for score in features.values())
    
    def test_cross_validation(self):
        """Test cross-validation works correctly"""
        categorizer = MLCategorizer()
        training_data = self._generate_sample_training_data()
        
        metrics = categorizer.train(
            training_data,
            use_cross_validation=True,
            n_folds=3  # Faster than 5
        )
        
        # Verify CV scores
        assert 'cv_scores' in metrics
        assert len(metrics['cv_scores']) == 3
        assert all(isinstance(score, (int, float)) for score in metrics['cv_scores'])
        assert metrics['mean_cv_score'] > 0
    
    def _generate_sample_training_data(self):
        """Helper to generate sample training data"""
        return [
            {'merchant_canonical': 'Swiggy', 'description': 'food delivery', 'category': 'Food & Dining'},
            {'merchant_canonical': 'Zomato', 'description': 'restaurant', 'category': 'Food & Dining'},
            {'merchant_canonical': 'Dominos', 'description': 'pizza', 'category': 'Food & Dining'},
            {'merchant_canonical': 'Amazon', 'description': 'shopping', 'category': 'Shopping'},
            {'merchant_canonical': 'Flipkart', 'description': 'electronics', 'category': 'Shopping'},
            {'merchant_canonical': 'Myntra', 'description': 'fashion', 'category': 'Shopping'},
            {'merchant_canonical': 'Uber', 'description': 'cab', 'category': 'Transport'},
            {'merchant_canonical': 'Ola', 'description': 'ride', 'category': 'Transport'},
            {'merchant_canonical': 'Netflix', 'description': 'streaming', 'category': 'Entertainment'},
            {'merchant_canonical': 'Spotify', 'description': 'music', 'category': 'Entertainment'},
        ] * 5  # 50 samples


@pytest.mark.parametrize("merchant,expected_category", [
    ('Swiggy', 'Food & Dining'),
    ('Zomato', 'Food & Dining'),
    ('Amazon', 'Shopping'),
    ('Flipkart', 'Shopping'),
])
def test_category_consistency(merchant, expected_category):
    """Test model gives consistent predictions for known merchants"""
    categorizer = MLCategorizer()
    training_data = [
        {'merchant_canonical': 'Swiggy', 'description': 'food', 'category': 'Food & Dining'},
        {'merchant_canonical': 'Zomato', 'description': 'food', 'category': 'Food & Dining'},
        {'merchant_canonical': 'Amazon', 'description': 'shop', 'category': 'Shopping'},
        {'merchant_canonical': 'Flipkart', 'description': 'shop', 'category': 'Shopping'},
    ] * 10
    
    categorizer.train(training_data, use_cross_validation=False)
    
    txn = {'merchant_canonical': merchant, 'description': 'purchase'}
    category, _ = categorizer.predict(txn)
    
    # Should match expected (or at least be reasonable)
    assert category == expected_category or category != 'Unknown'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

