"""Grader for Jupyter notebooks with JSON output comparison."""
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
from jupyter_client.kernelspec import NoSuchKernel

logger = logging.getLogger(__name__)


class NotebookGrader:
    """Grades Jupyter notebooks by executing them and comparing JSON outputs."""

    def __init__(self, timeout: int = 600 * 5):
        """
        Initialize the notebook grader.

        Args:
            timeout: Timeout in seconds for executing each notebook
        """
        self.timeout = timeout
        self.kernel_name = os.getenv('NB_KERNEL_NAME', 'python3')
        self.executor = self._create_executor()

    def _create_executor(self) -> ExecutePreprocessor:
        """Create an ExecutePreprocessor, installing the kernel if missing."""
        try:
            return ExecutePreprocessor(timeout=self.timeout, kernel_name=self.kernel_name)
        except NoSuchKernel:
            logger.warning(
                "Kernel '%s' not found. Attempting to install ipykernel...",
                self.kernel_name,
            )
            self._install_kernel_spec()
            return ExecutePreprocessor(timeout=self.timeout, kernel_name=self.kernel_name)

    def _install_kernel_spec(self):
        """Install the default ipykernel so notebooks can execute."""
        try:
            from ipykernel.kernelspec import install as install_kernel
        except ImportError as exc:
            raise RuntimeError(
                "ipykernel is not installed; cannot provision a Python kernel"
            ) from exc

        install_kernel(user=True)
        logger.info("Registered ipykernel for kernel name '%s'", self.kernel_name)

    def execute_notebook(self, notebook_path: Path) -> Optional[nbformat.NotebookNode]:
        """
        Execute a Jupyter notebook.

        Args:
            notebook_path: Path to the notebook file

        Returns:
            Executed notebook object, or None if execution failed
        """
        try:
            with open(notebook_path) as f:
                nb = nbformat.read(f, as_version=4)

            self.executor.preprocess(nb, {'metadata': {'path': str(notebook_path.parent)}})
            logger.info(f"Successfully executed {notebook_path.name}")
            return nb

        except NoSuchKernel:
            # Kernel missing at execution time (e.g. removed after init)
            logger.warning("Kernel '%s' missing during execution; reinstalling", self.kernel_name)
            self.executor = self._create_executor()
            return self.execute_notebook(notebook_path)
        except Exception as e:
            logger.error(f"Failed to execute {notebook_path.name}: {e}")
            return None

    def extract_json_outputs(self, notebook: nbformat.NotebookNode) -> List[Dict[str, Any]]:
        """
        Extract JSON outputs from an executed notebook.

        Args:
            notebook: Executed notebook object

        Returns:
            List of JSON outputs found in the notebook
        """
        json_outputs = []

        for cell in notebook.cells:
            if cell.cell_type == 'code' and 'outputs' in cell:
                for output in cell.outputs:
                    if output.output_type == 'execute_result' or output.output_type == 'display_data':
                        if 'data' in output and 'text/plain' in output.data:
                            text = output.data['text/plain']
                            try:
                                # Try to parse as JSON
                                json_obj = json.loads(text)
                                json_outputs.append(json_obj)
                            except (json.JSONDecodeError, TypeError):
                                # Not valid JSON, skip
                                pass
                    elif output.output_type == 'stream' and output.name == 'stdout':
                        # Check stdout for JSON
                        try:
                            json_obj = json.loads(output.text)
                            json_outputs.append(json_obj)
                        except (json.JSONDecodeError, TypeError):
                            pass

        return json_outputs

    def compare_outputs(
        self,
        student_output: List[Dict[str, Any]],
        expected_output: List[Dict[str, Any]],
        tolerance: float = 0.0
    ) -> Dict[str, Any]:
        """
        Compare student output with expected output.

        Args:
            student_output: JSON outputs from student's notebook
            expected_output: Expected JSON outputs
            tolerance: Numerical tolerance for float comparisons

        Returns:
            Grading result dictionary
        """
        result = {
            'total_expected': len(expected_output),
            'total_received': len(student_output),
            'matches': 0,
            'mismatches': [],
            'missing': [],
            'extra': [],
            'score': 0.0,
            'passed': False,
        }

        # Compare each expected output
        for i, expected in enumerate(expected_output):
            if i < len(student_output):
                if self._compare_json(student_output[i], expected, tolerance):
                    result['matches'] += 1
                else:
                    result['mismatches'].append({
                        'index': i,
                        'expected': expected,
                        'received': student_output[i]
                    })
            else:
                result['missing'].append({
                    'index': i,
                    'expected': expected
                })

        # Check for extra outputs
        if len(student_output) > len(expected_output):
            result['extra'] = student_output[len(expected_output):]

        # Calculate score
        if result['total_expected'] > 0:
            result['score'] = (result['matches'] / result['total_expected']) * 100
        else:
            result['score'] = 0.0

        result['passed'] = (
            result['matches'] == result['total_expected']
            and not result['mismatches']
            and not result['missing']
            and not result['extra']
        )

        return result

    def _compare_values(self, value: Any, expected: Any, operator: str = '==', tolerance: float = 0.0) -> bool:
        """
        Compare a value against expected using the specified operator.

        Args:
            value: Student's value
            expected: Expected value
            operator: Comparison operator ('==', '<', '<=', '>', '>=', '!=')
            tolerance: Relative tolerance for numerical comparisons with '=='

        Returns:
            True if comparison succeeds, False otherwise
        """
        # For numeric comparisons
        if isinstance(value, (int, float)) and isinstance(expected, (int, float)):
            if operator in ('==', 'eq'):
                if tolerance > 0:
                    if expected == 0:
                        return abs(value) <= tolerance
                    return abs(value - expected) / abs(expected) <= tolerance
                return value == expected
            elif operator in ('<', 'lt'):
                return value < expected
            elif operator in ('<=', 'lte'):
                return value <= expected
            elif operator in ('>', 'gt'):
                return value > expected
            elif operator in ('>=', 'gte'):
                return value >= expected
            elif operator in ('!=', 'ne'):
                return value != expected
            else:
                logger.warning(f"Unknown operator '{operator}', defaulting to '=='")
                return value == expected

        # For non-numeric, only equality/inequality makes sense
        if operator in ('!=', 'ne'):
            return value != expected
        else:  # Default to equality
            return value == expected

    def _compare_json(self, obj1: Any, obj2: Any, tolerance: float = 0.0) -> bool:
        """
        Recursively compare two JSON objects with numerical tolerance.

        Args:
            obj1: First object (student output)
            obj2: Second object (expected output)
            tolerance: Relative tolerance for numerical comparisons

        Returns:
            True if objects are equal within tolerance, False otherwise
        """
        # Handle numerical comparisons with tolerance
        if isinstance(obj1, (int, float)) and isinstance(obj2, (int, float)):
            if tolerance > 0:
                # Relative tolerance comparison
                if obj2 == 0:
                    return abs(obj1) <= tolerance
                return abs(obj1 - obj2) / abs(obj2) <= tolerance
            else:
                return obj1 == obj2

        if type(obj1) != type(obj2):
            return False

        if isinstance(obj1, dict):
            if set(obj1.keys()) != set(obj2.keys()):
                return False
            return all(self._compare_json(obj1[k], obj2[k], tolerance) for k in obj1.keys())

        elif isinstance(obj1, list):
            if len(obj1) != len(obj2):
                return False
            return all(self._compare_json(a, b, tolerance) for a, b in zip(obj1, obj2))

        else:
            return obj1 == obj2

    def grade_notebook_with_test_cases(
        self,
        student_notebook_path: Path,
        test_cases_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Grade a notebook using enhanced test cases format with per-case grading.

        Args:
            student_notebook_path: Path to student's notebook
            test_cases_config: Test cases configuration with format:
                {
                    "test_cases": [
                        {
                            "name": "Test case name",
                            "points": 10,
                            "expected": {...},
                            "tolerance": 0.01,  # Optional, for == comparisons
                            "compare": "==",  # Optional: ==, <, <=, >, >=, !=
                            "compare_fields": {"field": "<"},  # Optional: per-field operators
                            "tolerance_fields": {"field": 0.01}  # Optional: per-field tolerance
                        }
                    ]
                }

        Returns:
            Grading result dictionary with per-case grades
        """
        # Execute the student's notebook
        executed_nb = self.execute_notebook(student_notebook_path)

        if executed_nb is None:
            return {
                'error': 'Failed to execute notebook',
                'score': 0.0,
                'total_points': 0,
                'passed': False,
            }

        # Extract JSON outputs
        student_outputs = self.extract_json_outputs(executed_nb)

        test_cases = test_cases_config.get('test_cases', [])

        result = {
            'student_notebook': str(student_notebook_path),
            'total_test_cases': len(test_cases),
            'passed_cases': 0,
            'failed_cases': 0,
            'total_points': sum(tc.get('points', 0) for tc in test_cases),
            'earned_points': 0,
            'test_case_results': [],
            'passed': True,  # Points-based grading always "passes" - score is what matters
        }

        for i, test_case in enumerate(test_cases):
            case_name = test_case.get('name', f'Test Case {i+1}')
            points = test_case.get('points', 0)
            expected = test_case.get('expected')
            tolerance = test_case.get('tolerance', 0.0)
            compare = test_case.get('compare', '==')  # Default to equality

            case_result = {
                'name': case_name,
                'points': points,
                'earned': 0,
                'passed': False,
            }

            # Check if we have output for this test case
            if i < len(student_outputs):
                student_output = student_outputs[i]

                # Handle comparison-based test cases (for single values)
                if compare != '==' and not isinstance(expected, (dict, list)):
                    # Simple value comparison with operator
                    if self._compare_values(student_output, expected, compare, tolerance):
                        case_result['passed'] = True
                        case_result['earned'] = points
                        result['passed_cases'] += 1
                        result['earned_points'] += points
                    else:
                        case_result['error'] = f'Comparison failed: {student_output} {compare} {expected}'
                        case_result['expected'] = f'{compare} {expected}'
                        case_result['received'] = student_output
                        result['failed_cases'] += 1

                # Handle object/array comparisons with field-level operators
                elif isinstance(expected, dict) and 'compare' in test_case:
                    # Check if expected dict has comparison operators for fields
                    passed = True
                    errors = []

                    for key, exp_val in expected.items():
                        if key not in student_output:
                            passed = False
                            errors.append(f"Missing field '{key}'")
                            continue

                        # Check if there's a field-specific comparison
                        field_compare = test_case.get('compare_fields', {}).get(key, '==')
                        field_tolerance = test_case.get('tolerance_fields', {}).get(key, tolerance)

                        if not self._compare_values(student_output[key], exp_val, field_compare, field_tolerance):
                            passed = False
                            errors.append(f"Field '{key}': {student_output[key]} {field_compare} {exp_val}")

                    if passed:
                        case_result['passed'] = True
                        case_result['earned'] = points
                        result['passed_cases'] += 1
                        result['earned_points'] += points
                    else:
                        case_result['error'] = '; '.join(errors)
                        case_result['expected'] = expected
                        case_result['received'] = student_output
                        result['failed_cases'] += 1

                # Default: exact match comparison
                else:
                    if self._compare_json(student_output, expected, tolerance):
                        case_result['passed'] = True
                        case_result['earned'] = points
                        result['passed_cases'] += 1
                        result['earned_points'] += points
                    else:
                        case_result['error'] = 'Output does not match expected'
                        case_result['expected'] = expected
                        case_result['received'] = student_output
                        result['failed_cases'] += 1
            else:
                case_result['error'] = 'Missing output'
                case_result['expected'] = expected
                result['failed_cases'] += 1

            result['test_case_results'].append(case_result)

        # Calculate percentage score
        if result['total_points'] > 0:
            result['score'] = (result['earned_points'] / result['total_points']) * 100
        else:
            result['score'] = 0.0

        return result

    def grade_notebook(
        self,
        student_notebook_path: Path,
        expected_output_path: Optional[Path] = None,
        expected_outputs: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Grade a student's notebook.

        Args:
            student_notebook_path: Path to student's notebook
            expected_output_path: Path to JSON file with expected outputs
            expected_outputs: Expected outputs as a list of dicts

        Returns:
            Grading result dictionary
        """
        # Execute the student's notebook
        executed_nb = self.execute_notebook(student_notebook_path)

        if executed_nb is None:
            return {
                'error': 'Failed to execute notebook',
                'score': 0.0,
                'passed': False,
            }

        # Extract JSON outputs
        student_outputs = self.extract_json_outputs(executed_nb)

        # Load expected outputs
        if expected_output_path:
            with open(expected_output_path) as f:
                expected = json.load(f)

                # Check if this is the new test_cases format
                if isinstance(expected, dict) and 'test_cases' in expected:
                    return self.grade_notebook_with_test_cases(student_notebook_path, expected)

                # Legacy format
                if isinstance(expected, list):
                    expected_outputs = expected
                else:
                    expected_outputs = [expected]
        elif expected_outputs is None:
            return {
                'error': 'No expected outputs provided',
                'student_outputs': student_outputs,
                'passed': False,
            }

        # Compare outputs (legacy format)
        result = self.compare_outputs(student_outputs, expected_outputs)
        result['student_notebook'] = str(student_notebook_path)

        return result

    def generate_report(self, grading_result: Dict[str, Any]) -> str:
        """
        Generate a human-readable grading report.

        Args:
            grading_result: Result from grade_notebook

        Returns:
            Formatted report string
        """
        if 'error' in grading_result:
            return f"ERROR: {grading_result['error']}"

        report = []
        report.append("=" * 60)
        report.append("GRADING REPORT")
        report.append("=" * 60)

        # Check if this is the new test_cases format
        if 'test_case_results' in grading_result:
            # Enhanced format with per-case grading
            report.append(f"Score: {grading_result['earned_points']}/{grading_result['total_points']} ({grading_result['score']:.2f}%)")
            report.append(f"Passed: {grading_result['passed_cases']}/{grading_result['total_test_cases']}")
            report.append(f"Status: {'PASSED' if grading_result['passed'] else 'FAILED'}")
            report.append("")

            for case_result in grading_result['test_case_results']:
                status_icon = "✓" if case_result['passed'] else "✗"
                report.append(f"{status_icon} {case_result['name']}: {case_result['earned']}/{case_result['points']} points")
                if not case_result['passed'] and 'error' in case_result:
                    report.append(f"  Error: {case_result['error']}")
                    if 'expected' in case_result:
                        report.append(f"  Expected: {json.dumps(case_result['expected'], indent=2)}")
                    if 'received' in case_result:
                        report.append(f"  Received: {json.dumps(case_result['received'], indent=2)}")
                report.append("")
        else:
            # Legacy format
            report.append(f"Score: {grading_result['score']:.2f}%")
            report.append(f"Matches: {grading_result['matches']}/{grading_result['total_expected']}")
            report.append("")

            if grading_result.get('mismatches'):
                report.append("MISMATCHES:")
                for mismatch in grading_result['mismatches']:
                    report.append(f"  Output #{mismatch['index']}:")
                    report.append(f"    Expected: {json.dumps(mismatch['expected'], indent=2)}")
                    report.append(f"    Received: {json.dumps(mismatch['received'], indent=2)}")
                    report.append("")

            if grading_result.get('missing'):
                report.append("MISSING OUTPUTS:")
                for missing in grading_result['missing']:
                    report.append(f"  Output #{missing['index']}: {json.dumps(missing['expected'], indent=2)}")
                report.append("")

            if grading_result.get('extra'):
                report.append("EXTRA OUTPUTS:")
                for extra in grading_result['extra']:
                    report.append(f"  {json.dumps(extra, indent=2)}")
                report.append("")

        report.append("=" * 60)

        return "\n".join(report)
