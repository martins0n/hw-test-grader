# Simple Setup - Just Course IDs

The absolute simplest way to set up the homework grader.

## Step 1: Get Your Course ID

Run this once to see your course IDs:

```bash
python scripts/list_classroom_info.py courses
```

Copy the course ID(s) you want to monitor.

**Example output:**
```
1. Introduction to Python
   Course ID: 123456789    ← Copy this
   Section: Fall 2024

2. Data Science 101
   Course ID: 987654321    ← Copy this
   Section: Spring 2024
```

## Step 2: Add to .env File

Edit your `.env` file and add the course IDs:

```bash
# Add this line with your course IDs (comma-separated)
COURSE_IDS=123456789,987654321
```

That's it! The system will automatically:
- ✅ Discover ALL assignments from these courses
- ✅ Download new submissions
- ✅ Encrypt and grade them
- ✅ Include new assignments as you create them

## Step 3: Test Locally

```bash
python scripts/download_submissions.py
```

You should see:
```
Using COURSE_IDS from environment: 2 course(s)
Auto-discovering assignments from 2 course(s)
Fetching assignments from: Course 123456789
  Found 5 published assignment(s)
    ✓ Homework 1
    ✓ Homework 2
    ...
```

## Step 4: Deploy to GitHub

Add the course IDs as a GitHub Secret:

1. Go to your repository → Settings → Secrets → Actions
2. Click "New repository secret"
3. Name: `COURSE_IDS`
4. Value: `123456789,987654321` (your course IDs, comma-separated)
5. Click "Add secret"

Done! The workflow will now automatically grade everything.

## How It Works

```
You set:          COURSE_IDS=123456789

System automatically:
  ↓ Discovers all published assignments from course 123456789
  ↓ Downloads new submissions every hour
  ↓ Encrypts and commits to GitHub
  ↓ Grades them automatically
  ↓ Generates reports

New assignment added? → Automatically included!
```

## Multiple Courses

Just separate with commas:

```bash
COURSE_IDS=123456789,987654321,555666777
```

## Complete .env Example

```bash
# GitHub
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
GITHUB_REPO=myusername/homework-submissions

# Course IDs (comma-separated)
COURSE_IDS=123456789,987654321

# Google Classroom
GOOGLE_CLASSROOM_CREDENTIALS=credentials.json

# Logging
LOG_LEVEL=INFO
```

## What Gets Graded?

ALL published assignments from the specified courses.

To see what will be graded:

```bash
python -c "
from src.classroom_client import ClassroomClient
client = ClassroomClient()

# Replace with your course ID
coursework = client.list_course_work('123456789')
published = [w for w in coursework if w.get('state') == 'PUBLISHED']

print(f'Will grade {len(published)} assignments:')
for w in published:
    print(f'  - {w.get(\"title\")}')"
```

## Advanced: Filter Assignments

If you don't want to grade ALL assignments, you can use the old method:

1. Run `python scripts/auto_discover_assignments.py`
2. Edit `assignments_config.json` to remove unwanted assignments
3. Use `ASSIGNMENTS_CONFIG` instead of `COURSE_IDS`

But for most cases, just using `COURSE_IDS` is easiest!
