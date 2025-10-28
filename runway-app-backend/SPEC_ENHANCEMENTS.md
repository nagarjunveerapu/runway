# Technical Specification Enhancements

## Summary of Required Updates (Points 3-12)

This document contains all the enhancements needed for the technical specification based on the comprehensive review.

---

## 3. Config Management & Secrets ✅ (READY TO ADD)

### Add Section 2: Configuration & Secrets Management

**Insert after Section 1 (System Overview), before Technology Stack**

#### config.py
```python
"""Configuration management with python-dotenv"""
import os
from pathlib import Path
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Load .env file
env_path = Path('.env')
if env_path.exists():
    load_dotenv(env_path)
    logger.info(f"Loaded configuration from {env_path}")

class Config:
    """Application configuration"""

    # Vault & Security
    VAULT_KEY = os.getenv('VAULT_KEY')
    VAULT_KEY_FILE = os.getenv('VAULT_KEY_FILE', '.vault_key')

    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/finance.db')

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    # Feature Flags
    ENABLE_PDF_OCR = os.getenv('ENABLE_PDF_OCR', 'false').lower() == 'true'

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        if not cls.VAULT_KEY and not Path(cls.VAULT_KEY_FILE).exists():
            errors.append("VAULT_KEY not set and key file not found")
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(errors))
```

#### .env.example
```bash
# Vault Encryption (generate your own!)
VAULT_KEY=REPLACE_WITH_BASE64_KEY
VAULT_KEY_FILE=.vault_key

# Database
DATABASE_URL=sqlite:///data/finance.db

# Application Settings
LOG_LEVEL=INFO
ENABLE_AUDIT_LOGGING=true
ML_MODEL_PATH=ml/models/categorizer.pkl

# Feature Flags
ENABLE_PDF_OCR=false
ENABLE_CAMELOT=false
ENABLE_TABULA=false
```

#### Updated .gitignore
```gitignore
# Environment & Secrets (NEVER COMMIT!)
.env
.env.*
!.env.example
.vault_key
*.key
secrets.json
credentials.json
*.pem

# Database
*.db
*.sqlite3

# Logs
*.log
vault_audit.log
```

---

## 4. Enhanced ML Pipeline ✅ (READY TO ADD)

### Update ml/categorizer.py

#### Add imports:
```python
from sklearn.model_selection import StratifiedKFold, GridSearchCV
from sklearn.utils.class_weight import compute_class_weight
import json
```

#### Enhanced MLCategorizer class:

