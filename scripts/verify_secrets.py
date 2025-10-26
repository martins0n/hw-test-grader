#!/usr/bin/env python3
"""
Verify that secrets are properly formatted before uploading to GitHub.
"""
import base64
import json
import sys
from pathlib import Path


def verify_credentials():
    """Verify credentials.json is valid JSON."""
    print("1. Checking credentials.json...")
    credentials_path = Path("credentials.json")

    if not credentials_path.exists():
        print("   ✗ credentials.json not found")
        return False

    try:
        with open(credentials_path) as f:
            data = json.load(f)

        if "installed" in data or "web" in data:
            print(f"   ✓ Valid JSON ({len(json.dumps(data))} characters)")
            return True
        else:
            print("   ✗ JSON doesn't look like OAuth credentials")
            return False

    except json.JSONDecodeError as e:
        print(f"   ✗ Invalid JSON: {e}")
        return False


def verify_token():
    """Verify token.json can be base64 encoded/decoded."""
    print("\n2. Checking token.json...")
    token_path = Path("token.json")

    if not token_path.exists():
        print("   ⚠ token.json not found (optional)")
        return True  # Not required

    try:
        # Read binary file
        with open(token_path, 'rb') as f:
            original = f.read()

        # Encode to base64
        encoded = base64.b64encode(original).decode('utf-8')

        # Verify no whitespace
        if encoded != encoded.strip():
            print("   ✗ Base64 has whitespace")
            return False

        # Try to decode back
        decoded = base64.b64decode(encoded)

        if decoded == original:
            print(f"   ✓ Valid base64 ({len(encoded)} characters)")
            print(f"   First 20 chars: {encoded[:20]}...")
            return True
        else:
            print("   ✗ Decode verification failed")
            return False

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def verify_encryption_keys():
    """Verify encryption keys can be exported."""
    print("\n3. Checking encryption keys...")
    keys_dir = Path("student_keys")

    if not keys_dir.exists():
        print("   ⚠ student_keys/ directory not found (will be created)")
        return True

    key_files = list(keys_dir.glob("*.key"))

    if not key_files:
        print("   ⚠ No student keys found yet (will be generated)")
        return True

    try:
        keys_data = {}
        for key_file in key_files:
            student_id = key_file.stem
            key = key_file.read_bytes()
            # Encode key as base64
            keys_data[student_id] = base64.b64encode(key).decode('utf-8')

        # Verify it's valid JSON
        json_str = json.dumps(keys_data)
        json.loads(json_str)  # Verify it can be parsed back

        print(f"   ✓ Found {len(keys_data)} student key(s)")
        print(f"   JSON size: {len(json_str)} characters")
        return True

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def verify_assignments_config():
    """Verify assignments config is valid JSON."""
    print("\n4. Checking assignments_config.json...")
    config_path = Path("assignments_config.json")

    if not config_path.exists():
        print("   ⚠ assignments_config.json not found (optional)")
        return True

    try:
        with open(config_path) as f:
            data = json.load(f)

        if not isinstance(data, list):
            print("   ✗ Should be a JSON array")
            return False

        for i, assignment in enumerate(data):
            if not isinstance(assignment, dict):
                print(f"   ✗ Item {i} is not an object")
                return False

            if "course_id" not in assignment or "coursework_id" not in assignment:
                print(f"   ✗ Item {i} missing required fields")
                return False

        print(f"   ✓ Valid JSON with {len(data)} assignment(s)")
        return True

    except json.JSONDecodeError as e:
        print(f"   ✗ Invalid JSON: {e}")
        return False


def main():
    """Run all verification checks."""
    print("=" * 80)
    print("GITHUB SECRETS VERIFICATION")
    print("=" * 80)
    print("\nVerifying all files before export...\n")

    results = []
    results.append(("GOOGLE_CREDENTIALS", verify_credentials()))
    results.append(("GOOGLE_TOKEN", verify_token()))
    results.append(("ENCRYPTION_KEYS", verify_encryption_keys()))
    results.append(("ASSIGNMENTS_CONFIG", verify_assignments_config()))

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    all_passed = True
    for secret_name, passed in results:
        status = "✓ READY" if passed else "✗ FAILED"
        print(f"{secret_name:25} {status}")
        if not passed:
            all_passed = False

    print("=" * 80)

    if all_passed:
        print("\n✓ All checks passed!")
        print("\nNext steps:")
        print("1. Run: python scripts/export_secrets.py")
        print("2. Copy the values to GitHub Secrets")
        print("3. Test the workflow")
        return 0
    else:
        print("\n✗ Some checks failed!")
        print("\nPlease fix the issues above before exporting secrets.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
