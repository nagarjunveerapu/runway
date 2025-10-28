# Runway Finance API Documentation

A complete RESTful API for personal finance management with ML-powered transaction categorization.

## 🚀 Quick Start

### Start the API

```bash
# Using the startup script
./run_api.sh

# Or directly with uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at: `http://localhost:8000`

### Interactive Documentation

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 📚 API Endpoints

### Health & Status

#### `GET /`
Root endpoint with API information.

**Response:**
```json
{
  "message": "Runway Finance API",
  "version": "1.0.0",
  "docs": "/docs",
  "health": "/health"
}
```

#### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "healthy",
  "ml_model": "healthy (trained on 900 samples)",
  "timestamp": "2025-10-26T15:40:50.081766"
}
```

---

### Transactions

#### `GET /api/v1/transactions/`
Get paginated list of transactions with optional filters.

**Query Parameters:**
- `page` (int, default: 1): Page number
- `page_size` (int, default: 50, max: 100): Items per page
- `start_date` (string): Filter by start date (YYYY-MM-DD)
- `end_date` (string): Filter by end date (YYYY-MM-DD)
- `category` (string): Filter by category
- `min_amount` (float): Minimum amount
- `max_amount` (float): Maximum amount

**Example:**
```bash
curl "http://localhost:8000/api/v1/transactions/?page=1&page_size=10&category=Food%20%26%20Dining"
```

**Response:**
```json
{
  "transactions": [...],
  "total": 100,
  "page": 1,
  "page_size": 10,
  "total_pages": 10
}
```

#### `GET /api/v1/transactions/{transaction_id}`
Get a single transaction by ID.

**Example:**
```bash
curl "http://localhost:8000/api/v1/transactions/852c70f4-ae59-44f1-b397-2bda1342a2da"
```

#### `POST /api/v1/transactions/`
Create a new transaction.

**Request Body:**
```json
{
  "date": "2025-10-26",
  "amount": 500.00,
  "type": "debit",
  "description_raw": "Swiggy food order",
  "merchant_canonical": "Swiggy",
  "category": "Food & Dining",
  "balance": 45000.00,
  "source": "api"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/transactions/" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2025-10-26",
    "amount": 500.00,
    "type": "debit",
    "description_raw": "Swiggy food order",
    "merchant_canonical": "Swiggy",
    "category": "Food & Dining"
  }'
