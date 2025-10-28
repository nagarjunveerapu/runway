# ML Model Guide: Understanding, Testing & Scaling

## 📚 Part 1: How the Model Works

### Architecture Overview

Your model uses a **two-stage approach**:

```
Transaction Text
      ↓
[TF-IDF Vectorizer] → Feature Extraction (1000 features)
      ↓
[Random Forest Classifier] → Category Prediction
      ↓
Category + Confidence Score
```

### 1. TF-IDF Vectorization (`TfidfVectorizer`)

**What it does**: Converts transaction text into numerical features

**Example**:
```python
# Input: "Swiggy food order"
# Output: [0.42, 0.18, 0.0, 0.92, ...]  # 1000-dimension vector
```

**Key Parameters**:
- `max_features=1000`: Uses top 1000 most important words/phrases
- `ngram_range=(1, 2)`: Captures single words AND word pairs
  - Example: "food delivery" → ["food", "delivery", "food delivery"]
- `min_df=2`: Ignores rare words (appearing < 2 times)
- `stop_words='english'`: Removes "a", "the", "and", etc.

**Why it works**:
- "Swiggy" appears frequently in Food & Dining → High TF-IDF score
- "Netflix" appears in Entertainment → Different TF-IDF pattern
- Model learns these patterns

### 2. Random Forest Classifier

**What it does**: Makes final categorization decision

**How it works**:
- Builds 100 decision trees (n_estimators=100)
- Each tree votes on category
- Final category = majority vote
- Confidence = % of trees that agree

**Example**:
```
100 trees:
  - 85 votes: "Food & Dining"
  - 10 votes: "Transfer"
  - 5 votes: "Entertainment"
  
Result: "Food & Dining" with confidence=0.85
```

**Key Parameters**:
- `n_estimators=100`: Number of decision trees
- `max_depth=20`: Prevents overfitting
- `class_weight='balanced'`: Handles imbalanced categories

---

## 🧪 Part 2: Testing the Model

### Test Structure

```
tests/
├── unit/              # Individual component tests
└── integration/       # End-to-end tests
```

### Writing Unit Tests

```python
# tests/unit/test_ml_categorizer.py

import pytest
from ml.categorizer import MLCategorizer

def test_model_initialization():
    """Test model can be initialized"""
    categorizer = MLCategorizer()
    assert categorizer is not None
    assert categorizer.vectorizer is None  # Not trained yet
    assert categorizer.classifier is None

def test_model_training():
    """Test model can be trained"""
    training_data = [
        {'merchant_canonical': 'Swiggy', 'description': 'food order', 'category': 'Food & Dining'},
        {'merchant_canonical': 'Amazon', 'description': 'shopping', 'category': 'Shopping'},
        # ... more examples
    ]
    
    categorizer = MLCategorizer()
    metrics = categorizer.train(training_data)
    
    assert metrics['accuracy'] > 0.5  # At least 50% accuracy
    assert 'categories' in metrics
    assert len(metrics['categories']) > 0

def test_model_prediction():
    """Test model can predict categories"""
    # Create a trained model
    categorizer = MLCategorizer()
    training_data = [
        {'merchant_canonical': 'Swiggy', 'description': 'food', 'category': 'Food & Dining'},
    ] * 10
    categorizer.train(training_data)
    
    # Test prediction
    test_txn = {'merchant_canonical': 'Swiggy', 'description': 'food order'}
    category, confidence = categorizer.predict(test_txn)
    
    assert category in ['Food & Dining', 'Unknown']  # Should recognize Food
    assert 0.0 <= confidence <= 1.0

def test_batch_prediction():
    """Test model can predict multiple transactions"""
    categorizer = MLCategorizer()
    # ... setup model ...
    
    test_txns = [
        {'merchant_canonical': 'Swiggy', 'description': 'food'},
        {'merchant_canonical': 'Netflix', 'description': 'streaming'},
    ]
    
    results = categorizer.predict_batch(test_txns)
    
    assert len(results) == 2
    assert all(0.0 <= conf <= 1.0 for _, conf in results)

def test_model_save_and_load():
    """Test model persistence"""
    categorizer = MLCategorizer()
    # ... train model ...
    
    # Save
    categorizer.save_model()
    
    # Load
    new_categorizer = MLCategorizer()
    assert new_categorizer.vectorizer is not None
    assert new_categorizer.classifier is not None

def test_class_imbalance_handling():
    """Test model handles imbalanced categories"""
    training_data = [
        {'merchant_canonical': 'Food', 'description': 'meal', 'category': 'Food & Dining'},
    ] * 100  # Lots of Food
    
    training_data += [
        {'merchant_canonical': 'Rare', 'description': 'something', 'category': 'Rare'},
    ] * 5  # Few Rare
    
    categorizer = MLCategorizer()
    metrics = categorizer.train(training_data)
    
    # Should still predict rare category sometimes
    assert 'Rare' in metrics['categories']
```

