# Centralized Recurring Payments System

## Overview

The Recurring Payments system provides a single source of truth for all recurring financial obligations across the application. Instead of detecting EMIs/investments/insurance separately in each feature, users configure them once in **Salary Sweep Optimizer**, and all other features reuse this data.

## Categories

The system categorizes recurring payments into 4 main types:

1. **Loans** - Home Loans, Personal Loans, Auto Loans, EMIs
2. **Insurance** - Life Insurance, Health Insurance, Term Insurance
3. **Investments** - Mutual Fund SIPs, Investment Plans
4. **Government Schemes** - APY, NPS, PPF, EPF, ESI

## Database Schema

### DetectedEMIPattern Table
```sql
CREATE TABLE detected_emi_patterns (
    pattern_id VARCHAR(36) PRIMARY KEY,
    config_id VARCHAR(36),  -- FK to salary_sweep_configs
    user_id VARCHAR(36),    -- FK to users
    merchant_source VARCHAR(255),
    emi_amount FLOAT,
    occurrence_count INTEGER,
    category VARCHAR(50),           -- 'Loan', 'Insurance', 'Investment', 'Government Scheme'
    subcategory VARCHAR(100),       -- 'Home Loan', 'Life Insurance', 'Mutual Fund SIP', etc.
    is_confirmed BOOLEAN,
    user_label VARCHAR(255),
    suggested_action VARCHAR(50),
    suggestion_reason TEXT,
    transaction_ids JSON,
    first_detected_date VARCHAR(10),
    last_detected_date VARCHAR(10),
    created_at DATETIME,
    updated_at DATETIME
);
```

## API Endpoints

### 1. Centralized Endpoint (Recommended)

**GET** `/api/salary-sweep/recurring-payments`

Returns all saved recurring payments grouped by category.

**Response:**
```json
{
  "loans": [
    {
      "pattern_id": "uuid",
      "merchant_source": "CANFINHOMESLTD",
      "emi_amount": 31453.0,
      "occurrence_count": 6,
      "category": "Loan",
      "subcategory": "Home Loan",
      "is_confirmed": true,
      "user_label": "Home Loan EMI",
      "transaction_ids": ["txn1", "txn2"],
      "first_detected_date": "01/01/2025",
      "last_detected_date": "01/06/2025"
    }
  ],
  "insurance": [...],
  "investments": [...],
  "government_schemes": [...]
}
```

**Use Cases:**
- **Salary Sweep Optimizer**: Uses all categories
- **Loan Optimizer**: Uses only `loans` array
- **Investment Dashboard**: Uses only `investments` array
- **Insurance Tracker**: Uses only `insurance` array
- **Pension/Schemes Tracker**: Uses only `government_schemes` array

### 2. Detection & Setup

**POST** `/api/salary-sweep/detect`

Detects recurring payments from transactions. Returns both saved and newly detected patterns.

**Response:**
```json
{
  "has_existing_config": true,
  "salary": {
    "source": "ACME Corp",
    "amount": 150000.0,
    "count": 6,
    "is_confirmed": true
  },
  "emis": [
    {
      "pattern_id": "uuid",
      "merchant_source": "CANFINHOMESLTD",
      "emi_amount": 31453.0,
      "category": "Loan",
      "subcategory": "Home Loan",
      "is_confirmed": true,
      "suggested_action": "keep",
      "suggestion_reason": "Already tracked"
    },
    {
      "pattern_id": "uuid",
      "merchant_source": "SBI Life Insurance",
      "emi_amount": 25000.0,
      "category": "Insurance",
      "subcategory": "Life Insurance",
      "is_confirmed": false,
      "suggested_action": "keep",
      "suggestion_reason": "Newly detected recurring payment"
    }
  ],
  "message": "Found 2 recurring payments: 1 already tracked, 1 new patterns detected."
}
```

### 3. Save Configuration

**POST** `/api/salary-sweep/confirm`

