"""Regression checks for read-only Bandit classification."""
from scripts.bandit_touched_census import classify


def test_assert_findings_retained_without_security_credit():
    result = classify({"results": [
        {"test_id": "B101", "filename": "tests/test_one.py",
         "line_number": 5, "code": "assert value == 1"},
        {"test_id": "B603", "filename": "scripts/runner.py",
         "line_number": 7, "code": "subprocess.run(cmd)"}
    ]})
    assert result["counts_by_rule"] == {"B101": 1, "B603": 1}
    assert result["classification_counts"] == {
        "OTHER_FINDING": 1, "TEST_ASSERTION": 1
    }
    assert result["security_clearance"] is None
    assert result["disposition"] == "PENDING_INDEPENDENT_SECURITY_REVIEW"


def test_fingerprint_is_stable_and_source_sensitive():
    row = {"test_id": "B101", "filename": "tests/test_one.py",
           "line_number": 5, "code": "assert a"}
    a = classify({"results": [row, dict(row)]})
    assert len(a["findings"]) == 2
    assert a["findings"][0]["fingerprint"] == a["findings"][1]["fingerprint"]
    changed = dict(row, line_number=6)
    b = classify({"results": [changed]})
    assert a["findings"][0]["fingerprint"] != b["findings"][0]["fingerprint"]
