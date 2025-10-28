# Runway Finance - Feature Roadmap

## Overview
This document outlines planned features for the Runway Finance application to enhance personal financial management and FIRE planning capabilities.

## Current System Status
- ✅ Authentication & User Management
- ✅ Transaction Management (CSV Upload, Categorization)
- ✅ Assets & Liabilities Tracking
- ✅ Salary Sweep Optimizer
- ✅ Loan Prepayment Optimizer
- ✅ Dashboard with Financial Metrics
- ✅ Reports & Analytics
- ✅ Centralized Recurring Payments System

---

## Planned Features

### 1. Financial Goals Tracker 🎯

**Description**: Track financial goals with visual progress indicators

**Features**:
- Set FIRE target amount with timeline
- Track multiple financial goals (emergency fund, house down payment, retirement, etc.)
- Visual progress bars and charts
- Projections based on current savings rate
- Milestone notifications
- Goal achievements tracking

**Implementation Requirements**:
- New `goals` table in database
- API endpoints for CRUD operations
- Frontend component for goal management
- Integration with dashboard for progress tracking

**Priority**: High

---

### 2. Net Worth Dashboard 💰

**Description**: Comprehensive view of total financial position

**Features**:
- Combined view of assets, liabilities, and net worth
- Historical net worth trends (line charts)
- Breakdown by asset type (liquid, investments, real estate, etc.)
- Monthly/Yearly comparison
- Projections based on growth rates

**Implementation Requirements**:
- Aggregate data from assets, liquidations, and liabilities
- Create time-series data storage
- Charts for net worth over time
- Export functionality for financial reviews

**Priority**: High

---

### 3. Budget Planning Tool 📊

**Description**: Create and track budgets against actual spending

**Features**:
- Set monthly budgets by category
- Real-time budget vs. actual spending
- Visual warnings for over-spending
- Category-level budget allocation
- Historical budget tracking
- Suggestions for budget optimization

**Implementation Requirements**:
- New `budgets` table in database
- Budget creation/editing UI
- Real-time spending comparison
- Alert system for budget violations
- Reports showing budget performance

**Priority**: Medium

---

### 4. Enhanced Expense Analytics 📈

**Description**: Deep dive into spending patterns and trends

**Features**:
- Daily, weekly, monthly spending views
- Interactive category charts (Pie, Bar, Line)
- Spending trends over time
- Top spending areas identification
- Comparison with previous periods
- Seasonal spending patterns

**Implementation Requirements**:
- Enhanced analytics API endpoints
- Time-based filtering and aggregation
- Chart library integration (e.g., Recharts)
- Export to CSV/PDF
- Mobile-responsive charts

**Priority**: Medium

---

### 5. Recurring Payments Manager 🔄

**Description**: Comprehensive management interface for all recurring obligations

**Features**:
- View all EMIs, SIPs, Insurance premiums from one place
- Edit/Delete/Update recurring payments
- Timeline view of upcoming payments
- Payment calendar integration
- Auto-categorization of recurring payments
- Payment history tracking

**Implementation Requirements**:
- Enhance centralized recurring payments UI
- CRUD operations for managing patterns
- Calendar view component
- Payment reminders
- Edit modal for updating details

**Priority**: High

---

### 6. Financial Forecast & Projections 📅

**Description**: Project future financial position based on current trajectory

**Features**:
- Project future net worth based on savings rate
- Multiple scenario modeling (conservative, optimistic)
- Years to FIRE calculation
- Retirement fund projections
- Asset growth forecasts
- Interaction: Adjust parameters to see outcomes

**Implementation Requirements**:
- Financial projection algorithms
- Scenario modeling backend
- Interactive slider controls in UI
- Visualization of projection graphs
- Sensitivity analysis

**Priority**: Medium

---

### 7. Export & Reporting System 📄

**Description**: Generate reports and export data for external analysis

**Features**:
- Export transaction history to CSV
- Export transaction history to PDF
- Monthly financial summaries
- Annual reports with charts
- Tax-friendly transaction summaries
- Custom date range exports
- Category-wise breakdown in exports

**Implementation Requirements**:
- CSV generation from transaction data
- PDF generation library (jsPDF or similar)
- Report templates
- Export API endpoints
- Download functionality
- Email reports option (future)

**Priority**: Medium

---

### 8. Notifications & Alerts System 🔔

**Description**: Keep users informed about important financial events

**Features**:
- EMI payment reminders
- Budget alerts when spending exceeds limits
- Goal milestone celebrations
- Large transaction alerts
- Anomaly detection (unusual spending patterns)
- Salary credit notifications
- Monthly summary emails

**Implementation Requirements**:
- Notification system architecture
- Alert rules engine
- Notification preferences management
- In-app notifications
- Email notifications
- Browser push notifications (optional)

**Priority**: Low (can be phased)

---

## Implementation Priority

### Phase 1 (High Priority - Q1)
1. Financial Goals Tracker
2. Net Worth Dashboard
3. Recurring Payments Manager

### Phase 2 (Medium Priority - Q2)
4. Budget Planning Tool
5. Enhanced Expense Analytics
6. Export & Reporting System

### Phase 3 (Future - Q3+)
7. Financial Forecast & Projections
8. Notifications & Alerts System

---

## Technical Considerations

### Database Schema Extensions

**Goals Table**:
```sql
CREATE TABLE goals (
    goal_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36),
    goal_name VARCHAR(255),
    target_amount FLOAT,
    current_amount FLOAT,
    deadline DATE,
    monthly_contribution FLOAT,
    goal_type VARCHAR(50), -- 'FIRE', 'Emergency Fund', 'House', etc.
    created_at DATETIME,
    updated_at DATETIME
);
```

**Budgets Table**:
```sql
CREATE TABLE budgets (
    budget_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36),
    month VARCHAR(7), -- YYYY-MM
    category VARCHAR(100),
    budgeted_amount FLOAT,
    actual_amount FLOAT,
    created_at DATETIME,
    updated_at DATETIME
);
```

**Net Worth History Table**:
```sql
CREATE TABLE net_worth_history (
    history_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36),
    date DATE,
    total_assets FLOAT,
    total_liabilities FLOAT,
    net_worth FLOAT,
    created_at DATETIME
);
```

### API Endpoints Needed

- `POST /api/v1/goals` - Create goal
- `GET /api/v1/goals` - Get all goals
- `PATCH /api/v1/goals/:id` - Update goal
- `DELETE /api/v1/goals/:id` - Delete goal
- `GET /api/v1/net-worth/history` - Get net worth history
- `POST /api/v1/budgets` - Create budget
- `GET /api/v1/budgets` - Get budgets
- `GET /api/v1/export/transactions` - Export transactions
- `GET /api/v1/export/report` - Generate report

---

## Notes

- All features should maintain consistency with existing UI/UX design
- Mobile responsiveness is critical for all new components
- Performance optimization required for large datasets
- User privacy and data security must be maintained
- Consider offline capabilities for mobile app version

---

**Last Updated**: October 27, 2025
**Version**: 1.0

