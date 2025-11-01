# TODO: Separate Bank and Credit Card Transaction Tables

## Overview
This document outlines the implementation plan for separating bank transactions and credit card transactions into separate tables, with dedicated models, services, and API endpoints.

## Current State Analysis

### Current Architecture
- **Single Transaction Table**: `transactions` table handles both bank and credit card transactions
- **Differentiation**: Transactions are differentiated by `Account.account_type` field ('savings', 'current', 'credit_card')
- **Shared Services**: Services filter transactions by `account_type` when needed
- **Existing Models**: 
  - `Transaction` (unified model)
  - `Account` (has `account_type` field)
  - `CreditCardStatement` (statement metadata only)

### Issues with Current Approach
1. Query complexity - filtering by account_type in every query
2. Schema mismatch - bank and credit card transactions have different attributes
3. Performance - large unified table affects query performance
4. Business logic mixing - bank and credit card logic intertwined

---

## Implementation Plan

### Phase 1: Database Schema Design

#### 1.1 Create BankTransaction Model
- [ ] Create `BankTransaction` model in `storage/models.py`
  - [ ] Base fields: transaction_id, user_id, account_id, date, amount, type (debit/credit)
  - [ ] Bank-specific fields: balance, transaction_reference, cheque_number, branch_code
  - [ ] Inherit common fields: description_raw, merchant_canonical, category, etc.
  - [ ] Foreign keys: user_id → users, account_id → accounts
  - [ ] Indexes: user_id, account_id, date, type, merchant_canonical
  - [ ] Unique constraint: user_id + account_id + date + amount + description (normalized)

#### 1.2 Create CreditCardTransaction Model
- [ ] Create `CreditCardTransaction` model in `storage/models.py`
  - [ ] Base fields: transaction_id, user_id, account_id, date, amount, type (debit/credit)
  - [ ] Credit card-specific fields: statement_id, billing_cycle, due_date, reward_points, transaction_fee
  - [ ] Inherit common fields: description_raw, merchant_canonical, category, etc.
  - [ ] Foreign keys: user_id → users, account_id → accounts, statement_id → credit_card_statements
  - [ ] Indexes: user_id, account_id, date, statement_id, merchant_canonical
  - [ ] Unique constraint: user_id + account_id + date + amount + description (normalized)

#### 1.3 Update User Model Relationships
- [ ] Add `bank_transactions` relationship to User model
- [ ] Add `credit_card_transactions` relationship to User model
- [ ] Keep existing `transactions` relationship for backward compatibility (deprecated)
- [ ] Update `__repr__` methods if needed

#### 1.4 Update Account Model Relationships
- [ ] Add `bank_transactions` relationship to Account model (conditional on account_type)
- [ ] Add `credit_card_transactions` relationship to Account model (conditional on account_type)
- [ ] Keep existing `transactions` relationship for backward compatibility (deprecated)

#### 1.5 Create Database Migration Script
- [ ] Create migration script: `migrations/separate_transaction_tables.py`
  - [ ] Create `bank_transactions` table
  - [ ] Create `credit_card_transactions` table
  - [ ] Migrate existing data:
    - [ ] Query all transactions
    - [ ] Check `Account.account_type` for each transaction
    - [ ] Insert into appropriate table (bank_transactions or credit_card_transactions)
    - [ ] Validate migration (count matching)
  - [ ] Add rollback capability
  - [ ] Test migration on sample data

---

### Phase 2: Service Layer Implementation

#### 2.1 Create BankTransactionService
- [ ] Create `services/bank_transaction_service/bank_transaction_service.py`
  - [ ] `get_bank_transactions(user_id, account_id=None, start_date=None, end_date=None, ...)`
  - [ ] `get_bank_transaction_by_id(transaction_id)`
  - [ ] `create_bank_transaction(transaction_data)`
  - [ ] `update_bank_transaction(transaction_id, updates)`
  - [ ] `delete_bank_transaction(transaction_id)`
  - [ ] `get_bank_transaction_statistics(user_id, account_id=None)`
  - [ ] `bulk_insert_bank_transactions(transactions)`
- [ ] Create `services/bank_transaction_service/__init__.py`
- [ ] Handle account_type validation (only 'savings', 'current', 'checking')
- [ ] Implement duplicate detection logic specific to bank transactions

#### 2.2 Create CreditCardTransactionService
- [ ] Create `services/credit_card_transaction_service/credit_card_transaction_service.py`
  - [ ] `get_credit_card_transactions(user_id, account_id=None, statement_id=None, ...)`
  - [ ] `get_credit_card_transaction_by_id(transaction_id)`
  - [ ] `create_credit_card_transaction(transaction_data)`
  - [ ] `update_credit_card_transaction(transaction_id, updates)`
  - [ ] `delete_credit_card_transaction(transaction_id)`
  - [ ] `get_credit_card_transaction_statistics(user_id, account_id=None)`
  - [ ] `get_transactions_by_billing_cycle(account_id, billing_cycle)`
  - [ ] `bulk_insert_credit_card_transactions(transactions)`
