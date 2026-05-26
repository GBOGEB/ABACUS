import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / ".github"
    / "scripts"
    / "create_issues_from_failures.py"
)
SCRIPT_SPEC = importlib.util.spec_from_file_location(
    "create_issues_from_failures",
    SCRIPT_PATH,
)
SCRIPT_MODULE = importlib.util.module_from_spec(SCRIPT_SPEC)
assert SCRIPT_SPEC.loader is not None
SCRIPT_SPEC.loader.exec_module(SCRIPT_MODULE)
CIIssueCreator = SCRIPT_MODULE.CIIssueCreator


@pytest.mark.unit
def test_close_issue_for_test_closes_matching_open_issue():
    creator = object.__new__(CIIssueCreator)
    creator.closed_issues = []

    issue = Mock()
    issue.number = 31

    creator.get_existing_issues = Mock(return_value=[issue])

    closed_count = creator.close_issue_for_test(
        "DMAIC_V3/tests/test_integration.py::TestFullDMAICCycle::test_complete_cycle_iteration_1"
    )

    assert closed_count == 1
    assert creator.closed_issues == [31]
    issue.create_comment.assert_called_once()
    issue.edit.assert_called_once_with(state="closed")


@pytest.mark.unit
def test_process_test_results_closes_resolved_tests_before_creating_new_failures(tmp_path):
    creator = object.__new__(CIIssueCreator)
    creator.created_issues = []
    creator.closed_issues = []

    creator.close_issue_for_test = Mock(return_value=1)
    creator.create_issue_for_test = Mock(return_value=None)

    report_path = tmp_path / "test_report.json"
    report_path.write_text(
        """
        {
          "summary": {"total": 2, "passed": 1, "failed": 1},
          "tests": [
            {"nodeid": "tests/test_ok.py::test_ok", "outcome": "passed"},
            {"nodeid": "tests/test_bad.py::test_bad", "outcome": "failed"}
          ]
        }
        """.strip(),
        encoding="utf-8",
    )

    creator.process_test_results(str(report_path))

    creator.close_issue_for_test.assert_called_once_with("tests/test_ok.py::test_ok")
    creator.create_issue_for_test.assert_called_once_with(
        {"nodeid": "tests/test_bad.py::test_bad", "outcome": "failed"}
    )
