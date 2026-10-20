"""Fail-closed receipt validation for W3 three-pulse security qualification."""
from __future__ import annotations

from pathlib import Path

import pytest
from defusedxml.common import DefusedXmlException

from scripts.ci.w3_security_native_receipt import build_receipt

SHA = "a" * 40


def write_junit(tmp_path: Path, cases: str | None = None) -> Path:
    if cases is None:
        cases = "".join(f"<testcase name='test_{i}'/>" for i in range(8))
    path = tmp_path / "junit.xml"
    path.write_text("<testsuite>" + cases + "</testsuite>", encoding="utf-8")
    return path


def good_args(path: Path) -> dict:
    return dict(expected_head=SHA, observed_head=SHA,
                run_id="39064371857", attempt=1,
                os_cell="ubuntu-24.04", python_cell="3.10", junit_path=path)


def test_exact_head_good_junit_preserves_nonpromotion(tmp_path):
    value = build_receipt(**good_args(write_junit(tmp_path)))
    assert value["junit"]["total"] == value["junit"]["passed"] == 8
    assert len(value["junit"]["junit_sha256"]) == 64
    assert value["head_sha"] == value["observed_git_head"] == SHA
    assert value["native_run_attempt"] == 1
    assert value["native_numeric_job_id"] is None
    assert value["remote_worker_launch_id"] is None and value["accepted_rex"] is None
    assert value["formal_credit_delta"] == value["engineering_credit_delta"] == 0
    assert value["authority_transfer"] is False and value["security_waiver"] is False
    assert value["merge_admission"] == "HOLD"


@pytest.mark.parametrize(("name", "value"), [
    ("expected_head", "a" * 39),
    ("observed_head", "b" * 40),
    ("run_id", "UNKNOWN"),
    ("run_id", "0"),
    ("attempt", 0),
    ("attempt", False),
    ("os_cell", "UNKNOWN"),
    ("python_cell", "3.9"),
])
def test_forged_or_stale_native_identity_fails_closed(tmp_path, name, value):
    args = good_args(write_junit(tmp_path))
    args[name] = value
    with pytest.raises(ValueError):
        build_receipt(**args)


@pytest.mark.parametrize("cases", [
    "<testcase name='too_few'/>",
    "".join(f"<testcase name='t{i}'/>" for i in range(7)) +
        "<testcase name='skipped'><skipped/></testcase>",
    "".join(f"<testcase name='t{i}'/>" for i in range(7)) +
        "<testcase name='failed'><failure/></testcase>",
    "".join(f"<testcase name='t{i}'/>" for i in range(7)) +
        "<testcase name='error'><error/></testcase>",
])
def test_reduced_or_nonpassing_population_fails_closed(tmp_path, cases):
    with pytest.raises(ValueError):
        build_receipt(**good_args(write_junit(tmp_path, cases)))


def test_missing_junit_is_unknown_not_zero(tmp_path):
    with pytest.raises(ValueError, match="missing native JUnit"):
        build_receipt(**good_args(tmp_path / "missing.xml"))


def test_malicious_xml_entity_cannot_become_green(tmp_path):
    path = tmp_path / "forged.xml"
    path.write_text(
        '<!DOCTYPE testsuite [<!ENTITY forged SYSTEM "file:///etc/passwd">]>'
        '<testsuite><testcase name="&forged;"/></testsuite>',
        encoding="utf-8",
    )
    with pytest.raises(DefusedXmlException):
        build_receipt(**good_args(path))