```python
class MLCategorizer:
    """ML-based transaction categorizer with cross-validation and class balancing"""

    def __init__(self, model_path: str = "ml/models/categorizer.pkl", random_seed: int = 42):
        self.model_path = Path(model_path)
        self.random_seed = random_seed  # For reproducibility
        # ... existing code ...

    def train(self, training_data: List[Dict], test_size: float = 0.2,
              use_cross_validation: bool = True, hyperparameter_search: bool = False) -> Dict[str, Any]:
        """
        Train with stratified CV, class balancing, and optional hyperparameter search

        Args:
            training_data: Labeled transactions
            test_size: Test set fraction
            use_cross_validation: Use 5-fold stratified CV
            hyperparameter_search: Run GridSearchCV
        """
        logger.info(f"Training model on {len(training_data)} transactions (seed: {self.random_seed})")

        # Prepare features
        X, y = self.prepare_features(training_data)

        # Stratified split to preserve class distribution
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=self.random_seed, stratify=y
        )

        # Compute class weights for imbalanced datasets
        class_weights = compute_class_weight(
            class_weight='balanced',
            classes=np.unique(y_train),
            y=y_train
        )
        class_weight_dict = dict(zip(np.unique(y_train), class_weights))

        logger.info(f"Class distribution: {dict(zip(*np.unique(y_train, return_counts=True)))}")
        logger.info(f"Computed class weights: {class_weight_dict}")

        if hyperparameter_search:
            # GridSearchCV for hyperparameter tuning
            param_grid = {
                'n_estimators': [50, 100, 200],
                'max_depth': [10, 20, None],
                'min_samples_split': [2, 5, 10]
            }

            base_clf = RandomForestClassifier(
                random_state=self.random_seed,
                class_weight='balanced',
                n_jobs=-1
            )

            grid_search = GridSearchCV(
                base_clf, param_grid, cv=5, scoring='f1_weighted',
                n_jobs=-1, verbose=1
            )

            grid_search.fit(X_train, y_train)
            self.classifier = grid_search.best_estimator_
            best_params = grid_search.best_params_
            logger.info(f"Best hyperparameters: {best_params}")
        else:
            # Use balanced class weights
            self.classifier = RandomForestClassifier(
                n_estimators=100,
                max_depth=20,
                min_samples_split=5,
                class_weight='balanced',  # Handle imbalanced classes
                random_state=self.random_seed,
                n_jobs=-1
            )
            self.classifier.fit(X_train, y_train)
            best_params = None

        self.is_trained = True

        # Cross-validation for robust evaluation
        if use_cross_validation:
            skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=self.random_seed)
            cv_scores = []

            for train_idx, val_idx in skf.split(X_train, y_train):
                X_cv_train, X_cv_val = X_train[train_idx], X_train[val_idx]
                y_cv_train, y_cv_val = y_train[train_idx], y_train[val_idx]

                temp_clf = RandomForestClassifier(
                    **self.classifier.get_params()
                )
                temp_clf.fit(X_cv_train, y_cv_train)
                score = temp_clf.score(X_cv_val, y_cv_val)
                cv_scores.append(score)

            cv_mean = np.mean(cv_scores)
            cv_std = np.std(cv_scores)
            logger.info(f"5-fold CV accuracy: {cv_mean:.3f} ± {cv_std:.3f}")

        # Evaluate on test set
        y_pred = self.classifier.predict(X_test)
        test_accuracy = accuracy_score(y_test, y_pred)

        logger.info(f"Test accuracy: {test_accuracy:.3f}")

        # Save model with metadata
        self._save_model_with_metadata({
            'accuracy': test_accuracy,
            'cv_scores': cv_scores if use_cross_validation else None,
            'cv_mean': cv_mean if use_cross_validation else None,
            'cv_std': cv_std if use_cross_validation else None,
            'n_training_samples': len(X_train),
            'n_test_samples': len(X_test),
            'categories': self.categories,
            'class_weights': class_weight_dict,
            'best_params': best_params,
            'random_seed': self.random_seed,
            'trained_at': datetime.utcnow().isoformat() + 'Z',
            'feature_vocabulary_size': len(self.vectorizer.vocabulary_),
            'label_mapping': {i: cat for i, cat in enumerate(self.categories)}
        })

        return {
            'test_accuracy': test_accuracy,
            'cv_scores': cv_scores if use_cross_validation else None,
            'n_training_samples': len(X_train),
            'n_test_samples': len(X_test),
            'categories': self.categories,
            'class_distribution': class_weight_dict
        }

    def _save_model_with_metadata(self, metadata: Dict):
        """Save model with rich metadata for reproducibility"""
        model_data = {
            'vectorizer': self.vectorizer,
            'classifier': self.classifier,
            'categories': self.categories,
            'is_trained': self.is_trained,
            'metadata': metadata
        }

        # Save pickle
        joblib.dump(model_data, self.model_path)

        # Save metadata JSON separately for easy inspection
        metadata_path = self.model_path.with_suffix('.json')
        with open(metadata_path, 'w') as f:
            # Convert numpy types for JSON serialization
            json_metadata = {
                k: (v.tolist() if isinstance(v, np.ndarray) else
                    float(v) if isinstance(v, (np.float32, np.float64)) else v)
                for k, v in metadata.items()
            }
            json.dump(json_metadata, f, indent=2)

        logger.info(f"Model saved to {self.model_path}")
        logger.info(f"Metadata saved to {metadata_path}")
```

---

## 5. Explicit Deduplication Logic ✅ (READY TO ADD)

### Add deduplication/detector.py

