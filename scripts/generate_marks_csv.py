#!/usr/bin/env python3
"""
Generate CSV file with student marks from GitHub PRs.

Extracts marks from PRs with titles like:
"Submission: ayumikhaylyuk_at_gmail_com - Homework-4"

Gets scores from:
1. Last comment on the PR (preferred)
2. Artifacts attached to the PR

Outputs CSV with:
- Rows: One student per row
- Columns: Student Name (if available), Student Email, Homework assignments

Features:
- Student IDs like "ayumikhaylyuk_at_gmail_com" are automatically
  converted to proper email format "ayumikhaylyuk@gmail.com"
- Student names are extracted from PR body if available
  (looks for "**Student Name:** {name}" in PR description)
"""

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from github import Github, GithubException


def get_student_email_from_id(student_id: str) -> str:
    """
    Convert student_id back to email format.

    Args:
        student_id: Student identifier (email with @ and . replaced)

    Returns:
        Student email address
    
    Note:
        This conversion has a limitation: it cannot distinguish between
        underscores that were originally dots and underscores that were
        already in the email. For example:
        - 'test_user@example.com' becomes 'test_user_at_example_com' (encoded)
        - Then converts back to 'test.user@example.com' (incorrect)
        
        This matches the behavior in aggregate_grades.py and send_results.py.
        To avoid issues, student emails should not contain underscores.
    """
    # Reverse the transformation done in classroom_client.py:
    # email.replace('@', '_at_').replace('.', '_')
    email = student_id.replace('_at_', '@')
    # Replace remaining underscores with dots
    # This is a best-effort conversion (see Note in docstring)
    email = email.replace('_', '.')
    return email


def parse_pr_title(title: str) -> Optional[Tuple[str, str]]:
    """
    Parse PR title to extract student email and homework name.
    
    Expected format: "Submission: {student_email} - {homework_name}"
    
    Args:
        title: PR title string
        
    Returns:
        Tuple of (student_email, homework_name) or None if parsing fails
    """
    # Pattern: "Submission: email - homework"
    pattern = r'^Submission:\s*([^\s]+)\s*-\s*(.+)$'
    match = re.match(pattern, title, re.IGNORECASE)
    
    if match:
        student_email = match.group(1).strip()
        homework_name = match.group(2).strip()
        return (student_email, homework_name)
    
    return None


def extract_score_from_comment(comment_body: str) -> Optional[float]:
    """
    Extract score from PR comment text.
    
    Looks for patterns like:
    - "Score: 85/100"
    - "Score: 85.5%"
    - "earned_points: 85, total_points: 100"
    
    Args:
        comment_body: Comment text
        
    Returns:
        Score as percentage (0-100) or None if not found
    """
    # Pattern 1: "Score: X/Y" or "Score: X / Y"
    pattern1 = r'Score:\s*(\d+\.?\d*)\s*/\s*(\d+\.?\d*)'
    match = re.search(pattern1, comment_body, re.IGNORECASE)
    if match:
        earned = float(match.group(1))
        total = float(match.group(2))
        if total > 0:
            return (earned / total) * 100
    
    # Pattern 2: "Score: X%"
    pattern2 = r'Score:\s*(\d+\.?\d*)%'
    match = re.search(pattern2, comment_body, re.IGNORECASE)
    if match:
        return float(match.group(1))
    
    # Pattern 3: "earned_points: X, total_points: Y" (from grade_report)
    pattern3 = r'earned[_\s]*points[:\s]*(\d+\.?\d*).*total[_\s]*points[:\s]*(\d+\.?\d*)'
    match = re.search(pattern3, comment_body, re.IGNORECASE | re.DOTALL)
    if match:
        earned = float(match.group(1))
        total = float(match.group(2))
        if total > 0:
            return (earned / total) * 100
    
    # Pattern 4: Look for percentage with score keyword
    pattern4 = r'(?:score|grade|mark).*?(\d+\.?\d*)%'
    match = re.search(pattern4, comment_body, re.IGNORECASE)
    if match:
        return float(match.group(1))
    
    return None


