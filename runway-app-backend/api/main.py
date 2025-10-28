"""
Runway Finance API - FastAPI Application

A RESTful API for personal finance management with:
- Transaction management (CRUD)
- ML-powered categorization
- Analytics and insights
- Secure authentication
- File upload and batch processing

Run with: uvicorn api.main:app --reload
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from api.models.schemas import HealthCheck, ErrorResponse

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Runway Finance API",
    description="Personal Finance Management API with ML-powered categorization",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS configuration
# Allow specific origins for better security
# Development: http://localhost:3000 (React default)
# Production: Add your production frontend URL
ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React development server
    "http://localhost:3001",  # Alternative port
    "http://localhost:3002",  # Another alternative
    "http://127.0.0.1:3000",  # Alternative localhost
    "http://127.0.0.1:3001",  # Alternative localhost
    "http://127.0.0.1:3002",  # Another alternative localhost
    # Allow any localhost port for development
    "http://localhost:*",
]

# Add production origins from environment if configured
if Config.FRONTEND_URL:
    ALLOWED_ORIGINS.append(Config.FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            detail=str(exc),
            timestamp=datetime.now().isoformat()
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc),
            timestamp=datetime.now().isoformat()
        ).dict()
    )


# ============================================================================
# Health Check & Root Endpoints
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Runway Finance API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthCheck, tags=["Health"])
async def health_check():
    """
    Health check endpoint

    Returns system status including:
    - API status
    - Database connectivity
    - ML model availability
    """
    from storage.database import DatabaseManager
    from ml.categorizer import MLCategorizer

    # Check database
    try:
        db = DatabaseManager(Config.DATABASE_URL)
        db_status = "healthy"
        db.close()
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = f"unhealthy: {str(e)}"

    # Check ML model
    try:
        categorizer = MLCategorizer(Config.ML_MODEL_PATH)
        if categorizer.vectorizer and categorizer.classifier:
            ml_status = f"healthy (trained on {categorizer.metadata.get('training_samples', 0)} samples)"
        else:
            ml_status = "not trained"
    except Exception as e:
        logger.error(f"ML model health check failed: {e}")
        ml_status = f"unhealthy: {str(e)}"

    return HealthCheck(
        status="healthy" if db_status == "healthy" else "degraded",
        version="1.0.0",
        database=db_status,
        ml_model=ml_status,
        timestamp=datetime.now().isoformat()
    )


# ============================================================================
# Import Routers
# ============================================================================

# Import route modules
from api.routes import transactions, analytics, ml_categorization, upload, upload_categorize, upload_categorize_v2, auth, assets, liquidations, liabilities, accounts, salary_sweep_v2, loan_prepayment, fire_calculator, dashboard, emergency_fund, investment_optimizer, net_worth_timeline

# Register routers
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)

app.include_router(
    transactions.router,
    prefix="/api/v1/transactions",
    tags=["Transactions"]
)

app.include_router(
    analytics.router,
    prefix="/api/v1/analytics",
    tags=["Analytics"]
)

app.include_router(
    ml_categorization.router,
    prefix="/api/v1/ml",
    tags=["ML Categorization"]
)

app.include_router(
    upload.router,
    prefix="/api/v1/upload",
    tags=["File Upload"]
)

app.include_router(
    upload_categorize.router,
    prefix="/api/v1/upload",
    tags=["File Upload"]
)

app.include_router(
    upload_categorize_v2.router,
    prefix="/api/v1/upload",
    tags=["File Upload"]
)

app.include_router(
    assets.router,
    prefix="/api/v1/assets",
    tags=["Assets"]
)

app.include_router(
    liquidations.router,
    prefix="/api/v1/liquidations",
    tags=["Liquidations"]
)

app.include_router(
    liabilities.router,
    prefix="/api/v1/liabilities",
    tags=["Liabilities"]
)

app.include_router(
    accounts.router,
    prefix="/api/v1/accounts",
    tags=["Accounts"]
)

app.include_router(
    salary_sweep_v2.router,
    prefix="/api/v1/salary-sweep",
    tags=["Salary Sweep Optimizer V2"]
)

app.include_router(
    loan_prepayment.router,
    prefix="/api/v1/loan-prepayment",
    tags=["Loan Prepayment Optimizer"]
)

app.include_router(
    fire_calculator.router,
    prefix="/api/v1/fire",
    tags=["FIRE Calculator"]
)

app.include_router(
    dashboard.router,
    prefix="/api/v1/dashboard",
    tags=["Dashboard"]
)

app.include_router(
    emergency_fund.router,
    prefix="/api/v1/emergency-fund",
    tags=["Emergency Fund Health Check"]
)

app.include_router(
    investment_optimizer.router,
    prefix="/api/v1/investment-optimizer",
    tags=["Investment Optimizer"]
)

app.include_router(
    net_worth_timeline.router,
    prefix="/api/v1/net-worth",
    tags=["Net Worth Timeline"]
)


# ============================================================================
# Startup & Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 Runway Finance API starting...")
    logger.info(f"Database: {Config.get_database_url(mask_password=True)}")
    logger.info(f"ML Model: {Config.ML_MODEL_PATH}")
    logger.info(f"Log Level: {Config.LOG_LEVEL}")

    # Validate configuration
    try:
        Config.validate()
        logger.info("✅ Configuration validated")
    except Exception as e:
        logger.error(f"❌ Configuration validation failed: {e}")

    logger.info("✅ API ready to accept requests")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Runway Finance API...")


# ============================================================================
# Development Runner
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