### Writing Integration Tests

```python
# tests/integration/test_ml_pipeline.py

import pytest
from main import process_file, enrich_transactions

def test_end_to_end_with_ml():
    """Test complete pipeline with ML categorization"""
    # Process file
    txs = process_file(Path('data/sample_statement.csv'))
    assert len(txs) > 0
    
    # Enrich with categorization
    enriched = enrich_transactions(txs)
    
    # Check all transactions have categories
    assert all(t.get('category') for t in enriched)
    
    # Check categories are reasonable
    valid_categories = ['Food & Dining', 'Shopping', 'Transport', ...]
    assert all(t.get('category') in valid_categories for t in enriched)

def test_model_performance_threshold():
    """Test model meets minimum performance requirements"""
    # Load test data with known labels
    test_data = load_test_dataset()
    
    categorizer = MLCategorizer()
    categorizer.load_model()
    
    correct = 0
    for txn in test_data:
        category, _ = categorizer.predict(txn)
        if category == txn['true_category']:
            correct += 1
    
    accuracy = correct / len(test_data)
    assert accuracy >= 0.7  # At least 70% accuracy
```

### Cross-Validation Testing

```python
def test_cross_validation():
    """Test model with K-fold cross-validation"""
    categorizer = MLCategorizer()
    training_data = load_training_data()
    
    metrics = categorizer.train(
        training_data,
        use_cross_validation=True,
        n_folds=5
    )
    
    # Check CV scores are reasonable
    assert metrics['mean_cv_score'] > 0.6
    assert all(score > 0.5 for score in metrics['cv_scores'])

def test_hyperparameter_tuning():
    """Test model finds good hyperparameters"""
    categorizer = MLCategorizer()
    training_data = load_training_data()
    
    metrics = categorizer.train(
        training_data,
        tune_hyperparameters=True
    )
    
    # Should have reasonable accuracy
    assert metrics['accuracy'] > 0.65
```

---

## 🚀 Part 3: Scaling the Model

### Current Limitations

1. **Training Data**: Only 50 samples (low!)
2. **Vocabulary Size**: 47 features (very small)
3. **Categories**: 9 categories
4. **Accuracy**: 46.7% test, 78% CV (needs improvement)

### Scaling Strategies

#### 1. **Increase Training Data** ⭐ (Most Important!)

```python
# ml/training_data_generator.py

def generate_training_data():
    """Create comprehensive training dataset"""
    
    training_samples = [
        # Food & Dining
        {'merchant_canonical': 'Swiggy', 'description': 'food delivery', 'category': 'Food & Dining'},
        {'merchant_canonical': 'Zomato', 'description': 'restaurant', 'category': 'Food & Dining'},
        {'merchant_canonical': 'Uber Eats', 'description': 'food', 'category': 'Food & Dining'},
        {'merchant_canonical': 'Dominos', 'description': 'pizza', 'category': 'Food & Dining'},
        # Add 50+ more examples
        
        # Shopping
        {'merchant_canonical': 'Amazon', 'description': 'shopping', 'category': 'Shopping'},
        {'merchant_canonical': 'Flipkart', 'description': 'electronics', 'category': 'Shopping'},
        # Add 50+ more examples
        
        # ... for all 9 categories
    ]
    
    # Save to JSONL file
    with open('ml/training_data/labeled_transactions.jsonl', 'w') as f:
        for sample in training_samples:
            f.write(json.dumps(sample) + '\n')
    
    return training_samples

# Run this once to generate data
# training_data = generate_training_data()
# Minimum: 100 samples per category = 900 samples total
```

