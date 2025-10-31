# Service Layer Architecture - Parser Service

## Overview

This document describes the new service layer architecture for file parsing, which separates concerns and improves testability, maintainability, and extensibility.

## Architecture Components

### 1. ParserFactory (Factory Pattern)
**Location**: `services/parser_service/parser_factory.py`

**Purpose**: Factory pattern for file type detection and parser creation.

**Features**:
- Detects file type from filename and/or MIME content type
- Creates appropriate parser instance (PDF, CSV, or Legacy CSV)
- Validates file types before processing
- Supports bank-specific parsers via `bank_name` parameter

**Usage**:
```python
from services.parser_service import ParserFactory

# Detect file type
file_type = ParserFactory.detect_file_type("statement.pdf", "application/pdf")
# Returns: 'pdf'

# Validate file type
is_valid = ParserFactory.validate_file_type("statement.csv")
# Returns: True

# Create parser
parser = ParserFactory.create_parser(
    file_path="/tmp/statement.pdf",
    filename="statement.pdf",
    content_type="application/pdf",
    bank_name="HDFC Bank"  # Optional
)
```

### 2. ParserService (Business Logic Layer)
**Location**: `services/parser_service/parser_service.py`

**Purpose**: Orchestrates the complete parsing workflow.

**Features**:
- Coordinates file type detection, parsing, enrichment, and persistence
- Handles temporary file management
- Provides both full processing and parse-only modes
- Separates business logic from route handlers and database operations

**Workflow**:
1. Validate file type
2. Save file temporarily
3. Detect file type and create parser (factory pattern)
4. Parse transactions
5. Enrich transactions (merchant normalization, categorization)
6. Detect and handle duplicates
7. Persist to database
8. Cleanup temporary file

**Usage**:
```python
from services.parser_service import ParserService
from storage.database import DatabaseManager
from fastapi import UploadFile

db_manager = DatabaseManager(database_url)
parser_service = ParserService(db_manager=db_manager)

# Process uploaded file end-to-end
result = parser_service.process_uploaded_file(
    file=upload_file,
    user_id="user-123",
    account_id="account-456",  # Optional
    bank_name="HDFC Bank",     # Optional
    use_legacy_csv=False       # Optional
)

# Parse only (no enrichment or database operations)
transactions = parser_service.parse_file_only(
    file_path="/tmp/statement.pdf",
    filename="statement.pdf",
    content_type="application/pdf"
)
```

### 3. TransactionRepository (Data Access Layer)
**Location**: `services/parser_service/transaction_repository.py`

**Purpose**: Encapsulates all database operations related to transactions.

**Features**:
- Single transaction insertion
- Batch transaction insertion with progress tracking
- Support for both dict and CanonicalTransaction inputs
- Handles different field names from different parsers (PDF vs CSV)
- Transaction rollback on errors

**Usage**:
```python
from services.parser_service import TransactionRepository
from storage.database import DatabaseManager

db_manager = DatabaseManager(database_url)
repository = TransactionRepository(db_manager)

# Insert single transaction
txn = {
    'date': '2024-01-01',
    'amount': 5000.0,
    'type': 'debit',
    'description': 'SWIGGY',
    'merchant_canonical': 'Swiggy',
    'category': 'Food & Dining'
}
transaction = repository.insert_transaction(
    txn,
    user_id="user-123",
    account_id="account-456"
)

# Insert batch
transactions = [txn1, txn2, txn3]
inserted_count = repository.insert_transactions_batch(
    transactions,
    user_id="user-123",
    account_id="account-456",
    batch_size=100
)

# From CanonicalTransaction
from schema import CanonicalTransaction
canonical_txns = [CanonicalTransaction(...), ...]
inserted_count = repository.insert_from_canonical(
    canonical_txns,
    user_id="user-123"
)
```

### 4. TransactionEnrichmentService (Business Logic Layer)
**Location**: `services/parser_service/transaction_enrichment_service.py`

**Purpose**: Handles transaction enrichment logic.

**Features**:
- Merchant normalization using MerchantNormalizer
- Transaction categorization using rule-based classifier
- Duplicate detection and handling using DeduplicationDetector
- Handles different field names from different parsers
- Complete enrichment pipeline (enrich + deduplicate)

**Usage**:
```python
from services.parser_service import TransactionEnrichmentService

service = TransactionEnrichmentService()

# Enrich transactions
transactions = [
    {'description': 'SWIGGY BANGALORE', 'amount': 450.0}
]
enriched = service.enrich_transactions(transactions)

# Detect and handle duplicates
cleaned, stats = service.detect_and_handle_duplicates(enriched)

# Complete pipeline
cleaned, stats = service.enrich_and_deduplicate(transactions)
```

