# Transaction Deduplication Logic Explained

## Overview

The deduplication system uses **fuzzy matching** to identify and handle duplicate transactions. This is important because the same transaction might appear slightly differently in different bank statements.

## How It Works

### Current Deduplication Strategy (Fuzzy Matching)

The `DeduplicationDetector` checks if two transactions are duplicates using **three rules**:

#### Rule 1: Date Window (±N Days)
- Default: ±1 day tolerance
- Why? Same transaction might post on different days
- Example: Transaction on Oct 31 might post on Nov 1

#### Rule 2: Amount Match (Exact ± Tolerance)
- Default: ±0.01 INR (1 paisa)
- Why? Handles floating-point precision issues
- Example: ₹100.00 vs ₹100.01 → Match

#### Rule 3: Merchant Similarity (Fuzzy String Matching)
- Default: ≥85% similarity using `rapidfuzz.token_sort_ratio`
- Why? Same merchant might appear as:
  - "Swiggy Ltd"
  - "SWIGGY PAYMENTS"
  - "SWIGGY ONLINE"
- Example: "Swiggy Ltd" vs "SWIGGY PAYMENTS" → Match

### All Rules Must Match

A transaction is considered a **duplicate** only if **ALL three rules** pass:

```python
is_duplicate = (
    date_within_window(txn1, txn2) AND
    amount_matches(txn1, txn2) AND
    merchant_similar(txn1, txn2)
)
```

### What Happens to Duplicates?

#### Mode 1: Merge (Default)
- Duplicates are **removed** from the processed list
- A `duplicate_count` is incremented on the original transaction
- Example: 2 identical transactions → 1 transaction with `duplicate_count=1`

#### Mode 2: Flag (Optional)
- Duplicates are **kept** but marked
- `is_duplicate=True` is set
- `duplicate_of` points to the original transaction ID

## Why This Wasn't Working for Re-Imports

### The Problem

When you re-import the **exact same transactions** from the same file, the deduplication logic only checks against transactions **within the same batch** (last 100 transactions). It doesn't check against **existing transactions in the database**.

### Example Scenario

```
Import 1: File with 426 transactions → All inserted successfully
Import 2: Same file → Deduplication only checks within the 426 transactions
Result: All 426 transactions inserted AGAIN (duplicates!)
```

### Root Cause

The deduplication happens **in-memory** before database insertion:
1. Parse file → 426 transactions
2. Deduplicate within batch → 387 transactions (39 duplicates within batch)
3. Insert 387 to database → **No check against existing DB transactions!**

## The Solution: Database-Level Duplicate Prevention

### Adding Unique Constraint

We need to add a **composite unique constraint** at the database level to prevent exact duplicates from being inserted:

```sql
UNIQUE(user_id, account_id, date, amount, description_raw)
```

This means:
- **User A** can't have the same transaction twice in the **same account**
- Same date + amount + description = duplicate → Database will reject

### Why This Works

1. **Exact Match Detection**: Catches transactions with identical date, amount, and description
2. **User Isolation**: User A's transactions can't conflict with User B's
3. **Account Isolation**: Same transaction in different accounts is allowed (different account_id)
4. **Database Enforced**: Cannot be bypassed

## Combined Approach

We now use **both** approaches:

### 1. In-Memory Fuzzy Deduplication (Within Batch)
- Catches fuzzy duplicates (similar but not identical)
- Runs **before** database insertion
- More flexible matching

### 2. Database Unique Constraint (Exact Duplicates)
- Catches exact duplicates (identical date, amount, description)
- Runs **during** database insertion
- Cannot be bypassed

### How They Work Together

```
File Import → Parse → Fuzzy Dedup → Insert to DB
                                  ↓
              If exact duplicate: DB rejects with error
              TransactionRepository catches error and skips
```

## Configuration

### Deduplication Settings (config.py)

```python
DEDUP_TIME_WINDOW_DAYS = 1        # ±1 day tolerance
DEDUP_AMOUNT_TOLERANCE = 0.01     # ±1 paisa
DEDUP_FUZZY_THRESHOLD = 85        # 85% similarity
```

### Customizing

You can adjust these settings:

```python
detector = DeduplicationDetector(
    time_window_days=1,      # Stricter: 0 days
    fuzzy_threshold=85,      # Stricter: 95%
    merge_duplicates=True    # False = flag only
)
```

## Edge Cases Handled

### 1. Multiple Accounts
- Same transaction in Account A and Account B → **Allowed** (different account_id)

### 2. Multiple Users
- Same transaction for User A and User B → **Allowed** (different user_id)

### 3. Similar but Different
- "Swiggy" on Oct 31 → **Not duplicate**
- "Swiggy Ltd" on Oct 31 → **Not duplicate** (different description)

### 4. Same Merchant, Different Day
- "Swiggy" Oct 30 → **Not duplicate**
- "Swiggy" Oct 31 → **Not duplicate** (outside ±1 day window)

## Performance

### In-Memory Deduplication
- Only checks last 100 transactions
- O(n) complexity
- Fast for large files

### Database Unique Constraint
- Indexed lookup (very fast)
- Fails fast on duplicates
- No performance impact

## Summary

| Aspect | Fuzzy Deduplication | DB Unique Constraint |
|--------|--------------------|--------------------|
| **Purpose** | Catch similar duplicates | Catch exact duplicates |
| **When** | Before DB insertion | During DB insertion |
| **Matching** | Fuzzy (85% similar) | Exact match |
| **Scope** | Within batch only | All stored transactions |
| **Speed** | Fast (in-memory) | Very fast (indexed) |
| **Accuracy** | Flexible | Strict |

## Next Steps

1. ✅ Migration created to add unique constraint
2. ✅ TransactionRepository updated to handle duplicate errors gracefully
3. ✅ Both systems working together
4. ✅ Re-imports now properly rejected

## Testing

Test the deduplication:

```python
# Import same file twice
upload_file("Transactions.csv")  # First import: 426 transactions inserted
upload_file("Transactions.csv")  # Second import: 0 transactions inserted (all duplicates)
```

Logs will show:
```
💾 TRANSACTION REPOSITORY: ⚠️  Failed to insert transaction: duplicate unique constraint
💾 TRANSACTION REPOSITORY: ✅ Successfully inserted 0/426 transactions (426 were duplicates)
```

