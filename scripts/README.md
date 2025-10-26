# Scripts Directory

Helper scripts for managing the homework grading system.

## Quick Reference

| Script | Purpose | Usage |
|--------|---------|-------|
| `auto_discover_assignments.py` | Auto-discover all assignments | `python scripts/auto_discover_assignments.py` |
| `list_classroom_info.py` | Browse courses/assignments | `python scripts/list_classroom_info.py` |
| `export_secrets.py` | Export secrets for GitHub | `python scripts/export_secrets.py` |
| `verify_secrets.py` | Verify secrets before upload | `python scripts/verify_secrets.py` |
| `download_submissions.py` | Download submissions (CI/CD) | Used by GitHub Actions |
| `run_grader.py` | Grade a submission (CI/CD) | Used by GitHub Actions |
| `decrypt_submission.py` | Decrypt files (CI/CD) | Used by GitHub Actions |
| `send_results.py` | Send results (CI/CD) | Used by GitHub Actions |

## Setup Workflow

### 1. Auto-Discover All Assignments

```bash
# Discover all published assignments from all active courses
python scripts/auto_discover_assignments.py

# Preview without saving
python scripts/auto_discover_assignments.py --dry-run

# Include archived courses
python scripts/auto_discover_assignments.py --include-archived

# Include draft assignments
python scripts/auto_discover_assignments.py --state PUBLISHED DRAFT
```

This creates `assignments_config.json` with all your assignments.

### 2. Review and Edit (Optional)

```bash
# Edit the generated config to remove unwanted assignments
nano assignments_config.json
```

### 3. Verify Secrets

```bash
# Check all files are valid before exporting
python scripts/verify_secrets.py
```

### 4. Export for GitHub

```bash
# Generate values to copy to GitHub Secrets
python scripts/export_secrets.py
```

### 5. Manual Browse (Alternative)

```bash
# Interactive browser for courses and assignments
python scripts/list_classroom_info.py

# Just list courses
python scripts/list_classroom_info.py courses

# List assignments for a course
python scripts/list_classroom_info.py assignments COURSE_ID
```

## Script Details

### auto_discover_assignments.py

Automatically discovers all assignments from Google Classroom.

**Features:**
- Fetches all courses and their assignments
- Filters by course state (active/archived)
- Filters by assignment state (published/draft/deleted)
- Generates `assignments_config.json` automatically

**Options:**
```bash
--include-archived    # Include archived courses
--state PUBLISHED     # Filter by assignment state (default: PUBLISHED)
--output FILE         # Custom output path (default: assignments_config.json)
--dry-run            # Preview without saving
```

**Examples:**
```bash
# Get all published assignments from active courses
python scripts/auto_discover_assignments.py

# Get all assignments including archived courses
python scripts/auto_discover_assignments.py --include-archived

# Preview what would be generated
python scripts/auto_discover_assignments.py --dry-run

# Save to custom location
python scripts/auto_discover_assignments.py --output my_config.json
```

### list_classroom_info.py

Interactive browser for exploring courses and assignments.

**Modes:**
1. **Interactive mode** (default): Browse courses → Select → View assignments
2. **List courses**: Show all courses with IDs
3. **List assignments**: Show assignments for a specific course

**Examples:**
```bash
# Interactive browser
python scripts/list_classroom_info.py

# List all courses
python scripts/list_classroom_info.py courses

# List assignments for specific course
python scripts/list_classroom_info.py assignments 123456789
```

### export_secrets.py

Exports all secrets in the correct format for GitHub.

**Exports:**
- GOOGLE_CREDENTIALS (JSON)
- GOOGLE_TOKEN (base64)
- ENCRYPTION_KEYS (JSON with base64 keys)
- ASSIGNMENTS_CONFIG (JSON)

**Usage:**
```bash
python scripts/export_secrets.py
```

Saves all values to `github_secrets_export.txt` for easy copying.

### verify_secrets.py

Verifies all files are properly formatted before exporting.

**Checks:**
- credentials.json is valid JSON
- token.json can be base64 encoded/decoded
- Encryption keys are exportable
- assignments_config.json is valid JSON

**Usage:**
```bash
python scripts/verify_secrets.py
```

Returns exit code 0 if all checks pass, 1 if any fail.

### download_submissions.py

Downloads submissions from Google Classroom (used by GitHub Actions).

**Environment Variables:**
- `COURSE_ID`: Specific course to process (optional)
- `COURSEWORK_ID`: Specific assignment to process (optional)
- `ASSIGNMENTS_CONFIG`: JSON config of assignments (optional)

**Usage:**
```bash
# Process all configured assignments
python scripts/download_submissions.py

# Process specific assignment
COURSE_ID=123 COURSEWORK_ID=456 python scripts/download_submissions.py
```

### run_grader.py

Grades a student submission (used by GitHub Actions).

**Usage:**
```bash
python scripts/run_grader.py \
  --student-id STUDENT_ID \
  --assignment-id ASSIGNMENT_ID \
  --output reports/grade_report.json
```

### decrypt_submission.py

Decrypts student files (used by GitHub Actions).

**Usage:**
```bash
python scripts/decrypt_submission.py \
  --student-id STUDENT_ID \
  --assignment-id ASSIGNMENT_ID
```

### send_results.py

Sends grading results to students (used by GitHub Actions).

**Usage:**
```bash
python scripts/send_results.py \
  --student-id STUDENT_ID \
  --assignment-id ASSIGNMENT_ID \
  --report reports/grade_report.json
```

## Common Workflows

### Initial Setup

```bash
# 1. Authenticate
python example_usage.py

# 2. Auto-discover assignments
python scripts/auto_discover_assignments.py

# 3. Verify everything
python scripts/verify_secrets.py

# 4. Export for GitHub
python scripts/export_secrets.py

# 5. Copy values to GitHub Secrets
```

### Update Assignment List

```bash
# Re-discover all assignments
python scripts/auto_discover_assignments.py

# Export updated config
python scripts/export_secrets.py

# Update ASSIGNMENTS_CONFIG in GitHub Secrets
```

### Manual Assignment Selection

```bash
# Browse and note IDs
python scripts/list_classroom_info.py

# Manually create config
nano assignments_config.json

# Verify and export
python scripts/verify_secrets.py
python scripts/export_secrets.py
```

### Test Locally

```bash
# Download submissions locally
python scripts/download_submissions.py

# Grade a submission
python scripts/run_grader.py \
  --student-id test_student \
  --assignment-id homework1 \
  --output report.json
```

## Troubleshooting

### "No assignments found"

```bash
# Check what's available
python scripts/list_classroom_info.py courses

# Try including archived courses
python scripts/auto_discover_assignments.py --include-archived
```

### "Invalid JSON" errors

```bash
# Verify all files
python scripts/verify_secrets.py

# Check specific file
python -m json.tool assignments_config.json
```

### "Authentication failed"

```bash
# Re-authenticate
rm token.json
python example_usage.py
```

### "No student keys found"

```bash
# Process at least one test submission first
python example_usage.py
# Then export keys
python scripts/export_secrets.py
```
