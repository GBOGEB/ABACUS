"""Regression tests for disjoint Bandit worker census."""
from importlib import import_module

import pytest

module = import_module("scripts.bandit_disjoint_census")


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


@pytest.mark.parametrize("unsafe", [
    "/etc/passwd", "//server/share.py", r"\\server\share.py",
    "src/../outside.py", "src\\..\\outside.py",
])
def test_normalized_absolute_and_parent_paths_remain_rejected(unsafe):
    with pytest.raises(ValueError, match="Unsafe report path"):
        module.partition({"results": [finding(unsafe, "B603")]}, "a" * 40)


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


@pytest.mark.parametrize(
    "unsafe",
    ["/root.py", "///tmp/report.py", r"\root.py", r"\\server\share.py"],
)
def test_repeated_root_separators_fail_closed(unsafe):
    """Rooted paths remain unsafe before canonical separator coalescing."""
    with pytest.raises(ValueError, match="Unsafe report path"):
        module.partition({"results": [finding(unsafe, "B603")]}, "d" * 40)


@pytest.mark.parametrize(
    "safe",
    ["./src/worker.py", "src//worker.py", r"src\\worker.py", "src/./worker.py"],
)
def test_safe_relative_aliases_deduplicate_without_mutation(safe):
    row = finding(safe, "B603")
    snapshot = dict(row)
    result = module.partition({"results": [row, finding("src/worker.py", "B603")]}, "e" * 40)
    assert row == snapshot
    assert result["total_unique"] == 1
    assert result["lanes"]["B3-subprocess"]["files"] == 1
    assert result["lanes"]["B3-subprocess"]["items"][0]["path"] == "src/worker.py"
    assert result["authority_transfer"] is False


def test_mixed_safe_and_unsafe_paths_fail_atomically():
    report = {"results": [
        finding("src/safe.py", "B603"),
        finding("src/../outside.py", "B603"),
    ]}
    with pytest.raises(ValueError, match="Unsafe report path"):
        module.partition(report, "e" * 40)
    assert len(report["results"]) == 2


@pytest.mark.parametrize("unsafe", [
    "C:relative.py", "D:/absolute.py", r"D:\\relative.py",
    "src/../escape.py", r"src\\..\\escape.py",
    "//host/share.py", r"\\\\host\\share.py",
    "/absolute.py",
])
def test_drive_unc_and_traversal_are_rejected(unsafe):
    with pytest.raises(ValueError, match="Unsafe report path"):
        module.partition({"results": [finding(unsafe, "B105")]}, "f" * 40)


def test_same_file_mixed_b3_b4_b5_rules_have_one_owner():
    rows = [finding("tests/test_mix.py", "B603"),
            finding("tests/test_mix.py", "B105", 2),
            finding("tests/test_mix.py", "B101", 3)]
    result = module.partition({"results": rows}, "f" * 40)
    assert result["total_unique"] == 3
    assert result["lanes"]["B5-tests"]["findings"] == 3
    assert sum(v["files"] for v in result["lanes"].values()) == 1


@pytest.mark.parametrize("invalid", [123, [], None, {"results": "invalid"},
                                     {"results": [None]}])
def test_malformed_report_fails_closed(invalid):
    with pytest.raises((ValueError, AttributeError, TypeError)):
        module.partition(invalid, "f" * 40)


@pytest.mark.parametrize("malformed", [None, [], 12, "not a report"])
def test_non_object_report_rejected_explicitly(malformed):
    with pytest.raises(ValueError, match="Bandit JSON shall be an object"):
        module.partition(malformed, "f" * 40)


@pytest.mark.parametrize("malformed_row", [None, [], 12, "not a finding"])
def test_non_object_finding_rejected_explicitly(malformed_row):
    with pytest.raises(ValueError, match="Bandit finding shall be an object"):
        module.partition({"results": [malformed_row]}, "f" * 40)