```python
"""
Transaction Deduplication with Explicit Thresholds

Rules:
1. Same date ± 1 day window
2. Exact amount match
3. Fuzzy merchant similarity ≥ 85%
4. Keep earliest transaction, flag duplicates
"""

from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from rapidfuzz import fuzz
import logging

logger = logging.getLogger(__name__)

class DeduplicationDetector:
    """Detect and merge duplicate transactions"""

    def __init__(self,
                 time_window_days: int = 1,
                 fuzzy_threshold: int = 85,
                 merge_duplicates: bool = True):
        """
        Args:
            time_window_days: Date tolerance (±N days)
            fuzzy_threshold: Merchant similarity threshold (0-100)
            merge_duplicates: If True, merge; if False, only flag
        """
        self.time_window_days = time_window_days
        self.fuzzy_threshold = fuzzy_threshold
        self.merge_duplicates = merge_duplicates

    def detect_duplicates(self, transactions: List[Dict]) -> List[Dict]:
        """
        Detect and handle duplicates

        Returns:
            List of transactions with duplicates flagged/merged
        """
        # Sort by date to process chronologically
        sorted_txns = sorted(transactions, key=lambda t: t['date'])

        processed = []
        duplicate_groups = []

        for i, txn in enumerate(sorted_txns):
            is_duplicate = False

            # Check against all previous transactions
            for j in range(max(0, i - 50), i):  # Check last 50 txns for efficiency
                prev_txn = sorted_txns[j]

                if self._is_duplicate(txn, prev_txn):
                    # Found duplicate
                    is_duplicate = True

                    if self.merge_duplicates:
                        # Merge into existing transaction
                        existing = next((t for t in processed
                                       if t['transaction_id'] == prev_txn['transaction_id']), None)
                        if existing:
                            existing['duplicate_count'] = existing.get('duplicate_count', 0) + 1
                            existing['is_duplicate'] = False  # Original is not duplicate
                            logger.debug(f"Merged duplicate: {txn['transaction_id']} into {prev_txn['transaction_id']}")
                    else:
                        # Just flag as duplicate
                        txn['is_duplicate'] = True
                        txn['duplicate_of'] = prev_txn['transaction_id']
                        txn['duplicate_count'] = 0
                        processed.append(txn)
                        logger.debug(f"Flagged duplicate: {txn['transaction_id']}")

                    break

            if not is_duplicate:
                txn['is_duplicate'] = False
                txn['duplicate_count'] = 0
                processed.append(txn)

        logger.info(f"Processed {len(transactions)} transactions, "
                   f"found {len(transactions) - len(processed)} duplicates")

        return processed

    def _is_duplicate(self, txn1: Dict, txn2: Dict) -> bool:
        """Check if two transactions are duplicates"""
        # Rule 1: Date within time window
        date1 = datetime.fromisoformat(txn1['date'])
        date2 = datetime.fromisoformat(txn2['date'])
        date_diff = abs((date1 - date2).days)

        if date_diff > self.time_window_days:
            return False

        # Rule 2: Exact amount match
        if abs(txn1.get('amount', 0) - txn2.get('amount', 0)) > 0.01:
            return False

        # Rule 3: Fuzzy merchant similarity
        merchant1 = txn1.get('merchant_raw') or txn1.get('clean_description', '')
        merchant2 = txn2.get('merchant_raw') or txn2.get('clean_description', '')

        similarity = fuzz.token_sort_ratio(merchant1, merchant2)

        if similarity < self.fuzzy_threshold:
            return False

        logger.debug(f"Duplicate found: {date_diff}d, ₹{txn1['amount']}, {similarity}% similarity")
        return True


# Usage:
detector = DeduplicationDetector(time_window_days=1, fuzzy_threshold=85, merge_duplicates=True)
clean_transactions = detector.detect_duplicates(raw_transactions)
```

---

## 6. Merchant Mapping Editor ✅ (READY TO ADD)

### Add mapping/editor.py

