# Troubleshooting Guide

Common issues and solutions for the homework grading system.

## GitHub Actions Errors

### Error: "Resource not accessible by integration" (403)

**Full error:**
```
Request POST /repos/username/repo/git/refs failed with 403: Forbidden
Resource not accessible by integration
```

**Cause**: The default `GITHUB_TOKEN` doesn't have permission to create branches.

**Solution**: Add a Personal Access Token (PAT)

1. **Create a Personal Access Token**:
   - Go to GitHub → Settings (your profile) → Developer settings
   - Personal access tokens → Tokens (classic)
   - Generate new token (classic)
   - Name: `homework-grader`
   - Select scope: **repo** (all)
   - Generate and copy the token

2. **Add as GitHub Secret**:
   - Go to your repository → Settings → Secrets and variables → Actions
   - New repository secret
   - Name: `PAT_TOKEN`
   - Value: Your token
   - Add secret

3. **Re-run the workflow**

The workflow will automatically use `PAT_TOKEN` if available, otherwise falls back to `GITHUB_TOKEN`.

### Error: "credentials.json is not valid JSON"

**Cause**: The GOOGLE_CREDENTIALS secret has invalid JSON.

**Solution**:
```bash
# Verify locally first
python -m json.tool credentials.json

# Re-export
python scripts/export_secrets.py

# Update GitHub Secret with the exact output
```

Make sure you copy the **entire** JSON from `{` to `}` with no extra spaces.

### Error: "base64: invalid input"

**Cause**: The GOOGLE_TOKEN secret has invalid base64.

**Solutions**:

**Option 1**: Re-export the token
```bash
rm token.json
python example_usage.py  # Re-authenticate
python scripts/export_secrets.py  # Re-export
# Update GOOGLE_TOKEN in GitHub Secrets
```

**Option 2**: Remove the token secret
- Go to GitHub Secrets and delete `GOOGLE_TOKEN`
- The workflow will work without it (may require re-auth periodically)

### Error: "No courses or assignments configured"

**Cause**: Missing COURSE_IDS, COURSES_CONFIG, or ASSIGNMENTS_CONFIG secret.

**Solution**:
```bash
# Get your course IDs
python scripts/list_classroom_info.py courses

# Add to .env
echo "COURSE_IDS=123456789" >> .env

# Export
python scripts/export_secrets.py

# Add COURSE_IDS to GitHub Secrets
```

## Local Errors

### Error: "Scope has changed"

**Full error:**
```
Warning: Scope has changed from "..." to "..."
```

**Cause**: Cached token has different OAuth scopes.

**Solution**:
```bash
rm token.json
python example_usage.py  # Re-authenticate
```

### Error: "Credentials file not found"

**Cause**: Missing `credentials.json` file.

**Solution**:
1. Follow Google Cloud setup in README.md
2. Download OAuth credentials
3. Save as `credentials.json` in project root

### Error: "No encryption key found"

**Cause**: Student hasn't had any submissions processed yet.

**Solution**:
This is normal! Keys are generated automatically when you process the first submission. Export keys AFTER processing:

```bash
# Process at least one submission
python example_usage.py

# Then export keys
python scripts/export_secrets.py

# Add ENCRYPTION_KEYS to GitHub
```

### Error: "Failed to execute notebook"

**Possible causes and solutions**:

**Missing dependencies**:
```bash
# Add to requirements.txt
echo "pandas" >> requirements.txt
echo "numpy" >> requirements.txt
pip install -r requirements.txt
```

**Syntax errors in notebook**:
- Review the notebook manually
- Check CI/CD logs for specific error
- Student needs to fix and resubmit

**Timeout**:
```python
# Increase timeout in src/grader.py
grader = NotebookGrader(timeout=1200)  # 20 minutes
```

### Error: Import errors in scripts

**Cause**: Running from wrong directory or Python path issues.

**Solution**:
```bash
# Always run from project root
cd /path/to/homeworkgrader

# Run scripts with python -m or direct path
python scripts/export_secrets.py
# or
python -m scripts.export_secrets
```

## Workflow Not Triggering

### Schedule not running

**Possible causes**:

1. **Workflow disabled**:
   - Go to Actions → Enable workflow

2. **Repository inactive**:
   - GitHub may disable scheduled workflows after 60 days of no activity
   - Make any commit to re-enable

