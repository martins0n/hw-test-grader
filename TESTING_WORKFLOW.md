# Testing the Generate Marks CSV Workflow

This guide explains how to test the "Generate Marks CSV" workflow before merging to the default branch.

## Why Can't I Run the Workflow Directly?

GitHub Actions workflows are only available to run via `gh workflow run` if:
1. The workflow file exists on the **default branch** (usually `main` or `master`), OR
2. The workflow has already been triggered and run at least once

Since this workflow is currently on a feature branch (`copilot/create-github-action-workflow`), it won't appear in the workflow list yet.

## Testing Options

### Option 1: Test the Script Locally (Recommended Before Merge)

Run the unit tests to verify the core logic:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the test suite
python scripts/test_generate_marks_csv.py
```

This will test:
- PR title parsing
- Score extraction from comments
- All supported score formats

**Example output:**
```
============================================================
Testing generate_marks_csv.py functions
============================================================

Testing PR title parsing...
  ✓ 'Submission: ayumikhaylyuk_at_gmail_com - Homework-4' -> ('ayumikhaylyuk_at_gmail_com', 'Homework-4')
  ...

✅ All tests passed!
```

### Option 2: Test with Real PRs Locally

If you want to test with actual PRs from your repository:

```bash
# Set your GitHub token
export GITHUB_TOKEN=your_github_token

# Run the script manually
python scripts/generate_marks_csv.py \
  --repo martins0n/hw-test-grader \
  --output /tmp/test_marks.csv

# Check the output
cat /tmp/test_marks.csv
```

This will:
1. Fetch all PRs from the repository
2. Extract marks from PR titles and comments
3. Generate a CSV file

**Note:** This requires PRs with titles matching the pattern `Submission: {email} - {homework}` to exist in the repository.

### Option 3: Test After Merging

After merging to the default branch:

1. **Manual trigger via GitHub UI:**
   - Go to repository → Actions tab
   - Select "Generate Marks CSV" workflow
   - Click "Run workflow"
   - Select branch and click "Run workflow"

2. **Manual trigger via CLI:**
   ```bash
   gh workflow run "Generate Marks CSV"
   ```

3. **Wait for scheduled run:**
   - The workflow runs automatically every Sunday at 8 AM UTC
   - Check the Actions tab after the scheduled time

## Verifying the Output

After running the workflow (locally or on GitHub):

1. **Local testing:**
   ```bash
   # Check if CSV was created
   ls -lh reports/marks.csv
   
   # View the CSV
   cat reports/marks.csv
   
   # Or use column for better formatting
   column -t -s, reports/marks.csv
   ```

2. **GitHub Actions:**
   - Go to Actions tab → Select the workflow run
   - Scroll to "Artifacts" section
   - Download `marks-csv-{run_number}`
   - Extract and open `marks.csv`

## Expected CSV Format

The generated CSV should look like:

```csv
Student,Homework-1,Homework-2,Homework-3,Homework-4
john.doe@example.com,85.0,92.5,,88.0
jane.smith@example.com,90.0,95.0,78.5,
ayumikhaylyuk_at_gmail_com,88.0,,,85.0
```

Where:
- First column: Student email addresses
- Remaining columns: Homework assignments (sorted alphabetically)
- Values: Percentage scores (empty if not submitted/graded)

## Troubleshooting

### "could not find any workflows named Generate Marks CSV"

This is expected on feature branches. The workflow needs to be on the default branch first. Use Option 1 or 2 above to test before merging.

### "No submission PRs found"

- Ensure PRs exist with titles matching: `Submission: {email} - {homework}`
- Check that PRs are accessible with your GitHub token
- Verify the repository name is correct

### "No score found" warnings

- Check that PRs have comments with score information
- Verify comment format matches supported patterns (see docs/MARKS_CSV_WORKFLOW.md)
- Ensure scores are in the **last comment** of each PR

### Script errors

If the script fails:
1. Check you have the required dependencies: `pip install -r requirements.txt`
2. Verify your GitHub token has correct permissions
3. Check Python version (3.11+ recommended)

## Pre-Merge Checklist

Before merging this PR, verify:

- [ ] Unit tests pass: `python scripts/test_generate_marks_csv.py`
- [ ] Script can parse PR titles correctly
- [ ] Script can extract scores from various comment formats
- [ ] (Optional) Script works with actual PRs: `python scripts/generate_marks_csv.py --repo ... --output /tmp/test.csv`
- [ ] Workflow YAML syntax is valid
- [ ] Documentation is complete

## Post-Merge Verification

After merging to the default branch:

1. Trigger the workflow manually (see Option 3)
2. Check workflow logs for any errors
3. Download the artifact and verify CSV format
4. Spot-check a few entries against actual PRs
5. If everything looks good, let it run on schedule

## Questions?

See the full documentation in `docs/MARKS_CSV_WORKFLOW.md` for:
- Detailed usage instructions
- Customization options
- Integration with existing workflows
- Troubleshooting guide
