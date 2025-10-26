#!/usr/bin/env python3
"""
Helper script to export secrets for GitHub Actions.
Converts files to formats suitable for GitHub Secrets.
"""
import base64
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.encryption import EncryptionManager


def export_file_as_base64(file_path: Path) -> str:
    """
    Export a file as base64-encoded string.

    Args:
        file_path: Path to the file

    Returns:
        Base64-encoded string (single line, no wrapping)
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, 'rb') as f:
        content = f.read()

    # Encode to base64 as a single line (no line breaks)
    b64_string = base64.b64encode(content).decode('utf-8')

    # Ensure no whitespace
    return b64_string.strip()


def export_json_file(file_path: Path) -> str:
    """
    Export a JSON file as a string.

    Args:
        file_path: Path to the JSON file

    Returns:
        JSON string
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, 'r') as f:
        content = f.read()

    return content


def export_encryption_keys() -> str:
    """
    Export all student encryption keys as JSON.

    Returns:
        JSON string with all keys
    """
    manager = EncryptionManager()
    keys_dir = manager.keys_dir

    if not keys_dir.exists():
        return "{}"

    keys_data = {}
    for key_file in keys_dir.glob("*.key"):
        student_id = key_file.stem
        key = key_file.read_bytes()
        # Encode key as base64 for JSON serialization
        keys_data[student_id] = base64.b64encode(key).decode('utf-8')

    return json.dumps(keys_data, indent=2)


def main():
    """Main function to export all secrets."""
    print("=" * 80)
    print("GITHUB SECRETS EXPORT HELPER")
    print("=" * 80)
    print("\nThis script will help you export files for GitHub Secrets.")
    print("Copy the output values to your GitHub repository secrets.\n")
    print("=" * 80)

    # 1. GOOGLE_CREDENTIALS
    print("\n1. GOOGLE_CREDENTIALS")
    print("-" * 80)
    credentials_path = Path("credentials.json")
    if credentials_path.exists():
        try:
            credentials = export_json_file(credentials_path)
            print("✓ Found credentials.json")
            print("\nCopy this to GitHub Secret 'GOOGLE_CREDENTIALS':")
            print("\n" + "─" * 80)
            print(credentials)
            print("─" * 80)
        except Exception as e:
            print(f"✗ Error reading credentials.json: {e}")
    else:
        print("✗ credentials.json not found")
        print("  Please complete Google Cloud setup first (see README.md)")

    # 2. GOOGLE_TOKEN (base64 encoded because it's binary)
    print("\n\n2. GOOGLE_TOKEN (optional, but recommended)")
    print("-" * 80)
    token_path = Path("token.json")
    if token_path.exists():
        try:
            token_b64 = export_file_as_base64(token_path)
            print("✓ Found token.json")
            print(f"  File size: {token_path.stat().st_size} bytes")
            print(f"  Base64 length: {len(token_b64)} characters")
            print("\nCopy this ENTIRE string to GitHub Secret 'GOOGLE_TOKEN':")
            print("(Copy from the first character to the last, no extra spaces)")
            print("\n" + "─" * 80)
            print(token_b64)
            print("─" * 80)
            print("\nIMPORTANT:")
            print("  - Copy the ENTIRE string above (all on one line)")
            print("  - Do NOT add any spaces or newlines before/after")
            print("  - The workflow will decode it automatically")
            print("\nTo verify the base64 is valid:")
            print(f"  echo '{token_b64[:50]}...' | base64 -d > /dev/null && echo 'Valid' || echo 'Invalid'")
        except Exception as e:
            print(f"✗ Error reading token.json: {e}")
    else:
        print("✗ token.json not found")
        print("  Authenticate first by running: python example_usage.py")
        print("  Then run this script again.")

    # 3. ENCRYPTION_KEYS
    print("\n\n3. ENCRYPTION_KEYS")
    print("-" * 80)
    try:
        keys_json = export_encryption_keys()
        keys_data = json.loads(keys_json)

        if keys_data:
            print(f"✓ Found {len(keys_data)} student encryption key(s)")
            print("\nCopy this to GitHub Secret 'ENCRYPTION_KEYS':")
            print("\n" + "─" * 80)
            print(keys_json)
            print("─" * 80)
            print("\nNote: Keys are base64-encoded for JSON serialization.")
        else:
            print("✗ No student keys found")
            print("  Keys will be generated when you process your first submissions")
    except Exception as e:
        print(f"✗ Error exporting encryption keys: {e}")

    # 4. COURSES_CONFIG (recommended - auto-discovers assignments)
    print("\n\n4. COURSES_CONFIG (recommended)")
    print("-" * 80)
    courses_path = Path("courses_config.json")
    if courses_path.exists():
        try:
            courses = export_json_file(courses_path)
            print("✓ Found courses_config.json")
            print("\nCopy this to GitHub Secret 'COURSES_CONFIG':")
            print("\n" + "─" * 80)
            print(courses)
            print("─" * 80)
            print("\nNote: This will auto-discover ALL assignments from these courses")
        except Exception as e:
            print(f"✗ Error reading courses_config.json: {e}")
    else:
        print("✗ courses_config.json not found")
        print("  Run: python scripts/setup_courses.py")
        print("  This will auto-discover assignments from selected courses")

    # 5. ASSIGNMENTS_CONFIG (old format, backwards compatibility)
    print("\n\n5. ASSIGNMENTS_CONFIG (alternative to COURSES_CONFIG)")
    print("-" * 80)
    assignments_path = Path("assignments_config.json")
    if assignments_path.exists():
        try:
            assignments = export_json_file(assignments_path)
            print("✓ Found assignments_config.json")
            print("\nCopy this to GitHub Secret 'ASSIGNMENTS_CONFIG':")
            print("\n" + "─" * 80)
            print(assignments)
            print("─" * 80)
            print("\nNote: This processes specific assignments only")
        except Exception as e:
            print(f"✗ Error reading assignments_config.json: {e}")
    else:
        print("✗ assignments_config.json not found")
        print("  Not needed if using COURSES_CONFIG (recommended)")

    # Summary
    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("\n1. Go to your GitHub repository")
    print("2. Navigate to: Settings → Secrets and variables → Actions")
    print("3. Click 'New repository secret'")
    print("4. Add each secret with the name and value shown above")
    print("\nRequired secrets:")
    print("  - GOOGLE_CREDENTIALS")
    print("  - ENCRYPTION_KEYS (after processing first submission)")
    print("\nOptional but recommended:")
    print("  - GOOGLE_TOKEN (avoids re-authentication)")
    print("  - ASSIGNMENTS_CONFIG (enables automatic downloads)")
    print("\n" + "=" * 80)

    # Save to file for convenience
    output_file = Path("github_secrets_export.txt")
    with open(output_file, 'w') as f:
        f.write("GITHUB SECRETS EXPORT\n")
        f.write("=" * 80 + "\n\n")

        if credentials_path.exists():
            f.write("GOOGLE_CREDENTIALS:\n")
            f.write(export_json_file(credentials_path) + "\n\n")

        if token_path.exists():
            f.write("GOOGLE_TOKEN (base64):\n")
            f.write(export_file_as_base64(token_path) + "\n\n")

        keys_json = export_encryption_keys()
        if json.loads(keys_json):
            f.write("ENCRYPTION_KEYS:\n")
            f.write(keys_json + "\n\n")

        if assignments_path.exists():
            f.write("ASSIGNMENTS_CONFIG:\n")
            f.write(export_json_file(assignments_path) + "\n\n")

    print(f"\n✓ All secrets also saved to: {output_file}")
    print("  (This file is gitignored for security)")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