- [ ] Create `services/credit_card_transaction_service/__init__.py`
- [ ] Handle account_type validation (only 'credit_card', 'credit')
- [ ] Integrate with `CreditCardStatement` model
- [ ] Implement duplicate detection logic specific to credit card transactions

#### 2.3 Create Unified Transaction Repository
- [ ] Create `services/transaction_service/unified_transaction_repository.py`
  - [ ] `get_all_transactions(user_id, transaction_type='all')` - queries both tables
  - [ ] `get_transactions_by_type(user_id, account_type)` - routes to appropriate service
  - [ ] Abstract interface for transaction operations
- [ ] Use strategy pattern to route to BankTransactionService or CreditCardTransactionService

#### 2.4 Update ParserService
- [ ] Modify `services/parser_service/parser_service.py`
  - [ ] Detect account type during parsing (from metadata or account_type_hint)
  - [ ] Route to appropriate repository:
    - [ ] If `account_type` in ['savings', 'current', 'checking'] → BankTransactionService
    - [ ] If `account_type` in ['credit_card', 'credit'] → CreditCardTransactionService
  - [ ] Update `process_uploaded_file()` to handle routing
  - [ ] Maintain backward compatibility during transition

#### 2.5 Update TransactionEnrichmentService
- [ ] Update `services/parser_service/transaction_enrichment_service.py`
  - [ ] Ensure enrichment works for both transaction types
  - [ ] Handle different merchant normalization rules for bank vs credit card
  - [ ] Update categorization logic if needed

---

### Phase 3: API Routes Update

#### 3.1 Create Bank Transaction Routes
- [ ] Create `api/routes/bank_transactions.py`
  - [ ] `GET /api/v1/bank-transactions` - list bank transactions
  - [ ] `GET /api/v1/bank-transactions/{transaction_id}` - get single transaction
  - [ ] `POST /api/v1/bank-transactions` - create transaction
  - [ ] `PUT /api/v1/bank-transactions/{transaction_id}` - update transaction
  - [ ] `DELETE /api/v1/bank-transactions/{transaction_id}` - delete transaction
  - [ ] `GET /api/v1/bank-transactions/statistics` - get statistics
  - [ ] Use BankTransactionService
  - [ ] Add request/response models in `api/models/schemas.py`

#### 3.2 Create Credit Card Transaction Routes
- [ ] Create `api/routes/credit_card_transactions.py`
  - [ ] `GET /api/v1/credit-card-transactions` - list credit card transactions
  - [ ] `GET /api/v1/credit-card-transactions/{transaction_id}` - get single transaction
  - [ ] `POST /api/v1/credit-card-transactions` - create transaction
  - [ ] `PUT /api/v1/credit-card-transactions/{transaction_id}` - update transaction
  - [ ] `DELETE /api/v1/credit-card-transactions/{transaction_id}` - delete transaction
  - [ ] `GET /api/v1/credit-card-transactions/statistics` - get statistics
  - [ ] `GET /api/v1/credit-card-transactions/by-billing-cycle/{cycle}` - get by billing cycle
  - [ ] Use CreditCardTransactionService
  - [ ] Add request/response models in `api/models/schemas.py`

#### 3.3 Update Existing Routes
- [ ] Update `api/routes/transactions.py`
  - [ ] Modify to query both tables when needed
  - [ ] Add `transaction_type` query parameter ('all', 'bank', 'credit_card')
  - [ ] Use UnifiedTransactionRepository for combined queries
  - [ ] Maintain backward compatibility

#### 3.4 Update Salary Sweep Routes
- [ ] Update `api/routes/salary_sweep_v2.py`
  - [ ] Ensure salary detection only queries bank transactions
  - [ ] Ensure EMI detection queries appropriate table based on transaction_source
  - [ ] Update `detect_or_refresh_patterns()` to use new services

#### 3.5 Update Analytics Routes
- [ ] Update `api/routes/analytics.py`
  - [ ] Support filtering by transaction type
  - [ ] Update queries to use appropriate services
  - [ ] Combine results from both tables when needed

#### 3.6 Update Dashboard Routes
- [ ] Update `api/routes/dashboard.py`
  - [ ] Query both transaction types
  - [ ] Aggregate statistics from both tables
  - [ ] Update summary calculations

#### 3.7 Update Assets/Liabilities Routes
- [ ] Update `api/routes/assets.py`
  - [ ] Ensure asset detection queries bank transactions only
  - [ ] Update EMI detection logic
