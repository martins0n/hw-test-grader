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
    """Load encryption keys from environment variable."""
    import base64

    keys_json = os.getenv('ENCRYPTION_KEYS')
    if not keys_json:
        raise ValueError("ENCRYPTION_KEYS environment variable not set")

    keys_data = json.loads(keys_json)

    # Decode base64-encoded keys
    decoded_keys = {}
    for student_id, key_b64 in keys_data.items():
        decoded_keys[student_id] = base64.b64decode(key_b64).decode('utf-8')

    return decoded_keys


def decrypt_submissions(student_id: str, assignment_id: str):
    """
    Decrypt submission files for a student.

    Args:
        student_id: Student identifier (email-based)
        assignment_id: Assignment identifier (name-based)
    """
    # Load keys
    keys_data = load_encryption_keys()

    if student_id not in keys_data:
        raise ValueError(f"No encryption key found for student {student_id}")

    # Set up encryption manager
    keys_dir = Path("student_keys")
    keys_dir.mkdir(exist_ok=True)

    # Write student's key to file
    key_path = keys_dir / f"{student_id}.key"
    key_path.write_text(keys_data[student_id])

    encryption_manager = EncryptionManager(keys_dir)

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

        success = encryption_manager.decrypt_file(
            encrypted_file,
            decrypted_path,
            student_id
        )

        if success:
            print(f"✓ Decrypted: {decrypted_name}")
        else:
            print(f"✗ Failed to decrypt: {encrypted_file.name}")
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
