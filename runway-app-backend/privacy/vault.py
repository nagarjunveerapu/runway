"""
Privacy Vault - Secure PII Storage with AES-256-GCM Encryption

Stores sensitive PII (account numbers, card numbers, etc.) encrypted at rest.
Uses reference IDs in main database, actual data encrypted in vault.
"""

import os
import json
import logging
import hashlib
import shutil
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64

logger = logging.getLogger(__name__)


class PrivacyVault:
    """
    Secure vault for PII encryption and storage

    Features:
    - AES-256-GCM encryption
    - Reference-based access
    - Audit logging
    - Key rotation support
    """

    def __init__(self, vault_path: str = "data/privacy_vault.enc", key: Optional[str] = None):
        """
        Initialize privacy vault

        Args:
            vault_path: Path to encrypted vault file
            key: Encryption key (base64-encoded 256-bit key)
                 If None, will try to load from .vault_key file or generate new
        """
        self.vault_path = Path(vault_path)
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)

        # Load or generate encryption key
        self.key = self._init_key(key)

        # Initialize AESGCM cipher
        self.cipher = AESGCM(base64.b64decode(self.key))

        # In-memory vault data
        self.vault_data: Dict[str, Dict] = {}

        # Audit log
        self.audit_log_path = self.vault_path.parent / "vault_audit.log"

        # Load vault if exists
        self._load_vault()

    def _init_key(self, key: Optional[str]) -> str:
        """
        Initialize encryption key

        Priority:
        1. Provided key parameter
        2. VAULT_KEY environment variable
        3. .vault_key file
        4. Generate new key

        Returns:
            Base64-encoded 256-bit key
        """
        # 1. Use provided key
        if key:
            return key

        # 2. Try environment variable
        env_key = os.getenv('VAULT_KEY')
        if env_key:
            logger.info("Using VAULT_KEY from environment")
            return env_key

        # 3. Try loading from file
        key_file = Path('.vault_key')
        if key_file.exists():
            try:
                with open(key_file, 'r') as f:
                    file_key = f.read().strip()
                logger.info(f"Loaded encryption key from {key_file}")
                return file_key
            except Exception as e:
                logger.warning(f"Failed to load key from {key_file}: {e}")

        # 4. Generate new key
        logger.warning("No encryption key found, generating new key")
        new_key = self._generate_key()
        self._save_key(new_key, key_file)
        return new_key

    @staticmethod
    def _generate_key() -> str:
        """Generate a new 256-bit encryption key"""
        key_bytes = AESGCM.generate_key(bit_length=256)
        return base64.b64encode(key_bytes).decode('utf-8')

    @staticmethod
    def _save_key(key: str, key_file: Path):
        """Save encryption key to file with secure permissions"""
        with open(key_file, 'w') as f:
            f.write(key)

        # Set file permissions to 600 (owner read/write only)
        try:
            os.chmod(key_file, 0o600)
            logger.info(f"Saved encryption key to {key_file} with permissions 600")
        except Exception as e:
            logger.warning(f"Failed to set file permissions: {e}")

    def _load_vault(self):
        """Load and decrypt vault from disk"""
        if not self.vault_path.exists():
            logger.info(f"Vault file not found: {self.vault_path}, creating new vault")
            self.vault_data = {}
            return

        try:
            with open(self.vault_path, 'rb') as f:
                encrypted_data = f.read()

            # Decrypt vault
            decrypted_data = self._decrypt_data(encrypted_data)
            self.vault_data = json.loads(decrypted_data)

            logger.info(f"Loaded vault with {len(self.vault_data)} entries")

        except Exception as e:
            logger.error(f"Failed to load vault: {e}")
            # Create backup and start fresh
            if self.vault_path.exists():
                backup_path = self.vault_path.with_suffix('.backup')
                shutil.copy(self.vault_path, backup_path)
                logger.info(f"Created backup: {backup_path}")
            self.vault_data = {}

    def _save_vault(self):
        """Encrypt and save vault to disk"""
        try:
            # Serialize vault data
            json_data = json.dumps(self.vault_data, indent=2)

            # Encrypt data
            encrypted_data = self._encrypt_data(json_data.encode('utf-8'))

            # Save to file
            with open(self.vault_path, 'wb') as f:
                f.write(encrypted_data)

            # Set file permissions to 600
            os.chmod(self.vault_path, 0o600)

            logger.debug(f"Saved vault with {len(self.vault_data)} entries")

        except Exception as e:
            logger.error(f"Failed to save vault: {e}")
            raise

    def _encrypt_data(self, data: bytes) -> bytes:
        """
        Encrypt data using AES-256-GCM

        Args:
            data: Plaintext bytes

        Returns:
            Encrypted bytes (nonce + ciphertext + tag)
        """
        # Generate random nonce
        nonce = os.urandom(12)  # 96 bits for GCM

        # Encrypt
        ciphertext = self.cipher.encrypt(nonce, data, None)

        # Return nonce + ciphertext (GCM includes authentication tag in ciphertext)
        return nonce + ciphertext

    def _decrypt_data(self, encrypted_data: bytes) -> bytes:
        """
        Decrypt data using AES-256-GCM

        Args:
            encrypted_data: Encrypted bytes (nonce + ciphertext + tag)

        Returns:
            Plaintext bytes
        """
        # Extract nonce
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]

        # Decrypt
        plaintext = self.cipher.decrypt(nonce, ciphertext, None)

        return plaintext

    def store_pii(self, pii_data: str, entity_type: str = "generic") -> str:
        """
        Store PII data and return reference ID

        Args:
            pii_data: Sensitive data to encrypt
            entity_type: Type of entity (e.g., 'account_number', 'card_number')

        Returns:
            Reference ID (SHA256 hash of data)
        """
        # Generate reference ID (deterministic hash)
        ref_id = self._generate_ref_id(pii_data)

        # Store encrypted data
        self.vault_data[ref_id] = {
            'data': pii_data,
            'entity_type': entity_type,
            'created_at': datetime.now().isoformat(),
            'accessed_count': 0,
            'last_accessed': None,
        }

        # Save vault
        self._save_vault()

        # Audit log
        self._audit_log('STORE', ref_id, entity_type)

        logger.debug(f"Stored PII with ref_id: {ref_id[:8]}...")

        return ref_id

    def retrieve_pii(self, ref_id: str) -> Optional[str]:
        """
        Retrieve PII data by reference ID

        Args:
            ref_id: Reference ID

        Returns:
            Decrypted PII data or None if not found
        """
        if ref_id not in self.vault_data:
            logger.warning(f"PII not found for ref_id: {ref_id[:8]}...")
            return None

        # Update access metadata
        self.vault_data[ref_id]['accessed_count'] += 1
        self.vault_data[ref_id]['last_accessed'] = datetime.now().isoformat()

        # Get data
        pii_data = self.vault_data[ref_id]['data']

        # Audit log
        self._audit_log('RETRIEVE', ref_id, self.vault_data[ref_id]['entity_type'])

        return pii_data

    def delete_pii(self, ref_id: str) -> bool:
        """
        Delete PII data by reference ID

        Args:
            ref_id: Reference ID

        Returns:
            True if deleted, False if not found
        """
        if ref_id not in self.vault_data:
            logger.warning(f"PII not found for deletion: {ref_id[:8]}...")
            return False

        entity_type = self.vault_data[ref_id]['entity_type']

        # Delete from vault
        del self.vault_data[ref_id]

        # Save vault
        self._save_vault()

        # Audit log
        self._audit_log('DELETE', ref_id, entity_type)

        logger.info(f"Deleted PII with ref_id: {ref_id[:8]}...")

        return True

    @staticmethod
    def _generate_ref_id(data: str) -> str:
        """Generate deterministic reference ID from data"""
        return hashlib.sha256(data.encode()).hexdigest()

    def _audit_log(self, action: str, ref_id: str, entity_type: str):
        """Write audit log entry"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': action,
                'ref_id': ref_id[:8] + '...',  # Truncated for security
                'entity_type': entity_type,
            }

            with open(self.audit_log_path, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')

        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def rotate_key(self, new_key: Optional[str] = None) -> bool:
        """
        Rotate encryption key

        Steps:
        1. Backup current vault
        2. Decrypt all data with old key
        3. Re-encrypt with new key
        4. Save new key
        5. Update vault

        Args:
            new_key: New encryption key (if None, generates new)

        Returns:
            True if successful
        """
        logger.info("Starting key rotation...")

        # 1. Backup current vault
        backup_path = self.vault_path.with_suffix(f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        shutil.copy(self.vault_path, backup_path)
        logger.info(f"Created backup: {backup_path}")

        try:
            # 2. Decrypt all data with old key (already in memory)
            decrypted_data = self.vault_data.copy()

            # 3. Generate or use new key
            if not new_key:
                new_key = self._generate_key()

            # Update key and cipher
            self.key = new_key
            self.cipher = AESGCM(base64.b64decode(self.key))

            # 4. Save new key
            key_file = Path('.vault_key')
            self._save_key(new_key, key_file)

            # 5. Re-encrypt and save vault
            self.vault_data = decrypted_data
            self._save_vault()

            # Audit log
            self._audit_log('KEY_ROTATION', 'N/A', 'vault')

            logger.info("Key rotation completed successfully")
            return True

        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            # Restore from backup
            shutil.copy(backup_path, self.vault_path)
            logger.info("Restored from backup")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get vault statistics"""
        entity_types = {}
        for data in self.vault_data.values():
            entity_type = data['entity_type']
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1

        return {
            'total_entries': len(self.vault_data),
            'entity_types': entity_types,
            'vault_size_bytes': self.vault_path.stat().st_size if self.vault_path.exists() else 0,
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Initialize vault
    vault = PrivacyVault()

    # Store PII
    account_number = "1234567890123456"
    ref_id = vault.store_pii(account_number, entity_type='account_number')
    print(f"\nStored account number with ref_id: {ref_id[:16]}...")

    # Retrieve PII
    retrieved = vault.retrieve_pii(ref_id)
    print(f"Retrieved: {retrieved}")

    # Stats
    print(f"\nVault stats: {vault.get_stats()}")

    # Key rotation
    print("\nTesting key rotation...")
    success = vault.rotate_key()
    print(f"Key rotation: {'SUCCESS' if success else 'FAILED'}")

    # Verify data still accessible
    retrieved_after_rotation = vault.retrieve_pii(ref_id)
    print(f"Data after rotation: {retrieved_after_rotation}")
