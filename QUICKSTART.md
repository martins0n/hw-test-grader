# Quick Start Guide

Get your homework grading pipeline up and running in minutes.

## Step 1: Install Python Environment

```bash
# Install pyenv if not already installed
curl https://pyenv.run | bash

# Install Python 3.11
pyenv install 3.11.0

# Set local Python version
pyenv local 3.11.0

# Verify
python --version  # Should show Python 3.11.0
```

## Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 3: Set Up Google Classroom API

1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable "Google Classroom API"
4. Create OAuth 2.0 credentials (Desktop app)
5. Download `credentials.json` to project root

## Step 4: Set Up GitHub

1. Create a new repository (e.g., `username/homework-submissions`)
2. Generate a Personal Access Token:
   - Settings → Developer settings → Personal access tokens
   - Select `repo` scope
3. Copy `.env.example` to `.env`
4. Fill in your GitHub details:

```bash
cp .env.example .env
nano .env
```

## Step 5: First Run

```bash
# This will authenticate with Google Classroom
python example_usage.py
```

Follow the browser prompts to authorize the application.

## Step 6: Test the System

Test locally with the example assignment:

```bash
# Create a test submission directory
mkdir -p submissions/test_student/example_assignment

# Copy sample notebook
cp test_cases/example_assignment/sample_solution.ipynb \
   submissions/test_student/example_assignment/

# Run the grader
python scripts/run_grader.py \
  --student-id test_student \
  --assignment-id example_assignment \
  --output reports/test_report.json

# View results
cat reports/test_report.json
```

## Step 7: Process Real Submissions

```python
from src.submission_processor import SubmissionProcessor

processor = SubmissionProcessor()

# List your courses
processor.list_courses()

# List assignments in a course
processor.list_coursework(course_id="YOUR_COURSE_ID")

# Process submissions
processor.process_course_submissions(
    course_id="YOUR_COURSE_ID",
    coursework_id="YOUR_COURSEWORK_ID"
)
```

## Step 8: Set Up GitHub Actions

1. Go to your GitHub repository settings
2. Add repository secrets:
   - `ENCRYPTION_KEYS`: Export keys using:
     ```python
     from src.encryption import EncryptionManager
     from pathlib import Path

     manager = EncryptionManager()
     manager.export_keys(Path("keys.json"))
     # Copy content of keys.json to GitHub Secret
     ```
   - `GOOGLE_CREDENTIALS`: Copy content of `credentials.json`

3. Push the `.github/workflows/grade_submission.yml` file

4. GitHub Actions will now automatically grade submissions!

## Workflow Summary

```
Student → Google Classroom → Your Script → GitHub (encrypted) →
GitHub Actions → Grade → Report → Student
```

## Common Commands

```bash
# List courses
python -c "from src.submission_processor import SubmissionProcessor; \
           SubmissionProcessor().list_courses()"

# Process submissions
python example_usage.py

# Manual grading
python scripts/run_grader.py \
  --student-id STUDENT_ID \
  --assignment-id ASSIGNMENT_ID \
  --output report.json
```

## Troubleshooting

**Authentication fails**: Delete `token.json` and run again

**Import errors**: Make sure you're in the project directory and dependencies are installed

**No submissions found**: Check course_id and coursework_id are correct

**Grading fails**: Ensure test cases exist in `test_cases/ASSIGNMENT_ID/expected_output.json`

## Next Steps

- Set up email notifications (extend `scripts/send_results.py`)
- Create more test cases for your assignments
- Customize grading logic in `src/grader.py`
- Add support for additional file types

Need help? Check [README.md](README.md) for detailed documentation.