@pytest.mark.parametrize(
    ("path", "rule", "expected_lane"),
    [
        ("src/worker.py", "B603", "B3-subprocess"),
        ("src/worker.py", "B602", "B3-subprocess"),
        ("src/worker.py", "B609", "B3-subprocess"),
        ("src/worker.py", "B105", "B4-files-secrets"),
        ("src/worker.py", "B404", "B4-files-secrets"),
        ("src/worker.py", "B701", "B2-source"),
        ("tests/helper.py", "B603", "B5-tests"),
        ("src/test_worker.py", "B105", "B5-tests"),
    ],
)
def test_rule_and_file_classification_branches(path, rule, expected_lane):
    census = module.partition({"results": [finding(path, rule)]}, "a" * 40)
    assert census["total_unique"] == 1
    assert census["lanes"][expected_lane]["findings"] == 1
    assert sum(x["findings"] for x in census["lanes"].values()) == 1


def test_file_owner_priority_reassigns_all_rows_to_subprocess():
    census = module.partition({"results": [
        finding("pkg/tool.py", "B701", 1),
        finding("pkg/tool.py", "B105", 2),
        finding("pkg/tool.py", "B603", 3),
    ]}, "a" * 40)
    assert census["total_unique"] == 3
    assert census["lanes"]["B3-subprocess"]["findings"] == 3
    assert all(census["lanes"][lane]["findings"] == 0 for lane in
               ("B2-source", "B4-files-secrets", "B5-tests"))


def test_deduplication_key_distinguishes_issue_text():
    a = finding("pkg/tool.py", "B105")
    b = dict(a)
    a["issue_text"] = "first finding"
    b["issue_text"] = "second finding"
    census = module.partition({"results": [a, b]}, "a" * 40)
    items = census["lanes"]["B4-files-secrets"]["items"]
    assert len(items) == 2
    assert len({item["fingerprint"] for item in items}) == 2


def test_empty_findings_preserve_four_disjoint_lanes_and_no_approval():
    census = module.partition({"results": []}, "a" * 40)
    assert set(census["lanes"]) == {
        "B2-source", "B3-subprocess", "B4-files-secrets", "B5-tests"
    }
    assert census["security_disposition"] == "pending independent review"
    assert census["authority_transfer"] is False


@pytest.mark.parametrize("invalid_sha", ["short", "G" * 40, "A" * 40])
def test_disjoint_cli_rejects_invalid_sha(tmp_path, monkeypatch, invalid_sha):
    import sys
    report = tmp_path / "bandit.json"
    report.write_text('{"results": []}', encoding="utf-8")
    output = tmp_path / "out.json"
    monkeypatch.setattr(sys, "argv", [
        "bandit_disjoint_census.py", "--report", str(report),
        "--exact-sha", invalid_sha, "--out", str(output),
    ])
    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 2
    assert not output.exists()


def test_disjoint_cli_writes_deterministic_receipt(tmp_path, monkeypatch):
    import json
    import sys
    report = tmp_path / "bandit.json"
    report.write_text(json.dumps({"results": [finding("src/a.py", "B603")]}),
                      encoding="utf-8")
    output = tmp_path / "nested" / "disjoint.json"
    monkeypatch.setattr(sys, "argv", [
        "bandit_disjoint_census.py", "--report", str(report),
        "--exact-sha", "a" * 40, "--out", str(output),
    ])
    module.main()
    first = output.read_bytes()
    module.main()
    assert output.read_bytes() == first
    receipt = json.loads(first)
    assert receipt["total_unique"] == 1
    assert receipt["exact_sha"] == "a" * 40
    assert receipt["security_disposition"] == "pending independent review"


@pytest.mark.parametrize("empty_alias", [".", "./", "././", ".\\\\.", "./././"])
def test_empty_normalized_filename_rejected_before_ownership(empty_alias):
    with pytest.raises(ValueError, match="Unsafe empty report path"):
        module.partition({"results": [finding(empty_alias, "B603")]}, "a" * 40)


def test_b5_tests_directory_classifier_without_test_basename():
    census = module.partition(
        {"results": [finding("nested/tests/conftest.py", "B603")]}, "a" * 40
    )
    assert census["lanes"]["B5-tests"]["findings"] == 1
    assert census["lanes"]["B3-subprocess"]["findings"] == 0
