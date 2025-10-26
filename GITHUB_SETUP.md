# GitHub Actions Setup Guide

Complete guide to setting up GitHub Secrets for the automated grading system.

## Prerequisites

1. Complete local setup (see QUICKSTART.md)
2. Authenticate with Google Classroom locally
3. Process at least one test submission

## Step 1: Export Secrets

Run the export helper script:

```bash
python scripts/export_secrets.py
```

This will display all the values you need to copy to GitHub Secrets.

## Step 2: Add Secrets to GitHub

### Navigate to Secrets Settings

1. Go to your GitHub repository
2. Click **Settings** tab
3. Click **Secrets and variables** → **Actions**
4. Click **"New repository secret"** for each secret below

### Required Secrets

#### 1. GOOGLE_CREDENTIALS

**What it is**: Your Google Cloud OAuth credentials file

**How to get it**:
```bash
# After running export_secrets.py, copy the JSON output from section 1
# OR manually:
cat credentials.json
```

**How to add**:
1. Click "New repository secret"
2. Name: `GOOGLE_CREDENTIALS`
3. Value: Paste the **entire** JSON content from credentials.json
4. Click "Add secret"

**Important**:
- Must be valid JSON (starts with `{`, ends with `}`)
- Include everything - don't remove quotes or brackets
- Don't add extra spaces or newlines at the beginning/end

**Example format**:
```json
{
  "installed": {
    "client_id": "123456789-abcdefg.apps.googleusercontent.com",
    "project_id": "your-project",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "GOCSPX-xxxxxxxxxxxxxxxxxxxxx",
    "redirect_uris": ["http://localhost"]
  }
}
```

#### 2. GOOGLE_TOKEN (Recommended)

**What it is**: Your authenticated session token (avoids re-authentication)

**How to get it**:
```bash
# After running export_secrets.py, copy the base64 string from section 2
```

**How to add**:
1. Click "New repository secret"
2. Name: `GOOGLE_TOKEN`
3. Value: Paste the **base64-encoded** string (looks like: `gASVkQIAAAAAAAB9lC4uLg==`)
4. Click "Add secret"

**Note**: This is a binary file encoded as base64. The workflow will decode it automatically.

#### 3. ENCRYPTION_KEYS (Required after first submission)

**What it is**: Student encryption keys for decrypting submissions

**How to get it**:
```bash
# After processing at least one submission locally
python scripts/export_secrets.py
# Copy the JSON from section 3
```

**How to add**:
1. Click "New repository secret"
2. Name: `ENCRYPTION_KEYS`
3. Value: Paste the JSON object
4. Click "Add secret"

**Example format**:
```json
{
  "student123@example.com": "Z0FTVmtBSUFBQUFBQUFBQnNsQzRB...",
  "student456@example.com": "eEZTVmtBSUFBQUFBQUFBQnNsQzRB..."
}
```

**Important**:
- Keys are base64-encoded
- Add this secret **after** you've processed your first submission
- Update this secret whenever you process submissions from new students

#### 4. ASSIGNMENTS_CONFIG (Optional, for automatic downloads)

**What it is**: List of assignments to automatically download

**How to create**:
```bash
# Option 1: Use the example
cp assignments_config.json.example assignments_config.json
nano assignments_config.json

# Option 2: Get course/assignment IDs programmatically
python -c "
from src.submission_processor import SubmissionProcessor
p = SubmissionProcessor()
p.list_courses()
# Note the course ID
p.list_coursework(course_id='YOUR_COURSE_ID')
# Note the coursework IDs
"
```

**Format**:
```json
[
  {
    "name": "Homework 1 - Introduction",
    "course_id": "123456789",
    "coursework_id": "987654321"
  },
  {
    "name": "Lab 2 - Data Analysis",
    "course_id": "123456789",
    "coursework_id": "987654322"
  }
]
```

**How to add**:
1. Click "New repository secret"
2. Name: `ASSIGNMENTS_CONFIG`
3. Value: Paste the JSON array
4. Click "Add secret"

## Step 3: Verify Setup

### Test the Download Workflow

1. Go to **Actions** tab in your repository
2. Click on **"Download Student Submissions"** workflow
3. Click **"Run workflow"** dropdown
4. Leave fields empty (will use ASSIGNMENTS_CONFIG)
5. Click **"Run workflow"** button
6. Wait for the workflow to complete
7. Check the logs for any errors

