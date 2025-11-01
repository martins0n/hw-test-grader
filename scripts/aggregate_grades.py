#!/usr/bin/env python3
"""
Aggregate grades from individual grading reports into CSV files for bulk submission.

This script processes all grading report JSON files and creates one CSV file per
assignment containing all students' grades.
"""

import argparse
import json
import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def get_student_email_from_id(student_id: str) -> str:
    """
    Convert student_id back to email format.

    Args:
        student_id: Student identifier (email with @ and . replaced)

    Returns:
        Student email address
    """
    # Reverse the transformation done in classroom_client.py:
    # email.replace('@', '_at_').replace('.', '_')
    email = student_id.replace('_at_', '@')
    email = email.replace('_', '.')
    return email


def extract_grade_from_report(report: dict) -> tuple:
    """
    Extract grade information from a grading report.

    Args:
        report: Grading report dictionary

    Returns:
        Tuple of (grade_value, max_points)
    """
    if "error" in report:
        return (0, 100)

    # Support both legacy and new format
    if 'test_case_results' in report:
        # New format with per-case grading
        grade_value = report.get('earned_points', 0)
        max_points = report.get('total_points', 100)
    else:
        # Legacy format (percentage)
        grade_value = report.get('score', 0)
        max_points = 100

    return (grade_value, max_points)


def parse_artifact_name(artifact_name: str) -> tuple:
    """
    Parse artifact name to extract student_id and assignment_id.

    Expected format: grading-report-{student_id}-{assignment_id}

    Args:
        artifact_name: Name of the artifact directory

    Returns:
        Tuple of (student_id, assignment_id) or (None, None) if parsing fails
    """
    if not artifact_name.startswith('grading-report-'):
        return (None, None)

    # Remove 'grading-report-' prefix
    remainder = artifact_name[15:]

    # Split by last occurrence of '-' to separate student_id and assignment_id
    # (student_id may contain dashes)
    parts = remainder.rsplit('-', 1)
    if len(parts) != 2:
        return (None, None)

    return (parts[0], parts[1])


def aggregate_grades(artifacts_dir: str, output_dir: str, assignment_filter: str = None):
    """
    Aggregate all grading reports into CSV files by assignment.

    Args:
        artifacts_dir: Directory containing downloaded artifacts
        output_dir: Directory to write aggregated CSV files
        assignment_filter: Optional assignment ID to filter by
    """
    artifacts_path = Path(artifacts_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Group grades by assignment
    grades_by_assignment = defaultdict(list)

    # Process each artifact directory
    for artifact_dir in artifacts_path.iterdir():
        if not artifact_dir.is_dir():
            continue

        # Parse artifact name to get student_id and assignment_id
        student_id, assignment_id = parse_artifact_name(artifact_dir.name)

        if not student_id or not assignment_id:
            print(f"⚠️  Skipping {artifact_dir.name}: couldn't parse artifact name")
            continue

        # Filter by assignment if specified
        if assignment_filter and assignment_id != assignment_filter:
            continue

        # Find the grade_report.json file
        report_file = artifact_dir / 'grade_report.json'
        if not report_file.exists():
            print(f"⚠️  Skipping {artifact_dir.name}: no grade_report.json found")
            continue

        # Read the report
        try:
            with open(report_file) as f:
                report = json.load(f)
        except Exception as e:
            print(f"❌ Error reading {report_file}: {e}")
            continue

        # Extract grade
        grade_value, max_points = extract_grade_from_report(report)
        student_email = get_student_email_from_id(student_id)

        # Add to assignment group
        grades_by_assignment[assignment_id].append({
            'email': student_email,
            'grade': grade_value,
            'max_points': max_points,
            'student_id': student_id
        })

        print(f"✓ Processed {student_email} for {assignment_id}: {grade_value}/{max_points}")

    # Write CSV files
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    total_students = 0

    for assignment_id, grades in grades_by_assignment.items():
        csv_file = output_path / f'grades_{assignment_id}.csv'

        # Sort by email for consistency
        grades.sort(key=lambda x: x['email'])

        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow(['Student Email', 'Grade', 'Max Points', 'Timestamp', 'Assignment'])

            # Write grades
            for grade_entry in grades:
                writer.writerow([
                    grade_entry['email'],
                    grade_entry['grade'],
                    grade_entry['max_points'],
                    timestamp,
                    assignment_id
                ])

        print(f"\n📝 Created {csv_file} with {len(grades)} students")
        total_students += len(grades)

    # Summary
    print("\n" + "=" * 60)
    print(f"✅ Aggregation complete!")
    print(f"   Assignments: {len(grades_by_assignment)}")
    print(f"   Total students: {total_students}")
    print(f"   Output directory: {output_path}")
    print("=" * 60)

    return len(grades_by_assignment)


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate grading reports into CSV files"
    )
    parser.add_argument(
        '--artifacts-dir',
        required=True,
        help='Directory containing downloaded artifacts'
    )
    parser.add_argument(
        '--output-dir',
        required=True,
        help='Directory to write aggregated CSV files'
    )
    parser.add_argument(
        '--assignment-id',
        help='Optional: Filter by specific assignment ID'
    )

    args = parser.parse_args()

    try:
        count = aggregate_grades(
            args.artifacts_dir,
            args.output_dir,
            args.assignment_id
        )

        if count == 0:
            print("\n⚠️  No grades found to aggregate")
            print("   Make sure grading workflows have run and created artifacts")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
