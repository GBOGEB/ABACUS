"""P41-L4: exercise execution-tracker source with isolated file/process outcomes."""

from pathlib import Path
from types import SimpleNamespace

from DMAIC_V3.generators.execution_tracker import (
    ErrorType, ExecutionStatus, ExecutionTracker,
)


def test_real_python_execution_success_and_metadata(tmp_path, monkeypatch):
    tracker = ExecutionTracker(tmp_path / "reports")
    target = tmp_path / "source.py"
    target.write_text("import os\nclass Demo: pass\ndef run(): return 1\n", encoding="utf-8")
    calls = []

    def fake_run(argv, **kw):
        calls.append((argv, kw))
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("DMAIC_V3.generators.execution_tracker.subprocess.run", fake_run)
    result = tracker.execute_python_file(target)
    assert result.status is ExecutionStatus.SUCCESS
    assert result.functions_count == 1
    assert result.classes_count == 1
    assert result.imports_count == 1
    assert calls[0][0][-1] == str(target)
    assert calls[0][1]["cwd"] == target.parent


def test_real_python_execution_nonzero_classification(tmp_path, monkeypatch):
    tracker = ExecutionTracker(tmp_path / "reports")
    target = tmp_path / "broken.py"
    target.write_text("print('hello')\n", encoding="utf-8")
    monkeypatch.setattr(
        "DMAIC_V3.generators.execution_tracker.subprocess.run",
        lambda *a, **kw: SimpleNamespace(
            returncode=2, stdout="", stderr="ModuleNotFoundError: missing",
        ),
    )
    result = tracker.execute_python_file(target)
    assert result.status is ExecutionStatus.FAILED
    assert result.error_type is ErrorType.IMPORT_ERROR
    assert result.exit_code == 2


def test_real_python_execution_syntax_error_does_not_launch(tmp_path, monkeypatch):
    tracker = ExecutionTracker(tmp_path / "reports")
    target = tmp_path / "syntax.py"
    target.write_text("def invalid(:\n", encoding="utf-8")
    def denied(*a, **kw):
        raise AssertionError("must not execute malformed source")
    monkeypatch.setattr(
        "DMAIC_V3.generators.execution_tracker.subprocess.run", denied,
    )
    result = tracker.execute_python_file(target)
    assert result.status is ExecutionStatus.FAILED
    assert result.error_type is ErrorType.SYNTAX_ERROR


def test_vba_mismatch_and_missing_file_are_isolated(tmp_path):
    tracker = ExecutionTracker(tmp_path / "reports")
    target = tmp_path / "bad.bas"
    target.write_text("Public Sub Demo()\nEnd Sub\nEnd Sub\n", encoding="utf-8")
    result = tracker.validate_vba_file(target)
    assert result.status is ExecutionStatus.FAILED
    assert result.error_type is ErrorType.VBA_SYNTAX_ERROR

    missing = tracker.validate_vba_file(tmp_path / "absent.bas")
    assert missing.status is ExecutionStatus.FAILED
    assert missing.error_type is ErrorType.VBA_VALIDATION_ERROR
