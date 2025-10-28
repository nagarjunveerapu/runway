# Sample Data Information

The app now includes sample financial data to demonstrate functionality.

## Sample Data Includes:

### Transactions (8 transactions):
- **Income**: Monthly salary entries (Jan, Feb, Mar 2025) - ₹1,20,000 each
- **Investments**: SIP contributions to Motilal Oswal Midcap - ₹5,000 each month
- **Expenses**: Groceries, Dining Out, EMI (Home Loan)

### Assets (3 assets):
- **Savings Account**: ₹2,00,000 (liquid)
- **Mutual Fund - Motilal Oswal Midcap**: ₹1,20,000 (liquid)
- **Home - Chennai**: ₹60,00,000 (non-liquid)

### Lookups:
- Income categories
- Expense categories
- Asset types
- Liability types
- Investment categories

## What You'll See on Dashboard:

After login, you should see:
- **Avg Monthly Income**: ₹1,20,000
- **Avg Net Flow**: Positive (income minus expenses)
- **Runway**: Calculated months based on liquid assets

## To Refresh the Data:

If you need to reload the sample data:
```bash
# The app automatically loads sample data on startup
# To reset: clear browser localStorage
```

## Important Notes:

- All sample data uses dates from 2025
- Amounts are in Indian Rupees (₹)
- Data is stored in browser localStorage
- Data persists across sessions

