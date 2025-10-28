"""
Train and evaluate the ML Categorizer model

This script helps you:
1. Train the model with new data
2. Evaluate performance
3. Compare different model versions

Usage:
    python3 ml/train_and_evaluate.py                    # Train with default data
    python3 ml/train_and_evaluate.py --tune              # With hyperparameter tuning
    python3 ml/train_and_evaluate.py --evaluate-only    # Just evaluate existing model
"""

import json
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

from ml.categorizer import MLCategorizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_training_data(file_path: Path) -> List[Dict]:
    """Load training data from JSONL file"""
    if not file_path.exists():
        logger.error(f"Training data file not found: {file_path}")
        return []
    
    samples = []
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line.strip()))
    
    logger.info(f"Loaded {len(samples)} training samples from {file_path}")
    return samples


def save_evaluation_report(metrics: Dict, output_path: Path):
    """Save evaluation report to file"""
    report = {
        'evaluation_date': datetime.now().isoformat(),
        'metrics': metrics
    }
    
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    logger.info(f"Evaluation report saved to: {output_path}")


def evaluate_model(categorizer: MLCategorizer, test_data: List[Dict]) -> Dict:
    """Evaluate model on test data"""
    if not test_data:
        logger.warning("No test data provided")
        return {}
    
    logger.info(f"\nEvaluating model on {len(test_data)} test samples...")
    
    correct = 0
    category_stats = {}
    confidence_stats = []
    
    for sample in test_data:
        merchant = sample.get('merchant_canonical') or sample.get('merchant') or ''
        description = sample.get('description', '')
        true_category = sample.get('category', 'Unknown')
        
        if not merchant and not description:
            continue
        
        transaction = {
            'merchant_canonical': merchant,
            'description': description
        }
        
        # Predict
        predicted_category, confidence = categorizer.predict(transaction)
        
        # Track statistics
        is_correct = (predicted_category == true_category)
        if is_correct:
            correct += 1
        
        # Per-category stats
        if true_category not in category_stats:
            category_stats[true_category] = {'correct': 0, 'total': 0}
        category_stats[true_category]['total'] += 1
        if is_correct:
            category_stats[true_category]['correct'] += 1
        
        # Confidence tracking
        confidence_stats.append({
            'true_category': true_category,
            'predicted_category': predicted_category,
            'confidence': confidence,
            'correct': is_correct
        })
    
    # Calculate accuracy
    accuracy = correct / len(test_data) if test_data else 0
    
    # Calculate per-category accuracies
    category_accuracies = {
        cat: stats['correct'] / stats['total']
        for cat, stats in category_stats.items()
    }
    
    # Calculate average confidence
    avg_confidence = sum(c['confidence'] for c in confidence_stats) / len(confidence_stats) if confidence_stats else 0
    
    # Confidence for correct vs incorrect predictions
    correct_confidences = [c['confidence'] for c in confidence_stats if c['correct']]
    incorrect_confidences = [c['confidence'] for c in confidence_stats if not c['correct']]
    
    avg_correct_confidence = sum(correct_confidences) / len(correct_confidences) if correct_confidences else 0
    avg_incorrect_confidence = sum(incorrect_confidences) / len(incorrect_confidences) if incorrect_confidences else 0
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Overall Accuracy: {accuracy:.1%}")
    logger.info(f"Correct: {correct}/{len(test_data)}")
    logger.info(f"\nPer-Category Accuracy:")
    for cat, acc in sorted(category_accuracies.items()):
        logger.info(f"  {cat}: {acc:.1%} ({category_stats[cat]['correct']}/{category_stats[cat]['total']})")
    
    logger.info(f"\nConfidence Statistics:")
    logger.info(f"  Average: {avg_confidence:.2f}")
    logger.info(f"  Correct predictions: {avg_correct_confidence:.2f}")
    logger.info(f"  Incorrect predictions: {avg_incorrect_confidence:.2f}")
    logger.info(f"{'='*60}")
    
    return {
        'accuracy': accuracy,
        'correct': correct,
        'total': len(test_data),
        'category_accuracies': category_accuracies,
        'avg_confidence': avg_confidence,
        'avg_correct_confidence': avg_correct_confidence,
        'avg_incorrect_confidence': avg_incorrect_confidence
    }


