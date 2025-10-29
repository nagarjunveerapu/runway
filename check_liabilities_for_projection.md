# Why Your Net Worth Timeline Shows Flat Lines

## The Issue

Your timeline shows flat lines because:
1. **No EMI details configured**: The projection needs loan details to calculate paydown
2. **No historical snapshots**: Without snapshots, the basic endpoint returns flat data
3. **Projection requires specific fields**: Your liabilities need EMI info to generate dynamic projections

## Solution: Add EMI Details to Your Liabilities

### Check Your Current Liabilities

1. Go to the **Liabilities** page in the app
2. Check if your loans have these fields filled:
   - ✅ Principal Amount
   - ✅ Outstanding Balance
   - ⚠️ **EMI Amount** (required for projection)
   - ⚠️ **Interest Rate** (required for accurate amortization)
   - ⚠️ **Remaining Tenure (months)** (required for payoff timeline)

### Add EMI Details

For each loan/liability, edit it and add:
- **EMI Amount**: Monthly payment (e.g., ₹25,000)
- **Interest Rate**: Annual rate (e.g., 8.5%)
- **Remaining Tenure**: Months left (e.g., 48)

### Example: Car Loan

```
Name: HDFC Car Loan
Principal Amount: ₹500,000
Outstanding Balance: ₹300,000
EMI Amount: ₹25,000
Interest Rate: 10%
Remaining Tenure: 12 months
Lender: HDFC Bank
```

## What Happens When You Add EMI Details

Once you add EMI info and refresh:
1. **Liabilities line will slope downward** (debt reduces each month)
2. **Net Worth line will slope upward** (net worth increases)
3. **Payoff markers appear** (🎯 at loan completion dates)
4. **Cash flow improvements show** (monthly savings after payoff)

## Quick Test

1. **Edit a liability** (e.g., "Car Loan")
2. **Add EMI**: ₹20,000/month
3. **Add Interest**: 10%
4. **Add Remaining**: 24 months
5. **Save**
6. **Refresh the Wealth page**

The timeline should now show a downward slope for liabilities and upward slope for net worth!

## Debug: Check Console

Open browser DevTools (F12) → Console tab. You should see:

```
Timeline response: { timeline: [...], ... }
Has historical data: false/true
Timeline length: 12
```

If projection failed:
```
Projection failed, falling back to static timeline
```

This means your liabilities don't have EMI details yet.

