"""Regression tests for disjoint Bandit worker census."""
import importlib.util
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1] / "scripts" / "bandit_disjoint_census.py"
SPEC = importlib.util.spec_from_file_location("bandit_disjoint_census", PATH)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def finding(path, rule, line=1):
    return {"filename": path, "test_id": rule, "line_number": line,
            "issue_severity": "MEDIUM", "issue_confidence": "HIGH"}


def test_empty_scan_has_zero_denominator():
    result = module.partition({"results": []}, "a" * 40)
    assert result["total_unique"] == 0
    assert sum(lane["findings"] for lane in result["lanes"].values()) == 0


def test_duplicate_findings_not_double_counted():
    row = finding("src/a.py", "B603")
    result = module.partition({"results": [row, row]}, "a" * 40)
    assert result["total_unique"] == 1
    assert result["lanes"]["B3-subprocess"]["findings"] == 1


def test_file_ownership_exclusive_across_rule_families():
    result = module.partition({"results": [
        finding("src/a.py", "B603"), finding("src/a.py", "B105", 2),
        finding("tests/test_b.py", "B603"), finding("src/c.py", "B101"),
    ]}, "a" * 40)
    assert result["total_unique"] == 4
    ownership = {}
    for lane, info in result["lanes"].items():
        for item in info["items"]:
            assert item["path"] not in ownership or ownership[item["path"]] == lane
            ownership[item["path"]] = lane
    assert ownership["src/a.py"] == "B3-subprocess"
    assert ownership["tests/test_b.py"] == "B5-tests"
    assert result["authority_transfer"] is False


@pytest.mark.parametrize("bad", [{}, {"results": None}, {"results": [{}]}])
def test_invalid_reports_fail_closed(bad):
    with pytest.raises(ValueError):
        module.partition(bad, "a" * 40)


@pytest.mark.parametrize("bad_path", ["/etc/passwd", "../outside.py", "src/../../outside.py"])
def test_unsafe_paths_fail_closed(bad_path):
    with pytest.raises(ValueError):
        module.partition({"results": [finding(bad_path, "B603")]}, "a" * 40)


@pytest.mark.parametrize("line", [None, 0, -1, "3", True])
def test_invalid_line_identity_fails_closed(line):
    with pytest.raises(ValueError, match="line_number"):
        module.partition({"results": [finding("src/a.py", "B603", line)]}, "a" * 40)


def test_rule_counts_reconcile_with_unique_findings():
    result = module.partition({"results": [
        finding("src/a.py", "B603"), finding("src/a.py", "B105", 2),
        finding("src/b.py", "B603"), finding("tests/test_c.py", "B603"),
    ]}, "a" * 40)
    assert sum(lane["findings"] for lane in result["lanes"].values()) == 4
    assert sum(sum(lane["rules"].values()) for lane in result["lanes"].values()) == 4


def test_windows_separator_normalized_to_single_owner():
    result = module.partition({"results": [
        finding("src\\\\a.py", "B603"), finding("src/a.py", "B105", 2)
    ]}, "a" * 40)
    assert result["lanes"]["B3-subprocess"]["files"] == 1
    assert result["lanes"]["B3-subprocess"]["findings"] == 2


def test_repeated_separators_share_one_fingerprint_and_owner():
    rows = [
        finding("src\\\\a.py", "B603"),
        finding("src/a.py", "B603"),
        finding("src//a.py", "B105", 2),
    ]
    result = module.partition({"results": rows}, "a" * 40)
    assert result["total_unique"] == 2
    assert result["lanes"]["B3-subprocess"]["files"] == 1
    assert result["lanes"]["B3-subprocess"]["findings"] == 2
    assert {item["path"] for item in result["lanes"]["B3-subprocess"]["items"]} == {"src/a.py"}


def test_scan_does_not_claim_security_approval():
    result = module.partition({"results": [finding("src/a.py", "B603")]}, "a" * 40)
    assert result["security_disposition"] == "pending independent review"
    assert result["authority_transfer"] is False


def test_mixed_rules_in_test_file_remain_owned_by_test_lane():
    result = module.partition({"results": [
        finding("tests/test_worker.py", "B603"),
        finding("tests/test_worker.py", "B105", 2),
        finding("tests/test_worker.py", "B101", 3),
    ]}, "a" * 40)
    assert result["lanes"]["B5-tests"]["findings"] == 3
    assert result["lanes"]["B3-subprocess"]["files"] == 0
    assert result["lanes"]["B4-files-secrets"]["files"] == 0


@pytest.mark.parametrize(
    "unsafe",
    ["/etc/passwd", "//server/share.py", "../secret.py",
     "src/../secret.py", r"C:\\Windows\\system32.py"],
)
def test_unsafe_paths_rejected_before_normalization(unsafe):
    with pytest.raises(ValueError, match="Unsafe report path"):
        module.partition({"results": [finding(unsafe, "B603")]}, "a" * 40)


def test_redundant_separators_do_not_create_duplicate_owners():
    result = module.partition({"results": [
        finding("src//worker.py", "B603"),
        finding("src/worker.py", "B603"),
    ]}, "a" * 40)
    assert result["total_unique"] == 1
    assert result["lanes"]["B3-subprocess"]["files"] == 1
