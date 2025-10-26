#!/usr/bin/env python3
"""
Script to send grading results back to students.
Currently supports console output; can be extended for email/Google Classroom.
"""
import argparse
import json
import sys
from pathlib import Path


def send_results(student_id: str, assignment_id: str, report_path: str):
    """
    Send grading results to student.

    Args:
        student_id: Student identifier
        assignment_id: Assignment identifier
        report_path: Path to the grading report JSON
    """
    report_file = Path(report_path)

    if not report_file.exists():
        print(f"Report file not found: {report_path}")
        return

    with open(report_file) as f:
        report = json.load(f)

    print(f"\nSending results for Student {student_id}, Assignment {assignment_id}")
    print("=" * 60)

    if "error" in report:
        print(f"Grading Error: {report['error']}")
    else:
        print(f"Score: {report.get('score', 0)}%")
        print(f"Matches: {report.get('matches', 0)}/{report.get('total_expected', 0)}")

        if report.get('mismatches'):
            print(f"\nMismatches: {len(report['mismatches'])}")

        if report.get('missing'):
            print(f"Missing outputs: {len(report['missing'])}")

        if report.get('extra'):
            print(f"Extra outputs: {len(report['extra'])}")

    # TODO: Implement actual email sending or Google Classroom API integration
    print("\n[TODO] Implement email/Google Classroom delivery")
    print("For now, results are available in the CI/CD artifacts")


def main():
    parser = argparse.ArgumentParser(description="Send grading results to student")
    parser.add_argument("--student-id", required=True, help="Student ID")
    parser.add_argument("--assignment-id", required=True, help="Assignment ID")
    parser.add_argument("--report", required=True, help="Path to grading report JSON")

    args = parser.parse_args()

    try:
        send_results(args.student_id, args.assignment_id, args.report)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
