"""Lane A wave 11: bounded static-analysis diagnostics extraction."""

import pytest

from DMAIC_V3.core.static_analysis_diagnostics import summarize_static_analysis

LINES = "\n".join(
    [
        "pkg/a.py:10:5: E501 line too long (100 > 88 characters)",
        "not a flake8 line",
        "  pkg/b.py:3:1: F401 'os' imported but unused  ",
        "pkg/c.py:7:2: W1234 four digit rule",
        "pkg/d.py:x:1: E501 bad line number",
    ]
)


@pytest.mark.parametrize("bad", [0, 101, 1.0, True, "5"])
def test_rejects_bad_max_findings(bad):
    with pytest.raises(ValueError, match="max_findings"):
        summarize_static_analysis({}, max_findings=bad)


def test_missing_reports_is_unknown():
    result = summarize_static_analysis(None)
    assert result["status"] == "UNKNOWN"
    assert result["cause"] == "missing scanner result dictionary"
    assert result["finding_count"] is None


@pytest.mark.parametrize("reports", [{}, {"flake8": "oops"}])
def test_missing_flake8_is_unknown(reports):
    result = summarize_static_analysis(reports)
    assert result["status"] == "UNKNOWN"
    assert "flake8 not executed" in result["cause"]


@pytest.mark.parametrize("code", [None, "0", True])
def test_invalid_returncode_is_unknown(code):
    result = summarize_static_analysis({"flake8": {"returncode": code}})
    assert result["status"] == "UNKNOWN"
    assert "returncode" in result["cause"]


def test_failure_parses_findings():
    result = summarize_static_analysis({"flake8": {"returncode": 1, "output": LINES}})
    assert result["status"] == "FAIL"
    assert result["cause"] == "nonzero scanner exit"
    assert result["finding_count"] == 3
    assert result["truncated"] is False
    assert result["finding_detail_complete"] is True
    first, second, third = result["findings"]
    assert first == {
        "source_path": "pkg/a.py",
        "line": 10,
        "column": 5,
        "rule": "E501",
        "message": "line too long (100 > 88 characters)",
    }
    assert second["rule"] == "F401"
    assert second["source_path"] == "pkg/b.py"
    assert third["rule"] == "W1234"


def test_truncation_and_field_clipping():
    long_path = "".join(["p"] * 300) + ".py"
    long_msg = "".join(["m"] * 300)
    out = "\n".join(
        [
            long_path + ":1:1: E101 " + long_msg,
            "a.py:2:1: E102 two",
            "a.py:3:1: E103 three",
        ]
    )
    result = summarize_static_analysis(
        {"flake8": {"returncode": 1, "output": out}}, max_findings=1
    )
    assert result["finding_count"] == 3
    assert len(result["findings"]) == 1
    assert result["truncated"] is True
    assert result["finding_detail_complete"] is False
    assert len(result["findings"][0]["source_path"]) == 240
    assert len(result["findings"][0]["message"]) == 200


def test_pass_without_output():
    result = summarize_static_analysis({"flake8": {"returncode": 0}})
    assert result["status"] == "PASS"
    assert result["cause"] == "scanner exit zero"
    assert result["findings"] == []
    assert result["finding_count"] is None
    assert result["truncated"] is None
    assert result["finding_detail_complete"] is False


def test_pass_with_empty_output():
    result = summarize_static_analysis({"flake8": {"returncode": 0, "output": ""}})
    assert result["status"] == "PASS"
    assert result["finding_count"] == 0
    assert result["finding_detail_complete"] is True
