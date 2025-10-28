"""
ML Categorization API Routes

ML-powered transaction categorization
"""

from fastapi import APIRouter, HTTPException, status
import sys
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.models.schemas import (
    CategorizeRequest,
    CategorizeResponse,
    BatchCategorizeRequest,
    BatchCategorizeResponse
)
from ml.categorizer import MLCategorizer
from src.merchant_normalizer import MerchantNormalizer
from config import Config

logger = logging.getLogger(__name__)

router = APIRouter()


# Initialize ML components (singleton pattern)
_categorizer = None
_merchant_normalizer = None


def get_categorizer():
    """Get or initialize ML categorizer"""
    global _categorizer
    if _categorizer is None:
        _categorizer = MLCategorizer(Config.ML_MODEL_PATH)
        if not _categorizer.vectorizer or not _categorizer.classifier:
            logger.warning("ML model not trained, predictions may be unreliable")
    return _categorizer


def get_merchant_normalizer():
    """Get or initialize merchant normalizer"""
    global _merchant_normalizer
    if _merchant_normalizer is None:
        _merchant_normalizer = MerchantNormalizer()
    return _merchant_normalizer


@router.post("/categorize", response_model=CategorizeResponse)
async def categorize_transaction(request: CategorizeRequest):
    """
    Categorize a single transaction using ML

    - **description**: Transaction description
    - **merchant**: Merchant name (optional)

    Returns predicted category and confidence score
    """
    try:
        categorizer = get_categorizer()
        merchant_norm = get_merchant_normalizer()

        # Normalize merchant if provided
        merchant_canonical = None
        if request.merchant:
            merchant_canonical, score = merchant_norm.normalize(request.merchant)
            if score < 70:  # Low confidence, use original
                merchant_canonical = request.merchant

        # Prepare transaction for ML
        transaction = {
            'merchant_canonical': merchant_canonical or request.merchant or '',
            'description': request.description
        }

        # Predict category
        category, confidence = categorizer.predict(transaction)

        return CategorizeResponse(
            category=category,
            confidence=round(confidence, 3),
            merchant_canonical=merchant_canonical
        )

    except Exception as e:
        logger.error(f"Error categorizing transaction: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to categorize transaction: {str(e)}"
        )


@router.post("/categorize/batch", response_model=BatchCategorizeResponse)
async def categorize_transactions_batch(request: BatchCategorizeRequest):
    """
    Categorize multiple transactions in a batch

    More efficient than calling /categorize multiple times

    - **transactions**: List of transactions to categorize

    Returns list of predictions with categories and confidence scores
    """
    try:
        categorizer = get_categorizer()
        merchant_norm = get_merchant_normalizer()

        results = []

        # Prepare transactions
        transactions = []
        for req in request.transactions:
            # Normalize merchant
            merchant_canonical = None
            if req.merchant:
                merchant_canonical, score = merchant_norm.normalize(req.merchant)
                if score < 70:
                    merchant_canonical = req.merchant

            transactions.append({
                'merchant_canonical': merchant_canonical or req.merchant or '',
                'description': req.description,
                'original_merchant': merchant_canonical
            })

        # Batch predict
        predictions = categorizer.predict_batch(transactions)

        # Build results
        for txn, (category, confidence) in zip(transactions, predictions):
            results.append(CategorizeResponse(
                category=category,
                confidence=round(confidence, 3),
                merchant_canonical=txn.get('original_merchant')
            ))

        return BatchCategorizeResponse(
            results=results,
            processed_count=len(results)
        )

    except Exception as e:
        logger.error(f"Error batch categorizing: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch categorize: {str(e)}"
        )


@router.get("/model/info")
async def get_model_info():
    """
    Get ML model information

    Returns metadata about the trained model
    """
    try:
        categorizer = get_categorizer()

        if not categorizer.vectorizer or not categorizer.classifier:
            return {
                "status": "not_trained",
                "message": "ML model has not been trained yet"
            }

        metadata = categorizer.metadata

        return {
            "status": "trained",
            "version": metadata.get('version', 'unknown'),
            "trained_at": metadata.get('trained_at'),
            "training_samples": metadata.get('training_samples', 0),
            "categories": metadata.get('categories', []),
            "accuracy": round(metadata.get('accuracy', 0), 3),
            "mean_cv_score": round(metadata.get('mean_cv_score', 0), 3) if metadata.get('mean_cv_score') else None,
            "vocabulary_size": metadata.get('vocab_size', 0)
        }

    except Exception as e:
        logger.error(f"Error fetching model info: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch model info: {str(e)}"
        )


@router.get("/categories")
async def get_available_categories():
    """
    Get list of available categories

    Returns all categories the model can predict
    """
    try:
        categorizer = get_categorizer()

        if not categorizer.vectorizer or not categorizer.classifier:
            # Return default categories
            return {
                "categories": [
                    "Food & Dining",
                    "Groceries",
                    "Shopping",
                    "Transport",
                    "Entertainment",
                    "Bills & Utilities",
                    "Healthcare",
                    "Travel",
                    "Transfer"
                ],
                "source": "default"
            }

        categories = categorizer.metadata.get('categories', [])

        return {
            "categories": sorted(categories),
            "source": "trained_model",
            "count": len(categories)
        }

    except Exception as e:
        logger.error(f"Error fetching categories: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch categories: {str(e)}"
        )
