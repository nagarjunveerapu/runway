# Transaction Table ENUM Conversion Analysis

This document identifies columns in the `transactions` table that can be converted to PostgreSQL ENUM types for better data integrity, performance, and storage efficiency.

## Columns Suitable for ENUM Conversion

### 1. ✅ `type` - **STRONGLY RECOMMENDED**
- **Current**: `Column(String(10), nullable=False)`
- **Values**: `'debit'` or `'credit'`
- **Cardinality**: 2 values (very small, fixed set)
- **Used in**: Core business logic, filtering, analytics
- **ENUM Definition**:
```sql
CREATE TYPE transaction_type AS ENUM ('debit', 'credit');
```
- **Benefits**:
  - Enforces data integrity (no invalid values)
  - Smaller storage footprint (1 byte vs 10 bytes)
  - Better indexing performance
  - Type safety at database level

---

### 2. ✅ `source` - **RECOMMENDED** (after standardization)
- **Current**: `Column(String(50))`
- **Current Values Found in Code**:
  - `'pdf'`, `'csv'`, `'aa'`, `'manual'` (from comments)
  - `'pdf_upload'`, `'csv_upload'` (from code)
  - `'PDF'`, `'CSV'` (from code)
  - `'api'` (from schemas)
- **Cardinality**: ~5-7 values (after standardization)
- **Issue**: Values are inconsistent across codebase
- **Standardized Values** (recommended):
  - `'manual'` - Manually entered
  - `'pdf'` - PDF statement import
  - `'csv'` - CSV statement import
  - `'aa'` - Account Aggregator
  - `'api'` - API import
  - `'excel'` - Excel file import (if supported)
- **ENUM Definition**:
```sql
CREATE TYPE transaction_source AS ENUM (
    'manual',
    'pdf',
    'csv',
    'excel',
    'aa',
    'api'
);
```
- **Action Required**: Standardize existing values in database before migration
- **Benefits**: Same as `type`

---

### 3. ✅ `recurring_type` - **RECOMMENDED**
- **Current**: `Column(String(20))`
- **Values**: `'salary'`, `'emi'`, `'investment'`, `'expense'`
- **Cardinality**: 4 values (fixed set)
- **Nullability**: Nullable (not all transactions are recurring)
- **ENUM Definition**:
```sql
CREATE TYPE recurring_type AS ENUM ('salary', 'emi', 'investment', 'expense');
```
- **Benefits**: Same as `type`
- **Note**: Column is nullable, so ENUM must allow NULL

---

### 4. ⚠️ `category` - **CONDITIONALLY RECOMMENDED**
- **Current**: `Column(String(100), index=True)`
- **Predefined Values** (from `CategoryEnum`):
  - `'Food & Dining'`
  - `'Groceries'`
  - `'Shopping'`
  - `'Transport'`
  - `'Entertainment'`
  - `'Bills & Utilities'`
  - `'Healthcare'`
  - `'Education'`
  - `'Travel'`
  - `'Investment'`
  - `'Transfer'`
  - `'Salary'`
  - `'Refund'`
  - `'Other'`
  - `'Unknown'`
- **Cardinality**: ~15 predefined values
- **Considerations**:
  - Categories might expand (user-defined categories?)
  - ML model might suggest new categories
  - Already indexed as string
- **Recommendation**: 
  - **Option A**: Use ENUM if categories are fixed and won't expand
  - **Option B**: Keep as String with CHECK constraint if flexibility needed
  - **Option C**: Create `categories` lookup table (better for dynamic categories)
- **ENUM Definition** (if chosen):
```sql
CREATE TYPE transaction_category AS ENUM (
    'Food & Dining',
    'Groceries',
    'Shopping',
    'Transport',
    'Entertainment',
    'Bills & Utilities',
    'Healthcare',
    'Education',
    'Travel',
    'Investment',
    'Transfer',
    'Salary',
    'Refund',
    'Other',
    'Unknown'
);
```

---

### 5. ❌ `currency` - **NOT RECOMMENDED**
- **Current**: `Column(String(10), default='INR')`
- **Values**: ISO 4217 currency codes (e.g., 'INR', 'USD', 'EUR', etc.)
- **Cardinality**: ~180 currencies worldwide
- **Reason**: Too many possible values to use ENUM effectively
- **Recommendation**: 
  - Keep as String with CHECK constraint for format validation
  - Or use a `currencies` lookup table if you need currency metadata

