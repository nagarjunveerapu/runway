# Parser Refactoring Complete - Separation of Concerns

## Summary

Refactored CSV and PDF parsers to follow single responsibility principle:
- **Parsers**: Only extract raw data from files
- **Transaction Formatter**: All formatting, parsing, and business logic
- **Transaction Repository**: Database operations (already implemented)

## Problem

**Code duplication across parsers:**
- Column keyword definitions duplicated (lines 198-199, 240-241 in CSV parser)
- Column detection logic duplicated
- Amount extraction logic duplicated (lines 253-301)
- Amount parsing/cleaning logic duplicated
- Balance extraction logic duplicated

**Violation of Single Responsibility Principle:**
- Parsers were doing: file parsing + column detection + amount extraction + formatting
- Should only do: Extract raw data from files

## Solution

**Created comprehensive utilities in `transaction_formatter.py`:**

1. **Column Keyword Definitions** (Constants)
   - `DATE_KEYWORDS`, `DESC_KEYWORDS`, `DEBIT_KEYWORDS`, `CREDIT_KEYWORDS`
   - `AMOUNT_KEYWORDS`, `BALANCE_KEYWORDS`, `REF_KEYWORDS`

2. **Column Detection Utilities**
   - `detect_columns()` - Detects all columns from column names
   - `find_column_by_keywords()` - Finds single column by keywords

3. **Amount Extraction Utilities**
   - `parse_amount_string()` - Parses amount strings to float
   - `extract_amount_and_type()` - Extracts amount and determines type
   - `extract_balance()` - Extracts balance from row data

4. **Transaction Formatting** (Already existed)
   - `create_transaction_dict()` - Creates formatted transaction

## Changes Made

### 1. Transaction Formatter (`ingestion/transaction_formatter.py`)

**Added:**
```python
# Column keyword constants
DATE_KEYWORDS = ['date', 'txn date', 'transaction date', ...]
DEBIT_KEYWORDS = ['debit', 'withdrawal', 'dr', ...]
CREDIT_KEYWORDS = ['credit', 'deposit', 'cr', ...]
# ... etc

# Column detection
def detect_columns(columns: List[str]) -> Dict[str, Optional[str]]

# Amount parsing
def parse_amount_string(amount_str: str) -> Optional[float]

# Amount extraction
def extract_amount_and_type(row_data, col_map) -> Tuple[amount, type, withdrawal, deposit]

# Balance extraction
def extract_balance(row_data, col_map) -> Optional[float]
```

**Code added:** ~200 lines of common utilities

### 2. CSV Parser (`ingestion/csv_parser.py`)

**Before:**
```python
# 80+ lines of duplicate code:
- Column keyword definitions
- _detect_columns() method (40 lines)
- _extract_amount_and_type_legacy() method (80 lines)
- Manual amount parsing (re.sub, float conversion)
- Manual balance extraction
```

**After:**
```python
# Import common utilities
from ingestion.transaction_formatter import (
    detect_columns,
    extract_amount_and_type,
    extract_balance,
    create_transaction_dict
)

# Parser's responsibility: Extract raw data only
def _detect_columns(self, df):
    return detect_columns(list(df.columns))  # Delegates to formatter

# Use common utilities
amount, txn_type, withdrawal, deposit = extract_amount_and_type(row, col_map)
balance = extract_balance(row, col_map)
tx = create_transaction_dict(...)
```

**Code removed:** ~140 lines of duplicate logic

### 3. PDF Parser (`ingestion/pdf_parser.py`)

**Before:**
```python
# 60+ lines of duplicate code:
- Manual column detection with hardcoded keywords
- Manual amount parsing
- Manual balance extraction
- _find_column() helper method
```

**After:**
```python
# Import common utilities
from ingestion.transaction_formatter import (
    detect_columns,
    extract_amount_and_type,
    extract_balance,
    create_transaction_dict
)

# Use common column detection
col_map = detect_columns(list(df.columns))

# Use common amount extraction
amount, txn_type, withdrawal, deposit = extract_amount_and_type(row, col_map)
balance = extract_balance(row, col_map)
tx = create_transaction_dict(...)
```

**Code removed:** ~60 lines of duplicate logic

## Architecture

### Before (Mixed Responsibilities)

```
CSV Parser                 PDF Parser
├─ File parsing           ├─ File parsing
├─ Column keywords        ├─ Column keywords
├─ Column detection       ├─ Column detection
├─ Amount extraction      ├─ Amount extraction
├─ Amount parsing         ├─ Amount parsing
├─ Balance extraction     ├─ Balance extraction
└─ Transaction format     └─ Transaction format
```

