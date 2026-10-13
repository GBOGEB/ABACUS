"""Fail-closed comparable Bandit burndown tests."""
import importlib.util
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1] / "scripts" / "bandit_comparable_delta.py"
SPEC = importlib.util.spec_from_file_location("bandit_comparable_delta", PATH)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def item(path="src/a.py", rule="B603", line=4):
    return {"filename": path, "test_id": rule, "line_number": line,
            "issue_text": "unsafe execution"}


def compare(before, after, **kwargs):
    return module.compare(
        {"results": before}, {"results": after},
        before_sha="a" * 40, after_sha="b" * 40,
        before_config="full-default", after_config="full-default", **kwargs,
    )


def test_identical_findings_have_zero_delta():
    receipt = compare([item()], [item()])
    assert receipt["new"] == receipt["resolved"] == 0
    assert receipt["net_reduction"] == 0


def test_removed_finding_is_not_security_clearance():
    receipt = compare([item()], [])
    assert receipt["resolved"] == 1
    assert receipt["net_reduction"] == 1
    assert receipt["security_clearance"] is False


def test_new_finding_is_explicit_regression():
    receipt = compare([], [item()])
    assert receipt["new"] == 1
    assert receipt["new_by_rule"] == {"B603": 1}


def test_duplicate_rows_not_double_counted():
    receipt = compare([item(), item()], [item()])
    assert receipt["before_unique"] == 1
    assert receipt["net_reduction"] == 0


def test_changed_line_is_not_silent_repair():
    receipt = compare([item(line=4)], [item(line=5)])
    assert receipt["new"] == 1
    assert receipt["resolved"] == 1
    assert receipt["net_reduction"] == 0


def test_mismatched_configuration_rejected():
    with pytest.raises(ValueError, match="configuration mismatch"):
        module.compare(
            {"results": [item()]}, {"results": []},
            before_sha="a" * 40, after_sha="b" * 40,
            before_config="full-default", after_config="configured",
        )


@pytest.mark.parametrize("bad", [{}, {"results": None}, {"results": "bad"}])
def test_missing_results_rejected(bad):
    with pytest.raises(ValueError, match="missing results"):
        module.compare(
            bad, {"results": []}, before_sha="a" * 40,
            after_sha="b" * 40, before_config="full", after_config="full",
        )
