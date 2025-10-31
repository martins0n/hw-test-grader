# Test Cases Directory

This directory contains expected outputs for grading assignments.

## Directory Structure

Each assignment should have its own directory named using the **sanitized assignment name**:

```
test_cases/
├── homework-1-variables/
│   ├── expected_output.json
│   └── requirements.txt (optional)
├── lab-2-functions/
│   ├── expected_output.json
│   └── requirements.txt (optional)
└── final-project/
    ├── expected_output.json
    └── requirements.txt (optional)
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

#### Legacy Format (Simple output comparison)

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

#### Enhanced Format (Per-case grading with points and tolerance)

For more advanced grading with per-case points and numerical tolerance:

```json
{
  "test_cases": [
    {
      "name": "Basic arithmetic operations",
      "points": 10,
      "expected": {
        "sum": 15,
        "product": 50
      }
    },
    {
      "name": "Numerical comparison with tolerance",
      "points": 15,
      "tolerance": 0.01,
      "expected": {
        "pi": 3.14159,
        "e": 2.71828
      }
    }
  ]
}
```

**Enhanced Format Fields:**
- `test_cases`: Array of test case objects
- `name`: Descriptive name for the test case
- `points`: Points awarded for passing this test case
- `expected`: The expected output (JSON object or value)
- `tolerance`: (Optional) Relative tolerance for numerical comparisons (e.g., 0.01 = 1%)
- `compare`: (Optional) Comparison operator: `<`, `<=`, `>`, `>=`, `==` (default), `!=`
- `compare_fields`: (Optional) Dict mapping field names to comparison operators
- `tolerance_fields`: (Optional) Dict mapping field names to tolerance values

#### Comparison Operators

Use comparison operators for threshold-based grading (performance metrics, quality checks, etc.):

```json
{
  "test_cases": [
    {
      "name": "Execution time should be under 5 seconds",
      "points": 20,
      "expected": 5.0,
      "compare": "<"
    },
    {
      "name": "Accuracy must be at least 95%",
      "points": 25,
      "expected": 0.95,
      "compare": ">="
    },
    {
      "name": "Performance metrics with mixed comparisons",
      "points": 30,
      "expected": {
        "execution_time": 10.0,
        "memory_usage": 100,
        "accuracy": 0.9
      },
      "compare_fields": {
        "execution_time": "<",
        "memory_usage": "<=",
        "accuracy": ">="
      }
    }
  ]
}
```

**Use cases for comparison operators:**
- Performance: execution time `<` threshold
- Quality: accuracy `>=` minimum acceptable
- Resource limits: memory usage `<=` limit
- Error rates: error `<` maximum tolerable

### 4. (Optional) Add custom requirements.txt

If your assignment requires specific Python packages, create a `requirements.txt`:

```bash
nano test_cases/homework-1-variables/requirements.txt
```

Example content:
```
numpy==1.24.0
pandas==2.0.0
matplotlib>=3.7.0
```

These will be installed in addition to the base project requirements.

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

### Legacy Format
1. Student notebook is executed
2. JSON outputs are extracted from cell outputs
3. Each output is compared with expected_output.json
4. Score = (matches / total_expected) * 100%

### Enhanced Format
1. Student notebook is executed
2. JSON outputs are extracted from cell outputs
3. Each test case is evaluated independently
4. Numerical values are compared with tolerance if specified
5. Score = sum of earned points from all test cases
6. **CI fails if ANY test case fails**

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
