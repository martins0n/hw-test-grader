#!/usr/bin/env python3
"""
Example usage of the homework grader system.
Run this after completing the setup in README.md.
"""
from src.submission_processor import SubmissionProcessor


def main():
    print("=" * 80)
    print("HOMEWORK GRADER - Example Usage")
    print("=" * 80)

    # Initialize the processor
    print("\n1. Initializing submission processor...")
    processor = SubmissionProcessor()

    # List all courses
    print("\n2. Listing available courses...")
    processor.list_courses()

    # Get user input
    print("\n" + "=" * 80)
    course_id = input("Enter Course ID to view assignments (or press Enter to skip): ").strip()

    if course_id:
        print(f"\n3. Listing coursework for course {course_id}...")
        processor.list_coursework(course_id)

        coursework_id = input("\nEnter Coursework ID to process submissions (or press Enter to skip): ").strip()

        if coursework_id:
            print(f"\n4. Processing submissions for assignment {coursework_id}...")
            confirm = input(f"This will download, encrypt, and upload submissions to GitHub. Continue? (y/n): ")

            if confirm.lower() == 'y':
                processor.process_course_submissions(course_id, coursework_id)
                print("\n✓ Submissions processed successfully!")
                print("Check your GitHub repository for new commits on student branches.")
                print("The CI/CD pipeline should trigger automatically.")
            else:
                print("Cancelled.")
    else:
        print("\nSkipped. You can run this script again when ready.")

    print("\n" + "=" * 80)
    print("Next steps:")
    print("1. Check your GitHub repository for student branches")
    print("2. Review the CI/CD Actions tab for grading progress")
    print("3. Download grading reports from workflow artifacts")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
