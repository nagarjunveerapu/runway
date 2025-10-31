# Duplicate Investigation - First Import Issue

## Problem

During the first import, one transaction is being marked as duplicate even though it shouldn't be.

## Enhanced Logging Added

Now when a duplicate is detected, the logs will show:
1. **Duplicate number** (#1, #2, etc.)
2. **Date** of the duplicate transaction
3. **Amount** of the duplicate transaction
4. **Description** (first 80 chars) of the duplicate transaction
5. **Full error details** for first 5 duplicates

## How to Find the Duplicate

### Step 1: Upload CSV Again
The enhanced logging will now show exactly which transaction is flagged as duplicate.

### Step 2: Check Logs
```bash
tail -f runway-app-backend/backend.log | grep "Duplicate"
```

You'll see output like:
```
💾 TRANSACTION REPOSITORY: 🔄 Duplicate #1 detected - Date: 2025-07-15, Amount: ₹1500.0, Description: UPI/CRED/cred.utility@a/payment on/AXIS...
💾 TRANSACTION REPOSITORY: 🔄 Duplicate details: UNIQUE constraint failed...
```

### Step 3: Check CSV File
Once you know the date, amount, and description, you can:
1. Search the CSV file for that transaction
2. See if it appears multiple times
3. Check if the CSV has duplicate rows

## Possible Causes

### 1. CSV Has Duplicate Row
**Cause:** The CSV file itself contains the same transaction twice.

**Solution:** Check the CSV manually or use a script to find duplicates:
```bash
# Check for duplicate rows in CSV
sort your_file.csv | uniq -d
```

### 2. Parser Creating Duplicates
**Cause:** The CSV parser might be processing the same row twice.

**Solution:** Check parser logs for repeated processing.

### 3. Database Already Has Transaction
**Cause:** A previous import attempt partially succeeded.

**Solution:** Check database for existing transactions:
```sql
SELECT COUNT(*) FROM transactions;
```

### 4. Row-by-Row Processing Issue
**Cause:** Same transaction being inserted multiple times in the same batch.

**Solution:** Enhanced logging will show if this is happening.

## Next Steps

1. **Upload the CSV again** (after enhanced logging is active)
2. **Check the backend logs** for the duplicate transaction details
3. **Identify the specific transaction** using date, amount, description
4. **Check the CSV file** to see if that row appears multiple times
5. **Report back** with the duplicate transaction details

## Enhanced Logging Output

When a duplicate is detected, you'll see:

```
💾 TRANSACTION REPOSITORY: 🔄 Duplicate #1 detected - Date: 2025-07-15, Amount: ₹1500.0, Description: UPI/CRED/cred.utility@a/payment on/AXIS...
💾 TRANSACTION REPOSITORY: 🔄 Duplicate details: (sqlite3.IntegrityError) UNIQUE constraint failed: transactions.user_id, transactions.account_id, transactions.date, transactions.amount, transactions.description_raw
```

This will help identify:
- **Which transaction** is duplicate (date, amount, description)
- **When it happens** (transaction number in batch)
- **Why it's duplicate** (constraint violation details)

## Database Check

The database currently has:
- **425 transactions** (no duplicates in DB itself)
- **Unique constraint working** (no duplicate groups found)

This confirms the constraint is working correctly - it's catching duplicates during import as expected.