def train_model(
    training_data: List[Dict],
    tune_hyperparameters: bool = False,
    use_cross_validation: bool = True,
    test_size: float = 0.2
) -> Dict:
    """Train the model and return metrics"""
    logger.info(f"\n{'='*60}")
    logger.info("TRAINING MODEL")
    logger.info(f"{'='*60}")
    logger.info(f"Training samples: {len(training_data)}")
    logger.info(f"Hyperparameter tuning: {tune_hyperparameters}")
    logger.info(f"Cross-validation: {use_cross_validation}")
    
    categorizer = MLCategorizer()
    
    try:
        metrics = categorizer.train(
            training_data,
            test_size=test_size,
            use_cross_validation=use_cross_validation,
            tune_hyperparameters=tune_hyperparameters
        )
        
        logger.info(f"\nTraining completed successfully!")
        logger.info(f"Test Accuracy: {metrics['accuracy']:.1%}")
        if metrics.get('mean_cv_score'):
            logger.info(f"Mean CV Accuracy: {metrics['mean_cv_score']:.1%}")
        
        return metrics
        
    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        raise


def main():
    parser = argparse.ArgumentParser(
        description='Train and evaluate ML Categorizer'
    )
    parser.add_argument(
        '--data',
        type=str,
        default='ml/training_data/labeled_transactions.jsonl',
        help='Path to training data file'
    )
    parser.add_argument(
        '--tune',
        action='store_true',
        help='Perform hyperparameter tuning (slower but better)'
    )
    parser.add_argument(
        '--no-cv',
        action='store_true',
        help='Skip cross-validation (faster training)'
    )
    parser.add_argument(
        '--evaluate-only',
        action='store_true',
        help='Only evaluate existing model, don\'t train'
    )
    parser.add_argument(
        '--test-split',
        type=float,
        default=0.2,
        help='Fraction of data to use for testing (default: 0.2)'
    )
    
    args = parser.parse_args()
    
    # Load training data
    data_path = Path(args.data)
    
    if not args.evaluate_only:
        training_data = load_training_data(data_path)
        
        if not training_data:
            logger.error("No training data found. Generate it first:")
            logger.error("  python3 ml/generate_training_data.py")
            return
        
        # Split training and test data
        test_size = args.test_split
        split_idx = int(len(training_data) * (1 - test_size))
        train_data = training_data[:split_idx]
        test_data = training_data[split_idx:]
        
        logger.info(f"\nData Split:")
        logger.info(f"  Training: {len(train_data)} samples")
        logger.info(f"  Testing: {len(test_data)} samples")
        
        # Train model
        metrics = train_model(
            train_data,
            tune_hyperparameters=args.tune,
            use_cross_validation=not args.no_cv,
            test_size=test_size
        )
        
        # Save training metrics
        report_path = Path('ml/models/training_report.json')
        save_evaluation_report(metrics, report_path)
    else:
        # Load existing model
        categorizer = MLCategorizer()
        if not categorizer.load_model():
            logger.error("No trained model found. Train first:")
            logger.error("  python3 ml/train_and_evaluate.py")
            return
        
        # Load all data for evaluation
        all_data = load_training_data(data_path)
        if not all_data:
            logger.error("No training data found for evaluation")
            return
        
        test_data = all_data
        logger.info(f"Evaluating on {len(test_data)} samples")
    
    # Evaluate model
    categorizer = MLCategorizer()
    categorizer.load_model()
    
    if not args.evaluate_only:
        # Evaluate on test set
        eval_metrics = evaluate_model(categorizer, test_data)
        save_evaluation_report(eval_metrics, Path('ml/models/evaluation_report.json'))
    else:
        # Evaluate on all data
        eval_metrics = evaluate_model(categorizer, test_data)
        save_evaluation_report(eval_metrics, Path('ml/models/evaluation_report.json'))
    
    logger.info("\n✅ Done!")


if __name__ == "__main__":
    main()

