# ML Model Quick Start Guide

## 🎯 What You Have Now

- **Model**: TF-IDF + Random Forest Classifier
- **Training Data**: 50 samples
- **Accuracy**: ~77% (cross-validation), ~47% (test)
- **Categories**: 9 categories supported

## 🚀 Quick Commands

### 1. Generate More Training Data

```bash
# Generate 50 samples per category (450 total)
python3 ml/generate_training_data.py

# Generate 100 samples per category (900 total)
python3 ml/generate_training_data.py --samples-per-category 100
```

### 2. Train the Model

```bash
# Basic training
python3 ml/train_and_evaluate.py

# With hyperparameter tuning (slower but better)
python3 ml/train_and_evaluate.py --tune

# Skip cross-validation (faster)
python3 ml/train_and_evaluate.py --no-cv
```

### 3. Evaluate the Model

```bash
# Evaluate existing model
python3 ml/train_and_evaluate.py --evaluate-only

# View results
cat ml/models/evaluation_report.json | python3 -m json.tool
```

### 4. Run Tests

```bash
# Run all ML tests
pytest tests/unit/test_ml_categorizer.py -v

# Run specific test
pytest tests/unit/test_ml_categorizer.py::TestMLCategorizer::test_model_prediction -v
```

## 📚 Full Guide

See `MODEL_GUIDE.md` for comprehensive documentation:
- How the model works
- Testing strategies
- Scaling approaches
- Monitoring & metrics

## 🔄 Typical Workflow

```bash
# 1. Generate training data
python3 ml/generate_training_data.py --samples-per-category 100

# 2. Train model
python3 ml/train_and_evaluate.py

# 3. View results
cat ml/models/evaluation_report.json | python3 -m json.tool

# 4. Test the model
python3 main.py data/Transactions.csv

# 5. Check dashboard for predictions
streamlit run dashboard.py
```

## 📈 Expected Improvements

| Action | Expected Improvement |
|--------|---------------------|
| Add 100 more training samples | +10-15% accuracy |
| Add 500 more training samples | +20-30% accuracy |
| Hyperparameter tuning | +2-5% accuracy |
| Increase max_features to 2000 | +5-10% accuracy |

## 🧪 Testing Checklist

- [ ] Unit tests pass
- [ ] Model training succeeds
- [ ] Accuracy > 70%
- [ ] Cross-validation shows stable results
- [ ] All categories represented in training data

## 🐛 Common Issues

**"No training data found"**
```bash
python3 ml/generate_training_data.py
```

**"Model not trained"**
```bash
python3 ml/train_and_evaluate.py
```

**Low accuracy**
```bash
# Generate more data
python3 ml/generate_training_data.py --samples-per-category 200

# Retrain
python3 ml/train_and_evaluate.py
```

## 📊 Next Steps

1. Collect real user feedback on predictions
2. Add feedback to training data
3. Retrain model weekly
4. Monitor accuracy trends
5. Add new categories as needed

For detailed information, see `MODEL_GUIDE.md`.

