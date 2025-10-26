# GitHub Actions Workflows Guide

This document explains the two automated workflows in the homework grading system.

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Complete Automation Flow                     │
└─────────────────────────────────────────────────────────────────┘

  ┌──────────────────┐
  │ Google Classroom │ Student submits homework
  └────────┬─────────┘
           │
           ▼
  ┌─────────────────────────┐
  │ Download Workflow       │ Runs every hour (or manual)
  │ (Scheduled)             │
  ├─────────────────────────┤
  │ 1. Fetch submissions    │
  │ 2. Encrypt files        │
  │ 3. Commit to GitHub     │
  └────────┬────────────────┘
           │
           │ Push to student-*/assignment-* branch
           ▼
  ┌─────────────────────────┐
  │ Grading Workflow        │ Triggered by push
  │ (On Push)               │
  ├─────────────────────────┤
  │ 1. Decrypt files        │
  │ 2. Execute notebook     │
  │ 3. Compare outputs      │
  │ 4. Generate report      │
  │ 5. Upload artifact      │
  └────────┬────────────────┘
           │
           ▼
  ┌──────────────────┐
  │ Student receives │ Report available
  │ grading results  │
  └──────────────────┘
```

## Workflow 1: Download Submissions

**File**: `.github/workflows/download_submissions.yml`

### When It Runs

1. **Scheduled**: Every hour (cron: `0 * * * *`)
2. **Manual**: Via GitHub Actions UI with optional parameters

### Manual Trigger

To manually trigger the download workflow:

1. Go to your GitHub repository
2. Click "Actions" tab
3. Select "Download Student Submissions" workflow
4. Click "Run workflow"
5. (Optional) Enter specific course_id and coursework_id
6. Click "Run workflow"

### Configuration

The workflow needs the `ASSIGNMENTS_CONFIG` secret with this format:

```json
[
  {
    "name": "Homework 1 - Intro to Python",
    "course_id": "123456789",
    "coursework_id": "987654321"
  },
  {
    "name": "Homework 2 - Data Analysis",
    "course_id": "123456789",
    "coursework_id": "987654322"
  }
]
```

### How to Get Course and Coursework IDs

```python
from src.submission_processor import SubmissionProcessor

processor = SubmissionProcessor()

# List all courses
processor.list_courses()
# Note the course ID

# List coursework in a course
processor.list_coursework(course_id="YOUR_COURSE_ID")
# Note the coursework ID
```

### Required Secrets

- `GOOGLE_CREDENTIALS`: Your credentials.json content
- `GOOGLE_TOKEN`: (Optional) Your token.json for avoiding re-auth
- `GITHUB_TOKEN`: Automatically provided by GitHub Actions
- `ASSIGNMENTS_CONFIG`: JSON array of assignments to monitor

### Workflow Steps

1. **Checkout code**: Gets the latest code
2. **Set up Python**: Installs Python 3.11
3. **Install dependencies**: Installs required packages
4. **Set up Google Classroom credentials**: Loads auth credentials
5. **Set up GitHub token**: Configures GitHub API access
6. **Download submissions**: Runs `scripts/download_submissions.py`
7. **Summary**: Generates a summary of downloaded submissions

### Output

- Downloads new submissions from Google Classroom
- Encrypts them with student-specific keys
- Commits to branches: `student-{student_id}/assignment-{assignment_id}`
- Creates `download_summary.txt` with results

## Workflow 2: Grade Submission

**File**: `.github/workflows/grade_submission.yml`

### When It Runs

Automatically triggered when code is pushed to any branch matching `student-*`

### Workflow Steps

1. **Checkout code**: Gets the submission
2. **Set up Python**: Installs Python 3.11
3. **Install dependencies**: Installs grading packages
4. **Extract student and assignment info**: Parses from branch name
5. **Decrypt submission files**: Uses student's encryption key
6. **Run grading tests**: Executes notebook and compares outputs
7. **Upload grading report**: Saves report as artifact
8. **Send results**: (TODO) Delivers results to student
9. **Log completion**: Records grading status

### Required Secrets

- `ENCRYPTION_KEYS`: JSON object with all student encryption keys
- `GOOGLE_CREDENTIALS`: For sending results back (future)

### Branch Naming Convention

Branches must follow this pattern:
```
student-{student_id}/assignment-{assignment_id}
```

Examples:
- `student-john.doe@example.com/assignment-hw1`
- `student-12345/assignment-lab2`

### Accessing Grading Reports

1. Go to your repository
2. Click "Actions" tab
3. Click on the workflow run
4. Scroll down to "Artifacts"
5. Download the grading report JSON

## Setting Up the Workflows

### Step 1: Add GitHub Secrets

Go to: Repository → Settings → Secrets and variables → Actions

Add these secrets:

```bash
# Google Classroom credentials
GOOGLE_CREDENTIALS: <content of credentials.json>

