"""
Configuration management with python-dotenv

IMPORTANT: Never commit .env files to git!

Priority Order:
1. System environment variables (production)
2. .env file (development/local)
3. Default values (non-sensitive only)
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Load .env file if it exists
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

    # API Keys (optional - for future cloud integrations)
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

    # Frontend URL (for CORS configuration)
    FRONTEND_URL = os.getenv('FRONTEND_URL')  # e.g., https://your-frontend.com

    # Feature Flags
    ENABLE_PDF_OCR = os.getenv('ENABLE_PDF_OCR', 'false').lower() == 'true'
    ENABLE_CAMELOT = os.getenv('ENABLE_CAMELOT', 'false').lower() == 'true'
    ENABLE_TABULA = os.getenv('ENABLE_TABULA', 'false').lower() == 'true'

    # Deduplication Settings
    DEDUP_TIME_WINDOW_DAYS = int(os.getenv('DEDUP_TIME_WINDOW_DAYS', '1'))
    DEDUP_FUZZY_THRESHOLD = int(os.getenv('DEDUP_FUZZY_THRESHOLD', '85'))
    DEDUP_MERGE_DUPLICATES = os.getenv('DEDUP_MERGE_DUPLICATES', 'true').lower() == 'true'

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []

        # Check critical settings
        if not cls.VAULT_KEY and not Path(cls.VAULT_KEY_FILE).exists():
            errors.append("VAULT_KEY not set and key file not found")

        # Validate threshold ranges
        if not (0 <= cls.DEDUP_FUZZY_THRESHOLD <= 100):
            errors.append(f"DEDUP_FUZZY_THRESHOLD must be 0-100, got {cls.DEDUP_FUZZY_THRESHOLD}")

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

    @classmethod
    def print_config(cls):
        """Print current configuration (masked)"""
        print("\n" + "="*60)
        print("CONFIGURATION")
        print("="*60)
        print(f"Database URL: {cls.get_database_url(mask_password=True)}")
        print(f"Vault Key File: {cls.VAULT_KEY_FILE}")
        print(f"Vault Key (env): {'SET' if cls.VAULT_KEY else 'NOT SET'}")
        print(f"Log Level: {cls.LOG_LEVEL}")
        print(f"ML Model Path: {cls.ML_MODEL_PATH}")
        print(f"\nFeature Flags:")
        print(f"  PDF OCR: {cls.ENABLE_PDF_OCR}")
        print(f"  Camelot: {cls.ENABLE_CAMELOT}")
        print(f"  Tabula: {cls.ENABLE_TABULA}")
        print(f"\nDeduplication:")
        print(f"  Time Window: ±{cls.DEDUP_TIME_WINDOW_DAYS} days")
        print(f"  Fuzzy Threshold: {cls.DEDUP_FUZZY_THRESHOLD}%")
        print(f"  Merge Duplicates: {cls.DEDUP_MERGE_DUPLICATES}")
        print("="*60 + "\n")


# Usage in other modules:
# from config import Config
# vault_key = Config.VAULT_KEY
# if Config.ENABLE_PDF_OCR:
#     # Use OCR
