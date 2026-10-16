"""Adversarial regression controls for MIP2 evidence identity and confidential logs."""
import json
import pathlib
import re
import subprocess
import sys
from types import SimpleNamespace

import pytest
from defusedxml.common import DefusedXmlException

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "mip2"))
import local_testflight as local
from mip3_flight import junit

GOOD_SHA = "a" * 40


def test_command_receipt_does_not_persist_stdout_or_stderr(monkeypatch):
    monkeypatch.setattr(local.subprocess, "run", lambda *a, **k: SimpleNamespace(
        returncode=1, stdout="PRIVATE_TEST_SECRET", stderr="PRIVATE_TEST_TOKEN"))
    result = local.command("pytest", ["python", "-m", "pytest"])
    assert result["status"] == "FAIL"
    assert "PRIVATE_TEST_SECRET" not in json.dumps(result)
    assert "PRIVATE_TEST_TOKEN" not in json.dumps(result)
    assert "stdout_tail" not in result and "stderr_tail" not in result


def test_git_sha_is_source_validated(monkeypatch):
    monkeypatch.setattr(local.subprocess, "run", lambda *a, **k: SimpleNamespace(
        returncode=0, stdout=GOOD_SHA + "\n", stderr=""))
    result = local.command("git-head", ["git", "rev-parse", "HEAD"])
    assert result["status"] == "PASS"
    assert result["head_sha"] == GOOD_SHA


@pytest.mark.parametrize("git_output", ["", "synthetic merge", "a" * 39, "z" * 40, "a" * 41])
def test_invalid_git_identity_is_not_a_pass(monkeypatch, git_output):
    monkeypatch.setattr(local.subprocess, "run", lambda *a, **k: SimpleNamespace(
        returncode=0, stdout=git_output, stderr=""))
    result = local.command("git-head", ["git", "rev-parse", "HEAD"])
    assert result["status"] != "PASS"
    assert "head_sha" not in result


@pytest.mark.parametrize("observed,expected,want_success", [
    (None, None, False), (GOOD_SHA, "b" * 40, False),
    (GOOD_SHA, GOOD_SHA, True),
])
def test_local_flight_gates_identity_and_expected_head(monkeypatch, tmp_path, observed, expected, want_success):
    def fake_command(label, argv):
        if label == "git-head":
            if observed is None:
                return {"name": label, "status": "ERROR", "error_type": "FileNotFoundError"}
            return {"name": label, "status": "PASS", "head_sha": observed}
        return {"name": label, "status": "PASS", "exit_code": 0}
    monkeypatch.setattr(local, "command", fake_command)
    output = tmp_path / "flight.json"
    argv = ["local_testflight.py", "--output", str(output)]
    if expected:
        argv.extend(["--expected-head", expected])
    monkeypatch.setattr(sys, "argv", argv)
    exit_code = local.main()
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert (exit_code == 0) is want_success
    assert (receipt["status"] == "PASS") is want_success
    assert any(step["name"] == "git-head" for step in receipt["checks"])


def test_junit_rejects_entity_expansion(tmp_path):
    path = tmp_path / "junit.xml"
    path.write_text('<!DOCTYPE testsuite [<!ENTITY payload "forbidden">]>'
                    '<testsuite tests="1" failures="0" errors="0" skipped="0">'
                    '<testcase name="x">&payload;</testcase></testsuite>', encoding="utf-8")
    with pytest.raises(DefusedXmlException):
        junit(path)


@pytest.mark.parametrize("xml", [
    "<testsuite tests='1' failures='0' errors='0'/>",
    "<testsuites/>",
    "<not-junit tests='1' failures='0' errors='0' skipped='0'/>",
    "<testsuite tests='-1' failures='0' errors='0' skipped='0'/>",
    "<testsuite tests='1' failures='1' errors='1' skipped='0'/>",
])
def test_incomplete_or_inconsistent_junit_fails_closed(tmp_path, xml):
    path = tmp_path / "junit.xml"
    path.write_text(xml, encoding="utf-8")
    with pytest.raises(ValueError):
        junit(path)


def test_junit_input_size_limit(tmp_path, monkeypatch):
    path = tmp_path / "junit.xml"
    path.write_text('<testsuite tests="1" failures="0" errors="0" skipped="0"/>', encoding="utf-8")
    original = pathlib.Path.stat
    def oversized(self, *a, **k):
        v = original(self, *a, **k)
        if self == path:
            return SimpleNamespace(st_size=65 * 1024 * 1024)
        return v
    monkeypatch.setattr(pathlib.Path, "stat", oversized)
    with pytest.raises(ValueError, match="TOO_LARGE"):
        junit(path)


def test_native_checkout_and_credential_controls():
    workflow = (ROOT / ".github/workflows/mip2-method-qualification.yml").read_text()
    assert "github.event.pull_request.head.sha || github.sha" in workflow
    assert "persist-credentials: false" in workflow
    assert 'test "$(git rev-parse HEAD)" = "$EXPECTED_SHA"' in workflow
    assert '--expected-head "$EXPECTED_HEAD"' in workflow


def test_precommit_matches_real_python_paths():
    pre = (ROOT / ".pre-commit-config.yaml").read_text()
    found = re.search(r"^        files: (\S+)$", pre, flags=re.MULTILINE)
    assert found is not None
    assert re.match(found.group(1), "tools/mip2/mip3_flight.py")
    assert not re.match(found.group(1), "tools/mip2/README.md")