def extract_student_name_from_pr(pr) -> Optional[str]:
    """
    Extract student name from PR body if available.
    
    Args:
        pr: PR object from PyGithub
        
    Returns:
        Student name or None if not found
    """
    if not pr.body:
        return None
    
    # Look for patterns like "**Student Name:** John Doe"
    patterns = [
        r'\*\*Student Name:\*\*\s*(.+?)(?:\n|$)',
        r'Student Name:\s*(.+?)(?:\n|$)',
        r'\*\*Name:\*\*\s*(.+?)(?:\n|$)',
        r'Name:\s*(.+?)(?:\n|$)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, pr.body, re.MULTILINE)
        if match:
            name = match.group(1).strip()
            # Remove markdown bold/italic from beginning and end only
            # (e.g., "**John Doe**" -> "John Doe", but preserve internal underscores)
            name = name.strip('*_')
            return name if name else None
    
    return None


def extract_score_from_pr(pr) -> Optional[float]:
    """
    Extract score from a PR by checking comments.
    
    Args:
        pr: PR object from PyGithub
        
    Returns:
        Score as percentage or None
    """
    # Get all comments (issue comments on the PR)
    comments = list(pr.get_issue_comments())
    
    if not comments:
        return None
    
    # Check last comment first (most recent grade)
    for comment in reversed(comments):
        score = extract_score_from_comment(comment.body)
        if score is not None:
            return score
    
    return None


def generate_marks_csv(repo_name: str, token: str, output_file: str):
    """
    Generate CSV file with student marks from PRs.
    
    Args:
        repo_name: Repository in format "owner/repo"
        token: GitHub API token
        output_file: Path to output CSV file
    """
    print(f"🔍 Fetching PRs from {repo_name}...")
    
    # Initialize GitHub client
    g = Github(token)
    repo = g.get_repo(repo_name)
    
    # Get all PRs (open and closed)
    prs = list(repo.get_pulls(state='all'))
    print(f"   Found {len(prs)} PRs")
    
    # Parse PRs and extract marks
    marks = defaultdict(dict)  # {student_email: {homework: score}}
    student_names = {}  # {student_email: name}
    student_prs = defaultdict(list)  # {student_email: [prs]}
    homework_set = set()
    
    print("\n📊 Processing PRs...")
    for pr in prs:
        title = pr.title
        parsed = parse_pr_title(title)
        
        if not parsed:
            continue
        
        student_id, homework_name = parsed
        
        # Convert student_id to proper email format
        student_email = get_student_email_from_id(student_id)
        
        # Store PR for name extraction later
        if student_email not in student_names:
            student_prs[student_email].append(pr)
        
        # Extract score from PR
        score = extract_score_from_pr(pr)
        
        if score is not None:
            marks[student_email][homework_name] = score
            homework_set.add(homework_name)
            print(f"   ✓ {student_email} - {homework_name}: {score:.1f}%")
        else:
            print(f"   ⚠ {student_email} - {homework_name}: No score found")
    
    # Extract student names (one per student, from their first PR)
    print("\n📝 Extracting student names...")
    for student_email, pr_list in student_prs.items():
        if pr_list:
            # Try to get name from the first PR
            name = extract_student_name_from_pr(pr_list[0])
            if name:
                student_names[student_email] = name
                print(f"   ✓ Found name for {student_email}: {name}")
    
    if not marks:
        print("\n⚠️  No submission PRs found")
        print("   PRs must have titles like: 'Submission: email - Homework-X'")
        return
    
    # Sort students and homeworks for consistent output
    students = sorted(marks.keys())
    homeworks = sorted(homework_set)
    
    # Create output directory if needed
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write CSV
    print(f"\n📝 Writing CSV to {output_file}...")
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header row - include Name if any names were found
        if student_names:
            header = ['Student Name', 'Student Email'] + homeworks
        else:
            header = ['Student Email'] + homeworks
        writer.writerow(header)
        
        # Data rows
        for student in students:
            if student_names:
                # Include name column
                name = student_names.get(student, '')
                row = [name, student]
            else:
                # Email only
                row = [student]
            
            for homework in homeworks:
                score = marks[student].get(homework, '')
                if score != '':
                    row.append(f'{score:.1f}')
                else:
                    row.append('')
            writer.writerow(row)
    
    print(f"\n✅ CSV generated successfully!")
    print(f"   Students: {len(students)}")
    print(f"   Homeworks: {len(homeworks)}")
    print(f"   Total submissions: {sum(len(hw) for hw in marks.values())}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate CSV with student marks from GitHub PRs"
    )
    parser.add_argument(
        '--repo',
        required=True,
        help='Repository in format "owner/repo"'
    )
    parser.add_argument(
        '--token',
        help='GitHub API token (or use GITHUB_TOKEN env var)'
    )
    parser.add_argument(
        '--output',
        default='reports/marks.csv',
        help='Output CSV file path (default: reports/marks.csv)'
    )
    
    args = parser.parse_args()
    
    # Get GitHub token
    token = args.token or os.environ.get('GITHUB_TOKEN')
    if not token:
        print("❌ Error: GitHub token required")
        print("   Provide via --token argument or GITHUB_TOKEN environment variable")
        sys.exit(1)
    
    try:
        generate_marks_csv(args.repo, token, args.output)
    except GithubException as e:
        print(f"\n❌ GitHub API error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
