# Liabilities & Runway Tracking - Implementation Plan

## Goal
Track liabilities (EMIs, loans) alongside assets to calculate true net worth and financial runway.

## Current State

### What We Have:
- ✅ Assets tracked: Property, Investments, etc.
- ✅ Recurring EMIs detected via Centralized System
- ✅ Monthly income/expenses calculated
- ✅ Net worth = Assets only (ignoring liabilities)

### What's Missing:
- ❌ Liabilities not tracked (loans, EMIs)
- ❌ True Net Worth = Assets - Liabilities
- ❌ Financial Runway calculation
- ❌ Debt-to-Asset ratio
- ❌ Asset Allocation breakdown

## Proposed Homepage Enhancements

### 1. Net Worth Card (Existing - Needs Update)
**Current:** Shows only assets
**Enhanced:** Assets - Liabilities = True Net Worth

```
┌─────────────────────────────────────┐
│ Net Worth                           │
│                                     │
│ ₹66,00,000                           │
│                                     │
│ Assets:  ₹66,00,000  ━━━━━━ 100%  │
│ Liabilities: ₹0      ━              │
└─────────────────────────────────────┘
```

### 2. Financial Runway Card (NEW)
Calculate: Liquid Assets / Monthly Burn Rate

```
┌─────────────────────────────────────┐
│ Financial Runway                     │
│                                     │
│ 🏃 12 months                       │
│                                     │
│ Liquid: ₹10L                        │
│ Burn: ₹50K/month                    │
└─────────────────────────────────────┘
```

### 3. Debt-to-Asset Ratio (NEW)
Calculate: Total Liabilities / Total Assets

```
┌─────────────────────────────────────┐
│ Debt-to-Asset Ratio                 │
│                                     │
│ 0.0%  ✓ Excellent                 │
│                                     │
│ Ideal: < 30%                       │
└─────────────────────────────────────┘
```

### 4. Asset Allocation (NEW)
Breakdown: Liquid vs Non-liquid assets

```
┌─────────────────────────────────────┐
│ Asset Allocation                    │
│                                     │
│ Liquid:   15%  [████]              │
│ Property: 70%   [████████████]     │
│ Other:    15%   [████]              │
└─────────────────────────────────────┘
```

## Implementation Steps

### Backend Changes

#### 1. Create Liability Model
**File:** `runway/run_poc/storage/models.py`

```python
class Liability(Base):
    """Liability model (loans, EMIs, debts)"""
    __tablename__ = 'liabilities'
    
    liability_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.user_id'))
    
    # Liability details
    name = Column(String(255))  # e.g., "Home Loan", "Personal Loan"
    liability_type = Column(String(100))  # loan, credit_card, mortgage, etc.
    
    # Financial details
    principal_amount = Column(Float)  # Original loan amount
    outstanding_balance = Column(Float)  # Current balance
    interest_rate = Column(Float)  # Annual %
    emi_amount = Column(Float)  # Monthly EMI
    remaining_tenure_months = Column(Integer)  # Months left
    
    # Link to recurring payment pattern
    recurring_pattern_id = Column(String(36))  # Links to DetectedEMIPattern
    
    # Metadata
    start_date = Column(DateTime)
    lender_name = Column(String(255))
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
```

#### 2. Update Dashboard API
**File:** `runway/run_poc/api/routes/dashboard.py`

```python
# Calculate liabilities from EMIs
session = db.get_session()
liabilities = session.query(Liability).filter(
    Liability.user_id == current_user.user_id
).all()

# Calculate total liabilities
total_liabilities = sum(
    (liability.outstanding_balance or liability.principal_amount or 0)
    for liability in liabilities
)

# Calculate monthly liabilities (total EMI)
monthly_liabilities = sum(
    (liability.emi_amount or 0) for liability in liabilities
)

# True net worth
true_net_worth = total_asset_value - total_liabilities

# Financial runway
liquid_assets = sum(
    (getattr(a, 'current_value', 0) or getattr(a, 'purchase_price', 0))
    for a in active_assets if getattr(a, 'liquid', False)
)
monthly_burn = current_expenses - current_income  # Negative = saving
runway_months = liquid_assets / abs(monthly_burn) if monthly_burn < 0 else float('inf')

# Debt-to-asset ratio
debt_to_asset_ratio = (total_liabilities / total_asset_value * 100) if total_asset_value > 0 else 0
```

#### 3. Create Liability Management API
**File:** `runway/run_poc/api/routes/liabilities.py`

```python
@router.get("/", response_model=List[dict])
async def get_liabilities(...):
    """Get all liabilities for user"""
    
@router.post("/", response_model=dict)
async def create_liability(...):
    """Create new liability"""
    
@router.patch("/{liability_id}", response_model=dict)
async def update_liability(...):
    """Update existing liability"""
    
@router.delete("/{liability_id}")
async def delete_liability(...):
    """Delete liability"""
```