```python
"""
Merchant Mapping Editor and CLI Tool

Features:
- Add new mappings via CLI
- Review unmapped merchants
- Export for human review
- Track mapping metadata
"""

import pandas as pd
import csv
from pathlib import Path
from datetime import datetime
import logging
import click

logger = logging.getLogger(__name__)

class MerchantMappingEditor:
    """Manage merchant mappings"""

    def __init__(self, mapping_file: str = "mapping/merchant_map.csv"):
        self.mapping_file = Path(mapping_file)
        self.df = self._load_mappings()

    def _load_mappings(self) -> pd.DataFrame:
        """Load mappings with metadata"""
        if not self.mapping_file.exists():
            return pd.DataFrame(columns=[
                'merchant_raw', 'merchant_canonical', 'category',
                'source', 'last_updated', 'confidence'
            ])

        return pd.read_csv(self.mapping_file)

    def add_mapping(self, merchant_raw: str, merchant_canonical: str,
                   category: str, source: str = 'manual') -> bool:
        """Add new merchant mapping"""
        # Check if exists
        existing = self.df[self.df['merchant_raw'].str.lower() == merchant_raw.lower()]

        if len(existing) > 0:
            logger.warning(f"Mapping for '{merchant_raw}' already exists")
            return False

        # Add new row
        new_row = pd.DataFrame([{
            'merchant_raw': merchant_raw,
            'merchant_canonical': merchant_canonical,
            'category': category,
            'source': source,
            'last_updated': datetime.utcnow().isoformat() + 'Z',
            'confidence': 1.0
        }])

        self.df = pd.concat([self.df, new_row], ignore_index=True)
        self._save_mappings()

        logger.info(f"Added mapping: {merchant_raw} → {merchant_canonical} ({category})")
        return True

    def export_unmapped_for_review(self, transactions: List[Dict],
                                   output_file: str = "mapping/unmapped_review.csv"):
        """Export unmapped merchants for human review"""
        unmapped = []

        for txn in transactions:
            if txn.get('category') == 'Uncategorized' and txn.get('merchant_raw'):
                merchant = txn['merchant_raw']

                # Check if already in unmapped list
                if not any(u['merchant_raw'] == merchant for u in unmapped):
                    unmapped.append({
                        'merchant_raw': merchant,
                        'occurrences': sum(1 for t in transactions
                                         if t.get('merchant_raw') == merchant),
                        'suggested_canonical': merchant,  # User can edit
                        'suggested_category': 'FILL_ME',
                        'reviewed': False
                    })

        # Sort by occurrences
        unmapped_df = pd.DataFrame(unmapped)
        unmapped_df = unmapped_df.sort_values('occurrences', ascending=False)
        unmapped_df.to_csv(output_file, index=False)

        logger.info(f"Exported {len(unmapped)} unmapped merchants to {output_file}")
        logger.info("Review and edit the file, then run: finance-app import-mappings")

        return output_file

    def import_reviewed_mappings(self, review_file: str):
        """Import mappings from reviewed CSV"""
        review_df = pd.read_csv(review_file)

        reviewed = review_df[review_df['reviewed'] == True]

        for _, row in reviewed.iterrows():
            if row['suggested_category'] != 'FILL_ME':
                self.add_mapping(
                    row['merchant_raw'],
                    row['suggested_canonical'],
                    row['suggested_category'],
                    source='human_review'
                )

        logger.info(f"Imported {len(reviewed)} reviewed mappings")

    def _save_mappings(self):
        """Save mappings to CSV"""
        self.df.to_csv(self.mapping_file, index=False)


# CLI Commands
@click.group()
def mapping_cli():
    """Merchant mapping management"""
    pass

@mapping_cli.command('add')
@click.argument('merchant_raw')
@click.argument('merchant_canonical')
@click.argument('category')
def add_mapping_cmd(merchant_raw, merchant_canonical, category):
    """Add a new merchant mapping"""
    editor = MerchantMappingEditor()
    success = editor.add_mapping(merchant_raw, merchant_canonical, category)
    if success:
        click.echo(f"✓ Added: {merchant_raw} → {merchant_canonical} ({category})")
    else:
        click.echo("✗ Mapping already exists", err=True)

@mapping_cli.command('export-unmapped')
@click.argument('transactions_file')
def export_unmapped_cmd(transactions_file):
    """Export unmapped merchants for review"""
    import json

    with open(transactions_file, 'r') as f:
        transactions = [json.loads(line) for line in f]

    editor = MerchantMappingEditor()
    output = editor.export_unmapped_for_review(transactions)
    click.echo(f"✓ Exported unmapped merchants to {output}")
    click.echo("  Review the file and set reviewed=True for entries you've filled")
    click.echo("  Then run: finance-app import-mappings unmapped_review.csv")
```

