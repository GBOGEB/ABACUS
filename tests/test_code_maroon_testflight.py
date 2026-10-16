"""Regression tests for zero-test false greens and forged JUnit evidence."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/code_maroon/testflight_guard.py"
SPEC = importlib.util.spec_from_file_location("testflight_guard", SOURCE)
M = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(M)
SHA = "a" * 40


def junit(tmp_path, *, total=None, failures=0, errors=0, skipped=0, missing=None):
    cases = [(c, f'<testcase classname="tests.{c}" name="test_example"/>')
             for c in M.COHORTS if c != missing]
    n = len(cases) if total is None else total
    value = (f'<testsuite tests="{n}" failures="{failures}" errors="{errors}" '
             f'skipped="{skipped}">' + "".join(x[1] for x in cases) + '</testsuite>')
    path = tmp_path / "report.xml"
    path.write_text(value, encoding="utf-8")
    return path


def test_real_preflight_reports_declarations_only():
    report = M.preflight()
    assert min(report["declared_test_functions"].values()) >= 1
    assert report["collection_proved"] is False


def test_valid_junit_require_all_cohorts(tmp_path):
    r = M.verify_junit(junit(tmp_path), SHA)
    assert r["tests_executed"] == 3
    assert r["merge_authorized"] is False


@pytest.mark.parametrize("args,fragment", [
    ({"total": 0}, "denominator"),
    ({"total": 9}, "denominator"),
    ({"failures": 1}, "failed"),
    ({"errors": 1}, "failed"),
    ({"skipped": 1}, "failed"),
    ({"missing": "test_code_maroon_ooxml"}, "cohort"),
])
def test_bad_junit_rejected(tmp_path, args, fragment):
    with pytest.raises(ValueError, match=fragment):
        M.verify_junit(junit(tmp_path, **args), SHA)


def test_missing_source_sha_rejected(tmp_path):
    with pytest.raises(ValueError, match="source SHA"):
        M.verify_junit(junit(tmp_path), "unknown")


def test_duplicate_test_identity_rejected(tmp_path):
    path = junit(tmp_path)
    raw = path.read_text().replace('tests="3"', 'tests="4"').replace(
        '</testsuite>',
        '<testcase classname="tests.test_code_maroon_ooxml" name="test_example"/></testsuite>')
    path.write_text(raw, encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        M.verify_junit(path, SHA)


def test_empty_suite_rejected(tmp_path):
    path = tmp_path / "empty.xml"
    path.write_text('<testsuite tests="0" errors="0" failures="0" skipped="0"/>')
    with pytest.raises(ValueError, match="zero tests"):
        M.verify_junit(path, SHA)


def test_doctype_rejected(tmp_path):
    path = junit(tmp_path)
    path.write_text('<!DOCTYPE note [<!ENTITY x "bad">]>' + path.read_text())
    with pytest.raises(ValueError, match="unsafe"):
        M.verify_junit(path, SHA)


def test_unittest_runner_false_green_rejected(tmp_path):
    root = tmp_path
    (root / ".github/workflows").mkdir(parents=True)
    (root / "tests").mkdir()
    for name in M.COHORTS:
        (root / "tests" / (name + ".py")).write_text("def test_example():\n    assert True\n")
    (root / ".github/workflows/code-maroon.yml").write_text(
        "run: python -m unittest tests/test_code_maroon_reconcile.py\n"
        "verify: testflight_guard.py verify\n--junitxml=report.xml\n")
    with pytest.raises(ValueError, match="pytest runner"):
        M.preflight(root)


def test_no_pytest_functions_rejected(tmp_path):
    root = tmp_path
    (root / ".github/workflows").mkdir(parents=True)
    (root / "tests").mkdir()
    for name in M.COHORTS:
        (root / "tests" / (name + ".py")).write_text("# no tests\n")
    (root / ".github/workflows/code-maroon.yml").write_text(
        "run: python -m pytest --junitxml=report.xml\n"
        "verify: testflight_guard.py verify\n")
    with pytest.raises(ValueError, match="no pytest tests"):
        M.preflight(root)