**Best Practice**: Collect real transaction data
- Export transactions from dashboard
- Manually label incorrect predictions
- Add to training set
- Re-train weekly

#### 2. **Incremental Learning**

```python
def add_feedback(transaction: dict, correct_category: str):
    """Add user feedback to training data"""
    feedback_data = {
        'merchant_canonical': transaction.get('merchant_canonical'),
        'description': transaction.get('description'),
        'category': correct_category,  # User's correction
        'timestamp': datetime.now().isoformat()
    }
    
    # Append to training file
    with open('ml/training_data/labeled_transactions.jsonl', 'a') as f:
        f.write(json.dumps(feedback_data) + '\n')
    
    # Periodically retrain (e.g., every 10 new samples)
    if get_new_sample_count() >= 10:
        retrain_model()
```

#### 3. **Improve Feature Engineering**

```python
# ml/categorizer.py - Enhanced version

class EnhancedCategorizer:
    def __init__(self):
        # Add more sophisticated features
        self.vectorizer = TfidfVectorizer(
            max_features=5000,  # ← Increase from 1000
            ngram_range=(1, 3),  # ← Capture 3-word phrases
            min_df=2,
            stop_words='english',
            analyzer='char',  # ← Character-level for better matching
            max_df=0.95  # ← Ignore common words
        )

    def extract_features(self, transaction: dict):
        """Extract additional features"""
        text = f"{merchant} {description}"
        
        features = {
            'text': text,
            'has_amount_pattern': bool(re.search(r'\d+', description)),
            'has_card_suffix': 'XXXX' in description or 'CARD' in description,
            'has_upi_prefix': 'UPI' in description,
        }
        return features
```

#### 4. **Use Better Models**

```python
# ml/categorizer_advanced.py

from sklearn.ensemble import GradientBoostingClassifier
from sklearn.neural_network import MLPClassifier

class AdvancedCategorizer:
    """Use gradient boosting or neural networks"""
    
    def __init__(self):
        self.classifier = GradientBoostingClassifier(
            n_estimators=200,  # ← More trees
            max_depth=10,
            learning_rate=0.1,
            random_state=42
        )
        # Or use neural network:
        # self.classifier = MLPClassifier(
        #     hidden_layer_sizes=(100, 50),
        #     max_iter=500
        # )
```

#### 5. **Active Learning**

```python
def get_uncertain_predictions(transactions):
    """Find predictions with low confidence for manual labeling"""
    uncertain = []
    
    categorizer = MLCategorizer()
    for txn in transactions:
        category, confidence = categorizer.predict(txn)
        
        if confidence < 0.7:  # ← Low confidence
            uncertain.append({
                'transaction': txn,
                'predicted_category': category,
                'confidence': confidence
            })
    
    # Show these to user for labeling
    return uncertain
```

#### 6. **A/B Testing**

```python
def test_model_versions():
    """Compare old vs new model"""
    test_data = load_test_dataset()
    
    old_model = MLCategorizer(model_path='models/categorizer_v1.pkl')
    new_model = MLCategorizer(model_path='models/categorizer_v2.pkl')
    
    old_correct = sum(
        old_model.predict(txn)[0] == txn['category'] 
        for txn in test_data
    )
    
    new_correct = sum(
        new_model.predict(txn)[0] == txn['category']
        for txn in test_data
    )
    
    improvement = (new_correct - old_correct) / len(test_data)
    print(f"Improvement: {improvement:.1%}")
    
    if improvement > 0.05:  # 5% improvement
        # Deploy new model
        replace_model(new_model)
```

### Scaling Infrastructure

#### Option 1: Batch Processing (Current)
```python
# Process in batches
def process_batch(transactions):
    categories = categorizer.predict_batch(transactions)  # ✅ Efficient
    return categories
```