3. **Branch mismatch**:
   - Workflow must be on default branch (main/master)
   - Check: Repository → Settings → Branches → Default branch

**Test manually**:
```bash
# Go to Actions → Download Student Submissions → Run workflow
```

### Workflow runs but does nothing

**Check logs**:
1. Actions → Select workflow run
2. Click on job → Expand steps
3. Look for errors in "Download submissions" step

**Common issues**:
- No new submissions: Normal, will process next time
- No assignments configured: Add COURSE_IDS
- Authentication failed: Check GOOGLE_CREDENTIALS

## Grading Issues

### Notebook executes but score is 0

**Possible causes**:

1. **No JSON output**:
   - Student notebook doesn't print JSON
   - Check expected_output.json exists

2. **Wrong JSON format**:
```python
# Student should use:
import json
result = {"answer": 42}
print(json.dumps(result))
```

3. **Output mismatch**:
   - Review the grading report in workflow artifacts
   - Check for subtle differences (whitespace, types)

### Expected outputs not found

**Error**: "No expected output file found"

**Solution**:
```bash
# Create test case
mkdir -p test_cases/ASSIGNMENT_ID
nano test_cases/ASSIGNMENT_ID/expected_output.json
```

**Example expected_output.json**:
```json
[
  {"result": 42, "message": "success"},
  {"data": [1, 2, 3]}
]
```

## Permission Issues

### "Permission denied" on scripts

**Solution**:
```bash
chmod +x scripts/*.py
```

### Can't write to directory

**Check permissions**:
```bash
ls -la
# Should show you as owner

# Fix if needed
sudo chown -R $USER:$USER .
```

## Authentication Issues

### Google OAuth keeps prompting

**Cause**: Token not saved or expired.

**Solution**:
```bash
# Make sure token.json is created
ls -la token.json

# If missing, re-authenticate
python example_usage.py

# Export for GitHub
python scripts/export_secrets.py
# Add GOOGLE_TOKEN to secrets
```

### "Invalid grant" error

**Cause**: Refresh token expired or revoked.

**Solution**:
```bash
# Delete and re-authenticate
rm token.json
python example_usage.py
```

### Can't access courses

**Cause**: Wrong account or insufficient permissions.

**Solutions**:
1. Make sure you're logged in as teacher/instructor
2. Check you have access to the courses
3. Verify API scopes include classroom.courses.readonly

## Debugging Tips

### Enable debug logging

```bash
# In .env
LOG_LEVEL=DEBUG
```

### Test individual components

```bash
# Test Google Classroom connection
python -c "from src.classroom_client import ClassroomClient; c = ClassroomClient(); print(len(c.list_courses()))"

# Test encryption
python -c "from src.encryption import EncryptionManager; e = EncryptionManager(); print('OK')"

# Test GitHub connection
python -c "from src.github_manager import GitHubManager; import os; from dotenv import load_dotenv; load_dotenv(); g = GitHubManager(os.getenv('GITHUB_TOKEN'), os.getenv('GITHUB_REPO')); print('OK')"

# Test grading
python scripts/run_grader.py --student-id test --assignment-id example_assignment --output test.json
```

### View detailed workflow logs

```bash
# Using GitHub CLI
gh run list
gh run view <run-id> --log
```

### Test locally before deploying

```bash
# Set up .env with all variables
cp .env.example .env
nano .env

# Test download
python scripts/download_submissions.py

# Test encryption
python -c "from src.encryption import EncryptionManager; e = EncryptionManager(); k = e.get_or_create_key('test'); print('OK')"

# Verify secrets
python scripts/verify_secrets.py
```

## Getting Help

### Before asking for help, collect:

1. **Error message** (full traceback)
2. **What you were trying to do**
3. **Workflow logs** (from GitHub Actions)
4. **Local test results**
5. **Environment info**:
   ```bash
   python --version
   pip list
   cat .env (remove sensitive values!)
   ```

### Check these first:

- [ ] Read relevant README sections
- [ ] Verified all secrets are set in GitHub
- [ ] Tested authentication locally
- [ ] Checked workflow permissions
- [ ] Reviewed workflow logs
- [ ] Tried re-authenticating
- [ ] Verified file permissions

### Common quick fixes:

```bash
# Nuclear option - start fresh
rm token.json
rm -rf student_keys/
python example_usage.py  # Re-authenticate
python scripts/export_secrets.py  # Re-export
# Update all GitHub Secrets
```
