# Balance Added to Unique Constraint

## Problem

Two legitimate transactions were incorrectly identified as duplicates:
- **Date:** 2025-10-06
- **Amount:** ₹100000.0
- **Description:** TRF/TRINANYANI REALTORS PVT LTD/ICI...
- **Balance 1:** ₹138680.33
- **Balance 2:** ₹38680.33

These are **separate transactions** that happened at different times in the same day, but the unique constraint was too strict and blocked the second one.

## Solution

**Added balance to unique constraint** to differentiate transactions that occur at different times in the day.

### Old Constraint
```sql
CREATE UNIQUE INDEX idx_transaction_unique 
ON transactions(user_id, account_id, date, amount, description_raw)
```

**Problem:** Blocks legitimate transactions that happen multiple times in a day with same amount/description but different balances.

### New Constraint
```sql
CREATE UNIQUE INDEX idx_transaction_unique 
ON transactions(user_id, account_id, date, amount, description_raw, balance)
```

**Solution:** Allows same transaction with different balances (indicating different times).

## How Balance Differentiates Transactions

### Example: Two Separate Transactions Same Day

**Transaction 1 (Morning):**
- Date: 2025-10-06
- Amount: ₹100000
- Description: TRF/TRINANYANI REALTORS PVT LTD/ICI...
- Balance AFTER: ₹138680.33
- Balance BEFORE: ₹238680.33

**Transaction 2 (Afternoon):**
- Date: 2025-10-06
- Amount: ₹100000
- Description: TRF/TRINANYANI REALTORS PVT LTD/ICI...
- Balance AFTER: ₹38680.33
- Balance BEFORE: ₹138680.33

**Result:** Both are saved because they have different balances!

## Behavior

### Transactions with Balance
- ✅ **Different balances** → Saved separately (different times)
- ❌ **Same balance** → Blocked as duplicate (same time)

### Transactions without Balance (NULL)
- ❌ **Both NULL** → Blocked as duplicate (can't differentiate)
- ✅ **One NULL, one value** → Saved separately (different times)

## Real-World Scenarios

### Scenario 1: Multiple Payments Same Day
```
Payment 1: ₹5000 at 9 AM → Balance: ₹95000
Payment 2: ₹5000 at 6 PM → Balance: ₹90000
```
**Result:** ✅ Both saved (different balances indicate different times)

### Scenario 2: True Duplicate
```
Import 1: ₹5000 → Balance: ₹95000
Import 2: ₹5000 → Balance: ₹95000 (same balance = same time)
```
**Result:** ❌ Second import blocked (same balance = duplicate)

### Scenario 3: Transactions without Balance
```
Transaction 1: ₹5000 → Balance: NULL
Transaction 2: ₹5000 → Balance: NULL
```
**Result:** ❌ Second transaction blocked (can't differentiate without balance)

## Migration

**Migration script:** `migrations/add_balance_to_unique_constraint.py`

**What it does:**
1. Drops old unique index
2. Creates new unique index with balance
3. Verifies constraint creation
4. Checks for violations

**Run with:**
```bash
python3 migrations/add_balance_to_unique_constraint.py
```

## Files Modified

1. **`storage/models.py`** - Added balance to unique index definition
2. **`storage/database.py`** - Updated constraint creation on init
3. **`reset_and_setup.py`** - Updated constraint creation during setup
4. **`migrations/add_balance_to_unique_constraint.py`** - Migration script

## Testing

### Test Case 1: Same Day, Different Balances
```
Transaction 1: Date=2025-10-06, Amount=₹100000, Balance=₹138680.33
Transaction 2: Date=2025-10-06, Amount=₹100000, Balance=₹38680.33
Expected: ✅ Both saved
```

### Test Case 2: Same Day, Same Balance
```
Transaction 1: Date=2025-10-06, Amount=₹100000, Balance=₹138680.33
Transaction 2: Date=2025-10-06, Amount=₹100000, Balance=₹138680.33
Expected: ❌ Second blocked as duplicate
```

### Test Case 3: Re-Import
```
First import: 426 transactions → 425 saved, 1 duplicate
Second import: 426 transactions → 0 saved, 426 duplicates
Expected: ✅ Still blocks true duplicates
```

## Trade-offs

### Benefits
- ✅ Handles legitimate same-day transactions
- ✅ Uses balance as time differentiator
- ✅ More accurate duplicate detection

### Considerations
- ⚠️ Transactions without balance still blocked if all other fields match
- ⚠️ Same balance = treated as duplicate (might be too strict if rounding issues)

## Conclusion

**Before:** Too strict - blocked legitimate transactions  
**After:** Balanced - allows different times, blocks true duplicates  

**Result:** More accurate duplicate detection using balance as time indicator! 🎉

