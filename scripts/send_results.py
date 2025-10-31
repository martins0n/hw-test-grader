#!/usr/bin/env python3
"""
Script to send grading results back to students via Google Classroom.
"""
import argparse
import json
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.classroom_client import ClassroomClient


def get_student_email_from_id(student_id: str) -> str:
    """
    Convert student_id back to email format.

    Args:
        student_id: Student identifier (email with @ and . replaced)

    Returns:
        Student email address
    """
    # Reverse the transformation: _at_ -> @, _ -> .
    # This is a simplification; you may need more robust logic
    email = student_id.replace('_at_', '@')
    # Be careful with underscores in email vs those added by transformation
    # For now, assume the format is consistent
    return email


def load_assignment_config_from_pr() -> dict:
    """
    Load assignment configuration from PR metadata.

    Returns:
        Configuration dictionary with course_id and coursework_id
    """
    # Check if we're in a PR context
    pr_number = os.getenv('GITHUB_PR_NUMBER')
    if not pr_number:
        return {}

    try:
        from github import Github
        token = os.getenv('GITHUB_TOKEN')
        repo_name = os.getenv('GITHUB_REPOSITORY')

        if not token or not repo_name:
            return {}

        g = Github(token)
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(int(pr_number))

        # Extract metadata from PR body
        body = pr.body or ""

        # Look for metadata comment
        import re
        metadata_match = re.search(r'<!-- METADATA\n(.*?)\n-->', body, re.DOTALL)
        if metadata_match:
            metadata_text = metadata_match.group(1)
            config = {}
            for line in metadata_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    config[key.strip()] = value.strip()

            if 'course_id' in config and 'coursework_id' in config:
                return {
                    'course_id': config['course_id'],
                    'coursework_id': config['coursework_id'],
                    'max_points': 100  # Default, will be overridden by test results
                }
    except Exception as e:
        print(f"Could not load config from PR: {e}")

    return {}

def load_assignment_config(assignment_id: str) -> dict:
    """
    Load configuration for an assignment from environment or file.

    Checks in order:
    1. Environment variable: ASSIGNMENT_{NAME}_COURSEWORK_ID
    2. courses_config.json file

    Args:
        assignment_id: Assignment identifier

    Returns:
        Configuration dictionary with course_id and coursework_id
    """
    # Try environment variables first (simplest)
    # Format: ASSIGNMENT_HOMEWORK_1_EXAMPLE_COURSEWORK_ID=123456789
    env_key = f"ASSIGNMENT_{assignment_id.upper().replace('-', '_')}_COURSEWORK_ID"
    coursework_id = os.getenv(env_key)

    if coursework_id:
        # Use first course from COURSE_IDS
        course_ids = os.getenv('COURSE_IDS', '').split(',')
        course_id = course_ids[0].strip() if course_ids else None

        if course_id:
            max_points = int(os.getenv(f"{env_key.replace('_COURSEWORK_ID', '_MAX_POINTS')}", "100"))
            print(f"Using environment config for {assignment_id}")
            return {
                'course_id': course_id,
                'coursework_id': coursework_id,
                'max_points': max_points
            }

    # Try config file as fallback
    config_path = Path('courses_config.json')
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)

        # Look for assignment in config
        for course in config.get('courses', []):
            for assignment in course.get('assignments', []):
                if assignment.get('name') == assignment_id or assignment.get('id') == assignment_id:
                    return {
                        'course_id': course.get('id'),
                        'coursework_id': assignment.get('id'),
                        'max_points': assignment.get('maxPoints')
                    }

    return {}


