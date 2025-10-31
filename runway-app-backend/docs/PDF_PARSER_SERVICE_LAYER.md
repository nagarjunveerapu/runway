# PDF Parser Service Layer Integration

## Summary

PDF parser has been updated to use the same service layer architecture as CSV parser. Both now share:
- **Same parsing logic** (format conversion, enrichment, database)
- **Same service layer** (ParserService, TransactionEnrichmentService, TransactionRepository)
- **Same parser factory** (automatic file type detection)

## Changes Made

### 1. PDF Parser Output Format

**Before:** PDF parser returned simple format:
```python
{
    'date': '2025-10-06',
    'description': 'Transaction description',
    'amount': 1000.0,
    'type': 'debit',
    'balance': 5000.0
}
```

**After:** PDF parser now returns same format as CSV parser:
```python
{
    'id': 'uuid-string',
    'raw_remark': 'Transaction description',
    'remark': 'Transaction description',
    'amount': 1000.0,
    'transaction_type': 'withdrawal',
    'withdrawal': 1000.0,
    'deposit': 0.0,
    'balance': 5000.0,
    'date': '2025-10-06',
    'channel': 'UPI',
    'merchant_raw': 'Merchant Name',
    'merchant': None,
    'category': None,
    'recurring': False,
    'recurrence_count': 0,
    'notes': 'Parsed from PDF'
}
```

### 2. Added Merchant/Channel Extraction

PDF parser now extracts:
- **Merchant name** from description (same logic as CSV parser)
- **Transaction channel** (UPI, NEFT, ATM, etc.) from description

### 3. Added UUID Generation

PDF parser now generates transaction IDs:
- Uses legacy UUID generator if available
- Falls back to standard UUID if not

### 4. Service Layer Integration

**New endpoint:** `/api/v1/upload/pdf-smart` (same as `/csv-smart`)

Uses complete service layer:
- `ParserFactory` → Detects file type, creates PDF parser
- `ParserService` → Orchestrates workflow
- `TransactionEnrichmentService` → Merchant normalization, categorization
- `TransactionRepository` → Database operations

## Architecture

### Workflow (Same for CSV and PDF)

```
1. File Upload
   ↓
2. ParserFactory.detect_file_type()
   - Detects PDF vs CSV
   ↓
3. ParserFactory.create_parser()
   - Creates PDFParserAdapter or CSVParserAdapter
   ↓
4. ParserService.process_uploaded_file()
   - Saves file temporarily
   - Calls parser.parse()
   - Enriches transactions (same logic)
   - Persists to database (same logic)
   ↓
5. TransactionEnrichmentService.enrich_transactions()
   - Merchant normalization (same for both)
   - Categorization (same for both)
   ↓
6. TransactionRepository.insert_transactions_batch()
   - Database operations (same for both)
   - Handles duplicates (same for both)
```

### What's Different?

**Only file extraction differs:**
- **CSV:** Uses pandas to read CSV, detects columns, extracts data
- **PDF:** Uses pdfplumber/tabula/camelot to extract text/tables, then parses

**Everything else is identical:**
- ✅ Format conversion (to legacy format)
- ✅ Merchant extraction
- ✅ Channel detection
- ✅ UUID generation
- ✅ Enrichment logic
- ✅ Database operations
- ✅ Duplicate handling

## Files Modified

1. **`ingestion/pdf_parser.py`**
   - Added merchant/channel extraction imports
   - Updated transaction dictionary format to match CSV parser
   - Added UUID generation
   - Added withdrawal/deposit calculation

2. **`api/routes/upload_categorize_v2.py`**
   - Added `/pdf-smart` endpoint
   - Uses same service layer as `/csv-smart`
   - Same EMI/investment tracking

## Testing

### Endpoint

**PDF Upload:** `POST /api/v1/upload/pdf-smart`

**Request:**
```json
{
  "file": <PDF file>,
  "account_id": "optional-account-id"
}
```

**Response:**
```json
{
  "filename": "statement.pdf",
  "transactions_created": 150,
  "transactions_found": 150,
  "assets_created": 0,
  "emis_identified": 5,
  "duplicates_found": 0,
  "status": "success",
  "message": "Successfully imported 150 transactions"
}
```

### Verification

1. **Check logs:** Should see service layer workflow
   ```
   🏭 PARSER FACTORY: Detecting file type...
   🏭 PARSER FACTORY: Detected file type: pdf
   🏭 PARSER FACTORY: Creating PDF parser
   📊 Parsing transactions from file...
   ✨ ENRICHMENT SERVICE: Enriching transactions...
   💾 TRANSACTION REPOSITORY: Persisting to database...
   ```

2. **Check database:** Transactions should have:
   - ✅ Same format as CSV transactions
   - ✅ Merchant normalized
   - ✅ Channel detected
   - ✅ Category assigned
   - ✅ Duplicates handled (unique constraint)

## Benefits

1. **Consistency:** CSV and PDF use same logic after extraction
2. **Maintainability:** Changes to enrichment/database logic apply to both
3. **Reliability:** Same duplicate handling, same error handling
4. **Testability:** Can test enrichment/database logic once for both formats

## Next Steps

✅ **Complete!** PDF parsing now uses same service layer as CSV parsing.

Both formats now:
- ✅ Use ParserFactory for file type detection
- ✅ Use ParserService for orchestration
- ✅ Use TransactionEnrichmentService for enrichment
- ✅ Use TransactionRepository for database operations
- ✅ Return same format
- ✅ Handle duplicates the same way
- ✅ Support same features (EMI detection, investment tracking)

**Ready for testing!** 🎉

