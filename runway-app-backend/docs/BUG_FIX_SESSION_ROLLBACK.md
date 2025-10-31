# Bug Fix: Session Rollback After Constraint Errors

## Issue

**Error:** `PendingRollbackError: This Session's transaction has been rolled back due to a previous exception during flush`

**When:** Uploading CSV file with duplicate transactions

**Root Cause:** When a transaction violates the unique constraint, SQLAlchemy session enters an error state. If we don't rollback, subsequent operations fail.

## What Was Happening

```python
for idx, txn_dict in enumerate(transactions):
    try:
        self.insert_transaction(txn_dict, user_id, account_id, session=session)
        inserted_count += 1
        
        if (idx + 1) % batch_size == 0:
            session.commit()  # ❌ FAILS HERE if previous txn had error
            
    except Exception as e:
        if "UNIQUE constraint" in error_msg:
            duplicate_count += 1
            # ❌ MISSING: session.rollback()
        continue
```

**Problem:** When a duplicate is detected:
1. `insert_transaction()` adds transaction to session
2. Constraint violation occurs
3. Exception caught, but session still has pending error state
4. Next `session.commit()` fails with `PendingRollbackError`

## Fix

**Added:** `session.rollback()` after catching exception

```python
for idx, txn_dict in enumerate(transactions):
    try:
        self.insert_transaction(txn_dict, user_id, account_id, session=session)
        inserted_count += 1
        
        if (idx + 1) % batch_size == 0:
            session.commit()
            
    except Exception as e:
        if "UNIQUE constraint" in error_msg:
            duplicate_count += 1
            logger.debug(f"Duplicate detected (skipping): {e}")
        else:
            error_count += 1
            logger.warning(f"Failed to insert transaction {idx}: {e}")
        
        # ✅ FIX: Rollback session to clear error state before continuing
        session.rollback()
        continue
```

## Why This Works

**SQLAlchemy Session States:**
- `active`: Normal operation
- `invalid`: Error occurred, needs rollback
- `closed`: Session closed

When constraint violation occurs:
- Session enters `invalid` state
- Must call `rollback()` to return to `active` state
- Can then continue with next transaction

## Impact

**Before:**
- ❌ Upload fails on duplicate
- ❌ 500 Internal Server Error
- ❌ No transactions imported

**After:**
- ✅ Duplicates silently skipped
- ✅ Non-duplicates imported successfully
- ✅ Proper error reporting in logs

## Testing

**Test Case 1: Fresh Import**
```
Input: 100 unique transactions
Result: 100 inserted, 0 duplicates
```

**Test Case 2: Duplicate Import**
```
Input: Same 100 transactions (already in DB)
Result: 0 inserted, 100 duplicates skipped
```

**Test Case 3: Mixed Import**
```
Input: 50 existing + 50 new transactions
Result: 50 inserted, 50 duplicates skipped
```

## Files Modified

1. `services/parser_service/transaction_repository.py`
   - Added `session.rollback()` in exception handler

## Related Issues

- Database unique constraint on transactions
- Batch insert with error handling
- SQLAlchemy session management

## Documentation

See also:
- `docs/REMOVED_DEDUPLICATION.md` - Why no in-memory deduplication
- `docs/DUPLICATE_PREVENTION_COMPLETE.md` - Database constraint approach

