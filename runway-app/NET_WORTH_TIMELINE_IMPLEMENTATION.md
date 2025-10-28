# Net Worth Timeline - Implementation Guide

## 🎯 Overview

The Net Worth Timeline feature has been fully implemented with both frontend and backend components. This feature allows users to track their net worth over time with monthly snapshots, visualized in an interactive chart.

---

## 📦 Components Implemented

### **Frontend (React)**

1. **[NetWorthTimeline.jsx](src/components/Modern/NetWorthTimeline.jsx)** (296 lines)
   - Interactive area chart using Recharts
   - Time period toggles: 3M, 6M, 1Y, All
   - Growth indicators with percentage change
   - Custom tooltips and formatting
   - Loading, error, and empty states

2. **[netWorth.js](src/api/services/netWorth.js)** - API Service
   - `getNetWorthTimeline(months)` - Fetch timeline data
   - `getCurrentNetWorth()` - Get real-time snapshot
   - `createNetWorthSnapshot()` - Manual snapshot trigger

3. **[ModernWealth.jsx](src/components/Modern/ModernWealth.jsx)** - Updated
   - Integrated NetWorthTimeline component

### **Backend (FastAPI)**

1. **[net_worth_timeline.py](/Users/karthikeyaadhya/runway_workspace/runway/run_poc/api/routes/net_worth_timeline.py)** - API Routes
   - `GET /api/v1/net-worth/timeline` - Fetch timeline
   - `GET /api/v1/net-worth/current` - Current snapshot
   - `POST /api/v1/net-worth/snapshot` - Create/update snapshot
   - `DELETE /api/v1/net-worth/snapshots/{month}` - Delete snapshot
   - `GET /api/v1/net-worth/snapshots` - List all snapshots

2. **[models.py](/Users/karthikeyaadhya/runway_workspace/runway/run_poc/storage/models.py)** - Database Model
   - Added `NetWorthSnapshot` model
   - User relationship configured
   - Indexes for performance

3. **[main.py](/Users/karthikeyaadhya/runway_workspace/runway/run_poc/api/main.py)** - Updated
   - Registered net_worth_timeline router

4. **[add_net_worth_snapshots.py](/Users/karthikeyaadhya/runway_workspace/runway/run_poc/migrations/add_net_worth_snapshots.py)** - Migration Script
   - Creates net_worth_snapshots table

---

## 🗄️ Database Schema

### **net_worth_snapshots Table**

| Column | Type | Description |
|--------|------|-------------|
| snapshot_id | String(36) | Primary key (UUID) |
| user_id | String(36) | Foreign key to users table |
| snapshot_date | String(10) | Snapshot date (YYYY-MM-DD) |
| month | String(7) | Month for grouping (YYYY-MM) [Indexed] |
| total_assets | Float | Total asset value at snapshot time |
| total_liabilities | Float | Total liabilities at snapshot time |
| net_worth | Float | Calculated net worth (assets - liabilities) |
| liquid_assets | Float | Total liquid assets |
| asset_breakdown | JSON | Asset breakdown by type |
| liability_breakdown | JSON | Liability breakdown by type |
| created_at | DateTime | Snapshot creation timestamp |

**Indexes:**
- `idx_net_worth_user_month` on (user_id, month)

---

## 🚀 Setup Instructions

### **Step 1: Run Database Migration**

```bash
cd /Users/karthikeyaadhya/runway_workspace/runway/run_poc

# Run the migration
python migrations/add_net_worth_snapshots.py
```

Expected output:
```
INFO - Starting migration: Add net_worth_snapshots table
INFO - Database URL: sqlite:///data/finance.db
INFO - Creating net_worth_snapshots table...
INFO - ✅ Migration completed successfully!
INFO - Table 'net_worth_snapshots' has been created.
```

### **Step 2: Restart Backend Server**

```bash
cd /Users/karthikeyaadhya/runway_workspace/runway/run_poc

# Restart the API server
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### **Step 3: Verify API Endpoints**

Visit: `http://localhost:8000/docs`

You should see new endpoints under **"Net Worth Timeline"** section:
- GET `/api/v1/net-worth/timeline`
- GET `/api/v1/net-worth/current`
- POST `/api/v1/net-worth/snapshot`
- DELETE `/api/v1/net-worth/snapshots/{month}`
- GET `/api/v1/net-worth/snapshots`

### **Step 4: Test Frontend**

```bash
cd /Users/karthikeyaadhya/runway_workspace/FIRE/runway-app

# Ensure dependencies are installed
npm install

# Start the frontend
npm start
```

Navigate to the **Wealth** tab to see the Net Worth Timeline chart.

---

## 📊 API Usage Examples

