# Test Cases Directory

This directory contains expected outputs for grading assignments.

## Directory Structure

Each assignment should have its own directory named using the **sanitized assignment name**:

```
test_cases/
├── homework-1-variables/
│   └── expected_output.json
├── lab-2-functions/
│   └── expected_output.json
└── final-project/
    └── expected_output.json
```

## Assignment Name Format

Assignment names are automatically sanitized from Google Classroom titles:

| Original Title | Sanitized Name |
|---------------|----------------|
| "Homework 1 - Variables" | `homework-1-variables` |
| "Lab #2: Functions!" | `lab-2-functions` |
| "Final Project (2024)" | `final-project-2024` |

**Rules:**
- Converted to lowercase
- Spaces and special characters → hyphens
- Multiple hyphens → single hyphen
- Max 50 characters

## How to Find Assignment Names

### Method 1: Check branch names in GitHub

After a submission is processed, check the branch name:
```
student-john_at_example_com/assignment-homework-1-variables
                                      ^^^^^^^^^^^^^^^^^^^^
                                      This is the assignment name
```

### Method 2: Check workflow logs

Look at the download workflow logs:
```
Assignment title: Homework 1 - Variables
```

The sanitized version will be `homework-1-variables`.

### Method 3: Run locally

```python
from src.submission_processor import SubmissionProcessor

processor = SubmissionProcessor()

# This will show the assignment name
processor._sanitize_name("Homework 1 - Variables")
# Output: 'homework-1-variables'
```

## Creating Test Cases

### 1. Create directory with assignment name

```bash
mkdir -p test_cases/homework-1-variables
```

### 2. Create expected_output.json

```bash
nano test_cases/homework-1-variables/expected_output.json
```

### 3. Define expected JSON outputs

The grader expects a JSON array of expected outputs:

```json
[
  {
    "result": 42,
    "message": "success"
  },
  {
    "data": [1, 2, 3, 4, 5],
    "length": 5
  }
]
```

Each item in the array corresponds to one JSON output from the notebook.

## Student Notebook Format

Students should print JSON outputs using `json.dumps()`:

```python
import json

# Task 1
result = {
    "result": 42,
    "message": "success"
}
print(json.dumps(result))

# Task 2
data = [1, 2, 3, 4, 5]
output = {
    "data": data,
    "length": len(data)
}
print(json.dumps(output))
```

## Grading Process

1. Student notebook is executed
2. JSON outputs are extracted from cell outputs
3. Each output is compared with expected_output.json
4. Score = (matches / total_expected) * 100%

## Example Test Case

See `homework-1-example/` for a complete example with:
- expected_output.json
- README.md with assignment instructions
- sample_solution.ipynb

## Troubleshooting

### "No expected output file found"

**Cause:** The test case directory doesn't match the sanitized assignment name.

**Solution:**
1. Check the exact assignment name from logs or branch
2. Create directory with exact name: `test_cases/{assignment-name}/`
3. Add `expected_output.json`

### "No matches found"

**Cause:** Student output doesn't match expected format.

**Solutions:**
- Check student is using `json.dumps()` to print outputs
- Verify JSON structure matches exactly
- Check for whitespace differences
- Review grading report for details

## Tips

1. **Use descriptive assignment names** in Google Classroom (they become directory names)
2. **Test your test cases** with the sample solution first
3. **Version control** test cases in git
4. **Document** expected behavior in assignment READMEs
5. **Keep** expected outputs simple and focused on learning objectives
