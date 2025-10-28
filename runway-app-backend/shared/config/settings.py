"""
Centralized configuration for all microservices
"""
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Settings:
    """Application settings"""
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/finance.db")
    
    # Authentication
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    
    # CORS
    CORS_ORIGINS: list = None
    
    # ML
    ML_MODEL_PATH: str = os.getenv("ML_MODEL_PATH", "ml/models/categorizer.pkl")
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    
    # Service configuration
    AUTH_SERVICE_URL: Optional[str] = os.getenv("AUTH_SERVICE_URL", None)
    TRANSACTION_SERVICE_URL: Optional[str] = os.getenv("TRANSACTION_SERVICE_URL", None)
    
    def __post_init__(self):
        if self.CORS_ORIGINS is None:
            self.CORS_ORIGINS = ["http://localhost:3000", "http://localhost:8000"]

# Global settings instance
settings = Settings()

def get_settings() -> Settings:
    """Get application settings"""
    return settings