# After first local authentication, add token
GOOGLE_TOKEN: <content of token.json>

# Student encryption keys (export from local setup)
ENCRYPTION_KEYS: <JSON object with student keys>

# Assignments to auto-download
ASSIGNMENTS_CONFIG: <JSON array of assignments>
```

### Step 2: Export Encryption Keys

After processing some submissions locally:

```python
from src.encryption import EncryptionManager
from pathlib import Path

manager = EncryptionManager()
manager.export_keys(Path("keys_backup.json"))
```

Copy content of `keys_backup.json` to `ENCRYPTION_KEYS` secret.

### Step 3: Configure Assignments

Create `ASSIGNMENTS_CONFIG` secret with your assignments:

```json
[
  {
    "name": "Week 1 Assignment",
    "course_id": "YOUR_COURSE_ID",
    "coursework_id": "YOUR_COURSEWORK_ID"
  }
]
```

### Step 4: Verify Workflows

1. Check that both workflow files are in `.github/workflows/`
2. Push to GitHub
3. Manually trigger the download workflow to test
4. Check the Actions tab for results

## Monitoring and Debugging

### View Workflow Runs

1. Go to "Actions" tab
2. Select the workflow
3. Click on a specific run
4. Review logs for each step

### Common Issues

**Download workflow fails with authentication error:**
- Check `GOOGLE_CREDENTIALS` secret is set correctly
- Add `GOOGLE_TOKEN` secret to avoid OAuth prompts

**Grading workflow can't decrypt files:**
- Ensure `ENCRYPTION_KEYS` secret includes the student's key
- Verify key format matches export format

**No submissions downloaded:**
- Check `ASSIGNMENTS_CONFIG` has correct IDs
- Verify students have submitted work
- Review download workflow logs

**Grading fails:**
- Check test cases exist in `test_cases/{assignment_id}/expected_output.json`
- Review notebook execution logs
- Ensure notebook has valid Python code

### Viewing Logs

Each workflow step produces logs:

```
Actions → Select Workflow → Select Run → Click on Step
```

Download workflow logs show:
- Courses and assignments found
- Submissions downloaded
- Files encrypted and committed

Grading workflow logs show:
- Decryption status
- Notebook execution output
- Grading results and scores

## Customization

### Change Download Schedule

Edit `.github/workflows/download_submissions.yml`:

```yaml
schedule:
  # Run every 30 minutes
  - cron: '*/30 * * * *'

  # Run daily at 8 AM UTC
  - cron: '0 8 * * *'

  # Run every 6 hours
  - cron: '0 */6 * * *'
```

### Add Email Notifications

Extend `scripts/send_results.py` to send emails:

```python
import smtplib
from email.mime.text import MIMEText

def send_email(student_email, subject, body):
    # Configure your SMTP settings
    ...
```

Add email secrets to GitHub:
- `SMTP_SERVER`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`

### Add Slack Notifications

Add to grading workflow:

```yaml
- name: Notify Slack
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    text: 'Grading completed for ${{ steps.extract_info.outputs.student_id }}'
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

## Best Practices

1. **Test locally first**: Run scripts manually before relying on automation
2. **Monitor initially**: Check workflow runs frequently when first deployed
3. **Backup keys**: Keep a secure backup of `ENCRYPTION_KEYS`
4. **Limit scope**: Start with one course/assignment, then expand
5. **Review logs**: Regularly check workflow logs for errors
6. **Update token**: Refresh `GOOGLE_TOKEN` if authentication expires

## Security Considerations

1. **Secrets Management**:
   - Never commit secrets to Git
   - Use GitHub Secrets for all sensitive data
   - Rotate tokens periodically

2. **Access Control**:
   - Limit who can trigger workflows
   - Use branch protection rules
   - Review workflow permissions

3. **Data Privacy**:
   - Student files are encrypted before GitHub storage
   - Decrypted files only exist temporarily in workflow
   - Reports don't include sensitive student data

## Troubleshooting Commands

```bash
# Test download script locally
python scripts/download_submissions.py

# Test grading script locally
python scripts/run_grader.py \
  --student-id test_student \
  --assignment-id test_assignment \
  --output report.json

# View workflow logs
gh run list
gh run view <run-id>
gh run view <run-id> --log

# Trigger workflow manually
gh workflow run download_submissions.yml
```