### Common Issues and Solutions

#### Issue: "credentials.json is not valid JSON"

**Cause**: GOOGLE_CREDENTIALS secret has invalid JSON

**Solution**:
1. Run `python scripts/export_secrets.py` locally
2. Copy the **exact** output from section 1
3. Make sure you copy the entire JSON (from `{` to `}`)
4. Re-add the GOOGLE_CREDENTIALS secret in GitHub
5. Make sure there are no extra characters before/after the JSON

**Verify locally**:
```bash
# This should output formatted JSON without errors
cat credentials.json | python -m json.tool
```

#### Issue: "ENCRYPTION_KEYS secret is not set"

**Cause**: You haven't processed any submissions yet, or secret not added

**Solution**:
1. Process at least one test submission locally first
2. Run `python scripts/export_secrets.py`
3. Copy the ENCRYPTION_KEYS JSON from section 3
4. Add it to GitHub Secrets

#### Issue: "GOOGLE_TOKEN not set - authentication may require manual intervention"

**Cause**: GOOGLE_TOKEN secret not added (this is just a warning)

**Solution**: This is optional. The workflow will work without it, but:
- Without token: May fail if Google requires interactive auth
- With token: Workflow can authenticate automatically

To add it:
1. Authenticate locally first: `python example_usage.py`
2. Run `python scripts/export_secrets.py`
3. Copy the base64 string from section 2
4. Add as GOOGLE_TOKEN secret

#### Issue: "No assignments configured"

**Cause**: ASSIGNMENTS_CONFIG secret not set

**Solution**:
1. Create assignments_config.json locally
2. Run `python scripts/export_secrets.py`
3. Copy the JSON from section 4
4. Add as ASSIGNMENTS_CONFIG secret

OR manually trigger with specific course/coursework IDs:
1. Go to Actions → Download Student Submissions
2. Click "Run workflow"
3. Enter course_id and coursework_id
4. Click "Run workflow"

## Step 4: Monitor Workflow Runs

### Viewing Logs

1. Go to **Actions** tab
2. Click on a workflow run
3. Click on the **"download"** job
4. Expand each step to see detailed logs

### Understanding the Output

**Successful run**:
```
✓ credentials.json validated successfully
✓ token.json decoded successfully
Processing submissions for course 123456789, assignment 987654321
Found 5 submissions
Processing submission xyz from student abc
Downloaded: homework.ipynb
✓ Encrypted: homework.ipynb.enc
Successfully uploaded 1 encrypted files to GitHub
```

**Failed run** - check logs for specific errors

## Step 5: Set Up Automatic Schedule (Optional)

The workflow runs every hour by default. To change the schedule:

Edit `.github/workflows/download_submissions.yml`:

```yaml
on:
  schedule:
    # Run every 30 minutes
    - cron: '*/30 * * * *'

    # Run every day at 9 AM UTC
    - cron: '0 9 * * *'

    # Run every Monday at 8 AM UTC
    - cron: '0 8 * * 1'
```

## Security Best Practices

1. **Never commit secrets to Git**
   - credentials.json ✗
   - token.json ✗
   - .env ✗
   - student_keys/ ✗

2. **Rotate tokens periodically**
   - Refresh GOOGLE_TOKEN every few months
   - Update ENCRYPTION_KEYS when adding new students

3. **Limit repository access**
   - Only trusted collaborators should have access
   - Use branch protection rules

4. **Review workflow logs**
   - Check for authentication failures
   - Monitor for unusual activity

5. **Backup encryption keys**
   - Keep a secure offline backup of student_keys/
   - Store ENCRYPTION_KEYS secret value somewhere safe

## Troubleshooting Commands

```bash
# Test credentials file locally
python -m json.tool credentials.json

# Verify token file exists
ls -lh token.json

# Test authentication locally
python -c "from src.submission_processor import SubmissionProcessor; SubmissionProcessor().list_courses()"

# Export all secrets again
python scripts/export_secrets.py

# Manual download test
python scripts/download_submissions.py
```

## Next Steps

After setup is complete:

1. ✅ Verify all secrets are added
2. ✅ Test download workflow manually
3. ✅ Check that submissions are encrypted and committed
4. ✅ Verify grading workflow triggers automatically
5. ✅ Review grading reports in workflow artifacts

See **WORKFLOWS.md** for detailed workflow documentation.
