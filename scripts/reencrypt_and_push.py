#!/usr/bin/env python3
"""
Simple script to re-encrypt existing submissions with current key and push to GitHub.
This fixes the key mismatch issue.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.encryption import EncryptionManager

def main():
    # Setup encryption with default key
    encryption = EncryptionManager(use_default_key=True)

    # Find unencrypted submissions
    submissions_dir = Path("submissions")

    if not submissions_dir.exists():
        print("No submissions directory found")
        return

    # Process each student/assignment
    for student_dir in submissions_dir.iterdir():
        if not student_dir.is_dir():
            continue

        student_id = student_dir.name
        print(f"\nProcessing student: {student_id}")

        for assignment_dir in student_dir.iterdir():
            if not assignment_dir.is_dir():
                continue

            assignment_id = assignment_dir.name
            print(f"  Assignment: {assignment_id}")

            # Find .ipynb files
            for notebook in assignment_dir.glob("*.ipynb"):
                encrypted_path = notebook.parent / f"{notebook.name}.enc"

                # Encrypt
                success = encryption.encrypt_file(
                    notebook,
                    encrypted_path,
                    student_id
                )

                if success:
                    print(f"    ✓ Encrypted: {notebook.name}")
                else:
                    print(f"    ✗ Failed: {notebook.name}")

    print("\n" + "="*80)
    print("Re-encryption complete!")
    print("="*80)
    print("\nNext steps:")
    print("1. Commit and push the re-encrypted files:")
    print("   git add submissions/")
    print("   git commit -m 'Re-encrypt submissions with current key'")
    print("   git push")
    print("\n2. The GitHub Actions workflow will now be able to decrypt the files")

if __name__ == "__main__":
    main()
