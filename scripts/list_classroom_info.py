#!/usr/bin/env python3
"""
Helper script to list Google Classroom courses and assignments with their IDs.
Use this to find the course_id and coursework_id for assignments_config.json
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.classroom_client import ClassroomClient


def list_all_courses():
    """List all available courses."""
    print("=" * 80)
    print("GOOGLE CLASSROOM COURSES")
    print("=" * 80)

    client = ClassroomClient()
    courses = client.list_courses()

    if not courses:
        print("\nNo courses found.")
        print("Make sure:")
        print("  1. You have access to Google Classroom courses")
        print("  2. Your account has teacher/instructor permissions")
        return []

    print(f"\nFound {len(courses)} course(s):\n")

    for i, course in enumerate(courses, 1):
        print(f"{i}. {course.get('name', 'Unnamed Course')}")
        print(f"   Course ID: {course['id']}")
        print(f"   Section: {course.get('section', 'N/A')}")
        print(f"   State: {course.get('courseState', 'N/A')}")
        print(f"   Room: {course.get('room', 'N/A')}")
        print()

    return courses


def list_coursework_for_course(course_id: str, course_name: str = None):
    """List all coursework/assignments for a specific course."""
    print("=" * 80)
    if course_name:
        print(f"ASSIGNMENTS FOR: {course_name}")
    else:
        print(f"ASSIGNMENTS FOR COURSE: {course_id}")
    print("=" * 80)

    client = ClassroomClient()
    coursework = client.list_course_work(course_id)

    if not coursework:
        print("\nNo assignments found in this course.")
        return []

    print(f"\nFound {len(coursework)} assignment(s):\n")

    for i, work in enumerate(coursework, 1):
        print(f"{i}. {work.get('title', 'Untitled Assignment')}")
        print(f"   Coursework ID: {work['id']}")
        print(f"   State: {work.get('state', 'N/A')}")

        # Due date
        if 'dueDate' in work:
            due = work['dueDate']
            due_str = f"{due.get('year')}-{due.get('month'):02d}-{due.get('day'):02d}"
            print(f"   Due Date: {due_str}")
        else:
            print(f"   Due Date: No deadline")

        # Max points
        if 'maxPoints' in work:
            print(f"   Max Points: {work['maxPoints']}")

        print()

    return coursework


def generate_config(courses_data):
    """Generate assignments_config.json format."""
    print("=" * 80)
    print("GENERATE ASSIGNMENTS CONFIG")
    print("=" * 80)
    print("\nFormat for assignments_config.json:\n")
    print('[')
    print('  {')
    print('    "name": "Assignment Name",')
    print('    "course_id": "COURSE_ID",')
    print('    "coursework_id": "COURSEWORK_ID"')
    print('  },')
    print('  {')
    print('    "name": "Another Assignment",')
    print('    "course_id": "COURSE_ID",')
    print('    "coursework_id": "COURSEWORK_ID"')
    print('  }')
    print(']')


def interactive_mode():
    """Interactive mode to explore courses and assignments."""
    print("=" * 80)
    print("GOOGLE CLASSROOM ID FINDER")
    print("=" * 80)
    print("\nThis will help you find course IDs and assignment IDs for your config.\n")

    # List all courses
    courses = list_all_courses()

    if not courses:
        return

    # Ask user to select a course
    print("=" * 80)
    while True:
        choice = input("\nEnter course number to view assignments (or 'q' to quit): ").strip()

        if choice.lower() == 'q':
            break

        try:
            course_idx = int(choice) - 1
            if 0 <= course_idx < len(courses):
                selected_course = courses[course_idx]
                course_id = selected_course['id']
                course_name = selected_course.get('name', 'Unnamed')

                print()
                coursework = list_coursework_for_course(course_id, course_name)

                if coursework:
                    print("=" * 80)
                    print("COPY THESE VALUES:")
                    print("=" * 80)
                    print(f'  "course_id": "{course_id}"')
                    print("\nFor each assignment you want to grade, use:")
                    for work in coursework:
                        print(f'  "coursework_id": "{work["id"]}"  # {work.get("title", "Untitled")}')
                    print()

            else:
                print("Invalid course number. Try again.")

        except ValueError:
            print("Please enter a valid number or 'q' to quit.")

    print("\n" + "=" * 80)
    print("TIP: Copy the course_id and coursework_id values above")
    print("     and add them to assignments_config.json")
    print("=" * 80)


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "courses":
            # Just list courses
            list_all_courses()

        elif command == "assignments" and len(sys.argv) > 2:
            # List assignments for a specific course
            course_id = sys.argv[2]
            list_coursework_for_course(course_id)

        else:
            print("Usage:")
            print("  python scripts/list_classroom_info.py              # Interactive mode")
            print("  python scripts/list_classroom_info.py courses      # List all courses")
            print("  python scripts/list_classroom_info.py assignments COURSE_ID  # List assignments")

    else:
        # Interactive mode
        try:
            interactive_mode()
        except KeyboardInterrupt:
            print("\n\nExiting...")
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
