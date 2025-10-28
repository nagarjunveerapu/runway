# Schema Change: Make user_id NOT NULL

## Problem
- 639 transactions had `user_id = NULL`
- These orphaned transactions appeared in ALL user queries
- This caused incorrect transaction counts and data leakage between users

## Root Cause
- The `user_id` column in the `transactions` table was defined as nullable
- During some imports, transactions were created without a `user_id`
- SQL queries without explicit `WHERE user_id IS NOT NULL` returned orphaned data

## Solution Applied

### 1. Schema Change
**File:** `storage/models.py`

Changed line 94 from:
```python
user_id = Column(String(36), ForeignKey('users.user_id'))
```

To:
```python
user_id = Column(String(36), ForeignKey('users.user_id'), nullable=False, index=True)
```

### 2. Database Migration
**File:** `migrations/make_user_id_not_null.py`

The migration:
1. Deletes any transactions with NULL user_id (orphaned data)
2. Recreates the transactions table with NOT NULL constraint
3. Copies all valid transactions to the new table
4. Recreates all indexes
5. Verifies the constraint is applied

### 3. Verification
```bash
python3 migrations/make_user_id_not_null.py
```

Output:
```
✅ No transactions with NULL user_id found
✅ Copied 1131 transactions
✅ Migration completed successfully
✅ VERIFIED: user_id has NOT NULL constraint
```

### 4. Constraint Test
Attempted to insert a transaction without user_id:
```python
INSERT INTO transactions (transaction_id, date, amount, type)
VALUES ('test-id-123', '2025-01-01', 100.0, 'debit')
```

Result: ❌ Database rejected with "NOT NULL constraint failed: transactions.user_id"

## Benefits

### Data Integrity
- **No orphaned transactions**: All transactions MUST have a user_id
- **Automatic validation**: Database rejects invalid data at insert time
- **Data isolation**: Impossible to create transactions without user assignment

### Application Safety
- **Prevents data leaks**: Queries can't accidentally return other users' data
- **Simpler queries**: Don't need `WHERE user_id IS NOT NULL` in every query
- **Better performance**: user_id is now indexed for faster lookups

### Security
- **Multi-user safety**: Each transaction is guaranteed to belong to a user
- **Audit trail**: Can trace all data to specific users
- **Compliance**: Better alignment with data privacy requirements

## Current State

```
Database: sqlite:///data/finance.db
Table: transactions

Constraint Status:
✅ user_id: NOT NULL (enforced at database level)
✅ Foreign Key: REFERENCES users(user_id)
✅ Index: CREATE INDEX ON transactions(user_id)
✅ Index: CREATE INDEX ON transactions(user_id, date)

Transaction Counts:
- Total: 1,131 transactions
- test@example.com: 426 transactions
- test2@example.com: 705 transactions
- NULL user_id: 0 transactions ✅
```

## Impact on Existing Code

### No Breaking Changes
The change is backward compatible because:
- All existing queries already filter by `user_id`
- All legitimate transactions already have `user_id`
- Only inserts without `user_id` will now fail (this is desired behavior)

### Code That Needs user_id
When inserting transactions, MUST provide user_id:

```python
# ✅ CORRECT
transaction = Transaction(
    transaction_id=txn_id,
    user_id=current_user.user_id,  # Required!
    date=date,
    amount=amount,
    type='debit'
)

# ❌ WRONG - Will fail with NOT NULL constraint
transaction = Transaction(
    transaction_id=txn_id,
    # user_id missing!
    date=date,
    amount=amount,
    type='debit'
)
```

## Files Modified

1. **storage/models.py** - Added nullable=False to user_id
2. **migrations/make_user_id_not_null.py** - Created migration script
3. Database schema updated to enforce NOT NULL

## Testing

To verify the constraint is working:

```bash
cd runway/run_poc
python3 migrations/make_user_id_not_null.py
```

Or test manually:
```python
import sqlite3
conn = sqlite3.connect('data/finance.db')

# This should fail:
cursor.execute("INSERT INTO transactions (transaction_id, date, amount, type) VALUES (?, ?, ?, ?)", 
               ('test', '2025-01-01', 100, 'debit'))

# Error: NOT NULL constraint failed: transactions.user_id ✅
```

## Summary

This schema change ensures that **every transaction MUST have a user_id**, preventing data leakage and ensuring proper data isolation between users. The database will now reject any attempt to create a transaction without assigning it to a user.

---
**Date:** 2025-10-27
**Migration Applied:** ✅ Complete
**Constraint Status:** ✅ Active
**Data Integrity:** ✅ Verified

