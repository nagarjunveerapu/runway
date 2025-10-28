# Frontend Refactoring Plan

## Goal
Transform the frontend into a modular, scalable architecture with clear separation of concerns.

## Current Issues
- Tight coupling between components
- Business logic mixed with UI
- Duplicated code across components
- No clear feature boundaries
- Hard to maintain and extend

## Proposed Architecture

```
src/
├── shared/                    # Shared components and utilities
│   ├── ui/                    # Reusable UI components
│   │   ├── Button/
│   │   ├── Card/
│   │   ├── LoadingSpinner/
│   │   ├── EmptyState/
│   │   └── index.js
│   ├── hooks/                 # Custom React hooks
│   │   ├── useAuth.js
│   │   ├── useTransactions.js
│   │   ├── useAssets.js
│   │   └── useDebounce.js
│   ├── utils/                 # Utility functions
│   │   ├── formatters.js
│   │   ├── validators.js
│   │   └── constants.js
│   └── components/            # Shared complex components
│       ├── Layout/
│       ├── Sidebar/
│       └── Header/
│
├── features/                   # Feature modules
│   ├── dashboard/
│   │   ├── components/
│   │   │   ├── DashboardMetrics.jsx
│   │   │   └── KPISummary.jsx
│   │   ├── hooks/
│   │   │   └── useDashboard.js
│   │   └── DashboardPage.jsx
│   │
│   ├── reports/
│   │   ├── fire-calculator/
│   │   │   ├── FIRECalculator.jsx
│   │   │   └── hooks/useFIREMetrics.js
│   │   ├── emergency-fund/
│   │   │   ├── EmergencyFundHealth.jsx
│   │   │   └── hooks/useEmergencyFund.js
│   │   ├── salary-sweep/
│   │   │   ├── SalarySweepOptimizer.jsx
│   │   │   └── hooks/useSalarySweep.js
│   │   ├── loan-prepayment/
│   │   │   ├── LoanPrepaymentOptimizer.jsx
│   │   │   └── hooks/useLoanPrepayment.js
│   │   ├── recurring-payments/
│   │   │   ├── RecurringPayments.jsx
│   │   │   └── hooks/useRecurringPayments.js
│   │   └── ReportsPage.jsx
│   │
│   ├── transactions/
│   │   ├── components/
│   │   │   ├── TransactionList.jsx
│   │   │   ├── TransactionForm.jsx
│   │   │   └── TransactionFilters.jsx
│   │   ├── hooks/
│   │   │   └── useTransactions.js
│   │   └── TransactionsPage.jsx
│   │
│   ├── assets/
│   │   ├── components/
│   │   │   ├── AssetsList.jsx
│   │   │   └── AssetForm.jsx
│   │   ├── hooks/
│   │   │   └── useAssets.js
│   │   └── AssetsPage.jsx
│   │
│   ├── accounts/
│   │   ├── components/
│   │   └── hooks/
│   │   └── AccountsPage.jsx
│   │
│   └── upload/
│       ├── components/
│       │   └── CSVUpload.jsx
│       └── hooks/
│       └── UploadPage.jsx
│
├── api/                        # API layer
│   ├── services/              # API service clients
│   │   ├── auth.js
│   │   ├── transactions.js
│   │   ├── analytics.js
│   │   ├── fire.js
│   │   ├── emergencyFund.js
│   │   ├── salarySweep.js
│   │   ├── loanPrepayment.js
│   │   └── recurringPayments.js
│   └── client.js              # Axios client configuration
│
├── context/                    # React contexts
│   ├── AuthContext.jsx
│   └── AppContext.jsx
│
└── App.js                      # Root component

```

## Migration Strategy

### Phase 1: Shared Layer (Week 1)
1. Create shared UI components
2. Extract custom hooks
3. Create utility functions
4. Set up shared components structure

### Phase 2: Feature Extraction (Week 2)
1. Move reports to feature modules
2. Extract transaction management
3. Extract asset management
4. Extract dashboard components

### Phase 3: Integration (Week 3)
1. Update imports throughout app
2. Test all functionality
3. Remove duplicate code
4. Documentation

## Benefits
- **Maintainability**: Clear boundaries, easier to find and fix issues
- **Scalability**: Easy to add new features
- **Reusability**: Shared components reduce duplication
- **Testability**: Isolated features easier to test
- **Developer Experience**: Clear structure, easier onboarding
