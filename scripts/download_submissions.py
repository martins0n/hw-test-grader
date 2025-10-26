#!/usr/bin/env python3
"""
Script to download submissions from Google Classroom and commit to GitHub.
Designed to run in GitHub Actions.
"""
import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.submission_processor import SubmissionProcessor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_courses_config() -> Optional[List[Dict]]:
    """
    Load courses configuration from environment or file.
    Supports multiple formats:
    1. COURSE_IDS env var: comma-separated list of course IDs
    2. COURSES_CONFIG env var: JSON array
    3. courses_config.json file: JSON array

    Returns:
        List of course configurations or None
    """
    # Try simple COURSE_IDS first (easiest)
    course_ids_str = os.getenv('COURSE_IDS')
    if course_ids_str:
        course_ids = [cid.strip() for cid in course_ids_str.split(',') if cid.strip()]
        if course_ids:
            logger.info(f"Using COURSE_IDS from environment: {len(course_ids)} course(s)")
            return [{"course_id": cid} for cid in course_ids]

    # Try COURSES_CONFIG JSON
    config_json = os.getenv('COURSES_CONFIG')
    if config_json:
        try:
            return json.loads(config_json)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse COURSES_CONFIG: {e}")
            return None

    # Try to load from file
    config_path = Path('courses_config.json')
    if config_path.exists():
        try:
            with open(config_path) as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse courses_config.json: {e}")
            return None

    return None


def load_assignments_config() -> Optional[List[Dict]]:
    """
    Load assignments configuration from environment or file.
    This is the old format - kept for backwards compatibility.

    Returns:
        List of assignment configurations or None
    """
    # Try to load from environment variable
    config_json = os.getenv('ASSIGNMENTS_CONFIG')
    if config_json:
        try:
            return json.loads(config_json)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ASSIGNMENTS_CONFIG: {e}")
            return None

    # Try to load from file
    config_path = Path('assignments_config.json')
    if config_path.exists():
        try:
            with open(config_path) as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse assignments_config.json: {e}")
            return None

    return None


def process_assignments(processor: SubmissionProcessor, assignments: List[Dict]) -> Dict:
    """
    Process a list of assignments.

    Args:
        processor: SubmissionProcessor instance
        assignments: List of assignment configurations

    Returns:
        Summary statistics
    """
    summary = {
        'total_assignments': len(assignments),
        'successful': 0,
        'failed': 0,
        'details': []
    }

    for assignment in assignments:
        course_id = assignment.get('course_id')
        coursework_id = assignment.get('coursework_id')
        name = assignment.get('name', f"{course_id}/{coursework_id}")

        if not course_id or not coursework_id:
            logger.warning(f"Skipping invalid assignment config: {assignment}")
            summary['failed'] += 1
            continue

        logger.info(f"Processing assignment: {name}")

        try:
            # Pass the assignment name to use instead of ID
            processor.process_course_submissions(course_id, coursework_id, name)
            summary['successful'] += 1
            summary['details'].append({
                'name': name,
                'status': 'success',
                'course_id': course_id,
                'coursework_id': coursework_id
            })
            logger.info(f"✓ Successfully processed: {name}")

        except Exception as e:
            logger.error(f"✗ Failed to process {name}: {e}")
            summary['failed'] += 1
            summary['details'].append({
                'name': name,
                'status': 'failed',
                'error': str(e),
                'course_id': course_id,
                'coursework_id': coursework_id
            })

    return summary


def process_single_assignment(processor: SubmissionProcessor, course_id: str, coursework_id: str):
    """
    Process a single assignment.

    Args:
        processor: SubmissionProcessor instance
        course_id: Course ID
        coursework_id: Coursework ID
    """
    logger.info(f"Processing single assignment: {course_id}/{coursework_id}")

    try:
        # Assignment title will be fetched automatically
        processor.process_course_submissions(course_id, coursework_id)
        logger.info("✓ Successfully processed assignment")

        # Write summary
        with open('download_summary.txt', 'w') as f:
            f.write(f"\n### Assignment Processed\n")
            f.write(f"- Course ID: {course_id}\n")
            f.write(f"- Coursework ID: {coursework_id}\n")
            f.write(f"- Status: Success\n")

    except Exception as e:
        logger.error(f"✗ Failed to process assignment: {e}")

        with open('download_summary.txt', 'w') as f:
            f.write(f"\n### Assignment Failed\n")
            f.write(f"- Course ID: {course_id}\n")
            f.write(f"- Coursework ID: {coursework_id}\n")
            f.write(f"- Error: {str(e)}\n")

        raise


