#!/usr/bin/env python3
"""
Script to decrypt student submission files in CI/CD pipeline.
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.encryption import EncryptionManager


def load_encryption_keys():
    """
    Load encryption keys from environment variable.
    Returns None if using default key instead of per-student keys.
    """
    import base64

    keys_json = os.getenv('ENCRYPTION_KEYS')
    if not keys_json:
        print("ENCRYPTION_KEYS not set, will use default key")
        return None

    try:
        keys_data = json.loads(keys_json)

        # Decode base64-encoded keys
        decoded_keys = {}
        for student_id, key_b64 in keys_data.items():
            decoded_keys[student_id] = base64.b64decode(key_b64).decode('utf-8')

        return decoded_keys
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Failed to parse ENCRYPTION_KEYS: {e}", file=sys.stderr)
        return None


def decrypt_submissions(student_id: str, assignment_id: str):
    """
    Decrypt submission files for a student.

    Args:
        student_id: Student identifier (email-based)
        assignment_id: Assignment identifier (name-based)
    """
    # Load keys
    keys_data = load_encryption_keys()

    # Set up encryption manager
    keys_dir = Path("student_keys")
    keys_dir.mkdir(exist_ok=True)

    if keys_data is None:
        # Use default encryption key
        print("Using default encryption key for all students")

        # Check if default key secret is provided
        default_key_b64 = os.getenv('DEFAULT_ENCRYPTION_KEY')
        if default_key_b64:
            import base64
            # Strip any whitespace that might have been added
            default_key_b64 = default_key_b64.strip()


            default_key = base64.b64decode(default_key_b64)


            default_key_path = keys_dir / "default.key"
            default_key_path.write_bytes(default_key)
            print("Loaded default key from environment")

        encryption_manager = EncryptionManager(keys_dir, use_default_key=True)
    else:
        # Use per-student keys
        if student_id not in keys_data:
            raise ValueError(f"No encryption key found for student {student_id}")

        # Write student's key to file
        key_path = keys_dir / f"{student_id}.key"
        key_path.write_text(keys_data[student_id])

        encryption_manager = EncryptionManager(keys_dir, use_default_key=False)

    # Find encrypted files (assignment_id is now the assignment name)
    submissions_dir = Path("submissions") / student_id / assignment_id
    decrypted_dir = Path("decrypted_submissions") / student_id / assignment_id
    decrypted_dir.mkdir(parents=True, exist_ok=True)

    if not submissions_dir.exists():
        print(f"No submissions found at {submissions_dir}")
        return

    encrypted_files = list(submissions_dir.glob("*.enc"))
    print(f"Found {len(encrypted_files)} encrypted files")

    for encrypted_file in encrypted_files:
        # Remove .enc extension for decrypted file
        decrypted_name = encrypted_file.name[:-4]
        decrypted_path = decrypted_dir / decrypted_name

        try:
            # Get the key
            key = encryption_manager.get_or_create_key(student_id)
            from cryptography.fernet import Fernet
            fernet = Fernet(key)

            # Decrypt
            encrypted_data = encrypted_file.read_bytes()
            print(f"Encrypted file size: {len(encrypted_data)} bytes")
            print(f"Key length: {len(key)} bytes")

            plaintext = fernet.decrypt(encrypted_data)

            # Save decrypted file
            decrypted_path.parent.mkdir(parents=True, exist_ok=True)
            decrypted_path.write_bytes(plaintext)

            print(f"✓ Decrypted: {decrypted_name}")
        except Exception as e:
            print(f"✗ Failed to decrypt: {encrypted_file.name}")
            print(f"Error details: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    print(f"\nAll files decrypted to: {decrypted_dir}")


def main():
    parser = argparse.ArgumentParser(description="Decrypt student submission files")
    parser.add_argument("--student-id", required=True, help="Student ID")
    parser.add_argument("--assignment-id", required=True, help="Assignment ID")

    args = parser.parse_args()

    try:
        decrypt_submissions(args.student_id, args.assignment_id)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
