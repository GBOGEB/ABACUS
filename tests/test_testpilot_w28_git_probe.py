"""W28 reverse/negative native tests for preflight Git and subprocess receipts.

These cases explicitly distinguish a successful empty Git census from a failed
Git command, without relaxing the existing CI or security acceptance policy.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import testpilot_preflight as pilot


def _proc(stdout="", stderr="", code=0):
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=code)


@pytest.mark.parametrize("code", [1, 128, 255])
def test_force_trip_failed_git_probes_cannot_be_empty_success(monkeypatch, code):
    monkeypatch.setattr(pilot.subprocess, "run", lambda *a, **k: _proc("", "fatal", code))
    with pytest.raises(pilot.GitProbeError, match=f"git diff exited {code}"):
        pilot.git_lines("diff", "--name-only")


@pytest.mark.parametrize("exc", [FileNotFoundError("git"), PermissionError("git")])
def test_force_trip_git_spawn_error_cannot_be_empty_success(monkeypatch, exc):
    def broken(*args, **kwargs):
        raise exc
    monkeypatch.setattr(pilot.subprocess, "run", broken)
    with pytest.raises(pilot.GitProbeError, match="git diff unavailable"):
        pilot.git_lines("diff", "--name-only")


def test_reverse_successful_empty_git_census_is_allowed(monkeypatch):
    monkeypatch.setattr(pilot.subprocess, "run", lambda *a, **k: _proc())
    assert pilot.git_lines("diff", "--name-only") == []


@pytest.mark.parametrize("stage", [
    ("diff", "--cached", "--name-only", "--diff-filter=ACMR"),
    ("diff", "--name-only", "--diff-filter=ACMR"),
    ("ls-files", "--others", "--exclude-standard"),
])
def test_force_trip_each_changed_file_census_source_fails_closed(monkeypatch, stage):
    def fake(*args):
        if args == stage:
            raise pilot.GitProbeError("injected git failure")
        return []
    monkeypatch.setattr(pilot, "git_lines", fake)
    with pytest.raises(pilot.GitProbeError, match="injected git failure"):
        pilot.changed_files()


@pytest.mark.parametrize("reported", [
    [], ["a" * 39], ["a" * 41], ["A" * 40], ["not-a-sha"],
    ["a" * 40, "b" * 40],
])
def test_negative_noncanonical_head_remains_unknown(monkeypatch, reported):
    monkeypatch.setattr(pilot, "git_lines", lambda *a: reported)
    assert pilot.source_sha() is None


def test_positive_full_lowercase_source_sha(monkeypatch):
    monkeypatch.setattr(pilot, "git_lines", lambda *a: ["a" * 40])
    assert pilot.source_sha() == "a" * 40


@pytest.mark.parametrize("exc", [
    FileNotFoundError("tool"), PermissionError("tool"),
    subprocess.TimeoutExpired(cmd=["tool"], timeout=3),
])
def test_force_trip_subprocess_spawn_or_timeout_preserves_fail_receipt(monkeypatch, exc):
    def broken(*args, **kwargs):
        raise exc
    monkeypatch.setattr(pilot.subprocess, "run", broken)
    report = pilot.run(["tool"])
    assert report["status"] == "FAIL"
    assert report["returncode"] is None
    assert report["error_kind"] == type(exc).__name__
    assert report["seconds"] >= 0


def _main(monkeypatch, tmp_path, *, files=None, sha="a" * 40):
    output = tmp_path / "preflight.json"
    monkeypatch.setattr(sys, "argv", [
        "testpilot_preflight.py", "--mode", "fast", "--receipt", str(output)
    ])
    def sample_files():
        if isinstance(files, Exception):
            raise files
        return [] if files is None else files
    def sample_sha():
        if isinstance(sha, Exception):
            raise sha
        return sha
    monkeypatch.setattr(pilot, "changed_files", sample_files)
    monkeypatch.setattr(pilot, "source_sha", sample_sha)
    monkeypatch.setattr(pilot, "targeted_pytest",
                        lambda: [{"name": "injected-targeted", "status": "PASS"}])
    code = pilot.main()
    return code, json.loads(output.read_text(encoding="utf-8"))


def test_force_trip_git_change_detection_error_is_persisted(monkeypatch, tmp_path):
    code, report = _main(monkeypatch, tmp_path,
                         files=pilot.GitProbeError("diff exploded"))
    assert code == 1 and report["status"] == "FAIL"
    assert report["source_sha"] == "a" * 40
    assert report["subject_files"] == []
    assert any(c["name"] == "git_changed_files" and c["status"] == "FAIL"
               for c in report["checks"])


def test_force_trip_git_head_probe_error_is_persisted(monkeypatch, tmp_path):
    code, report = _main(monkeypatch, tmp_path,
                         sha=pilot.GitProbeError("rev-parse exploded"))
    assert code == 1 and report["status"] == "FAIL"
    assert report["source_sha"] is None
    assert any(c["name"] == "git_source_sha" and c["status"] == "FAIL"
               for c in report["checks"])


@pytest.mark.parametrize("reported", [None, "", "xyz"])
def test_force_trip_missing_head_never_claims_green(monkeypatch, tmp_path, reported):
    code, report = _main(monkeypatch, tmp_path, sha=reported)
    assert code == 1 and report["status"] == "FAIL"
    assert any(c["name"] == "git_source_sha" and c["status"] == "FAIL"
               for c in report["checks"])


def test_reverse_successful_empty_diff_and_full_sha_do_not_force_false_red(monkeypatch, tmp_path):
    code, report = _main(monkeypatch, tmp_path)
    assert code == 0 and report["status"] == "PASS"
    assert report["failure_count"] == 0
    assert report["unverified_check_count"] == 0


def test_force_trip_git_failure_dominates_independent_success(monkeypatch, tmp_path):
    code, report = _main(monkeypatch, tmp_path,
                         files=pilot.GitProbeError("one Git probe failed"))
    assert code == 1 and report["status"] == "FAIL"
    assert any(x.get("status") == "PASS" for x in report["checks"])
    assert report["failure_count"] >= 1


def test_force_trip_actual_targeted_subprocess_failure_is_not_success(monkeypatch, tmp_path):
    output = tmp_path / "preflight-targeted.json"
    monkeypatch.setattr(sys, "argv", ["testpilot_preflight.py", "--mode", "fast",
                                     "--receipt", str(output)])
    monkeypatch.setattr(pilot, "changed_files", lambda: [])
    monkeypatch.setattr(pilot, "source_sha", lambda: "b" * 40)
    monkeypatch.setattr(pilot, "targeted_pytest",
                        lambda: [{"name": "nested-test", "status": "FAIL",
                                  "returncode": None, "error_kind": "FileNotFoundError"}])
    assert pilot.main() == 1
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["status"] == "FAIL"
    assert receipt["failure_count"] == 1
    assert receipt["checks"][-1]["error_kind"] == "FileNotFoundError"