#### Option 2: API Server
```python
# api_server.py
from fastapi import FastAPI
from ml.categorizer import MLCategorizer

app = FastAPI()
categorizer = MLCategorizer()
categorizer.load_model()

@app.post("/predict")
async def predict(request):
    category, confidence = categorizer.predict(request.transaction)
    return {"category": category, "confidence": confidence}

# Run: uvicorn api_server:app --host 0.0.0.0 --port 8000
```

#### Option 3: Microservice
```python
# ml_service.py
class MLService:
    def __init__(self):
        self.categorizer = MLCategorizer()
        self.categorizer.load_model()
        self.batch_size = 100
    
    def predict_stream(self, transactions):
        """Process transactions as they come in"""
        results = []
        for i in range(0, len(transactions), self.batch_size):
            batch = transactions[i:i+self.batch_size]
            batch_results = self.categorizer.predict_batch(batch)
            results.extend(batch_results)
        return results
```

---

## 📊 Part 4: Monitoring & Metrics

### Track Model Performance

```python
# ml/monitoring.py

class ModelMonitor:
    def __init__(self):
        self.metrics = []
    
    def log_prediction(self, transaction, predicted, actual):
        """Log prediction for analysis"""
        self.metrics.append({
            'timestamp': datetime.now(),
            'merchant': transaction.get('merchant'),
            'predicted': predicted,
            'actual': actual,
            'correct': predicted == actual
        })
    
    def get_accuracy_trend(self):
        """Calculate accuracy over time"""
        recent = self.metrics[-100:]  # Last 100 predictions
        accuracy = sum(m['correct'] for m in recent) / len(recent)
        return accuracy
    
    def get_category_errors(self):
        """Find which categories are misclassified"""
        errors = {}
        for m in self.metrics:
            if not m['correct']:
                key = f"{m['actual']} → {m['predicted']}"
                errors[key] = errors.get(key, 0) + 1
        return sorted(errors.items(), key=lambda x: x[1], reverse=True)
```

### Dashboard Metrics

Add to your dashboard:
- **Accuracy**: % correct predictions
- **Confidence Distribution**: Histogram of confidence scores
- **Category Performance**: Accuracy per category
- **Error Examples**: Show misclassifications
- **Training Data Size**: Number of labeled samples

---

## 🎯 Action Plan

### Week 1: Testing
1. Write unit tests (from Part 2)
2. Create integration tests
3. Run cross-validation
4. Set up CI/CD to run tests automatically

### Week 2: Data Collection
1. Export 500+ transactions
2. Manually label them
3. Add to `ml/training_data/`
4. Generate comprehensive training set

### Week 3: Model Improvement
1. Retrain with 500+ samples
2. Tune hyperparameters
3. Test new model vs old
4. Deploy if better

### Week 4: Monitoring
1. Implement ModelMonitor
2. Track accuracy over time
3. Collect user feedback
4. Continuous improvement

---

## 📚 Additional Resources

- **TF-IDF**: https://en.wikipedia.org/wiki/Tf%E2%80%93idf
- **Random Forest**: https://scikit-learn.org/stable/modules/ensemble.html#forest
- **Cross-Validation**: https://scikit-learn.org/stable/modules/cross_validation.html
- **Hyperparameter Tuning**: https://scikit-learn.org/stable/modules/grid_search.html

---

## 🐛 Common Issues & Solutions

**Low accuracy (< 70%)**
- ➡️ Add more training data
- ➡️ Increase `max_features` to 2000+
- ➡️ Add more n-grams

**Memory usage too high**
- ➡️ Reduce `max_features` to 500
- ➡️ Process in smaller batches

**Slow predictions**
- ➡️ Use `predict_batch()` instead of loop
- ➡️ Limit `n_estimators` to 50

**Category imbalance**
- ➡️ Already handled with `class_weight='balanced'`
- ➡️ Add more training data for rare categories

**Model not improving**
- ➡️ Check if features are informative (use `get_feature_importance()`)
- ➡️ Try different models (Gradient Boosting, SVM)
- ➡️ Get more diverse training data

