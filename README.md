# Homework Grader Pipeline

Automated homework grading system that integrates Google Classroom, GitHub, and CI/CD for secure, automated grading of Jupyter notebook assignments.

## Features

- **Google Classroom Integration**: Automatically downloads student submissions
- **Secure Storage**: Encrypts student files before storing in GitHub
- **Automated Grading**: Executes notebooks and compares JSON outputs
- **CI/CD Pipeline**: GitHub Actions workflow for automatic grading
- **Student Privacy**: Each student has a unique encryption key
- **Branch Management**: Separate branches for each student/assignment combination

## Architecture

```
1. Student submits assignment via Google Classroom
2. Script downloads submission
3. Files are encrypted with student-specific key
4. Encrypted files committed to GitHub (student branch)
5. GitHub Actions triggered
6. Pipeline decrypts files
7. Notebook executed and graded
8. Results sent back to student
```

## Setup Instructions

### Prerequisites

- Python 3.11+ (managed with pyenv)
- GitHub account with a repository for storing submissions
- Google Cloud project with Classroom API enabled
- Git installed

### 1. Install pyenv and Python

```bash
# Install pyenv (if not already installed)
curl https://pyenv.run | bash

# Install Python 3.11
pyenv install 3.11.0
pyenv local 3.11.0
```

### 2. Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt
```

### 3. Google Classroom API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google Classroom API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Classroom API"
   - Click "Enable"
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Select "Desktop app" as application type
   - Download the credentials JSON file
   - Save it as `credentials.json` in the project root

### 4. GitHub Setup

1. Create a GitHub repository for storing submissions (e.g., `username/homework-submissions`)
2. Create a Personal Access Token:
   - Go to GitHub Settings > Developer settings > Personal access tokens > Tokens (classic)
   - Generate new token with `repo` permissions
   - Save the token securely

3. Add repository secrets for GitHub Actions:
   - Go to your repository > Settings > Secrets and variables > Actions
   - Add the following secrets:
     - `ENCRYPTION_KEYS`: JSON object with student encryption keys (see below)
     - `GOOGLE_CREDENTIALS`: Content of your credentials.json file
     - `GOOGLE_TOKEN`: (Optional) Content of token.json after first authentication
     - `ASSIGNMENTS_CONFIG`: (Optional) JSON array of assignments to auto-download (see below)

### 5. Configure Environment Variables

```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your values
nano .env
```

Update `.env`:
```
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_REPO=username/homework-submissions
GOOGLE_CLASSROOM_CREDENTIALS=credentials.json
LOG_LEVEL=INFO
```

### 6. First Run - Authenticate with Google

```bash
# Run the main script to authenticate
python -m src.submission_processor
```

This will:
- Open a browser for Google OAuth
- Save authentication token to `token.json`
- List your available courses

### 7. Configure Automatic Download (Optional)

To enable automatic downloading of submissions from Google Classroom:

1. Create an assignments configuration file or GitHub Secret with your assignments:

```bash
# Option A: Create a local file (for reference)
cp assignments_config.json.example assignments_config.json
nano assignments_config.json
```

Example `assignments_config.json`:
```json
[
  {
    "name": "Homework 1 - Introduction to Python",
    "course_id": "123456789",
    "coursework_id": "987654321"
  },
  {
    "name": "Homework 2 - Data Structures",
    "course_id": "123456789",
    "coursework_id": "987654322"
  }
]
```

2. Add this configuration as a GitHub Secret named `ASSIGNMENTS_CONFIG`

3. The workflow will run automatically every hour, or you can trigger it manually:
   - Go to Actions tab in your GitHub repository
   - Select "Download Student Submissions"
   - Click "Run workflow"
   - Optionally specify a single course_id and coursework_id

## Usage

### List Available Courses

```python
from src.submission_processor import SubmissionProcessor

