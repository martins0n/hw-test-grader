#!/usr/bin/env python3
"""
Script to run the grader on decrypted submissions.
"""
import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.grader import NotebookGrader


def grade_submission(student_id: str, assignment_id: str, output_path: str):
    """
    Grade a student's submission.

    Args:
        student_id: Student identifier
        assignment_id: Assignment identifier
        output_path: Path to save the grading report
    """
    grader = NotebookGrader()

    # Find decrypted notebook
    decrypted_dir = Path("decrypted_submissions") / student_id / assignment_id
    notebooks = list(decrypted_dir.glob("*.ipynb"))

    if not notebooks:
        result = {
            "error": "No Jupyter notebooks found in submission",
            "student_id": student_id,
            "assignment_id": assignment_id,
            "score": 0.0
        }
    else:
        # Grade the first notebook found (or you can modify to grade all)
        notebook_path = notebooks[0]
        print(f"Grading notebook: {notebook_path}")

        # Load expected outputs for this assignment
        expected_path = Path("test_cases") / assignment_id / "expected_output.json"

        if not expected_path.exists():
            print(f"Warning: No expected output file found at {expected_path}")
            print("Executing notebook without comparison...")

            # Execute notebook without grading
            executed_nb = grader.execute_notebook(notebook_path)
            if executed_nb:
                student_outputs = grader.extract_json_outputs(executed_nb)
                result = {
                    "student_id": student_id,
                    "assignment_id": assignment_id,
                    "notebook": str(notebook_path),
                    "student_outputs": student_outputs,
                    "note": "No expected outputs available for comparison"
                }
            else:
                result = {
                    "error": "Failed to execute notebook",
                    "student_id": student_id,
                    "assignment_id": assignment_id,
                    "score": 0.0
                }
        else:
            # Grade with expected outputs
            result = grader.grade_notebook(notebook_path, expected_path)
            result["student_id"] = student_id
            result["assignment_id"] = assignment_id

    # Save report
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2))

    # Print human-readable report
    print("\n" + "=" * 60)
    if "error" in result:
        print(f"ERROR: {result['error']}")
    elif "note" in result:
        print(result["note"])
        print(f"Student outputs: {json.dumps(result.get('student_outputs', []), indent=2)}")
    else:
        print(grader.generate_report(result))

    print(f"\nReport saved to: {output_path}")

    return result.get("score", 0.0)


def main():
    parser = argparse.ArgumentParser(description="Grade student notebook submission")
    parser.add_argument("--student-id", required=True, help="Student ID")
    parser.add_argument("--assignment-id", required=True, help="Assignment ID")
    parser.add_argument("--output", required=True, help="Output path for grading report")

    args = parser.parse_args()

    try:
        score = grade_submission(args.student_id, args.assignment_id, args.output)
        print(f"\nFinal Score: {score}%")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
