"""Deterministic encryption module for student submissions."""
import os
import base64
import binascii
import hashlib
from pathlib import Path
from typing import Dict, Optional, Union

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import logging
import json

logger = logging.getLogger(__name__)


class EncryptionManager:
    """Manages encryption and decryption of student files."""

    VERSION_PREFIX = b"HWG2"
    NONCE_SIZE = 12

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
        self._default_key: Optional[bytes] = None

    # ------------------------------------------------------------------
    # Key management helpers
    # ------------------------------------------------------------------
    def _get_key_path(self, student_id: str) -> Path:
        """Get the path to a student's key file."""
        return self.keys_dir / f"{student_id}.key"

    @staticmethod
    def _encode_key_material(key_bytes: bytes) -> bytes:
        """Encode raw key bytes to a storable representation."""
        return base64.urlsafe_b64encode(key_bytes)

    @staticmethod
    def _decode_key_material(raw_key: Union[bytes, str]) -> bytes:
        """Decode stored key material to raw bytes."""
        if isinstance(raw_key, str):
            raw_key = raw_key.encode('utf-8')

        key_candidate = raw_key.strip()
        if not key_candidate:
            raise ValueError("Empty key material")

        # First attempt base64 decoding (legacy Fernet keys)
        try:
            decoded = base64.urlsafe_b64decode(key_candidate)
            if len(decoded) in (16, 24, 32):
                return decoded
        except (binascii.Error, ValueError):
            pass

        # Fall back to raw bytes if length matches AES key sizes
        if len(key_candidate) in (16, 24, 32):
            return key_candidate

        raise ValueError("Key material must be 16, 24, or 32 bytes (or base64-encoded)")

    def _load_key_from_file(self, key_path: Path) -> bytes:
        raw = key_path.read_bytes()
        return self._decode_key_material(raw)

    def _store_key_to_file(self, key_path: Path, key_bytes: bytes):
        key_path.write_bytes(self._encode_key_material(key_bytes))

    def _get_or_create_default_key(self) -> bytes:
        """Get or create the default encryption key."""
        if self._default_key:
            return self._default_key

        default_key_path = self.keys_dir / "default.key"

        # Prefer key supplied via environment (matches CI secrets)
        default_key_env = os.getenv('DEFAULT_ENCRYPTION_KEY')
        if default_key_env:
            try:
                key_bytes = self._decode_key_material(default_key_env)
            except ValueError as exc:
                logger.error(f"Invalid DEFAULT_ENCRYPTION_KEY: {exc}")
            else:
                self._default_key = key_bytes
                try:
                    self._store_key_to_file(default_key_path, key_bytes)
                except Exception as file_err:
                    logger.warning(f"Failed to persist default key file: {file_err}")
                logger.info("Loaded default encryption key from environment")
                return self._default_key

        if default_key_path.exists():
            try:
                self._default_key = self._load_key_from_file(default_key_path)
                logger.info("Loaded existing default encryption key")
            except ValueError as exc:
                logger.error(f"Existing default key invalid ({exc}); generating new key")
                self._default_key = AESGCM.generate_key(bit_length=256)
                self._store_key_to_file(default_key_path, self._default_key)
        else:
            self._default_key = AESGCM.generate_key(bit_length=256)
            self._store_key_to_file(default_key_path, self._default_key)
            logger.info("Generated new default encryption key")

        return self._default_key

    def get_or_create_key(self, student_id: str) -> bytes:
        """
        Get or create an encryption key for a student.

        Args:
            student_id: Unique identifier for the student

        Returns:
            Raw encryption key bytes
        """
        # Use default key if configured
        if self.use_default_key:
            return self._get_or_create_default_key()

        if student_id in self._keys_cache:
            return self._keys_cache[student_id]

        key_path = self._get_key_path(student_id)

        if key_path.exists():
            try:
                key_bytes = self._load_key_from_file(key_path)
                logger.info(f"Loaded existing key for student {student_id}")
            except ValueError as exc:
                logger.error(f"Stored key for {student_id} invalid ({exc}); regenerating")
                key_bytes = AESGCM.generate_key(bit_length=256)
                self._store_key_to_file(key_path, key_bytes)
        else:
            key_bytes = AESGCM.generate_key(bit_length=256)
            self._store_key_to_file(key_path, key_bytes)
            logger.info(f"Generated new key for student {student_id}")

        self._keys_cache[student_id] = key_bytes
        return key_bytes

    # ------------------------------------------------------------------
    # Encryption / decryption
    # ------------------------------------------------------------------
    def _associated_data(self, student_id: str) -> bytes:
        """Associated data ensures ciphertext is bound to the student."""
        return f"homeworkgrader:{student_id}".encode('utf-8')

    def _to_fernet_key(self, key_bytes: bytes) -> bytes:
        """Convert raw key bytes to a Fernet-compatible base64 key."""
        return base64.urlsafe_b64encode(key_bytes)

    def encrypt_file(self, input_path: Path, output_path: Path, student_id: str) -> bool:
        """Encrypt a file deterministically for a specific student."""
        try:
            key = self.get_or_create_key(student_id)
            plaintext = input_path.read_bytes()

            # Derive a deterministic nonce from the student ID and plaintext
            nonce = hashlib.blake2s(
                student_id.encode('utf-8') + plaintext,
                digest_size=self.NONCE_SIZE
            ).digest()

            aesgcm = AESGCM(key)
            ciphertext = aesgcm.encrypt(nonce, plaintext, self._associated_data(student_id))
            payload = self.VERSION_PREFIX + nonce + ciphertext

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(payload)

            logger.info(
                "Encrypted %s for student %s (deterministic ciphertext, %d bytes)",
                input_path.name,
                student_id,
                len(payload)
            )
            return True

        except Exception as e:
            logger.error(f"Encryption failed for {input_path}: {e}")
            return False

    def _decrypt_new_format(self, data: bytes, key: bytes, student_id: str) -> bytes:
        if not data.startswith(self.VERSION_PREFIX):
            raise ValueError("Unsupported ciphertext format")

        header_len = len(self.VERSION_PREFIX)
        if len(data) <= header_len + self.NONCE_SIZE:
            raise ValueError("Ciphertext truncated")

        nonce = data[header_len:header_len + self.NONCE_SIZE]
        ciphertext = data[header_len + self.NONCE_SIZE:]

        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, self._associated_data(student_id))

    def _decrypt_legacy(self, data: bytes, key: bytes) -> bytes:
        # Legacy Fernet ciphertext support
        fernet_key = self._to_fernet_key(key)
        fernet = Fernet(fernet_key)
        return fernet.decrypt(data)

    def decrypt_file(self, input_path: Path, output_path: Path, student_id: str) -> bool:
        """Decrypt a file for a specific student (supports legacy format)."""
        try:
            key = self.get_or_create_key(student_id)
            encrypted = input_path.read_bytes()

            try:
                plaintext = self._decrypt_new_format(encrypted, key, student_id)
            except Exception:
                # Fallback to legacy Fernet ciphertexts
                plaintext = self._decrypt_legacy(encrypted, key)

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
        """
        keys_data = {}
        for key_file in self.keys_dir.glob("*.key"):
            student_id = key_file.stem
            key = key_file.read_bytes()
            keys_data[student_id] = key.decode('utf-8')

        output_path.write_text(json.dumps(keys_data, indent=2))
        logger.info(f"Exported {len(keys_data)} keys to {output_path}")
