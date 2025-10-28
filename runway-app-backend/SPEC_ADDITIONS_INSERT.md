# Technical Specification - Sections to Insert

## Instructions
Insert these sections into TECHNICAL_SPECIFICATION.md at the specified line numbers.

---

## INSERT AFTER LINE 86 (before "## 2. Canonical Transaction Schema")

```markdown
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

Create `config.py` in project root:

```python
"""
Configuration management with python-dotenv
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Load .env file
env_path = Path('.env')
if env_path.exists():
    load_dotenv(env_path)
    logger.info(f"Loaded configuration from {env_path}")
else:
    logger.warning(f".env file not found at {env_path}")
    logger.warning("Using system environment variables and defaults")

class Config:
    """Application configuration"""

    # Vault & Security
    VAULT_KEY = os.getenv('VAULT_KEY')
    VAULT_KEY_FILE = os.getenv('VAULT_KEY_FILE', '.vault_key')

    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/finance.db')

    # API Keys (optional)
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

    # Account Aggregator
    AA_CLIENT_ID = os.getenv('AA_CLIENT_ID')
    AA_CLIENT_SECRET = os.getenv('AA_CLIENT_SECRET')
    AA_REDIRECT_URI = os.getenv('AA_REDIRECT_URI')

    # Application Settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    ENABLE_AUDIT_LOGGING = os.getenv('ENABLE_AUDIT_LOGGING', 'true').lower() == 'true'
    ML_MODEL_PATH = os.getenv('ML_MODEL_PATH', 'ml/models/categorizer.pkl')

    # Feature Flags
    ENABLE_PDF_OCR = os.getenv('ENABLE_PDF_OCR', 'false').lower() == 'true'
    ENABLE_CAMELOT = os.getenv('ENABLE_CAMELOT', 'false').lower() == 'true'
    ENABLE_TABULA = os.getenv('ENABLE_TABULA', 'false').lower() == 'true'

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []

        # Check critical settings
        if not cls.VAULT_KEY and not Path(cls.VAULT_KEY_FILE).exists():
            errors.append("VAULT_KEY not set and key file not found")

        if errors:
            raise ValueError(f"Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))

        logger.info("Configuration validated successfully")

    @classmethod
    def get_database_url(cls, mask_password=True) -> str:
        """Get database URL with optional password masking"""
        url = cls.DATABASE_URL
        if mask_password and '@' in url:
            # Mask password in postgres://user:PASSWORD@host/db
            parts = url.split('@')
            if ':' in parts[0]:
                user_pass = parts[0].split(':')
                return f"{user_pass[0]}:****@{parts[1]}"
        return url


# Usage in other modules:
# from config import Config
# vault_key = Config.VAULT_KEY
```

### 2.3 Environment Files

Create `.env` (NEVER commit to git):
```bash
# Vault Encryption
VAULT_KEY=base64_encoded_256bit_key_here
VAULT_KEY_FILE=.vault_key

# Database
DATABASE_URL=sqlite:///data/finance.db
# DATABASE_URL=postgresql://user:pass@localhost/financedb  # Production

# API Keys (if using cloud services)
# AWS_ACCESS_KEY_ID=your_key
# AWS_SECRET_ACCESS_KEY=your_secret
# OPENAI_API_KEY=sk-...  # If using GPT for categorization

# Account Aggregator (when using real AA)
# AA_CLIENT_ID=your_fiu_client_id
# AA_CLIENT_SECRET=your_fiu_secret
# AA_REDIRECT_URI=https://yourapp.com/aa/callback

# Application Settings
LOG_LEVEL=INFO
ENABLE_AUDIT_LOGGING=true
ML_MODEL_PATH=ml/models/categorizer.pkl

# Feature Flags
ENABLE_PDF_OCR=false
ENABLE_CAMELOT=false
ENABLE_TABULA=false
```

Create `.env.example` (safe to commit):
```bash
# Vault Encryption (generate your own!)
VAULT_KEY=REPLACE_WITH_BASE64_KEY_FROM_SETUP
VAULT_KEY_FILE=.vault_key

# Database
DATABASE_URL=sqlite:///data/finance.db

# API Keys (leave blank, fill in production)
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
# OPENAI_API_KEY=

# Account Aggregator
# AA_CLIENT_ID=
# AA_CLIENT_SECRET=
# AA_REDIRECT_URI=

# Application Settings
LOG_LEVEL=INFO
ENABLE_AUDIT_LOGGING=true
ML_MODEL_PATH=ml/models/categorizer.pkl

# Feature Flags
ENABLE_PDF_OCR=false
ENABLE_CAMELOT=false
ENABLE_TABULA=false
```

### 2.4 Updated .gitignore

**Add to .gitignore:**
```gitignore
# Environment & Secrets (NEVER COMMIT!)
.env
.env.local
.env.*.local
*.env
!.env.example

# Vault keys
.vault_key
.vault_key.*
*.vault_key

# Credentials
secrets.json
credentials.json
service-account.json

# API keys
api_keys.txt
*.pem
*.key

# Database files
*.db
*.sqlite
*.sqlite3
data/*.db

# Logs
*.log
logs/
vault_audit.log

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo
.DS_Store

# Backups
*.backup
*_backup_*
vault_backup_*

# Temporary files
*.tmp
*.temp
.cache/
```

### 2.5 Security Checklist for Configuration

- [ ] `.env` file created with secure values
- [ ] `.env` added to `.gitignore`
- [ ] `.env.example` provided as template (no secrets)
- [ ] All API keys rotated after any leak
- [ ] Vault key backed up securely offline
- [ ] File permissions set: `chmod 600 .env .vault_key`
- [ ] Secrets validated on application start
- [ ] Production uses system env vars (not `.env` files)
```

---

## RENUMBER: Original "## 2" becomes "## 3", "## 3" becomes "## 4", etc.

The sections should now be:
- Section 1: System Overview
- Section 2: Configuration & Secrets Management (NEW)
- Section 3: Canonical Transaction Schema (was 2)
- Section 4: Architecture & Data Flow (was 3)
- ...and so on

---

## Additional File to Create: deduplication/detector.py

Location: Create new file at `deduplication/detector.py`

```python
"""
Transaction Deduplication with Explicit Thresholds

