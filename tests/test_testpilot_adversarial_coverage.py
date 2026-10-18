"""W26 TestPilot adversarial behavioral coverage: no live subprocesses or CI bypasses.

The real preflight entrypoint is exercised through bounded dependency injection.
Each negative/reverse/force-trip test asserts fail-closed or explicit partial status.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from scripts import testpilot_preflight as pilot


def _mk(tmp_path: Path, name: str, content: str) -> Path:
    dest = tmp_path / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return dest


def _proc(stdout: str = "", stderr: str = "", code: int = 0):
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=code)


def _main_receipt(monkeypatch, tmp_path, *argv, outcomes=None):
    output = tmp_path / "receipt.json"
    monkeypatch.setattr(sys, "argv", ["testpilot_preflight.py", *argv, "--receipt", str(output)])
    monkeypatch.setattr(pilot, "changed_files", lambda: [])
    monkeypatch.setattr(pilot, "parity_subject_files", lambda: [])
    monkeypatch.setattr(pilot, "targeted_pytest", lambda: outcomes if outcomes is not None else [{"name": "targeted", "status": "PASS"}])
    monkeypatch.setattr(pilot, "source_sha", lambda: "a" * 40)
    return output


def test_positive_git_lines_strips_and_drops_empty(monkeypatch):
    monkeypatch.setattr(pilot.subprocess, "run", lambda *a, **k: _proc(" a.py\n\n b.py \n"))
    assert pilot.git_lines("ls-files") == ["a.py", "b.py"]


def test_negative_git_lines_failure_not_misclassified_as_changed_files(monkeypatch):
    monkeypatch.setattr(pilot.subprocess, "run", lambda *a, **k: _proc("a.py", "fatal", 128))
    assert pilot.git_lines("diff") == []  # observed existing behavior; see fail-open BD


def test_positive_run_receipt_records_exit_and_bounded_tails(monkeypatch):
    got = {}
    def fake(cmd, **kw):
        got.update(kw)
        return _proc("x" * 5100, "y" * 5200, 3)
    monkeypatch.setattr(pilot.subprocess, "run", fake)
    monkeypatch.setattr(pilot.time, "monotonic", iter([4.0, 5.2351]).__next__)
    receipt = pilot.run(["tool", "--check"])
    assert receipt["status"] == "FAIL" and receipt["returncode"] == 3
    assert (len(receipt["stdout_tail"]), len(receipt["stderr_tail"])) == (5000, 5000)
    assert receipt["seconds"] == 1.235
    assert got["capture_output"] and got["check"] is False


def test_reverse_run_zero_exit_is_pass_not_forced_red(monkeypatch):
    monkeypatch.setattr(pilot.subprocess, "run", lambda *a, **kw: _proc("ok", "", 0))
    assert pilot.run(["tool"])["status"] == "PASS"


def test_positive_changed_files_deduplicates_three_git_sources(monkeypatch, tmp_path):
    monkeypatch.setattr(pilot, "ROOT", tmp_path)
    _mk(tmp_path, "a.py", "x=1\n")
    _mk(tmp_path, "b.yml", "x: yes\n")
    outputs = iter([["a.py", "b.yml"], ["a.py"], ["b.yml", "missing.py"]])
    monkeypatch.setattr(pilot, "git_lines", lambda *a: next(outputs))
    assert pilot.changed_files() == [tmp_path / "a.py", tmp_path / "b.yml"]


def test_negative_changed_files_excludes_missing_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(pilot, "ROOT", tmp_path)
    monkeypatch.setattr(pilot, "git_lines", lambda *a: ["missing.py"])
    assert pilot.changed_files() == []


def test_positive_parity_subjects_only_existing_files(monkeypatch, tmp_path):
    monkeypatch.setattr(pilot, "ROOT", tmp_path)
    _mk(tmp_path, "scripts/testpilot_preflight.py", "x=1")
    _mk(tmp_path, "pytest.ini", "[pytest]")
    results = [p.relative_to(tmp_path).as_posix() for p in pilot.parity_subject_files()]
    assert results == ["scripts/testpilot_preflight.py", "pytest.ini"]


@pytest.mark.parametrize("text,expected", [
    ("<<<<<<< HEAD\na\n=======\nb\n>>>>>>> other\n", "FAIL"),
    ("<<<<<<< HEAD\na\n=======\n", "PASS"),
    ("literal <<<<<<< and >>>>>>> in a sentence", "PASS"),
    ("ordinary Markdown\n", "PASS"),
])
def test_conflict_triplet_only_when_complete(monkeypatch, tmp_path, text, expected):
    monkeypatch.setattr(pilot, "ROOT", tmp_path)
    p = _mk(tmp_path, "README.md", text)
    got = pilot.check_conflicts([p])
    assert got["status"] == expected
    assert got["files"] == (["README.md"] if expected == "FAIL" else [])


def test_negative_conflicts_missing_text_file_fail_closed(monkeypatch, tmp_path):
    monkeypatch.setattr(pilot, "ROOT", tmp_path)
    got = pilot.check_conflicts([tmp_path / "missing.md"])
    assert got["status"] == "FAIL" and got["files"] == ["missing.md"]


def test_reverse_conflicts_binary_extension_not_scanned(monkeypatch, tmp_path):
    monkeypatch.setattr(pilot, "ROOT", tmp_path)
    p = _mk(tmp_path, "payload.bin", "<<<<<<< HEAD\n=======\n>>>>>>> other\n")
    assert pilot.check_conflicts([p])["status"] == "PASS"


def test_positive_python_compile_valid_file(monkeypatch, tmp_path):
    monkeypatch.setattr(pilot, "ROOT", tmp_path)
    p = _mk(tmp_path, "valid.py", "def f():\n    return 1\n")
    assert pilot.check_python_compile([p]) == {"name": "python_compile", "status": "PASS", "checked": 1, "failures": []}


def test_negative_python_compile_invalid_file_records_error(monkeypatch, tmp_path):
    monkeypatch.setattr(pilot, "ROOT", tmp_path)
    p = _mk(tmp_path, "bad.py", "def f(:\n    pass\n")
    got = pilot.check_python_compile([p])
    assert got["status"] == "FAIL" and got["checked"] == 1
    assert got["failures"][0]["file"] == "bad.py"


def test_reverse_compile_non_python_not_counted(monkeypatch, tmp_path):
    monkeypatch.setattr(pilot, "ROOT", tmp_path)
    p = _mk(tmp_path, "bad.md", "def f(:\n")
    assert pilot.check_python_compile([p])["checked"] == 0


@pytest.mark.parametrize("filename,content,valid", [
    ("v.json", '{"valid": true}', True),
    ("e.json", "{incomplete", False),
    ("v.toml", '[example]\nvalue=12\n', True),
    ("e.toml", '[example\nvalue=1\n', False),
    ("v.yaml", 'items:\n  - one\n', True),
    ("e.yaml", '[unclosed\n', False),
    ("v.yml", 'valid: yes\n', True),
])
def test_configs_detect_parser_failure_not_false_green(monkeypatch, tmp_path, filename, content, valid):
    monkeypatch.setattr(pilot, "ROOT", tmp_path)
    got = pilot.check_configs([_mk(tmp_path, filename, content)])
    assert got["checked"] == 1
    assert got["status"] == ("PASS" if valid else "FAIL")
    assert len(got["failures"]) == (0 if valid else 1)


def test_negative_missing_yaml_config_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setattr(pilot, "ROOT", tmp_path)
    got = pilot.check_configs([tmp_path / "missing.yml"])
    assert got["status"] == "FAIL" and got["checked"] == 1


def test_reverse_config_unknown_extension_not_counted(monkeypatch, tmp_path):
    monkeypatch.setattr(pilot, "ROOT", tmp_path)
    got = pilot.check_configs([_mk(tmp_path, "ignored.ini", "[bad")])
    assert got["status"] == "PASS" and got["checked"] == 0


def test_positive_ruff_no_python_files_is_complete_without_command(monkeypatch, tmp_path):
    monkeypatch.setattr(pilot, "ROOT", tmp_path)
    assert pilot.ruff_check([_mk(tmp_path, "readme.md", "x")], fix=False) == {
        "name": "ruff", "status": "PASS", "checked": 0, "fix": False}


@pytest.mark.parametrize("fix,expected", [(False, "SKIP"), (True, "FAIL")])
def test_negative_ruff_missing_tool_preserves_parity(monkeypatch, tmp_path, fix, expected):
    monkeypatch.setattr(pilot, "ROOT", tmp_path)
    monkeypatch.setattr(pilot.importlib.util, "find_spec", lambda name: None)
    got = pilot.ruff_check([_mk(tmp_path, "app.py", "x=1")], fix=fix)
    assert got["status"] == expected and got["checked"] == 1


@pytest.mark.parametrize("fix", [False, True])
def test_positive_ruff_command_does_not_bypass_verification(monkeypatch, tmp_path, fix):
    monkeypatch.setattr(pilot, "ROOT", tmp_path)
    monkeypatch.setattr(pilot.importlib.util, "find_spec", lambda name: object())
    seen = []
    def fake(cmd, **kw):
        seen.append(cmd)
        return {"status": "FAIL", "returncode": 1}
    monkeypatch.setattr(pilot, "run", fake)
    got = pilot.ruff_check([_mk(tmp_path, "app.py", "x=1")], fix=fix)
    assert got["status"] == "FAIL" and got["checked"] == 1
    assert seen[0][:4] == [sys.executable, "-m", "ruff", "check"]
    assert ("--fix" in seen[0]) is fix
    assert seen[0][-1] == "app.py"


def test_positive_targeted_pytest_two_explicit_commands(monkeypatch):
    seen = []
    def fake(cmd, **kw):
        seen.append(cmd)
        return {"status": "PASS"}
    monkeypatch.setattr(pilot, "run", fake)
    got = pilot.targeted_pytest()
    assert [x["name"] for x in got] == ["pytest_targeted_1", "pytest_targeted_2"]
    assert "--collect-only" in seen[0] and "--maxfail=1" in seen[1]


def test_negative_targeted_pytest_records_first_red(monkeypatch):
    monkeypatch.setattr(pilot, "run", lambda cmd: {"status": "FAIL"})
    assert [x["status"] for x in pilot.targeted_pytest()] == ["FAIL", "FAIL"]


def test_positive_coverage_floor_not_lowered(monkeypatch, tmp_path):
    monkeypatch.setattr(pilot, "ROOT", tmp_path)
    called = []
    def fake(cmd, **kw):
        called.append((cmd, kw))
        return {"status": "PASS"}
    monkeypatch.setattr(pilot, "run", fake)
    result = pilot.coverage_check(84.5)
    assert "--cov-fail-under=84.5" in called[0][0]
    assert called[0][1]["cwd"] == tmp_path / "DMAIC_V3"
    assert result["coverage_floor_pct"] == 84.5


@pytest.mark.parametrize("mode,parity,outcome", [
    ("fast", False, ("PARTIAL", 0)),
    ("full", False, ("PARTIAL", 0)),
    ("fast", True, ("FAIL", 1)),
    ("gate", False, ("FAIL", 1)),
])
def test_reverse_skips_cannot_inflate_gate_success(mode, parity, outcome):
    assert pilot.receipt_outcome([{"status": "SKIP"}], mode, parity=parity) == outcome


def test_force_trip_unknown_status_is_never_green():
    assert pilot.receipt_outcome([{"status": "NOT_RUN"}], "gate") == ("FAIL", 1)


def test_force_trip_explicit_failure_dominates_skips():
    assert pilot.receipt_outcome([{"status": "SKIP"}, {"status": "FAIL"}], "fast") == ("FAIL", 1)


def test_positive_source_sha_from_git_only(monkeypatch):
    monkeypatch.setattr(pilot, "git_lines", lambda *args: ["a" * 40])
    assert pilot.source_sha() == "a" * 40


def test_negative_source_sha_absent_stays_unknown(monkeypatch):
    monkeypatch.setattr(pilot, "git_lines", lambda *args: [])
    assert pilot.source_sha() is None


def test_positive_main_fast_verified_receipt(monkeypatch, tmp_path):
    receipt_path = _main_receipt(monkeypatch, tmp_path, "--mode", "fast")
    assert pilot.main() == 0
    a = json.loads(receipt_path.read_text())
    assert a["mode"] == "fast" and a["status"] == "PASS"
    assert a["failure_count"] == 0 and a["unverified_check_count"] == 0
    assert a["source_sha"] == "a" * 40


def test_negative_main_full_preserves_failed_coverage(monkeypatch, tmp_path):
    receipt_path = _main_receipt(monkeypatch, tmp_path, "--mode", "full")
    monkeypatch.setattr(pilot, "coverage_check", lambda floor: {"status": "FAIL", "coverage_floor_pct": floor})
    assert pilot.main() == 1
    a = json.loads(receipt_path.read_text())
    assert a["status"] == "FAIL" and a["failure_count"] == 1
    assert a["checks"][-1]["coverage_floor_pct"] == 25.0


def test_reverse_main_gate_floor_minimum_preserved(monkeypatch, tmp_path):
    receipt_path = _main_receipt(monkeypatch, tmp_path, "--mode", "gate")
    monkeypatch.setattr(pilot, "coverage_check", lambda floor: {"status": "PASS", "coverage_floor_pct": floor})
    assert pilot.main() == 0
    assert json.loads(receipt_path.read_text())["checks"][-1]["coverage_floor_pct"] == 75.0


def test_force_trip_main_gate_unknown_check_fails_closed(monkeypatch, tmp_path):
    receipt_path = _main_receipt(monkeypatch, tmp_path, "--mode", "gate", outcomes=[{"status": "UNKNOWN"}])
    monkeypatch.setattr(pilot, "coverage_check", lambda floor: {"status": "PASS", "coverage_floor_pct": floor})
    assert pilot.main() == 1
    assert json.loads(receipt_path.read_text())["unverified_check_count"] == 1


def test_negative_main_parity_skipped_ruff_is_blocking(monkeypatch, tmp_path):
    receipt_path = _main_receipt(monkeypatch, tmp_path, "--mode", "fast", "--parity")
    monkeypatch.setattr(pilot, "ruff_check", lambda files, fix: {"status": "SKIP"})
    assert pilot.main() == 1
    assert json.loads(receipt_path.read_text())["status"] == "FAIL"


def test_reverse_main_nonparity_skipped_ruff_partial(monkeypatch, tmp_path):
    receipt_path = _main_receipt(monkeypatch, tmp_path, "--mode", "fast")
    monkeypatch.setattr(pilot, "ruff_check", lambda files, fix: {"status": "SKIP"})
    assert pilot.main() == 0
    assert json.loads(receipt_path.read_text())["status"] == "PARTIAL"


@pytest.mark.parametrize("floor", ["nan", "-1", "101", "74.9"])
def test_force_trip_main_rejects_invalid_gate_floor(monkeypatch, tmp_path, floor):
    _main_receipt(monkeypatch, tmp_path, "--mode", "gate", "--coverage-floor", floor)
    with pytest.raises(SystemExit) as exc:
        pilot.main()
    assert exc.value.code == 2


def test_negative_empty_check_list_requires_failure():
    # Regression target: zero checks must not be represented as a green gate.
    assert pilot.receipt_outcome([], "gate") == ("FAIL", 1)
