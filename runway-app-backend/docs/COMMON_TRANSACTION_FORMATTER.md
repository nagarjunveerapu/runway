# Common Transaction Formatter - Refactoring Complete

## Summary

Refactored duplicate code from `csv_parser.py` and `pdf_parser.py` into a common utility module `transaction_formatter.py`.

## Problem

**Duplicate code across parsers:**
- UUID generation logic duplicated
- Merchant/channel extraction duplicated
- Date normalization duplicated
- Transaction dictionary creation duplicated

**Impact:**
- Maintenance burden (fix bugs in 2 places)
- Inconsistency risk (one parser updated, other not)
- Code bloat (redundant code)

## Solution

**Created:** `ingestion/transaction_formatter.py`

**Contains:**
- `generate_transaction_id()` - UUID generation
- `detect_channel()` - Channel detection
- `extract_merchant_raw()` - Merchant extraction
- `normalize_date()` - Date normalization
- `create_transaction_dict()` - Transaction dictionary creation

## Changes Made

### 1. Created Common Module

**File:** `ingestion/transaction_formatter.py`

```python
# Common utilities for transaction formatting
- generate_transaction_id()
- detect_channel()
- extract_merchant_raw()
- normalize_date()
- create_transaction_dict()
```

### 2. Updated CSV Parser

**Before:**
```python
# 60+ lines of duplicate code:
- _gen_uuid() function
- _detect_channel() function
- _extract_merchant_raw() function
- _normalize_date() method
- Transaction dictionary creation (20+ lines)
```

**After:**
```python
from ingestion.transaction_formatter import create_transaction_dict

# Simple call:
tx = create_transaction_dict(
    description=description,
    amount=amount,
    txn_type=txn_type,
    date=date_str,
    balance=balance,
    source='CSV'
)
tx['notes'] = f'Parsed from CSV: {csv_path.name}'
```

**Code removed:** ~80 lines of duplicate code

### 3. Updated PDF Parser

**Before:**
```python
# 60+ lines of duplicate code:
- _gen_uuid_fallback() function
- _detect_channel() function
- _extract_merchant_raw() function
- _normalize_date() method
- Transaction dictionary creation (20+ lines)
```

**After:**
```python
from ingestion.transaction_formatter import create_transaction_dict

# Simple call:
tx = create_transaction_dict(
    description=description,
    amount=amount,
    txn_type=txn_type,
    date=date_str,
    balance=balance,
    source='PDF'
)
tx['notes'] = f'Parsed from PDF: {self.pdf_path.name}'
```

**Code removed:** ~80 lines of duplicate code

## Benefits

### 1. **Maintainability**
- ✅ Single source of truth for transaction formatting
- ✅ Fix bugs once, applies to both parsers
- ✅ Easier to update formatting logic

### 2. **Consistency**
- ✅ Same logic for both CSV and PDF
- ✅ Same format output guaranteed
- ✅ Same UUID generation, merchant extraction, etc.

### 3. **Code Quality**
- ✅ Reduced code duplication (~160 lines removed)
- ✅ Better separation of concerns
- ✅ Easier to test formatting logic independently

### 4. **Extensibility**
- ✅ Easy to add new parsers (Excel, etc.)
- ✅ Just import and use `create_transaction_dict()`
- ✅ Consistent format across all parsers

## Architecture

### Before (Duplicated)

```
csv_parser.py          pdf_parser.py
├─ UUID gen            ├─ UUID gen
├─ Channel detect      ├─ Channel detect
├─ Merchant extract    ├─ Merchant extract
├─ Date normalize      ├─ Date normalize
└─ Create dict         └─ Create dict
```

### After (Shared)

```
transaction_formatter.py (shared)
├─ UUID gen
├─ Channel detect
├─ Merchant extract
├─ Date normalize
└─ Create dict

csv_parser.py          pdf_parser.py
└─ import & use        └─ import & use
```

## Files Modified

1. **`ingestion/transaction_formatter.py`** (NEW)
   - Contains all shared transaction formatting logic

2. **`ingestion/csv_parser.py`**
   - Removed duplicate functions
   - Uses `create_transaction_dict()` from formatter
   - ~80 lines removed

3. **`ingestion/pdf_parser.py`**
   - Removed duplicate functions
   - Uses `create_transaction_dict()` from formatter
   - ~80 lines removed

## Testing

✅ **Verified:**
- Common formatter imports successfully
- Transaction creation works correctly
- Output format matches expected legacy format

## Usage

### For New Parsers

```python
from ingestion.transaction_formatter import create_transaction_dict

# Extract transaction data from file
description = "Transaction description"
amount = 1000.0
txn_type = "debit"  # or "credit"
date = "2025-10-06"
balance = 5000.0

# Create transaction using common formatter
tx = create_transaction_dict(
    description=description,
    amount=amount,
    txn_type=txn_type,
    date=date,
    balance=balance,
    source='EXCEL'  # or 'CSV', 'PDF', etc.
)

# Result: Properly formatted transaction dictionary
```

## Result

✅ **Refactoring complete!**

- ✅ Duplicate code eliminated (~160 lines removed)
- ✅ Single source of truth for transaction formatting
- ✅ Both CSV and PDF parsers use same logic
- ✅ Easier to maintain and extend

**Next Steps:**
- Both parsers now use shared formatting logic
- Future parsers can easily use same formatter
- Formatting logic can be updated in one place