---

## 7. Transaction Schema Updates ✅ (ALREADY DONE)

Schema updated with:
- ✅ `timestamp` - ISO 8601 with timezone
- ✅ `merchant_id` - SHA256 hash for fast joins
- ✅ `original_amount` / `original_currency` - Multi-currency support
- ✅ `labels` - Array for multi-label support
- ✅ `duplicate_of` / `duplicate_count` - Deduplication tracking
- ✅ `ingestion_timestamp` - When ingested

---

## 8. Testing Realism ✅ (READY TO ADD)

### Update tests/test_ml/test_categorizer.py

```python
"""
ML Categorizer Tests - Conditional on Data Volume

NOTE: ML accuracy tests are OPTIONAL and only run if sufficient labeled data exists.
For small sample datasets, we only test pipeline correctness.
"""

import pytest
from ml.categorizer import MLCategorizer

# Minimum data required for meaningful ML tests
MIN_SAMPLES_FOR_ML_TEST = 100
MIN_SAMPLES_PER_CLASS = 5

def test_feature_extraction_shape():
    """Test that feature extraction produces correct shape (always runs)"""
    categorizer = MLCategorizer()

    sample_data = [
        {'description': 'UPI Swiggy payment', 'category': 'Food'},
        {'description': 'Netflix subscription', 'category': 'Entertainment'},
    ]

    X, y = categorizer.prepare_features(sample_data)

    assert X.shape[0] == len(sample_data)
    assert y.shape[0] == len(sample_data)
    assert X.shape[1] > 0  # Has features

def test_train_pipeline_runs(sample_training_data):
    """Test that training pipeline runs without errors (always runs)"""
    categorizer = MLCategorizer()

    # Should not raise
    metrics = categorizer.train(sample_training_data, use_cross_validation=False)

    assert 'test_accuracy' in metrics
    assert categorizer.is_trained is True

@pytest.mark.skipif(
    not has_sufficient_data(),
    reason="Insufficient labeled data for ML accuracy test (need 100+ samples)"
)
def test_ml_accuracy_with_sufficient_data(large_training_dataset):
    """
    Test ML accuracy only if we have sufficient data

    This test is OPTIONAL and skipped if data is insufficient.
    Expand ml/training_data/labeled_transactions.jsonl to enable.
    """
    categorizer = MLCategorizer()
    metrics = categorizer.train(large_training_dataset)

    # With sufficient data, expect reasonable accuracy
    assert metrics['test_accuracy'] > 0.6, "Accuracy should be > 60% with good data"

    # Check cross-validation results
    if metrics.get('cv_scores'):
        cv_mean = sum(metrics['cv_scores']) / len(metrics['cv_scores'])
        assert cv_mean > 0.55, "CV accuracy should be > 55%"

def has_sufficient_data() -> bool:
    """Check if we have enough data for ML tests"""
    try:
        from ml.prepare_training_data import TrainingDataPreparer
        preparer = TrainingDataPreparer()
        data = preparer.load_labeled_data()

        if len(data) < MIN_SAMPLES_FOR_ML_TEST:
            return False

        # Check class distribution
        from collections import Counter
        categories = Counter(d['category'] for d in data)
        min_class_count = min(categories.values())

        return min_class_count >= MIN_SAMPLES_PER_CLASS
    except:
        return False
```

---

## 9. Docker CI Setup ✅ (ALREADY ADDED)

Docker support already added in main spec with:
- ✅ Dockerfile with all system deps
- ✅ docker-compose.yml
- ✅ .dockerignore