def auto_discover_from_courses(processor: SubmissionProcessor, courses: List[Dict]) -> List[Dict]:
    """
    Auto-discover all assignments from specified courses.

    Args:
        processor: SubmissionProcessor instance
        courses: List of course configs with course_id

    Returns:
        List of discovered assignments
    """
    discovered = []

    logger.info(f"Auto-discovering assignments from {len(courses)} course(s)")

    for course_config in courses:
        course_id = course_config.get('course_id')
        course_name = course_config.get('name', f'Course {course_id}')

        if not course_id:
            logger.warning(f"Skipping course config without course_id: {course_config}")
            continue

        logger.info(f"Fetching assignments from: {course_name}")

        try:
            coursework_list = processor.classroom.list_course_work(course_id)

            # Filter to only published assignments
            published = [w for w in coursework_list if w.get('state') == 'PUBLISHED']

            logger.info(f"  Found {len(published)} published assignment(s)")

            for work in published:
                work_title = work.get('title', 'Untitled')
                work_id = work['id']

                assignment = {
                    'name': work_title,
                    'course_id': course_id,
                    'coursework_id': work_id
                }

                discovered.append(assignment)
                logger.info(f"    ✓ {work_title}")

        except Exception as e:
            logger.error(f"Failed to fetch coursework from {course_name}: {e}")
            continue

    logger.info(f"Auto-discovered {len(discovered)} total assignment(s)")
    return discovered


def process_all_configured(processor: SubmissionProcessor):
    """
    Process all configured assignments.
    Supports two modes:
    1. COURSES_CONFIG: Auto-discover all assignments from specified courses
    2. ASSIGNMENTS_CONFIG: Process specific assignments (backwards compatibility)

    Args:
        processor: SubmissionProcessor instance
    """
    # Try new courses-based config first
    courses = load_courses_config()

    if courses:
        logger.info("Using COURSES_CONFIG - auto-discovering assignments")
        assignments = auto_discover_from_courses(processor, courses)

        if not assignments:
            logger.warning("No assignments discovered from configured courses")
            with open('download_summary.txt', 'w') as f:
                f.write(f"\n### No Assignments Found\n")
                f.write(f"- Checked {len(courses)} configured course(s)\n")
                f.write(f"- No published assignments found\n")
            return

    else:
        # Fall back to old assignments-based config
        assignments = load_assignments_config()

        if not assignments:
            logger.warning("No courses or assignments configured")
            logger.info("TIP: Create courses_config.json with your course IDs")

            # List available courses and coursework for reference
            logger.info("Listing available courses:")
            try:
                all_courses = processor.classroom.list_courses()
                logger.info(f"Found {len(all_courses)} courses")

                with open('download_summary.txt', 'w') as f:
                    f.write(f"\n### No Configuration Found\n")
                    f.write(f"- Found {len(all_courses)} available courses\n")
                    f.write(f"- Create courses_config.json with course IDs (recommended)\n")
                    f.write(f"- Or create assignments_config.json with specific assignments\n")
                    f.write(f"\n### Available Courses:\n")
                    for course in all_courses[:10]:  # Show first 10
                        f.write(f"- {course['name']} (ID: {course['id']})\n")

            except Exception as e:
                logger.error(f"Failed to list courses: {e}")

            return

        logger.info(f"Using ASSIGNMENTS_CONFIG - processing {len(assignments)} specific assignment(s)")

    # Process the assignments
    logger.info(f"Processing {len(assignments)} assignment(s)")
    summary = process_assignments(processor, assignments)

    # Write summary
    with open('download_summary.txt', 'w') as f:
        f.write(f"\n### Download Summary\n")
        f.write(f"- Total assignments: {summary['total_assignments']}\n")
        f.write(f"- Successful: {summary['successful']}\n")
        f.write(f"- Failed: {summary['failed']}\n")
        f.write(f"\n### Details:\n")

        for detail in summary['details']:
            status_icon = "✓" if detail['status'] == 'success' else "✗"
            f.write(f"{status_icon} {detail['name']}: {detail['status']}\n")
            if 'error' in detail:
                f.write(f"  Error: {detail['error']}\n")

    logger.info("Summary written to download_summary.txt")

    # Print summary
    print("\n" + "=" * 80)
    print("DOWNLOAD SUMMARY")
    print("=" * 80)
    print(f"Total assignments: {summary['total_assignments']}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print("=" * 80)


def main():
    """Main entry point."""
    # Get inputs from environment (set by GitHub Actions)
    course_id = os.getenv('COURSE_ID', '').strip()
    coursework_id = os.getenv('COURSEWORK_ID', '').strip()

    logger.info("Starting submission download script")
    logger.info(f"Course ID from env: {course_id if course_id else 'Not set'}")
    logger.info(f"Coursework ID from env: {coursework_id if coursework_id else 'Not set'}")

    try:
        # Initialize processor
        processor = SubmissionProcessor()

        # Decide what to process
        if course_id and coursework_id:
            # Process single assignment (manual trigger)
            process_single_assignment(processor, course_id, coursework_id)
        else:
            # Process all configured assignments (scheduled run)
            process_all_configured(processor)

        logger.info("Download script completed successfully")

    except Exception as e:
        logger.error(f"Download script failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