processor = SubmissionProcessor()
processor.list_courses()
```

### List Assignments in a Course

```python
processor.list_coursework(course_id="YOUR_COURSE_ID")
```

### Process Submissions for an Assignment

```python
processor.process_course_submissions(
    course_id="YOUR_COURSE_ID",
    coursework_id="YOUR_COURSEWORK_ID"
)
```

This will:
1. Download all submissions
2. Encrypt files with student-specific keys
3. Commit to GitHub on student branches
4. Trigger CI/CD pipeline for grading

### Setting Up Test Cases

Create expected outputs for each assignment:

```bash
mkdir -p test_cases/ASSIGNMENT_ID
```

Create `test_cases/ASSIGNMENT_ID/expected_output.json`:

```json
[
  {"result": "expected_value_1"},
  {"result": "expected_value_2"}
]
```

The grader will execute the student's notebook and compare JSON outputs.

### Manual Grading (Local)

```bash
# Grade a specific notebook
python scripts/run_grader.py \
  --student-id STUDENT_ID \
  --assignment-id ASSIGNMENT_ID \
  --output reports/grade_report.json
```

## Project Structure

```
homeworkgrader/
├── .github/
│   └── workflows/
│       ├── download_submissions.yml   # Auto-download from Classroom
│       └── grade_submission.yml       # CI/CD grading workflow
├── src/
│   ├── __init__.py
│   ├── classroom_client.py         # Google Classroom API
│   ├── encryption.py               # File encryption/decryption
│   ├── github_manager.py           # GitHub operations
│   ├── grader.py                   # Notebook grading logic
│   └── submission_processor.py     # Main orchestrator
├── scripts/
│   ├── download_submissions.py     # CI/CD: Download from Classroom
│   ├── decrypt_submission.py       # CI/CD: Decrypt files
│   ├── run_grader.py               # CI/CD: Run grading
│   └── send_results.py             # CI/CD: Send results
├── test_cases/                     # Expected outputs per assignment
├── student_keys/                   # Encryption keys (gitignored)
├── .env                            # Environment config (gitignored)
├── .env.example                    # Example environment config
├── assignments_config.json.example # Example assignments config
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## Security Notes

1. **Encryption Keys**: Student encryption keys are stored in `student_keys/` and should NEVER be committed to Git
2. **GitHub Secrets**: Store encryption keys in GitHub Secrets for CI/CD access
3. **Credentials**: Never commit `credentials.json`, `token.json`, or `.env` files

### Managing Encryption Keys

To export keys for GitHub Secrets:

```python
from src.encryption import EncryptionManager

manager = EncryptionManager()
manager.export_keys(Path("keys_backup.json"))
```

Then copy the content of `keys_backup.json` to GitHub Secrets as `ENCRYPTION_KEYS`.

## CI/CD Pipeline

The system includes two GitHub Actions workflows:

### 1. Download Submissions Workflow (`download_submissions.yml`)

Automatically downloads new submissions from Google Classroom:

- **Trigger**: Runs hourly on schedule, or manually via workflow_dispatch
- **Process**:
  1. Authenticates with Google Classroom API
  2. Downloads new submissions based on `ASSIGNMENTS_CONFIG`
  3. Encrypts files with student-specific keys
  4. Commits encrypted files to student branches
  5. Triggers the grading workflow

### 2. Grading Workflow (`grade_submission.yml`)

Automatically grades submissions when they arrive:

- **Trigger**: Runs on push to `student-*` branches
- **Process**:
  1. Extracts student ID and assignment ID from branch name
  2. Decrypts submission files
  3. Executes and grades the notebook
  4. Generates grading report
  5. Uploads report as artifact
  6. (TODO) Sends results to student

## Grading Logic

The grader:
1. Executes the Jupyter notebook
2. Extracts JSON outputs from cell outputs
3. Compares with expected outputs
4. Calculates score based on matches
5. Generates detailed report with mismatches

## Troubleshooting

### "Credentials file not found"
- Ensure `credentials.json` is in the project root
- Follow the Google Classroom API setup instructions

### "GITHUB_TOKEN not set"
- Check your `.env` file
- Ensure the token has `repo` permissions

### "No encryption key found"
- Keys are generated automatically on first submission
- Ensure `student_keys/` directory exists

### Notebook execution fails
- Check notebook has valid Python code
- Ensure required libraries are in `requirements.txt`
- Check CI/CD logs for detailed errors

## Future Enhancements

- [ ] Email notification system
- [ ] Google Classroom grade posting
- [ ] Support for multiple notebooks per assignment
- [ ] Web dashboard for viewing results
- [ ] Support for other file types (PDF, docx, etc.)
- [ ] Plagiarism detection
- [ ] Manual override for grades

## Contributing

Feel free to submit issues and enhancement requests!

## License

MIT License