---

## 10. Performance & Scaling Guidance ✅ (READY TO ADD)

### Add Section 15: Performance & Scaling

```markdown
## 15. Performance & Scaling

### 15.1 Current Architecture Limits

**SQLite (Current):**
- Max concurrent writers: 1
- Max DB size: ~140 TB (practical limit ~1 TB)
- Good for: < 1M transactions, single user, local deployment

**When to Scale:**
- > 500K transactions
- Multiple concurrent users
- Cloud deployment
- Real-time analytics needs

### 15.2 Scaling Path

#### Phase 1: Optimize SQLite (< 500K transactions)
```python
# Add indexes
CREATE INDEX idx_date ON transactions(date);
CREATE INDEX idx_category ON transactions(category);
CREATE INDEX idx_merchant_id ON transactions(merchant_id);

# Use JSONL for raw data
transactions.to_json('data/transactions.jsonl', orient='records', lines=True)

# Batch inserts
repo.create_batch(transactions)  # vs individual inserts
```

#### Phase 2: Move to PostgreSQL (500K - 10M transactions)
```python
# Update config
DATABASE_URL=postgresql://user:pass@localhost/financedb

# Migrations with Alembic
alembic init alembic
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

#### Phase 3: Add Caching (> 1M transactions)
```python
# Redis for frequently accessed data
import redis

cache = redis.Redis(host='localhost', port=6379)

# Cache spending summaries
@cached(cache, ttl=3600)
def get_spending_by_category(date_from, date_to):
    # ...
```

#### Phase 4: Columnar Storage for Analytics (> 5M transactions)
```python
# Export to Parquet for analytics
df.to_parquet('data/transactions.parquet', compression='snappy')

# Query with DuckDB (fast OLAP)
import duckdb
result = duckdb.query("SELECT category, SUM(amount) FROM 'data/transactions.parquet' GROUP BY category")
```

#### Phase 5: Cloud Architecture (> 10M transactions)
```
┌──────────────┐
│  S3/GCS      │  ← Store raw PDFs/CSVs
└──────┬───────┘
       │
┌──────▼───────┐
│  Lambda/     │  ← Process files
│  Cloud Run   │
└──────┬───────┘
       │
┌──────▼───────┐
│  RDS/         │  ← PostgreSQL
│  Cloud SQL    │
└──────┬───────┘
       │
┌──────▼───────┐
│  BigQuery/   │  ← Analytics
│  Redshift    │
└──────────────┘
```

### 15.3 Memory Limits

**Current (In-Memory Processing):**
- PDF parsing: ~100 MB per 100-page statement
- ML training: ~500 MB for 100K samples
- Batch processing: Process 10K transactions per batch

**Optimization:**
```python
# Stream large files
for chunk in pd.read_csv('large.csv', chunksize=10000):
    process_chunk(chunk)

# Generator for memory efficiency
def stream_transactions(file_path):
    with open(file_path) as f:
        for line in f:
            yield json.loads(line)
```

### 15.4 Scaling Checklist

**500K transactions:**
- [ ] Add database indexes
- [ ] Batch processing for inserts
- [ ] Pagination for queries

**1M transactions:**
- [ ] Migrate to PostgreSQL
- [ ] Add connection pooling
- [ ] Implement caching layer

**5M transactions:**
- [ ] Partition tables by date
- [ ] Use columnar storage (Parquet)
- [ ] Separate OLTP and OLAP databases

**10M+ transactions:**
- [ ] Move to cloud (AWS/GCP)
- [ ] Use data warehouse (BigQuery/Redshift)
- [ ] Implement data lifecycle policies
```

---

## 11. Structured Logging & Error Handling ✅ (READY TO ADD)

### Add logging_config.py

```python
"""
Structured Logging Configuration

Features:
- JSON structured logs
- Request ID tracking
- Performance metrics
- Error context capture
"""

import logging
import logging.config
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import traceback

class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }

        # Add extra fields
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms

        return json.dumps(log_data)


