"""
Auth Service - Handles authentication and authorization
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from shared.config.settings import get_settings
from shared.database.connection import init_database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize app
app = FastAPI(
    title="Auth Service",
    description="User authentication and authorization service",
    version="1.0.0"
)

# Add CORS middleware
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
init_database()

# Import routes
from services.auth_service.routes import auth

# Include routers
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Auth Service starting up...")
    logger.info(f"Database: {settings.DATABASE_URL}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Auth Service...")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "auth-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
