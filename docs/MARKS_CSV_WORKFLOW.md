# Marks CSV Generation Workflow

This document explains the workflow for generating a CSV file with student marks from GitHub Pull Requests.

## Overview

The `generate_marks_csv.yml` workflow extracts student marks from Pull Requests and generates a CSV file with:
- **Rows**: One student per row
- **Columns**: One homework assignment per column
- **Values**: Percentage scores (0-100)

## How It Works

### 1. PR Title Format

The workflow looks for PRs with titles following this pattern:
```
Submission: {student_email} - {homework_name}
```

**Examples:**
- `Submission: ayumikhaylyuk_at_gmail_com - Homework-4`
- `Submission: john.doe@example.com - Lab-Assignment-2`
- `Submission: student123@university.edu - Final-Project`

### 2. Score Extraction

Scores are extracted from the **last comment** on each PR. The script looks for these patterns:

**Pattern 1: Score with fraction**
```
Score: 85/100
Score: 42.5 / 50
```

**Pattern 2: Score with percentage**
```
Score: 85.5%
Grade: 92%
```

**Pattern 3: Grading report format**
```
earned_points: 85
total_points: 100
```

**Pattern 4: General score mention**
```
The final score is 88%
Your grade for this assignment: 75%
```

### 3. CSV Output Format

The generated CSV file has this structure:

```csv
Student,Homework-1,Homework-2,Homework-3,Homework-4
john.doe@example.com,85.0,92.5,,88.0
jane.smith@example.com,90.0,95.0,78.5,
ayumikhaylyuk_at_gmail_com,88.0,,,85.0
```

- First column: Student email
- Remaining columns: One per homework (sorted alphabetically)
- Values: Percentage scores (empty if not submitted/graded)

## Running the Workflow

### Automatic Runs

The workflow runs automatically:
- **Weekly**: Every Sunday at 8 AM UTC
- Schedule can be adjusted in `.github/workflows/generate_marks_csv.yml`

### Manual Trigger

To generate the CSV on demand:

1. Go to your GitHub repository
2. Click the **Actions** tab
3. Select **Generate Marks CSV** workflow
4. Click **Run workflow** button
5. Click **Run workflow** to confirm

### Accessing the CSV

After the workflow completes:

1. Go to the workflow run in the **Actions** tab
2. Scroll down to **Artifacts** section
3. Download `marks-csv-{run_number}`
4. Extract the ZIP file to get `marks.csv`

## Workflow Configuration

### Required Permissions

The workflow needs these permissions (automatically granted):
- `contents: read` - To checkout the repository
- `pull-requests: read` - To read PR information

### Dependencies

The workflow installs:
- Python 3.11
- `requests` library (for GitHub API calls)

No additional configuration or secrets are required beyond the default `GITHUB_TOKEN`.

## Script Details

### Location

The script is located at: `scripts/generate_marks_csv.py`

### Usage

```bash
python scripts/generate_marks_csv.py \
  --repo "owner/repo" \
  --output reports/marks.csv \
  [--token GITHUB_TOKEN]
```

**Arguments:**
- `--repo`: Repository in format "owner/repo" (required)
- `--output`: Output CSV file path (default: reports/marks.csv)
- `--token`: GitHub API token (or use GITHUB_TOKEN env var)

### Testing Locally

To test the script locally:

```bash
# Set your GitHub token
export GITHUB_TOKEN=your_github_token

# Run the script
python scripts/generate_marks_csv.py \
  --repo martins0n/hw-test-grader \
  --output test_marks.csv
```

## Troubleshooting

### No PRs Found

**Issue**: "No submission PRs found"

**Solutions:**
- Check that PRs exist with titles matching: `Submission: {email} - {homework}`
- Verify PRs are not filtered by state (workflow checks all states)
- Ensure you have read permissions on the repository

### No Scores Found

**Issue**: "No score found" warnings for specific PRs

**Solutions:**
- Check that PRs have comments with score information
- Verify comment format matches one of the supported patterns
- Ensure the score appears in the **last comment** (most recent)
- Comments should include phrases like "Score:", "Grade:", or percentage values

### API Rate Limiting

**Issue**: GitHub API rate limit errors

**Solutions:**
- Authenticated requests have higher rate limits (5000/hour)
- The workflow uses `GITHUB_TOKEN` automatically
- For manual runs, ensure token is provided
- Space out manual runs if hitting limits

### Missing Homeworks in CSV

**Issue**: Some homework columns are missing

**Solutions:**
- CSV only includes homeworks that have at least one submission
- Check PR titles match the expected format exactly
- Homework names are case-sensitive

## Customization

### Change Schedule

Edit `.github/workflows/generate_marks_csv.yml`:

```yaml
schedule:
  # Run daily at midnight
  - cron: '0 0 * * *'
  
  # Run twice a week (Monday and Thursday at 9 AM)
  - cron: '0 9 * * 1,4'
  
  # Run on first day of each month
  - cron: '0 0 1 * *'
```

### Modify Score Patterns

Edit `scripts/generate_marks_csv.py` in the `extract_score_from_comment()` function to add new patterns:

```python
# Add custom pattern
pattern5 = r'Final Grade:\s*(\d+\.?\d*)'
match = re.search(pattern5, comment_body, re.IGNORECASE)
if match:
    return float(match.group(1))
```

### Change CSV Format

Modify the CSV writing section in `generate_marks_csv()`:

```python
# Example: Add total column
row = [student]
total = 0
count = 0
for homework in homeworks:
    score = marks[student].get(homework, '')
    if score != '':
        row.append(f'{score:.1f}')
        total += score
        count += 1
    else:
        row.append('')

# Add average
if count > 0:
    row.append(f'{total/count:.1f}')
else:
    row.append('')

writer.writerow(row)
```

## Integration with Existing Workflows

This workflow complements the existing grading workflows:

1. **grade_submission.yml**: Grades individual submissions and posts comments
2. **aggregate_grades.yml**: Aggregates grades from workflow artifacts
3. **generate_marks_csv.yml**: Consolidates all marks into a single CSV

All three can run simultaneously and serve different purposes:
- `grade_submission.yml`: Immediate feedback to students
- `aggregate_grades.yml`: Per-assignment grade exports
- `generate_marks_csv.yml`: Overall class gradebook

## Best Practices

1. **Consistent PR Titles**: Enforce the title format for all submissions
2. **Clear Score Comments**: Post scores in a consistent format
3. **Regular Runs**: Schedule the workflow to run regularly for up-to-date data
4. **Backup CSV Files**: Download and backup CSV artifacts periodically
5. **Verify Scores**: Spot-check the generated CSV against actual submissions

## Example Workflow

Here's a typical usage scenario:

1. **Student Submission**: Student submits via Google Classroom
2. **Auto-grading**: `grade_submission.yml` runs and posts score comment
3. **PR Created**: PR titled "Submission: student@email.com - Homework-X"
4. **Score Comment**: Last comment contains "Score: 85/100"
5. **Weekly CSV**: `generate_marks_csv.yml` runs Sunday morning
6. **Download**: Teacher downloads CSV with all current marks
7. **Import**: CSV imported into gradebook or LMS

## Support

For issues or questions:
- Check the workflow logs in the Actions tab
- Review PR title and comment formats
- Verify GitHub token permissions
- See the main README.md for general troubleshooting
