"""
Simple encryption/decryption module for student submissions.
Uses Fernet (symmetric encryption) from cryptography library.
"""
import os
import base64
import binascii
from pathlib import Path
from typing import Dict
from cryptography.fernet import Fernet
import logging
import json

logger = logging.getLogger(__name__)


class EncryptionManager:
    """Manages encryption and decryption of student files."""

    def __init__(self, keys_dir: Path = Path("student_keys"), use_default_key: bool = False):
        """
        Initialize the encryption manager.

        Args:
            keys_dir: Directory to store student-specific encryption keys
            use_default_key: If True, use a single default key for all students
        """
        self.keys_dir = Path(keys_dir)
        self.keys_dir.mkdir(exist_ok=True)
        self._keys_cache: Dict[str, bytes] = {}
        self.use_default_key = use_default_key
        self._default_key: bytes = None

    def _get_key_path(self, student_id: str) -> Path:
        """Get the path to a student's key file."""
        return self.keys_dir / f"{student_id}.key"

    def _get_or_create_default_key(self) -> bytes:
        """
        Get or create the default encryption key.

        Returns:
            Default encryption key bytes
        """
        if self._default_key:
            return self._default_key

        default_key_path = self.keys_dir / "default.key"

        # Prefer key supplied via environment (matches CI secrets)
        default_key_env = os.getenv('DEFAULT_ENCRYPTION_KEY')
        if default_key_env:
            env_key = default_key_env.strip()
            candidates = []

            # First try decoding base64 (export script encodes the key)
            try:
                candidates.append(base64.b64decode(env_key))
            except (binascii.Error, ValueError):
                logger.warning("DEFAULT_ENCRYPTION_KEY is not valid base64; trying raw value")

            # Always attempt to use the raw value as well (handles single-encoded secrets)
            candidates.append(env_key.encode('utf-8'))

            for candidate in candidates:
                try:
                    # Validate key format before persisting
                    Fernet(candidate)
                except ValueError:
                    continue

                self._default_key = candidate
                default_key_path.write_bytes(self._default_key)
                logger.info("Loaded default encryption key from environment")
                return self._default_key

            logger.error("DEFAULT_ENCRYPTION_KEY provided but not a valid Fernet key")

        if default_key_path.exists():
            self._default_key = default_key_path.read_bytes()
            logger.info("Loaded existing default encryption key")
        else:
            self._default_key = Fernet.generate_key()
            default_key_path.write_bytes(self._default_key)
            logger.info("Generated new default encryption key")

        return self._default_key

    def get_or_create_key(self, student_id: str) -> bytes:
        """
        Get or create an encryption key for a student.

        Args:
            student_id: Unique identifier for the student

        Returns:
            Encryption key bytes
        """
        # Use default key if configured
        if self.use_default_key:
            return self._get_or_create_default_key()

        if student_id in self._keys_cache:
            return self._keys_cache[student_id]

        key_path = self._get_key_path(student_id)

        if key_path.exists():
            key = key_path.read_bytes()
            logger.info(f"Loaded existing key for student {student_id}")
        else:
            key = Fernet.generate_key()
            key_path.write_bytes(key)
            logger.info(f"Generated new key for student {student_id}")

        self._keys_cache[student_id] = key
        return key

    def encrypt_file(self, input_path: Path, output_path: Path, student_id: str) -> bool:
        """
        Encrypt a file for a specific student.

        Args:
            input_path: Path to the file to encrypt
            output_path: Path where encrypted file will be saved
            student_id: Student identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            key = self.get_or_create_key(student_id)
            fernet = Fernet(key)

            plaintext = input_path.read_bytes()
            encrypted = fernet.encrypt(plaintext)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(encrypted)

            logger.info(f"Encrypted {input_path.name} for student {student_id}")
            return True

        except Exception as e:
            logger.error(f"Encryption failed for {input_path}: {e}")
            return False

    def decrypt_file(self, input_path: Path, output_path: Path, student_id: str) -> bool:
        """
        Decrypt a file for a specific student.

        Args:
            input_path: Path to the encrypted file
            output_path: Path where decrypted file will be saved
            student_id: Student identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            key = self.get_or_create_key(student_id)
            fernet = Fernet(key)

            encrypted = input_path.read_bytes()
            plaintext = fernet.decrypt(encrypted)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(plaintext)

            logger.info(f"Decrypted {input_path.name} for student {student_id}")
            return True

        except Exception as e:
            logger.error(f"Decryption failed for {input_path}: {e}")
            return False

    def export_keys(self, output_path: Path):
        """
        Export all student keys to a JSON file (for backup).
        WARNING: Keep this file secure!

        Args:
            output_path: Path to save the keys JSON file
        """
        keys_data = {}
        for key_file in self.keys_dir.glob("*.key"):
            student_id = key_file.stem
            key = key_file.read_bytes()
            keys_data[student_id] = key.decode('utf-8')

        output_path.write_text(json.dumps(keys_data, indent=2))
        logger.info(f"Exported {len(keys_data)} keys to {output_path}")