- [ ] Update `api/routes/liabilities.py` (if exists)
  - [ ] Query credit card transactions for liability tracking

---

### Phase 4: Database Layer Updates

#### 4.1 Update DatabaseManager
- [ ] Update `storage/database.py`
  - [ ] Add `get_bank_transactions()` method
  - [ ] Add `get_credit_card_transactions()` method
  - [ ] Update `get_transactions()` to support querying both tables
  - [ ] Add `insert_bank_transaction()` method
  - [ ] Add `insert_credit_card_transaction()` method
  - [ ] Maintain backward compatibility for `insert_transaction()`

#### 4.2 Update Database Queries
- [ ] Review all queries in `storage/database.py` that use Transaction model
- [ ] Create separate query methods or update to handle both tables
- [ ] Ensure proper indexing for performance

---

### Phase 5: Frontend Integration

#### 5.1 Update Frontend API Services
- [ ] Update `runway-app/src/api/services/transactions.js`
  - [ ] Add methods for bank transactions: `getBankTransactions()`, `createBankTransaction()`, etc.
  - [ ] Add methods for credit card transactions: `getCreditCardTransactions()`, etc.
  - [ ] Update existing methods to support `transaction_type` parameter

#### 5.2 Update Frontend Components
- [ ] Update transaction list components to filter by type
- [ ] Update upload components to route to appropriate endpoints
- [ ] Update analytics components to handle both transaction types
- [ ] Add UI for switching between bank and credit card views

---

### Phase 6: Testing & Validation

#### 6.1 Unit Tests
- [ ] Test BankTransactionService methods
- [ ] Test CreditCardTransactionService methods
- [ ] Test UnifiedTransactionRepository
- [ ] Test updated ParserService routing
- [ ] Test migration script

#### 6.2 Integration Tests
- [ ] Test API endpoints for bank transactions
- [ ] Test API endpoints for credit card transactions
- [ ] Test combined queries (both transaction types)
- [ ] Test file upload routing to correct table

#### 6.3 Data Migration Testing
- [ ] Test migration script on production-like data
- [ ] Validate data integrity after migration
- [ ] Test rollback procedure
- [ ] Performance testing on migrated data

---

### Phase 7: Documentation & Deployment

#### 7.1 Documentation
- [ ] Update API documentation for new endpoints
- [ ] Document new database schema
- [ ] Create migration guide for developers
- [ ] Update README with new architecture

#### 7.2 Deployment Plan
- [ ] Create deployment checklist
- [ ] Backup existing database
- [ ] Run migration script in staging
- [ ] Validate staging environment
- [ ] Deploy to production
- [ ] Monitor for issues
- [ ] Rollback plan ready

---

## Migration Strategy

### Step 1: Parallel Running (Backward Compatible)
- Implement new models and services alongside existing Transaction model
- New transactions go to appropriate table based on account_type
- Old transactions remain in unified `transactions` table
- API routes support both old and new endpoints

### Step 2: Data Migration
- Run migration script to move existing transactions
- Validate migration completeness
- Keep old `transactions` table for read-only queries during transition

### Step 3: Switch Over
- Update all services to use new tables only
- Update API routes to use new services
- Mark old Transaction model as deprecated

### Step 4: Cleanup
- Remove old Transaction model (after ensuring no dependencies)
- Remove deprecated code
- Archive old `transactions` table (optional)

---

## Considerations

### Performance
- Indexes on both new tables for optimal query performance
- Consider partitioning for large datasets
- Optimize queries that need to aggregate both tables

### Data Consistency
- Ensure foreign key constraints are properly set
- Maintain referential integrity during migration
- Handle edge cases (transactions with null account_id)

### Backward Compatibility
- Maintain old API endpoints during transition period
- Provide deprecation warnings
- Document migration path for API consumers

### Security
- Ensure authorization checks work for both transaction types
- Validate user ownership for both tables
- Maintain audit logging

---

## Estimated Effort

- **Phase 1 (Schema)**: 2-3 days
- **Phase 2 (Services)**: 3-4 days
- **Phase 3 (API Routes)**: 2-3 days
- **Phase 4 (Database Layer)**: 1-2 days
- **Phase 5 (Frontend)**: 2-3 days
- **Phase 6 (Testing)**: 2-3 days
- **Phase 7 (Documentation/Deployment)**: 1-2 days

**Total Estimated Time**: 13-20 days

---

## Dependencies

- Complete understanding of current transaction usage
- Database backup before migration
- Test environment for validation
- Frontend team coordination

---

## Notes

- Keep old `transactions` table during migration for rollback capability
- Consider creating database views for unified queries if needed
- Document any breaking changes clearly
- Consider feature flag for gradual rollout