---

### 6. ❌ `transaction_sub_type` - **NOT RECOMMENDED**
- **Current**: `Column(String(100))`
- **Example Values**: `'EMI/Loan'`, `'Credit Card Payment'`, etc.
- **Reason**: Too many possible values, not a fixed set
- **Recommendation**: Keep as String

---

## Migration Steps (for Recommended ENUMs)

### Step 1: Create ENUM Types
```sql
-- Connect to runway_finance database
\c runway_finance

-- Create ENUM types
CREATE TYPE transaction_type AS ENUM ('debit', 'credit');
CREATE TYPE transaction_source AS ENUM ('manual', 'pdf', 'csv', 'excel', 'aa', 'api');
CREATE TYPE recurring_type AS ENUM ('salary', 'emi', 'investment', 'expense');
```

### Step 2: Standardize Existing Data (for `source` column)
```sql
-- Standardize source values
UPDATE transactions 
SET source = CASE
    WHEN source IN ('pdf_upload', 'PDF') THEN 'pdf'
    WHEN source IN ('csv_upload', 'CSV') THEN 'csv'
    WHEN source = 'api' THEN 'api'
    WHEN source = 'manual' THEN 'manual'
    WHEN source = 'aa' THEN 'aa'
    ELSE 'manual'  -- Default for unknown values
END
WHERE source IS NOT NULL;
```

### Step 3: Add New Columns with ENUM Type
```sql
-- Add temporary columns with ENUM type
ALTER TABLE transactions 
ADD COLUMN type_new transaction_type,
ADD COLUMN source_new transaction_source,
ADD COLUMN recurring_type_new recurring_type;

-- Copy data
UPDATE transactions 
SET type_new = type::transaction_type,
    source_new = source::transaction_source,
    recurring_type_new = recurring_type::recurring_type;
```

### Step 4: Drop Old Columns and Rename
```sql
-- Drop old columns
ALTER TABLE transactions 
DROP COLUMN type,
DROP COLUMN source,
DROP COLUMN recurring_type;

-- Rename new columns
ALTER TABLE transactions 
RENAME COLUMN type_new TO type;
ALTER TABLE transactions 
RENAME COLUMN source_new TO source;
ALTER TABLE transactions 
RENAME COLUMN recurring_type_new TO recurring_type;
```

### Step 5: Update Constraints
```sql
-- Add NOT NULL constraint back for type (if it was not null)
ALTER TABLE transactions 
ALTER COLUMN type SET NOT NULL;
```

## SQLAlchemy Model Updates

```python
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ENUM

class Transaction(Base):
    # ... other columns ...
    
    # ENUM columns
    type = Column(
        SQLEnum('debit', 'credit', name='transaction_type', create_type=False),
        nullable=False
    )
    
    source = Column(
        SQLEnum('manual', 'pdf', 'csv', 'excel', 'aa', 'api', 
                name='transaction_source', create_type=False),
        nullable=True
    )
    
    recurring_type = Column(
        SQLEnum('salary', 'emi', 'investment', 'expense',
                name='recurring_type', create_type=False),
        nullable=True
    )
```

**Note**: Set `create_type=False` if ENUMs are created manually via migrations.

## Benefits Summary

| Column | Storage Savings | Performance | Data Integrity |
|-------|----------------|-------------|----------------|
| `type` | ~90% (1 byte vs 10) | ✅ Better | ✅ Enforced |
| `source` | ~95% (1 byte vs 50) | ✅ Better | ✅ Enforced |
| `recurring_type` | ~95% (1 byte vs 20) | ✅ Better | ✅ Enforced |

## Risks & Considerations

1. **Migration Complexity**: Requires downtime or careful migration strategy
2. **Value Standardization**: `source` column needs data cleanup first
3. **Future Flexibility**: Adding new ENUM values requires ALTER TYPE (can be done online in PostgreSQL 12+)
4. **SQLite Compatibility**: ENUMs not supported in SQLite; need separate migration strategy for SQLite
5. **Code Updates**: Update all Python code that sets these values to use ENUM types

## Recommendation Priority

1. **High Priority**: `type` - Core field, small cardinality, widely used
2. **Medium Priority**: `source` - Needs standardization first
3. **Medium Priority**: `recurring_type` - Less frequently used but benefits are clear
4. **Low Priority**: `category` - Consider lookup table instead for flexibility

