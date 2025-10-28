# FIRE + run_way Backend Integration To-Do List

## Architecture Overview

```
+----------------------+        +--------------------+        +------------------+
|  FIRE (frontend/API) | <----> |  run_way Backend   | <----> |  Shared DB (SQL) |
|  (React/Flask/Node)  |   API  |  (ingest/mapper/ml)|  ORM   | (SQLite/Postgres)|
+----------------------+        +--------------------+        +------------------+
                                         ^
                                         |
                                +------------------+
                                |  Privacy Vault   |
                                | (PII encrypted)  |
                                +------------------+
```

---

## Phase 1: API Infrastructure Setup ✅ COMPLETE

### 1.1 Frontend API Client ✅
- [x] Install axios or configure fetch API client
- [x] Create `src/api/client.js` with base configuration
  - Base URL configuration
  - Request/response interceptors
  - Error handling utilities
- [x] Add environment configuration files
  - `.env.development` (local API: http://localhost:8000)
  - `.env.production` (production API URL)
- [x] Add `REACT_APP_API_BASE_URL` to environment variables

### 1.2 Backend Configuration ✅
- [x] Update CORS configuration in backend (`api/main.py`)
  - Replace `allow_origins=["*"]` with specific frontend URLs
  - Enable credentials support
- [x] Verify backend runs on port 8000
- [x] Test health check endpoint: `GET /health`

---

## Phase 2: Authentication & Security

### 2.1 Frontend Authentication
- [ ] Create `src/context/AuthContext.jsx`
  - JWT token storage (localStorage/sessionStorage)
  - Login/logout functions
  - User state management
  - Token refresh logic
- [ ] Create authentication UI components
  - `src/components/Auth/Login.jsx`
  - `src/components/Auth/Register.jsx`
  - `src/components/Auth/ProtectedRoute.jsx`
- [ ] Update `RunwayApp.jsx` to wrap routes with authentication

### 2.2 Backend Authentication
- [ ] Create authentication endpoints in backend
  - `POST /api/v1/auth/register` - User registration
  - `POST /api/v1/auth/login` - User login (returns JWT)
  - `POST /api/v1/auth/refresh` - Token refresh
  - `GET /api/v1/auth/me` - Get current user
- [ ] Implement JWT token generation and validation
- [ ] Add password hashing with bcrypt (already in requirements.txt)
- [ ] Create User authentication middleware
- [ ] Update all existing endpoints to require authentication

---

## Phase 3: API Service Layer

### 3.1 Transaction Services
- [ ] Create `src/api/services/transactions.js`
  ```javascript
  - getTransactions(filters) → GET /api/v1/transactions
  - getTransaction(id) → GET /api/v1/transactions/:id
  - createTransaction(data) → POST /api/v1/transactions
  - updateTransaction(id, data) → PATCH /api/v1/transactions/:id
  - deleteTransaction(id) → DELETE /api/v1/transactions/:id
  - categorizeTransaction(data) → POST /api/v1/ml/categorize
  ```

### 3.2 Asset Services
- [ ] Create `src/api/services/assets.js`
  ```javascript
  - getAssets() → GET /api/v1/assets
  - getAsset(id) → GET /api/v1/assets/:id
  - createAsset(data) → POST /api/v1/assets
  - updateAsset(id, data) → PATCH /api/v1/assets/:id
  - deleteAsset(id) → DELETE /api/v1/assets/:id
  ```

### 3.3 Liquidation Services
- [ ] Create `src/api/services/liquidations.js`
  ```javascript
  - getLiquidations() → GET /api/v1/liquidations
  - getLiquidation(id) → GET /api/v1/liquidations/:id
  - createLiquidation(data) → POST /api/v1/liquidations
  - deleteLiquidation(id) → DELETE /api/v1/liquidations/:id
  ```

### 3.4 Analytics Services
- [ ] Create `src/api/services/analytics.js`
  ```javascript
  - getSummary(dateRange) → GET /api/v1/analytics/summary
  - getTopMerchants(dateRange) → GET /api/v1/analytics/top-merchants
  - getCategoryTrends(dateRange) → GET /api/v1/analytics/category-trends
  ```

---

## Phase 4: Backend Data Models

### 4.1 Extend Transaction Model
- [ ] Update `storage/models.py` - Transaction model
  - Add `linked_asset_id` (ForeignKey to Asset)
  - Add `liquidation_event_id` (ForeignKey to Liquidation)
  - Add `month` field (YYYY-MM format)
  - Ensure all FIRE fields are supported

### 4.2 Create Asset Model
- [ ] Add Asset model to `storage/models.py`
  ```python
  Asset:
    - id (UUID primary key)
    - user_id (ForeignKey)
    - name (String)
    - quantity (Float)
    - current_value (Float)
    - purchase_price (Float)
    - purchase_date (Date)
    - type (String: Stock, MutualFund, etc.)
    - disposed (Boolean)
    - created_at (DateTime)
    - updated_at (DateTime)
  ```

### 4.3 Create Liquidation Model
- [ ] Add Liquidation model to `storage/models.py`
  ```python
  Liquidation:
    - id (UUID primary key)
    - user_id (ForeignKey)
    - asset_id (ForeignKey)
    - date (Date)
    - gross_proceeds (Float)
    - fees (Float)
    - net_received (Float)
    - quantity_sold (Float)
    - notes (Text)
    - created_at (DateTime)
  ```

### 4.4 Create API Endpoints
- [ ] Create `api/routes/assets.py` with CRUD endpoints
- [ ] Create `api/routes/liquidations.py` with CRUD endpoints
- [ ] Create Pydantic schemas in `api/models/` for validation
  - `AssetCreate`, `AssetUpdate`, `AssetResponse`
  - `LiquidationCreate`, `LiquidationResponse`
- [ ] Register routes in `api/main.py`

### 4.5 EMI & SIP Support
- [ ] Create EMI model in backend (or extend Transaction with EMI metadata)
- [ ] Create SIP model in backend (or extend Transaction with SIP metadata)
- [ ] Create endpoints: `/api/v1/emis` and `/api/v1/sips`
- [ ] Create corresponding frontend services

---

## Phase 5: AppContext Migration

### 5.1 Update AppContext.jsx
- [ ] Add loading states
  ```javascript
  - isLoading (boolean)
  - error (string | null)
  - isAuthenticated (boolean)
  ```
- [ ] Replace localStorage calls with API calls
  - `useEffect` to fetch transactions on mount
  - `useEffect` to fetch assets on mount
  - `useEffect` to fetch liquidations on mount
- [ ] Update action functions
  - `addTransaction` → call API then update state
  - `addAsset` → call API then update state
  - `recordLiquidation` → call API then update state
  - Add optimistic updates for better UX
- [ ] Add error handling for all API calls
- [ ] Keep localStorage as fallback/cache mechanism (optional)

### 5.2 Migration Strategy
- [ ] Create data migration script
  - Read existing localStorage data
  - POST to backend API to seed database
  - Verify data integrity
- [ ] Add "Sync to Server" button in Settings (optional)
- [ ] Handle offline mode (cache data locally, sync when online)

---

## Phase 6: UI/UX Updates

### 6.1 Loading States
- [ ] Add loading spinners to Dashboard
- [ ] Add loading skeletons to Reports
- [ ] Add loading states to transaction lists
- [ ] Add loading states to asset lists

### 6.2 Error Handling
- [ ] Create `src/components/Common/Toast.jsx` for notifications
- [ ] Add error boundaries for React components
- [ ] Display user-friendly error messages
- [ ] Add retry mechanisms for failed API calls

### 6.3 Component Updates
- [ ] Update `Dashboard.jsx` to handle async data
- [ ] Update `Reports.jsx` to use analytics API
- [ ] Update `Add/AddTransaction.jsx` to call ML categorization API
- [ ] Update all inline edit components to use API

### 6.4 Request/Response Interceptors
- [ ] Add auth token to all requests (Authorization header)
- [ ] Handle 401 Unauthorized → redirect to login
- [ ] Handle 403 Forbidden → show error message
- [ ] Handle 500 Server Error → show retry option
- [ ] Implement token refresh on 401 errors

---

## Phase 7: Advanced Features

### 7.1 ML Categorization Integration
- [ ] Integrate ML categorization in AddTransaction flow
  - Auto-suggest category based on description
  - Show confidence score
  - Allow manual override
- [ ] Add batch categorization option
  - Select multiple transactions
  - Bulk categorize using `/api/v1/ml/batch-categorize`

### 7.2 Privacy Vault Integration
- [ ] Update backend to store sensitive data in vault
  - Bank account numbers
  - Card numbers (if added in future)
- [ ] Ensure frontend never displays raw encrypted data
- [ ] Add audit logging for PII access

### 7.3 File Upload Support
- [ ] Add file upload UI component
- [ ] Create upload endpoint in FIRE UI
- [ ] Connect to backend `/api/v1/upload/upload`
- [ ] Display upload progress
- [ ] Show success/failure results for each uploaded file

---

## Phase 8: Database & Deployment

### 8.1 Database Setup
- [ ] Create database initialization script
  - `python -m storage.database init`
  - Create all tables
  - Create indexes
- [ ] Test with SQLite locally
- [ ] Set up PostgreSQL for production
  - Install PostgreSQL
  - Create database and user
  - Update `config.py` with production DB URL
- [ ] Run database migrations (Alembic recommended)

### 8.2 Docker Containerization
- [ ] Create `Dockerfile` for backend
- [ ] Create `docker-compose.yml`
  - Backend service
  - PostgreSQL service
  - Nginx service (optional)
- [ ] Test Docker deployment locally

### 8.3 Reverse Proxy (Nginx)
- [ ] Configure Nginx for API reverse proxy
  - Route `/api/*` to backend (port 8000)
  - Serve frontend static files
- [ ] Configure SSL/TLS certificates (Let's Encrypt)
- [ ] Set up rate limiting in Nginx

### 8.4 Environment Configuration
- [ ] Create `.env.production` for backend
- [ ] Set up environment variables
  - `DATABASE_URL`
  - `JWT_SECRET_KEY`
  - `VAULT_KEY_PATH`
  - `CORS_ORIGINS`
- [ ] Secure sensitive environment variables

---

## Phase 9: Testing & Quality Assurance

### 9.1 Integration Testing
- [ ] Test user registration and login flow
- [ ] Test CRUD operations for transactions
- [ ] Test CRUD operations for assets
- [ ] Test CRUD operations for liquidations
- [ ] Test ML categorization accuracy
- [ ] Test file upload functionality
- [ ] Test analytics endpoints
- [ ] Test error handling and edge cases

### 9.2 Security Audit
- [ ] OWASP Top 10 vulnerability check
- [ ] SQL injection testing
- [ ] XSS prevention verification
- [ ] CSRF protection verification
- [ ] Authentication and authorization testing
- [ ] Rate limiting testing
- [ ] Encryption verification (vault)

### 9.3 Performance Testing
- [ ] Load testing with Apache Bench or k6
- [ ] Database query optimization
- [ ] API response time measurement
- [ ] Frontend bundle size optimization
- [ ] Lazy loading for React components

---

## Phase 10: Monitoring & Documentation

### 10.1 Monitoring
- [ ] Add logging to backend (Python logging)
- [ ] Set up error tracking (Sentry or similar)
- [ ] Add performance monitoring (New Relic or similar)
- [ ] Create health check dashboard

### 10.2 Documentation
- [ ] Generate OpenAPI/Swagger documentation
  - FastAPI auto-generates at `/docs`
- [ ] Create API documentation for FIRE developers
- [ ] Create user guide for new features
- [ ] Document deployment process
- [ ] Create troubleshooting guide

### 10.3 Backup & Recovery
- [ ] Set up automated database backups
- [ ] Test database recovery process
- [ ] Create backup vault keys
- [ ] Document disaster recovery plan

---

## Priority Levels

### High Priority (MVP)
1. API Infrastructure Setup (Phase 1)
2. Authentication (Phase 2)
3. Transaction API Integration (Phase 3.1)
4. Backend Transaction Model (Phase 4.1)
5. AppContext Migration (Phase 5)
6. Basic UI Updates (Phase 6.1-6.2)

### Medium Priority
7. Asset & Liquidation APIs (Phase 3.2-3.3, 4.2-4.4)
8. Advanced UI Features (Phase 6.3-6.4)
9. ML Categorization (Phase 7.1)
10. Database Production Setup (Phase 8.1)

### Low Priority (Post-MVP)
11. EMI & SIP Support (Phase 4.5)
12. File Upload (Phase 7.3)
13. Privacy Vault (Phase 7.2)
14. Docker & Deployment (Phase 8.2-8.4)
15. Monitoring & Docs (Phase 10)

---

## Key Files Reference

### Frontend Critical Files
- `src/context/AppContext.jsx` - State management (needs migration)
- `src/utils/localStorage.js` - localStorage hook (will be replaced)
- `package.json` - Dependencies (add axios)

### Backend Critical Files
- `api/main.py` - FastAPI entry point
- `api/routes/transactions.py` - Transaction endpoints
- `storage/models.py` - Database models (extend here)
- `config.py` - Configuration management
- `privacy/vault.py` - PII encryption

### New Files to Create
- **Frontend:**
  - `src/api/client.js`
  - `src/api/services/transactions.js`
  - `src/api/services/assets.js`
  - `src/api/services/liquidations.js`
  - `src/api/services/analytics.js`
  - `src/context/AuthContext.jsx`
  - `src/components/Auth/Login.jsx`
  - `src/components/Auth/Register.jsx`
  - `src/components/Common/Toast.jsx`
  - `.env.development`
  - `.env.production`

- **Backend:**
  - `api/routes/auth.py`
  - `api/routes/assets.py`
  - `api/routes/liquidations.py`
  - `api/models/asset_schemas.py`
  - `api/models/liquidation_schemas.py`
  - `Dockerfile`
  - `docker-compose.yml`

---

## Estimated Timeline

- **Week 1-2:** Phases 1-2 (API Infrastructure + Auth)
- **Week 3-4:** Phases 3-5 (Services + Models + Migration)
- **Week 5-6:** Phases 6-7 (UI Updates + Advanced Features)
- **Week 7-8:** Phases 8-10 (Deployment + Testing + Docs)

**Total: ~8 weeks for full integration**

---

## Notes

- Current FIRE app uses localStorage only - no backend integration exists
- Backend (run_way) is fully functional with FastAPI + SQLAlchemy
- Privacy Vault provides AES-256-GCM encryption for PII
- ML categorization model needs to be trained (`ml/models/categorizer.pkl`)
- Backend supports both SQLite (dev) and PostgreSQL (prod)
- Consider implementing offline-first sync strategy for better UX

---

**Last Updated:** 2025-10-26
**Status:** Phase 1 Complete ✅
**Next Action:** Start Phase 2 - Authentication & Security