def setup_logging(log_level: str = 'INFO', log_file: str = 'logs/app.log'):
    """Configure application logging"""

    log_dir = Path(log_file).parent
    log_dir.mkdir(exist_ok=True)

    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                '()': JSONFormatter
            },
            'simple': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'simple',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': log_level,
                'formatter': 'json',
                'filename': log_file,
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5
            }
        },
        'root': {
            'level': log_level,
            'handlers': ['console', 'file']
        }
    }

    logging.config.dictConfig(config)


class ErrorSummary:
    """Track and summarize errors"""

    def __init__(self):
        self.errors = []

    def log_error(self, error_type: str, message: str, context: Dict = None):
        """Log error with context"""
        self.errors.append({
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'type': error_type,
            'message': message,
            'context': context or {}
        })

    def get_summary(self) -> Dict:
        """Get error summary"""
        from collections import Counter

        error_types = Counter(e['type'] for e in self.errors)

        return {
            'total_errors': len(self.errors),
            'error_types': dict(error_types),
            'recent_errors': self.errors[-10:]  # Last 10 errors
        }


# Usage:
setup_logging(log_level='INFO')
logger = logging.getLogger(__name__)
logger.info("Application started", extra={'request_id': '12345'})
```

### Add CLI command for error summary

```python
@cli.command('errors')
@click.option('--last', type=int, default=100, help='Show last N errors')
def show_errors(last: int):
    """Show error summary from logs"""
    import json

    log_file = Path('logs/app.log')
    if not log_file.exists():
        click.echo("No log file found")
        return

    errors = []
    with open(log_file) as f:
        for line in f:
            try:
                log = json.loads(line)
                if log['level'] in ['ERROR', 'CRITICAL'] and 'exception' in log:
                    errors.append(log)
            except:
                continue

    errors = errors[-last:]

    click.echo(f"\nFound {len(errors)} errors:\n")

    for err in errors:
        click.echo(f"{err['timestamp']} - {err['exception']['type']}")
        click.echo(f"  {err['exception']['message']}")
        click.echo()
```

---

## 12. Compliance Checklist ✅ (READY TO ADD)

### Add Section 16: Compliance & Regulatory Checklist

```markdown
## 16. Compliance & Regulatory Checklist

### 16.1 India - Digital Personal Data Protection Act (DPDP) 2023

**Data Minimization:**
- [ ] Only collect necessary transaction data
- [ ] Justify each field in canonical schema
- [ ] Document data retention periods

**Consent Management:**
- [ ] Implement explicit consent for data processing
- [ ] Allow users to withdraw consent
- [ ] Maintain consent records with timestamps
- [ ] Provide granular consent options (e.g., ML vs storage)

**Right to Access:**
- [ ] Provide export functionality (JSONL, CSV)
- [ ] Allow users to view all stored data
- [ ] Include metadata in exports

**Right to Erasure:**
- [ ] Implement data deletion workflow
- [ ] Delete from all systems (DB, vault, logs)
- [ ] Confirm deletion to user

**Right to Correction:**
- [ ] Allow users to correct transaction categorization
- [ ] Implement manual override for ML predictions
- [ ] Track correction history

**Data Localization:**
- [ ] Store data within India (if required)
- [ ] Use Indian cloud regions (AWS ap-south-1, GCP asia-south1)
- [ ] Document data transfer policies

### 16.2 RBI DEPA (Data Empowerment and Protection Architecture)

**Account Aggregator Integration:**
- [ ] Implement Sahamati-compliant AA flow
- [ ] Support consent artifacts (digital signatures)
- [ ] Implement time-bound consent (auto-expiry)
- [ ] Support consent revocation

**Data Fiduciary Obligations:**
- [ ] Register as Data Fiduciary (if applicable)
- [ ] Implement purpose limitation
- [ ] Maintain processing records
- [ ] Conduct DPIA (Data Protection Impact Assessment)

### 16.3 GDPR (if serving EU users)

**Lawful Basis:**
- [ ] Document lawful basis for processing (consent/contract/legitimate interest)
- [ ] Implement consent management
- [ ] Provide withdrawal mechanism

