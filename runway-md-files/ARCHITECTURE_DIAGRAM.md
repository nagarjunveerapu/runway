# Centralized Recurring Payments Architecture

## System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER JOURNEY                             │
└─────────────────────────────────────────────────────────────────┘

Step 1: ONE-TIME SETUP (Salary Sweep Optimizer)
┌──────────────────────────────────────────────────────────────────┐
│  User clicks "Detect Salary & EMI Patterns"                      │
│                                                                   │
│  ┌────────────────────────────────────────────────────┐         │
│  │  Backend: Analyze all transactions                  │         │
│  │  - Filter debits (min ₹500)                        │         │
│  │  - Skip UPI/transfers                              │         │
│  │  - Check keywords for categories                   │         │
│  │    • Loans: canfin, bajaj, emi, loan              │         │
│  │    • Insurance: sbi life, lic, insurance          │         │
│  │    • Investments: mutual fund, sip, zerodha       │         │
│  │    • Govt Schemes: apy, nps, ppf, epf             │         │
│  │  - Detect exact amount + 2+ months patterns       │         │
│  │  - Auto-categorize using categorize_recurring_payment()│    │
│  └────────────────────────────────────────────────────┘         │
│                           ↓                                       │
│  ┌────────────────────────────────────────────────────┐         │
│  │  Frontend: Display categorized patterns             │         │
│  │                                                      │         │
│  │  🏦 Loans (2)                                       │         │
│  │  ☐ Canfin Homes - ₹31,453 [🏦 Home Loan]         │         │
│  │  ☐ Bajaj Finserv - ₹65,328 [🏦 Personal Loan]    │         │
│  │                                                      │         │
│  │  🛡️ Insurance (1)                                  │         │
│  │  ☐ SBI Life - ₹25,000 [🛡️ Life Insurance]        │         │
│  │                                                      │         │
│  │  📈 Investments (1)                                 │         │
│  │  ☐ HDFC SIP - ₹10,000 [📈 Mutual Fund SIP]       │         │
│  │                                                      │         │
│  │  🏛️ Government Schemes (1)                         │         │
│  │  ☐ APY - ₹1,000 [🏛️ APY]                         │         │
│  └────────────────────────────────────────────────────┘         │
│                           ↓                                       │
│  User selects desired payments and clicks "Save"                 │
│                           ↓                                       │
│  ┌────────────────────────────────────────────────────┐         │
│  │  Database: Save to detected_emi_patterns           │         │
│  │                                                      │         │
│  │  Table: detected_emi_patterns                       │         │
│  │  ┌─────────────┬─────────────┬──────────┬─────────┐│         │
│  │  │ pattern_id  │ merchant    │ category │ amount  ││         │
│  │  ├─────────────┼─────────────┼──────────┼─────────┤│         │
│  │  │ uuid-1      │ Canfin      │ Loan     │ 31453   ││         │
│  │  │ uuid-2      │ SBI Life    │ Insurance│ 25000   ││         │
│  │  │ uuid-3      │ HDFC SIP    │ Investment│ 10000  ││         │
│  │  │ uuid-4      │ APY         │ Govt     │ 1000    ││         │
│  │  └─────────────┴─────────────┴──────────┴─────────┘│         │
│  └────────────────────────────────────────────────────┘         │
└──────────────────────────────────────────────────────────────────┘