## Migration from Old Architecture

### Old Approach
```python
# Route handler contained all logic
@router.post("/csv")
async def upload_csv(file: UploadFile = File(...)):
    # Parse
    transactions = parse_csv_file(temp_file)
    
    # Enrich
    merchant_norm = MerchantNormalizer()
    for txn in transactions:
        merchant_canonical, _ = merchant_norm.normalize(...)
        category = rule_based_category(...)
    
    # Deduplicate
    dedup = DeduplicationDetector(...)
    clean_transactions = dedup.detect_duplicates(transactions)
    
    # Database
    db = DatabaseManager(...)
    db.insert_transactions_batch(...)
```

### New Approach
```python
# Route handler delegates to service layer
@router.post("/csv")
async def upload_csv(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    parser_service: ParserService = Depends(get_parser_service)
):
    result = parser_service.process_uploaded_file(
        file=file,
        user_id=current_user.user_id
    )
    return FileUploadResponse(**result)
```

## Benefits

1. **Separation of Concerns**: Business logic is separated from route handlers and database operations
2. **Testability**: Each layer can be tested independently with mocks
3. **Maintainability**: Changes to business logic don't affect route handlers or database layer
4. **Extensibility**: Easy to add new parsers or enrichment steps
5. **Reusability**: Services can be used from multiple routes or other services
6. **Factory Pattern**: Easy to add new file types or parsers without modifying existing code

## Backward Compatibility

### Existing Routes
- Original `api/routes/upload.py` routes remain unchanged
- New service-based routes are available in `api/routes/upload_v2_service.py`
- Both can coexist during migration period

### Migration Path
1. **Phase 1**: New service layer created alongside existing routes (Current state)
2. **Phase 2**: Update existing routes to use service layer (Optional)
3. **Phase 3**: Remove duplicate routes and consolidate (Future)

## Testing

Test files are located in `tests/`:
- `test_parser_factory.py`: Tests for ParserFactory
- `test_transaction_repository.py`: Tests for TransactionRepository
- `test_transaction_enrichment_service.py`: Tests for TransactionEnrichmentService
- `test_parser_service.py`: Tests for main ParserService

Run tests:
```bash
pytest tests/test_parser_factory.py -v
pytest tests/test_transaction_repository.py -v
pytest tests/test_transaction_enrichment_service.py -v
pytest tests/test_parser_service.py -v
```

## Implications

### UI/Frontend
✅ **No changes required** - API endpoints remain the same (same URL, same request/response format)

### Existing Test Cases
⚠️ **May need updates** - Tests that directly test route handlers may need to be updated if routes are migrated to use service layer. However, existing tests should still pass since old routes remain.

### Performance
✅ **No negative impact** - Service layer adds minimal overhead (mostly function calls), and may improve performance through better code organization and potential caching opportunities.

### Database Operations
✅ **No schema changes** - Repository layer uses existing database schema and models.

## Adding New Parsers

To add a new parser type (e.g., Excel):

1. **Create Parser Class** (e.g., `ExcelParser`)
2. **Create Adapter**:
   ```python
   class ExcelParserAdapter(ParserInterface):
       def __init__(self, bank_name: Optional[str] = None):
           self.parser = ExcelParser(bank_name=bank_name)
       
       def parse(self, file_path: str) -> List[Dict]:
           return self.parser.parse(file_path)
   ```
3. **Update ParserFactory**:
   ```python
   def detect_file_type(...):
       if 'excel' in mime_type or filename.endswith('.xlsx'):
           return 'excel'
   
   def create_parser(...):
       if file_type == 'excel':
           return ExcelParserAdapter(bank_name=bank_name)
   ```

## File Structure

```
services/
  parser_service/
    __init__.py                    # Module exports
    parser_factory.py              # Factory pattern for parsers
    parser_service.py              # Main service orchestration
    transaction_repository.py      # Data access layer
    transaction_enrichment_service.py  # Enrichment business logic

api/
  routes/
    upload.py                      # Original routes (unchanged)
    upload_v2_service.py           # New service-based routes

tests/
  test_parser_factory.py
  test_transaction_repository.py
  test_transaction_enrichment_service.py
  test_parser_service.py
```

## Dependencies

The service layer depends on:
- `ingestion.pdf_parser`: PDFParser
- `ingestion.csv_parser`: CSVParser
- `src.csv_parser`: Legacy CSV parser (for backward compatibility)
- `storage.database`: DatabaseManager
- `storage.models`: Transaction model
- `schema`: CanonicalTransaction
- `deduplication.detector`: DeduplicationDetector
- `src.merchant_normalizer`: MerchantNormalizer
- `src.classifier`: rule_based_category
- `config`: Config

All dependencies are existing components - no new dependencies introduced.

