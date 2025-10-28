# Personal Finance App - Comprehensive Upgrade Plan

## Project Overview
Transform the current transaction parser POC into a full-featured personal finance application with:
- Multi-format statement ingestion (PDF, CSV)
- Canonical transaction schema
- Merchant mapping with fuzzy matching
- Data privacy vault (encrypted PII storage)
- Account Aggregator (AA) integration stub
- ML-powered transaction categorization
- SQLite storage layer
- CLI interface

## Implementation Phases

### Phase 1: Core Infrastructure (Priority 1)
1. **Project Restructuring**
   - Create new modular structure
   - Preserve existing working code
   - Setup requirements.txt with all dependencies

2. **Canonical Schema**
   - Define transaction JSON schema
   - Implement normalizer module
   - Create validation utilities

3. **Storage Layer**
   - SQLite database setup
   - SQLAlchemy models
   - Query utilities

### Phase 2: Ingestion Engine (Priority 1)
1. **CSV Parser (upgrade existing)**
   - Auto-detect delimiter and column mapping
   - Handle multiple CSV formats
   - Normalize to canonical schema

2. **PDF Parser (new)**
   - Implement pdfplumber-based parser
   - Handle table-based and text-based PDFs
   - Fallback regex extraction

3. **Normalizer**
   - Date format normalization
   - Amount parsing
   - Merchant name cleaning
   - UPI tag extraction

### Phase 3: Merchant Mapping (Priority 1)
1. **Merchant Mapper**
   - Fuzzy matching with rapidfuzz
   - Rule-based overrides
   - Confidence scoring
   - Indian merchant database

2. **Category Resolution**
   - Priority: exact > regex > fuzzy
   - Confidence thresholds
   - Merchant→Category mapping

### Phase 4: Privacy & Security (Priority 2)
1. **Privacy Vault**
   - AES-GCM encryption
   - PII storage (account numbers, PAN, phone)
   - Masking utilities
   - Key management

2. **PII Handling**
   - Reference-based storage
   - Masked output generation
   - Encryption/decryption APIs

### Phase 5: AA Integration Stub (Priority 2)
1. **AA Client Stub**
   - Sahamati flow simulation
   - Token management
   - Mock statement fetch
   - Pluggable interface

### Phase 6: ML Pipeline (Priority 2)
1. **Data Preparation**
   - Feature engineering (TF-IDF)
   - Train/test split
   - Labeled dataset handling

2. **Model Training**
   - RandomForest baseline
   - XGBoost alternative
   - Evaluation metrics
   - Model persistence

3. **Inference**
   - Model loading
   - Prediction pipeline
   - Confidence scoring
   - Hybrid (mapping + ML) categorization

### Phase 7: CLI & UX (Priority 3)
1. **CLI Interface (Click)**
   - `ingest` command
   - `train` command
   - `predict` command
   - `query` command

2. **Testing**
   - Unit tests (pytest)
   - Integration tests
   - Sample data generation

3. **Documentation**
   - Comprehensive README
   - API documentation
   - Usage examples

## New Project Structure

```
run_poc/
├── README.md                           # Comprehensive documentation
├── requirements.txt                    # All dependencies
├── requirements-dev.txt               # Dev dependencies
├── setup.py                           # Package setup
├── main.py                            # CLI entry point
├── config.py                          # Configuration
├── schema.py                          # Canonical transaction schema
│
├── ingest/                            # Statement ingestion
│   ├── __init__.py
│   ├── pdf_parser.py                 # PDF parsing (pdfplumber)
│   ├── csv_parser.py                 # CSV parsing (upgraded)
│   ├── normalizer.py                 # Data normalization
│   └── deduplicator.py              # Duplicate detection
│
├── mapping/                           # Merchant mapping
│   ├── __init__.py
│   ├── merchant_mapper.py            # Fuzzy matching
│   ├── merchant_map.csv             # Merchant database
│   └── rules.py                      # Rule-based overrides
│
├── privacy/                           # Privacy & encryption
│   ├── __init__.py
│   ├── vault.py                      # Encrypted PII storage
│   └── masking.py                    # PII masking utilities
│
├── aa/                                # Account Aggregator
│   ├── __init__.py
│   ├── aa_client_stub.py            # Sahamati stub
│   └── aa_schema.py                  # AA response schemas
│
├── ml/                                # Machine Learning
│   ├── __init__.py
│   ├── prepare.py                    # Feature engineering
│   ├── train.py                      # Model training
│   ├── infer.py                      # Inference
│   ├── evaluate.py                   # Metrics & visualization
│   └── transformer_example.py        # Optional: Hugging Face
│
├── storage/                           # Data persistence
│   ├── __init__.py
│   ├── models.py                     # SQLAlchemy models
│   └── repository.py                 # Query utilities
│
├── utils/                             # Shared utilities
│   ├── __init__.py
│   ├── date_utils.py
│   ├── amount_utils.py
│   └── validation.py
│
├── tests/                             # Test suite
│   ├── __init__.py
│   ├── test_parsers.py
│   ├── test_mapper.py
│   ├── test_vault.py
│   ├── test_ml.py
│   └── test_integration.py
│
├── sample_statements/                 # Sample data
│   ├── sample_csv_1.csv
│   ├── sample_csv_2.csv
│   └── sample_pdf_1.pdf
│
├── data/                              # Working data
│   ├── transactions.jsonl            # Canonical transactions
│   ├── transactions_labeled.jsonl    # Training data
│   └── vault.enc                     # Encrypted PII
│
├── models/                            # Trained models
│   ├── latest.pkl
│   └── vectorizer.pkl
│
└── artifacts/                         # Outputs
    ├── confusion.png
    └── metrics.json
```

## Key Design Decisions

1. **Backward Compatibility**: Preserve existing working code from `src/`
2. **Modular Architecture**: Each module is independent and testable
3. **Offline-First**: No cloud dependencies, all local
4. **Extensible**: Easy to add new parsers, merchants, categories
5. **Privacy-Focused**: PII encryption built-in
6. **Production-Ready**: Comprehensive tests, error handling, logging

## Implementation Notes

- Use existing `src/` code as foundation for `ingest/csv_parser.py`
- Leverage current merchant normalizer and classifier
- Add new capabilities incrementally
- Maintain test coverage throughout
- Document as we build

## Timeline Estimate

- Phase 1-2: Core + Ingestion (current session)
- Phase 3-4: Mapping + Privacy (current session)
- Phase 5-6: AA + ML (current session if time permits)
- Phase 7: CLI + Tests (current session)

Total: Full implementation in current session with modular, testable code.