Step 2: REUSE EVERYWHERE
┌──────────────────────────────────────────────────────────────────┐
│                                                                   │
│  Centralized API Endpoint                                        │
│  ┌────────────────────────────────────────────────────┐         │
│  │  GET /api/salary-sweep/recurring-payments          │         │
│  │                                                      │         │
│  │  Returns:                                            │         │
│  │  {                                                   │         │
│  │    "loans": [uuid-1, uuid-2],                      │         │
│  │    "insurance": [uuid-3],                          │         │
│  │    "investments": [uuid-4],                        │         │
│  │    "government_schemes": [uuid-5]                  │         │
│  │  }                                                   │         │
│  └────────────────────────────────────────────────────┘         │
│                           ↓                                       │
│         ┌────────────────┼────────────────┬────────────┐        │
│         │                │                │            │        │
│         ↓                ↓                ↓            ↓        │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────┐   │
│  │   Loan      │ │  Investment  │ │Insurance │ │  Pension │   │
│  │ Optimizer   │ │  Dashboard   │ │ Tracker  │ │ Tracker  │   │
│  └─────────────┘ └──────────────┘ └──────────┘ └──────────┘   │
│         │                │                │            │        │
│         ↓                ↓                ↓            ↓        │
│  Uses loans[]    Uses investments[] Uses insurance[] Uses      │
│  + asks for:     + asks for:        + asks for:    govt[]     │
│  - Principal     - Current Value    - Policy #     schemes    │
│  - Interest      - Returns          - Sum Assured             │
│  - Tenure        - Asset Class      - Maturity                │
│                                                                 │
└──────────────────────────────────────────────────────────────────┘
```

## Data Flow Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                      BACKEND (Python/FastAPI)                     │
└──────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│  ML Model (categorizer.pkl)                                     │
│  - Trained on 13 categories                                     │
│  - 85.6% accuracy                                               │
│  - Used as fallback if keyword matching fails                   │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│  Detection Logic (salary_sweep_v2.py)                          │
│                                                                 │
│  1. Filter transactions                                         │
│     - Type: debit                                               │
│     - Amount: ≥ ₹500                                           │
│     - Exclude: UPI, transfers                                   │
│                                                                 │
│  2. Keyword Matching (Primary)                                  │
│     categorize_recurring_payment(merchant, description)        │
│     - Check loan keywords → ('Loan', 'Home Loan')             │
│     - Check insurance keywords → ('Insurance', 'Life')         │
│     - Check investment keywords → ('Investment', 'SIP')        │
│     - Check govt keywords → ('Government Scheme', 'APY')       │
│                                                                 │
│  3. Pattern Detection                                           │
│     - Group by merchant + exact amount                          │
│     - Require: 2+ occurrences in different months              │
│                                                                 │
│  4. Response                                                    │
│     - Each pattern includes category + subcategory              │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│  Database (SQLite)                                              │
│                                                                 │
│  Table: detected_emi_patterns                                   │
│  ┌────────────────┬──────────┬──────────────┬─────────────┐   │
│  │ Field          │ Type     │ Example      │ Purpose     │   │
│  ├────────────────┼──────────┼──────────────┼─────────────┤   │
│  │ pattern_id     │ UUID     │ abc-123-def  │ Primary key │   │
│  │ merchant_source│ String   │ Canfin Homes │ Display name│   │
│  │ emi_amount     │ Float    │ 31453.0      │ Monthly amt │   │
│  │ category       │ String   │ Loan         │ Category    │   │
│  │ subcategory    │ String   │ Home Loan    │ Subtype     │   │
│  │ is_confirmed   │ Boolean  │ true         │ User saved  │   │
│  └────────────────┴──────────┴──────────────┴─────────────┘   │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│  API Endpoint                                                   │
│  GET /api/salary-sweep/recurring-payments                       │
│                                                                 │
│  Response:                                                      │
│  {                                                              │
│    "loans": [{                                                  │
│      "pattern_id": "abc-123",                                  │
│      "merchant_source": "Canfin Homes",                        │
│      "emi_amount": 31453.0,                                    │
│      "category": "Loan",                                        │
│      "subcategory": "Home Loan",                               │
│      "occurrence_count": 6,                                     │
│      "first_detected_date": "01/01/2025"                       │
│    }],                                                          │
│    "insurance": [...],                                          │
│    "investments": [...],                                        │
│    "government_schemes": [...]                                  │
│  }                                                              │
└────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                      FRONTEND (React)                             │
└──────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│  API Service (recurringPayments.js)                            │
│                                                                 │
│  getAllRecurringPayments()  → Returns all categories           │
│  getLoans()                 → Returns loans[] only             │
│  getInsurance()             → Returns insurance[] only         │
│  getInvestments()           → Returns investments[] only       │
│  getGovernmentSchemes()     → Returns govt_schemes[] only      │
│                                                                 │
│  transformToLoan()          → Add loan-specific fields         │
│  transformToInvestment()    → Add investment-specific fields   │
│  transformToInsurance()     → Add insurance-specific fields    │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│  Feature Components                                             │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  SalarySweepOptimizerV2                                   │ │
│  │  - Uses ALL categories                                    │ │
│  │  - Displays with category badges                         │ │
│  │  - Shows category breakdown                              │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  LoanOptimizer                                            │ │
│  │  const loans = await getLoans();                         │ │
│  │  - Pre-filled: merchant, monthlyEMI, category           │ │
│  │  - User fills: principal, interest, tenure               │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  InvestmentDashboard                                      │ │
│  │  const investments = await getInvestments();             │ │
│  │  - Pre-filled: name, monthlyAmount, startDate           │ │
│  │  - User fills: currentValue, returns                     │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  InsuranceTracker                                         │ │
│  │  const insurance = await getInsurance();                 │ │
│  │  - Pre-filled: policyName, premium, type                │ │
│  │  - User fills: sumAssured, policyNumber                 │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

## Category Mapping

```
┌──────────────────────────────────────────────────────────────────┐
│  LOAN (🏦 Blue)                                                  │
├──────────────────────────────────────────────────────────────────┤
│  Keywords:                                                        │
│  - Merchants: canfin, bajaj finserv, bajaj finance, tata capital│
│               hdfc, icici, sbi, iifl, mahindra finance           │
│  - Description: emi, loan, housing, mortgage, auto loan          │
│                                                                   │
│  Subcategories:                                                   │
│  • Home Loan    - Keywords: home, housing, canfin               │
│  • Auto Loan    - Keywords: car, auto, vehicle                  │
│  • Personal Loan - Keywords: personal, pl                        │
│  • EMI          - Default                                        │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  INSURANCE (🛡️ Purple)                                           │
├──────────────────────────────────────────────────────────────────┤
│  Keywords:                                                        │
│  - sbi life, lic, hdfc life, icici prudential, max life         │
│    bajaj allianz, tata aia, birla sun life, insurance           │
│    kotak life, star health, care health                          │
│                                                                   │
│  Subcategories:                                                   │
│  • Life Insurance   - Keywords: life, term                       │
│  • Health Insurance - Keywords: health, mediclaim                │
│  • Insurance Premium - Default                                   │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  INVESTMENT (📈 Green)                                           │
├──────────────────────────────────────────────────────────────────┤
│  Keywords:                                                        │
│  - mutual fund, sip, systematic, zerodha, groww                 │
│    paytm money, et money, kuvera, coin dcb                       │
│    hdfc mf, icici mf, sbi mf, axis mf, kotak mf                 │
│                                                                   │
│  Subcategories:                                                   │
│  • Mutual Fund SIP - Keywords: sip, systematic                   │
│  • Investment      - Default                                     │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  GOVERNMENT SCHEME (🏛️ Amber)                                   │
├──────────────────────────────────────────────────────────────────┤
│  Keywords:                                                        │
│  - apy, atal pension, nps, national pension, ppf                │
│    public provident, epf, employee provident, esi                │
│    sukanya samriddhi, pmjjby, pmsby                              │
│                                                                   │
│  Subcategories:                                                   │
│  • APY - Keywords: apy, atal pension                            │
│  • NPS - Keywords: nps, national pension                        │
│  • PPF - Keywords: ppf, public provident                        │
│  • EPF - Keywords: epf, employee provident                      │
│  • Govt Scheme - Default                                        │
└──────────────────────────────────────────────────────────────────┘
```

## Benefits Summary

```
┌──────────────────────────────────────────────────────────────────┐
│  ✅ BEFORE (Without Centralized System)                          │
├──────────────────────────────────────────────────────────────────┤
│  1. User goes to Loan Optimizer                                  │
│     → Detects EMIs from transactions (1000+ transactions)        │
│     → User selects 2 loan EMIs                                   │
│                                                                   │
│  2. User goes to Investment Dashboard                            │
│     → Detects EMIs from transactions AGAIN (1000+ transactions)  │
│     → User selects 1 SIP                                         │
│                                                                   │
│  3. User goes to Insurance Tracker                               │
│     → Detects EMIs from transactions AGAIN (1000+ transactions)  │
│     → User selects 1 insurance                                   │
│                                                                   │
│  Problems:                                                        │
│  ❌ Redundant detection (3x processing)                          │
│  ❌ User re-enters same data 3 times                             │
│  ❌ No single source of truth                                    │
│  ❌ Inconsistent data across features                            │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  ✅ AFTER (With Centralized System)                              │
├──────────────────────────────────────────────────────────────────┤
│  1. User goes to Salary Sweep (One-time)                         │
│     → Detects ALL recurring payments (1x processing)             │
│     → Auto-categorizes (Loans, Insurance, Investments, Schemes)  │
│     → User confirms 4 payments                                   │
│     → Saved to database with categories                          │
│                                                                   │
│  2. User goes to Loan Optimizer                                  │
│     → Fetches loans from saved data (instant)                    │
│     → Shows 2 pre-configured loans                               │
│     → User only fills loan-specific fields                       │
│                                                                   │
│  3. User goes to Investment Dashboard                            │
│     → Fetches investments from saved data (instant)              │
│     → Shows 1 pre-configured SIP                                 │
│     → User only fills investment-specific fields                 │
│                                                                   │
│  4. User goes to Insurance Tracker                               │
│     → Fetches insurance from saved data (instant)                │
│     → Shows 1 pre-configured policy                              │
│     → User only fills insurance-specific fields                  │
│                                                                   │
│  Benefits:                                                        │
│  ✅ One-time detection (1x processing)                           │
│  ✅ User configures once, uses everywhere                        │
│  ✅ Single source of truth                                       │
│  ✅ Consistent data across features                              │
│  ✅ Faster feature adoption                                      │
│  ✅ Better user experience                                       │
└──────────────────────────────────────────────────────────────────┘
```