### **1. Get Timeline (12 months)**

```bash
curl -X GET "http://localhost:8000/api/v1/net-worth/timeline?months=12" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response:**
```json
{
  "timeline": [
    {
      "month": "2024-01",
      "assets": 5000000,
      "liabilities": 2000000,
      "net_worth": 3000000
    },
    {
      "month": "2024-02",
      "assets": 5200000,
      "liabilities": 1950000,
      "net_worth": 3250000
    }
  ],
  "has_historical_data": true,
  "months_requested": 12,
  "months_returned": 12
}
```

### **2. Get Current Net Worth**

```bash
curl -X GET "http://localhost:8000/api/v1/net-worth/current" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response:**
```json
{
  "user_id": "user-uuid",
  "calculated_at": "2024-10-27T10:30:00",
  "total_assets": 5500000,
  "total_liabilities": 1900000,
  "net_worth": 3600000,
  "liquid_assets": 1500000,
  "asset_breakdown": {
    "property": 3000000,
    "stocks": 1500000,
    "gold": 500000,
    "fd": 500000
  },
  "liability_breakdown": {
    "home_loan": 1500000,
    "car_loan": 400000
  }
}
```

### **3. Create Manual Snapshot**

```bash
curl -X POST "http://localhost:8000/api/v1/net-worth/snapshot" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response:**
```json
{
  "message": "Snapshot created",
  "snapshot_id": "snapshot-uuid",
  "month": "2024-10",
  "total_assets": 5500000,
  "total_liabilities": 1900000,
  "net_worth": 3600000,
  "liquid_assets": 1500000,
  "asset_breakdown": {...},
  "liability_breakdown": {...}
}
```

---

## 🔄 How It Works

### **Data Flow**

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Opens Wealth Tab                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  NetWorthTimeline Component Mounts                              │
│  └─> Calls getNetWorthTimeline(12) from API service           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Frontend API: GET /api/v1/net-worth/timeline?months=12        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Backend: net_worth_timeline.get_net_worth_timeline()          │
│  ├─> Query NetWorthSnapshot table for user's snapshots         │
│  ├─> If snapshots exist: Return timeline data                  │
│  └─> If no snapshots: Calculate from current assets/liabilities│
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Response: { timeline: [...], has_historical_data: true }      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  NetWorthTimeline Component                                     │
│  ├─> Transforms data for Recharts                              │
│  ├─> Renders AreaChart with Assets & Net Worth                 │
│  ├─> Shows growth indicator (↑ ₹50K, 5.2%)                    │
│  └─> Displays period toggles (3M, 6M, 1Y, All)                │
└─────────────────────────────────────────────────────────────────┘
```

### **Snapshot Creation**

**Automatic** (Recommended):
- Set up a cron job to call `POST /api/v1/net-worth/snapshot` on the 1st of each month
- This ensures historical data is captured

**Manual**:
- Users or admins can trigger snapshots via API
- Useful for testing or backfilling data

### **Fallback for New Users**

If no snapshots exist:
- Backend calculates current net worth from assets + liabilities
- Returns synthetic timeline (flat values for now)
- Once user creates snapshots, real historical data shows

---

## 🎨 Frontend Features

### **Interactive Chart**
- **Assets Line** (Blue): Shows total asset value
- **Net Worth Area** (Green): Main focus, filled gradient
- **Hover Tooltips**: Shows exact values for assets, liabilities, net worth

### **Time Period Selection**
- **3M**: Last 3 months
- **6M**: Last 6 months
- **1Y**: Last 12 months
- **All**: All available data

### **Growth Indicator**
- Shows absolute growth: ↑ ₹50,000
- Shows percentage: (5.2%)
- Green for positive, Red for negative

### **Smart States**
1. **Loading**: Spinner with "Loading timeline..." message
2. **Error**: Friendly error with retry button
3. **Empty**: "No Timeline Data Yet" with explanation
4. **Success**: Beautiful chart with data

---

## 🧪 Testing Guide

### **Test Case 1: New User (No Snapshots)**

1. Login as a new user
2. Navigate to Wealth tab
3. **Expected**: Chart shows "No Timeline Data Yet" message
4. Create assets and liabilities via UI
5. Call `POST /api/v1/net-worth/snapshot` via Postman or curl
6. Refresh page
7. **Expected**: Chart shows single data point for current month

### **Test Case 2: Existing User (With Snapshots)**

1. Create 12 monthly snapshots via API
2. Navigate to Wealth tab
3. **Expected**: Chart displays 12-month timeline
4. Toggle between 3M, 6M, 1Y, All
5. **Expected**: Chart updates to show selected period
6. Hover over data points
7. **Expected**: Tooltip shows detailed breakdown

