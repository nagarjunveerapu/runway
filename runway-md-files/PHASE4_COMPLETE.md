# ✅ Phase 4: Backend Data Models - COMPLETE

## Overview

Phase 4 has been implemented to extend the backend data models with Asset and Liquidation support, and add corresponding API endpoints.

## Changes Made

### 1. Extended Transaction Model
**File**: `runway/run_poc/storage/models.py`

Added FIRE integration fields:
- ✅ `linked_asset_id` - Reference to Asset model
- ✅ `liquidation_event_id` - Reference to Liquidation event
- ✅ `month` - YYYY-MM format for monthly aggregation

### 2. Created Asset Model
**File**: `runway/run_poc/storage/models.py`

Complete asset model with:
- ✅ `asset_id` - Primary key (UUID)
- ✅ `user_id` - Foreign key to User
- ✅ `name` - Asset name
- ✅ `asset_type` - Type (Stock, MutualFund, Property, etc.)
- ✅ `quantity` - Quantity held
- ✅ `purchase_price` - Purchase price
- ✅ `current_value` - Current value
- ✅ `purchase_date` - Purchase date
- ✅ `liquid` - Is liquid asset (boolean)
- ✅ `disposed` - Is disposed (boolean)
- ✅ `notes` - Additional notes
- ✅ `created_at` / `updated_at` - Timestamps
- ✅ `to_dict()` method for serialization

### 3. Created Liquidation Model
**File**: `runway/run_poc/storage/models.py`

Complete liquidation model with:
- ✅ `liquidation_id` - Primary key (UUID)
- ✅ `user_id` - Foreign key to User
- ✅ `asset_id` - Asset being liquidated
- ✅ `date` - Liquidation date (YYYY-MM-DD)
- ✅ `gross_proceeds` - Gross proceeds
- ✅ `fees` - Fees
- ✅ `net_received` - Net received (calculated)
- ✅ `quantity_sold` - Quantity sold
- ✅ `notes` - Additional notes
- ✅ `created_at` - Timestamp
- ✅ `to_dict()` method for serialization

### 4. Created Asset API Routes
**File**: `runway/run_poc/api/routes/assets.py`

Complete CRUD operations:
- ✅ `GET /api/v1/assets` - Get all assets (user-specific)
- ✅ `GET /api/v1/assets/{asset_id}` - Get single asset
- ✅ `POST /api/v1/assets` - Create new asset
- ✅ `PATCH /api/v1/assets/{asset_id}` - Update asset
- ✅ `DELETE /api/v1/assets/{asset_id}` - Delete asset

All endpoints require authentication via `get_current_user` dependency.

### 5. Created Liquidation API Routes
**File**: `runway/run_poc/api/routes/liquidations.py`

Complete CRUD operations:
- ✅ `GET /api/v1/liquidations` - Get all liquidations (user-specific)
- ✅ `GET /api/v1/liquidations/{liquidation_id}` - Get single liquidation
- ✅ `POST /api/v1/liquidations` - Create new liquidation (auto-calculates net)
- ✅ `DELETE /api/v1/liquidations/{liquidation_id}` - Delete liquidation

All endpoints require authentication via `get_current_user` dependency.

### 6. Registered Routes
**Files**: `runway/run_poc/api/routes/__init__.py`, `runway/run_poc/api/main.py`

- ✅ Added routes to `__init__.py`
- ✅ Registered asset routes in `main.py`
- ✅ Registered liquidation routes in `main.py`
- ✅ Both routes are under authentication protection

### 7. Database Indexes
**File**: `runway/run_poc/storage/models.py`

Added indexes for performance:
- ✅ `idx_user_month` - User + month for transaction queries
- ✅ `idx_asset_user` - User + asset for asset queries
- ✅ `idx_liquidation_user` - User + asset for liquidation queries

## Database Schema Changes

### Transaction Table (Extended)
```sql
ALTER TABLE transactions ADD COLUMN linked_asset_id VARCHAR(36);
ALTER TABLE transactions ADD COLUMN liquidation_event_id VARCHAR(36);
ALTER TABLE transactions ADD COLUMN month VARCHAR(7);
CREATE INDEX idx_user_month ON transactions(user_id, month);
```

### Assets Table (New)
```sql
CREATE TABLE assets (
    asset_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    asset_type VARCHAR(100),
    quantity FLOAT,
    purchase_price FLOAT,
    current_value FLOAT,
    purchase_date DATETIME,
    liquid BOOLEAN DEFAULT FALSE,
    disposed BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at DATETIME,
    updated_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
CREATE INDEX idx_asset_user ON assets(user_id);
```

### Liquidations Table (New)
```sql
CREATE TABLE liquidations (
    liquidation_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    asset_id VARCHAR(36) NOT NULL,
    date VARCHAR(10) NOT NULL,
    gross_proceeds FLOAT,
    fees FLOAT DEFAULT 0.0,
    net_received FLOAT,
    quantity_sold FLOAT,
    notes TEXT,
    created_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
CREATE INDEX idx_liquidation_user ON liquidations(user_id, asset_id);
```

## API Documentation

### Assets Endpoints
- **Base URL**: `/api/v1/assets`
- **Authentication**: Required (JWT token)
- **Response Format**: JSON

**GET /api/v1/assets**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/assets
```

**POST /api/v1/assets**
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Apple Inc",
    "asset_type": "Stock",
    "quantity": 10,
    "purchase_price": 150.00,
    "current_value": 175.00,
    "liquid": true
  }' \
  http://localhost:8000/api/v1/assets
```

### Liquidations Endpoints
- **Base URL**: `/api/v1/liquidations`
- **Authentication**: Required (JWT token)
- **Response Format**: JSON

**GET /api/v1/liquidations**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/liquidations
```

**POST /api/v1/liquidations**
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "asset_id": "asset-uuid",
    "date": "2025-01-15",
    "gross_proceeds": 1750.00,
    "fees": 10.00,
    "quantity_sold": 10,
    "notes": "Sold all shares"
  }' \
  http://localhost:8000/api/v1/liquidations
```

## Migration Instructions

The database schema has been updated. To apply changes:

1. **Stop the backend server**
2. **Run the reset script** (will recreate tables with new schema):
```bash
cd runway/run_poc
python3 reset_and_setup.py
```

3. **Restart the backend**:
```bash
python3 -m uvicorn api.main:app --reload
```

## Integration Status

| Component | Status | Notes |
|-----------|--------|-------|
| Asset Model | ✅ Complete | Full CRUD support |
| Liquidation Model | ✅ Complete | Full CRUD support |
| Transaction Extension | ✅ Complete | Added FIRE fields |
| Asset API | ✅ Complete | All endpoints protected |
| Liquidation API | ✅ Complete | All endpoints protected |
| Database Indexes | ✅ Complete | Optimized for queries |

## Next Steps

### Phase 5: AppContext Migration
- [ ] Update AppContext to use API services for transactions
- [ ] Update AppContext to use API services for assets
- [ ] Update AppContext to use API services for liquidations
- [ ] Add loading and error states
- [ ] Implement optimistic updates
- [ ] Keep localStorage as cache

## Testing

To test the new endpoints:

```bash
# Get auth token
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpassword123"}' \
  | jq -r '.access_token')

# Get all assets
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/assets

# Get all liquidations
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/liquidations
```

## Documentation

- API Docs: http://localhost:8000/docs
- Models: `runway/run_poc/storage/models.py`
- Routes: `runway/run_poc/api/routes/`

