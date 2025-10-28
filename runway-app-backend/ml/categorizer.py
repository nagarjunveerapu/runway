"""
ML Transaction Categorizer

Uses TF-IDF + Random Forest for transaction categorization.
Supports incremental learning from user corrections.
"""

import joblib
import logging
import json
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime
import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, StratifiedKFold, GridSearchCV
from sklearn.metrics import classification_report, accuracy_score
from sklearn.utils.class_weight import compute_class_weight

logger = logging.getLogger(__name__)


class MLCategorizer:
    """
    ML-based transaction categorizer

    Features:
    - TF-IDF feature extraction from merchant names and descriptions
    - Random Forest classifier with hyperparameter tuning
    - Stratified cross-validation
    - Class weight balancing for imbalanced datasets
    - Incremental learning support
    - Model versioning and metadata tracking
    """

    def __init__(self, model_path: str = "ml/models/categorizer.pkl"):
        """
        Initialize ML categorizer

        Args:
            model_path: Path to save/load trained model
        """
        self.model_path = Path(model_path)
        self.model_path.parent.mkdir(parents=True, exist_ok=True)

        # ML components
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.classifier: Optional[RandomForestClassifier] = None

        # Model metadata
        self.metadata = {
            'version': '1.0',
            'trained_at': None,
            'training_samples': 0,
            'categories': [],
            'accuracy': 0.0,
        }

        # Try to load existing model
        self.load_model()

    def train(self,
              transactions: List[Dict],
              test_size: float = 0.2,
              use_cross_validation: bool = True,
              n_folds: int = 5,
              tune_hyperparameters: bool = False) -> Dict:
        """
        Train categorizer on labeled transactions

        Args:
            transactions: List of transactions with 'description'/'merchant' and 'category' fields
            test_size: Fraction of data to use for testing
            use_cross_validation: Whether to use cross-validation
            n_folds: Number of CV folds
            tune_hyperparameters: Whether to perform grid search for hyperparameters

        Returns:
            Training metrics dictionary
        """
        if not transactions:
            raise ValueError("No transactions provided for training")

        logger.info(f"Training categorizer on {len(transactions)} transactions...")

        # Prepare features and labels
        X_text = []
        y = []

        for txn in transactions:
            # Combine merchant and description for richer features
            merchant = txn.get('merchant_canonical') or txn.get('merchant_raw') or ''
            description = txn.get('clean_description') or txn.get('description') or ''
            text = f"{merchant} {description}".strip()

            category = txn.get('category')

            if not text or not category:
                continue

            X_text.append(text)
            y.append(category)

        if len(X_text) < 10:
            raise ValueError(f"Insufficient training data: {len(X_text)} samples (need at least 10)")

        # Get unique categories
        unique_categories = sorted(list(set(y)))
        logger.info(f"Categories: {unique_categories}")

        # Initialize vectorizer
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            ngram_range=(1, 2),
            min_df=2,
            stop_words='english'
        )

        # Transform text to features
        X = self.vectorizer.fit_transform(X_text)

        # Compute class weights for imbalanced datasets
        class_weights = compute_class_weight(
            class_weight='balanced',
            classes=np.array(unique_categories),
            y=y
        )
        class_weight_dict = dict(zip(unique_categories, class_weights))
        logger.info(f"Class weights: {class_weight_dict}")

        # Initialize classifier
        if tune_hyperparameters:
            logger.info("Performing hyperparameter tuning...")
            self.classifier = self._tune_hyperparameters(X, y, unique_categories, class_weight_dict)
        else:
            self.classifier = RandomForestClassifier(
                n_estimators=100,
                max_depth=20,
                min_samples_split=5,
                min_samples_leaf=2,
                class_weight=class_weight_dict,
                random_state=42,
                n_jobs=-1
            )

        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )

        # Train model
        self.classifier.fit(X_train, y_train)

        # Evaluate
        y_pred = self.classifier.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)

        logger.info(f"Test accuracy: {accuracy:.3f}")

        # Cross-validation
        cv_scores = []
        if use_cross_validation and len(X_text) >= n_folds * 2:
            logger.info(f"Running {n_folds}-fold cross-validation...")
            cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)

            for fold, (train_idx, val_idx) in enumerate(cv.split(X, y), 1):
                X_fold_train = X[train_idx]
                X_fold_val = X[val_idx]
                y_fold_train = [y[i] for i in train_idx]
                y_fold_val = [y[i] for i in val_idx]

                fold_clf = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=20,
                    class_weight=class_weight_dict,
                    random_state=42,
                    n_jobs=-1
                )
                fold_clf.fit(X_fold_train, y_fold_train)
                fold_score = fold_clf.score(X_fold_val, y_fold_val)
                cv_scores.append(fold_score)
                logger.info(f"  Fold {fold}: {fold_score:.3f}")

            mean_cv_score = np.mean(cv_scores)
            logger.info(f"Mean CV accuracy: {mean_cv_score:.3f} ± {np.std(cv_scores):.3f}")

        # Classification report
        report = classification_report(y_test, y_pred)
        logger.info(f"\nClassification Report:\n{report}")

        # Update metadata
        self.metadata = {
            'version': '2.0',
            'trained_at': datetime.now().isoformat(),
            'training_samples': len(X_text),
            'categories': unique_categories,
            'accuracy': accuracy,
            'cv_scores': cv_scores,
            'mean_cv_score': np.mean(cv_scores) if cv_scores else None,
            'vocab_size': len(self.vectorizer.vocabulary_),
            'class_weights': class_weight_dict,
        }

        # Save model
        self.save_model()

        return {
            'accuracy': accuracy,
            'cv_scores': cv_scores,
            'mean_cv_score': np.mean(cv_scores) if cv_scores else None,
            'training_samples': len(X_text),
            'categories': unique_categories,
        }

    def _tune_hyperparameters(self, X, y, categories, class_weight_dict) -> RandomForestClassifier:
        """Perform grid search for hyperparameter tuning"""
        param_grid = {
            'n_estimators': [50, 100, 200],
            'max_depth': [10, 20, 30],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4],
        }

        base_clf = RandomForestClassifier(
            class_weight=class_weight_dict,
            random_state=42,
            n_jobs=-1
        )

        grid_search = GridSearchCV(
            base_clf,
            param_grid,
            cv=3,
            scoring='accuracy',
            n_jobs=-1,
            verbose=1
        )

        grid_search.fit(X, y)

        logger.info(f"Best parameters: {grid_search.best_params_}")
        logger.info(f"Best CV score: {grid_search.best_score_:.3f}")

        return grid_search.best_estimator_

    def predict(self, transaction: Dict) -> Tuple[str, float]:
        """
        Predict category for a single transaction

        Args:
            transaction: Transaction dictionary with 'description'/'merchant' fields

        Returns:
            Tuple of (predicted_category, confidence)
        """
        if not self.vectorizer or not self.classifier:
            raise ValueError("Model not trained. Call train() first or load_model()")

        # Extract text features
        merchant = transaction.get('merchant_canonical') or transaction.get('merchant_raw') or ''
        description = transaction.get('clean_description') or transaction.get('description') or ''
        text = f"{merchant} {description}".strip()

        if not text:
            return 'Unknown', 0.0

        # Transform to features
        X = self.vectorizer.transform([text])

        # Predict
        category = self.classifier.predict(X)[0]

        # Get confidence (probability)
        probabilities = self.classifier.predict_proba(X)[0]
        confidence = float(np.max(probabilities))

        return category, confidence

    def predict_batch(self, transactions: List[Dict]) -> List[Tuple[str, float]]:
        """
        Predict categories for multiple transactions

        Args:
            transactions: List of transaction dictionaries

        Returns:
            List of (category, confidence) tuples
        """
        if not self.vectorizer or not self.classifier:
            raise ValueError("Model not trained. Call train() first or load_model()")

        # Extract text features
        X_text = []
        for txn in transactions:
            merchant = txn.get('merchant_canonical') or txn.get('merchant_raw') or ''
            description = txn.get('clean_description') or txn.get('description') or ''
            text = f"{merchant} {description}".strip()
            X_text.append(text if text else ' ')  # Avoid empty strings

        # Transform to features
        X = self.vectorizer.transform(X_text)

        # Predict
        categories = self.classifier.predict(X)
        probabilities = self.classifier.predict_proba(X)
        confidences = np.max(probabilities, axis=1)

        return list(zip(categories, confidences))

    def save_model(self):
        """Save trained model to disk"""
        if not self.vectorizer or not self.classifier:
            logger.warning("No model to save")
            return

        model_data = {
            'vectorizer': self.vectorizer,
            'classifier': self.classifier,
            'metadata': self.metadata,
        }

        joblib.dump(model_data, self.model_path)
        logger.info(f"Saved model to {self.model_path}")

        # Save metadata separately for easy access
        metadata_path = self.model_path.with_suffix('.json')
        with open(metadata_path, 'w') as f:
            # Convert numpy types to native Python types for JSON
            metadata_json = {
                k: (v.tolist() if isinstance(v, np.ndarray) else
                    float(v) if isinstance(v, np.floating) else
                    v)
                for k, v in self.metadata.items()
            }
            json.dump(metadata_json, f, indent=2, default=str)

    def load_model(self) -> bool:
        """
        Load trained model from disk

        Returns:
            True if model loaded successfully, False otherwise
        """
        if not self.model_path.exists():
            logger.info(f"No saved model found at {self.model_path}")
            return False

        try:
            model_data = joblib.load(self.model_path)

            self.vectorizer = model_data['vectorizer']
            self.classifier = model_data['classifier']
            self.metadata = model_data.get('metadata', {})

            logger.info(f"Loaded model from {self.model_path}")
            logger.info(f"Model metadata: {self.metadata}")

            return True

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    def get_feature_importance(self, top_n: int = 20) -> Dict[str, float]:
        """
        Get top N important features

        Args:
            top_n: Number of top features to return

        Returns:
            Dictionary of feature names and their importance scores
        """
        if not self.classifier or not self.vectorizer:
            return {}

        # Get feature importances
        importances = self.classifier.feature_importances_
        feature_names = self.vectorizer.get_feature_names_out()

        # Sort by importance
        indices = np.argsort(importances)[::-1][:top_n]

        return {
            feature_names[i]: float(importances[i])
            for i in indices
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Sample labeled training data
    training_data = [
        {'merchant_canonical': 'Swiggy', 'description': 'food delivery', 'category': 'Food & Dining'},
        {'merchant_canonical': 'Zomato', 'description': 'restaurant order', 'category': 'Food & Dining'},
        {'merchant_canonical': 'Amazon', 'description': 'online shopping', 'category': 'Shopping'},
        {'merchant_canonical': 'Flipkart', 'description': 'electronics', 'category': 'Shopping'},
        {'merchant_canonical': 'Uber', 'description': 'cab ride', 'category': 'Transport'},
        {'merchant_canonical': 'Netflix', 'description': 'streaming', 'category': 'Entertainment'},
    ] * 10  # Repeat to have enough samples

    categorizer = MLCategorizer()

    print("Training model...")
    metrics = categorizer.train(training_data, use_cross_validation=True)
    print(f"\nTraining metrics: {metrics}")

    # Test prediction
    test_txn = {'merchant_canonical': 'Swiggy', 'description': 'food order'}
    category, confidence = categorizer.predict(test_txn)
    print(f"\nPrediction: {category} (confidence: {confidence:.3f})")

    # Feature importance
    print(f"\nTop features: {categorizer.get_feature_importance(top_n=10)}")