### **Test Case 3: Growth Calculation**

1. Create snapshots with varying net worth values
2. View timeline
3. **Expected**: Growth indicator shows:
   - Positive growth: Green ↑ ₹X (Y%)
   - Negative growth: Red ↓ ₹X (Y%)

### **Test Case 4: API Error Handling**

1. Stop backend server
2. Navigate to Wealth tab
3. **Expected**: Error state with retry button
4. Restart server
5. Click retry
6. **Expected**: Chart loads successfully

---

## 🔧 Customization Options

### **Change Chart Colors**

Edit `NetWorthTimeline.jsx`:
```jsx
// Line colors
<Area stroke="#10b981" /> // Net Worth (green)
<Area stroke="#3b82f6" /> // Assets (blue)

// Gradient fills
<linearGradient id="colorNetWorth">
  <stop offset="5%" stopColor="#10b981" />
</linearGradient>
```

### **Change Default Period**

```jsx
const [selectedPeriod, setSelectedPeriod] = useState('6'); // Default to 6 months
```

### **Add More Periods**

```jsx
const periods = [
  { value: '1', label: '1M' },
  { value: '3', label: '3M' },
  { value: '6', label: '6M' },
  { value: '12', label: '1Y' },
  { value: '24', label: '2Y' },
  { value: 'all', label: 'All' }
];
```

---

## 📈 Future Enhancements

### **Planned Features**

1. **FIRE Goal Projection Line**
   - Show target net worth line on chart
   - Calculate trajectory to FIRE goal

2. **Annotations**
   - Mark major events (e.g., "Bought house", "Paid off loan")
   - Allow users to add notes to specific months

3. **Comparison Mode**
   - Compare this year vs last year
   - Show year-over-year growth

4. **Export Chart**
   - Download as PNG
   - Share on social media

5. **Automated Snapshots**
   - Background job to create monthly snapshots
   - Email alerts when net worth milestones reached

---

## 🐛 Troubleshooting

### **Issue: Chart Not Loading**

**Symptoms**: Spinner shows forever

**Solutions**:
1. Check backend is running: `curl http://localhost:8000/api/v1/net-worth/timeline`
2. Check browser console for errors
3. Verify JWT token is valid
4. Check backend logs for errors

### **Issue: "No Timeline Data Yet"**

**Symptoms**: Empty state shows even after creating assets

**Solutions**:
1. Create a snapshot: `POST /api/v1/net-worth/snapshot`
2. Verify snapshots exist: `GET /api/v1/net-worth/snapshots`
3. Check user_id matches between assets and snapshots

### **Issue: Chart Shows Flat Line**

**Symptoms**: Chart displays but all values are the same

**Solutions**:
1. This is expected for new users (fallback behavior)
2. Create snapshots over multiple months with varying values
3. Update asset/liability values between snapshots

### **Issue: Migration Fails**

**Symptoms**: Error when running add_net_worth_snapshots.py

**Solutions**:
1. Check database file exists
2. Verify DATABASE_URL in .env
3. Ensure no other process is locking the database
4. Check file permissions

---

## 📝 Files Modified/Created

### **Frontend Files**

| File | Type | Lines |
|------|------|-------|
| `/src/components/Modern/NetWorthTimeline.jsx` | New | 296 |
| `/src/api/services/netWorth.js` | New | 42 |
| `/src/components/Modern/ModernWealth.jsx` | Modified | +3 |

### **Backend Files**

| File | Type | Lines |
|------|------|-------|
| `/run_poc/api/routes/net_worth_timeline.py` | New | 308 |
| `/run_poc/storage/models.py` | Modified | +51 |
| `/run_poc/api/main.py` | Modified | +4 |
| `/run_poc/migrations/add_net_worth_snapshots.py` | New | 44 |

---

## ✅ Implementation Checklist

- [x] Create NetWorthSnapshot database model
- [x] Add database indexes for performance
- [x] Create API endpoints (GET timeline, POST snapshot, etc.)
- [x] Register router in main.py
- [x] Create database migration script
- [x] Build NetWorthTimeline React component
- [x] Add API service for frontend
- [x] Integrate timeline into ModernWealth page
- [x] Implement time period toggles
- [x] Add growth indicators
- [x] Handle loading/error/empty states
- [x] Create documentation

---

## 🎯 Next Steps

1. **Run the migration** to create the table
2. **Restart the backend** to load new endpoints
3. **Test the timeline** in the Wealth tab
4. **Create snapshots** manually or via cron
5. **Set up automated snapshots** (optional)

---

**Last Updated**: 2025-10-27
**Version**: 1.0
**Status**: ✅ Complete & Ready for Testing
