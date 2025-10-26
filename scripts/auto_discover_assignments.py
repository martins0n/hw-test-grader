#!/usr/bin/env python3
"""
Automatically discover all assignments from Google Classroom and generate config.
"""
import sys
import json
from pathlib import Path
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.classroom_client import ClassroomClient


def discover_all_assignments(
    include_archived: bool = False,
    state_filter: List[str] = None
) -> List[Dict]:
    """
    Discover all assignments from all courses.

    Args:
        include_archived: Include archived courses
        state_filter: List of assignment states to include (e.g., ['PUBLISHED'])

    Returns:
        List of assignment configurations
    """
    if state_filter is None:
        state_filter = ['PUBLISHED']

    client = ClassroomClient()
    assignments_config = []

    print("=" * 80)
    print("AUTO-DISCOVERING ASSIGNMENTS FROM GOOGLE CLASSROOM")
    print("=" * 80)

    # Get all courses
    print("\nStep 1: Fetching all courses...")
    courses = client.list_courses()

    if not courses:
        print("No courses found.")
        return []

    print(f"Found {len(courses)} course(s)")

    # Filter courses
    active_courses = []
    for course in courses:
        course_state = course.get('courseState', 'UNKNOWN')

        if course_state == 'ARCHIVED' and not include_archived:
            print(f"  Skipping archived: {course.get('name', 'Unnamed')}")
            continue

        active_courses.append(course)

    print(f"Processing {len(active_courses)} active course(s)")

    # Get assignments from each course
    print("\nStep 2: Fetching assignments from each course...")

    total_assignments = 0
    for course in active_courses:
        course_id = course['id']
        course_name = course.get('name', 'Unnamed Course')
        section = course.get('section', '')

        print(f"\n  Course: {course_name}")
        if section:
            print(f"  Section: {section}")

        try:
            coursework = client.list_course_work(course_id)

            if not coursework:
                print(f"    No assignments found")
                continue

            # Filter by state
            filtered_work = [
                w for w in coursework
                if w.get('state', 'UNKNOWN') in state_filter
            ]

            print(f"    Found {len(filtered_work)} assignment(s) (state: {', '.join(state_filter)})")

            for work in filtered_work:
                work_title = work.get('title', 'Untitled')
                work_id = work['id']

                # Build assignment name
                assignment_name = work_title
                if section:
                    assignment_name = f"{section} - {work_title}"

                config_entry = {
                    "name": assignment_name,
                    "course_id": course_id,
                    "coursework_id": work_id
                }

                assignments_config.append(config_entry)
                total_assignments += 1

                print(f"      ✓ {work_title}")

        except Exception as e:
            print(f"    Error fetching coursework: {e}")
            continue

    print("\n" + "=" * 80)
    print(f"DISCOVERY COMPLETE: {total_assignments} assignment(s) found")
    print("=" * 80)

    return assignments_config


def save_config(assignments: List[Dict], output_path: Path):
    """Save assignments config to file."""
    with open(output_path, 'w') as f:
        json.dump(assignments, f, indent=2)

    print(f"\n✓ Configuration saved to: {output_path}")
    print(f"  Total assignments: {len(assignments)}")


def display_config(assignments: List[Dict]):
    """Display the generated config."""
    print("\n" + "=" * 80)
    print("GENERATED CONFIGURATION")
    print("=" * 80)
    print("\n" + json.dumps(assignments, indent=2))
    print("\n" + "=" * 80)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Auto-discover all assignments from Google Classroom"
    )
    parser.add_argument(
        '--include-archived',
        action='store_true',
        help='Include archived courses'
    )
    parser.add_argument(
        '--state',
        nargs='+',
        default=['PUBLISHED'],
        choices=['PUBLISHED', 'DRAFT', 'DELETED'],
        help='Assignment states to include (default: PUBLISHED)'
    )
    parser.add_argument(
        '--output',
        default='assignments_config.json',
        help='Output file path (default: assignments_config.json)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be generated without saving'
    )

    args = parser.parse_args()

    try:
        # Discover assignments
        assignments = discover_all_assignments(
            include_archived=args.include_archived,
            state_filter=args.state
        )

        if not assignments:
            print("\nNo assignments found with the specified criteria.")
            print("\nTips:")
            print("  - Use --include-archived to include archived courses")
            print("  - Use --state DRAFT to include draft assignments")
            return 1

        # Display the config
        display_config(assignments)

        if args.dry_run:
            print("\n[DRY RUN] Configuration not saved (remove --dry-run to save)")
        else:
            # Save to file
            output_path = Path(args.output)
            save_config(assignments, output_path)

            print("\nNext steps:")
            print("1. Review the configuration above")
            print(f"2. Edit {output_path} if needed to remove unwanted assignments")
            print("3. Run: python scripts/export_secrets.py")
            print("4. Copy ASSIGNMENTS_CONFIG to GitHub Secrets")
            print("\nOR for local testing:")
            print("   python scripts/download_submissions.py")

        return 0

    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        return 1
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
