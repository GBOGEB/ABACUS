"""W26 adversarial tests of exact-head scoped TestPilot coverage admission."""

from __future__ import annotations

import json

import pytest

from tools.mip2 import testpilot_coverage_compare as m

SHA = "a" * 40
B = {
    "num_statements": 154,
    "covered_lines": 88,
    "num_branches": 50,
    "covered_branches": 18,
}
A = {
    "num_statements": 154,
    "covered_lines": 150,
    "num_branches": 50,
    "covered_branches": 48,
}
J0 = {"tests": 14, "failures": 0, "errors": 0, "skipped": 0}
J1 = {"tests": 66, "failures": 0, "errors": 0, "skipped": 0}


def _file(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def _cov(tmp_path, name, totals, branch=True, path=m.EXPECTED_FILE):
    return _file(
        tmp_path,
        name,
        json.dumps(
            {
                "meta": {"branch_coverage": branch},
                "files": {path: {"summary": totals}},
                "totals": totals,
            }
        ),
    )


def test_positive_exact_head_matched_scoped_uplift():
    r = m.compare(B, A, J0, J1, SHA)
    assert r["uplift"]["covered_statements"] == 62
    assert r["uplift"]["covered_branches"] == 30
    assert r["uplift"]["additional_executed_tests"] == 52
    assert r["uplift"]["combined_denominator"] == 204
    assert r["global_main_coverage_uplift"] is None
    assert r["governed_merge_admission"] == "HOLD"


@pytest.mark.parametrize("head", ["", "invalid", "a" * 39, "a" * 41, "z" * 40, None])
def test_negative_exact_sha_required(head):
    with pytest.raises(ValueError, match="exact-source SHA"):
        m.compare(B, A, J0, J1, head)


def test_reverse_statement_denominator_change_not_comparable():
    with pytest.raises(ValueError, match="mismatched coverage denominators"):
        m.compare(B, {**A, "num_statements": 155}, J0, J1, SHA)


def test_reverse_branch_denominator_change_not_comparable():
    with pytest.raises(ValueError, match="mismatched coverage denominators"):
        m.compare(B, {**A, "num_branches": 51}, J0, J1, SHA)


def test_force_trip_missed_branch_not_hidden_by_line_uplift():
    with pytest.raises(ValueError, match="coverage regression"):
        m.compare(B, {**A, "covered_branches": 17}, J0, J1, SHA)


def test_negative_same_test_count_cannot_claim_growth():
    with pytest.raises(ValueError, match="new test cases"):
        m.compare(B, A, J0, J0, SHA)


def test_negative_zero_branch_uplift_not_credited():
    with pytest.raises(ValueError, match="statement and branch uplift"):
        m.compare(B, {**A, "covered_branches": 18}, J0, J1, SHA)


def test_negative_zero_statement_uplift_not_credited():
    with pytest.raises(ValueError, match="statement and branch uplift"):
        m.compare(B, {**A, "covered_lines": 88}, J0, J1, SHA)


def test_positive_branch_instrumentation_and_sha256(tmp_path):
    path = _cov(tmp_path, "coverage.json", B)
    data, sha = m.load_coverage(path)
    assert data == B and len(sha) == 64


def test_force_trip_coverage_without_branch_instrumentation(tmp_path):
    path = _cov(tmp_path, "coverage.json", B, False)
    with pytest.raises(ValueError, match="branch instrumentation required"):
        m.load_coverage(path)


def test_negative_foreign_module_scope_rejected(tmp_path):
    path = _cov(tmp_path, "coverage.json", B, True, "scripts/other.py")
    with pytest.raises(ValueError, match="only exact TestPilot"):
        m.load_coverage(path)


def test_negative_nonnumeric_coverage_denominator_rejected(tmp_path):
    path = _cov(tmp_path, "coverage.json", {**B, "num_statements": "154"})
    with pytest.raises(ValueError, match="nonnegative coverage integer"):
        m.load_coverage(path)


def test_negative_impossible_coverage_rejected(tmp_path):
    path = _cov(tmp_path, "coverage.json", {**B, "covered_lines": 155})
    with pytest.raises(ValueError, match="invalid covered population"):
        m.load_coverage(path)


def test_negative_coverage_zero_size_rejected(tmp_path):
    path = _file(tmp_path, "coverage.json", "")
    with pytest.raises(ValueError, match="missing or oversized"):
        m.load_coverage(path)


def test_positive_junit_parses_fail_closed(tmp_path):
    path = _file(
        tmp_path,
        "junit.xml",
        '<testsuites><testsuite tests="14" failures="0" errors="0" skipped="0">'
        + "".join(f'<testcase classname="suite" name="test_{i}"/>' for i in range(14))
        + "</testsuite></testsuites>",
    )
    result, digest = m.load_junit(path)
    assert result == J0 and len(digest) == 64


@pytest.mark.parametrize(
    "xml,reason",
    [
        ('<testsuite tests="0" failures="0" errors="0" skipped="0"/>', "zero tests"),
        (
            '<testsuite tests="1" failures="1" errors="0" skipped="0"><testcase classname="c" name="f"><failure/></testcase></testsuite>',
            "failing JUnit",
        ),
        (
            '<testsuite tests="1" failures="0" errors="1" skipped="0"><testcase classname="c" name="e"><error/></testcase></testsuite>',
            "failing JUnit",
        ),
        (
            '<testsuite tests="nan" failures="0" errors="0" skipped="0"/>',
            "invalid JUnit",
        ),
        (
            '<not-junit tests="1" failures="0" errors="0" skipped="0"/>',
            "JUnit root invalid",
        ),
    ],
)
def test_force_trip_junit_denies_false_green(tmp_path, xml, reason):
    path = _file(tmp_path, "junit.xml", xml)
    with pytest.raises(ValueError, match=reason):
        m.load_junit(path)


def test_negative_xml_entity_expansion_rejected(tmp_path):
    path = _file(
        tmp_path,
        "junit.xml",
        '<!DOCTYPE testsuite [<!ENTITY x "secret">]'
        '<testsuite tests="1" failures="0" errors="0" skipped="0">&x;</testsuite>',
    )
    with pytest.raises(Exception):
        m.load_junit(path)


def test_negative_junit_missing_file_is_not_unknown_as_zero(tmp_path):
    with pytest.raises(FileNotFoundError):
        m.load_junit(tmp_path / "nonexistent.xml")


def test_force_trip_coverage_summary_disagrees_with_totals(tmp_path):
    path = _cov(tmp_path, "coverage.json", B)
    data = json.loads(path.read_text())
    data["files"][m.EXPECTED_FILE]["summary"]["covered_lines"] -= 1
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="source/global totals mismatch"):
        m.load_coverage(path)


