# Backend Microservices Refactoring Plan

## Goal
Transform the monolithic FastAPI backend into a microservices architecture with clear service boundaries and independent scalability.

## Current Issues
- Monolithic structure with all routes in one main.py
- Tight coupling between different features
- Database sessions scattered across route handlers
- Hard to scale individual features
- All routes share the same database connection
- No clear separation of concerns

## Proposed Architecture

### Service Structure

```
run_poc/
├── services/                     # Individual microservices
│   ├── auth_service/
│   │   ├── __init__.py
│   │   ├── main.py              # Service entry point
│   │   ├── routes/
│   │   │   └── auth.py
│   │   ├── models/
│   │   │   └── user.py
│   │   └── dependencies.py
│   │
│   ├── transaction_service/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── routes/
│   │   │   └── transactions.py
│   │   ├── models/
│   │   └── dependencies.py
│   │
│   ├── analytics_service/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── routes/
│   │   │   └── analytics.py
│   │   └── dependencies.py
│   │
│   ├── fire_service/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── routes/
│   │   │   └── fire_calculator.py
│   │   ├── business_logic/
│   │   │   └── fire_calculator.py
│   │   └── dependencies.py
│   │
│   ├── reports_service/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── routes/
│   │   │   ├── emergency_fund.py
│   │   │   ├── loan_prepayment.py
│   │   │   ├── recurring_payments.py
│   │   │   └── salary_sweep.py
│   │   └── dependencies.py
│   │
│   ├── assets_service/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── routes/
│   │   │   ├── assets.py
│   │   │   ├── liabilities.py
│   │   │   └── liquidations.py
│   │   └── dependencies.py
│   │
│   └── dashboard_service/
│       ├── __init__.py
│       ├── main.py
│       ├── routes/
│       │   └── dashboard.py
│       └── dependencies.py
│
├── shared/                       # Shared code across services
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py        # Database connection pool
│   │   └── models.py            # Shared models
│   │
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── jwt.py
│   │   └── password.py
│   │
│   ├── config/
│   │   └── settings.py          # Centralized configuration
│   │
│   └── middleware/
│       ├── __init__.py
│       ├── cors.py
│       └── logging.py
│
├── api_gateway/                  # API Gateway (optional)
│   ├── __init__.py
│   └── main.py
│
├── storage/                      # Shared storage layer
│   ├── __init__.py
│   ├── database.py
│   └── models.py
│
└── main.py                       # Legacy entry point (to be deprecated)

```

## Service Responsibilities

### 1. Auth Service
- User authentication and authorization
- JWT token management
- Password hashing
- User CRUD operations

### 2. Transaction Service
- Transaction CRUD operations
- Transaction filtering and search
- Upload and categorization
- ML categorization integration

### 3. Analytics Service
- Summary analytics
- Top merchants
- Category breakdown
- Spending patterns

### 4. FIRE Service
- FIRE calculations
- Financial runway analysis
- Savings rate calculations
- Retirement planning

### 5. Reports Service
- Emergency fund analysis
- Loan prepayment optimization
- Recurring payments detection
- Salary sweep optimization

### 6. Assets Service
- Asset management
- Liabilities tracking
- Liquidations tracking
- Net worth calculations

### 7. Dashboard Service
- Dashboard summary
- KPI aggregation
- Health score calculations

## Migration Strategy

### Phase 1: Foundation (Week 1)
1. Create shared directory structure
2. Extract shared database connection
3. Create shared configuration
4. Extract shared auth utilities

### Phase 2: Service Extraction (Week 2)
1. Extract auth service
2. Extract transaction service
3. Extract analytics service
4. Extract FIRE service

### Phase 3: Remaining Services (Week 3)
1. Extract reports service
2. Extract assets service
3. Extract dashboard service
4. Create service orchestration layer

### Phase 4: Integration (Week 4)
1. Update frontend to use service endpoints
2. Add inter-service communication
3. Implement service discovery (optional)
4. Add monitoring and logging

## Benefits
- **Scalability**: Scale services independently based on load
- **Maintainability**: Clear boundaries, easier to debug
- **Deployment**: Deploy services independently
- **Technology**: Use different tech stacks per service
- **Team**: Different teams can own different services
- **Resilience**: Failure in one service doesn't bring down all

## Implementation Approach

### Incremental Migration
1. Keep existing routes working
2. Create new service structure
3. Migrate routes gradually
4. Test each service independently
5. Deprecate old routes once migrated

### Zero Downtime
- Both old and new APIs available during migration
- Frontend switches gradually
- Rollback capability at each stage

## Technology Stack

### Current
- FastAPI
- SQLAlchemy
- SQLite
- JWT for auth

### Proposed (per service)
- FastAPI (continued)
- Shared database (SQLite for now, Postgres in production)
- JWT tokens for inter-service communication
- Optional: Redis for caching
- Optional: Message queue for async processing

## Next Steps

1. Create shared infrastructure
2. Extract first service (auth)
3. Test service independently
4. Migrate remaining services
5. Update frontend
6. Add monitoring
7. Document API contracts

---

**Status:** Planning Phase
**Priority:** High
**Estimated Time:** 4-6 weeks
