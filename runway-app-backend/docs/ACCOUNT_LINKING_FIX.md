# Fix: Account Linking to Test User

## Problem

Accounts created by `reset_and_setup.py` were not visible in the frontend.

### Root Causes

1. **KeyError:** Code tried to access `acc_data["current_balance"]` but user removed this key from sample_accounts
2. **Balance display error:** Print statement tried to format missing `current_balance`

## Solution

### Fix Applied

1. **Made `current_balance` optional:**
   ```python
   # Before:
   current_balance=acc_data["current_balance"]  # KeyError if missing
   
   # After:
   current_balance = acc_data.get("current_balance")  # Returns None if missing
   current_balance=current_balance,  # Can be None
   ```

2. **Fixed balance display:**
   ```python
   # Before:
   print(f"... (₹{acc_data['current_balance']:,.2f})")  # KeyError if missing
   
   # After:
   if current_balance is not None:
       balance_str = f"₹{current_balance:,.2f}"
   else:
       balance_str = "No balance set"
   print(f"... ({balance_str})")
   ```

3. **Added explicit linking comment:**
   ```python
   user_id=user.user_id,  # Link account to test user
   ```

## Verification

### Database Check
✅ **All 4 accounts are correctly linked:**
- Axis Bank - Axis Salary Account → Linked ✅
- HDFC Bank - HDFC Savings Account → Linked ✅
- ICICI Bank - ICICI Current Account → Linked ✅
- State Bank of India - SBI Credit Card → Linked ✅

### API Endpoint Check
✅ **API filters correctly:**
```python
accounts = session.query(Account).filter(
    Account.user_id == current_user.user_id,
    Account.is_active == True
).all()
```

## Result

✅ **Fixed!** Accounts are now:
- ✅ Created successfully (4 accounts)
- ✅ Linked to test user (user_id matches)
- ✅ Active (is_active = True)
- ✅ Visible via API endpoint (`/api/v1/accounts/`)

## Testing

**Test User Credentials:**
- Username: `test@example.com`
- Email: `test@example.com`
- Password: `testpassword123`

**Expected Result:**
- Login with test user
- Navigate to Accounts page
- Should see 4 accounts:
  1. HDFC Savings Account
  2. ICICI Current Account
  3. SBI Credit Card
  4. Axis Salary Account

## Next Steps

If accounts still don't appear in frontend:
1. **Check authentication:** Ensure you're logged in as test user
2. **Check API response:** Test `/api/v1/accounts/` endpoint
3. **Check browser console:** Look for API errors
4. **Check network tab:** Verify accounts endpoint returns data

## Files Modified

- `reset_and_setup.py`: Fixed account creation to handle optional `current_balance`

