# ENUM Migration Guide

This document tracks the ENUM migration for transaction columns and the files that need to be updated.

## ✅ Completed

1. **Database Setup** (`setup_enums.py`) - Creates ENUM types and migrates columns
2. **Models** (`storage/models.py`) - Updated to use ENUM types with PostgreSQL/SQLite compatibility
3. **Database Manager** (`storage/database.py`) - Updated to use ENUM values
4. **Analytics Routes** (`api/routes/analytics.py`) - Updated to use ENUM values

## 🔄 Files That Need ENUM Updates

### High Priority (Core Business Logic)

1. **`api/routes/assets.py`**
   - Line 64: `Transaction.type == "debit"` → `Transaction.type == TransactionType.DEBIT`

2. **`api/routes/transactions.py`**
   - Line 90: `t.type == 'credit'` → Use ENUM comparison

3. **`api/routes/upload.py`**
   - Line 304: `txn_type = txn.get('type') or ...` → Use `TransactionType.DEBIT.value`
   - Line 315: `type=txn_type` → Use `TransactionType(txn_type)` or `.value`
   - Line 323: `source='pdf_upload'` → `source=TransactionSource.PDF.value`

4. **`api/routes/upload_categorize.py`**
   - Line 143: `trans_type = "debit"` → `TransactionType.DEBIT.value`
   - Line 146: `trans_type = "credit"` → `TransactionType.CREDIT.value`
   - Line 181: `type=txn['type']` → Use ENUM
   - Line 187: `source='csv_upload'` → `TransactionSource.CSV.value`

5. **`api/routes/upload_categorize_v2.py`**
   - Line 135: `Transaction.source == 'csv_upload'` → `Transaction.source == TransactionSource.CSV`
   - Line 269: `Transaction.source == 'pdf_upload'` → `Transaction.source == TransactionSource.PDF`

6. **`api/routes/dashboard.py`**
   - Line 290: `txn.type == "credit"` → Use ENUM comparison
   - Line 321: `txn.type == "credit"` → Use ENUM comparison

7. **`api/routes/emergency_fund.py`**
   - Line 50: `Transaction.type == 'debit'` → `Transaction.type == TransactionType.DEBIT`

8. **`api/routes/fire_calculator.py`**
   - Line 73: `txn.type == "credit"` → Use ENUM comparison

9. **`api/routes/loan_prepayment.py`**
   - Line 164: `Transaction.type == 'debit'` → `Transaction.type == TransactionType.DEBIT`
   - Line 221-222: `t.type == 'credit'` and `t.type == 'debit'` → Use ENUM comparison

10. **`api/routes/net_worth_calculator.py`**
    - Line 262-264: `txn.type == 'credit'` and `txn.type == 'debit'` → Use ENUM comparison

11. **`api/routes/salary_sweep.py`**
    - Line 140: `t.type == 'credit'` → Use ENUM comparison
    - Line 190: `t.type == 'debit'` → Use ENUM comparison

### Medium Priority (Services)

12. **`services/credit_card_service/credit_card_service.py`**
    - Line 294: `Transaction.type == 'credit'` → `Transaction.type == TransactionType.CREDIT`

13. **`services/parser_service/parser_service.py`**
    - Line 226: `source = 'pdf_upload' if ... else 'csv_upload'` → Use `TransactionSource.PDF.value` / `TransactionSource.CSV.value`

14. **`ingestion/pdf_parser.py`**
    - Multiple lines with `txn_type = 'debit'` / `txn_type = 'credit'` → Use `TransactionType.DEBIT.value` / `TransactionType.CREDIT.value`
    - Line 411, 548: `source='PDF'` → `source=TransactionSource.PDF.value`

15. **`ingestion/csv_parser.py`**
    - Line 185: `source='CSV'` → `source=TransactionSource.CSV.value`

16. **`ingestion/transaction_formatter.py`**
    - Multiple lines with `txn_type = 'debit'` / `txn_type = 'credit'` → Use ENUM

### Low Priority (Utilities, Tests, Docs)

17. **`parse_and_load_csv.py`**
    - Line 202, 206, 209: `trans_type = "debit"` / `trans_type = "credit"` → Use ENUM

18. **`direct_upload.py`**
    - Line 70: `txn_type = txn.get('type', 'debit')` → Use ENUM
    - Line 87: `source='pdf_upload'` → `TransactionSource.PDF.value`

19. **`load_sample_data_to_db.py`**
    - Line 69: `type="credit" if ... else "debit"` → Use ENUM
    - Line 74: `source="manual"` → `TransactionSource.MANUAL.value`

20. **Test files** (`tests/`, `test_*.py`)
    - Update all test fixtures and assertions to use ENUM values

## Usage Pattern

### For Assignments (Creating Transactions)

```python
from storage.models import TransactionType, TransactionSource, TransactionCategory, RecurringType

# When creating a transaction
transaction = Transaction(
    type=TransactionType.DEBIT.value,  # Use .value for string value
    source=TransactionSource.PDF.value,
    category=TransactionCategory.FOOD_DINING.value,
    recurring_type=RecurringType.SALARY.value  # if applicable
)
```

### For Comparisons (Querying)

```python
# When filtering queries
query.filter(Transaction.type == TransactionType.DEBIT)  # Direct ENUM comparison works in SQLAlchemy

# When checking in Python code (handles both ENUM and string for backward compatibility)
txn_type_value = txn.type.value if hasattr(txn.type, 'value') else txn.type
if txn_type_value == TransactionType.DEBIT.value:
    # Handle debit
```

### For String Values (API/JSON Serialization)

```python
# When returning JSON or string values
type_str = txn.type.value if hasattr(txn.type, 'value') else txn.type
# or simply use the enum value directly
type_str = TransactionType.DEBIT.value  # Returns "debit"
```

## Helper Function

You can use this helper for backward-compatible comparisons:

```python
def get_enum_value(value, enum_class):
    """Get enum value, handling both ENUM and string types"""
    if hasattr(value, 'value'):
        return value.value
    elif isinstance(value, str):
        # Try to find matching enum value
        for enum_item in enum_class:
            if enum_item.value == value:
                return value
    return value

# Usage
txn_type = get_enum_value(txn.type, TransactionType)
if txn_type == TransactionType.DEBIT.value:
    # ...
```

## Running the Migration

1. **Run the database migration script:**
   ```bash
   cd runway-app-backend
   python3 setup_enums.py
   ```

2. **Verify ENUM types are created:**
   ```sql
   -- In psql
   \dT+ transaction_type
   \dT+ transaction_source
   \dT+ recurring_type
   \dT+ transaction_category
   ```

3. **Update business logic files** (see list above)

4. **Test thoroughly** - especially:
   - Creating new transactions
   - Querying transactions by type/category/source
   - Filtering and analytics
   - Importing from CSV/PDF

## Notes

- The model uses `_get_enum_column_type()` to automatically detect PostgreSQL vs SQLite
- For PostgreSQL: Uses PostgresEnum (created via setup_enums.py)
- For SQLite: Falls back to SQLEnum (string with enum constraints)
- All comparisons should be backward-compatible (handle both ENUM objects and strings)

