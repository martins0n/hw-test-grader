"""
Main submission processor that orchestrates the entire workflow.
"""
import os
import logging
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from dotenv import load_dotenv

from .classroom_client import ClassroomClient
from .encryption import EncryptionManager
from .github_manager import GitHubManager
from .grader import NotebookGrader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SubmissionProcessor:
    """Main processor for handling homework submissions."""

    def __init__(self):
        """Initialize the submission processor."""
        load_dotenv()

        # Initialize components
        self.classroom = ClassroomClient(
            credentials_path=os.getenv('GOOGLE_CLASSROOM_CREDENTIALS', 'credentials.json')
        )
        self.encryption = EncryptionManager()

        github_token = os.getenv('GITHUB_TOKEN')
        github_repo = os.getenv('GITHUB_REPO')

        if not github_token or not github_repo:
            raise ValueError("GITHUB_TOKEN and GITHUB_REPO must be set in .env file")

        self.github = GitHubManager(github_token, github_repo)
        self.grader = NotebookGrader()

        # Directories
        self.submissions_dir = Path("submissions")
        self.encrypted_dir = Path("encrypted_submissions")
        self.decrypted_dir = Path("decrypted_submissions")
        self.reports_dir = Path("reports")

        for directory in [self.submissions_dir, self.encrypted_dir, self.decrypted_dir, self.reports_dir]:
            directory.mkdir(exist_ok=True)

    def process_course_submissions(self, course_id: str, coursework_id: str):
        """
        Process all submissions for a specific assignment.

        Args:
            course_id: Google Classroom course ID
            coursework_id: Coursework/assignment ID
        """
        logger.info(f"Processing submissions for course {course_id}, assignment {coursework_id}")

        # Get all submissions
        submissions = self.classroom.get_submissions(course_id, coursework_id)
        logger.info(f"Found {len(submissions)} submissions")

        for submission in submissions:
            try:
                self.process_single_submission(course_id, coursework_id, submission)
            except Exception as e:
                logger.error(f"Error processing submission {submission.get('id')}: {e}")

    def process_single_submission(self, course_id: str, coursework_id: str, submission: Dict):
        """
        Process a single student submission.

        Args:
            course_id: Course ID
            coursework_id: Assignment ID
            submission: Submission dictionary from Google Classroom
        """
        student_id = submission['userId']
        submission_id = submission['id']
        state = submission.get('state', 'UNKNOWN')

        logger.info(f"Processing submission {submission_id} from student {student_id} (state: {state})")

        # Only process turned in or graded submissions
        if state not in ['TURNED_IN', 'RETURNED']:
            logger.info(f"Skipping submission with state {state}")
            return

        # Check if there are attachments
        assignment_submission = submission.get('assignmentSubmission', {})
        attachments = assignment_submission.get('attachments', [])

        if not attachments:
            logger.warning(f"No attachments found for submission {submission_id}")
            return

        # Download attachments
        student_dir = self.submissions_dir / student_id / coursework_id
        student_dir.mkdir(parents=True, exist_ok=True)

        downloaded_files = []
        for attachment in attachments:
            file_path = self.classroom.download_attachment(attachment, student_dir)
            if file_path:
                downloaded_files.append(file_path)

        if not downloaded_files:
            logger.warning(f"No files downloaded for submission {submission_id}")
            return

        # Encrypt and upload to GitHub
        self._encrypt_and_upload(student_id, coursework_id, downloaded_files)

    def _encrypt_and_upload(self, student_id: str, assignment_id: str, files: List[Path]):
        """
        Encrypt files and upload to GitHub.

        Args:
            student_id: Student ID
            assignment_id: Assignment ID
            files: List of file paths to encrypt and upload
        """
        # Create branch
        branch_name = self.github.get_or_create_branch(student_id, assignment_id)

        # Encrypt and prepare files
        files_to_commit = []
        for file_path in files:
            # Encrypt file
            encrypted_path = self.encrypted_dir / student_id / assignment_id / f"{file_path.name}.enc"
            success = self.encryption.encrypt_file(file_path, encrypted_path, student_id)

            if success:
                # Prepare for GitHub commit
                repo_path = f"submissions/{student_id}/{assignment_id}/{file_path.name}.enc"
                files_to_commit.append((encrypted_path, repo_path))

        # Commit to GitHub
        if files_to_commit:
            timestamp = datetime.now().isoformat()
            commit_message = f"Submission for {assignment_id} by student {student_id} at {timestamp}"

            success = self.github.commit_multiple_files(
                files_to_commit,
                branch_name,
                commit_message
            )

            if success:
                logger.info(f"Successfully uploaded {len(files_to_commit)} encrypted files to GitHub")
            else:
                logger.error("Failed to upload files to GitHub")

    def list_courses(self):
        """List all available courses."""
        courses = self.classroom.list_courses()

        print("\nAvailable Courses:")
        print("-" * 80)
        for course in courses:
            print(f"ID: {course['id']}")
            print(f"Name: {course['name']}")
            print(f"Section: {course.get('section', 'N/A')}")
            print("-" * 80)

    def list_coursework(self, course_id: str):
        """
        List all coursework for a course.

        Args:
            course_id: Course ID
        """
        coursework = self.classroom.list_course_work(course_id)

        print(f"\nCoursework for course {course_id}:")
        print("-" * 80)
        for work in coursework:
            print(f"ID: {work['id']}")
            print(f"Title: {work['title']}")
            print(f"State: {work.get('state', 'N/A')}")
            print(f"Due: {work.get('dueDate', 'N/A')}")
            print("-" * 80)


def main():
    """Main entry point for the submission processor."""
    processor = SubmissionProcessor()

    # Example usage - list courses
    processor.list_courses()

    # To process submissions, call:
    # processor.process_course_submissions(course_id="YOUR_COURSE_ID", coursework_id="YOUR_COURSEWORK_ID")


if __name__ == "__main__":
    main()
