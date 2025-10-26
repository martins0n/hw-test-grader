#!/usr/bin/env python3
"""
Helper script to set up courses_config.json by selecting courses interactively.
"""
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.classroom_client import ClassroomClient


def main():
    """Main entry point."""
    print("=" * 80)
    print("COURSES CONFIGURATION SETUP")
    print("=" * 80)
    print("\nThis will help you select which courses to automatically grade.\n")

    # Connect to Classroom
    print("Connecting to Google Classroom...")
    client = ClassroomClient()

    # Get all courses
    print("Fetching courses...\n")
    courses = client.list_courses()

    if not courses:
        print("No courses found.")
        return 1

    # Filter to active courses
    active_courses = [c for c in courses if c.get('courseState') == 'ACTIVE']

    print(f"Found {len(active_courses)} active course(s):\n")

    # Display courses
    for i, course in enumerate(active_courses, 1):
        name = course.get('name', 'Unnamed Course')
        section = course.get('section', '')
        course_id = course['id']

        print(f"{i}. {name}")
        if section:
            print(f"   Section: {section}")
        print(f"   Course ID: {course_id}")
        print()

    # Ask user to select courses
    print("=" * 80)
    print("Select courses to monitor (enter numbers separated by spaces)")
    print("Example: 1 3 4")
    print("Or enter 'all' to select all courses")
    print("=" * 80)

    selection = input("\nYour selection: ").strip()

    if not selection:
        print("No selection made. Exiting.")
        return 0

    # Process selection
    selected_courses = []

    if selection.lower() == 'all':
        selected_courses = active_courses
    else:
        try:
            indices = [int(x.strip()) - 1 for x in selection.split()]

            for idx in indices:
                if 0 <= idx < len(active_courses):
                    selected_courses.append(active_courses[idx])
                else:
                    print(f"Warning: Invalid index {idx + 1}, skipping")

        except ValueError:
            print("Error: Invalid input. Please enter numbers separated by spaces.")
            return 1

    if not selected_courses:
        print("No valid courses selected. Exiting.")
        return 0

    # Build config
    config = []
    for course in selected_courses:
        name = course.get('name', 'Unnamed Course')
        section = course.get('section', '')
        course_id = course['id']

        display_name = name
        if section:
            display_name = f"{name} - {section}"

        config.append({
            "course_id": course_id,
            "name": display_name
        })

    # Show what will be saved
    print("\n" + "=" * 80)
    print("SELECTED COURSES")
    print("=" * 80)
    print(json.dumps(config, indent=2))

    # Ask for confirmation
    print("\n" + "=" * 80)
    confirm = input("Save this configuration? (y/n): ").strip().lower()

    if confirm != 'y':
        print("Configuration not saved.")
        return 0

    # Save to file
    output_path = Path("courses_config.json")
    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"\n✓ Configuration saved to: {output_path}")
    print(f"  Monitoring {len(config)} course(s)")

    # Show preview of what will be discovered
    print("\n" + "=" * 80)
    print("PREVIEW: Assignments that will be auto-discovered")
    print("=" * 80)

    total_assignments = 0
    for course_config in config:
        course_id = course_config['course_id']
        course_name = course_config['name']

        print(f"\n{course_name}:")

        try:
            coursework = client.list_course_work(course_id)
            published = [w for w in coursework if w.get('state') == 'PUBLISHED']

            if published:
                print(f"  {len(published)} published assignment(s):")
                for work in published:
                    print(f"    - {work.get('title', 'Untitled')}")
                    total_assignments += 1
            else:
                print("  No published assignments")

        except Exception as e:
            print(f"  Error fetching assignments: {e}")

    print("\n" + "=" * 80)
    print(f"Total: {total_assignments} assignment(s) will be automatically graded")
    print("=" * 80)

    print("\nNext steps:")
    print("1. Test locally: python scripts/download_submissions.py")
    print("2. Export for GitHub: python scripts/export_secrets.py")
    print("3. Copy COURSES_CONFIG to GitHub Secrets")
    print("\nThe system will automatically discover and grade ALL published")
    print("assignments from these courses every hour.")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
