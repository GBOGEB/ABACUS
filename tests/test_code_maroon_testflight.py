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
    cases = [
        (c, f'<testcase classname="tests.{c}" name="test_example"/>')
        for c in M.COHORTS
        if c != missing
    ]
    n = len(cases) if total is None else total
    value = (
        f'<testsuite tests="{n}" failures="{failures}" errors="{errors}" '
        f'skipped="{skipped}">' + "".join(x[1] for x in cases) + "</testsuite>"
    )
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


@pytest.mark.parametrize(
    "args,fragment",
    [
        ({"total": 0}, "denominator"),
        ({"total": 9}, "denominator"),
        ({"failures": 1}, "failed"),
        ({"errors": 1}, "failed"),
        ({"skipped": 1}, "failed"),
        ({"missing": "test_code_maroon_ooxml"}, "cohort"),
    ],
)
def test_bad_junit_rejected(tmp_path, args, fragment):
    with pytest.raises(ValueError, match=fragment):
        M.verify_junit(junit(tmp_path, **args), SHA)


def test_missing_source_sha_rejected(tmp_path):
    with pytest.raises(ValueError, match="source SHA"):
        M.verify_junit(junit(tmp_path), "unknown")


def test_duplicate_test_identity_rejected(tmp_path):
    path = junit(tmp_path)
    raw = (
        path.read_text()
        .replace('tests="3"', 'tests="4"')
        .replace(
            "</testsuite>",
            '<testcase classname="tests.test_code_maroon_ooxml" name="test_example"/></testsuite>',
        )
    )
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
        (root / "tests" / (name + ".py")).write_text(
            "def test_example():\n    assert True\n"
        )
    (root / ".github/workflows/code-maroon.yml").write_text(
        "run: python -m unittest tests/test_code_maroon_reconcile.py\n"
        "verify: testflight_guard.py verify\n--junitxml=report.xml\n"
    )
    with pytest.raises(ValueError, match="pytest runner"):
        M.preflight(root)


def test_no_pytest_functions_rejected(tmp_path):
    root = tmp_path
    (root / ".github/workflows").mkdir(parents=True)
    (root / "tests").mkdir()
    for name in M.COHORTS:
        (root / "tests" / (name + ".py")).write_text("# no tests\n")
    (root / ".github/workflows/code-maroon.yml").write_text(
        "run: python -m pytest --noconftest --junitxml=report.xml\n"
        "verify: testflight_guard.py verify\n"
    )
    with pytest.raises(ValueError, match="no pytest tests"):
        M.preflight(root)


def test_missing_conftest_isolation_fails_closed(tmp_path):
    root = tmp_path
    (root / ".github/workflows").mkdir(parents=True)
    (root / "tests").mkdir()
    for name in M.COHORTS:
        (root / "tests" / (name + ".py")).write_text(
            "def test_case():\n    assert True\n"
        )
    (root / ".github/workflows/code-maroon.yml").write_text(
        "run: python -m pytest --junitxml=report.xml\n"
        "verify: testflight_guard.py verify\n"
    )
    with pytest.raises(ValueError, match="conftest isolation"):
        M.preflight(root)


def test_cli_verify_emits_digest_and_exact_source_receipt(
    tmp_path, monkeypatch, capsys
):
    import hashlib
    import json
    import sys

    source = junit(tmp_path)
    target = tmp_path / "nested" / "verified.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "testflight_guard",
            "verify",
            "--junit",
            str(source),
            "--source-sha",
            SHA,
            "--out",
            str(target),
        ],
    )
    M.main()
    raw = target.read_bytes()
    receipt = json.loads(raw)
    assert receipt["source_sha"] == SHA
    assert receipt["tests_executed"] == 3
    assert receipt["merge_authorized"] is False
    assert (
        target.with_suffix(".sha256").read_text().strip()
        == hashlib.sha256(raw).hexdigest()
    )
    assert (
        json.loads(capsys.readouterr().out)["junit_sha256"] == receipt["junit_sha256"]
    )


def test_cli_preflight_does_not_claim_executed_tests(monkeypatch, capsys):
    import json
    import sys

    monkeypatch.setattr(sys, "argv", ["testflight_guard", "preflight"])
    M.main()
    result = json.loads(capsys.readouterr().out)
    assert result["collection_proved"] is False
    assert all(n > 0 for n in result["declared_test_functions"].values())


def test_cli_invalid_source_fails_closed_with_explicit_hold(
    tmp_path, monkeypatch, capsys
):
    import sys

    source = junit(tmp_path)
    target = tmp_path / "should-not-exist.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "testflight_guard",
            "verify",
            "--junit",
            str(source),
            "--source-sha",
            "INVALID",
            "--out",
            str(target),
        ],
    )
    with pytest.raises(SystemExit) as exc:
        M.main()
    assert exc.value.code == 2
    assert "TESTFLIGHT HOLD" in capsys.readouterr().err
    assert not target.exists()