def send_results(student_id: str, assignment_id: str, report_path: str, submit_grade: bool = True):
    """
    Send grading results to student via Google Classroom.

    Args:
        student_id: Student identifier
        assignment_id: Assignment identifier
        report_path: Path to the grading report JSON
        submit_grade: Whether to submit grade to Google Classroom (default: True)
    """
    report_file = Path(report_path)

    if not report_file.exists():
        print(f"Report file not found: {report_path}")
        return

    with open(report_file) as f:
        report = json.load(f)

    print(f"\nProcessing results for Student {student_id}, Assignment {assignment_id}")
    print("=" * 60)

    # Display results
    if "error" in report:
        print(f"Grading Error: {report['error']}")
        grade_value = 0
    else:
        # Support both legacy and new format
        if 'test_case_results' in report:
            # New format
            grade_value = report.get('earned_points', 0)
            total_points = report.get('total_points', 100)
            print(f"Score: {grade_value}/{total_points} ({report.get('score', 0):.2f}%)")
            print(f"Passed: {report.get('passed_cases', 0)}/{report.get('total_test_cases', 0)}")
        else:
            # Legacy format - convert percentage to points
            grade_value = report.get('score', 0)
            print(f"Score: {grade_value}%")
            print(f"Matches: {report.get('matches', 0)}/{report.get('total_expected', 0)}")

    # Submit to Google Classroom if enabled
    if submit_grade and os.getenv('GOOGLE_CREDENTIALS'):
        try:
            print("\nSubmitting grade to Google Classroom...")

            # Try to load assignment configuration from PR metadata first
            assignment_config = load_assignment_config_from_pr()

            # Fall back to environment/file config
            if not assignment_config:
                assignment_config = load_assignment_config(assignment_id)

            if not assignment_config:
                print(f"⚠️  No configuration found for assignment '{assignment_id}'")
                print("")
                print("To enable Google Classroom grade submission, set environment variables:")
                print(f"  ASSIGNMENT_{assignment_id.upper().replace('-', '_')}_COURSEWORK_ID=<coursework_id>")
                print(f"  ASSIGNMENT_{assignment_id.upper().replace('-', '_')}_MAX_POINTS=100")
                print("")
                print("Or create courses_config.json - see docs/GOOGLE_CLASSROOM_SETUP.md")
                print("")
                print("Skipping Google Classroom submission")
                return

            course_id = assignment_config.get('course_id')
            coursework_id = assignment_config.get('coursework_id')
            max_points = assignment_config.get('max_points', 100)

            if not course_id or not coursework_id:
                print("Error: Missing course_id or coursework_id in configuration")
                return

            # Initialize Classroom client
            client = ClassroomClient()

            # Convert student_id back to email
            student_email = get_student_email_from_id(student_id)

            # Find submission
            submission_id = client.find_submission_for_student(
                course_id, coursework_id, student_email
            )

            if not submission_id:
                print(f"Warning: Could not find submission for {student_email}")
                print("Skipping grade submission")
                return

            # Submit grade (as draft for teacher approval)
            success = client.submit_grade(
                course_id=course_id,
                coursework_id=coursework_id,
                submission_id=submission_id,
                grade=grade_value,
                max_points=max_points
            )

            if success:
                print("✓ Draft grade submitted successfully to Google Classroom")
                print("  Note: Grade is pending teacher approval")
            else:
                print("✗ Failed to submit grade to Google Classroom")

        except Exception as e:
            print(f"Error submitting to Google Classroom: {e}")
            import traceback
            traceback.print_exc()
    else:
        if not submit_grade:
            print("\nGrade submission disabled")
        else:
            print("\nGOOGLE_CREDENTIALS not found, skipping Google Classroom submission")
        print("Results are available in the CI/CD artifacts")


def main():
    parser = argparse.ArgumentParser(description="Send grading results to student")
    parser.add_argument("--student-id", required=True, help="Student ID")
    parser.add_argument("--assignment-id", required=True, help="Assignment ID")
    parser.add_argument("--report", required=True, help="Path to grading report JSON")
    parser.add_argument(
        "--no-submit",
        action="store_true",
        help="Don't submit grade to Google Classroom"
    )

    args = parser.parse_args()

    try:
        send_results(
            args.student_id,
            args.assignment_id,
            args.report,
            submit_grade=not args.no_submit
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
