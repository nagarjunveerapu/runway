# Net Worth Projection Endpoint Enhancement

## Overview

The `/api/v1/net-worth/projection` endpoint has been significantly enhanced to provide detailed liability tracking, accurate loan amortization calculations, and cash flow improvement insights.

## What's New

### 1. **Detailed Liability/Loan Data with EMI Details** ✅

Returns comprehensive information for each liability:
- Principal amount
- Current outstanding balance
- Interest rate
- EMI amount
- Original and remaining tenure
- Lender information
- Loan start date

### 2. **Future Timeline from Loan Amortization** ✅

Calculates accurate loan balances month-by-month using proper amortization schedules, showing:
- Exact loan paydown progression
- Remaining balance at each point
- Principal vs interest breakdown

### 3. **Extended Timeline with Historical Data** ✅

Combines historical net worth snapshots with future projections to show:
- Past performance (from snapshots)
- Present state (current calculation)
- Future trajectory (projected)

### 4. **Exact EMI Payoff Dates** ✅

Marks the precise month when each loan will be paid off:
- Accurate to the month level
- Sorted chronologically
- Includes remaining months count

### 5. **Cash Flow Improvement Tracking** ✅

Shows financial impact of each loan payoff:
- Monthly savings after each payoff
- Cumulative cash flow improvement
- Total cash freed up over time

### 6. **Visual Distinction Between Historical & Projected** ✅

Each timeline entry includes:
- `is_historical`: True for past data
- `is_projected`: True for future data
- Payoff event markers

## API Endpoint

### Request

```
GET /api/v1/net-worth/projection?years=5
```

**Parameters:**
- `years` (query param): Number of years to project ahead (1-30, default: 5)

### Response Structure

```json
{
  "timeline": [
    {
      "month": "2025-01",
      "assets": 5000000,
      "liabilities": 2800000,
      "net_worth": 2200000,
      "liquid_assets": 800000,
      "is_historical": false,
      "is_projected": true,
      "payoff_event": null,
      "cash_flow_improvement": 0,
      "cumulative_cash_flow_improvement": 0
    },
    {
      "month": "2027-06",
      "assets": 5700000,
      "liabilities": 1500000,
      "net_worth": 4200000,
      "liquid_assets": 1200000,
      "is_historical": false,
      "is_projected": true,
      "payoff_event": {
        "loan_name": "Personal Loan",
        "current_balance": 300000,
        "monthly_savings": 25000
      },
      "cash_flow_improvement": 25000,
      "cumulative_cash_flow_improvement": 25000
    }
  ],
  "historical_timeline": [
    {
      "month": "2024-06",
      "assets": 4500000,
      "liabilities": 3200000,
      "net_worth": 1300000,
      "is_historical": true
    }
  ],
  "liability_details": [
    {
      "liability_id": "loan-123",
      "name": "Home Loan",
      "type": "mortgage",
      "principal": 2500000,
      "current_balance": 2000000,
      "interest_rate": 8.5,
      "emi_amount": 28000,
      "original_tenure": 240,
      "remaining_months": 180,
      "lender": "HDFC Bank",
      "start_date": "2020-01-15"
    },
    {
      "liability_id": "loan-456",
      "name": "Personal Loan",
      "type": "loan",
      "principal": 500000,
      "current_balance": 300000,
      "interest_rate": 12.0,
      "emi_amount": 25000,
      "original_tenure": 24,
      "remaining_months": 8,
      "lender": "ICICI Bank",
      "start_date": "2024-06-01"
    }
  ],
  "total_monthly_emi": 53000,
  "loan_payoff_schedule": [
    {
      "name": "Personal Loan",
      "payoff_month": "2025-02",
      "months_remaining": 8,
      "current_balance": 300000,
      "emi_amount": 25000,
      "monthly_savings_after_payoff": 25000
    },
    {
      "name": "Home Loan",
      "payoff_month": "2039-08",
      "months_remaining": 180,
      "current_balance": 2000000,
      "emi_amount": 28000,
      "monthly_savings_after_payoff": 28000
    }
  ],
  "cash_flow_improvements": [
    {
      "month": "2025-02",
      "loan_name": "Personal Loan",
      "balance_paid_off": 300000,
      "monthly_cash_flow_improvement": 25000
    },
    {
      "month": "2039-08",
      "loan_name": "Home Loan",
      "balance_paid_off": 2000000,
      "monthly_cash_flow_improvement": 28000
    }
  ],
  "total_cash_flow_improvement": 53000,
  "crossover_point": null,
  "years_projected": 5,
  "final_net_worth": 6500000,
  "total_growth": 5200000,
  "insights": {
    "will_be_positive": true,
    "months_to_positive": null,
    "current_total_liabilities": 2300000,
    "total_loans": 2,
    "loans_with_emi": 2,
    "quickest_payoff": {
      "name": "Personal Loan",
      "payoff_month": "2025-02",
      "months_remaining": 8,
      "current_balance": 300000,
      "emi_amount": 25000,
      "monthly_savings_after_payoff": 25000
    }
  }
}
```

