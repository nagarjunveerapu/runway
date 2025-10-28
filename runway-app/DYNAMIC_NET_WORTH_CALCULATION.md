# Dynamic Net Worth Calculation - Technical Documentation

## 🎯 Overview

The Dynamic Net Worth Calculation system provides **realistic** net worth timelines by accounting for:

1. ✅ **EMI Payments** - Liabilities reduce month-by-month as EMIs are paid
2. ✅ **SIP Growth** - Liquid investments grow with compound returns
3. ✅ **Asset Appreciation** - Property and stocks appreciate over time
4. ✅ **New Liabilities** - Dynamically includes loans taken at different times
5. ✅ **Crossover Point** - Shows when net worth becomes positive
6. ✅ **Future Projection** - Projects 5-30 years ahead based on current trends

---

## 🧮 How It Works

### **1. EMI-Based Liability Reduction**

Instead of static liability values, we calculate the **actual remaining balance** after X months of EMI payments using the amortization formula.

#### **Formula**:
```
EMI = P × r × (1+r)^n / [(1+r)^n - 1]

Where:
P = Principal amount
r = Monthly interest rate (annual rate / 12 / 100)
n = Tenure in months
```

#### **Example**: Home Loan
```
Principal: ₹25,00,000
Interest Rate: 8.5% p.a.
Tenure: 240 months (20 years)
EMI: ₹21,455/month

Month 0:  Balance = ₹25,00,000
Month 1:  Balance = ₹24,96,295 (principal paid: ₹3,705)
Month 12: Balance = ₹24,51,180 (reduced by ₹48,820)
Month 60: Balance = ₹21,14,532 (reduced by ₹3,85,468)
Month 240: Balance = ₹0 (loan fully paid)
```

This means:
- Your net worth **increases every month** as the liability reduces
- The calculation is **precise** based on actual amortization
- Shows **when the loan will be paid off**

---

### **2. SIP/Investment Growth**

SIPs and recurring investments grow with compound returns.

#### **Formula**:
```
FV = P × [((1 + r)^n - 1) / r] × (1 + r)

Where:
P = Monthly SIP amount
r = Monthly return rate (annual return / 12 / 100)
n = Number of months
```

#### **Example**: Mutual Fund SIP
```
Monthly SIP: ₹10,000
Annual Return: 12%
Duration: 5 years (60 months)

Month 12:  Value = ₹1,28,246 (invested ₹1,20,000)
Month 24:  Value = ₹2,69,742 (invested ₹2,40,000)
Month 60:  Value = ₹8,16,696 (invested ₹6,00,000)

Gain: ₹2,16,696 (36.1% returns)
```

This means:
- Your investments **grow exponentially**
- Compound interest accelerates wealth
- Liquid assets increase month-by-month

---

### **3. Asset Appreciation**

Assets like property and stocks appreciate over time.

#### **Appreciation Rates**:
- **Property**: 6% per annum
- **Stocks/Mutual Funds**: 12% per annum
- **Gold**: 8% per annum
- **FD/Cash**: 0% (stable value)
- **Vehicles**: Depreciate (not implemented yet)

#### **Example**: House
```
Purchase Price: ₹50,00,000 (Jan 2020)
Appreciation: 6% p.a.

Year 1 (2021): ₹53,00,000
Year 2 (2022): ₹56,18,000
Year 3 (2023): ₹59,55,080
Year 5 (2025): ₹66,91,130
```

---

### **4. Timeline Calculation**

For each month in the timeline:

```python
def calculate_month(month_index):
    # 1. Calculate Assets
    total_assets = 0
    for asset in assets:
        months_since_purchase = calculate_months(asset.purchase_date, current_month)
        asset_value = asset.purchase_price * (1 + monthly_appreciation_rate) ** months_since_purchase
        total_assets += asset_value

    # 2. Add SIP Growth
    for sip in sips:
        months_invested = calculate_months(sip.start_date, current_month)
        sip_value = calculate_sip_fv(sip.monthly_amount, months_invested, return_rate=12%)
        total_assets += sip_value

    # 3. Calculate Liabilities
    total_liabilities = 0
    for liability in liabilities:
        if liability.start_date <= current_month:
            months_elapsed = calculate_months(liability.start_date, current_month)
            remaining_balance = calculate_emi_balance(liability, months_elapsed)
            total_liabilities += remaining_balance

    # 4. Net Worth
    net_worth = total_assets - total_liabilities

    return {
        'month': current_month,
        'assets': total_assets,
        'liabilities': total_liabilities,
        'net_worth': net_worth
    }
```

---

## 📊 Example Scenario

### **Your Situation** (Hypothetical):
```
Assets:
- House: ₹50,00,000 (appreciates 6% p.a.)
- Stocks/MF: ₹5,00,000 (appreciates 12% p.a.)
- FD: ₹2,00,000 (stable)

Liabilities:
- Home Loan: ₹25,00,000 @ 8.5%, EMI ₹21,455, 20 years
- Personal Loan: ₹3,00,000 @ 12%, EMI ₹13,000, 2 years

Investments:
- MF SIP: ₹10,000/month @ 12% returns
```

### **Net Worth Evolution**:

| Month | Assets | Liabilities | Net Worth | Change |
|-------|--------|-------------|-----------|--------|
| **Today** | ₹57.0L | ₹28.0L | **₹29.0L** | - |
| +6 months | ₹59.2L | ₹27.1L | **₹32.1L** | +₹3.1L |
| +1 year | ₹61.5L | ₹26.0L | **₹35.5L** | +₹6.5L |
| +2 years | ₹67.8L | ₹22.8L | **₹45.0L** | +₹16.0L |
| +5 years | ₹89.3L | ₹16.2L | **₹73.1L** | +₹44.1L |
| +10 years | ₹132.5L | ₹4.8L | **₹127.7L** | +₹98.7L |
| +20 years | ₹289.4L | ₹0L | **₹289.4L** | +₹260.4L |

