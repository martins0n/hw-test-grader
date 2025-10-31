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

        # Use default key if USE_DEFAULT_ENCRYPTION_KEY is set
        use_default_key = os.getenv('USE_DEFAULT_ENCRYPTION_KEY', 'false').lower() == 'true'
        self.encryption = EncryptionManager(use_default_key=use_default_key)

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

    def process_course_submissions(self, course_id: str, coursework_id: str, coursework_title: str = None):
        """
        Process all submissions for a specific assignment.

        Args:
            course_id: Google Classroom course ID
            coursework_id: Coursework/assignment ID
            coursework_title: Assignment title/name (optional, will fetch if not provided)
        """
        logger.info(f"Processing submissions for course {course_id}, assignment {coursework_id}")

        # Get assignment title if not provided
        if not coursework_title:
            try:
                coursework_list = self.classroom.list_course_work(course_id)
                for work in coursework_list:
                    if work['id'] == coursework_id:
                        coursework_title = work.get('title', coursework_id)
                        break
                if not coursework_title:
                    coursework_title = coursework_id
            except Exception as e:
                logger.warning(f"Could not fetch assignment title: {e}")
                coursework_title = coursework_id

        logger.info(f"Assignment title: {coursework_title}")

        # Get all submissions
        submissions = self.classroom.get_submissions(course_id, coursework_id)
        logger.info(f"Found {len(submissions)} submissions")

        for submission in submissions:
            try:
                self.process_single_submission(course_id, coursework_id, submission, coursework_title, coursework_id)
            except Exception as e:
                logger.error(f"Error processing submission {submission.get('id')}: {e}")

    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize a name for use in git branches and file paths.

        Args:
            name: Name to sanitize

        Returns:
            Sanitized name safe for git branches
        """
        import re
        # Convert to lowercase
        name = name.lower()
        # Replace spaces and special chars with hyphens
        name = re.sub(r'[^a-z0-9]+', '-', name)
        # Remove leading/trailing hyphens
        name = name.strip('-')
        # Limit length
        if len(name) > 50:
            name = name[:50].rstrip('-')
        return name

    def process_single_submission(self, course_id: str, coursework_id: str, submission: Dict, coursework_title: str = None, assignment_coursework_id: str = None):
        """
        Process a single student submission.

        Args:
            course_id: Course ID
            coursework_id: Assignment ID (for fetching submission)
            assignment_coursework_id: Assignment ID to pass to PR metadata
            submission: Submission dictionary from Google Classroom
            coursework_title: Assignment title/name
        """
        user_id = submission['userId']
        submission_id = submission['id']
        state = submission.get('state', 'UNKNOWN')

        # Get student email for identification
        student_id = self.classroom.get_student_email(course_id, user_id)

        # Sanitize assignment name for use in paths
        assignment_name = self._sanitize_name(coursework_title) if coursework_title else coursework_id

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

        # Encrypt and upload to GitHub, and create PR
        self._encrypt_and_upload(student_id, assignment_name, downloaded_files, course_id, assignment_coursework_id or coursework_id, submission, coursework_title)

    def _encrypt_and_upload(
        self,
        student_id: str,
        assignment_name: str,
        files: List[Path],
        course_id: str = None,
        coursework_id: str = None,
        submission: Dict = None,
        assignment_title: str = None
    ):
        """
        Encrypt files and upload to GitHub, then create PR.

        Args:
            student_id: Student ID (email-based)
            assignment_name: Sanitized assignment name for branches/paths
            files: List of file paths to encrypt and upload
            course_id: Course ID (for metadata)
            coursework_id: Coursework/assignment ID (for metadata)
            submission: Submission dict (for PR metadata)
            assignment_title: Original assignment title for display
        """
        # Create branch
        branch_name = self.github.get_or_create_branch(student_id, assignment_name)

        # Encrypt and prepare files
        timestamp = datetime.now().isoformat()
        commit_message = (
            f"Submission sync for {assignment_title or assignment_name} "
            f"by student {student_id} at {timestamp}"
        )

        files_to_commit = []
        repo_paths = set()
        encryption_failed = False
        for file_path in files:
            # Encrypt file
            encrypted_path = self.encrypted_dir / student_id / assignment_name / f"{file_path.name}.enc"
            success = self.encryption.encrypt_file(file_path, encrypted_path, student_id)

            if success:
                # Prepare for GitHub commit
                repo_path = f"submissions/{student_id}/{assignment_name}/{file_path.name}.enc"
                files_to_commit.append((encrypted_path, repo_path))
                repo_paths.add(repo_path)
            else:
                encryption_failed = True

        if not files_to_commit and not repo_paths:
            logger.info("No files to process after encryption")
            return

        # Determine existing repository state
        repo_directory = f"submissions/{student_id}/{assignment_name}"
        existing_repo_files = {
            path for path in self.github.list_files(repo_directory, branch_name)
            if path.endswith('.enc')
        }

        # Filter unchanged files to avoid redundant commits
        filtered_files = []
        for encrypted_path, repo_path in files_to_commit:
            existing_content = self.github.get_file_content(repo_path, branch_name)
            if existing_content is not None:
                current_content = encrypted_path.read_bytes()
                if existing_content == current_content:
                    logger.info(f"Skipping unchanged file {repo_path}")
                    continue
            filtered_files.append((encrypted_path, repo_path))

        files_to_commit = filtered_files

        # Determine files that should be removed (e.g. renamed attachments)
        stale_files = sorted(existing_repo_files - repo_paths)
        if encryption_failed and stale_files:
            logger.warning(
                "Skipping deletion of %d file(s) due to encryption failures",
                len(stale_files)
            )
            stale_files = []
        if not files_to_commit and not stale_files:
            logger.info("No changes detected for submission; skipping GitHub commit")
            return
        # Try batch commit first (handles additions and deletions)
        success = self.github.commit_multiple_files(
            files_to_commit,
            branch_name,
            commit_message,
            delete_paths=stale_files
        )

        if not success:
            logger.warning("Batch commit failed, falling back to individual GitHub operations")

            success_count = 0

            for encrypted_path, repo_path in files_to_commit:
                if self.github.commit_file(encrypted_path, repo_path, branch_name, commit_message):
                    success_count += 1
                else:
                    logger.error(f"Failed to commit {repo_path}")

            delete_count = 0
            for repo_path in stale_files:
                if self.github.delete_file(repo_path, branch_name, commit_message):
                    delete_count += 1
                else:
                    logger.error(f"Failed to delete {repo_path}")

            if success_count + delete_count == len(files_to_commit) + len(stale_files):
                success = True
            elif success_count + delete_count > 0:
                success = True
                logger.warning("Partial success when applying GitHub changes")
            else:
                success = False

        if success:
            logger.info(
                "Successfully synchronized %d additions and %d deletions",
                len(files_to_commit),
                len(stale_files)
            )
            # Create Pull Request (even if only deletions were applied)
            pr_title = f"Submission: {student_id} - {assignment_title or assignment_name}"

            # Build PR body
            pr_body = f"## Student Submission\n\n"
            pr_body += f"**Student:** {student_id}\n"
            pr_body += f"**Assignment:** {assignment_title or assignment_name}\n"
            pr_body += f"**Submitted:** {timestamp}\n"
            pr_body += f"**Files:** {len(repo_paths)}\n\n"

            # Add Google Classroom metadata for grade submission
            pr_body += f"<!-- METADATA\n"
            pr_body += f"course_id: {course_id}\n"
            pr_body += f"coursework_id: {coursework_id}\n"
            pr_body += f"assignment_name: {assignment_name}\n"
            pr_body += f"-->\n\n"

            if submission:
                state = submission.get('state', 'UNKNOWN')
                pr_body += f"**State:** {state}\n"

            if files_to_commit:
                pr_body += f"\n### Updated Files\n"
                for _, repo_path in files_to_commit:
                    filename = repo_path.split('/')[-1].replace('.enc', '')
                    pr_body += f"- {filename}\n"

            if stale_files:
                pr_body += f"\n### Removed Files\n"
                for repo_path in stale_files:
                    filename = repo_path.split('/')[-1].replace('.enc', '')
                    pr_body += f"- {filename}\n"

            if repo_paths:
                pr_body += f"\n### Current Submission Files\n"
                for repo_path in sorted(repo_paths):
                    filename = repo_path.split('/')[-1].replace('.enc', '')
                    pr_body += f"- {filename}\n"

            pr_body += f"\n---\n"
            pr_body += f"🤖 Automated submission from Google Classroom\n"
            pr_body += f"✅ Grading workflow will run automatically\n"

            pr_url = self.github.create_pull_request(
                branch_name=branch_name,
                title=pr_title,
                body=pr_body
            )

            if pr_url:
                logger.info(f"Created PR: {pr_url}")
            else:
                logger.warning("Failed to create PR, but repository state was synchronized")
        else:
            logger.error("Failed to synchronize submission with GitHub")

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
