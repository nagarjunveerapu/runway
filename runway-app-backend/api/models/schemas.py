"""
Pydantic schemas for API request/response validation
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class TransactionType(str, Enum):
    """Transaction type enumeration"""
    DEBIT = "debit"
    CREDIT = "credit"


class CategoryEnum(str, Enum):
    """Transaction category enumeration"""
    FOOD_DINING = "Food & Dining"
    GROCERIES = "Groceries"
    SHOPPING = "Shopping"
    TRANSPORT = "Transport"
    ENTERTAINMENT = "Entertainment"
    BILLS_UTILITIES = "Bills & Utilities"
    HEALTHCARE = "Healthcare"
    EDUCATION = "Education"
    TRAVEL = "Travel"
    INVESTMENT = "Investment"
    TRANSFER = "Transfer"
    SALARY = "Salary"
    REFUND = "Refund"
    OTHER = "Other"
    UNKNOWN = "Unknown"


# ============================================================================
# Transaction Schemas
# ============================================================================

class TransactionBase(BaseModel):
    """Base transaction schema"""
    date: str = Field(..., description="Transaction date (YYYY-MM-DD)")
    amount: float = Field(..., gt=0, description="Transaction amount (must be positive)")
    type: TransactionType = Field(..., description="Transaction type (debit/credit)")
    description_raw: str = Field(..., description="Original transaction description")

    merchant_canonical: Optional[str] = Field(None, description="Canonical merchant name")
    category: Optional[str] = Field("Unknown", description="Transaction category")
    balance: Optional[float] = Field(None, description="Account balance after transaction")
    source: str = Field("api", description="Data source")

    @validator('date')
    def validate_date(cls, v):
        """Validate date format"""
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")


class TransactionCreate(TransactionBase):
    """Schema for creating a transaction"""
    account_id: Optional[str] = None
    bank_name: Optional[str] = None


class TransactionUpdate(BaseModel):
    """Schema for updating a transaction"""
    category: Optional[str] = None
    merchant_canonical: Optional[str] = None
    description_raw: Optional[str] = None


class TransactionResponse(BaseModel):
    """Schema for transaction response"""
    transaction_id: str
    date: str
    amount: float
    type: str
    description_raw: str
    clean_description: Optional[str] = None
    merchant_raw: Optional[str] = None
    merchant_canonical: Optional[str] = None
    merchant_id: Optional[str] = None
    category: str
    confidence: Optional[float] = None
    balance: Optional[float] = None
    currency: str = "INR"
    is_duplicate: bool = False
    duplicate_count: int = 0
    source: str
    bank_name: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class TransactionList(BaseModel):
    """Schema for paginated transaction list"""
    transactions: List[TransactionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# ML Categorization Schemas
# ============================================================================

class CategorizeRequest(BaseModel):
    """Request schema for ML categorization"""
    description: str = Field(..., description="Transaction description")
    merchant: Optional[str] = Field(None, description="Merchant name")


class CategorizeResponse(BaseModel):
    """Response schema for ML categorization"""
    category: str
    confidence: float
    merchant_canonical: Optional[str] = None


class BatchCategorizeRequest(BaseModel):
    """Request schema for batch categorization"""
    transactions: List[CategorizeRequest]


class BatchCategorizeResponse(BaseModel):
    """Response schema for batch categorization"""
    results: List[CategorizeResponse]
    processed_count: int


# ============================================================================
# Analytics Schemas
# ============================================================================

class SummaryStats(BaseModel):
    """Summary statistics response"""
    total_transactions: int
    total_debit: float
    total_credit: float
    net: float
    category_breakdown: Dict[str, Dict[str, Any]]
    date_range: Optional[Dict[str, str]] = None


class CategoryBreakdown(BaseModel):
    """Category-wise breakdown"""
    category: str
    count: int
    total_amount: float
    percentage: float


class MonthlyTrend(BaseModel):
    """Monthly spending trend"""
    month: str
    debit: float
    credit: float
    net: float


class TopMerchant(BaseModel):
    """Top merchant by spend"""
    merchant: str
    total_spend: float
    transaction_count: int


class AnalyticsResponse(BaseModel):
    """Comprehensive analytics response"""
    summary: SummaryStats
    category_breakdown: List[CategoryBreakdown]
    monthly_trends: Optional[List[MonthlyTrend]] = None
    top_merchants: Optional[List[TopMerchant]] = None


# ============================================================================
# File Upload Schemas
# ============================================================================

class FileUploadResponse(BaseModel):
    """File upload response"""
    filename: str
    transactions_found: int
    transactions_imported: int
    duplicates_found: int
    status: str
    message: str


class BulkImportResponse(BaseModel):
    """Bulk import response"""
    files_processed: int
    total_transactions: int
    successful_imports: int
    failed_imports: int
    errors: List[str] = []


# ============================================================================
# Authentication Schemas
# ============================================================================

class UserCreate(BaseModel):
    """User creation schema"""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    """User login schema"""
    username: str
    password: str


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Token payload data"""
    username: Optional[str] = None
    user_id: Optional[str] = None


class UserResponse(BaseModel):
    """User response schema"""
    user_id: str
    username: str
    email: str
    created_at: str

    class Config:
        from_attributes = True


# ============================================================================
# Health Check & Status Schemas
# ============================================================================

class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    version: str
    database: str
    ml_model: str
    timestamp: str


class ErrorResponse(BaseModel):
    """Error response schema"""
    error: str
    detail: Optional[str] = None
    timestamp: str


# ============================================================================
# Query Filter Schemas
# ============================================================================

class TransactionFilters(BaseModel):
    """Transaction query filters"""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    category: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    merchant: Optional[str] = None
    transaction_type: Optional[TransactionType] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=100)
