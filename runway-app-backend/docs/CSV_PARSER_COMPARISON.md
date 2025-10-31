# CSV Parser Comparison: Legacy vs New

## Overview

This document compares the two CSV parsers available in the codebase:
1. **Legacy Parser**: `src/csv_parser.py` - Function-based parser
2. **New Parser**: `ingestion/csv_parser.py` - Class-based parser

## Key Differences

### 1. **Architecture**

#### Legacy Parser (`src/csv_parser.py`)
- **Approach**: Function-based (`parse_csv_file()`, `parse_bank_statement_csv()`)
- **Format Detection**: Reads first 5 rows (`nrows=5`) to detect format
- **Hardcoded Expectations**: Expects specific bank statement format

```python
def parse_csv_file(file_path: str) -> List[Dict[str, Any]]:
    df = pd.read_csv(file_path, encoding='utf-8-sig', nrows=5)
    csv_format = detect_csv_format(df)
    return parse_bank_statement_csv(file_path)
```

#### New Parser (`ingestion/csv_parser.py`)
- **Approach**: Class-based (`CSVParser` class)
- **Full File Reading**: Reads entire CSV file
- **Flexible**: More generic, handles various CSV formats

```python
class CSVParser:
    def parse(self, csv_path: str, encoding: str = 'utf-8') -> List[Dict]:
        # Reads full file, tries multiple encodings
        df = pd.read_csv(csv_path, encoding=enc)
```

### 2. **Encoding Handling**

#### Legacy Parser
- **Single Encoding**: Only uses `utf-8-sig` (handles BOM)
- **No Fallback**: If encoding fails, parsing fails

```python
df = pd.read_csv(file_path, encoding='utf-8-sig')
```

#### New Parser
- **Multiple Encodings**: Tries 5 different encodings
- **Automatic Fallback**: Tries next encoding if one fails
- **Better Compatibility**: Handles files from different systems

```python
encodings = [encoding, 'utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
for enc in encodings:
    try:
        df = pd.read_csv(csv_path, encoding=enc)
        break
    except Exception as e:
        continue
```

### 3. **Column Detection**

#### Legacy Parser
- **Specific Patterns**: Looks for exact column name patterns
- **Less Flexible**: Expects columns like "Transaction Remarks", "Transaction Date"
- **Hardcoded Mapping**: Column mapping is hardcoded

```python
if 'transaction date' in col_lower:
    column_mapping['transaction_date'] = col
elif 'transaction remark' in col_lower or 'remark' in col_lower:
    column_mapping['remarks'] = col
```

#### New Parser
- **Keyword Matching**: Uses flexible keyword matching
- **More Flexible**: Finds columns using multiple keywords
- **Dynamic Mapping**: Detects columns based on keywords

```python
date_keywords = ['date', 'txn date', 'transaction date', 'value date', 'posting date']
desc_keywords = ['description', 'particulars', 'narration', 'details', 'remarks']
col_map['date'] = self._find_column_by_keywords(columns_lower, date_keywords)
```

### 4. **Transaction Type Handling**

#### Legacy Parser
- **Uses**: `'transaction_type': 'withdrawal' or 'deposit'`
- **Amount Calculation**: `amount = deposit - withdrawal` (signed amount)
- **Stores Both**: Keeps both `withdrawal` and `deposit` fields

```python
amount = deposit - withdrawal  # Can be negative
tx = {
    'amount': abs(amount),
    'transaction_type': 'withdrawal' if withdrawal > 0 else 'deposit',
    'withdrawal': withdrawal,
    'deposit': deposit,
}
```

#### New Parser
- **Uses**: `'type': 'debit' or 'credit'`
- **Handles Two Cases**:
  1. Separate debit/credit columns
  2. Single amount column (uses sign to determine type)
- **Cleaner Output**: Only returns amount and type

```python
# Case 1: Separate columns
if col_map.get('debit') and col_map.get('credit'):
    return abs(float(debit_val)), 'debit'
    return abs(float(credit_val)), 'credit'

# Case 2: Single amount column
if amount < 0:
    return abs(amount), 'debit'
else:
    return abs(amount), 'credit'
```