def test_force_trip_coverage_summary_absent(tmp_path):
    path = _cov(tmp_path, "coverage.json", B)
    data = json.loads(path.read_text())
    data["files"][m.EXPECTED_FILE] = {}
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="source coverage summary missing"):
        m.load_coverage(path)


@pytest.mark.parametrize(
    "xml,reason",
    [
        (
            '<testsuite tests="2" failures="0" errors="0" skipped="0">'
            '<testcase classname="c" name="only"/></testsuite>',
            "testcase count",
        ),
        (
            '<testsuite tests="1" failures="0" errors="0" skipped="0">'
            '<testcase classname="c"/></testsuite>',
            "identity missing",
        ),
        (
            '<testsuite tests="2" failures="0" errors="0" skipped="0">'
            '<testcase classname="c" name="duplicate"/>'
            '<testcase classname="c" name="duplicate"/></testsuite>',
            "duplicate JUnit",
        ),
        (
            '<testsuite tests="1" failures="0" errors="0" skipped="1">'
            '<testcase classname="c" name="not_skipped"/></testsuite>',
            "testcase outcomes",
        ),
        (
            '<testsuite tests="1" failures="0" errors="0" skipped="0">'
            '<testcase classname="c" name="failure"><failure/></testcase></testsuite>',
            "testcase outcomes",
        ),
        (
            '<testsuite tests="1" failures="0" errors="0" skipped="0">'
            '<testcase classname="c" name="conflict"><failure/><skipped/></testcase></testsuite>',
            "conflicting JUnit",
        ),
    ],
)
def test_force_trip_unreliable_junit_manifest(tmp_path, xml, reason):
    with pytest.raises(ValueError, match=reason):
        m.load_junit(_file(tmp_path, "integrity.xml", xml))


def test_reverse_skipped_growth_is_not_executed_growth():
    before = {"tests": 14, "failures": 0, "errors": 0, "skipped": 0}
    after = {"tests": 20, "failures": 0, "errors": 0, "skipped": 6}
    with pytest.raises(ValueError, match="independently executed"):
        m.compare(B, A, before, after, SHA)


def test_positive_real_executed_growth_excludes_skips():
    before = {"tests": 14, "failures": 0, "errors": 0, "skipped": 2}
    after = {"tests": 20, "failures": 0, "errors": 0, "skipped": 3}
    assert (
        m.compare(B, A, before, after, SHA)["uplift"]["additional_executed_tests"] == 5
    )


# W28: native Windows JSON separator qualification; preserve fail-closed scope.
@pytest.mark.parametrize(
    "key",
    [
        "scripts/testpilot_preflight.py",
        r"scripts\testpilot_preflight.py",
    ],
)
def test_native_platform_exact_source_key_is_accepted(tmp_path, key):
    source = _cov(tmp_path, "native-coverage.json", B, path=key)
    counts, raw_sha256 = m.load_coverage(source)
    assert counts == B
    assert len(raw_sha256) == 64


@pytest.mark.parametrize(
    "wrong",
    [
        r"scripts\..\testpilot_preflight.py",
        r"C:\repo\scripts\testpilot_preflight.py",
        "./scripts/testpilot_preflight.py",
        "../scripts/testpilot_preflight.py",
        "/scripts/testpilot_preflight.py",
        r"scripts\/testpilot_preflight.py",
        r"scripts\TESTPILOT_preflight.py",
        "scripts/testpilot_preflight.py/",
    ],
)
def test_native_path_whitelist_rejects_aliases_or_traversal(tmp_path, wrong):
    source = _cov(tmp_path, "invalid-path.json", B, path=wrong)
    with pytest.raises(ValueError, match="only exact TestPilot"):
        m.load_coverage(source)


def test_dual_platform_keys_do_not_double_count_one_module(tmp_path):
    source = _cov(tmp_path, "double-path.json", B)
    doc = json.loads(source.read_text(encoding="utf-8"))
    doc["files"][r"scripts\testpilot_preflight.py"] = {"summary": B}
    source.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ValueError, match="only exact TestPilot"):
        m.load_coverage(source)
