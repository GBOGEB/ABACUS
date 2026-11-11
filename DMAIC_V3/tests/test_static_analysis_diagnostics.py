"""Bounded DMAIC static-scan diagnostics: negative and positive controls."""

import pytest

from DMAIC_V3.core.static_analysis_diagnostics import summarize_static_analysis


def test_error_exposes_source_line_column_rule():
    scan = {
        "flake8": {
            "returncode": 1,
            "output": (
                "DMAIC_V3/core/test_system_bridge.py:73:5: "
                "E301 expected 1 blank line, found 0\n"
            ),
        }
    }
    report = summarize_static_analysis(scan)
    assert report["status"] == "FAIL"
    assert report["returncode"] == 1
    assert report["finding_count"] == 1
    assert report["findings"][0] == {
        "source_path": "DMAIC_V3/core/test_system_bridge.py",
        "line": 73,
        "column": 5,
        "rule": "E301",
        "message": "expected 1 blank line, found 0",
    }


def test_windows_drive_path_is_preserved():
    result = summarize_static_analysis(
        {
            "flake8": {
                "returncode": 1,
                "output": "C:/runner/project/module.py:41:9: F821 undefined name 'x'",
            }
        }
    )
    assert result["findings"][0]["source_path"] == "C:/runner/project/module.py"
    assert result["findings"][0]["line"] == 41


@pytest.mark.parametrize(
    "reports",
    [
        None,
        {},
        {"flake8": None},
        {"flake8": {"error": "scanner crashed"}},
        {"flake8": {"returncode": "0", "output": ""}},
        {"flake8": {"returncode": True, "output": ""}},
    ],
)
def test_unexecuted_or_unauthenticated_scanner_is_unknown(reports):
    evidence = summarize_static_analysis(reports)
    assert evidence["status"] == "UNKNOWN"
    assert evidence["finding_count"] is None
    assert evidence["truncated"] is None


def test_nonzero_exit_without_matching_findings_remains_red():
    evidence = summarize_static_analysis(
        {"flake8": {"returncode": 2, "output": "FATAL: scanner failure"}}
    )
    assert evidence["status"] == "FAIL"
    assert evidence["finding_count"] == 0
    assert evidence["cause"] == "nonzero scanner exit"


def test_zero_exit_is_only_scanner_receipt_not_deployment_admission():
    report = summarize_static_analysis({"flake8": {"returncode": 0, "output": ""}})
    assert report["status"] == "PASS"
    assert "deployment_ready" not in report
    assert "merge_admission" not in report


def test_bounded_diagnostics_keep_actual_finding_denominator():
    lines = [f"project/a.py:{n}:1: E301 missing blank" for n in range(1, 37)]
    result = summarize_static_analysis(
        {"flake8": {"returncode": 1, "output": "\n".join(lines)}},
        max_findings=10,
    )
    assert len(result["findings"]) == 10
    assert result["finding_count"] == 36
    assert result["truncated"] is True
    assert result["finding_detail_complete"] is False


def test_no_raw_log_content_is_published():
    scan = {
        "flake8": {
            "returncode": 1,
            "output": "some unparsed diagnostic secret like raw data",
        }
    }
    result = summarize_static_analysis(scan)
    assert "output" not in result
    assert "some unparsed" not in str(result)


def test_diagnostic_message_is_bounded():
    result = summarize_static_analysis(
        {
            "flake8": {
                "returncode": 1,
                "output": "src/a.py:1:2: E501 " + "x" * 1000,
            }
        }
    )
    assert len(result["findings"][0]["message"]) == 200


@pytest.mark.parametrize("limit", [0, -1, 101, True, 1.5])
def test_invalid_limits_are_rejected(limit):
    with pytest.raises(ValueError):
        summarize_static_analysis(
            {"flake8": {"returncode": 1, "output": ""}},
            max_findings=limit,
        )
