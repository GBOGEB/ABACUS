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


def compare(before, after):
    return module.compare(
        {"results": before}, {"results": after},
        before_sha="a" * 40, after_sha="b" * 40,
        before_config="full-default", after_config="full-default",
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


@pytest.mark.parametrize("before,after,expected_new,expected_resolved", [
    ([], [], 0, 0),
    ([item(rule="B101")], [item(rule="B101"), item(rule="B603", line=8)], 1, 0),
    ([item(rule="B101"), item(rule="B603", line=8)], [item(rule="B603", line=8)], 0, 1),
    ([item(path="src/a.py")], [item(path="src/b.py")], 1, 1),
])
def test_comparable_delta_adversarial_transitions(
        before, after, expected_new, expected_resolved):
    receipt = compare(before, after)
    assert receipt["new"] == expected_new
    assert receipt["resolved"] == expected_resolved
    assert receipt["net_reduction"] == expected_resolved - expected_new
    assert receipt["security_clearance"] is False


@pytest.mark.parametrize("bad", [None, False, 4, {"results": {}}])
def test_invalid_after_report_fails_closed(bad):
    with pytest.raises((ValueError, TypeError, AttributeError)):
        module.compare(
            {"results": []}, bad,
            before_sha="a" * 40, after_sha="b" * 40,
            before_config="full", after_config="full",
        )


@pytest.mark.parametrize("before_sha,after_sha", [
    ("a" * 40, "a" * 40),
    ("b" * 40, "b" * 40),
])
def test_same_sha_rejects_comparable_delta(before_sha, after_sha):
    with pytest.raises(ValueError, match="shall differ"):
        module.compare({"results": []}, {"results": []},
                       before_sha=before_sha, after_sha=after_sha,
                       before_config="full", after_config="full")


def test_mixed_rules_report_opened_resolved_and_net_separately():
    previous = [item(rule="B101"), item(rule="B603", line=8)]
    current = [item(rule="B603", line=8), item(rule="B105", line=9)]
    receipt = compare(previous, current)
    assert receipt["before_unique"] == receipt["after_unique"] == 2
    assert receipt["new"] == receipt["resolved"] == 1
    assert receipt["new_by_rule"] == {"B105": 1}
    assert receipt["resolved_by_rule"] == {"B101": 1}
    assert receipt["net_reduction"] == 0
    assert receipt["security_clearance"] is False


def test_comparable_delta_does_not_mutate_original_reports():
    before = {"results": [item()]}
    after = {"results": [item()]}
    snapshots = (repr(before), repr(after))
    receipt = module.compare(before, after, before_sha="a" * 40,
                             after_sha="b" * 40, before_config="full",
                             after_config="full")
    assert (repr(before), repr(after)) == snapshots
    assert receipt["new"] == receipt["resolved"] == 0


@pytest.mark.parametrize("invalid_sha", ["short", "G" * 40, "A" * 40])
def test_comparable_cli_rejects_invalid_sha(tmp_path, monkeypatch, invalid_sha):
    import sys
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    before.write_text('{"results": []}', encoding="utf-8")
    after.write_text('{"results": []}', encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [
        "bandit_comparable_delta.py", "--before", str(before),
        "--after", str(after), "--before-sha", invalid_sha,
        "--after-sha", "b" * 40, "--before-config", "full",
        "--after-config", "full", "--out", str(tmp_path / "out.json"),
    ])
    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 2
    assert not (tmp_path / "out.json").exists()


def test_comparable_cli_writes_source_bound_receipt(tmp_path, monkeypatch):
    import json
    import sys
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    before.write_text(json.dumps({"results": [item()]}), encoding="utf-8")
    after.write_text(json.dumps({"results": []}), encoding="utf-8")
    output = tmp_path / "nested" / "delta.json"
    monkeypatch.setattr(sys, "argv", [
        "bandit_comparable_delta.py", "--before", str(before),
        "--after", str(after), "--before-sha", "a" * 40,
        "--after-sha", "b" * 40, "--before-config", "full",
        "--after-config", "full", "--out", str(output),
    ])
    module.main()
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["before_sha"] == "a" * 40
    assert receipt["after_sha"] == "b" * 40
    assert receipt["resolved"] == 1
    assert receipt["security_clearance"] is False