#### 4. Auto-create Liabilities from EMIs
**Enhancement:** When user confirms EMI patterns, automatically create Liability records

**File:** `runway/run_poc/api/routes/salary_sweep.py`

```python
# After user confirms EMIs, create liability records
for confirmed_emi in confirmed_emis:
    # Check if liability exists
    existing = session.query(Liability).filter(
        Liability.user_id == current_user.user_id,
        Liability.recurring_pattern_id == confirmed_emi.pattern_id
    ).first()
    
    if not existing:
        liability = Liability(
            liability_id=str(uuid.uuid4()),
            user_id=current_user.user_id,
            name=confirmed_emi.user_label or confirmed_emi.merchant_source,
            liability_type='loan',
            emi_amount=confirmed_emi.emi_amount,
            recurring_pattern_id=confirmed_emi.pattern_id,
            # Estimate outstanding balance (user can update later)
            outstanding_balance=confirmed_emi.emi_amount * 60,  # Rough estimate
            lender_name=confirmed_emi.merchant_source
        )
        session.add(liability)
```

### Frontend Changes

#### 1. Update Homepage (ModernHome.jsx)

Add new cards after the existing ones:

```jsx
{/* Financial Runway Card */}
<div className="bg-gradient-to-br from-blue-50 to-cyan-50 rounded-2xl p-5 border border-blue-200">
  <div className="flex items-center justify-between mb-3">
    <div className="font-semibold text-blue-900">Financial Runway</div>
    <span className="text-xs text-blue-600">{runway_months.toFixed(1)} months</span>
  </div>
  <div className="text-2xl font-bold text-blue-600">
    {runway_months >= 12 ? '🛫' : runway_months >= 6 ? '✈️' : '⚠️'}
  </div>
</div>

{/* Debt-to-Asset Ratio */}
<div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-2xl p-5 border border-green-200">
  <div className="font-semibold text-green-900 mb-2">Debt-to-Asset Ratio</div>
  <div className="text-2xl font-bold text-green-600">{debt_ratio}%</div>
  <div className="text-xs text-green-600 mt-1">
    {debt_ratio < 30 ? '✓ Healthy' : '⚠️ High Debt'}
  </div>
</div>
```

#### 2. Update Dashboard Summary Response

Add fields to DashboardSummary model:

```python
class DashboardSummary(BaseModel):
    # Existing fields...
    assets: AssetSummary
    
    # NEW FIELDS:
    liabilities: LiabilitySummary
    liabilities_total: float
    monthly_liabilities: float
    true_net_worth: float  # Assets - Liabilities
    runway_months: float
    debt_to_asset_ratio: float
    liquid_assets: float
```

#### 3. Create Liability Management UI

**New Component:** `ModernLiabilities.jsx`

Similar to ModernAssets, but for tracking debts:
- List all liabilities
- Show outstanding balance
- Show EMI amount
- Show interest rate
- Allow editing/updating

## Database Schema Updates Needed

### New Table: liabilities
```sql
CREATE TABLE liabilities (
    liability_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    name VARCHAR(255),
    liability_type VARCHAR(100),
    principal_amount FLOAT,
    outstanding_balance FLOAT,
    interest_rate FLOAT,
    emi_amount FLOAT,
    remaining_tenure_months INTEGER,
    recurring_pattern_id VARCHAR(36),
    start_date DATETIME,
    lender_name VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Key Metrics to Display

### 1. True Net Worth
**Formula:** `Total Assets - Total Liabilities`

**Interpretation:**
- Positive: Building wealth
- Negative: Debt exceeds assets

### 2. Financial Runway
**Formula:** `Liquid Assets / Monthly Burn Rate`

**Interpretation:**
- 6+ months: Excellent emergency fund
- 3-6 months: Good
- < 3 months: Build emergency fund

### 3. Debt-to-Asset Ratio
**Formula:** `(Total Liabilities / Total Assets) * 100`

**Interpretation:**
- < 30%: Healthy
- 30-50%: Manageable
- > 50%: High risk

### 4. Monthly Liquidity
**Formula:** `Monthly Income - Monthly Expenses - Monthly Liabilities`

**Interpretation:**
- Positive: Building savings
- Negative: Living beyond means

## Next Steps

1. **Create Liability Model** - Database schema
2. **Add Liability API Endpoints** - CRUD operations
3. **Auto-create from EMIs** - Link confirmed EMIs to liabilities
4. **Update Dashboard API** - Calculate metrics
5. **Update Homepage** - Display new cards
6. **Create Liability Management UI** - Allow editing

Would you like me to start implementing these changes?

