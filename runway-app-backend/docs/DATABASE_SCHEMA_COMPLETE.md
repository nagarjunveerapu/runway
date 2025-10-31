# Database Schema and Migration Complete

## Summary

Successfully created a complete database schema with all tables, indexes, and unique constraints for duplicate prevention.

## Database Schema

### Tables Created (10 total)

1. **users** - User accounts and authentication
2. **accounts** - Bank accounts
3. **merchants** - Canonical merchant list
4. **transactions** - All transaction records
5. **assets** - Investment assets
6. **liquidations** - Asset liquidation events
7. **liabilities** - Loans and debts
8. **salary_sweep_configs** - User salary sweep configuration
9. **detected_emi_patterns** - Recurring payment patterns
10. **net_worth_snapshots** - Historical net worth data

### Indexes Created

#### Performance Indexes
- `idx_user_date` - (user_id, date)
- `idx_user_category` - (user_id, category)
- `idx_date_category` - (date, category)
- `idx_merchant_date` - (merchant_canonical, date)
- `idx_user_month` - (user_id, month)
- `idx_asset_user` - (user_id)
- `idx_asset_recurring_pattern` - (recurring_pattern_id)
- `idx_liquidation_user` - (user_id, asset_id)
- `idx_liability_user` - (user_id)
- `idx_liability_pattern` - (recurring_pattern_id)
- `idx_net_worth_user_month` - (user_id, month)

#### Single-Column Indexes (Auto-created by SQLAlchemy)
- `ix_transactions_user_id`
- `ix_transactions_date`
- `ix_transactions_category`
- `ix_transactions_merchant_canonical`
- `ix_transactions_duplicate_of`
- `ix_transactions_is_recurring`
- `ix_transactions_recurring_group_id`
- `ix_transactions_linked_asset_id`
- `ix_transactions_liquidation_event_id`
- `ix_transactions_month`

### Unique Constraint for Duplicates

**Index:** `idx_transaction_unique`

```sql
CREATE UNIQUE INDEX idx_transaction_unique 
ON transactions(user_id, account_id, date, amount, description_raw)
```

**Purpose:** Prevent exact duplicate transactions

**Note:** SQLite treats NULL as distinct in UNIQUE indexes. This means:
- ✅ Transactions WITH account_id: Fully protected against duplicates
- ⚠️  Transactions WITHOUT account_id: Application-level duplicate detection required

**Solution:** The `TransactionRepository` now checks for duplicates manually when `account_id` is NULL.

## Migration History

### All Migrations Applied:

1. ✅ `make_user_id_not_null.py` - Make user_id NOT NULL
2. ✅ `add_salary_sweep_tables.py` - Add salary sweep and EMI pattern tables
3. ✅ `add_category_columns.py` - Add category/subcategory to EMI patterns
4. ✅ `add_net_worth_snapshots.py` - Add net worth tracking
5. ✅ `add_liability_rate_fields.py` - Add rate fields to liabilities
6. ✅ `add_liability_original_tenure.py` - Add tenure fields to liabilities
7. ✅ `add_asset_recurring_pattern_id.py` - Add recurring pattern support to assets
8. ✅ `add_transaction_unique_constraint.py` - Add unique constraint for duplicates

### Schema Evolution

All migrations have been consolidated into the base schema in `models.py`. Running `reset_and_setup.py` or initializing `DatabaseManager` creates:

1. All tables with latest schema
2. All indexes for performance
3. Unique constraint for duplicate prevention
4. Test user for development

## How It Works

### Database Initialization

**File:** `storage/database.py`

```python
def _init_database(self):
    # Create engine
    # Create tables via Base.metadata.create_all()
    # Create unique constraint manually via SQL
    
    session.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_transaction_unique 
        ON transactions(user_id, account_id, date, amount, description_raw)
    """))
```

### Application Reset

**File:** `reset_and_setup.py`

1. Backup existing database
2. Initialize new database with full schema
3. Create unique constraint
4. Create test user
5. Ready for development!

## Duplicate Prevention Strategy

### Three-Layer Approach

#### Layer 1: In-Memory Fuzzy Dedup (Within Batch)
- **Service:** `TransactionEnrichmentService`
- **Method:** `DeduplicationDetector`
- **Rules:** Date ±1 day, Amount ±0.01, Merchant 85% similar
- **Purpose:** Catch similar duplicates within the same file

#### Layer 2: Application-Level Exact Check (For NULL account_id)
- **Service:** `TransactionRepository.insert_transaction()`
- **Method:** Query database before insert
- **Rules:** Exact match on (user, NULL account, date, amount, description)
- **Purpose:** Prevent exact duplicates when account_id is NULL

#### Layer 3: Database UNIQUE Constraint (For WITH account_id)
- **Database:** SQLite UNIQUE INDEX
- **Method:** Database-level constraint
- **Rules:** Exact match on (user, account, date, amount, description)
- **Purpose:** Prevent exact duplicates when account_id is set

### Why Three Layers?

1. **Fuzzy Dedup:** Same merchant with slightly different descriptions
2. **App Check:** NULL account_id handling (SQLite limitation)
3. **DB Constraint:** Enforced at database level, cannot be bypassed

## Testing

### Manual Test

```bash
cd runway-app-backend
./reset_and_setup.py
```

**Expected Output:**
```
✅ Database created successfully!
✅ Unique constraint created successfully
✅ Test user created successfully!
```

### Verify Schema

```python
from sqlalchemy import text
from storage.database import DatabaseManager

db = DatabaseManager()
with db.engine.connect() as conn:
    # Check unique constraint
    result = conn.execute(text("""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND name='idx_transaction_unique'
    """))
    assert result.fetchone()  # ✅ Exists
    
    # Check tables
    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
    tables = [row[0] for row in result]
    assert len(tables) >= 10  # ✅ All tables created
```

## Current Status

✅ **Base schema complete** - All models defined in `models.py`  
✅ **Indexes optimized** - All performance indexes created  
✅ **Unique constraint applied** - Duplicate prevention active  
✅ **Test data ready** - Test user created  
✅ **Migrations available** - Can run individually if needed  
✅ **Service layer working** - Enhanced parser, enrichment, repository  

## Next Steps

The database is now ready for:
1. ✅ File uploads (CSV/PDF)
2. ✅ Transaction deduplication
3. ✅ User authentication
4. ✅ Asset/liability tracking
5. ✅ Analytics and reporting

## Summary

All migrations have been integrated into the base schema. No need to run individual migrations - just reset and go!

**To start fresh:**
```bash
cd runway-app-backend
./reset_and_setup.py
```

**To verify:**
```bash
python3 -c "from storage.database import DatabaseManager; db = DatabaseManager(); print('✅ Ready!')"
```

🎉 **Database schema is production-ready!**

