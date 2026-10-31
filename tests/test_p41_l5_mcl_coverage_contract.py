"""P41-L5: negative/reverse controls for the genuine MCL pulse comparator."""

import pytest

from mission_control_lite import coverage_pulse as pulse


def minimal():
    return {
        "schema": pulse.SCHEMA,
        "repository": "GBOGEB/ABACUS",
        "scope_id": "mission_control_lite/branch-v1",
        "files": ["mission_control_lite/core.py"],
        "coverage_version": "7.16.2",
        "source_sha": "a" * 40,
        "totals": {
            "covered_lines": 6,
            "num_statements": 10,
            "covered_branches": 2,
            "num_branches": 4,
        },
        "line_percent": 60.0,
        "branch_percent": 50.0,
        "tests_by_suite": {"core": 3},
        "test_case_ids": ["a", "b", "c"],
        "tests_passed": 3,
    }


def test_matched_observations_only_credit_source_matched_delta():
    old = minimal()
    new = minimal()
    new["source_sha"] = "b" * 40
    new["totals"] = {**old["totals"], "covered_lines": 8, "covered_branches": 3}
    new["line_percent"], new["branch_percent"] = 80.0, 75.0
    result = pulse.compare(old, new)
    assert result["status"] == "COMPARABLE"
    assert result["new_covered_lines"] == 2
    assert result["new_covered_branches"] == 1
    assert result["line_delta_pp"] == 20.0


def test_changed_denominators_must_not_be_credited():
    old, new = minimal(), minimal()
    new["totals"] = {**new["totals"], "num_statements": 11}
    result = pulse.compare(old, new)
    assert result["status"] == "INCOMPARABLE"
    assert "denominator" in result["reason"]


def test_source_scope_change_must_not_be_credited():
    old, new = minimal(), minimal()
    new["files"] = ["mission_control_lite/rex.py"]
    assert pulse.compare(old, new)["status"] == "INCOMPARABLE"


def test_unknown_native_baseline_does_not_yield_zero_delta():
    result = pulse.compare(None, minimal())
    assert result["status"] == "UNKNOWN"
    assert "new_covered_lines" not in result


@pytest.mark.parametrize(
    "invalid",
    [
        {
            "covered_lines": True,
            "num_statements": 10,
            "covered_branches": 0,
            "num_branches": 1,
        },
        {
            "covered_lines": 11,
            "num_statements": 10,
            "covered_branches": 0,
            "num_branches": 1,
        },
        {
            "covered_lines": 1,
            "num_statements": 10,
            "covered_branches": 2,
            "num_branches": 1,
        },
    ],
)
def test_invalid_coverage_is_rejected_not_silently_cast(invalid):
    with pytest.raises(ValueError):
        pulse._counts(invalid)