```

#### `PATCH /api/v1/transactions/{transaction_id}`
Update a transaction.

**Request Body:**
```json
{
  "category": "Food & Dining",
  "merchant_canonical": "Swiggy"
}
```

#### `DELETE /api/v1/transactions/{transaction_id}`
Delete a transaction.

---

### Analytics

#### `GET /api/v1/analytics/summary`
Get summary statistics.

**Query Parameters:**
- `start_date` (optional): Start date filter
- `end_date` (optional): End date filter

**Example:**
```bash
curl "http://localhost:8000/api/v1/analytics/summary"
```

**Response:**
```json
{
  "total_transactions": 450,
  "total_debit": 125000.00,
  "total_credit": 50000.00,
  "net": -75000.00,
  "category_breakdown": {
    "Food & Dining": {"count": 120, "total": 25000.00},
    "Shopping": {"count": 80, "total": 35000.00}
  },
  "date_range": {
    "start": "2025-01-01",
    "end": "2025-10-26"
  }
}
```

#### `GET /api/v1/analytics/category-breakdown`
Get spending breakdown by category.

**Example:**
```bash
curl "http://localhost:8000/api/v1/analytics/category-breakdown"
```

**Response:**
```json
[
  {
    "category": "Food & Dining",
    "count": 120,
    "total_amount": 25000.00,
    "percentage": 20.0
  },
  {
    "category": "Shopping",
    "count": 80,
    "total_amount": 35000.00,
    "percentage": 28.0
  }
]
```

#### `GET /api/v1/analytics/top-merchants`
Get top merchants by spending.

**Query Parameters:**
- `limit` (int, default: 10, max: 50): Number of merchants
- `start_date` (optional): Start date filter
- `end_date` (optional): End date filter

**Example:**
```bash
curl "http://localhost:8000/api/v1/analytics/top-merchants?limit=5"
```

**Response:**
```json
[
  {
    "merchant": "Swiggy",
    "total_spend": 12500.00,
    "transaction_count": 45
  },
  {
    "merchant": "Amazon",
    "total_spend": 8500.00,
    "transaction_count": 28
  }
]
```

#### `GET /api/v1/analytics/comprehensive`
Get comprehensive analytics (all analytics in one response).

---

### ML Categorization

#### `POST /api/v1/ml/categorize`
Categorize a single transaction using ML.

**Request Body:**
```json
{
  "description": "SWIGGY BANGALORE",
  "merchant": "Swiggy"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/ml/categorize" \
  -H "Content-Type: application/json" \
  -d '{"description": "SWIGGY BANGALORE", "merchant": "Swiggy"}'
```

**Response:**
```json
{
  "category": "Food & Dining",
  "confidence": 0.91,
  "merchant_canonical": "Swiggy"
}
```

#### `POST /api/v1/ml/categorize/batch`
Categorize multiple transactions in batch.

**Request Body:**
```json
{
  "transactions": [
    {"description": "SWIGGY BANGALORE", "merchant": "Swiggy"},
    {"description": "NETFLIX SUBSCRIPTION", "merchant": "Netflix"}
  ]
}
```

**Response:**
```json
{
  "results": [
    {
      "category": "Food & Dining",
      "confidence": 0.91,
      "merchant_canonical": "Swiggy"
    },
    {
      "category": "Entertainment",
      "confidence": 0.95,
      "merchant_canonical": "Netflix"
    }
  ],
  "processed_count": 2
}
```

#### `GET /api/v1/ml/model/info`
Get ML model information.

**Response:**
```json
{
  "status": "trained",
  "version": "2.0",
  "trained_at": "2025-10-26T15:21:40.895617",
  "training_samples": 900,
  "categories": ["Food & Dining", "Shopping", "Transport", ...],
  "accuracy": 0.91,
  "mean_cv_score": 0.903,
  "vocabulary_size": 462
}
```

#### `GET /api/v1/ml/categories`
Get list of available categories.

**Response:**
```json
{
  "categories": [
    "Bills & Utilities",
    "Entertainment",
    "Food & Dining",
    "Groceries",
    "Healthcare",
    "Shopping",
    "Transfer",
    "Transport",
    "Travel"
  ],
  "source": "trained_model",
  "count": 9
}
```

---

### File Upload

#### `POST /api/v1/upload/csv`
Upload and process a CSV bank statement.

**Form Data:**
- `file`: CSV file

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/upload/csv" \
  -F "file=@data/Transactions.csv"
```

**Response:**
```json
{
  "filename": "Transactions.csv",
  "transactions_found": 450,
  "transactions_imported": 442,
  "duplicates_found": 8,
  "status": "success",
  "message": "Successfully imported 442 transactions"
}
```

#### `POST /api/v1/upload/bulk`
Upload and process multiple CSV files.

**Form Data:**
- `files`: Multiple CSV files

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/upload/bulk" \
  -F "files=@file1.csv" \
  -F "files=@file2.csv"
```

**Response:**
```json
{
  "files_processed": 2,
  "total_transactions": 900,
  "successful_imports": 885,
  "failed_imports": 0,
  "errors": []
}
```

---

## 🔧 Configuration

The API uses environment variables from `.env` file. Key configurations:

- `DATABASE_URL`: Database connection string (default: sqlite:///data/finance.db)
- `ML_MODEL_PATH`: Path to ML model (default: ml/models/categorizer.pkl)
- `LOG_LEVEL`: Logging level (default: INFO)
- `DEDUP_TIME_WINDOW_DAYS`: Deduplication time window (default: 1)
- `DEDUP_FUZZY_THRESHOLD`: Merchant similarity threshold (default: 85)

---

## 🧪 Testing

### Using cURL

```bash
# Health check
curl http://localhost:8000/health

# Get transactions
curl "http://localhost:8000/api/v1/transactions/?page=1&page_size=5"

# Categorize transaction
curl -X POST "http://localhost:8000/api/v1/ml/categorize" \
  -H "Content-Type: application/json" \
  -d '{"description": "Swiggy order", "merchant": "Swiggy"}'

# Get analytics
curl "http://localhost:8000/api/v1/analytics/summary"
```

### Using Python

```python
import requests

# Base URL
BASE_URL = "http://localhost:8000"

# Health check
response = requests.get(f"{BASE_URL}/health")
print(response.json())

# Get transactions
response = requests.get(
    f"{BASE_URL}/api/v1/transactions/",
    params={"page": 1, "page_size": 10}
)
transactions = response.json()

# Create transaction
response = requests.post(
    f"{BASE_URL}/api/v1/transactions/",
    json={
        "date": "2025-10-26",
        "amount": 500.00,
        "type": "debit",
        "description_raw": "Swiggy food order",
        "merchant_canonical": "Swiggy",
        "category": "Food & Dining"
    }
)
new_transaction = response.json()

# ML categorization
response = requests.post(
    f"{BASE_URL}/api/v1/ml/categorize",
    json={
        "description": "Netflix subscription",
        "merchant": "Netflix"
    }
)
category_prediction = response.json()
print(f"Category: {category_prediction['category']}, "
      f"Confidence: {category_prediction['confidence']}")
```

---

## 🏗️ Architecture

```
api/
├── main.py                 # FastAPI application entry point
├── models/
│   └── schemas.py         # Pydantic models for request/response validation
├── routes/
│   ├── transactions.py    # Transaction CRUD endpoints
│   ├── analytics.py       # Analytics and summary endpoints
│   ├── ml_categorization.py  # ML categorization endpoints
│   └── upload.py          # File upload endpoints
└── middleware/
    └── (future: auth, rate limiting, etc.)
```

---

## 📊 Response Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `204 No Content`: Resource deleted successfully
- `400 Bad Request`: Invalid request data
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

---

## 🔐 Future Enhancements

- [ ] Authentication (JWT tokens)
- [ ] Rate limiting
- [ ] API key management
- [ ] Webhooks for real-time updates
- [ ] GraphQL endpoint
- [ ] WebSocket support for real-time data
- [ ] Advanced analytics (charts, trends)
- [ ] Export endpoints (PDF, Excel)

---

## 📝 Notes

- All dates should be in `YYYY-MM-DD` format
- All amounts are in the account's currency (default: INR)
- Transaction IDs are UUID v4 strings
- The API automatically handles deduplication during CSV uploads
- ML categorization requires the model to be trained first (see ML_QUICK_START.md)

---

## 🤝 Support

For issues or questions:
- Check the Swagger documentation at `/docs`
- Review the health endpoint at `/health`
- Check logs for detailed error messages