Saves selected recurring payments with their categories.

**Request:**
```json
{
  "salary_source": "ACME Corp",
  "salary_amount": 150000.0,
  "emi_pattern_ids": ["pattern-id-1", "pattern-id-2"],
  "salary_account_rate": 2.5,
  "savings_account_rate": 7.0
}
```

## How It Works

### 1. User Journey

1. **Setup** (One-time)
   - User goes to Salary Sweep Optimizer
   - System detects all recurring payments (loans, insurance, investments, schemes)
   - User confirms which ones to track
   - System saves to database with proper categorization

2. **Reuse Everywhere**
   - Loan Optimizer: Fetches `/recurring-payments`, uses only `loans[]`
   - Investment Dashboard: Fetches `/recurring-payments`, uses only `investments[]`
   - Insurance Tracker: Fetches `/recurring-payments`, uses only `insurance[]`

3. **Add More Later**
   - User clicks "Add EMIs" in Salary Sweep
   - System re-detects ALL transactions
   - Shows already saved patterns (marked) + new patterns
   - User can add more

### 2. Categorization Logic

The system uses keyword matching on merchant names and transaction descriptions:

```python
# Example categorization
"ACH/CANFINHOMESLTD/*" → Loan / Home Loan
"SBI Life Insurance" → Insurance / Life Insurance
"HDFC MF SIP" → Investment / Mutual Fund SIP
"APY_Debit" → Government Scheme / APY
```

See `categorize_recurring_payment()` function in [salary_sweep_v2.py](../api/routes/salary_sweep_v2.py) for full logic.

## Integration Examples

### Example 1: Loan Optimizer

```javascript
// Fetch only loans from centralized endpoint
const response = await fetch('/api/salary-sweep/recurring-payments');
const data = await response.json();

// Use only loans
const loans = data.loans.map(loan => ({
  id: loan.pattern_id,
  name: loan.user_label || loan.merchant_source,
  monthlyEMI: loan.emi_amount,
  type: loan.subcategory  // 'Home Loan', 'Personal Loan', etc.
}));

// Now ask user for additional details
loans.forEach(loan => {
  // Ask for principal amount, interest rate, remaining tenure
  // These are loan-specific details not captured in recurring payments
});
```

### Example 2: Investment Dashboard

```javascript
// Fetch only investments
const response = await fetch('/api/salary-sweep/recurring-payments');
const { investments } = await response.json();

// Display SIPs
investments.forEach(sip => {
  console.log(`${sip.user_label}: ₹${sip.emi_amount}/month`);
  console.log(`Type: ${sip.subcategory}`);  // 'Mutual Fund SIP'
});
```

### Example 3: Insurance Tracker

```javascript
// Fetch only insurance
const response = await fetch('/api/salary-sweep/recurring-payments');
const { insurance } = await response.json();

// Display premiums
insurance.forEach(policy => {
  console.log(`${policy.merchant_source}: ₹${policy.emi_amount}/month`);
  console.log(`Type: ${policy.subcategory}`);  // 'Life Insurance', 'Health Insurance'
});
```

## Benefits

1. **No Duplicate Detection**: Detect once, use everywhere
2. **Consistent Data**: Single source of truth
3. **Better UX**: Users don't re-enter same data
4. **Easy Maintenance**: Update in one place, reflects everywhere
5. **Category-Based Access**: Each feature gets only what it needs

## Future Enhancements

- [ ] Add frequency field (monthly, quarterly, yearly)
- [ ] Add due date tracking for each payment
- [ ] Add auto-categorization using ML model
- [ ] Add bulk edit capabilities
- [ ] Add payment history visualization
- [ ] Add alerts for upcoming payments

## Migration Notes

For existing features using EMI detection:
1. Update to use `/recurring-payments` endpoint
2. Filter by category as needed
3. Remove local detection logic
4. Map to feature-specific data structure