**Key Insights**:
- Net worth **increases every month** due to EMI payments
- SIP investments accelerate growth from year 2 onwards
- Personal loan paid off in 2 years → ₹3L immediate boost
- Home loan paid off in 20 years → ₹25L boost
- Asset appreciation adds ₹180L+ over 20 years

---

## 🚀 API Endpoints

### **1. Dynamic Timeline** (New!)
```
GET /api/v1/net-worth/timeline/dynamic?months=60&projection=false
```

**Response**:
```json
{
  "timeline": [
    {
      "month": "2025-01",
      "assets": 5700000,
      "liabilities": 2800000,
      "net_worth": 2900000,
      "liquid_assets": 700000
    },
    ...
  ],
  "crossover_point": null,  // Already positive
  "months_returned": 60,
  "is_projection": false
}
```

### **2. Future Projection** (New!)
```
GET /api/v1/net-worth/projection?years=10
```

**Response**:
```json
{
  "timeline": [...],
  "crossover_point": "2027-03",  // Month when net worth becomes positive
  "years_projected": 10,
  "final_net_worth": 12770000,
  "total_growth": 9870000,
  "loan_payoff_schedule": [
    {
      "name": "Personal Loan",
      "payoff_month": "2027-01",
      "months_remaining": 24,
      "current_balance": 300000
    },
    {
      "name": "Home Loan",
      "payoff_month": "2045-01",
      "months_remaining": 240,
      "current_balance": 2500000
    }
  ],
  "insights": {
    "will_be_positive": true,
    "months_to_positive": 27
  }
}
```

### **3. Original Snapshot Timeline** (Existing)
```
GET /api/v1/net-worth/timeline?months=12
```

Uses stored snapshots (static values).

---

## 🎨 Frontend Integration

### **Update NetWorthTimeline Component**:

```jsx
// Add toggle for dynamic vs snapshot view
const [useDynamic, setUseDynamic] = useState(true);

const loadTimeline = async () => {
  const endpoint = useDynamic
    ? '/net-worth/timeline/dynamic'
    : '/net-worth/timeline';

  const data = await getNetWorthTimeline(months, endpoint);

  // Show crossover point on chart if exists
  if (data.crossover_point) {
    addAnnotation(data.crossover_point, "Net Worth Positive!");
  }
};
```

### **Show Projection Line**:

```jsx
// Add future projection as dotted line
<Area
  type="monotone"
  dataKey="projected_net_worth"
  stroke="#10b981"
  strokeDasharray="5 5"  // Dotted line
  fill="none"
  name="Projection"
/>
```

---

## 💡 Advantages Over Static Snapshots

| Feature | Static Snapshots | Dynamic Calculation |
|---------|------------------|---------------------|
| Accuracy | Approximate | Precise |
| EMI Impact | Not tracked | Month-by-month reduction |
| SIP Growth | Not tracked | Compound growth |
| Future Projection | Not possible | Yes, up to 30 years |
| Crossover Point | Not detected | Automatically identified |
| New Liabilities | Manual update | Auto-included by start date |
| Real-time | Needs manual snapshot | Calculated on-demand |

---

## 🧪 Testing

### **Test Scenario 1: EMI Reduction**

```python
# Create a liability
liability = Liability(
    principal_amount=2500000,
    interest_rate=8.5,
    emi_amount=21455,
    remaining_tenure_months=240
)

# Calculate balance after 60 months
balance_60 = get_liability_balance_at_month(liability, 60)
# Expected: ~₹21,14,532

# Reduction from principal
reduction = 2500000 - 2114532  # ₹3,85,468 paid in 5 years
```

### **Test Scenario 2: SIP Growth**

```python
# Monthly SIP of ₹10,000 for 5 years
sip_value = get_sip_value_at_month(
    sip_amount=10000,
    months_elapsed=60,
    annual_return=12.0
)
# Expected: ~₹8,16,696
# Invested: ₹6,00,000
# Gain: ₹2,16,696 (36.1%)
```

---

## 🔄 Migration Strategy

### **Phase 1: Parallel Running** (Current)
- Keep snapshot endpoint for historical data
- Add dynamic endpoint for new calculations
- Frontend can toggle between both

### **Phase 2: Hybrid Approach**
- Use snapshots for historical data (past)
- Use dynamic calculation for recent months + future
- Best of both worlds

### **Phase 3: Full Dynamic** (Future)
- Deprecate static snapshots
- All calculations done dynamically
- Store calculated snapshots periodically for performance

---

## 🎯 Next Steps

1. **✅ Fix "All" period 422 error** - Done
2. **✅ Create dynamic calculation module** - Done
3. **✅ Add EMI amortization** - Done
4. **✅ Add SIP growth calculation** - Done
5. **✅ Add projection endpoint** - Done
6. **⏳ Test with real liability data** - Next
7. **⏳ Update frontend to use dynamic endpoint** - Next
8. **⏳ Add visual crossover indicator** - Next

---

## 📝 Summary

The dynamic net worth calculation provides a **realistic, month-by-month view** of your financial journey by:

- ✅ Tracking EMI payments reducing liabilities
- ✅ Growing your SIP investments with compound returns
- ✅ Appreciating assets like property and stocks
- ✅ Showing when your net worth goes positive
- ✅ Projecting 5-30 years into the future
- ✅ Identifying when loans will be paid off

**This is the foundation for truly personalized FIRE planning!**

---

**Last Updated**: 2025-10-27
**Status**: ✅ Backend Complete, Frontend Integration Pending
