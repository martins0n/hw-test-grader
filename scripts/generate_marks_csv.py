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
- Columns: One homework per column
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
    homework_set = set()
    
    print("\n📊 Processing PRs...")
    for pr in prs:
        title = pr.title
        parsed = parse_pr_title(title)
        
        if not parsed:
            continue
        
        student_email, homework_name = parsed
        
        # Extract score from PR
        score = extract_score_from_pr(pr)
        
        if score is not None:
            marks[student_email][homework_name] = score
            homework_set.add(homework_name)
            print(f"   ✓ {student_email} - {homework_name}: {score:.1f}%")
        else:
            print(f"   ⚠ {student_email} - {homework_name}: No score found")
    
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
        
        # Header row
        header = ['Student'] + homeworks
        writer.writerow(header)
        
        # Data rows
        for student in students:
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
