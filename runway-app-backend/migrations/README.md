# Migration Files - Status and Usage

## ⚠️ Important Notice

**All migrations have been consolidated into the base schema!**

Running `reset_and_setup.py` creates the complete database schema automatically.

## When to Use These Files

### ✅ Keep for Reference
These files document the **schema evolution** and are useful for:
- Understanding what changed over time
- Upgrading existing production databases
- Audit trails and historical reference

### ✅ Still Functional
You can still run individual migrations if needed:
```bash
python3 migrations/add_transaction_unique_constraint.py
python3 migrations/add_salary_sweep_tables.py
# etc.
```

**Use cases:**
- Upgrading existing database without losing data
- Applying specific changes incrementally
- Troubleshooting schema issues

### ⚠️ Not Needed for Fresh Databases
**Fresh databases:** Just run `./reset_and_setup.py` and everything is created!

## Migration Files

### Current Migrations (8 total)

1. **make_user_id_not_null.py**
   - Added NOT NULL constraint to user_id
   - Removed orphaned transactions
   - **Status:** ✅ Consolidated

2. **add_salary_sweep_tables.py**
   - Created salary_sweep_configs table
   - Created detected_emi_patterns table
   - **Status:** ✅ Consolidated

3. **add_category_columns.py**
   - Added category/subcategory to EMI patterns
   - **Status:** ✅ Consolidated

4. **add_net_worth_snapshots.py**
   - Created net_worth_snapshots table
   - **Status:** ✅ Consolidated

5. **add_liability_rate_fields.py**
   - Added interest rate fields to liabilities
   - **Status:** ✅ Consolidated

6. **add_liability_original_tenure.py**
   - Added tenure fields to liabilities
   - **Status:** ✅ Consolidated

7. **add_asset_recurring_pattern_id.py**
   - Added recurring pattern support to assets
   - **Status:** ✅ Consolidated

8. **add_transaction_unique_constraint.py**
   - Added unique constraint for duplicate prevention
   - Cleans existing duplicates
   - **Status:** ✅ Consolidated

## Recommendation

### Keep Files
**Status:** These are now **reference documentation**
- Show schema evolution
- Can be run if upgrading existing DB
- Good for historical records

### For New Databases
**Just use:** `./reset_and_setup.py`

No individual migrations needed!

### For Existing Databases
If upgrading existing production database:
- Run relevant migrations in order
- Or reset completely with `reset_and_setup.py`

## Summary

**Migration files:** Historical reference, still functional if needed  
**Base schema:** Complete, includes all migrations  
**Default workflow:** Use `reset_and_setup.py` for fresh databases