## Key Features

### Timeline Data

Each month in the timeline includes:
- **Financial metrics**: Assets, liabilities, net worth, liquid assets
- **Temporal markers**: `is_historical`, `is_projected` flags
- **Event markers**: `payoff_event` for loan completions
- **Cash flow data**: Immediate and cumulative improvements

### Liability Details

For each loan, you get:
- Complete loan terms
- Current status
- Amortization schedule
- Payoff timeline

### Loan Payoff Schedule

Sorted chronologically showing:
- When each loan completes
- Remaining months
- Cash flow benefit

### Cash Flow Improvements

Tracking how monthly obligations reduce over time:
- When loans complete
- How much is freed up
- Cumulative impact

### Insights

Summary information including:
- Total debt burden
- Number of active loans
- Quickest payoff opportunity
- Net worth trajectory

## Usage Examples

### Frontend Implementation

```javascript
// Fetch projection data
const response = await api.get('/net-worth/projection', {
  params: { years: 10 }
});

const projection = response.data;

// Display timeline with visual distinction
projection.timeline.forEach(month => {
  if (month.is_historical) {
    // Style historical data differently (e.g., solid line)
    styleHistorical(month);
  } else if (month.is_projected) {
    // Style projected data differently (e.g., dashed line)
    styleProjected(month);
  }
  
  // Highlight payoff events
  if (month.payoff_event) {
    markPayoffEvent(month);
  }
});

// Show cash flow improvements
projection.cash_flow_improvements.forEach(improvement => {
  displayMessage(
    `After ${improvement.month}, ${improvement.loan_name} completed.
     Monthly cash flow improves by ₹${improvement.monthly_cash_flow_improvement}`
  );
});
```

### Display Loan Schedule

```javascript
// Show user when loans will complete
projection.loan_payoff_schedule.forEach(loan => {
  const daysUntilPayoff = calculateDaysUntil(loan.payoff_month);
  
  displayCard({
    title: loan.name,
    body: `${daysUntilPayoff} days until payoff`,
    highlight: `+₹${loan.monthly_savings_after_payoff}/month cash flow`
  });
});
```

### Visual Timeline Chart

```javascript
// Create chart with historical and projected data
const chartData = projection.historical_timeline
  .concat(projection.timeline)
  .sort((a, b) => a.month.localeCompare(b.month));

// Style based on data type
const lineStyles = {
  historical: { stroke: '#3b82f6', strokeWidth: 2, strokeDasharray: '0' },
  projected: { stroke: '#10b981', strokeWidth: 2, strokeDasharray: '5 5' }
};

// Add payoff markers
chartData.forEach(month => {
  if (month.payoff_event) {
    addMarker({
      x: month.month,
      y: month.net_worth,
      label: month.payoff_event.loan_name,
      symbol: '🎯'
    });
  }
});
```

## Benefits

1. **Accurate Planning**: Users see exactly when loans will be paid off
2. **Cash Flow Visibility**: Understand financial improvement timeline
3. **Holistic View**: Historical context + future projections
4. **Clear Distinction**: Visual separation of fact vs prediction
5. **Financial Insights**: Quick understanding of debt trajectory

## Technical Details

### Loan Amortization

Uses standard EMI formula:
```
EMI = P × r × (1 + r)^n / ((1 + r)^n - 1)
```

Where:
- P = Principal
- r = Monthly interest rate
- n = Number of months

### Timeline Calculation

For each month in projection:
1. Calculate asset values (with optional appreciation)
2. Calculate liability balances using amortization
3. Calculate net worth
4. Check for loan payoffs
5. Calculate cash flow improvements
6. Mark historical vs projected

### Data Sources

- **Historical**: From `NetWorthSnapshot` table
- **Current**: Real-time calculation from `Asset` and `Liability` tables
- **Projected**: Calculated using `project_future_net_worth()`

## Future Enhancements

Potential improvements:
- Support for prepayments
- Variable interest rates
- New loan addition during projection
- Investment growth projections
- Goal-based projections (FIRE calculations)