Rules:
1. Same date ± 1 day window
2. Exact amount match (±0.01 tolerance)
3. Fuzzy merchant similarity ≥ 85%
4. Keep earliest transaction, flag/merge duplicates

Configuration:
- time_window_days: Date tolerance (default: 1)
- fuzzy_threshold: Merchant similarity 0-100 (default: 85)
- merge_duplicates: True = merge, False = flag only
"""

from typing import List, Dict
from datetime import datetime, timedelta
from rapidfuzz import fuzz
import logging

logger = logging.getLogger(__name__)

class DeduplicationDetector:
    """Detect and merge duplicate transactions"""

    def __init__(self,
                 time_window_days: int = 1,
                 amount_tolerance: float = 0.01,
                 fuzzy_threshold: int = 85,
                 merge_duplicates: bool = True):
        """
        Args:
            time_window_days: Date tolerance (±N days)
            amount_tolerance: Amount difference tolerance
            fuzzy_threshold: Merchant similarity threshold (0-100)
            merge_duplicates: If True, merge; if False, only flag
        """
        self.time_window_days = time_window_days
        self.amount_tolerance = amount_tolerance
        self.fuzzy_threshold = fuzzy_threshold
        self.merge_duplicates = merge_duplicates

        logger.info(f"Deduplication config: ±{time_window_days}d, "
                   f"amount_tol={amount_tolerance}, fuzzy≥{fuzzy_threshold}%, "
                   f"merge={merge_duplicates}")

    def detect_duplicates(self, transactions: List[Dict]) -> List[Dict]:
        """
        Detect and handle duplicates

        Returns:
            List of transactions with duplicates flagged/merged
        """
        if not transactions:
            return []

        # Sort by date to process chronologically
        sorted_txns = sorted(transactions, key=lambda t: t.get('date', ''))

        processed = []
        skipped_count = 0

        for i, txn in enumerate(sorted_txns):
            is_duplicate = False

            # Check against previous transactions (within window)
            # Limit search to last 100 txns for performance
            start_idx = max(0, i - 100)

            for j in range(start_idx, i):
                prev_txn = sorted_txns[j]

                if self._is_duplicate(txn, prev_txn):
                    # Found duplicate
                    is_duplicate = True
                    skipped_count += 1

                    if self.merge_duplicates:
                        # Merge into existing transaction
                        existing = next((t for t in processed
                                       if t['transaction_id'] == prev_txn['transaction_id']), None)
                        if existing:
                            existing['duplicate_count'] = existing.get('duplicate_count', 0) + 1
                            logger.debug(f"Merged duplicate: {txn.get('transaction_id')} "
                                       f"into {prev_txn.get('transaction_id')}")
                    else:
                        # Just flag as duplicate
                        txn['is_duplicate'] = True
                        txn['duplicate_of'] = prev_txn['transaction_id']
                        txn['duplicate_count'] = 0
                        processed.append(txn)
                        logger.debug(f"Flagged duplicate: {txn.get('transaction_id')}")

                    break

            if not is_duplicate:
                txn['is_duplicate'] = False
                txn['duplicate_count'] = 0
                processed.append(txn)

        logger.info(f"Deduplication complete: {len(transactions)} → {len(processed)} "
                   f"({skipped_count} duplicates removed/merged)")

        return processed

    def _is_duplicate(self, txn1: Dict, txn2: Dict) -> bool:
        """
        Check if two transactions are duplicates

        Returns True if ALL rules match:
        1. Date within time window
        2. Amount matches (within tolerance)
        3. Merchant similarity ≥ threshold
        """
        # Rule 1: Date within time window
        try:
            date1_str = txn1.get('date', '')
            date2_str = txn2.get('date', '')

            if not date1_str or not date2_str:
                return False

            # Handle both YYYY-MM-DD and full ISO format
            date1 = datetime.fromisoformat(date1_str.split('T')[0])
            date2 = datetime.fromisoformat(date2_str.split('T')[0])

            date_diff = abs((date1 - date2).days)

            if date_diff > self.time_window_days:
                return False

        except (ValueError, AttributeError) as e:
            logger.debug(f"Date parsing error: {e}")
            return False

        # Rule 2: Exact amount match (with small tolerance for float comparison)
        amount1 = txn1.get('amount', 0.0)
        amount2 = txn2.get('amount', 0.0)

        if abs(amount1 - amount2) > self.amount_tolerance:
            return False

        # Rule 3: Fuzzy merchant similarity
        # Use merchant_raw or clean_description as fallback
        merchant1 = (txn1.get('merchant_raw') or
                    txn1.get('merchant_canonical') or
                    txn1.get('clean_description', ''))
        merchant2 = (txn2.get('merchant_raw') or
                    txn2.get('merchant_canonical') or
                    txn2.get('clean_description', ''))

        if not merchant1 or not merchant2:
            return False

        # Use token_sort_ratio for better matching
        similarity = fuzz.token_sort_ratio(merchant1, merchant2)

        if similarity < self.fuzzy_threshold:
            return False

        logger.debug(f"Duplicate detected: {date_diff}d apart, ₹{amount1:.2f}, "
                    f"{similarity}% similarity ({merchant1[:30]}...)")

        return True

    def get_duplicate_stats(self, transactions: List[Dict]) -> Dict:
        """Get statistics about duplicates"""
        total = len(transactions)
        duplicates = sum(1 for t in transactions if t.get('is_duplicate', False))
        merged = sum(t.get('duplicate_count', 0) for t in transactions)

        return {
            'total_transactions': total,
            'flagged_duplicates': duplicates,
            'merged_count': merged,
            'unique_transactions': total - duplicates,
            'duplicate_rate': duplicates / total if total > 0 else 0
        }


# Usage Example
if __name__ == "__main__":
    detector = DeduplicationDetector(
        time_window_days=1,
        fuzzy_threshold=85,
        merge_duplicates=True
    )

    transactions = [
        {'transaction_id': '1', 'date': '2025-10-26', 'amount': 100.0, 'merchant_raw': 'Swiggy'},
        {'transaction_id': '2', 'date': '2025-10-26', 'amount': 100.0, 'merchant_raw': 'Swiggy Ltd'},  # Duplicate
        {'transaction_id': '3', 'date': '2025-10-27', 'amount': 200.0, 'merchant_raw': 'Zomato'},
    ]

    clean = detector.detect_duplicates(transactions)
    print(f"Original: {len(transactions)}, After dedup: {len(clean)}")

    stats = detector.get_duplicate_stats(clean)
    print(f"Stats: {stats}")
```

---

## Additional File to Create: mapping/editor.py

Location: Create new file at `mapping/editor.py`

[Content from SPEC_ENHANCEMENTS.md - Merchant Mapping Editor section]

---

## Additional File to Create: logging_config.py

Location: Create new file at `logging_config.py` in project root

[Content from SPEC_ENHANCEMENTS.md - Structured Logging section]

---

## Summary of Changes

### Files to Create:
1. `config.py` - Configuration management
2. `.env.example` - Template for environment variables
3. `deduplication/detector.py` - Deduplication logic
4. `mapping/editor.py` - Merchant mapping CLI tools
5. `logging_config.py` - Structured logging

### Files to Modify:
1. `TECHNICAL_SPECIFICATION.md` - Insert Section 2 (Config Management)
2. `.gitignore` - Add entries for secrets
3. `requirements.txt` - Ensure python-dotenv is included

### Sections to Add to Spec:
- Section 2: Configuration & Secrets Management (insert after line 86)
- Section 15: Performance & Scaling (append near end)
- Section 16: Compliance & Regulatory Checklist (append at end)
- Enhanced ML Pipeline code (replace existing ml/categorizer.py section)
- Enhanced Testing Strategy (replace existing test section)

Would you like me to:
A) Create these files one by one
B) Provide a complete updated TECHNICAL_SPECIFICATION.md
C) Create a patch file you can apply
