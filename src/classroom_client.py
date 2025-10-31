"""
Google Classroom API client for downloading student submissions.
"""
import os
import pickle
from typing import List, Dict, Optional
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import logging

logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/classroom.courses.readonly',
    'https://www.googleapis.com/auth/classroom.coursework.students.readonly',
    'https://www.googleapis.com/auth/classroom.student-submissions.students.readonly',
    'https://www.googleapis.com/auth/classroom.student-submissions.me.readonly',
    'https://www.googleapis.com/auth/classroom.coursework.students',  # Required to submit grades
    'https://www.googleapis.com/auth/classroom.rosters.readonly',  # Required to get student emails
    'https://www.googleapis.com/auth/classroom.profile.emails',  # Required to access email addresses
    'https://www.googleapis.com/auth/drive.readonly'
]


class ClassroomClient:
    """Client for interacting with Google Classroom API."""

    def __init__(self, credentials_path: str = 'credentials.json', token_path: str = 'token.json'):
        """
        Initialize the Classroom client.

        Args:
            credentials_path: Path to the OAuth credentials JSON file
            token_path: Path to store the access token
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self.drive_service = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with Google Classroom API."""
        creds = None

        # Load token if it exists
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)

        # If there are no (valid) credentials, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Credentials file not found at {self.credentials_path}. "
                        "Please follow the setup instructions in README.md"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                # Disable strict scope validation to handle scope reordering
                import os as _os
                _os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
                try:
                    creds = flow.run_local_server(port=0)
                finally:
                    # Clean up environment variable
                    _os.environ.pop('OAUTHLIB_RELAX_TOKEN_SCOPE', None)

            # Save the credentials for the next run
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)

        self.service = build('classroom', 'v1', credentials=creds)
        self.drive_service = build('drive', 'v3', credentials=creds)
        logger.info("Successfully authenticated with Google Classroom API")

    def list_courses(self) -> List[Dict]:
        """List all courses accessible to the authenticated user."""
        results = self.service.courses().list(pageSize=100).execute()
        courses = results.get('courses', [])
        return courses

    def list_course_work(self, course_id: str) -> List[Dict]:
        """
        List all coursework for a given course.

        Args:
            course_id: The ID of the course

        Returns:
            List of coursework items
        """
        results = self.service.courses().courseWork().list(
            courseId=course_id
        ).execute()
        coursework = results.get('courseWork', [])
        return coursework

    def get_submissions(self, course_id: str, coursework_id: str) -> List[Dict]:
        """
        Get all student submissions for a specific assignment.

        Args:
            course_id: The ID of the course
            coursework_id: The ID of the coursework/assignment

        Returns:
            List of submissions
        """
        submissions = []
        page_token = None

        while True:
            results = self.service.courses().courseWork().studentSubmissions().list(
                courseId=course_id,
                courseWorkId=coursework_id,
                pageToken=page_token
            ).execute()

            submissions.extend(results.get('studentSubmissions', []))
            page_token = results.get('nextPageToken')

            if not page_token:
                break

        return submissions

    def download_attachment(self, attachment: Dict, output_dir: Path) -> Optional[Path]:
        """
        Download a submission attachment.

        Args:
            attachment: Attachment dictionary from submission
            output_dir: Directory to save the file

        Returns:
            Path to the downloaded file, or None if download failed
        """
        try:
            if 'driveFile' in attachment:
                drive_file = attachment['driveFile']
                file_id = drive_file['id']
                title = drive_file.get('title', 'untitled')

                request = self.drive_service.files().get_media(fileId=file_id)

                output_path = output_dir / title
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)

                done = False
                while not done:
                    status, done = downloader.next_chunk()

                fh.seek(0)
                output_path.write_bytes(fh.read())

                logger.info(f"Downloaded: {title}")
                return output_path
            else:
                logger.warning(f"Attachment type not supported: {attachment}")
                return None

        except Exception as e:
            logger.error(f"Error downloading attachment: {e}")
            return None

    def get_student_info(self, course_id: str, user_id: str) -> Dict:
        """
        Get student information.

        Args:
            course_id: The ID of the course
            user_id: The ID of the student

        Returns:
            Student information dictionary with email
        """
        try:
            student = self.service.courses().students().get(
                courseId=course_id,
                userId=user_id
            ).execute()
            return student
        except Exception as e:
            logger.error(f"Error getting student info: {e}")
            return {}

    def get_student_email(self, course_id: str, user_id: str) -> str:
        """
        Get student email address.

        Args:
            course_id: The ID of the course
            user_id: The ID of the student

        Returns:
            Student email address or user_id if email not available
        """
        try:
            student = self.get_student_info(course_id, user_id)
            profile = student.get('profile', {})
            email = profile.get('emailAddress', '')

            if email:
                # Clean email for use as identifier (remove @ and .)
                return email.replace('@', '_at_').replace('.', '_')
            else:
                logger.warning(f"No email found for student {user_id}, using ID")
                return user_id
        except Exception as e:
            logger.error(f"Error getting student email: {e}")
            return user_id

    def submit_grade(
        self,
        course_id: str,
        coursework_id: str,
        submission_id: str,
        grade: float,
        max_points: Optional[float] = None
    ) -> bool:
        """
        Submit a draft grade for a student submission.

        Note: This submits a draft grade that must be approved by the teacher.
        The grade will not be final until the teacher reviews and approves it.

        Args:
            course_id: The ID of the course
            coursework_id: The ID of the coursework/assignment
            submission_id: The ID of the submission
            grade: The grade to assign (must be <= max_points)
            max_points: Maximum points for the assignment (optional, for validation)

        Returns:
            True if grade was submitted successfully, False otherwise
        """
        try:
            # Validate grade
            if max_points is not None and grade > max_points:
                logger.warning(
                    f"Grade {grade} exceeds max points {max_points}, capping at max"
                )
                grade = max_points

            # Prepare the update body
            body = {
                'draftGrade': grade
            }

            # Update the submission with draft grade
            result = self.service.courses().courseWork().studentSubmissions().patch(
                courseId=course_id,
                courseWorkId=coursework_id,
                id=submission_id,
                updateMask='draftGrade',
                body=body
            ).execute()

            logger.info(
                f"Submitted draft grade {grade} for submission {submission_id} "
                f"(course: {course_id}, coursework: {coursework_id})"
            )
            return True

        except Exception as e:
            logger.error(f"Error submitting grade: {e}")
            return False

    def find_submission_for_student(
        self,
        course_id: str,
        coursework_id: str,
        student_email: str
    ) -> Optional[str]:
        """
        Find a submission ID for a specific student by email.

        Args:
            course_id: The ID of the course
            coursework_id: The ID of the coursework/assignment
            student_email: The student's email address

        Returns:
            Submission ID if found, None otherwise
        """
        try:
            submissions = self.get_submissions(course_id, coursework_id)

            for submission in submissions:
                user_id = submission.get('userId')
                student_info = self.get_student_info(course_id, user_id)
                profile = student_info.get('profile', {})
                email = profile.get('emailAddress', '')

                if email.lower() == student_email.lower():
                    return submission.get('id')

            logger.warning(
                f"No submission found for student {student_email} "
                f"in course {course_id}, coursework {coursework_id}"
            )
            return None

        except Exception as e:
            logger.error(f"Error finding submission: {e}")
            return None
