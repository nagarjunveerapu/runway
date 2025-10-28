# Personal Finance App - Complete Technical Specification

## Table of Contents
1. [System Overview](#system-overview)
2. [Configuration & Secrets Management](#configuration--secrets-management)
3. [Canonical Transaction Schema](#canonical-transaction-schema)
4. [Architecture & Data Flow](#architecture--data-flow)
5. [Module Specifications](#module-specifications)
6. [Implementation Templates](#implementation-templates)
7. [Database Schema](#database-schema)
8. [API Specifications](#api-specifications)
9. [Security & Privacy](#security--privacy)
10. [ML Pipeline Details](#ml-pipeline-details)
11. [Testing Strategy](#testing-strategy)
12. [Performance & Scaling](#performance--scaling)
13. [Compliance & Regulatory](#compliance--regulatory)

---

## 1. System Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI Interface (Click)                     │
│                          main.py                                 │
└───────────┬─────────────┬─────────────┬─────────────────────────┘
            │             │             │
    ┌───────▼──────┐ ┌───▼──────┐ ┌───▼──────┐ ┌──────────────┐
    │   INGEST     │ │  TRAIN   │ │ PREDICT  │ │    QUERY     │
    │   Command    │ │ Command  │ │ Command  │ │   Command    │
    └───────┬──────┘ └───┬──────┘ └───┬──────┘ └──────┬───────┘
            │             │             │               │
    ┌───────▼──────────────────────────────────────────▼───────┐
    │              Ingestion Engine                             │
    │  ┌──────────┐ ┌──────────┐ ┌────────────┐              │
    │  │   PDF    │ │   CSV    │ │ Normalizer │              │
    │  │  Parser  │ │  Parser  │ │            │              │
    │  └─────┬────┘ └────┬─────┘ └──────┬─────┘              │
    └────────┼───────────┼──────────────┼────────────────────┘
             │           │              │
    ┌────────▼───────────▼──────────────▼────────────────────┐
    │              Canonical Transactions                      │
    │                (JSON Schema)                             │
    └────────┬───────────┬──────────────┬────────────────────┘
             │           │              │
    ┌────────▼────┐ ┌────▼─────┐ ┌─────▼──────┐ ┌──────────┐
    │  Merchant   │ │ Privacy  │ │    ML      │ │    AA    │
    │   Mapper    │ │  Vault   │ │  Engine    │ │   Stub   │
    │  (Fuzzy)    │ │ (Encrypt)│ │ (Predict)  │ │          │
    └────────┬────┘ └────┬─────┘ └─────┬──────┘ └────┬─────┘
             │           │              │             │
    ┌────────▼───────────▼──────────────▼─────────────▼──────┐
    │              Storage Layer (SQLite + SQLAlchemy)        │
    │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
    │  │ Transactions │ │     PII      │ │   Metadata   │   │
    │  └──────────────┘ └──────────────┘ └──────────────┘   │
    └─────────────────────────────────────────────────────────┘
```

### 1.2 Technology Stack

**Core Libraries:**
```python
# requirements.txt
pandas==2.0.3
numpy==1.24.3
pdfplumber==0.10.3
camelot-py[cv]==0.11.0
rapidfuzz==3.5.2
sqlalchemy==2.0.23
cryptography==41.0.7
scikit-learn==1.3.2
xgboost==2.0.3
joblib==1.3.2
click==8.1.7
python-dotenv==1.0.0
pytest==7.4.3
matplotlib==3.8.2
seaborn==0.13.0

# requirements-dev.txt (optional advanced features)
transformers==4.35.2
datasets==2.15.0
torch==2.1.1
```

---

## 2. Configuration & Secrets Management

### 2.1 Environment Variables with python-dotenv

**CRITICAL: Never commit secrets to git!**

The application uses `python-dotenv` for configuration management. All sensitive data (API keys, vault keys, database URLs) must be stored in environment variables.

**Priority Order:**
1. System environment variables (production)
2. `.env` file (development/local)
3. Default values (non-sensitive only)

### 2.2 Configuration File (config.py)

The `config.py` file has been created in the project root with comprehensive configuration management including:

- **Vault & Security**: VAULT_KEY, VAULT_KEY_FILE with automatic key generation
- **Database**: DATABASE_URL with masked password display
- **API Keys**: AWS, OpenAI (optional)
- **Account Aggregator**: AA_CLIENT_ID, AA_CLIENT_SECRET, AA_REDIRECT_URI
- **Application Settings**: LOG_LEVEL, ENABLE_AUDIT_LOGGING, ML_MODEL_PATH
- **Feature Flags**: ENABLE_PDF_OCR, ENABLE_CAMELOT, ENABLE_TABULA
- **Deduplication Settings**: DEDUP_TIME_WINDOW_DAYS, DEDUP_FUZZY_THRESHOLD, DEDUP_MERGE_MODE

Key features:
- Automatic .env loading with python-dotenv
- Configuration validation on startup
- Secure key generation if not found
- Password masking for database URLs
- Feature flag support for optional dependencies

### 2.3 Environment Files

**`.env.example`** (safe to commit) - Template created in project root

**`.env`** (NEVER commit to git) - Create locally with:
```bash
cp .env.example .env
# Edit .env with your actual secrets
chmod 600 .env
```

### 2.4 Updated .gitignore

A comprehensive `.gitignore` file has been created protecting:
- Environment files (.env, *.env except .env.example)
- Vault keys (.vault_key, *.vault_key)
- Credentials (credentials.json, secrets.json, *.pem, *.key)
- Database files (*.db, *.sqlite, *.sqlite3)
- Logs (*.log, logs/, vault_audit.log)
- Backups (*_backup_*, vault_backup_*)
- Standard Python/IDE artifacts

### 2.5 Security Checklist for Configuration

- [x] `config.py` created with secure defaults
- [x] `.env.example` provided as template (no secrets)
- [x] `.gitignore` configured to protect secrets
- [ ] `.env` file created locally with secure values
- [ ] File permissions set: `chmod 600 .env .vault_key`
- [ ] Vault key backed up securely offline
- [ ] All API keys rotated after any leak
- [ ] Production uses system env vars (not `.env` files)

---

## 3. Canonical Transaction Schema

### 3.1 Core Schema Definition

```python
# schema.py

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import uuid

class TransactionType(Enum):
    DEBIT = "debit"
    CREDIT = "credit"
    TRANSFER = "transfer"

class TransactionChannel(Enum):
    UPI = "upi"
    NEFT = "neft"
    IMPS = "imps"
    RTGS = "rtgs"
    CARD = "card"
    CASH = "cash"
    CHEQUE = "cheque"
    ATM = "atm"
    OTHER = "other"

@dataclass
class CanonicalTransaction:
    """
    Canonical transaction schema - single source of truth
    for all transaction data across the system.

    Schema Version: 2.0
    ISO 8601 timestamps, multi-currency support, deduplication tracking
    """
    # Unique identifier
    transaction_id: str  # UUID v4

    # Core transaction details with timezone-aware timestamps
    date: str  # ISO 8601 format: YYYY-MM-DD (transaction date)
    timestamp: Optional[str] = None  # ISO 8601 with timezone: 2025-10-26T10:30:00+05:30
    transaction_type: str = "debit"  # debit/credit/transfer
    amount: float = 0.0  # Amount in transaction currency (always positive)
    currency: str = "INR"  # ISO 4217 currency code

    # Multi-currency support
    original_amount: Optional[float] = None  # Original amount if converted
    original_currency: Optional[str] = None  # Original currency if different

    # Description & merchant
    raw_description: str = ""  # Original unprocessed description
    clean_description: str = ""  # Normalized description
    merchant_raw: Optional[str] = None  # Extracted merchant name
    merchant_canonical: Optional[str] = None  # Mapped canonical merchant
    merchant_id: Optional[str] = None  # Hash of canonical name for fast joins

    # Categorization (supports multi-label)
    category: str = "Uncategorized"  # Primary category
    category_source: str = "none"  # mapping/ml/rule/manual
    category_confidence: float = 0.0  # 0.0 to 1.0
    subcategory: Optional[str] = None
    labels: List[str] = None  # Additional labels/tags

    # Channel & mode
    channel: Optional[str] = None  # upi/neft/imps/etc
    transaction_mode: Optional[str] = None  # online/pos/atm

    # Account information (references, not actual PII)
    account_ref: Optional[str] = None  # Reference to encrypted account
    account_number_masked: Optional[str] = None  # e.g., XXXX1234
    counterparty_ref: Optional[str] = None
    counterparty_name: Optional[str] = None

    # Balance & fees
    balance_after: Optional[float] = None
    fees: float = 0.0
    tax: float = 0.0

    # Metadata
    source: str = "unknown"  # pdf/csv/aa/manual
    source_file: Optional[str] = None
    statement_date: Optional[str] = None
    ingestion_timestamp: Optional[str] = None  # When ingested into system

    # Flags
    is_recurring: bool = False
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None  # transaction_id of original
    duplicate_count: int = 0  # Number of duplicates merged
    is_flagged: bool = False
    flag_reason: Optional[str] = None

    # UPI specific fields
    upi_id: Optional[str] = None
    upi_ref_id: Optional[str] = None

    # Timestamps (always UTC with Z suffix)
    created_at: str = None  # ISO 8601: 2025-10-26T10:30:00Z
    updated_at: str = None  # ISO 8601: 2025-10-26T10:30:00Z

    # Custom fields (extensible)
    custom_fields: Dict[str, Any] = None

    def __post_init__(self):
        import hashlib

        if self.transaction_id is None:
            self.transaction_id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat() + "Z"
        if self.updated_at is None:
            self.updated_at = self.created_at
        if self.custom_fields is None:
            self.custom_fields = {}
        if self.labels is None:
            self.labels = []

        # Auto-generate ingestion timestamp if not set
        if self.ingestion_timestamp is None:
            self.ingestion_timestamp = datetime.utcnow().isoformat() + "Z"

        # Compute merchant_id hash for fast joins
        if self.merchant_canonical and self.merchant_id is None:
            # Use SHA256 hash of canonical merchant name (first 16 chars)
            self.merchant_id = hashlib.sha256(
                self.merchant_canonical.lower().encode('utf-8')
            ).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    def to_json_line(self) -> str:
        """Convert to JSONL format"""
        import json
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CanonicalTransaction':
        """Create from dictionary"""
        return cls(**data)

    def mask_pii(self) -> 'CanonicalTransaction':
        """Return a copy with PII masked for analytics"""
        data = self.to_dict()
        # Keep only masked account number, remove refs
        data['account_ref'] = None
        data['counterparty_ref'] = None
        # UPI IDs may contain phone numbers, mask them
        if data['upi_id']:
            data['upi_id'] = mask_upi_id(data['upi_id'])
        return CanonicalTransaction.from_dict(data)

def mask_upi_id(upi: str) -> str:
    """Mask phone numbers in UPI IDs"""
    import re
    # Replace 10-digit phone numbers with XXXXXX[last 4]
    return re.sub(r'\d{10}', lambda m: 'XXXXXX' + m.group()[-4:], upi)

def mask_account_number(account: str) -> str:
    """Mask account number, show last 4 digits"""
    if len(account) <= 4:
        return 'X' * len(account)
    return 'X' * (len(account) - 4) + account[-4:]
```

### 2.2 Sample Transaction JSON

```json
{
  "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
  "date": "2025-10-15",
  "transaction_type": "debit",
  "amount": 1250.00,
  "currency": "INR",
  "raw_description": "UPI/Swiggy Ltd/swiggyupi@axb/Payment/AXIS BANK/266553694203",
  "clean_description": "UPI Swiggy Ltd swiggyupi@axb Payment AXIS BANK 266553694203",
  "merchant_raw": "Swiggy Ltd",
  "merchant_canonical": "Swiggy",
  "category": "Food",
  "category_source": "mapping",
  "category_confidence": 0.95,
  "subcategory": "Food Delivery",
  "channel": "upi",
  "transaction_mode": "online",
  "account_ref": "acc_ref_12345",
  "account_number_masked": "XXXX5678",
  "counterparty_ref": null,
  "counterparty_name": "Swiggy Ltd",
  "balance_after": 45230.50,
  "fees": 0.0,
  "tax": 0.0,
  "source": "csv",
  "source_file": "statement_oct_2025.csv",
  "statement_date": "2025-10-31",
  "is_recurring": false,
  "is_duplicate": false,
  "is_flagged": false,
  "flag_reason": null,
  "upi_id": "swiggyupi@axb",
  "upi_ref_id": "266553694203",
  "created_at": "2025-10-26T10:30:00Z",
  "updated_at": "2025-10-26T10:30:00Z",
  "custom_fields": {}
}
```

---

## 4. Architecture & Data Flow

### 4.1 Ingestion Flow

```
Input Files (PDF/CSV)
       │
       ├──► PDF Parser ──────┐
       │                     │
       └──► CSV Parser ──────┤
                             │
                    ┌────────▼─────────┐
                    │   Normalizer     │
                    │  - Date formats  │
                    │  - Amount parse  │
                    │  - Merchant      │
                    │  - Channel       │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  Deduplicator    │
                    │  - Same date     │
                    │  - Same amount   │
                    │  - Fuzzy merchant│
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ PII Handler      │
                    │  - Extract PII   │
                    │  - Store in vault│
                    │  - Create refs   │
                    │  - Mask accounts │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ Merchant Mapper  │
                    │  - Exact match   │
                    │  - Regex rules   │
                    │  - Fuzzy match   │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ ML Categorizer   │
                    │  (if enabled)    │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ Category Resolver│
                    │  - Mapping prio  │
                    │  - ML fallback   │
                    │  - Confidence    │
                    └────────┬─────────┘
                             │
                    Canonical Transaction
                             │
                    ┌────────▼─────────┐
                    │  Save to DB      │
                    │  Export JSONL    │
                    └──────────────────┘
```

### 3.2 Category Resolution Algorithm

```python
def resolve_category(
    transaction: Dict,
    mapping_result: Dict,
    ml_result: Optional[Dict],
    config: Dict
) -> Dict:
    """
    Resolve final category with priority and confidence thresholds.

    Priority:
    1. Exact merchant match (confidence = 1.0)
    2. Regex rule match (confidence = 0.95)
    3. Fuzzy merchant match (confidence varies)
    4. ML prediction (if enabled)
    5. Uncategorized (default)

    Thresholds (configurable):
    - mapping_threshold: 0.8
    - ml_threshold: 0.6
    """

    # Extract results
    mapping_category = mapping_result.get('category')
    mapping_confidence = mapping_result.get('confidence', 0.0)
    mapping_method = mapping_result.get('method')  # exact/regex/fuzzy

    ml_category = ml_result.get('category') if ml_result else None
    ml_confidence = ml_result.get('confidence', 0.0) if ml_result else 0.0

    # Decision logic
    if mapping_confidence >= config['mapping_threshold']:
        return {
            'category': mapping_category,
            'confidence': mapping_confidence,
            'source': 'mapping',
            'method': mapping_method
        }

    elif ml_confidence >= config['ml_threshold']:
        return {
            'category': ml_category,
            'confidence': ml_confidence,
            'source': 'ml',
            'method': 'classifier'
        }

    elif mapping_confidence > 0:
        # Use mapping even if below threshold (better than nothing)
        return {
            'category': mapping_category,
            'confidence': mapping_confidence,
            'source': 'mapping',
            'method': f'{mapping_method}_low_confidence'
        }

    else:
        return {
            'category': 'Uncategorized',
            'confidence': 0.0,
            'source': 'default',
            'method': 'none'
        }
```

---

## 5. Module Specifications

### 4.1 Ingestion Module

#### 4.1.0 PDF Parsing Strategy & Recommendations

**IMPORTANT: PDF Parsing Reality Check**

Bank statement PDFs are notoriously difficult to parse due to:
- Inconsistent formats across banks and statement periods
- Complex layouts with merged cells and varying column structures
- Password protection and security restrictions
- Scanned/image-based PDFs requiring OCR
- Font encoding issues and non-standard characters

**Recommended Approach:**

1. **Start Simple (pdfplumber only)**
   - Works for 70-80% of modern PDFs
   - Zero system dependencies
   - Fast and reliable for text-based PDFs

2. **Add Optional Tools as Needed**
   - Install Java + tabula-py for specific banks with complex tables
   - Install Ghostscript + camelot-py for PDFs with grid-based layouts
   - Install Tesseract + pytesseract only if you encounter scanned PDFs

3. **Bank-Specific Configurations**
   - Create bank-specific parsers in `ingest/parsers/` directory
   - Example: `ingest/parsers/hdfc_parser.py`, `ingest/parsers/axis_parser.py`
   - Each bank parser can have custom regex patterns and extraction logic

4. **Fallback to CSV**
   - **Recommendation**: Ask users to download CSV statements instead of PDFs when possible
   - CSV parsing is 100% reliable and bank-agnostic
   - Most Indian banks provide CSV export option

**Supported Statement Sources (in priority order):**
1. ✅ **CSV Export** (Recommended - 100% reliable)
2. ✅ **PDF Text-based** (pdfplumber - 70% success rate)
3. ⚠️ **PDF Table-based** (tabula/camelot - 40% success rate, requires system deps)
4. ⚠️ **PDF Scanned** (OCR - 30% success rate, slow, requires Tesseract)

#### 4.1.1 PDF Parser (`ingest/pdf_parser.py`)

```python
"""
PDF Statement Parser with Multi-Strategy Fallback

IMPORTANT: PDF parsing is fragile and bank-specific. This parser implements
a fallback chain to maximize success rate:

Strategy Priority:
1. Text extraction (pdfplumber) - Works for most modern PDFs
2. Table extraction (pdfplumber) - For well-structured table-based PDFs
3. Tabula (optional) - Fallback for complex tables (requires Java)
4. Camelot (optional) - Advanced table detection (requires Ghostscript)
5. OCR (optional) - For scanned/image PDFs (requires Tesseract)

System Dependencies:
- pdfplumber: pip install (pure Python, no deps)
- tabula-py: Requires Java JRE 8+
- camelot-py: Requires Ghostscript (brew install ghostscript on macOS)
- pytesseract: Requires Tesseract OCR (brew install tesseract on macOS)

Recommendation: Start with pdfplumber only (no system deps), add others as needed.
"""

import pdfplumber
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Optional imports with graceful degradation
try:
    import tabula
    TABULA_AVAILABLE = True
except ImportError:
    TABULA_AVAILABLE = False
    logger.warning("tabula-py not available. Install with: pip install tabula-py (requires Java)")

try:
    import camelot
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False
    logger.warning("camelot-py not available. Install with: pip install camelot-py[cv] (requires Ghostscript)")

try:
    import pytesseract
    from PIL import Image
    import pdf2image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("OCR not available. Install with: pip install pytesseract pdf2image (requires Tesseract)")

logger = logging.getLogger(__name__)

class PDFParser:
    """Parse bank statement PDFs into structured transactions with fallback strategies"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.patterns = self._load_patterns()

        # Strategy configuration
        self.enable_tabula = self.config.get('enable_tabula', TABULA_AVAILABLE)
        self.enable_camelot = self.config.get('enable_camelot', CAMELOT_AVAILABLE)
        self.enable_ocr = self.config.get('enable_ocr', False)  # OCR is slow, opt-in only

    def parse(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Parse PDF using fallback chain

        Returns:
            List[Dict]: Raw transaction dictionaries
        """
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            return []

        logger.info(f"Parsing PDF: {pdf_path.name}")

        # Strategy 1: pdfplumber text extraction (fastest, most reliable)
        transactions = self._try_pdfplumber_text(pdf_path)
        if transactions:
            logger.info(f"✓ Extracted {len(transactions)} transactions using pdfplumber text")
            return transactions

        # Strategy 2: pdfplumber table extraction
        transactions = self._try_pdfplumber_tables(pdf_path)
        if transactions:
            logger.info(f"✓ Extracted {len(transactions)} transactions using pdfplumber tables")
            return transactions

        # Strategy 3: Tabula (optional, requires Java)
        if self.enable_tabula and TABULA_AVAILABLE:
            transactions = self._try_tabula(pdf_path)
            if transactions:
                logger.info(f"✓ Extracted {len(transactions)} transactions using tabula")
                return transactions

        # Strategy 4: Camelot (optional, requires Ghostscript)
        if self.enable_camelot and CAMELOT_AVAILABLE:
            transactions = self._try_camelot(pdf_path)
            if transactions:
                logger.info(f"✓ Extracted {len(transactions)} transactions using camelot")
                return transactions

        # Strategy 5: OCR (optional, slow, for scanned PDFs)
        if self.enable_ocr and OCR_AVAILABLE:
            transactions = self._try_ocr(pdf_path)
            if transactions:
                logger.info(f"✓ Extracted {len(transactions)} transactions using OCR")
                return transactions

        logger.error(f"✗ Failed to extract transactions from {pdf_path.name} using all strategies")
        return []

    def _try_pdfplumber_text(self, pdf_path: Path) -> List[Dict]:
        """Strategy 1: Extract transactions from text lines"""
        try:
            transactions = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if not text:
                        continue

                    lines = text.split('\n')
                    for line in lines:
                        txn = self._parse_text_line(line)
                        if txn:
                            transactions.append(txn)

            return transactions if len(transactions) > 0 else []

        except Exception as e:
            logger.debug(f"pdfplumber text extraction failed: {e}")
            return []

    def _try_pdfplumber_tables(self, pdf_path: Path) -> List[Dict]:
        """Strategy 2: Extract transactions from tables"""
        try:
            transactions = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()

                    for table in tables or []:
                        if not table or len(table) < 2:
                            continue

                        # Assume first row is header
                        headers = table[0]
                        header_map = self._map_headers(headers)

                        if not header_map:
                            continue

                        for row in table[1:]:
                            txn = self._parse_table_row(row, header_map)
                            if txn:
                                transactions.append(txn)

            return transactions if len(transactions) > 0 else []

        except Exception as e:
            logger.debug(f"pdfplumber table extraction failed: {e}")
            return []

    def _try_tabula(self, pdf_path: Path) -> List[Dict]:
        """Strategy 3: Extract using tabula-py (requires Java)"""
        if not TABULA_AVAILABLE:
            return []

        try:
            # Read all tables from PDF
            dfs = tabula.read_pdf(str(pdf_path), pages='all', multiple_tables=True)

            transactions = []
            for df in dfs:
                if df.empty:
                    continue

                # Try to map columns
                header_map = self._map_headers(df.columns.tolist())
                if not header_map:
                    continue

                for _, row in df.iterrows():
                    txn = self._parse_table_row(row.tolist(), header_map)
                    if txn:
                        transactions.append(txn)

            return transactions if len(transactions) > 0 else []

        except Exception as e:
            logger.debug(f"Tabula extraction failed: {e}")
            return []

    def _try_camelot(self, pdf_path: Path) -> List[Dict]:
        """Strategy 4: Extract using camelot-py (requires Ghostscript)"""
        if not CAMELOT_AVAILABLE:
            return []

        try:
            # Try stream mode first (text-based), then lattice mode (line-based)
            tables = camelot.read_pdf(str(pdf_path), pages='all', flavor='stream')

            if not tables or len(tables) == 0:
                tables = camelot.read_pdf(str(pdf_path), pages='all', flavor='lattice')

            transactions = []
            for table in tables:
                df = table.df

                if df.empty:
                    continue

                # First row is usually header
                headers = df.iloc[0].tolist()
                header_map = self._map_headers(headers)

                if not header_map:
                    continue

                for idx in range(1, len(df)):
                    row = df.iloc[idx].tolist()
                    txn = self._parse_table_row(row, header_map)
                    if txn:
                        transactions.append(txn)

            return transactions if len(transactions) > 0 else []

        except Exception as e:
            logger.debug(f"Camelot extraction failed: {e}")
            return []

    def _try_ocr(self, pdf_path: Path) -> List[Dict]:
        """Strategy 5: OCR for scanned PDFs (requires Tesseract)"""
        if not OCR_AVAILABLE:
            return []

        try:
            logger.info("Using OCR (slow) - this may take a while...")

            # Convert PDF pages to images
            images = pdf2image.convert_from_path(str(pdf_path))

            transactions = []
            for page_num, image in enumerate(images):
                # Extract text using OCR
                text = pytesseract.image_to_string(image)

                if not text:
                    continue

                lines = text.split('\n')
                for line in lines:
                    txn = self._parse_text_line(line)
                    if txn:
                        transactions.append(txn)

            return transactions if len(transactions) > 0 else []

        except Exception as e:
            logger.debug(f"OCR extraction failed: {e}")
            return []

    def _extract_tables(self, pdf) -> List[Dict]:
        """Extract transactions from table-based PDFs"""
        transactions = []

        for page in pdf.pages:
            tables = page.extract_tables()

            for table in tables:
                if not table:
                    continue

                # Assume first row is header
                headers = table[0] if table else []
                header_map = self._map_headers(headers)

                if not header_map:
                    continue  # Can't identify columns

                for row in table[1:]:
                    if not row or len(row) < len(headers):
                        continue

                    txn = self._parse_table_row(row, header_map)
                    if txn:
                        transactions.append(txn)

        return transactions

    def _extract_text(self, pdf) -> List[Dict]:
        """Extract transactions from text-based PDFs"""
        transactions = []

        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            lines = text.split('\n')
            for line in lines:
                txn = self._parse_text_line(line)
                if txn:
                    transactions.append(txn)

        return transactions

    def _map_headers(self, headers: List[str]) -> Dict[str, int]:
        """
        Map table headers to column indices

        Returns:
            Dict mapping field names to column indices
        """
        header_map = {}

        # Common header patterns (case-insensitive)
        patterns = {
            'date': ['date', 'txn date', 'transaction date', 'value date'],
            'description': ['description', 'particulars', 'narration', 'details', 'transaction details'],
            'debit': ['debit', 'withdrawal', 'dr', 'paid out', 'debits'],
            'credit': ['credit', 'deposit', 'cr', 'paid in', 'credits'],
            'amount': ['amount', 'value'],
            'balance': ['balance', 'closing balance', 'bal']
        }

        for idx, header in enumerate(headers):
            if not header:
                continue

            header_lower = header.lower().strip()

            for field, keywords in patterns.items():
                if any(kw in header_lower for kw in keywords):
                    header_map[field] = idx
                    break

        return header_map if 'date' in header_map else {}

    def _parse_table_row(self, row: List[str], header_map: Dict[str, int]) -> Dict:
        """Parse a table row into transaction dict"""
        try:
            date_str = row[header_map['date']].strip() if 'date' in header_map else None
            if not date_str:
                return None

            # Parse date
            date = self._parse_date(date_str)
            if not date:
                return None

            # Description
            desc_idx = header_map.get('description')
            description = row[desc_idx].strip() if desc_idx is not None and desc_idx < len(row) else ""

            # Amount (check debit/credit columns)
            debit_idx = header_map.get('debit')
            credit_idx = header_map.get('credit')
            amount_idx = header_map.get('amount')

            debit = self._parse_amount(row[debit_idx]) if debit_idx is not None and debit_idx < len(row) else 0
            credit = self._parse_amount(row[credit_idx]) if credit_idx is not None and credit_idx < len(row) else 0
            amount = self._parse_amount(row[amount_idx]) if amount_idx is not None and amount_idx < len(row) else 0

            # Determine transaction type and amount
            if debit > 0:
                txn_type = "debit"
                txn_amount = debit
            elif credit > 0:
                txn_type = "credit"
                txn_amount = credit
            elif amount > 0:
                # Need to infer from description or default to debit
                txn_type = "debit"
                txn_amount = amount
            else:
                return None

            # Balance
            balance_idx = header_map.get('balance')
            balance = self._parse_amount(row[balance_idx]) if balance_idx is not None and balance_idx < len(row) else None

            return {
                'date': date,
                'description': description,
                'type': txn_type,
                'amount': txn_amount,
                'balance': balance,
                'source': 'pdf_table'
            }

        except Exception as e:
            logger.debug(f"Failed to parse table row: {e}")
            return None

    def _parse_text_line(self, line: str) -> Dict:
        """Parse a text line using regex patterns"""
        # Example pattern: DD/MM/YYYY Description... 1,234.56 Dr/Cr
        # This is highly bank-specific, provide multiple patterns

        for pattern_name, pattern in self.patterns.items():
            match = re.search(pattern, line)
            if match:
                return self._extract_from_match(match, pattern_name)

        return None

    def _load_patterns(self) -> Dict[str, str]:
        """Load regex patterns for text extraction"""
        return {
            'standard': r'(\d{2}[/-]\d{2}[/-]\d{4})\s+(.+?)\s+([\d,]+\.?\d*)\s+(Dr|Cr|Debit|Credit)',
            'indian_bank': r'(\d{2}-\w{3}-\d{4})\s+(.+?)\s+([\d,]+\.\d{2})',
            # Add more patterns as needed
        }

    def _extract_from_match(self, match, pattern_name: str) -> Dict:
        """Extract transaction from regex match"""
        groups = match.groups()

        # Pattern-specific extraction
        if pattern_name == 'standard':
            return {
                'date': self._parse_date(groups[0]),
                'description': groups[1].strip(),
                'amount': self._parse_amount(groups[2]),
                'type': 'debit' if 'dr' in groups[3].lower() else 'credit',
                'source': 'pdf_text'
            }

        # Add more pattern handlers
        return None

    def _parse_date(self, date_str: str) -> str:
        """Parse date string to ISO format (YYYY-MM-DD)"""
        date_str = date_str.strip()

        # Common formats
        formats = [
            '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y',
            '%d/%m/%y', '%d-%m-%y',
            '%d-%b-%Y', '%d-%b-%y',
            '%d %b %Y', '%d %B %Y',
            '%Y-%m-%d'  # ISO format
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {date_str}")
        return None

    def _parse_amount(self, amount_str: str) -> float:
        """Parse amount string to float"""
        if not amount_str:
            return 0.0

        # Remove currency symbols, commas, spaces
        amount_str = str(amount_str).strip()
        amount_str = re.sub(r'[₹$,\s]', '', amount_str)

        # Handle negative amounts in parentheses
        if amount_str.startswith('(') and amount_str.endswith(')'):
            amount_str = '-' + amount_str[1:-1]

        try:
            return abs(float(amount_str))
        except ValueError:
            return 0.0


# Usage Example
if __name__ == "__main__":
    parser = PDFParser()
    transactions = parser.parse("sample_statements/statement.pdf")
    for txn in transactions:
        print(txn)
```

#### 4.1.2 CSV Parser (`ingest/csv_parser.py`)

```python
"""
Enhanced CSV Parser with auto-detection and multiple format support

Features:
- Auto-detect delimiter (comma, semicolon, tab, pipe)
- Auto-detect column mapping (flexible header matching)
- Handle multiple CSV formats (Indian banks, international)
- Support for BOM, different encodings
- Robust error handling
"""

import pandas as pd
import csv
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class CSVParser:
    """Parse bank statement CSVs into structured transactions"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.column_mapping_rules = self._load_column_mapping_rules()

    def parse(self, csv_path: str) -> List[Dict[str, Any]]:
        """
        Parse CSV file and return list of raw transactions

        Args:
            csv_path: Path to CSV file

        Returns:
            List[Dict]: Raw transaction dictionaries
        """
        try:
            # Auto-detect encoding
            encoding = self._detect_encoding(csv_path)

            # Auto-detect delimiter
            delimiter = self._detect_delimiter(csv_path, encoding)

            # Read CSV
            df = pd.read_csv(
                csv_path,
                encoding=encoding,
                delimiter=delimiter,
                skip_blank_lines=True,
                keep_default_na=False
            )

            # Clean and normalize column names
            df.columns = [str(col).strip() for col in df.columns]

            # Remove completely empty rows
            df = df.dropna(how='all')

            # Map columns to standard names
            column_map = self._map_columns(df.columns.tolist())

            if not column_map:
                logger.error(f"Could not identify required columns in {csv_path}")
                return []

            # Parse rows
            transactions = []
            for idx, row in df.iterrows():
                txn = self._parse_row(row, column_map)
                if txn:
                    txn['source'] = 'csv'
                    txn['source_file'] = Path(csv_path).name
                    transactions.append(txn)

            logger.info(f"Parsed {len(transactions)} transactions from {csv_path}")
            return transactions

        except Exception as e:
            logger.error(f"Failed to parse CSV {csv_path}: {e}")
            return []

    def _detect_encoding(self, file_path: str) -> str:
        """Detect file encoding"""
        # Try common encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read(1024)  # Read small chunk
                return encoding
            except UnicodeDecodeError:
                continue

        return 'utf-8'  # Default fallback

    def _detect_delimiter(self, file_path: str, encoding: str) -> str:
        """Auto-detect CSV delimiter"""
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                sample = f.read(2048)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                return delimiter
        except:
            return ','  # Default to comma

    def _load_column_mapping_rules(self) -> Dict[str, List[str]]:
        """
        Load column mapping rules

        Returns:
            Dict mapping standard field names to possible column names
        """
        return {
            'date': [
                'date', 'txn date', 'transaction date', 'value date',
                'posting date', 'txn_date', 'transaction_date', 'tran date'
            ],
            'description': [
                'description', 'particulars', 'narration', 'details',
                'transaction details', 'remarks', 'transaction remarks',
                'transaction_remarks', 'remark', 'txn details'
            ],
            'debit': [
                'debit', 'withdrawal', 'withdrawal amount', 'debit amount',
                'dr', 'paid out', 'debits', 'withdrawal amount (inr)',
                'withdrawal_amount', 'debit_amount'
            ],
            'credit': [
                'credit', 'deposit', 'deposit amount', 'credit amount',
                'cr', 'paid in', 'credits', 'deposit amount (inr)',
                'deposit_amount', 'credit_amount'
            ],
            'amount': [
                'amount', 'transaction amount', 'txn amount', 'value',
                'transaction_amount', 'txn_amount'
            ],
            'balance': [
                'balance', 'closing balance', 'available balance',
                'balance (inr)', 'balance_inr', 'bal'
            ],
            'cheque_no': [
                'cheque number', 'cheque no', 'chq no', 'check number',
                'cheque_number', 'chq_no'
            ]
        }

    def _map_columns(self, columns: List[str]) -> Dict[str, str]:
        """
        Map CSV columns to standard field names

        Args:
            columns: List of column names from CSV

        Returns:
            Dict mapping standard field names to actual column names
        """
        column_map = {}
        columns_lower = {col.lower().strip(): col for col in columns}

        for standard_field, possible_names in self.column_mapping_rules.items():
            for possible_name in possible_names:
                if possible_name.lower() in columns_lower:
                    column_map[standard_field] = columns_lower[possible_name.lower()]
                    break

        # Must have at least date and (description or amount)
        required = ['date']
        if not all(field in column_map for field in required):
            return {}

        return column_map

    def _parse_row(self, row: pd.Series, column_map: Dict[str, str]) -> Optional[Dict]:
        """Parse a CSV row into transaction dict"""
        try:
            # Date (required)
            date_col = column_map.get('date')
            if not date_col or pd.isna(row[date_col]) or str(row[date_col]).strip() == '':
                return None

            date_str = str(row[date_col]).strip()

            # Description
            desc_col = column_map.get('description')
            description = str(row[desc_col]).strip() if desc_col and not pd.isna(row.get(desc_col)) else ""

            if not description:
                return None  # Skip rows without description

            # Parse amounts
            debit_col = column_map.get('debit')
            credit_col = column_map.get('credit')
            amount_col = column_map.get('amount')

            debit = self._parse_amount(row.get(debit_col)) if debit_col else 0
            credit = self._parse_amount(row.get(credit_col)) if credit_col else 0
            amount = self._parse_amount(row.get(amount_col)) if amount_col else 0

            # Determine transaction type and amount
            if debit > 0:
                txn_type = "debit"
                txn_amount = debit
            elif credit > 0:
                txn_type = "credit"
                txn_amount = credit
            elif amount > 0:
                # Try to infer from description
                txn_type = self._infer_type_from_description(description)
                txn_amount = amount
            else:
                return None  # No valid amount

            # Balance
            balance_col = column_map.get('balance')
            balance = self._parse_amount(row.get(balance_col)) if balance_col else None

            # Cheque number
            cheque_col = column_map.get('cheque_no')
            cheque_no = str(row.get(cheque_col)).strip() if cheque_col and not pd.isna(row.get(cheque_col)) else None

            return {
                'date': date_str,  # Will be normalized later
                'description': description,
                'type': txn_type,
                'amount': txn_amount,
                'balance': balance,
                'cheque_number': cheque_no
            }

        except Exception as e:
            logger.debug(f"Failed to parse CSV row: {e}")
            return None

    def _parse_amount(self, value) -> float:
        """Parse amount value to float"""
        if pd.isna(value) or value == '' or value is None:
            return 0.0

        # Convert to string
        amount_str = str(value).strip()

        # Remove currency symbols, commas, spaces
        amount_str = amount_str.replace('₹', '').replace('$', '').replace(',', '').replace(' ', '')

        # Handle parentheses as negative
        if amount_str.startswith('(') and amount_str.endswith(')'):
            amount_str = '-' + amount_str[1:-1]

        try:
            return abs(float(amount_str))
        except ValueError:
            return 0.0

    def _infer_type_from_description(self, description: str) -> str:
        """Infer transaction type from description"""
        description_lower = description.lower()

        credit_keywords = ['deposit', 'credit', 'salary', 'refund', 'cashback']
        debit_keywords = ['withdrawal', 'debit', 'purchase', 'payment', 'transfer']

        if any(kw in description_lower for kw in credit_keywords):
            return 'credit'
        elif any(kw in description_lower for kw in debit_keywords):
            return 'debit'

        return 'debit'  # Default


# Usage Example
if __name__ == "__main__":
    parser = CSVParser()
    transactions = parser.parse("sample_statements/statement.csv")
    for txn in transactions:
        print(txn)
```

#### 4.1.3 Normalizer (`ingest/normalizer.py`)

```python
"""
Transaction Normalizer

Converts raw parsed transactions into canonical schema format
Handles:
- Date normalization to ISO format
- Amount parsing and validation
- Merchant extraction from descriptions
- Channel detection (UPI/NEFT/IMPS/etc)
- Description cleaning
- Field mapping
"""

from typing import Dict, Any, Optional
from datetime import datetime
import re
import logging

from schema import CanonicalTransaction, mask_account_number

logger = logging.getLogger(__name__)

class TransactionNormalizer:
    """Normalize raw transactions to canonical format"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.channel_patterns = self._load_channel_patterns()
        self.upi_pattern = re.compile(r'UPI/([^/]+)/([^/]+)', re.IGNORECASE)

    def normalize(self, raw_transaction: Dict[str, Any]) -> CanonicalTransaction:
        """
        Convert raw transaction to canonical format

        Args:
            raw_transaction: Dict from parser (PDF/CSV)

        Returns:
            CanonicalTransaction object
        """
        try:
            # Extract and normalize date
            date_iso = self._normalize_date(raw_transaction.get('date'))

            # Extract transaction type and amount
            txn_type = raw_transaction.get('type', 'debit')
            amount = float(raw_transaction.get('amount', 0.0))

            # Get description
            raw_description = raw_transaction.get('description', '')
            clean_description = self._clean_description(raw_description)

            # Extract merchant
            merchant_raw = self._extract_merchant(raw_description)

            # Detect channel
            channel = self._detect_channel(raw_description)

            # Extract UPI details if applicable
            upi_id, upi_ref = self._extract_upi_details(raw_description)

            # Extract account info (to be encrypted later)
            account_info = self._extract_account_info(raw_description)

            # Create canonical transaction
            txn = CanonicalTransaction(
                transaction_id=None,  # Will be generated
                date=date_iso,
                transaction_type=txn_type,
                amount=amount,
                currency="INR",
                raw_description=raw_description,
                clean_description=clean_description,
                merchant_raw=merchant_raw,
                merchant_canonical=None,  # Will be filled by mapper
                category="Uncategorized",  # Will be filled by categorizer
                category_source="none",
                category_confidence=0.0,
                channel=channel,
                transaction_mode=self._infer_mode(channel, raw_description),
                account_number_masked=mask_account_number(account_info.get('account', '')),
                counterparty_name=account_info.get('counterparty'),
                balance_after=raw_transaction.get('balance'),
                source=raw_transaction.get('source', 'unknown'),
                source_file=raw_transaction.get('source_file'),
                upi_id=upi_id,
                upi_ref_id=upi_ref,
                custom_fields={
                    'cheque_number': raw_transaction.get('cheque_number'),
                    'raw_account': account_info.get('account')  # Temporary, will be vaulted
                }
            )

            return txn

        except Exception as e:
            logger.error(f"Failed to normalize transaction: {e}")
            logger.error(f"Raw transaction: {raw_transaction}")
            raise

    def _normalize_date(self, date_input: Any) -> str:
        """Normalize date to ISO format (YYYY-MM-DD)"""
        if not date_input:
            return datetime.now().strftime('%Y-%m-%d')

        date_str = str(date_input).strip()

        # If already in ISO format
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return date_str

        # Common date formats
        formats = [
            '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y',
            '%d/%m/%y', '%d-%m-%y', '%d.%m.%y',
            '%d-%b-%Y', '%d-%b-%y', '%d %b %Y', '%d %B %Y',
            '%Y-%m-%d', '%Y/%m/%d',
            '%m/%d/%Y', '%m-%d-%Y'  # US format
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                # Handle 2-digit years
                if dt.year < 100:
                    dt = dt.replace(year=dt.year + 2000)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {date_str}, using current date")
        return datetime.now().strftime('%Y-%m-%d')

    def _clean_description(self, description: str) -> str:
        """Clean and normalize description text"""
        if not description:
            return ""

        # Remove excessive whitespace
        clean = re.sub(r'\s+', ' ', description).strip()

        # Remove common noise
        clean = re.sub(r'[/*]{2,}', ' ', clean)

        # Normalize separators
        clean = clean.replace('/', ' ').replace('|', ' ').replace('-', ' ')
        clean = re.sub(r'\s+', ' ', clean).strip()

        return clean

    def _extract_merchant(self, description: str) -> Optional[str]:
        """Extract merchant name from transaction description"""
        if not description:
            return None

        # UPI pattern: UPI/Merchant/...
        upi_match = self.upi_pattern.search(description)
        if upi_match:
            merchant = upi_match.group(1).strip()
            # Clean merchant name
            merchant = re.sub(r'\d+', '', merchant).strip()
            if merchant and len(merchant) > 2:
                return merchant

        # NEFT/IMPS pattern: NEFT/Merchant or to Merchant
        neft_pattern = r'(?:NEFT|IMPS|RTGS)[/\s]+(?:to\s+)?([A-Za-z\s]+)'
        neft_match = re.search(neft_pattern, description, re.IGNORECASE)
        if neft_match:
            merchant = neft_match.group(1).strip()
            if merchant and len(merchant) > 2:
                return merchant

        # Generic: Look for capitalized words
        # Skip common transaction keywords
        skip_keywords = {'UPI', 'NEFT', 'IMPS', 'RTGS', 'ATM', 'POS', 'BANK',
                        'PAYMENT', 'TRANSFER', 'WITHDRAWAL', 'DEPOSIT'}

        words = description.split()
        for word in words:
            if (word.isupper() and len(word) > 3 and
                word not in skip_keywords and
                not word.isdigit()):
                return word

        return None

    def _detect_channel(self, description: str) -> Optional[str]:
        """Detect transaction channel from description"""
        if not description:
            return None

        desc_upper = description.upper()

        for channel, patterns in self.channel_patterns.items():
            if any(pattern in desc_upper for pattern in patterns):
                return channel

        return None

    def _load_channel_patterns(self) -> Dict[str, List[str]]:
        """Load channel detection patterns"""
        return {
            'upi': ['UPI/', 'UPI-', '@', 'PAYTM', 'GPAY', 'PHONEPE', 'BHIM'],
            'neft': ['NEFT', 'NEFT/'],
            'imps': ['IMPS', 'IMPS/'],
            'rtgs': ['RTGS', 'RTGS/'],
            'card': ['POS', 'CARD', 'VISA', 'MASTERCARD', 'RUPAY'],
            'atm': ['ATM', 'CASH WDL', 'CASH WITHDRAWAL'],
            'cheque': ['CHQ', 'CHEQUE', 'CHECK'],
            'ach': ['ACH/', 'NACH', 'ECS'],
            'cash': ['CASH DEP', 'CASH DEPOSIT']
        }

    def _extract_upi_details(self, description: str) -> tuple:
        """Extract UPI ID and reference from description"""
        upi_id = None
        upi_ref = None

        # Extract UPI ID (format: name@bank or phone@bank)
        upi_id_pattern = r'([\w\.\-]+@[\w]+)'
        upi_id_match = re.search(upi_id_pattern, description)
        if upi_id_match:
            upi_id = upi_id_match.group(1)

        # Extract UPI reference number (typically long numeric)
        upi_ref_pattern = r'(\d{12,})'
        upi_ref_match = re.search(upi_ref_pattern, description)
        if upi_ref_match:
            upi_ref = upi_ref_match.group(1)

        return upi_id, upi_ref

    def _extract_account_info(self, description: str) -> Dict[str, str]:
        """Extract account numbers and counterparty info"""
        info = {}

        # Extract account numbers (8-20 digits)
        account_pattern = r'\b(\d{8,20})\b'
        account_match = re.search(account_pattern, description)
        if account_match:
            info['account'] = account_match.group(1)

        # Extract counterparty (after "to" or "from")
        counterparty_pattern = r'(?:to|from)\s+([A-Za-z\s]{3,30})'
        counterparty_match = re.search(counterparty_pattern, description, re.IGNORECASE)
        if counterparty_match:
            info['counterparty'] = counterparty_match.group(1).strip()

        return info

    def _infer_mode(self, channel: Optional[str], description: str) -> Optional[str]:
        """Infer transaction mode from channel and description"""
        if not channel:
            return None

        if channel in ['upi', 'neft', 'imps', 'rtgs']:
            return 'online'
        elif channel == 'card':
            if 'POS' in description.upper():
                return 'pos'
            return 'online'
        elif channel == 'atm':
            return 'atm'
        elif channel == 'cash':
            return 'branch'

        return None


# Usage Example
if __name__ == "__main__":
    normalizer = TransactionNormalizer()

    raw_txn = {
        'date': '15/10/2025',
        'description': 'UPI/Swiggy Ltd/swiggyupi@axb/Payment/AXIS BANK/266553694203',
        'type': 'debit',
        'amount': 1250.00,
        'balance': 45230.50,
        'source': 'csv'
    }

    canonical_txn = normalizer.normalize(raw_txn)
    print(canonical_txn.to_json_line())
```

---

## 6. Merchant Mapping Module

### 5.1 Merchant Mapper (`mapping/merchant_mapper.py`)

```python
"""
Merchant Mapping with Multi-Strategy Matching

Strategies (in priority order):
1. Exact match - Direct lookup in merchant_map.csv
2. Regex rules - Pattern-based matching (e.g., APOLLO* -> Apollo Pharmacy)
3. Fuzzy match - rapidfuzz for similar names with confidence threshold

Configuration: mapping/config.yaml
Merchant Map: mapping/merchant_map.csv
Rules: mapping/rules.py
"""

from typing import Dict, Any, Optional, Tuple, List
from rapidfuzz import fuzz, process
import pandas as pd
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class MerchantMapper:
    """Map raw merchant names to canonical names with category"""

    def __init__(self, config_path: str = "mapping/config.yaml"):
        self.config = self._load_config(config_path)
        self.merchant_map = self._load_merchant_map()
        self.regex_rules = self._load_regex_rules()
        self.fuzzy_threshold = self.config.get('fuzzy_threshold', 85)

        # Pre-build fuzzy search index
        self.canonical_merchants = list(self.merchant_map.keys())

    def map_merchant(self, merchant_raw: Optional[str]) -> Dict[str, Any]:
        """
        Map raw merchant to canonical with category

        Returns:
            Dict with keys: merchant_canonical, category, confidence, method
        """
        if not merchant_raw:
            return {
                'merchant_canonical': None,
                'category': 'Uncategorized',
                'confidence': 0.0,
                'method': 'none'
            }

        merchant_clean = self._clean_merchant_name(merchant_raw)

        # Strategy 1: Exact match
        result = self._exact_match(merchant_clean)
        if result:
            return result

        # Strategy 2: Regex rules
        result = self._regex_match(merchant_clean)
        if result:
            return result

        # Strategy 3: Fuzzy match
        result = self._fuzzy_match(merchant_clean)
        if result:
            return result

        # No match found
        return {
            'merchant_canonical': merchant_raw,
            'category': 'Uncategorized',
            'confidence': 0.0,
            'method': 'none'
        }

    def _exact_match(self, merchant: str) -> Optional[Dict]:
        """Exact match in merchant map"""
        merchant_lower = merchant.lower()

        # Check exact match
        if merchant_lower in self.merchant_map:
            mapping = self.merchant_map[merchant_lower]
            return {
                'merchant_canonical': mapping['canonical'],
                'category': mapping['category'],
                'confidence': 1.0,
                'method': 'exact'
            }

        return None

    def _regex_match(self, merchant: str) -> Optional[Dict]:
        """Match using regex rules"""
        for rule in self.regex_rules:
            pattern = rule['pattern']
            if re.search(pattern, merchant, re.IGNORECASE):
                return {
                    'merchant_canonical': rule['canonical'],
                    'category': rule['category'],
                    'confidence': 0.95,
                    'method': 'regex'
                }

        return None

    def _fuzzy_match(self, merchant: str) -> Optional[Dict]:
        """Fuzzy match using rapidfuzz"""
        # Use process.extractOne for best match
        result = process.extractOne(
            merchant.lower(),
            self.canonical_merchants,
            scorer=fuzz.WRatio,
            score_cutoff=self.fuzzy_threshold
        )

        if result:
            canonical_lower, score, _ = result
            mapping = self.merchant_map[canonical_lower]

            return {
                'merchant_canonical': mapping['canonical'],
                'category': mapping['category'],
                'confidence': score / 100.0,
                'method': 'fuzzy'
            }

        return None

    def _clean_merchant_name(self, merchant: str) -> str:
        """Clean merchant name for better matching"""
        # Remove common suffixes
        merchant = re.sub(r'\s+(ltd|limited|pvt|private|inc|corp|llc)\.?$', '', merchant, flags=re.IGNORECASE)

        # Remove special characters
        merchant = re.sub(r'[^\w\s]', ' ', merchant)

        # Normalize whitespace
        merchant = re.sub(r'\s+', ' ', merchant).strip()

        return merchant

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration"""
        try:
            import yaml
            with open(config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except:
            # Default config
            return {
                'fuzzy_threshold': 85,
                'merchant_map_path': 'mapping/merchant_map.csv',
                'rules_path': 'mapping/rules.py'
            }

    def _load_merchant_map(self) -> Dict[str, Dict]:
        """Load merchant mapping from CSV"""
        merchant_map_path = self.config.get('merchant_map_path', 'mapping/merchant_map.csv')

        try:
            df = pd.read_csv(merchant_map_path)

            # Expected columns: merchant_raw, merchant_canonical, category
            merchant_map = {}
            for _, row in df.iterrows():
                raw = str(row['merchant_raw']).lower().strip()
                canonical = str(row['merchant_canonical']).strip()
                category = str(row['category']).strip()

                merchant_map[raw] = {
                    'canonical': canonical,
                    'category': category
                }

            logger.info(f"Loaded {len(merchant_map)} merchant mappings")
            return merchant_map

        except Exception as e:
            logger.warning(f"Could not load merchant map: {e}")
            return {}

    def _load_regex_rules(self) -> List[Dict]:
        """Load regex matching rules"""
        # Can be loaded from rules.py or inline
        default_rules = [
            {
                'pattern': r'^apollo',
                'canonical': 'Apollo Pharmacy',
                'category': 'Pharmacy'
            },
            {
                'pattern': r'swiggy',
                'canonical': 'Swiggy',
                'category': 'Food'
            },
            {
                'pattern': r'zomato',
                'canonical': 'Zomato',
                'category': 'Food'
            },
            {
                'pattern': r'zepto',
                'canonical': 'Zepto',
                'category': 'Food'
            },
            {
                'pattern': r'netflix',
                'canonical': 'Netflix',
                'category': 'Subscriptions'
            },
            {
                'pattern': r'amazon',
                'canonical': 'Amazon',
                'category': 'Shopping'
            },
            {
                'pattern': r'flipkart',
                'canonical': 'Flipkart',
                'category': 'Shopping'
            },
            {
                'pattern': r'(hp\s*pay|indian\s*oil|bharat\s*petroleum)',
                'canonical': 'Fuel Station',
                'category': 'Fuel'
            },
            {
                'pattern': r'(starbucks|ccd|cafe\s*coffee\s*day)',
                'canonical': 'Coffee Shop',
                'category': 'Food'
            },
            {
                'pattern': r'(uber|ola|rapido)',
                'canonical': 'Ride Hailing',
                'category': 'Transport'
            },
            {
                'pattern': r'(groww|zerodha|upstox)',
                'canonical': 'Investment Platform',
                'category': 'Investment'
            },
        ]

        return default_rules

    def add_merchant_mapping(self, merchant_raw: str, merchant_canonical: str, category: str):
        """Add new merchant mapping (runtime)"""
        merchant_lower = merchant_raw.lower().strip()
        self.merchant_map[merchant_lower] = {
            'canonical': merchant_canonical,
            'category': category
        }
        self.canonical_merchants = list(self.merchant_map.keys())


# Usage Example
if __name__ == "__main__":
    mapper = MerchantMapper()

    test_merchants = [
        "Swiggy Ltd",
        "APOLLO PHARMACY",
        "Netflix India",
        "HP PAY STATION",
        "Unknown Store"
    ]

    for merchant in test_merchants:
        result = mapper.map_merchant(merchant)
        print(f"{merchant} -> {result}")
```

### 5.2 Merchant Map CSV (`mapping/merchant_map.csv`)

```csv
merchant_raw,merchant_canonical,category
swiggy,Swiggy,Food
swiggy ltd,Swiggy,Food
zomato,Zomato,Food
zepto,Zepto,Food
zepto online,Zepto,Food
apollo pharmacy,Apollo Pharmacy,Pharmacy
apollo dia,Apollo Pharmacy,Pharmacy
netflix,Netflix,Subscriptions
netflix india,Netflix,Subscriptions
amazon,Amazon,Shopping
amazon pay,Amazon,Shopping
flipkart,Flipkart,Shopping
cred,CRED,Bills
paytm,Paytm,Bills
phonepe,PhonePe,Bills
google pay,Google Pay,Bills
gpay,Google Pay,Bills
hp pay,HP Petrol Pump,Fuel
indian oil,Indian Oil,Fuel
bharat petroleum,Bharat Petroleum,Fuel
bpcl,Bharat Petroleum,Fuel
groww,Groww,Investment
zerodha,Zerodha,Investment
upstox,Upstox,Investment
uber,Uber,Transport
ola,Ola,Transport
rapido,Rapido,Transport
starbucks,Starbucks,Food
cafe coffee day,Cafe Coffee Day,Food
ccd,Cafe Coffee Day,Food
dominos,Dominos,Food
pizza hut,Pizza Hut,Food
mcdonald,McDonalds,Food
kfc,KFC,Food
airtel,Airtel,Bills
jio,Reliance Jio,Bills
vodafone,Vodafone,Bills
electricity board,Electricity Board,Bills
gas agency,Gas Agency,Bills
rent,Rent Payment,Rent
```

### 5.3 Configuration (`mapping/config.yaml`)

```yaml
# Merchant Mapping Configuration

fuzzy_threshold: 85  # Minimum similarity score (0-100)

merchant_map_path: mapping/merchant_map.csv
rules_path: mapping/rules.py

# Priority settings
strategy_priority:
  - exact
  - regex
  - fuzzy

# Confidence thresholds for category resolution
category_resolution:
  mapping_threshold: 0.8  # Use mapping if confidence >= 0.8
  ml_threshold: 0.6       # Use ML if confidence >= 0.6

# Merchant name cleaning
cleaning_rules:
  remove_suffixes:
    - ltd
    - limited
    - pvt
    - private
    - inc
    - corp
    - llc
  remove_prefixes:
    - mr
    - mrs
    - ms
```

---

## 7. Privacy & Vault Module

### 6.1 Privacy Vault (`privacy/vault.py`)

```python
"""
Privacy Vault with AES-GCM Encryption and Key Rotation

SECURITY NOTES:
- Uses AES-256-GCM authenticated encryption
- Keys stored in secure file with OS-level permissions (600)
- Supports key rotation without data loss
- All PII access is logged for audit trail

Key Management:
1. POC/Development: Keys stored in local file with 600 permissions
2. Production Options:
   - Use OS keyring (keyring library)
   - Use cloud KMS (AWS KMS, GCP KMS, Azure Key Vault)
   - Use HSM for highest security

Key Storage Priority:
1. VAULT_KEY environment variable (base64 encoded)
2. VAULT_KEY_FILE path (defaults to .vault_key with 600 perms)
3. Generate new key and save to VAULT_KEY_FILE

IMPORTANT:
- NEVER commit .vault_key to git (add to .gitignore)
- Backup vault key securely (key loss = permanent data loss)
- Rotate keys periodically (use rotate_key method)
"""

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import os
import stat
import base64
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class PrivacyVault:
    """Manage encrypted storage of PII with secure key management"""

    def __init__(self, vault_path: str = "data/vault.db",
                 key: Optional[bytes] = None,
                 key_file: Optional[str] = None):
        self.vault_path = Path(vault_path)
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)

        # Key file location (from env var or default)
        self.key_file = Path(key_file) if key_file else Path(os.getenv('VAULT_KEY_FILE', '.vault_key'))

        # Initialize or load encryption key
        self.key = key or self._get_or_create_key()
        self.aesgcm = AESGCM(self.key)

        # Track key version for rotation
        self.key_version = self._get_key_version()

        # In-memory vault (could be SQLite for production)
        self.vault = self._load_vault()

        # Audit log for PII access
        self.audit_log_path = self.vault_path.parent / "vault_audit.log"

    def store_pii(self, pii_data: Dict[str, Any]) -> str:
        """
        Store PII and return reference ID

        Args:
            pii_data: Dict containing PII fields

        Returns:
            pii_ref: Reference ID to retrieve PII later
        """
        try:
            # Generate reference ID
            pii_ref = self._generate_ref_id()

            # Serialize PII data
            pii_json = json.dumps(pii_data)
            pii_bytes = pii_json.encode('utf-8')

            # Encrypt
            nonce = os.urandom(12)  # 96-bit nonce for GCM
            ciphertext = self.aesgcm.encrypt(nonce, pii_bytes, None)

            # Store encrypted data with nonce
            encrypted_package = {
                'nonce': base64.b64encode(nonce).decode('utf-8'),
                'ciphertext': base64.b64encode(ciphertext).decode('utf-8')
            }

            self.vault[pii_ref] = encrypted_package
            self._save_vault()

            logger.debug(f"Stored PII with ref: {pii_ref}")
            return pii_ref

        except Exception as e:
            logger.error(f"Failed to store PII: {e}")
            raise

    def retrieve_pii(self, pii_ref: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve PII data by reference ID

        Args:
            pii_ref: Reference ID

        Returns:
            Dict containing PII fields or None if not found
        """
        try:
            if pii_ref not in self.vault:
                logger.warning(f"PII ref not found: {pii_ref}")
                return None

            encrypted_package = self.vault[pii_ref]

            # Decode
            nonce = base64.b64decode(encrypted_package['nonce'])
            ciphertext = base64.b64decode(encrypted_package['ciphertext'])

            # Decrypt
            plaintext = self.aesgcm.decrypt(nonce, ciphertext, None)
            pii_json = plaintext.decode('utf-8')
            pii_data = json.loads(pii_json)

            return pii_data

        except Exception as e:
            logger.error(f"Failed to retrieve PII: {e}")
            return None

    def delete_pii(self, pii_ref: str) -> bool:
        """Delete PII by reference"""
        if pii_ref in self.vault:
            del self.vault[pii_ref]
            self._save_vault()
            logger.info(f"Deleted PII ref: {pii_ref}")
            return True
        return False

    def _get_or_create_key(self) -> bytes:
        """
        Get encryption key with priority:
        1. VAULT_KEY environment variable
        2. Key file (VAULT_KEY_FILE or .vault_key)
        3. Generate new key
        """
        # Priority 1: Environment variable
        key_b64 = os.environ.get('VAULT_KEY')
        if key_b64:
            try:
                logger.info("Using vault key from VAULT_KEY environment variable")
                return base64.b64decode(key_b64)
            except Exception as e:
                logger.error(f"Invalid VAULT_KEY in environment: {e}")

        # Priority 2: Key file
        if self.key_file.exists():
            try:
                return self._load_key_from_file()
            except Exception as e:
                logger.error(f"Failed to load key from {self.key_file}: {e}")

        # Priority 3: Generate new key
        return self._generate_and_save_key()

    def _load_key_from_file(self) -> bytes:
        """Load key from secure key file"""
        # Check file permissions (should be 600)
        file_stat = self.key_file.stat()
        if file_stat.st_mode & 0o777 != 0o600:
            logger.warning(f"Key file {self.key_file} has insecure permissions: {oct(file_stat.st_mode)}")
            logger.warning("Recommended: chmod 600 .vault_key")

        with open(self.key_file, 'r') as f:
            key_data = json.load(f)

        key_b64 = key_data['key']
        logger.info(f"Loaded vault key from {self.key_file} (version: {key_data.get('version', 1)})")

        return base64.b64decode(key_b64)

    def _generate_and_save_key(self) -> bytes:
        """Generate new encryption key and save securely"""
        logger.warning("Generating new vault encryption key...")

        # Generate 256-bit key
        key = AESGCM.generate_key(bit_length=256)
        key_b64 = base64.b64encode(key).decode('utf-8')

        # Save to key file with metadata
        key_data = {
            'key': key_b64,
            'version': 1,
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'algorithm': 'AES-256-GCM'
        }

        with open(self.key_file, 'w') as f:
            json.dump(key_data, f, indent=2)

        # Set secure file permissions (600 = rw-------)
        os.chmod(self.key_file, stat.S_IRUSR | stat.S_IWUSR)

        logger.warning(f"✓ Vault key saved to: {self.key_file}")
        logger.warning(f"✓ File permissions set to: 600 (owner read/write only)")
        logger.warning("⚠️  IMPORTANT: Backup this key securely!")
        logger.warning("⚠️  Key loss = permanent PII data loss!")
        logger.warning(f"⚠️  Add {self.key_file} to .gitignore")

        return key

    def _get_key_version(self) -> int:
        """Get current key version"""
        if not self.key_file.exists():
            return 1

        try:
            with open(self.key_file, 'r') as f:
                key_data = json.load(f)
            return key_data.get('version', 1)
        except:
            return 1

    def rotate_key(self, new_key: Optional[bytes] = None) -> bool:
        """
        Rotate encryption key and re-encrypt all vault data

        Args:
            new_key: New encryption key (generates random if None)

        Returns:
            bool: Success status

        IMPORTANT: This operation:
        1. Decrypts all PII with old key
        2. Encrypts all PII with new key
        3. Updates key file with new version
        4. Creates backup of old vault

        WARNING: Ensure you have a backup before rotating!
        """
        logger.warning("Starting key rotation process...")

        try:
            # Backup current vault
            backup_path = self.vault_path.parent / f"vault_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.db"
            import shutil
            shutil.copy2(self.vault_path, backup_path)
            logger.info(f"Created vault backup: {backup_path}")

            # Decrypt all PII with old key
            old_aesgcm = self.aesgcm
            decrypted_data = {}

            for pii_ref, encrypted_package in self.vault.items():
                try:
                    nonce = base64.b64decode(encrypted_package['nonce'])
                    ciphertext = base64.b64decode(encrypted_package['ciphertext'])
                    plaintext = old_aesgcm.decrypt(nonce, ciphertext, None)
                    pii_json = plaintext.decode('utf-8')
                    decrypted_data[pii_ref] = json.loads(pii_json)
                except Exception as e:
                    logger.error(f"Failed to decrypt {pii_ref}: {e}")
                    raise

            logger.info(f"Decrypted {len(decrypted_data)} PII entries with old key")

            # Generate or use new key
            if new_key is None:
                new_key = AESGCM.generate_key(bit_length=256)

            new_aesgcm = AESGCM(new_key)

            # Re-encrypt all PII with new key
            new_vault = {}
            for pii_ref, pii_data in decrypted_data.items():
                pii_json = json.dumps(pii_data)
                pii_bytes = pii_json.encode('utf-8')

                nonce = os.urandom(12)
                ciphertext = new_aesgcm.encrypt(nonce, pii_bytes, None)

                new_vault[pii_ref] = {
                    'nonce': base64.b64encode(nonce).decode('utf-8'),
                    'ciphertext': base64.b64encode(ciphertext).decode('utf-8')
                }

            logger.info(f"Re-encrypted {len(new_vault)} PII entries with new key")

            # Update vault and key
            self.vault = new_vault
            self.key = new_key
            self.aesgcm = new_aesgcm
            self.key_version += 1

            # Save new key
            key_b64 = base64.b64encode(new_key).decode('utf-8')
            key_data = {
                'key': key_b64,
                'version': self.key_version,
                'created_at': datetime.utcnow().isoformat() + 'Z',
                'rotated_from_version': self.key_version - 1,
                'algorithm': 'AES-256-GCM'
            }

            with open(self.key_file, 'w') as f:
                json.dump(key_data, f, indent=2)

            os.chmod(self.key_file, stat.S_IRUSR | stat.S_IWUSR)

            # Save updated vault
            self._save_vault()

            logger.warning(f"✓ Key rotation complete!")
            logger.warning(f"✓ New key version: {self.key_version}")
            logger.warning(f"✓ Backup saved to: {backup_path}")
            logger.warning(f"⚠️  IMPORTANT: Backup new key from {self.key_file}")

            return True

        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            logger.error(f"Vault backup available at: {backup_path}")
            return False

    def _generate_ref_id(self) -> str:
        """Generate unique reference ID"""
        import uuid
        return f"pii_{uuid.uuid4().hex[:16]}"

    def _load_vault(self) -> Dict:
        """Load vault from disk"""
        if not self.vault_path.exists():
            return {}

        try:
            with open(self.vault_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load vault: {e}")
            return {}

    def _save_vault(self):
        """Save vault to disk"""
        try:
            with open(self.vault_path, 'w') as f:
                json.dump(self.vault, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save vault: {e}")


# Usage Example
if __name__ == "__main__":
    vault = PrivacyVault()

    # Store PII
    pii_data = {
        'account_number': '1234567890123456',
        'pan': 'ABCDE1234F',
        'ifsc': 'AXIS0001234'
    }

    pii_ref = vault.store_pii(pii_data)
    print(f"Stored PII with ref: {pii_ref}")

    # Retrieve PII
    retrieved = vault.retrieve_pii(pii_ref)
    print(f"Retrieved PII: {retrieved}")
```

### 6.2 Masking Utilities (`privacy/masking.py`)

```python
"""
PII Masking Utilities

Functions to mask sensitive data for display and analytics
"""

import re
from typing import Optional

def mask_account_number(account: Optional[str], show_last: int = 4) -> Optional[str]:
    """
    Mask account number, show last N digits

    Example: 1234567890 -> XXXXXX7890
    """
    if not account:
        return None

    account = str(account).strip()

    if len(account) <= show_last:
        return 'X' * len(account)

    return 'X' * (len(account) - show_last) + account[-show_last:]


def mask_pan(pan: Optional[str]) -> Optional[str]:
    """
    Mask PAN number, show last 4 characters

    Example: ABCDE1234F -> XXXXXX234F
    """
    if not pan:
        return None

    pan = str(pan).strip().upper()

    if len(pan) != 10:
        return 'X' * len(pan)

    return 'X' * 6 + pan[-4:]


def mask_upi_id(upi: Optional[str]) -> Optional[str]:
    """
    Mask phone numbers in UPI IDs

    Example: 9876543210@paytm -> XXXXXX3210@paytm
    """
    if not upi:
        return None

    # Replace 10-digit phone numbers with XXXXXX[last 4]
    return re.sub(r'\d{10}', lambda m: 'XXXXXX' + m.group()[-4:], upi)


def mask_phone(phone: Optional[str]) -> Optional[str]:
    """
    Mask phone number, show last 4 digits

    Example: 9876543210 -> XXXXXX3210
    """
    if not phone:
        return None

    phone = re.sub(r'[^\d]', '', str(phone))  # Keep only digits

    if len(phone) < 4:
        return 'X' * len(phone)

    return 'X' * (len(phone) - 4) + phone[-4:]


def mask_email(email: Optional[str]) -> Optional[str]:
    """
    Mask email address

    Example: john.doe@example.com -> j***@example.com
    """
    if not email:
        return None

    parts = email.split('@')
    if len(parts) != 2:
        return 'X' * len(email)

    username = parts[0]
    domain = parts[1]

    if len(username) <= 1:
        masked_username = 'X'
    else:
        masked_username = username[0] + '*' * (len(username) - 1)

    return f"{masked_username}@{domain}"


def mask_ifsc(ifsc: Optional[str]) -> Optional[str]:
    """
    Mask IFSC code, show first 4 and last 2

    Example: AXIS0001234 -> AXIS00XXX34
    """
    if not ifsc:
        return None

    ifsc = str(ifsc).strip().upper()

    if len(ifsc) != 11:
        return 'X' * len(ifsc)

    return ifsc[:6] + 'X' * 3 + ifsc[-2:]


# Testing
if __name__ == "__main__":
    print(mask_account_number("1234567890123456"))  # XXXXXXXXXXXX3456
    print(mask_pan("ABCDE1234F"))  # XXXXXX234F
    print(mask_upi_id("9876543210@paytm"))  # XXXXXX3210@paytm
    print(mask_phone("9876543210"))  # XXXXXX3210
    print(mask_email("john.doe@example.com"))  # j*******@example.com
    print(mask_ifsc("AXIS0001234"))  # AXIS00XXX34
```

---

## 8. Account Aggregator Stub Module

### 7.1 AA Client Stub (`aa/aa_client_stub.py`)

```python
"""
Account Aggregator (AA) Integration Stub

Simulates the Sahamati AA flow for demonstration purposes.
In production, integrate with actual AA APIs (Sahamati, Finvu, etc.)

AA Flow:
1. User consent via AA app
2. Request token from FIU (Financial Information User)
3. Fetch account data from FIP (Financial Information Provider)
4. Parse and normalize transactions

This stub provides:
- Mock consent flow
- Mock data fetch
- Token storage (encrypted)
- Pluggable interface for real AA integration
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)

class AAClientStub:
    """Stub client for Account Aggregator integration"""

    def __init__(self, config_path: str = "aa/config.json"):
        self.config = self._load_config(config_path)
        self.token_store = {}  # In production: use encrypted storage
        self.is_stub = True  # Flag to indicate stub mode

    def request_consent(self, user_id: str, account_ids: List[str],
                       date_range: Dict[str, str]) -> Dict[str, Any]:
        """
        Request user consent for account aggregation

        Args:
            user_id: User identifier
            account_ids: List of account IDs to fetch
            date_range: {'from': 'YYYY-MM-DD', 'to': 'YYYY-MM-DD'}

        Returns:
            Dict with consent_id and status
        """
        logger.info(f"[STUB] Requesting consent for user {user_id}")

        # In real AA: Redirect user to AA app for consent
        # Here: Mock immediate consent
        consent_id = f"consent_{uuid.uuid4().hex[:16]}"

        consent_data = {
            'consent_id': consent_id,
            'user_id': user_id,
            'account_ids': account_ids,
            'date_range': date_range,
            'status': 'granted',  # Mock granted
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=90)).isoformat()
        }

        self.token_store[consent_id] = consent_data

        logger.info(f"[STUB] Consent granted: {consent_id}")

        return {
            'consent_id': consent_id,
            'status': 'granted',
            'message': '[STUB MODE] Consent granted immediately'
        }

    def fetch_account_data(self, consent_id: str) -> Dict[str, Any]:
        """
        Fetch account data using consent token

        Args:
            consent_id: Consent identifier

        Returns:
            Dict with account data and transactions
        """
        logger.info(f"[STUB] Fetching data for consent {consent_id}")

        if consent_id not in self.token_store:
            raise ValueError("Invalid consent ID")

        consent_data = self.token_store[consent_id]

        # In real AA: Call FIP APIs to fetch actual data
        # Here: Return mock data
        mock_data = self._generate_mock_account_data(consent_data)

        logger.info(f"[STUB] Fetched {len(mock_data['transactions'])} transactions")

        return mock_data

    def parse_aa_transactions(self, aa_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse AA data format to our standard format

        Args:
            aa_data: Raw data from AA

        Returns:
            List of standardized transaction dicts
        """
        transactions = []

        for txn in aa_data.get('transactions', []):
            # AA standard format (FI Data schema)
            parsed_txn = {
                'date': txn['transactionTimestamp'][:10],  # YYYY-MM-DD
                'description': txn['narration'],
                'type': 'debit' if txn['type'] == 'DEBIT' else 'credit',
                'amount': float(txn['amount']),
                'balance': float(txn.get('currentBalance', 0)),
                'source': 'aa',
                'source_file': f"aa_{aa_data.get('account_id', 'unknown')}"
            }

            transactions.append(parsed_txn)

        return transactions

    def _generate_mock_account_data(self, consent_data: Dict) -> Dict[str, Any]:
        """Generate mock account data for stub"""
        account_id = consent_data['account_ids'][0] if consent_data['account_ids'] else 'mock_account'

        # Generate mock transactions
        mock_transactions = [
            {
                'transactionTimestamp': '2025-10-15T10:30:00Z',
                'narration': 'UPI/Swiggy Ltd/swiggyupi@axb/Payment',
                'type': 'DEBIT',
                'amount': '1250.00',
                'currentBalance': '45230.50'
            },
            {
                'transactionTimestamp': '2025-10-14T14:20:00Z',
                'narration': 'Salary Credit from ABC Corp',
                'type': 'CREDIT',
                'amount': '75000.00',
                'currentBalance': '46480.50'
            },
            {
                'transactionTimestamp': '2025-10-13T09:15:00Z',
                'narration': 'NEFT/Rent Payment/Transfer',
                'type': 'DEBIT',
                'amount': '25000.00',
                'currentBalance': '21480.50'
            },
        ]

        return {
            'account_id': account_id,
            'account_type': 'savings',
            'bank_name': 'Mock Bank',
            'transactions': mock_transactions,
            'fetched_at': datetime.now().isoformat(),
            'is_stub_data': True
        }

    def _load_config(self, config_path: str) -> Dict:
        """Load AA configuration"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except:
            # Default stub config
            return {
                'mode': 'stub',
                'fiu_id': 'mock-fiu',
                'api_base_url': 'https://api.sahamati.org.in',  # Example
                'timeout': 30
            }


# Usage Example
if __name__ == "__main__":
    aa_client = AAClientStub()

    # Step 1: Request consent
    consent_result = aa_client.request_consent(
        user_id='user123',
        account_ids=['acc_001'],
        date_range={'from': '2025-01-01', 'to': '2025-10-31'}
    )

    print(f"Consent: {consent_result}")

    # Step 2: Fetch data
    aa_data = aa_client.fetch_account_data(consent_result['consent_id'])
    print(f"Fetched data: {json.dumps(aa_data, indent=2)}")

    # Step 3: Parse transactions
    transactions = aa_client.parse_aa_transactions(aa_data)
    print(f"Parsed transactions: {len(transactions)}")
    for txn in transactions:
        print(txn)
```

### 7.2 AA Configuration (`aa/config.json`)

```json
{
  "mode": "stub",
  "fiu_id": "your-fiu-id",
  "fiu_name": "Your Finance App",
  "api_base_url": "https://api.sahamati.org.in",
  "api_version": "v1",
  "timeout": 30,
  "consent_duration_days": 90,
  "data_fetch_frequency": "daily",
  "supported_fips": [
    "AXIS",
    "HDFC",
    "ICICI",
    "SBI",
    "KOTAK"
  ],
  "stub_settings": {
    "auto_grant_consent": true,
    "mock_transaction_count": 50,
    "mock_date_range_days": 90
  }
}
```

### 7.3 Integration Interface (`aa/interface.py`)

```python
"""
Account Aggregator Integration Interface

Provides abstract interface for AA implementations.
Supports both stub and production AA clients.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List

class AAClientInterface(ABC):
    """Abstract interface for AA clients"""

    @abstractmethod
    def request_consent(self, user_id: str, account_ids: List[str],
                       date_range: Dict[str, str]) -> Dict[str, Any]:
        """Request user consent"""
        pass

    @abstractmethod
    def fetch_account_data(self, consent_id: str) -> Dict[str, Any]:
        """Fetch account data"""
        pass

    @abstractmethod
    def parse_aa_transactions(self, aa_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse AA data to standard format"""
        pass


class AAClientFactory:
    """Factory to create appropriate AA client"""

    @staticmethod
    def create(mode: str = 'stub', config: Dict = None):
        """
        Create AA client based on mode

        Args:
            mode: 'stub' or 'production'
            config: Configuration dict

        Returns:
            AAClientInterface implementation
        """
        if mode == 'stub':
            from aa.aa_client_stub import AAClientStub
            return AAClientStub()
        elif mode == 'production':
            # Import production AA client when implemented
            # from aa.aa_client_production import AAClientProduction
            # return AAClientProduction(config)
            raise NotImplementedError("Production AA client not yet implemented")
        else:
            raise ValueError(f"Unknown AA mode: {mode}")


# Usage
if __name__ == "__main__":
    # Create stub client
    aa_client = AAClientFactory.create(mode='stub')

    # Use via interface
    result = aa_client.request_consent(
        user_id='user123',
        account_ids=['acc_001'],
        date_range={'from': '2025-01-01', 'to': '2025-10-31'}
    )

    print(result)
```

---

---

## 9. Machine Learning Pipeline

### 8.1 ML Categorizer (`ml/categorizer.py`)

```python
"""
ML-based Transaction Categorizer

Pipeline:
1. Prepare: Feature engineering from transaction descriptions
2. Train: Train classifier on labeled data
3. Infer: Predict categories for new transactions
4. Evaluate: Measure performance metrics

Features:
- TF-IDF vectorization of transaction descriptions
- RandomForest or XGBoost classifier
- Multi-class classification (20+ categories)
- Confidence scores for predictions
- Incremental learning support
"""

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib
import logging
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class MLCategorizer:
    """ML-based transaction categorizer"""

    def __init__(self, model_path: str = "ml/models/categorizer.pkl"):
        self.model_path = Path(model_path)
        self.model_path.parent.mkdir(parents=True, exist_ok=True)

        self.vectorizer = None
        self.classifier = None
        self.categories = []
        self.is_trained = False

        # Try to load existing model
        self._load_model()

    def prepare_features(self, transactions: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare features from transactions for training

        Args:
            transactions: List of transaction dicts with 'description' and 'category'

        Returns:
            Tuple of (features, labels)
        """
        # Extract descriptions and categories
        descriptions = [txn.get('clean_description', txn.get('description', ''))
                       for txn in transactions]
        categories = [txn.get('category', 'Uncategorized') for txn in transactions]

        # Remove uncategorized for training
        valid_indices = [i for i, cat in enumerate(categories) if cat != 'Uncategorized']
        descriptions = [descriptions[i] for i in valid_indices]
        categories = [categories[i] for i in valid_indices]

        if not descriptions:
            raise ValueError("No valid transactions for training")

        # Initialize or fit vectorizer
        if self.vectorizer is None:
            self.vectorizer = TfidfVectorizer(
                max_features=1000,
                ngram_range=(1, 2),
                min_df=2,
                stop_words='english'
            )
            features = self.vectorizer.fit_transform(descriptions)
        else:
            features = self.vectorizer.transform(descriptions)

        # Store unique categories
        self.categories = sorted(list(set(categories)))

        return features.toarray(), np.array(categories)

    def train(self, training_data: List[Dict], test_size: float = 0.2) -> Dict[str, Any]:
        """
        Train the ML model

        Args:
            training_data: List of labeled transactions
            test_size: Fraction of data for testing

        Returns:
            Dict with training metrics
        """
        logger.info(f"Training model on {len(training_data)} transactions")

        # Prepare features
        X, y = self.prepare_features(training_data)

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )

        # Train classifier
        self.classifier = RandomForestClassifier(
            n_estimators=100,
            max_depth=20,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1
        )

        self.classifier.fit(X_train, y_train)
        self.is_trained = True

        # Evaluate
        y_pred = self.classifier.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)

        logger.info(f"Model trained with accuracy: {accuracy:.3f}")

        # Save model
        self._save_model()

        return {
            'accuracy': accuracy,
            'n_training_samples': len(X_train),
            'n_test_samples': len(X_test),
            'categories': self.categories
        }

    def predict(self, transaction: Dict) -> Dict[str, Any]:
        """
        Predict category for a single transaction

        Args:
            transaction: Transaction dict with description

        Returns:
            Dict with category, confidence, and probabilities
        """
        if not self.is_trained:
            return {
                'category': 'Uncategorized',
                'confidence': 0.0,
                'probabilities': {}
            }

        # Extract description
        description = transaction.get('clean_description', transaction.get('description', ''))

        if not description:
            return {
                'category': 'Uncategorized',
                'confidence': 0.0,
                'probabilities': {}
            }

        # Vectorize
        features = self.vectorizer.transform([description]).toarray()

        # Predict
        prediction = self.classifier.predict(features)[0]
        probabilities = self.classifier.predict_proba(features)[0]

        # Get confidence (max probability)
        confidence = float(probabilities.max())

        # Get top 3 predictions
        top_3_indices = probabilities.argsort()[-3:][::-1]
        top_3_probs = {
            self.classifier.classes_[i]: float(probabilities[i])
            for i in top_3_indices
        }

        return {
            'category': prediction,
            'confidence': confidence,
            'probabilities': top_3_probs
        }

    def predict_batch(self, transactions: List[Dict]) -> List[Dict[str, Any]]:
        """Predict categories for multiple transactions"""
        return [self.predict(txn) for txn in transactions]

    def evaluate(self, test_data: List[Dict]) -> Dict[str, Any]:
        """
        Evaluate model on test data

        Args:
            test_data: List of labeled transactions

        Returns:
            Dict with evaluation metrics
        """
        if not self.is_trained:
            raise ValueError("Model not trained")

        # Prepare features
        X_test, y_test = self.prepare_features(test_data)

        # Predict
        y_pred = self.classifier.predict(X_test)
        y_proba = self.classifier.predict_proba(X_test)

        # Calculate metrics
        accuracy = accuracy_score(y_test, y_pred)
        conf_matrix = confusion_matrix(y_test, y_pred, labels=self.categories)
        class_report = classification_report(y_test, y_pred, output_dict=True)

        # Calculate average confidence
        confidences = [proba.max() for proba in y_proba]
        avg_confidence = np.mean(confidences)

        return {
            'accuracy': accuracy,
            'avg_confidence': avg_confidence,
            'confusion_matrix': conf_matrix.tolist(),
            'classification_report': class_report,
            'n_test_samples': len(X_test)
        }

    def _save_model(self):
        """Save model to disk"""
        try:
            model_data = {
                'vectorizer': self.vectorizer,
                'classifier': self.classifier,
                'categories': self.categories,
                'is_trained': self.is_trained
            }

            joblib.dump(model_data, self.model_path)
            logger.info(f"Model saved to {self.model_path}")

        except Exception as e:
            logger.error(f"Failed to save model: {e}")

    def _load_model(self):
        """Load model from disk"""
        if not self.model_path.exists():
            logger.info("No existing model found")
            return

        try:
            model_data = joblib.load(self.model_path)

            self.vectorizer = model_data['vectorizer']
            self.classifier = model_data['classifier']
            self.categories = model_data['categories']
            self.is_trained = model_data['is_trained']

            logger.info(f"Model loaded from {self.model_path}")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")


# Usage Example
if __name__ == "__main__":
    categorizer = MLCategorizer()

    # Sample training data
    training_data = [
        {'description': 'UPI Swiggy Ltd payment', 'category': 'Food'},
        {'description': 'Netflix subscription charge', 'category': 'Subscriptions'},
        {'description': 'Amazon shopping purchase', 'category': 'Shopping'},
        # ... more labeled data
    ]

    # Train
    metrics = categorizer.train(training_data)
    print(f"Training metrics: {metrics}")

    # Predict
    test_txn = {'description': 'UPI Zomato order payment'}
    prediction = categorizer.predict(test_txn)
    print(f"Prediction: {prediction}")
```

### 8.2 Training Data Preparation (`ml/prepare_training_data.py`)

```python
"""
Prepare training data from labeled transactions

Sources:
1. Manually labeled transactions (JSONL file)
2. Transactions with mapping-based categories (high confidence)
3. User corrections (feedback loop)
"""

import json
import logging
from typing import List, Dict, Any
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)

class TrainingDataPreparer:
    """Prepare and manage training data"""

    def __init__(self, data_dir: str = "ml/training_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.labeled_file = self.data_dir / "labeled_transactions.jsonl"
        self.auto_labeled_file = self.data_dir / "auto_labeled.jsonl"

    def load_labeled_data(self) -> List[Dict]:
        """Load manually labeled transactions"""
        if not self.labeled_file.exists():
            return []

        transactions = []
        with open(self.labeled_file, 'r') as f:
            for line in f:
                if line.strip():
                    transactions.append(json.loads(line))

        logger.info(f"Loaded {len(transactions)} labeled transactions")
        return transactions

    def add_labeled_transaction(self, transaction: Dict):
        """Add a manually labeled transaction"""
        with open(self.labeled_file, 'a') as f:
            f.write(json.dumps(transaction) + '\n')

    def extract_auto_labeled(self, transactions: List[Dict],
                            min_confidence: float = 0.95) -> List[Dict]:
        """
        Extract transactions with high-confidence categories from mapping

        Args:
            transactions: List of canonical transactions
            min_confidence: Minimum confidence threshold

        Returns:
            List of transactions suitable for training
        """
        auto_labeled = []

        for txn in transactions:
            # Only use mapping-based categories with high confidence
            if (txn.get('category_source') == 'mapping' and
                txn.get('category_confidence', 0) >= min_confidence and
                txn.get('category') != 'Uncategorized'):

                training_sample = {
                    'description': txn.get('clean_description'),
                    'category': txn.get('category'),
                    'confidence': txn.get('category_confidence')
                }

                auto_labeled.append(training_sample)

        logger.info(f"Extracted {len(auto_labeled)} auto-labeled transactions")
        return auto_labeled

    def combine_training_data(self, auto_labeled: List[Dict] = None) -> List[Dict]:
        """
        Combine manual and auto-labeled data

        Args:
            auto_labeled: Optional list of auto-labeled transactions

        Returns:
            Combined training dataset
        """
        # Load manual labels (priority)
        manual = self.load_labeled_data()

        # Add auto-labeled if provided
        combined = manual.copy()
        if auto_labeled:
            combined.extend(auto_labeled)

        logger.info(f"Combined training data: {len(combined)} samples")
        return combined

    def get_category_distribution(self, training_data: List[Dict]) -> Dict[str, int]:
        """Get distribution of categories in training data"""
        categories = {}
        for txn in training_data:
            cat = txn.get('category', 'Unknown')
            categories[cat] = categories.get(cat, 0) + 1

        return dict(sorted(categories.items(), key=lambda x: x[1], reverse=True))

    def export_to_csv(self, training_data: List[Dict], output_path: str):
        """Export training data to CSV for review"""
        df = pd.DataFrame(training_data)
        df.to_csv(output_path, index=False)
        logger.info(f"Exported training data to {output_path}")


# Usage Example
if __name__ == "__main__":
    preparer = TrainingDataPreparer()

    # Load existing labeled data
    labeled = preparer.load_labeled_data()
    print(f"Loaded {len(labeled)} labeled transactions")

    # Get distribution
    dist = preparer.get_category_distribution(labeled)
    print("Category distribution:")
    for cat, count in dist.items():
        print(f"  {cat}: {count}")
```

### 8.3 Model Evaluation (`ml/evaluate.py`)

```python
"""
Model Evaluation and Performance Analysis
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, classification_report
import logging
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)

class ModelEvaluator:
    """Evaluate ML model performance"""

    def __init__(self, output_dir: str = "ml/evaluation"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def evaluate_and_report(self, categorizer, test_data: List[Dict]) -> Dict[str, Any]:
        """
        Run full evaluation and generate report

        Args:
            categorizer: Trained MLCategorizer instance
            test_data: List of labeled test transactions

        Returns:
            Dict with evaluation metrics
        """
        logger.info(f"Evaluating model on {len(test_data)} test samples")

        # Get evaluation metrics
        metrics = categorizer.evaluate(test_data)

        # Generate visualizations
        self._plot_confusion_matrix(
            metrics['confusion_matrix'],
            categorizer.categories,
            save_path=self.output_dir / "confusion_matrix.png"
        )

        self._plot_category_performance(
            metrics['classification_report'],
            save_path=self.output_dir / "category_performance.png"
        )

        # Save detailed report
        self._save_text_report(metrics, save_path=self.output_dir / "evaluation_report.txt")

        logger.info(f"Evaluation complete. Accuracy: {metrics['accuracy']:.3f}")

        return metrics

    def _plot_confusion_matrix(self, conf_matrix: np.ndarray, categories: List[str],
                               save_path: Path):
        """Plot confusion matrix heatmap"""
        plt.figure(figsize=(12, 10))

        sns.heatmap(
            conf_matrix,
            annot=True,
            fmt='d',
            cmap='Blues',
            xticklabels=categories,
            yticklabels=categories,
            cbar_kws={'label': 'Count'}
        )

        plt.title('Confusion Matrix')
        plt.xlabel('Predicted Category')
        plt.ylabel('True Category')
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)
        plt.tight_layout()

        plt.savefig(save_path, dpi=150)
        plt.close()

        logger.info(f"Confusion matrix saved to {save_path}")

    def _plot_category_performance(self, class_report: Dict, save_path: Path):
        """Plot per-category precision, recall, f1-score"""
        # Extract metrics for each category
        categories = [k for k in class_report.keys()
                     if k not in ['accuracy', 'macro avg', 'weighted avg']]

        precision = [class_report[cat]['precision'] for cat in categories]
        recall = [class_report[cat]['recall'] for cat in categories]
        f1 = [class_report[cat]['f1-score'] for cat in categories]

        # Create DataFrame
        df = pd.DataFrame({
            'Category': categories,
            'Precision': precision,
            'Recall': recall,
            'F1-Score': f1
        })

        # Sort by F1-score
        df = df.sort_values('F1-Score', ascending=True)

        # Plot
        fig, ax = plt.subplots(figsize=(10, max(6, len(categories) * 0.3)))

        x = np.arange(len(df))
        width = 0.25

        ax.barh(x - width, df['Precision'], width, label='Precision', alpha=0.8)
        ax.barh(x, df['Recall'], width, label='Recall', alpha=0.8)
        ax.barh(x + width, df['F1-Score'], width, label='F1-Score', alpha=0.8)

        ax.set_xlabel('Score')
        ax.set_title('Per-Category Performance Metrics')
        ax.set_yticks(x)
        ax.set_yticklabels(df['Category'])
        ax.legend()
        ax.grid(axis='x', alpha=0.3)

        plt.tight_layout()
        plt.savefig(save_path, dpi=150)
        plt.close()

        logger.info(f"Category performance plot saved to {save_path}")

    def _save_text_report(self, metrics: Dict, save_path: Path):
        """Save detailed text report"""
        with open(save_path, 'w') as f:
            f.write("=" * 60 + "\n")
            f.write("ML CATEGORIZER EVALUATION REPORT\n")
            f.write("=" * 60 + "\n\n")

            f.write(f"Overall Accuracy: {metrics['accuracy']:.4f}\n")
            f.write(f"Average Confidence: {metrics['avg_confidence']:.4f}\n")
            f.write(f"Test Samples: {metrics['n_test_samples']}\n\n")

            f.write("=" * 60 + "\n")
            f.write("CLASSIFICATION REPORT\n")
            f.write("=" * 60 + "\n\n")

            # Format classification report
            report = metrics['classification_report']
            for category, metrics_dict in report.items():
                if isinstance(metrics_dict, dict):
                    f.write(f"{category}:\n")
                    f.write(f"  Precision: {metrics_dict.get('precision', 0):.4f}\n")
                    f.write(f"  Recall:    {metrics_dict.get('recall', 0):.4f}\n")
                    f.write(f"  F1-Score:  {metrics_dict.get('f1-score', 0):.4f}\n")
                    f.write(f"  Support:   {metrics_dict.get('support', 0)}\n\n")

        logger.info(f"Text report saved to {save_path}")


# Usage Example
if __name__ == "__main__":
    from ml.categorizer import MLCategorizer
    from ml.prepare_training_data import TrainingDataPreparer

    # Load test data
    preparer = TrainingDataPreparer()
    test_data = preparer.load_labeled_data()

    # Load trained model
    categorizer = MLCategorizer()

    # Evaluate
    evaluator = ModelEvaluator()
    metrics = evaluator.evaluate_and_report(categorizer, test_data)
```

---

## 10. Storage Layer (SQLite + SQLAlchemy)

### 9.1 Database Models (`storage/models.py`)

```python
"""
SQLAlchemy Database Models

Tables:
- transactions: Main transaction records
- pii_vault: Encrypted PII storage
- metadata: Statement metadata
- user_corrections: User feedback for ML training
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


class Transaction(Base):
    """Transaction model"""
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(64), unique=True, nullable=False, index=True)

    # Core fields
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    transaction_type = Column(String(20), nullable=False)  # debit/credit/transfer
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default='INR')

    # Descriptions
    raw_description = Column(Text, nullable=False)
    clean_description = Column(Text)

    # Merchant
    merchant_raw = Column(String(255))
    merchant_canonical = Column(String(255), index=True)

    # Category
    category = Column(String(50), nullable=False, index=True)
    category_source = Column(String(20))  # mapping/ml/rule/manual
    category_confidence = Column(Float)
    subcategory = Column(String(50))

    # Channel
    channel = Column(String(20), index=True)
    transaction_mode = Column(String(20))

    # Account references
    account_ref = Column(String(64))
    account_number_masked = Column(String(20))
    counterparty_ref = Column(String(64))
    counterparty_name = Column(String(255))

    # Financial
    balance_after = Column(Float)
    fees = Column(Float, default=0.0)
    tax = Column(Float, default=0.0)

    # Metadata
    source = Column(String(20))  # pdf/csv/aa/manual
    source_file = Column(String(255))
    statement_date = Column(String(10))

    # Flags
    is_recurring = Column(Boolean, default=False)
    is_duplicate = Column(Boolean, default=False)
    is_flagged = Column(Boolean, default=False)
    flag_reason = Column(String(255))

    # UPI specific
    upi_id = Column(String(100))
    upi_ref_id = Column(String(50))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Custom fields (JSON)
    custom_fields = Column(JSON)

    def __repr__(self):
        return f"<Transaction(id={self.id}, date={self.date}, amount={self.amount}, category={self.category})>"


class PIIVault(Base):
    """PII encrypted storage"""
    __tablename__ = 'pii_vault'

    id = Column(Integer, primary_key=True, autoincrement=True)
    pii_ref = Column(String(64), unique=True, nullable=False, index=True)

    # Encrypted data (base64 encoded)
    nonce = Column(Text, nullable=False)
    ciphertext = Column(Text, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    accessed_at = Column(DateTime)

    def __repr__(self):
        return f"<PIIVault(ref={self.pii_ref})>"


class StatementMetadata(Base):
    """Statement file metadata"""
    __tablename__ = 'statement_metadata'

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512))
    file_hash = Column(String(64), unique=True)  # SHA256 for deduplication

    # Statement info
    statement_date = Column(String(10))
    account_ref = Column(String(64))
    bank_name = Column(String(100))
    source_type = Column(String(20))  # pdf/csv/aa

    # Processing info
    transaction_count = Column(Integer, default=0)
    processed_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default='processed')  # processed/error/duplicate

    def __repr__(self):
        return f"<StatementMetadata(file={self.file_name}, date={self.statement_date})>"


class UserCorrection(Base):
    """User corrections for ML training"""
    __tablename__ = 'user_corrections'

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(64), nullable=False, index=True)

    # Original prediction
    original_category = Column(String(50))
    original_confidence = Column(Float)

    # User correction
    corrected_category = Column(String(50), nullable=False)
    correction_reason = Column(String(255))

    # Timestamp
    corrected_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<UserCorrection(txn={self.transaction_id}, {self.original_category} -> {self.corrected_category})>"


class DatabaseManager:
    """Database connection and session management"""

    def __init__(self, db_path: str = "data/finance.db"):
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create tables
        Base.metadata.create_all(self.engine)
        logger.info(f"Database initialized: {db_path}")

    def get_session(self):
        """Get a new database session"""
        return self.SessionLocal()

    def close(self):
        """Close database connection"""
        self.engine.dispose()


# Usage Example
if __name__ == "__main__":
    # Initialize database
    db = DatabaseManager("data/test.db")

    # Create session
    session = db.get_session()

    # Create a transaction
    txn = Transaction(
        transaction_id="test_001",
        date="2025-10-26",
        transaction_type="debit",
        amount=1250.00,
        raw_description="UPI Swiggy payment",
        clean_description="UPI Swiggy payment",
        merchant_canonical="Swiggy",
        category="Food",
        category_source="mapping",
        category_confidence=0.95,
        channel="upi",
        source="csv"
    )

    session.add(txn)
    session.commit()

    # Query
    result = session.query(Transaction).filter_by(category="Food").first()
    print(result)

    session.close()
```

### 9.2 Repository Layer (`storage/repository.py`)

```python
"""
Repository layer for database operations

Provides high-level CRUD operations and queries
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from sqlalchemy import func, and_, or_
from storage.models import Transaction, PIIVault, StatementMetadata, UserCorrection, DatabaseManager

logger = logging.getLogger(__name__)


class TransactionRepository:
    """Repository for transaction operations"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def create(self, transaction_data: Dict[str, Any]) -> Transaction:
        """Create a new transaction"""
        session = self.db.get_session()
        try:
            txn = Transaction(**transaction_data)
            session.add(txn)
            session.commit()
            session.refresh(txn)
            return txn
        finally:
            session.close()

    def create_batch(self, transactions_data: List[Dict[str, Any]]) -> int:
        """Create multiple transactions"""
        session = self.db.get_session()
        try:
            transactions = [Transaction(**data) for data in transactions_data]
            session.bulk_save_objects(transactions)
            session.commit()
            return len(transactions)
        finally:
            session.close()

    def get_by_id(self, transaction_id: str) -> Optional[Transaction]:
        """Get transaction by ID"""
        session = self.db.get_session()
        try:
            return session.query(Transaction).filter_by(transaction_id=transaction_id).first()
        finally:
            session.close()

    def get_all(self, limit: int = 1000, offset: int = 0) -> List[Transaction]:
        """Get all transactions with pagination"""
        session = self.db.get_session()
        try:
            return session.query(Transaction).limit(limit).offset(offset).all()
        finally:
            session.close()

    def filter_by_date_range(self, start_date: str, end_date: str) -> List[Transaction]:
        """Get transactions in date range"""
        session = self.db.get_session()
        try:
            return session.query(Transaction).filter(
                and_(
                    Transaction.date >= start_date,
                    Transaction.date <= end_date
                )
            ).order_by(Transaction.date.desc()).all()
        finally:
            session.close()

    def filter_by_category(self, category: str) -> List[Transaction]:
        """Get transactions by category"""
        session = self.db.get_session()
        try:
            return session.query(Transaction).filter_by(category=category).all()
        finally:
            session.close()

    def filter_by_merchant(self, merchant: str) -> List[Transaction]:
        """Get transactions by merchant"""
        session = self.db.get_session()
        try:
            return session.query(Transaction).filter_by(merchant_canonical=merchant).all()
        finally:
            session.close()

    def get_spending_by_category(self, start_date: str = None, end_date: str = None) -> Dict[str, float]:
        """Get total spending by category"""
        session = self.db.get_session()
        try:
            query = session.query(
                Transaction.category,
                func.sum(Transaction.amount).label('total')
            ).filter(Transaction.transaction_type == 'debit')

            if start_date and end_date:
                query = query.filter(
                    and_(
                        Transaction.date >= start_date,
                        Transaction.date <= end_date
                    )
                )

            results = query.group_by(Transaction.category).all()

            return {cat: float(total) for cat, total in results}

        finally:
            session.close()

    def get_top_merchants(self, limit: int = 10, start_date: str = None, end_date: str = None) -> List[Dict]:
        """Get top merchants by spending"""
        session = self.db.get_session()
        try:
            query = session.query(
                Transaction.merchant_canonical,
                func.sum(Transaction.amount).label('total'),
                func.count(Transaction.id).label('count')
            ).filter(
                and_(
                    Transaction.transaction_type == 'debit',
                    Transaction.merchant_canonical.isnot(None)
                )
            )

            if start_date and end_date:
                query = query.filter(
                    and_(
                        Transaction.date >= start_date,
                        Transaction.date <= end_date
                    )
                )

            results = query.group_by(Transaction.merchant_canonical).order_by(
                func.sum(Transaction.amount).desc()
            ).limit(limit).all()

            return [
                {'merchant': merchant, 'total': float(total), 'count': count}
                for merchant, total, count in results
            ]

        finally:
            session.close()

    def mark_duplicate(self, transaction_id: str, is_duplicate: bool = True):
        """Mark transaction as duplicate"""
        session = self.db.get_session()
        try:
            txn = session.query(Transaction).filter_by(transaction_id=transaction_id).first()
            if txn:
                txn.is_duplicate = is_duplicate
                session.commit()
        finally:
            session.close()

    def update_category(self, transaction_id: str, category: str, source: str = 'manual', confidence: float = 1.0):
        """Update transaction category"""
        session = self.db.get_session()
        try:
            txn = session.query(Transaction).filter_by(transaction_id=transaction_id).first()
            if txn:
                txn.category = category
                txn.category_source = source
                txn.category_confidence = confidence
                txn.updated_at = datetime.utcnow()
                session.commit()
        finally:
            session.close()


# Usage Example
if __name__ == "__main__":
    db = DatabaseManager("data/test.db")
    repo = TransactionRepository(db)

    # Get spending by category
    spending = repo.get_spending_by_category(start_date='2025-01-01', end_date='2025-12-31')
    print("Spending by category:")
    for cat, amount in spending.items():
        print(f"  {cat}: ₹{amount:,.2f}")

    # Get top merchants
    top_merchants = repo.get_top_merchants(limit=5)
    print("\nTop merchants:")
    for m in top_merchants:
        print(f"  {m['merchant']}: ₹{m['total']:,.2f} ({m['count']} transactions)")
```

---

## 11. CLI Interface (Click)

### 10.1 Main CLI (`cli/main.py`)

```python
"""
CLI Interface using Click

Commands:
- ingest: Ingest statement files (PDF/CSV)
- train: Train ML model
- predict: Predict categories for uncategorized transactions
- query: Query transactions
- dashboard: Launch dashboard
"""

import click
import logging
from pathlib import Path
from typing import List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """Personal Finance App - Transaction Analysis & Categorization"""
    pass


@cli.command()
@click.argument('files', nargs=-1, type=click.Path(exists=True), required=True)
@click.option('--output', '-o', type=click.Path(), default='data/transactions.jsonl',
              help='Output file for canonical transactions')
@click.option('--no-ml', is_flag=True, help='Disable ML categorization')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def ingest(files: tuple, output: str, no_ml: bool, verbose: bool):
    """
    Ingest statement files (PDF/CSV) and process transactions

    Example:
        finance-app ingest statement.pdf transactions.csv
        finance-app ingest data/*.csv --output processed.jsonl
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    click.echo(f"Ingesting {len(files)} file(s)...")

    # Import modules
    from ingest.pdf_parser import PDFParser
    from ingest.csv_parser import CSVParser
    from ingest.normalizer import TransactionNormalizer
    from mapping.merchant_mapper import MerchantMapper
    from ml.categorizer import MLCategorizer
    from storage.models import DatabaseManager
    from storage.repository import TransactionRepository

    # Initialize components
    pdf_parser = PDFParser()
    csv_parser = CSVParser()
    normalizer = TransactionNormalizer()
    merchant_mapper = MerchantMapper()

    if not no_ml:
        ml_categorizer = MLCategorizer()

    db = DatabaseManager()
    repo = TransactionRepository(db)

    all_transactions = []

    for file_path in files:
        file_path = Path(file_path)
        click.echo(f"\nProcessing: {file_path.name}")

        # Parse based on file type
        if file_path.suffix.lower() == '.pdf':
            raw_transactions = pdf_parser.parse(str(file_path))
        elif file_path.suffix.lower() == '.csv':
            raw_transactions = csv_parser.parse(str(file_path))
        else:
            click.echo(f"  Skipping unsupported file type: {file_path.suffix}", err=True)
            continue

        click.echo(f"  Parsed: {len(raw_transactions)} transactions")

        # Normalize
        for raw_txn in raw_transactions:
            canonical_txn = normalizer.normalize(raw_txn)

            # Map merchant
            mapping_result = merchant_mapper.map_merchant(canonical_txn.merchant_raw)
            canonical_txn.merchant_canonical = mapping_result['merchant_canonical']

            # Categorize
            if mapping_result['confidence'] >= 0.8:
                canonical_txn.category = mapping_result['category']
                canonical_txn.category_source = 'mapping'
                canonical_txn.category_confidence = mapping_result['confidence']
            elif not no_ml and ml_categorizer.is_trained:
                ml_result = ml_categorizer.predict(canonical_txn.to_dict())
                canonical_txn.category = ml_result['category']
                canonical_txn.category_source = 'ml'
                canonical_txn.category_confidence = ml_result['confidence']

            all_transactions.append(canonical_txn)

    # Save to database
    if all_transactions:
        click.echo(f"\nSaving {len(all_transactions)} transactions to database...")
        transaction_dicts = [txn.to_dict() for txn in all_transactions]
        count = repo.create_batch(transaction_dicts)
        click.echo(f"  Saved: {count} transactions")

        # Export to JSONL
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            for txn in all_transactions:
                f.write(txn.to_json_line() + '\n')
        click.echo(f"  Exported to: {output_path}")

    click.echo("\n✓ Ingestion complete!")


@cli.command()
@click.option('--training-data', '-t', type=click.Path(exists=True), required=True,
              help='Path to labeled training data (JSONL)')
@click.option('--test-size', type=float, default=0.2, help='Test set fraction')
@click.option('--evaluate', is_flag=True, help='Run evaluation after training')
def train(training_data: str, test_size: float, evaluate: bool):
    """
    Train ML categorization model

    Example:
        finance-app train --training-data labeled.jsonl --evaluate
    """
    import json
    from ml.categorizer import MLCategorizer
    from ml.evaluate import ModelEvaluator

    click.echo("Loading training data...")

    # Load JSONL
    transactions = []
    with open(training_data, 'r') as f:
        for line in f:
            if line.strip():
                transactions.append(json.loads(line))

    click.echo(f"  Loaded: {len(transactions)} labeled transactions")

    # Train
    click.echo("\nTraining model...")
    categorizer = MLCategorizer()
    metrics = categorizer.train(transactions, test_size=test_size)

    click.echo(f"\n✓ Training complete!")
    click.echo(f"  Accuracy: {metrics['accuracy']:.3f}")
    click.echo(f"  Categories: {len(metrics['categories'])}")

    # Evaluate
    if evaluate:
        click.echo("\nRunning evaluation...")
        evaluator = ModelEvaluator()
        eval_metrics = evaluator.evaluate_and_report(categorizer, transactions[:100])
        click.echo(f"  Evaluation accuracy: {eval_metrics['accuracy']:.3f}")
        click.echo(f"  Reports saved to: ml/evaluation/")


@cli.command()
@click.option('--date-from', type=str, help='Start date (YYYY-MM-DD)')
@click.option('--date-to', type=str, help='End date (YYYY-MM-DD)')
@click.option('--category', type=str, help='Filter by category')
@click.option('--merchant', type=str, help='Filter by merchant')
@click.option('--limit', type=int, default=20, help='Number of results')
def query(date_from: str, date_to: str, category: str, merchant: str, limit: int):
    """
    Query transactions

    Example:
        finance-app query --category Food --limit 10
        finance-app query --date-from 2025-01-01 --date-to 2025-12-31
    """
    from storage.models import DatabaseManager
    from storage.repository import TransactionRepository

    db = DatabaseManager()
    repo = TransactionRepository(db)

    # Build query
    if date_from and date_to:
        transactions = repo.filter_by_date_range(date_from, date_to)
    elif category:
        transactions = repo.filter_by_category(category)
    elif merchant:
        transactions = repo.filter_by_merchant(merchant)
    else:
        transactions = repo.get_all(limit=limit)

    # Display results
    click.echo(f"\nFound {len(transactions)} transaction(s):\n")

    for txn in transactions[:limit]:
        click.echo(f"{txn.date} | ₹{txn.amount:>10,.2f} | {txn.category:<15} | {txn.merchant_canonical or 'N/A'}")
        if txn.clean_description:
            click.echo(f"         {txn.clean_description[:80]}")
        click.echo()


@cli.command()
@click.option('--date-from', type=str, help='Start date (YYYY-MM-DD)')
@click.option('--date-to', type=str, help='End date (YYYY-MM-DD)')
def summary(date_from: str, date_to: str):
    """
    Show spending summary

    Example:
        finance-app summary --date-from 2025-01-01 --date-to 2025-12-31
    """
    from storage.models import DatabaseManager
    from storage.repository import TransactionRepository

    db = DatabaseManager()
    repo = TransactionRepository(db)

    # Get spending by category
    spending = repo.get_spending_by_category(start_date=date_from, end_date=date_to)
    total_spending = sum(spending.values())

    click.echo("\n" + "="*60)
    click.echo("SPENDING SUMMARY")
    click.echo("="*60)

    if date_from and date_to:
        click.echo(f"Period: {date_from} to {date_to}\n")

    click.echo(f"{'Category':<20} {'Amount':>15} {'%':>8}")
    click.echo("-"*60)

    for category in sorted(spending, key=spending.get, reverse=True):
        amount = spending[category]
        percentage = (amount / total_spending * 100) if total_spending > 0 else 0
        click.echo(f"{category:<20} ₹{amount:>13,.2f} {percentage:>7.1f}%")

    click.echo("-"*60)
    click.echo(f"{'TOTAL':<20} ₹{total_spending:>13,.2f}")
    click.echo("="*60 + "\n")

    # Top merchants
    top_merchants = repo.get_top_merchants(limit=10, start_date=date_from, end_date=date_to)

    click.echo("TOP MERCHANTS")
    click.echo("-"*60)

    for merchant_data in top_merchants:
        merchant = merchant_data['merchant']
        amount = merchant_data['total']
        count = merchant_data['count']
        click.echo(f"{merchant:<30} ₹{amount:>10,.2f} ({count} txns)")

    click.echo()


@cli.command()
@click.option('--port', type=int, default=8501, help='Dashboard port')
def dashboard(port: int):
    """
    Launch Streamlit dashboard

    Example:
        finance-app dashboard --port 8501
    """
    import subprocess

    click.echo(f"Launching dashboard on port {port}...")
    subprocess.run(['streamlit', 'run', 'dashboard.py', '--server.port', str(port)])


@cli.command('rotate-key')
@click.option('--backup/--no-backup', default=True, help='Create backup before rotation')
@click.confirmation_option(prompt='Are you sure you want to rotate the vault key?')
def rotate_key(backup: bool):
    """
    Rotate vault encryption key

    WARNING: This will re-encrypt all PII data.
    Make sure you have a backup before proceeding!

    Example:
        finance-app rotate-key
        finance-app rotate-key --no-backup  # Skip backup (not recommended)
    """
    from privacy.vault import PrivacyVault

    click.echo("Starting vault key rotation...")
    click.echo("This may take a while for large vaults...")

    vault = PrivacyVault()

    if backup:
        click.echo("Creating backup...")

    success = vault.rotate_key()

    if success:
        click.echo("\n✓ Key rotation successful!")
        click.echo(f"✓ New key version: {vault.key_version}")
        click.echo(f"✓ Key saved to: {vault.key_file}")
        click.echo("\n⚠️  IMPORTANT: Backup your new key securely!")
    else:
        click.echo("\n✗ Key rotation failed!", err=True)
        click.echo("Check logs for details", err=True)


@cli.command('vault-info')
def vault_info():
    """
    Show vault information and statistics

    Example:
        finance-app vault-info
    """
    from privacy.vault import PrivacyVault
    import os

    vault = PrivacyVault()

    click.echo("\n" + "="*60)
    click.echo("VAULT INFORMATION")
    click.echo("="*60)

    click.echo(f"\nVault File: {vault.vault_path}")
    click.echo(f"Key File: {vault.key_file}")
    click.echo(f"Key Version: {vault.key_version}")

    # Check key file permissions
    if vault.key_file.exists():
        file_stat = vault.key_file.stat()
        perms = oct(file_stat.st_mode & 0o777)
        is_secure = (file_stat.st_mode & 0o777) == 0o600

        click.echo(f"\nKey File Permissions: {perms}")
        if is_secure:
            click.echo("✓ Key file permissions are secure (600)")
        else:
            click.echo("⚠️  WARNING: Key file has insecure permissions!")
            click.echo(f"   Run: chmod 600 {vault.key_file}")

    # Vault statistics
    pii_count = len(vault.vault)
    click.echo(f"\nPII Entries: {pii_count}")

    if vault.vault_path.exists():
        vault_size = vault.vault_path.stat().st_size
        click.echo(f"Vault Size: {vault_size:,} bytes")

    click.echo()


if __name__ == '__main__':
    cli()
```

---

## 12. Testing Strategy

### 11.1 Test Structure (`tests/`)

```
tests/
├── __init__.py
├── conftest.py                 # Pytest fixtures
├── test_ingest/
│   ├── test_pdf_parser.py
│   ├── test_csv_parser.py
│   └── test_normalizer.py
├── test_mapping/
│   └── test_merchant_mapper.py
├── test_ml/
│   ├── test_categorizer.py
│   └── test_training_data.py
├── test_storage/
│   ├── test_models.py
│   └── test_repository.py
├── test_privacy/
│   ├── test_vault.py
│   └── test_masking.py
└── test_integration/
    └── test_end_to_end.py
```

### 11.2 Pytest Configuration (`pytest.ini`)

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --tb=short
    --strict-markers
    --cov=.
    --cov-report=term-missing
    --cov-report=html
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow-running tests
```

### 11.3 Sample Test Files

#### Test CSV Parser (`tests/test_ingest/test_csv_parser.py`)

```python
"""
Tests for CSV Parser
"""

import pytest
from pathlib import Path
from ingest.csv_parser import CSVParser

@pytest.fixture
def csv_parser():
    """Fixture for CSV parser"""
    return CSVParser()

@pytest.fixture
def sample_csv_file(tmp_path):
    """Create a sample CSV file for testing"""
    csv_content = """Date,Description,Withdrawal Amount (INR),Deposit Amount (INR),Balance (INR)
15/10/2025,UPI/Swiggy Ltd/payment,1250.00,,45230.50
14/10/2025,Salary Credit,,75000.00,46480.50
13/10/2025,NEFT/Rent Payment,25000.00,,21480.50
"""
    csv_file = tmp_path / "test_statement.csv"
    csv_file.write_text(csv_content)
    return str(csv_file)

def test_parse_csv_basic(csv_parser, sample_csv_file):
    """Test basic CSV parsing"""
    transactions = csv_parser.parse(sample_csv_file)

    assert len(transactions) == 3
    assert transactions[0]['amount'] == 1250.00
    assert transactions[0]['type'] == 'debit'
    assert transactions[1]['type'] == 'credit'

def test_parse_csv_with_invalid_file(csv_parser):
    """Test parsing with non-existent file"""
    transactions = csv_parser.parse("non_existent.csv")
    assert len(transactions) == 0

def test_detect_delimiter(csv_parser, tmp_path):
    """Test delimiter detection"""
    # Semicolon-separated CSV
    csv_content = "Date;Description;Amount\n15/10/2025;Test;1000"
    csv_file = tmp_path / "semicolon.csv"
    csv_file.write_text(csv_content)

    transactions = csv_parser.parse(str(csv_file))
    assert len(transactions) > 0
```

#### Test Merchant Mapper (`tests/test_mapping/test_merchant_mapper.py`)

```python
"""
Tests for Merchant Mapper
"""

import pytest
from mapping.merchant_mapper import MerchantMapper

@pytest.fixture
def merchant_mapper():
    """Fixture for merchant mapper"""
    return MerchantMapper()

def test_exact_match(merchant_mapper):
    """Test exact merchant matching"""
    result = merchant_mapper.map_merchant("Swiggy")

    assert result['merchant_canonical'] == 'Swiggy'
    assert result['category'] == 'Food'
    assert result['confidence'] == 1.0
    assert result['method'] == 'exact'

def test_regex_match(merchant_mapper):
    """Test regex-based matching"""
    result = merchant_mapper.map_merchant("Apollo Pharmacy Store")

    assert result['merchant_canonical'] == 'Apollo Pharmacy'
    assert result['category'] == 'Pharmacy'
    assert result['method'] == 'regex'

def test_fuzzy_match(merchant_mapper):
    """Test fuzzy matching"""
    result = merchant_mapper.map_merchant("Swigy Ltd")  # Typo

    assert result['merchant_canonical'] == 'Swiggy'
    assert result['confidence'] >= 0.85
    assert result['method'] == 'fuzzy'

def test_no_match(merchant_mapper):
    """Test when no match is found"""
    result = merchant_mapper.map_merchant("Unknown Merchant XYZ")

    assert result['category'] == 'Uncategorized'
    assert result['confidence'] == 0.0
```

#### Test Privacy Vault (`tests/test_privacy/test_vault.py`)

```python
"""
Tests for Privacy Vault
"""

import pytest
from privacy.vault import PrivacyVault
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import stat

@pytest.fixture
def vault(tmp_path):
    """Fixture for privacy vault"""
    vault_path = tmp_path / "test_vault.db"
    key_file = tmp_path / ".vault_key"
    return PrivacyVault(str(vault_path), key_file=str(key_file))

def test_store_and_retrieve_pii(vault):
    """Test storing and retrieving PII"""
    pii_data = {
        'account_number': '1234567890123456',
        'pan': 'ABCDE1234F',
        'ifsc': 'AXIS0001234'
    }

    # Store PII
    pii_ref = vault.store_pii(pii_data)
    assert pii_ref.startswith('pii_')

    # Retrieve PII
    retrieved = vault.retrieve_pii(pii_ref)
    assert retrieved == pii_data

def test_retrieve_non_existent_pii(vault):
    """Test retrieving non-existent PII"""
    result = vault.retrieve_pii("invalid_ref")
    assert result is None

def test_delete_pii(vault):
    """Test deleting PII"""
    pii_data = {'account': '123456'}
    pii_ref = vault.store_pii(pii_data)

    # Delete
    success = vault.delete_pii(pii_ref)
    assert success is True

    # Verify deleted
    retrieved = vault.retrieve_pii(pii_ref)
    assert retrieved is None

def test_key_file_permissions(tmp_path):
    """Test that key file has secure permissions"""
    vault_path = tmp_path / "test_vault.db"
    key_file = tmp_path / ".vault_key"

    vault = PrivacyVault(str(vault_path), key_file=str(key_file))

    # Check file permissions (should be 600)
    file_stat = key_file.stat()
    perms = file_stat.st_mode & 0o777
    assert perms == 0o600, f"Key file has insecure permissions: {oct(perms)}"

def test_key_rotation(vault):
    """Test key rotation without data loss"""
    # Store some PII with old key
    pii_data_1 = {'account': '1111222233334444', 'pan': 'ABCDE1111A'}
    pii_data_2 = {'account': '5555666677778888', 'pan': 'FGHIJ2222B'}
    pii_data_3 = {'account': '9999000011112222', 'pan': 'KLMNO3333C'}

    ref1 = vault.store_pii(pii_data_1)
    ref2 = vault.store_pii(pii_data_2)
    ref3 = vault.store_pii(pii_data_3)

    # Verify old key version
    old_version = vault.key_version

    # Rotate key
    success = vault.rotate_key()
    assert success is True

    # Verify new key version
    assert vault.key_version == old_version + 1

    # Verify all PII can still be retrieved with new key
    assert vault.retrieve_pii(ref1) == pii_data_1
    assert vault.retrieve_pii(ref2) == pii_data_2
    assert vault.retrieve_pii(ref3) == pii_data_3

def test_key_rotation_with_custom_key(vault):
    """Test key rotation with user-provided key"""
    # Store PII
    pii_data = {'account': '1234567890'}
    pii_ref = vault.store_pii(pii_data)

    # Generate custom new key
    new_key = AESGCM.generate_key(bit_length=256)

    # Rotate to custom key
    success = vault.rotate_key(new_key=new_key)
    assert success is True

    # Verify data is retrievable
    assert vault.retrieve_pii(pii_ref) == pii_data

    # Verify vault is using new key
    assert vault.key == new_key

def test_key_from_environment(tmp_path, monkeypatch):
    """Test loading key from environment variable"""
    vault_path = tmp_path / "test_vault.db"
    key_file = tmp_path / ".vault_key"

    # Generate a key and set in environment
    import base64
    test_key = AESGCM.generate_key(bit_length=256)
    test_key_b64 = base64.b64encode(test_key).decode('utf-8')
    monkeypatch.setenv('VAULT_KEY', test_key_b64)

    # Create vault (should use env key)
    vault = PrivacyVault(str(vault_path), key_file=str(key_file))

    # Verify it's using the env key
    assert vault.key == test_key
```

#### Integration Test (`tests/test_integration/test_end_to_end.py`)

```python
"""
End-to-end integration test
"""

import pytest
from pathlib import Path
from ingest.csv_parser import CSVParser
from ingest.normalizer import TransactionNormalizer
from mapping.merchant_mapper import MerchantMapper
from storage.models import DatabaseManager
from storage.repository import TransactionRepository

@pytest.fixture
def sample_statement(tmp_path):
    """Create sample statement CSV"""
    csv_content = """Date,Description,Withdrawal Amount (INR),Balance (INR)
15/10/2025,UPI/Swiggy Ltd/payment,1250.00,45230.50
14/10/2025,UPI/Zepto/groceries,608.24,46480.50
"""
    csv_file = tmp_path / "statement.csv"
    csv_file.write_text(csv_content)
    return str(csv_file)

@pytest.fixture
def db(tmp_path):
    """Create test database"""
    return DatabaseManager(str(tmp_path / "test.db"))

def test_full_ingestion_pipeline(sample_statement, db):
    """Test complete ingestion pipeline"""
    # Initialize components
    csv_parser = CSVParser()
    normalizer = TransactionNormalizer()
    merchant_mapper = MerchantMapper()
    repo = TransactionRepository(db)

    # Parse
    raw_transactions = csv_parser.parse(sample_statement)
    assert len(raw_transactions) == 2

    # Normalize and map
    canonical_transactions = []
    for raw_txn in raw_transactions:
        canonical = normalizer.normalize(raw_txn)

        # Map merchant
        mapping = merchant_mapper.map_merchant(canonical.merchant_raw)
        canonical.merchant_canonical = mapping['merchant_canonical']
        canonical.category = mapping['category']
        canonical.category_confidence = mapping['confidence']

        canonical_transactions.append(canonical)

    # Save to database
    transaction_dicts = [txn.to_dict() for txn in canonical_transactions]
    count = repo.create_batch(transaction_dicts)
    assert count == 2

    # Query and verify
    food_transactions = repo.filter_by_category('Food')
    assert len(food_transactions) == 2

    spending = repo.get_spending_by_category()
    assert 'Food' in spending
    assert spending['Food'] == pytest.approx(1858.24, 0.01)
```

---

## 13. Sample Data

### 12.1 Sample Labeled Training Data (`ml/training_data/labeled_transactions.jsonl`)

```jsonl
{"description": "UPI Swiggy Ltd payment for food delivery", "category": "Food"}
{"description": "UPI Zomato order payment", "category": "Food"}
{"description": "UPI Zepto groceries shopping", "category": "Food"}
{"description": "Netflix subscription monthly charge", "category": "Subscriptions"}
{"description": "Amazon Prime Video subscription", "category": "Subscriptions"}
{"description": "Spotify premium monthly payment", "category": "Subscriptions"}
{"description": "Amazon shopping purchase electronics", "category": "Shopping"}
{"description": "Flipkart order clothing", "category": "Shopping"}
{"description": "HP Pay fuel station payment", "category": "Fuel"}
{"description": "Indian Oil petrol pump", "category": "Fuel"}
{"description": "Apollo Pharmacy medicine purchase", "category": "Pharmacy"}
{"description": "Uber ride payment", "category": "Transport"}
{"description": "Ola cab service", "category": "Transport"}
{"description": "CRED credit card bill payment", "category": "Bills"}
{"description": "Airtel mobile recharge", "category": "Bills"}
{"description": "Electricity bill payment", "category": "Bills"}
{"description": "Groww mutual fund investment", "category": "Investment"}
{"description": "Zerodha stock purchase", "category": "Investment"}
{"description": "Starbucks coffee purchase", "category": "Food"}
{"description": "Dominos pizza order", "category": "Food"}
```

### 12.2 Sample Merchant Map (`mapping/merchant_map.csv`)

Already provided in Section 5.2

### 12.3 Sample CSV Statement (`sample_data/statement.csv`)

```csv
Date,Transaction Remarks,Withdrawal Amount (INR),Deposit Amount (INR),Balance (INR)
15/10/2025,UPI/Swiggy Ltd/swiggyupi@axb/Payment/AXIS,1250.00,,45230.50
15/10/2025,UPI/Zepto/ZEPTOONLINE@yb/Groceries,608.24,,44622.26
14/10/2025,Salary Credit From ABC Corp,,75000.00,120622.26
13/10/2025,NEFT/Rent Payment/To John Doe,25000.00,,45622.26
12/10/2025,UPI/Netflix/netflix@icici/Subscription,799.00,,20622.26
11/10/2025,ATM Withdrawal Cash,5000.00,,21421.26
10/10/2025,UPI/Amazon/amazonpay@axl/Shopping,2399.00,,26421.26
09/10/2025,UPI/HP Pay/hppay@paytm/Fuel,3500.00,,28820.26
08/10/2025,Card Purchase Apollo Pharmacy,1250.00,,32320.26
07/10/2025,UPI/Uber/uber@axl/Ride,385.00,,33570.26
```

---

## 14. Complete Implementation Guide

### 13.1 Project Structure

```
finance-app/
├── ingest/
│   ├── __init__.py
│   ├── pdf_parser.py
│   ├── csv_parser.py
│   └── normalizer.py
├── mapping/
│   ├── __init__.py
│   ├── merchant_mapper.py
│   ├── merchant_map.csv
│   └── config.yaml
├── privacy/
│   ├── __init__.py
│   ├── vault.py
│   └── masking.py
├── aa/
│   ├── __init__.py
│   ├── aa_client_stub.py
│   ├── interface.py
│   └── config.json
├── ml/
│   ├── __init__.py
│   ├── categorizer.py
│   ├── prepare_training_data.py
│   ├── evaluate.py
│   ├── models/              # Trained model files
│   ├── training_data/       # Labeled JSONL files
│   └── evaluation/          # Reports and plots
├── storage/
│   ├── __init__.py
│   ├── models.py
│   └── repository.py
├── cli/
│   ├── __init__.py
│   └── main.py
├── tests/
│   └── [test files as shown above]
├── data/
│   ├── statements/          # Input PDF/CSV files
│   ├── transactions.jsonl   # Processed canonical transactions
│   ├── finance.db           # SQLite database
│   └── vault.db             # Encrypted PII storage
├── sample_data/             # Sample files for testing
│   ├── statement.csv
│   └── labeled_transactions.jsonl
├── schema.py                # Canonical schema definition
├── dashboard.py             # Streamlit dashboard (existing)
├── requirements.txt
├── requirements-dev.txt
├── setup.py
├── pytest.ini
├── .env                     # Environment variables (not in git)
├── .gitignore
└── README.md
```

### 13.2 Setup Instructions

#### Step 1: Environment Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development

# Create necessary directories
mkdir -p data/statements data/cleaned reports ml/models ml/training_data ml/evaluation
mkdir -p mapping privacy aa storage cli tests sample_data
```

#### Step 2: Configuration Files

Create `requirements.txt`:
```txt
# Core dependencies (no system deps required)
pandas==2.0.3
numpy==1.24.3
pdfplumber==0.10.3              # Pure Python PDF parsing
rapidfuzz==3.5.2
sqlalchemy==2.0.23
cryptography==41.0.7
scikit-learn==1.3.2
xgboost==2.0.3
joblib==1.3.2
click==8.1.7
python-dotenv==1.0.0
streamlit==1.29.0
matplotlib==3.8.2
seaborn==0.13.0
pyyaml==6.0.1
```

Create `requirements-optional.txt` (requires system dependencies):
```txt
# Optional PDF parsing (requires system deps)
tabula-py==2.8.2                # Requires: Java JRE 8+
camelot-py[cv]==0.11.0          # Requires: Ghostscript, OpenCV
pytesseract==0.3.10             # Requires: Tesseract OCR
pdf2image==1.16.3               # Requires: Poppler

# Optional ML dependencies
# transformers==4.35.2
# datasets==2.15.0
# torch==2.1.1
```

Create `requirements-full.txt` (all dependencies):
```txt
-r requirements.txt
-r requirements-optional.txt
```

Create `requirements-dev.txt`:
```txt
pytest==7.4.3
pytest-cov==4.1.0
black==23.12.1
flake8==7.0.0
mypy==1.7.1
```

Create `setup.py`:
```python
from setuptools import setup, find_packages

setup(
    name="finance-app",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        'pandas>=2.0.3',
        'numpy>=1.24.3',
        'pdfplumber>=0.10.3',
        'camelot-py[cv]>=0.11.0',
        'rapidfuzz>=3.5.2',
        'sqlalchemy>=2.0.23',
        'cryptography>=41.0.7',
        'scikit-learn>=1.3.2',
        'xgboost>=2.0.3',
        'joblib>=1.3.2',
        'click>=8.1.7',
        'python-dotenv>=1.0.0',
        'streamlit>=1.29.0',
    ],
    entry_points={
        'console_scripts': [
            'finance-app=cli.main:cli',
        ],
    },
    python_requires='>=3.8',
)
```

#### Step 3: Initialize Components

Create all module files from the specification templates above in their respective directories.

#### Step 4: Install Package

```bash
# Install in development mode
pip install -e .

# Verify installation
finance-app --version
```

### 13.3 Usage Examples

#### Example 1: Ingest CSV Statements

```bash
# Ingest single file
finance-app ingest data/statements/october_2025.csv

# Ingest multiple files
finance-app ingest data/statements/*.csv

# Ingest with options
finance-app ingest data/statements/*.csv --output processed.jsonl --verbose
```

#### Example 2: Train ML Model

```bash
# Prepare training data
python -m ml.prepare_training_data

# Train model
finance-app train --training-data ml/training_data/labeled_transactions.jsonl --evaluate
```

#### Example 3: Query Transactions

```bash
# Query by category
finance-app query --category Food --limit 20

# Query by date range
finance-app query --date-from 2025-01-01 --date-to 2025-12-31

# Get spending summary
finance-app summary --date-from 2025-10-01 --date-to 2025-10-31
```

#### Example 4: Launch Dashboard

```bash
# Launch default dashboard
finance-app dashboard

# Launch on specific port
finance-app dashboard --port 8502
```

### 13.4 Development Workflow

#### Adding New Merchants

1. Edit `mapping/merchant_map.csv`:
```csv
new_merchant,Canonical Name,Category
```

2. Or add runtime:
```python
from mapping.merchant_mapper import MerchantMapper

mapper = MerchantMapper()
mapper.add_merchant_mapping('raw_name', 'Canonical Name', 'Category')
```

#### Adding Training Data

1. Manually label transactions:
```python
from ml.prepare_training_data import TrainingDataPreparer

preparer = TrainingDataPreparer()
preparer.add_labeled_transaction({
    'description': 'UPI Payment to XYZ',
    'category': 'Food'
})
```

2. Extract high-confidence auto-labeled data:
```python
# From ingested transactions
auto_labeled = preparer.extract_auto_labeled(transactions, min_confidence=0.95)
```

#### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_ingest/test_csv_parser.py

# Run with coverage
pytest --cov=. --cov-report=html

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration
```

### 13.5 System Dependencies (Optional PDF Parsing)

#### macOS (Homebrew)
```bash
# For tabula-py (advanced table extraction)
brew install openjdk@11
brew link openjdk@11

# For camelot-py (complex table detection)
brew install ghostscript

# For OCR (scanned PDFs)
brew install tesseract
brew install poppler
```

#### Ubuntu/Debian
```bash
# For tabula-py
sudo apt-get install default-jre

# For camelot-py
sudo apt-get install ghostscript python3-tk

# For OCR
sudo apt-get install tesseract-ocr
sudo apt-get install poppler-utils
```

#### Verification
```bash
# Check Java (for tabula)
java -version

# Check Ghostscript (for camelot)
gs --version

# Check Tesseract (for OCR)
tesseract --version
```

### 13.6 Docker Support

Create `Dockerfile`:
```dockerfile
FROM python:3.10-slim

# Install system dependencies for optional PDF parsing
RUN apt-get update && apt-get install -y \
    default-jre \
    ghostscript \
    python3-tk \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY requirements.txt requirements-optional.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements-optional.txt || true

# Copy application code
COPY . .

# Install package
RUN pip install -e .

# Create data directories
RUN mkdir -p data/statements data/cleaned reports ml/models ml/training_data

# Expose Streamlit port
EXPOSE 8501

# Default command
CMD ["streamlit", "run", "dashboard.py"]
```

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  finance-app:
    build: .
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data
      - ./ml:/app/ml
      - ./mapping:/app/mapping
    environment:
      - FINANCE_APP_VAULT_KEY=${FINANCE_APP_VAULT_KEY}
    command: streamlit run dashboard.py --server.address=0.0.0.0
```

Create `.dockerignore`:
```
__pycache__
*.pyc
*.pyo
*.pyd
.Python
venv/
env/
.env
.git
.gitignore
*.log
*.db
.DS_Store
.vscode
.idea
```

#### Docker Usage
```bash
# Build image
docker build -t finance-app .

# Run with docker-compose
docker-compose up

# Run CLI commands
docker run -v $(pwd)/data:/app/data finance-app finance-app ingest data/statements/*.csv

# Interactive shell
docker run -it finance-app /bin/bash
```

### 13.7 Security Best Practices

#### Vault Key Management

**Initial Setup:**
```bash
# The app will generate .vault_key on first run with 600 permissions
# Verify permissions
ls -la .vault_key
# Should show: -rw------- (600)

# If permissions are wrong, fix them:
chmod 600 .vault_key

# Backup key securely
cp .vault_key ~/.ssh/vault_key.backup
chmod 600 ~/.ssh/vault_key.backup
```

**Environment Variables (Recommended for Production):**
```bash
# Option 1: Set in environment
export VAULT_KEY="base64_encoded_key_here"

# Option 2: Use custom key file location
export VAULT_KEY_FILE="/secure/path/to/vault.key"

# Option 3: Docker secrets
docker secret create vault_key .vault_key
```

**Key Rotation Schedule:**
```bash
# Rotate key every 90 days (recommended)
finance-app rotate-key

# Check vault info
finance-app vault-info

# Manual backup before rotation
cp data/vault.db data/vault_backup_$(date +%Y%m%d).db
cp .vault_key .vault_key.backup_$(date +%Y%m%d)
```

**.gitignore Requirements:**
```gitignore
# Vault keys (CRITICAL!)
.vault_key
.vault_key.*
*.vault_key
vault_key*

# Vault data
data/vault.db
data/vault_backup_*

# Environment files
.env
.env.*

# PII audit logs
vault_audit.log
```

**Production Key Storage Options:**

1. **AWS Secrets Manager:**
```python
import boto3

def get_vault_key_from_aws():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='finance-app/vault-key')
    return base64.b64decode(response['SecretString'])
```

2. **GCP Secret Manager:**
```python
from google.cloud import secretmanager

def get_vault_key_from_gcp():
    client = secretmanager.SecretManagerServiceClient()
    name = "projects/PROJECT_ID/secrets/vault-key/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return base64.b64decode(response.payload.data)
```

3. **OS Keyring:**
```python
import keyring

def get_vault_key_from_keyring():
    key_b64 = keyring.get_password('finance-app', 'vault-key')
    return base64.b64decode(key_b64)
```

### 13.8 Deployment Checklist

**Security:**
- [ ] Vault key backed up securely (offsite)
- [ ] `.vault_key` has 600 permissions
- [ ] `.vault_key` added to `.gitignore`
- [ ] Environment variables configured (production)
- [ ] Key rotation schedule established (90 days)
- [ ] Audit logs enabled and monitored
- [ ] PII access logged

**Code Quality:**
- [ ] All tests passing (`pytest`)
- [ ] Code formatted (`black .`)
- [ ] Linting clean (`flake8 .`)
- [ ] Type checking passed (`mypy`)
- [ ] Security scan completed (`bandit`)

**Deployment:**
- [ ] Requirements frozen (`pip freeze > requirements-lock.txt`)
- [ ] Sample data and trained model included
- [ ] README.md updated with usage instructions
- [ ] System dependencies documented
- [ ] Docker setup tested
- [ ] Database migrations planned (if using Alembic)
- [ ] Backup strategy for encrypted PII vault
- [ ] Documentation generated (`sphinx` optional)
- [ ] Monitoring and alerting configured

---

## 15. Roadmap & Future Enhancements

### Phase 1: MVP (Current Specification)
- ✅ PDF/CSV statement ingestion
- ✅ Canonical transaction schema
- ✅ Merchant mapping with fuzzy matching
- ✅ ML-based categorization
- ✅ Privacy vault for PII
- ✅ SQLite storage
- ✅ CLI interface
- ✅ AA stub integration

### Phase 2: Enhanced Features
- [ ] Web UI (FastAPI + React)
- [ ] Multi-user support with authentication
- [ ] Recurring transaction detection
- [ ] Budget tracking and alerts
- [ ] Export to Excel/PDF reports
- [ ] Mobile app (React Native)
- [ ] Cloud sync (optional)

### Phase 3: Advanced Analytics
- [ ] Spending insights and trends
- [ ] Anomaly detection
- [ ] Predictive budgeting
- [ ] Tax categorization (India-specific)
- [ ] Investment portfolio tracking
- [ ] Bill reminders

### Phase 4: Production AA Integration
- [ ] Real Sahamati AA client implementation
- [ ] OAuth flow for AA consent
- [ ] Live bank statement fetch
- [ ] Automated daily sync
- [ ] Multi-account aggregation

### Phase 5: ML Enhancements
- [ ] Transformer-based categorization (BERT/FinBERT)
- [ ] Active learning pipeline
- [ ] Custom category creation
- [ ] Multi-language support
- [ ] Receipt OCR integration

---

## 16. Performance & Scaling

### 16.1 Performance Optimization

**Database Indexing:**
```sql
-- Critical indexes for query performance
CREATE INDEX idx_transaction_date ON transactions(date);
CREATE INDEX idx_transaction_merchant ON transactions(merchant_canonical);
CREATE INDEX idx_transaction_category ON transactions(category);
CREATE INDEX idx_transaction_account ON transactions(account_id);
CREATE INDEX idx_transaction_amount ON transactions(amount);
CREATE INDEX idx_transaction_duplicate ON transactions(duplicate_of);

-- Composite indexes for common queries
CREATE INDEX idx_date_category ON transactions(date, category);
CREATE INDEX idx_merchant_date ON transactions(merchant_canonical, date);
```

**Query Optimization:**
```python
# Use pagination for large result sets
def get_transactions_paginated(db_session, page=1, page_size=100):
    offset = (page - 1) * page_size
    return db_session.query(Transaction)\\
        .order_by(Transaction.date.desc())\\
        .limit(page_size)\\
        .offset(offset)\\
        .all()

# Use select_related for eager loading
def get_transactions_with_merchant(db_session):
    return db_session.query(Transaction)\\
        .join(Merchant)\\
        .options(joinedload(Transaction.merchant))\\
        .all()
```

**Caching Strategy:**
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_merchant_mapping(merchant_raw: str) -> str:
    """Cache merchant lookups"""
    return merchant_mapper.map_merchant(merchant_raw)

# Clear cache when mappings updated
def update_merchant_mapping(...):
    get_merchant_mapping.cache_clear()
    # ... update logic
```

### 16.2 Scaling Recommendations

**Development (< 10K transactions):**
- SQLite is sufficient
- Single process
- No caching needed

**Small Scale (10K - 100K transactions):**
- SQLite with WAL mode
- Add query caching
- Background processing for ML

**Medium Scale (100K - 1M transactions):**
- Migrate to PostgreSQL
- Connection pooling
- Celery for async tasks
- Redis for caching

**Large Scale (> 1M transactions):**
- PostgreSQL with partitioning (by year/month)
- Read replicas
- Elasticsearch for search
- Distributed ML training

**Migration Path:**
```python
# config.py - Environment-based database selection
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/finance.db')

# Production example:
# DATABASE_URL=postgresql://user:pass@localhost/financedb

# No code changes needed - SQLAlchemy handles dialect differences
```

### 16.3 Monitoring & Observability

**Application Metrics:**
```python
from logging_config import PerformanceLogger

# Track operation performance
with PerformanceLogger(logger, "pdf_parsing"):
    transactions = pdf_parser.parse(file_path)

# Logs: "Completed: pdf_parsing, duration_ms: 1234.56"
```

**Database Metrics:**
```python
# Monitor query performance
import time

def log_slow_queries(query_func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = query_func(*args, **kwargs)
        duration = (time.time() - start) * 1000

        if duration > 1000:  # > 1 second
            logger.warning(f"Slow query detected: {query_func.__name__}, "
                         f"duration_ms={duration:.2f}")
        return result
    return wrapper

@log_slow_queries
def get_all_transactions():
    return db.query(Transaction).all()
```

**Error Rate Tracking:**
```python
from logging_config import ErrorSummary

error_tracker = ErrorSummary()

try:
    parse_pdf(file_path)
except Exception as e:
    error_tracker.log_error('ParseError', str(e), {'file': file_path})

# Periodically check error summary
summary = error_tracker.get_summary()
if summary['total_errors'] > 100:
    logger.critical(f"High error rate detected: {summary}")
```

---

## 17. Compliance & Regulatory

### 17.1 Data Protection & Privacy Compliance

**DPDP Act 2023 (India) Compliance:**

- [ ] **Data Minimization**: Only collect necessary financial data
- [ ] **Consent Management**: Explicit user consent for data processing
- [ ] **Right to Erasure**: Implement data deletion on user request
- [ ] **Data Localization**: Store Indian user data within India
- [ ] **Encryption**: All PII encrypted at rest (AES-256-GCM)
- [ ] **Audit Logging**: Track all PII access with timestamps
- [ ] **Data Retention**: Define and enforce retention policies
- [ ] **Breach Notification**: Process for notifying users within 72 hours

**Implementation:**
```python
# User consent tracking
class UserConsent(Base):
    __tablename__ = 'user_consents'
    user_id = Column(String, primary_key=True)
    consent_type = Column(String)  # 'data_processing', 'ml_training'
    granted_at = Column(DateTime)
    withdrawn_at = Column(DateTime, nullable=True)

# Data deletion
def delete_user_data(user_id: str):
    """Right to erasure implementation"""
    # 1. Delete from vault
    vault.delete_pii(user_id)
    # 2. Delete transactions
    db.query(Transaction).filter_by(user_id=user_id).delete()
    # 3. Audit log
    audit_log(f"User {user_id} data deleted", level='INFO')
```

**RBI DEPA Framework (Account Aggregator):**

- [ ] **User Consent Architecture**: AA consent flow implemented
- [ ] **Data Fiduciary Role**: Clear responsibility for data protection
- [ ] **Purpose Limitation**: Use data only for stated purposes
- [ ] **Consent Revocation**: Allow users to revoke AA access
- [ ] **Data Retention Limits**: Delete fetched data after consent expiry

**GDPR Readiness (for EU users):**

- [ ] **Right to Access**: Export user data in machine-readable format
- [ ] **Right to Portability**: JSON export functionality
- [ ] **Privacy by Design**: Encryption, pseudonymization by default
- [ ] **Data Protection Officer**: Designate responsible person
- [ ] **Privacy Policy**: Clear disclosure of data practices

### 17.2 Financial Regulations

**RBI Guidelines:**
- Do NOT store CVV, full card numbers, or OTPs
- Implement two-factor authentication for sensitive operations
- Maintain audit trails for all financial transactions
- Use certified payment gateways for any payment processing

**PCI-DSS (if handling card data):**
- Never store full card numbers - use tokenization
- Encrypt card data in transit (TLS 1.2+)
- Regular security audits

### 17.3 Security Best Practices

**Application Security:**
```python
# Input validation
def validate_amount(amount: float) -> bool:
    if not isinstance(amount, (int, float)):
        raise ValueError("Amount must be numeric")
    if amount < 0:
        raise ValueError("Amount cannot be negative")
    if amount > 1e10:  # 1 billion max
        raise ValueError("Amount exceeds maximum")
    return True

# SQL injection prevention (SQLAlchemy parameterized queries)
# NEVER use string concatenation for queries
def get_transactions_by_merchant(merchant: str):
    # Good - parameterized
    return db.query(Transaction).filter(Transaction.merchant == merchant).all()

    # Bad - SQL injection risk
    # return db.execute(f"SELECT * FROM transactions WHERE merchant = '{merchant}'")
```

**File Upload Security:**
```python
def validate_upload(file_path: str) -> bool:
    # Check file size
    if os.path.getsize(file_path) > 10 * 1024 * 1024:  # 10MB
        raise ValueError("File too large")

    # Check file type
    allowed_extensions = {'.pdf', '.csv'}
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in allowed_extensions:
        raise ValueError(f"File type {ext} not allowed")

    # Check for malicious content (basic)
    with open(file_path, 'rb') as f:
        header = f.read(100)
        if b'<script>' in header or b'javascript:' in header:
            raise ValueError("Potentially malicious file content")

    return True
```

### 17.4 Audit & Compliance Checklist

**Pre-Production:**
- [ ] All secrets in environment variables (not committed to git)
- [ ] Database backups configured
- [ ] PII encryption enabled and tested
- [ ] Audit logging enabled
- [ ] Rate limiting on API endpoints
- [ ] Input validation on all user inputs
- [ ] HTTPS enforced (if web interface added)
- [ ] Security headers configured
- [ ] Dependency vulnerability scan (pip-audit, safety)
- [ ] Code review completed
- [ ] Penetration testing performed

**Ongoing:**
- [ ] Monthly security updates
- [ ] Quarterly access reviews
- [ ] Annual compliance audit
- [ ] Incident response plan tested
- [ ] Backup restoration tested
- [ ] User data export tested (GDPR/DPDP)

---

## 18. Conclusion

This technical specification provides a complete blueprint for building a production-ready personal finance application with:

1. **Robust Ingestion**: PDF/CSV parsing with normalization
2. **Intelligent Categorization**: Rule-based + ML hybrid approach
3. **Privacy-First**: AES-GCM encryption for sensitive data
4. **Extensible Architecture**: Modular design for easy enhancement
5. **Developer-Friendly**: CLI, comprehensive tests, clear documentation

**Next Steps:**
1. Review this specification
2. Set up development environment
3. Implement modules incrementally (start with ingestion)
4. Test each module thoroughly
5. Integrate components
6. Deploy MVP

**Estimated Timeline:**
- Module Implementation: 2-3 weeks
- Testing & Integration: 1 week
- Documentation: 3-4 days
- MVP Deployment: ~4 weeks total

The specification is designed to be implemented incrementally while maintaining functionality at each stage. Start with the ingestion pipeline and build up from there.

---

**END OF TECHNICAL SPECIFICATION**

*Generated: October 26, 2025*
*Version: 1.0.0*
*Document Size: ~4,500 lines of specification + ~3,000 lines of code templates*