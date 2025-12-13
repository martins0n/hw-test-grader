#!/usr/bin/env python3
"""
Test script for generate_marks_csv.py

This script allows testing the CSV generation locally before merging the workflow.
It creates mock PR data to verify the logic works correctly.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the functions we want to test
from generate_marks_csv import parse_pr_title, extract_score_from_comment, get_student_email_from_id, extract_student_name_from_pr


def test_extract_student_name_from_pr():
    """Test student name extraction from PR body."""
    print("Testing student name extraction from PR body...")
    
    # Create a simple mock PR object with body attribute
    class MockPR:
        def __init__(self, body):
            self.body = body
    
    test_cases = [
        ("**Student Name:** John Doe\n**Student:** test@example.com", "John Doe"),
        ("Student Name: Jane Smith\nAssignment: HW1", "Jane Smith"),
        ("**Name:** Bob Johnson\n", "Bob Johnson"),
        ("Name: Alice Williams\nOther info", "Alice Williams"),
        ("No name here\nJust other content", None),
        (None, None),
    ]
    
    passed = 0
    failed = 0
    
    for body, expected in test_cases:
        pr = MockPR(body)
        result = extract_student_name_from_pr(pr)
        if result == expected:
            print(f"  ✓ Extracted name: '{result}'")
            passed += 1
        else:
            print(f"  ✗ Expected '{expected}', got '{result}'")
            failed += 1
    
    print(f"\nName Extraction: {passed} passed, {failed} failed\n")
    return failed == 0


def test_get_student_email_from_id():
    """Test student ID to email conversion."""
    print("Testing student ID to email conversion...")
    
    test_cases = [
        ("ayumikhaylyuk_at_gmail_com", "ayumikhaylyuk@gmail.com"),
        ("john_doe_at_example_com", "john.doe@example.com"),
        ("student123_at_university_edu", "student123@university.edu"),
        ("test_user_at_domain_co_uk", "test.user@domain.co.uk"),
    ]
    
    passed = 0
    failed = 0
    
    for student_id, expected in test_cases:
        result = get_student_email_from_id(student_id)
        if result == expected:
            print(f"  ✓ '{student_id}' -> '{result}'")
            passed += 1
        else:
            print(f"  ✗ '{student_id}' -> Expected '{expected}', got '{result}'")
            failed += 1
    
    print(f"\nEmail Conversion: {passed} passed, {failed} failed\n")
    return failed == 0


def test_parse_pr_title():
    """Test PR title parsing."""
    print("Testing PR title parsing...")
    
    test_cases = [
        ("Submission: ayumikhaylyuk_at_gmail_com - Homework-4", 
         ("ayumikhaylyuk_at_gmail_com", "Homework-4")),
        ("Submission: john.doe@example.com - Lab-Assignment-2",
         ("john.doe@example.com", "Lab-Assignment-2")),
        ("Submission: student123@university.edu - Final-Project",
         ("student123@university.edu", "Final-Project")),
        ("Not a submission PR", None),
        ("submission: lowercase@test.com - HW1", 
         ("lowercase@test.com", "HW1")),  # Case insensitive
    ]
    
    passed = 0
    failed = 0
    
    for title, expected in test_cases:
        result = parse_pr_title(title)
        if result == expected:
            print(f"  ✓ '{title}' -> {result}")
            passed += 1
        else:
            print(f"  ✗ '{title}' -> Expected {expected}, got {result}")
            failed += 1
    
    print(f"\nPR Title Parsing: {passed} passed, {failed} failed\n")
    return failed == 0


def test_extract_score_from_comment():
    """Test score extraction from comments."""
    print("Testing score extraction from comments...")
    
    test_cases = [
        ("Score: 85/100", 85.0),
        ("Score: 42.5 / 50", 85.0),
        ("Score: 85.5%", 85.5),
        ("Grade: 92%", 92.0),
        ("earned_points: 85\ntotal_points: 100", 85.0),
        ("The final score is 88%", 88.0),
        ("Your grade for this assignment: 75%", 75.0),
        ("## 🤖 Grading Results\n\nScore: 90/100 (90.00%)", 90.0),
        ("No score here", None),
    ]
    
    passed = 0
    failed = 0
    
    for comment, expected in test_cases:
        result = extract_score_from_comment(comment)
        if result == expected:
            print(f"  ✓ '{comment[:50]}...' -> {result}")
            passed += 1
        else:
            print(f"  ✗ '{comment[:50]}...' -> Expected {expected}, got {result}")
            failed += 1
    
    print(f"\nScore Extraction: {passed} passed, {failed} failed\n")
    return failed == 0


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing generate_marks_csv.py functions")
    print("=" * 60)
    print()
    
    results = []
    results.append(test_extract_student_name_from_pr())
    results.append(test_get_student_email_from_id())
    results.append(test_parse_pr_title())
    results.append(test_extract_score_from_comment())
    
    print("=" * 60)
    if all(results):
        print("✅ All tests passed!")
        print("=" * 60)
        print()
        print("The script logic is working correctly.")
        print("To test with real PRs, you need to:")
        print("  1. Merge this PR to the default branch")
        print("  2. Run: gh workflow run 'Generate Marks CSV'")
        print("  3. Or wait for the scheduled run (Sundays at 8 AM UTC)")
        return 0
    else:
        print("❌ Some tests failed!")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
