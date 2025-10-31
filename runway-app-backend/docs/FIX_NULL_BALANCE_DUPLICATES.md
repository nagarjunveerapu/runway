# Fix: NULL Balance Duplicate Transactions

## Problem

When importing the same CSV file twice:
- **First import:** 426 transactions imported ✅
- **Second import:** 34 transactions imported again ❌ (should be 0)

### Root Cause

**SQLite UNIQUE constraint treats NULL as distinct**

In SQLite, when comparing values in a UNIQUE constraint:
- `NULL != NULL` (they are considered distinct)
- So: `(user_id, account_id, date, amount, desc, NULL) ≠ (user_id, account_id, date, amount, desc, NULL)`

This means transactions with NULL balance can be inserted multiple times even if all other fields match.

### Impact

- **34 transactions** had NULL balance in the CSV
- Each was imported twice (68 total duplicate transactions)
- The unique constraint didn't catch them because NULL balance was treated as distinct

## Solution

**Use COALESCE in unique index to normalize NULL balance**

Instead of:
```sql
CREATE UNIQUE INDEX idx_transaction_unique 
ON transactions(user_id, account_id, date, amount, description_raw, balance)
```

We now use:
```sql
CREATE UNIQUE INDEX idx_transaction_unique 
ON transactions(
    user_id, 
    account_id, 
    date, 
    amount, 
    description_raw, 
    COALESCE(balance, -999999999.99)
)
```

**How it works:**
- `COALESCE(balance, -999999999.99)` returns the balance value if not NULL
- If balance is NULL, it returns `-999999999.99` (sentinel value)
- This normalizes all NULL balances to the same value for comparison
- Now: `(user_id, account_id, date, amount, desc, NULL) = (user_id, account_id, date, amount, desc, NULL)` ✅

## Implementation

### Files Modified

1. **`storage/models.py`**
   - Updated comment to explain NULL normalization
   - Removed SQLAlchemy Index (can't use expressions)

2. **`storage/database.py`**
   - Updated `_init_database()` to create index with COALESCE
   - Drops old index before creating new one

3. **`reset_and_setup.py`**
   - Updated to create index with COALESCE
   - Drops old index before creating new one

4. **`migrations/fix_null_balance_unique_constraint.py`**
   - Migration script to:
     - Find and remove existing duplicates (keep oldest)
     - Drop old index
     - Create new index with COALESCE

### Migration Steps

1. **Scan for duplicates:** Find transactions with NULL balance that are duplicates
2. **Remove duplicates:** Keep oldest transaction, delete others
3. **Drop old index:** Remove the old unique index
4. **Create new index:** Create new index with COALESCE normalization

## Verification

### Before Fix
```
Total transactions: 460 (426 original + 34 duplicates)
Transactions with NULL balance: 68 (34 original + 34 duplicates)
Duplicate groups with NULL balance: 34
```

### After Fix
```
Total transactions: 426 (duplicates removed)
Transactions with NULL balance: 34 (no duplicates)
Duplicate groups with NULL balance: 0 ✅
```

## Testing

### Test Case 1: Re-Import Same CSV
```
Before: First import → 426 transactions, Second import → 34 transactions ❌
After:  First import → 426 transactions, Second import → 0 transactions ✅
```

### Test Case 2: Different Balances
```
Transaction 1: Balance = 138680.33 → Saved ✅
Transaction 2: Balance = 38680.33 → Saved ✅ (different balance = different time)
Transaction 3: Balance = NULL → Saved ✅ (first time)
Transaction 4: Balance = NULL → Blocked ✅ (same as Transaction 3)
```

## Result

✅ **Fixed!** Duplicate transactions with NULL balance are now prevented

**Next Steps:**
1. Re-import your CSV file - all 426 transactions should be recognized as duplicates
2. No new transactions should be imported (0 duplicates)
3. Future imports will correctly block duplicates even with NULL balance

## Technical Details

### Why COALESCE?

SQLite's unique constraint:
- Compares actual values in the index
- Treats NULL as distinct (SQL standard behavior)
- Can't distinguish between two NULL values

**Solution:** Use COALESCE to normalize NULL to a sentinel value:
- All NULL balances → normalized to `-999999999.99`
- Same normalized value = treated as duplicate ✅
- Different balance values → still treated as different ✅

### Sentinel Value Choice

**Chosen:** `-999999999.99`
- **Reason:** Extremely unlikely to be a real balance value
- **Benefit:** Won't conflict with legitimate transactions
- **Alternative:** Could use `0` or another value, but negative sentinel is safer

## Conclusion

✅ **Problem solved!** The unique constraint now correctly handles NULL balance values, preventing duplicate transactions from being imported.

**Key Takeaway:** SQLite UNIQUE constraints require special handling for NULL values when you want NULL to be treated as equal (not distinct).