**Data Protection Officer:**
- [ ] Appoint DPO (if required)
- [ ] Publish contact details

**DSAR (Data Subject Access Requests):**
- [ ] Respond within 30 days
- [ ] Provide data in machine-readable format
- [ ] Implement automated DSAR handling

### 16.4 Security & Audit

**Encryption:**
- [x] PII encrypted at rest (AES-256-GCM)
- [ ] Encryption in transit (TLS 1.3)
- [ ] Key rotation every 90 days
- [ ] Backup encryption keys securely

**Access Control:**
- [ ] Implement RBAC (Role-Based Access Control)
- [ ] Multi-factor authentication (MFA)
- [ ] Principle of least privilege
- [ ] Regular access reviews

**Audit Logging:**
- [x] Log all PII access (vault_audit.log)
- [ ] Log authentication attempts
- [ ] Log data exports
- [ ] Log consent changes
- [ ] Retain audit logs for 7 years

**Incident Response:**
- [ ] Data breach notification plan (72 hours)
- [ ] Contact details for security team
- [ ] Breach detection mechanisms
- [ ] Regular security drills

**Data Retention:**
- [ ] Define retention periods (e.g., 7 years for financial data)
- [ ] Implement auto-deletion after retention period
- [ ] Document retention policy
- [ ] Allow user-initiated deletion

### 16.5 Code Implementation

#### Consent Manager
```python
class ConsentManager:
    """Manage user consent for data processing"""

    def record_consent(self, user_id: str, purpose: str,
                      expiry_days: int = 365) -> str:
        """Record user consent"""
        consent_id = str(uuid.uuid4())
        consent = {
            'consent_id': consent_id,
            'user_id': user_id,
            'purpose': purpose,
            'granted_at': datetime.utcnow().isoformat() + 'Z',
            'expires_at': (datetime.utcnow() + timedelta(days=expiry_days)).isoformat() + 'Z',
            'revoked': False
        }
        # Store in DB
        return consent_id

    def check_consent(self, user_id: str, purpose: str) -> bool:
        """Check if user has valid consent for purpose"""
        # Query DB for active consent
        pass

    def revoke_consent(self, consent_id: str):
        """Revoke user consent"""
        # Mark as revoked, trigger data deletion
        pass
```

### 16.6 Compliance Checklist Summary

**Pre-Launch:**
- [ ] Privacy policy drafted and reviewed
- [ ] Terms of service published
- [ ] Cookie consent implemented (if web app)
- [ ] Data processing agreements signed (if using vendors)
- [ ] Security audit completed
- [ ] Penetration testing done

**Ongoing:**
- [ ] Monthly security reviews
- [ ] Quarterly access audits
- [ ] Annual DPIA review
- [ ] Regular consent renewals
- [ ] Incident response drills (quarterly)

**Documentation:**
- [ ] Data flow diagrams
- [ ] RoPA (Record of Processing Activities)
- [ ] DPIA documentation
- [ ] Vendor agreements
- [ ] Security policies
- [ ] Incident response plan
```

---

## Summary of All Enhancements

| # | Enhancement | Status | Priority |
|---|-------------|--------|----------|
| 3 | Config Management (.env, python-dotenv) | ✅ Ready | HIGH |
| 4 | ML Pipeline (CV, class balancing, metadata) | ✅ Ready | HIGH |
| 5 | Deduplication Logic (explicit thresholds) | ✅ Ready | HIGH |
| 6 | Merchant Mapping Editor (CLI tools) | ✅ Ready | MEDIUM |
| 7 | Transaction Schema Updates | ✅ Done | HIGH |
| 8 | Testing Realism (conditional ML tests) | ✅ Ready | MEDIUM |
| 9 | Docker CI Setup | ✅ Done | MEDIUM |
| 10 | Performance & Scaling Guidance | ✅ Ready | MEDIUM |
| 11 | Structured Logging & Error Handling | ✅ Ready | HIGH |
| 12 | Compliance Checklist (DPDP, RBI, GDPR) | ✅ Ready | HIGH |

All enhancements are documented and ready to be added to the main specification!