### 5. **Output Format**

#### Legacy Parser Output
```python
{
    'id': 'uuid-here',
    'raw_remark': 'SWIGGY BANGALORE',
    'remark': 'SWIGGY BANGALORE',
    'amount': 450.0,
    'transaction_type': 'withdrawal',  # or 'deposit'
    'withdrawal': 450.0,
    'deposit': 0.0,
    'balance': 10000.0,
    'date': '2024-01-15',
    'channel': 'ONLINE',  # Detected via parser
    'merchant_raw': 'SWIGGY',  # Extracted via parser
    'merchant': None,
    'category': None,
    'recurring': False,
    'recurrence_count': 0,
    'notes': 'Parsed from CSV: file.csv',
}
```

#### New Parser Output
```python
{
    'date': '2024-01-15',  # Normalized to ISO format
    'description': 'SWIGGY BANGALORE',
    'amount': 450.0,
    'type': 'debit',  # or 'credit'
    'balance': 10000.0,
    'reference_number': None,  # If available
}
```

### 6. **Additional Features**

#### Legacy Parser
- ✅ **UUID Generation**: Generates UUID for each transaction
- ✅ **Merchant Extraction**: Uses `parser.extract_merchant_raw()` to extract merchant
- ✅ **Channel Detection**: Uses `parser.detect_channel()` to detect payment channel
- ✅ **Notes Field**: Includes parsing metadata

#### New Parser
- ✅ **Date Normalization**: Normalizes dates to ISO format (handles multiple formats)
- ✅ **Reference Number**: Extracts reference/transaction ID if available
- ✅ **Better Error Handling**: More specific error messages
- ✅ **Amount Cleaning**: Strips non-numeric characters from amounts
- ❌ **No UUID Generation**: Doesn't generate IDs
- ❌ **No Merchant Extraction**: Merchant extraction happens in service layer
- ❌ **No Channel Detection**: Channel detection happens in service layer

### 7. **Error Handling**

#### Legacy Parser
```python
try:
    # Parse logic
except Exception as e:
    logger.error(f"Failed to parse CSV file {file_path}: {e}")
    return []  # Returns empty list on error
```

#### New Parser
```python
if df is None:
    raise ValueError(f"Could not read CSV: {csv_path} - All encoding attempts failed")
if df.empty:
    raise ValueError(f"CSV file is empty: {csv_path}")
if not col_map.get('date') or not col_map.get('description'):
    raise ValueError(f"Could not detect required columns. Found columns: {list(df.columns)}")
```

## Why Legacy Parser Works Better Currently

1. **Field Names Match**: Legacy parser returns `'transaction_type'`, `'remark'`, `'raw_remark'` which match what the existing code expects
2. **Pre-processing Included**: Merchant extraction and channel detection happen in the parser
3. **UUID Generation**: Generates transaction IDs upfront
4. **Proven Compatibility**: Has been tested with actual bank statement formats

## Why New Parser Fails Currently

1. **Different Field Names**: Returns `'type'` instead of `'transaction_type'`, `'description'` instead of `'remark'`
2. **Incomplete Data**: Doesn't extract merchant/channel (relies on service layer)
3. **Missing Fields**: No UUID, no merchant extraction in parser
4. **Requires Post-Processing**: Service layer needs to transform the output format

## Recommendations

### Option 1: Fix New Parser (Recommended for Future)
- Add merchant/channel extraction in parser or adapter
- Generate UUIDs
- Match output format to what service layer expects
- Keep the improved encoding handling and date normalization

### Option 2: Keep Using Legacy Parser (Current Solution)
- Legacy parser works well with current service layer
- Better compatibility with existing CSV formats
- Already proven in production

### Option 3: Create Adapter Layer
- Keep both parsers
- Create adapter that normalizes output from both to common format
- Best of both worlds

## Current Status

- **Using**: Legacy parser (`use_legacy_csv=True`) ✅
- **Reason**: Better compatibility with existing CSV formats
- **Future**: Can migrate to new parser once output format is normalized