### After (Separation of Concerns)

```
CSV Parser                 PDF Parser
└─ File parsing           └─ File parsing
    └─ Extract raw data       └─ Extract raw data
         │                          │
         └──────────────────────────┘
                    │
                    ▼
         Transaction Formatter
         ├─ Column keywords (constants)
         ├─ Column detection
         ├─ Amount parsing
         ├─ Amount extraction
         ├─ Balance extraction
         └─ Transaction formatting
                    │
                    ▼
         Transaction Repository
         └─ Database operations
```

## Responsibility Separation

### 1. Parser's Responsibility (CSV/PDF)
✅ **ONLY:** Extract raw data from files
- Read file content
- Extract rows/records
- Pass data to formatter

❌ **NOT:** Column detection, amount parsing, formatting

### 2. Transaction Formatter's Responsibility
✅ **ONLY:** Business logic and formatting
- Column detection
- Amount parsing and extraction
- Transaction type determination
- Transaction formatting (legacy format)

❌ **NOT:** File I/O, database operations

### 3. Transaction Repository's Responsibility
✅ **ONLY:** Database operations
- Insert transactions
- Handle duplicates
- Query transactions

❌ **NOT:** File parsing, formatting logic

## Benefits

### 1. **Single Responsibility Principle**
- ✅ Each module has one clear responsibility
- ✅ Easier to understand and maintain
- ✅ Changes to logic don't affect file parsing

### 2. **DRY (Don't Repeat Yourself)**
- ✅ ~200 lines of duplicate code eliminated
- ✅ Single source of truth for all logic
- ✅ Fix bugs once, applies everywhere

### 3. **Consistency**
- ✅ Same column detection logic for CSV and PDF
- ✅ Same amount parsing logic
- ✅ Same transaction format guaranteed

### 4. **Testability**
- ✅ Parser tests: Focus on file extraction
- ✅ Formatter tests: Focus on logic
- ✅ Repository tests: Focus on database

### 5. **Extensibility**
- ✅ New parser (Excel, etc.): Just extract raw data
- ✅ All formatting logic reused automatically
- ✅ Easy to add new column keywords

## Files Modified

1. **`ingestion/transaction_formatter.py`** (+200 lines)
   - Added column keyword constants
   - Added column detection utilities
   - Added amount parsing utilities
   - Added amount extraction utilities

2. **`ingestion/csv_parser.py`** (-140 lines)
   - Removed duplicate column detection
   - Removed duplicate amount extraction
   - Uses common utilities

3. **`ingestion/pdf_parser.py`** (-60 lines)
   - Removed duplicate column detection
   - Removed duplicate amount parsing
   - Uses common utilities

## Code Reduction

- **Before:** ~200 lines of duplicate code
- **After:** ~0 lines of duplicate code
- **Net:** ~200 lines moved to common module
- **Result:** Single source of truth for all parsing logic

## Usage Example

### New Parser (e.g., Excel)

```python
from ingestion.transaction_formatter import (
    detect_columns,
    extract_amount_and_type,
    extract_balance,
    create_transaction_dict
)

class ExcelParser:
    def parse(self, excel_path):
        # Parser's responsibility: Extract raw data
        df = pd.read_excel(excel_path)
        
        # Use common column detection
        col_map = detect_columns(list(df.columns))
        
        transactions = []
        for _, row in df.iterrows():
            # Extract raw data
            date_str = str(row[col_map['date']])
            description = str(row[col_map['description']])
            
            # Use common amount extraction
            amount, txn_type, withdrawal, deposit = extract_amount_and_type(row, col_map)
            balance = extract_balance(row, col_map)
            
            # Use common formatter
            tx = create_transaction_dict(
                description=description,
                amount=amount,
                txn_type=txn_type,
                date=date_str,
                balance=balance,
                source='EXCEL'
            )
            transactions.append(tx)
        
        return transactions
```

**New parser implementation:** ~30 lines (vs ~150 lines before)

## Testing

✅ **Verified:**
- Common utilities import successfully
- Column detection works correctly
- Amount parsing works correctly
- Amount extraction works correctly
- Both CSV and PDF parsers use common utilities
- Output format consistent

## Result

✅ **Refactoring complete!**

- ✅ ~200 lines of duplicate code eliminated
- ✅ Single responsibility principle enforced
- ✅ Clear separation of concerns
- ✅ Easier to maintain and extend
- ✅ Consistent behavior across all parsers

**Next Steps:**
- All parsers now follow single responsibility
- All formatting logic in one place
- Easy to add new parsers
- Easy to update formatting logic

