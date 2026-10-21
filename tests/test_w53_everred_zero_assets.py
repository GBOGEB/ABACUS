"""W53 EVERRED: fail-closed recovery and negative-path tests for four zero files.

Every subprocess is mocked, file mutation is restricted to pytest tmp_path,
and engineering/reporting fixtures carry no release or QPS acceptance authority.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _source(relative: str):
    name = "w53_red_" + relative.replace("/", "_").replace(".", "_")
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _dow():
    return _source("DMAIC_V3/dow_integration_executor.py")


def _runner():
    return _source("DMAIC_V3/generators/test_real_execution.py")


def _package():
    return _source("rextools/populate_package.py")


def _books():
    return _source("DMAIC_V3/validate_canonical_books.py")


def test_dow_fails_on_missing_target_without_creating_receipt(tmp_path):
    mod = _dow()
    executor = mod.DOWIntegrationExecutor()
    result = executor.execute_pipeline(1, str(tmp_path / "absent"))
    assert result["status"] == "error"
    assert result["error"] == "Target directory not found"
    assert executor.results == []


def test_dow_first_failed_required_stage_stops_six_stage_pipeline(tmp_path):
    mod = _dow()
    executor = mod.DOWIntegrationExecutor()
    with patch.object(
        executor,
        "_run_agent",
        return_value={"status": "error", "error": "forced-red"},
    ) as agent:
        result = executor.execute_pipeline(1, str(tmp_path))
    assert result["status"] == "error"
    assert result["stage"] == 1
    assert result["reason"] == "forced-red"
    assert len(result["results"]) == 1
    assert agent.call_count == 1
    assert "1/6" in result["summary"]


def test_dow_all_six_successes_are_distinct_and_positive(tmp_path):
    mod = _dow()
    executor = mod.DOWIntegrationExecutor()
    success = {"status": "success", "output": "synthetic"}
    with (
        patch.object(
            executor, "_run_agent", side_effect=lambda *args: success.copy()
        ),
        patch.object(
            executor, "_run_ranking", side_effect=lambda *args: success.copy()
        ),
        patch.object(
            executor, "_run_validation", side_effect=lambda *args: success.copy()
        ),
    ):
        result = executor.execute_pipeline(1, str(tmp_path))
    assert result["status"] == "success"
    assert result["required_stages"] == result["successful_stages"] == 6
    assert [row["stage"] for row in result["results"]] == list(range(1, 7))
    assert "[OK] Successful: 6" in result["summary"]


def test_dow_missing_and_stub_ranking_are_never_success(tmp_path, monkeypatch):
    mod = _dow()
    monkeypatch.chdir(tmp_path)
    executor = mod.DOWIntegrationExecutor()
    missing = executor._run_ranking("unused")
    assert missing["status"] == "blocked_missing_parent_mechanic"
    path = (
        tmp_path
        / "DMAIC_V3"
        / "local_mcp"
        / "agents"
        / "recursive_self_ranking_v2.3_OPTIMIZED.py"
    )
    path.parent.mkdir(parents=True)
    path.write_text("# 0.0.0-stub\n", encoding="utf-8")
    stub = executor._run_ranking("unused")
    assert stub["status"] == "blocked_stub_parent_mechanic"
    assert stub["agent"] == "recursive_self_ranking"


def test_dow_missing_validation_and_missing_agent_fail_closed(tmp_path, monkeypatch):
    mod = _dow()
    monkeypatch.chdir(tmp_path)
    executor = mod.DOWIntegrationExecutor()
    assert executor._run_validation("unused")["status"].startswith("blocked_")
    assert executor._run_agent("unavailable", [])["status"].startswith("blocked_")


@pytest.mark.parametrize(
    ("mode", "status", "code"),
    [("good", "success", None), ("exit7", "error", 7), ("timeout", "error", None)],
)
def test_dow_script_runtime_typed_positive_and_terminal_negative(
    tmp_path, mode, status, code
):
    mod = _dow()
    executor = mod.DOWIntegrationExecutor()
    target = tmp_path / "agent.py"
    target.write_text("print('fixture')\n", encoding="utf-8")
    if mode == "timeout":
        response = mod.subprocess.TimeoutExpired("fake-cmd", 2)
    else:
        rc = 0 if mode == "good" else 7
        response = SimpleNamespace(
            returncode=rc, stdout="fixture\n", stderr="terminal failure"
        )
    with patch.object(
        mod.subprocess,
        "run",
        side_effect=response if mode == "timeout" else None,
        return_value=None if mode == "timeout" else response,
    ) as runner:
        result = executor._run_script("synthetic", target, [], timeout=2)
    assert runner.call_count == 1
    assert result["status"] == status
    if code is not None:
        assert result["return_code"] == code
    if mode == "timeout":
        assert result["error"] == "Timeout"


@pytest.mark.parametrize(
    ("mode", "expected_status"),
    [("ok", "SUCCESS"), ("failure", "FAILED"), ("timeout", "TIMEOUT")],
)
def test_real_execution_never_runs_untrusted_python_code(
    tmp_path, mode, expected_status
):
    mod = _runner()
    target = tmp_path / "test.py"
    target.write_text("raise RuntimeError('would execute')\n", encoding="utf-8")
    if mode == "timeout":
        effect = mod.subprocess.TimeoutExpired("python", 60)
        value = None
    else:
        effect = None
        value = SimpleNamespace(
            returncode=0 if mode == "ok" else 7,
            stdout="receipt",
            stderr="" if mode == "ok" else "deliberate error",
        )
    with patch.object(mod.subprocess, "run", side_effect=effect, return_value=value):
        result = mod.run_python_file(target, tmp_path)
    assert result["status"] == expected_status
    assert result["file_path"] == "test.py"
    if mode == "timeout":
        assert result["exit_code"] == -1
    elif mode == "failure":
        assert result["exit_code"] == 7
        assert result["error"] == "deliberate error"


def test_real_execution_unexpected_runner_exception_is_visible(tmp_path):
    mod = _runner()
    target = tmp_path / "safe.py"
    target.write_text("pass\n", encoding="utf-8")
    with patch.object(
        mod.subprocess, "run", side_effect=OSError("no runner")
    ):
        result = mod.run_python_file(target, tmp_path)
    assert result["status"] == "ERROR"
    assert result["exit_code"] == -1
    assert "no runner" in result["error"]


def _status(verdict):
    return {
        "verdict": verdict,
        "n_open_gates": 1 if verdict == "ISSUE_RFI" else 0,
        "energy_model": "UNVERIFIED_SYNTHETIC",
        "open_gates": (
            [{"id": "TEST-GATE"}] if verdict == "ISSUE_RFI" else []
        ),
    }


def test_package_headers_distinguish_rfi_and_ready_without_promotion():
    mod = _package()
    pending = mod._status_block(_status("ISSUE_RFI"))
    assert "DRAFT-GATED" in pending and "TEST-GATE" in pending
    ready = mod._status_block(_status("PROCEED_MDA"))
    assert "READY FOR MDA" in ready
    assert mod._divider("APPENDIX") == "\n---\n\n## APPENDIX\n\n"


def test_package_assembly_uses_only_local_trusted_fixture_files(
    tmp_path, monkeypatch
):
    mod = _package()
    source = tmp_path / "skeleton.md"
    gen = tmp_path / "generated"
    gen.mkdir()
    source.write_text("# Source document\n", encoding="utf-8")
    (gen / "t_available_grid.md").write_text("grid", encoding="utf-8")
    (gen / "applicant_rfi.md").write_text("rfi", encoding="utf-8")
    monkeypatch.setattr(mod, "SKELETON", source)
    monkeypatch.setattr(mod, "GEN", gen)
    assembled = mod.assemble(_status("ISSUE_RFI"))
    assert "# Source document" in assembled
    assert "grid" in assembled and "rfi" in assembled
    assert "DRAFT-GATED" in assembled
    (gen / "applicant_rfi.md").unlink()
    with pytest.raises(FileNotFoundError):
        mod.assemble(_status("ISSUE_RFI"))


def test_canonical_books_invalid_registry_and_missing_books_record_failures(
    tmp_path, monkeypatch
):
    mod = _books()
    monkeypatch.chdir(tmp_path)
    folder = tmp_path / "CANONICAL_KNOWLEDGE"
    folder.mkdir()
    validator = mod.CanonicalBooksValidator(folder)
    validator._test_books_exist()
    assert validator.results["tests_failed"] > 0
    registry = folder / "document_registry.json"
    registry.write_text("not-json", encoding="utf-8")
    validator._test_document_registry()
    assert any(
        "Document registry parsing" in row["test"]
        for row in validator.results["validations"]
    )


def test_canonical_books_positive_phases_and_registry(tmp_path, monkeypatch):
    mod = _books()
    monkeypatch.chdir(tmp_path)
    folder = tmp_path / "CANONICAL_KNOWLEDGE"
    dmaic = folder / "DMAIC"
    dmaic.mkdir(parents=True)
    (dmaic / "DMAIC_BOOK_1.md").write_text(
        "# Define, Measure, Analyze, Improve, Control\n",
        encoding="utf-8",
    )
    (folder / "document_registry.json").write_text(
        '{"documents": [], "version_history": []}',
        encoding="utf-8",
    )
    validator = mod.CanonicalBooksValidator(folder)
    validator._test_dmaic_references()
    validator._test_document_registry()
    assert validator.results["tests_passed"] == 2
    validator._generate_report()
    saved = json.loads(
        (folder / "VALIDATION_REPORT.json").read_text(encoding="utf-8")
    )
    assert saved["tests_run"] == 2
    assert saved["tests_failed"] == 0
