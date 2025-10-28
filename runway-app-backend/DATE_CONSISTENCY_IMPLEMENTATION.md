# Date Consistency Implementation

## Overview
This document outlines the implementation of centralized, consistent date parsing across the entire Runway Finance application.

## Problem
The application was handling dates inconsistently across different modules:
- Database stored dates in DD/MM/YYYY format
- Backend API parsed dates inconsistently (some using date[:7], some manual parsing)
- Frontend had its own date parsing logic in DashboardModern
- Multiple helper functions (`formatMonth`, `extractMonth`, `parse_date`) doing similar things

This caused:
- Incorrect savings rate calculations
- Wrong monthly aggregations
- Inconsistent date-based queries

## Solution

### 1. Centralized Date Utility (Backend)
**File:** `runway/run_poc/utils/date_parser.py`

Provides:
- `parse_date(date_str) -> YYYY-MM-DD` - Parse any format to ISO
- `parse_month_from_date(date_str) -> YYYY-MM` - Extract month in YYYY-MM format
- `format_month_for_display(month_str) -> "Month YYYY"` - Display formatting
- `get_current_month() -> YYYY-MM` - Get current month
- `is_valid_month(month_str) -> bool` - Validate YYYY-MM format

**Supported Input Formats:**
- DD/MM/YYYY, DD/MM/YY (e.g., "15/07/2025", "15/07/25", "15/7/25")
- YYYY-MM-DD (ISO format)
- DD-MM-YYYY
- MM/DD/YYYY
- Any format detectable by Python's datetime

**Year Normalization:**
- Single digit "2" → "2025"
- Two digits "25" → "2025"
- Three digits → treated as error, defaults to "2025"
- Four digits → used as-is

### 2. Centralized Date Utility (Frontend)
**File:** `FIRE/runway-app/src/utils/dateParser.js`

Provides same API as backend:
- `parseDate(dateStr) -> YYYY-MM-DD`
- `parseMonth(dateStr) -> YYYY-MM`
- `formatMonthForDisplay(monthStr) -> "Month YYYY"`
- `getCurrentMonth() -> YYYY-MM`
- `isValidMonth(monthStr) -> bool`

### 3. Database Schema
**Files:** `runway/run_poc/storage/models.py`

The models already define dates correctly:
- `Transaction.date` - Column(String(10)) for YYYY-MM-DD
- `Transaction.month` - Column(String(7)) for YYYY-MM
- `Liquidation.date` - Column(String(10)) for YYYY-MM-DD

**Issue:** Database currently has dates in DD/MM/YYYY format from old CSV uploads.

### 4. Migration Tool
**File:** `runway/run_poc/utils/date_migration.py`

Tool to migrate existing database dates to ISO format:
```bash
cd runway/run_poc
python -m utils.date_migration --db data/finance.db
```

This will:
- Convert all `Transaction.date` to YYYY-MM-DD format
- Convert all `Liquidation.date` to YYYY-MM-DD format
- Update `Transaction.month` to YYYY-MM format

### 5. Updated Files

#### Backend:
- ✅ `runway/run_poc/api/routes/dashboard.py` - Uses `parse_month_from_date()`
- ✅ `runway/run_poc/api/routes/upload_categorize_v2.py` - Normalizes dates before saving

#### Frontend:
- ✅ `FIRE/runway-app/src/utils/helpers.js` - Uses `dateParser.parseMonth()`
- ✅ `FIRE/runway-app/src/components/Dashboard/DashboardModern.jsx` - Uses `parseMonth()`

## Migration Required

To fix existing data inconsistency:

```bash
cd runway/run_poc
python -m utils.date_migration --db data/finance.db
```

## Standard Pattern

### Date Storage (Database)
- **Format:** YYYY-MM-DD (ISO format)
- **Example:** "2025-01-15"
- **Field:** `date` (String(10))

### Month Storage (Database)
- **Format:** YYYY-MM
- **Example:** "2025-01"
- **Field:** `month` (String(7))

### Date Input (CSV/API)
- Accepts: DD/MM/YYYY, DD/MM/YY, YYYY-MM-DD, etc.
- Normalized to: YYYY-MM-DD before saving

### Month Extraction
- Always use `parse_month_from_date()` (backend) or `parseMonth()` (frontend)
- Returns: YYYY-MM format
- Used for: Monthly aggregation, filtering, grouping

## Usage Examples

### Backend (Python)
```python
from utils.date_parser import parse_date, parse_month_from_date

# Parse date to ISO format
date = parse_date("15/01/2025")  # Returns "2025-01-15"
date = parse_date("2025-01-15")   # Returns "2025-01-15"
date = parse_date("25")          # Returns "2025-01-01" (assumes current year, month)

# Extract month
month = parse_month_from_date("15/01/2025")  # Returns "2025-01"
month = parse_month_from_date("2025-01-15") # Returns "2025-01"
```

### Frontend (JavaScript)
```javascript
import { parseDate, parseMonth } from '../utils/dateParser';

// Parse date
const date = parseDate("15/01/2025");  // Returns "2025-01-15"
const date = parseDate("2025-01-15");  // Returns "2025-01-15"

// Extract month
const month = parseMonth("15/01/2025"); // Returns "2025-01"
const month = parseMonth("2025-01-15"); // Returns "2025-01"
```

## Testing

After implementation, verify:
1. ✅ All dates in database are in YYYY-MM-DD format
2. ✅ All months in database are in YYYY-MM format
3. ✅ Dashboard shows correct savings rate
4. ✅ Monthly aggregations work correctly
5. ✅ CSV uploads normalize dates correctly

## Next Steps

1. Run the migration tool to fix existing data
2. Update any remaining files that parse dates:
   - `upload_categorize.py`
   - `salary_sweep.py`
   - `parse_and_load_csv.py`
   - Any other modules that handle dates

3. Add validation to prevent future inconsistencies:
   - Add SQL CHECK constraints if using PostgreSQL
   - Add model-level validation in SQLAlchemy

## Related Files

### Core Utilities
- `runway/run_poc/utils/date_parser.py` - Backend date parsing
- `FIRE/runway-app/src/utils/dateParser.js` - Frontend date parsing
- `runway/run_poc/utils/date_migration.py` - Database migration tool

### Updated Files
- `runway/run_poc/api/routes/dashboard.py`
- `runway/run_poc/api/routes/upload_categorize_v2.py`
- `FIRE/runway-app/src/utils/helpers.js`
- `FIRE/runway-app/src/components/Dashboard/DashboardModern.jsx`

### Database Schema
- `runway/run_poc/storage/models.py`

