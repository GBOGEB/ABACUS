"""W53 BD/LDAB: source-owned positive and adversarial generator tests.

No real subprocess execution or repository-wide reconciliation is permitted.
Every write is confined to temporary workspaces with source identity intact.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _source(relative: str):
    name = "w53_bd_" + relative.replace("/", "_").replace(".", "_")
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _master():
    return _source("DMAIC_V3/generators/master_reconciliation.py")


def _pipeline():
    return _source("DMAIC_V3/generators/test_integration_pipeline.py")


def test_reconciliation_unicode_repair_is_scoped_to_temp_source(tmp_path):
    mod = _master()
    system = mod.MasterReconciliationSystem(tmp_path)
    system.master_doc_dir.mkdir()
    script = system.master_doc_dir / "fixture.py"
    script.write_text('message = "→"\n', encoding="utf-8")
    assert system.fix_python_unicode_errors() == 1
    assert script.read_text(encoding="utf-8") == 'message = "->"\n'
    assert system.fix_python_unicode_errors() == 0
    assert any("Fixed 1/1" in line for line in system.reconciliation_log)


def test_reconciliation_dmaic_baselines_are_explicitly_incomplete(tmp_path):
    mod = _master()
    system = mod.MasterReconciliationSystem(tmp_path)
    metrics = system.generate_dmaic_metrics_per_phase()
    assert set(metrics) == {"DEFINE", "MEASURE", "ANALYZE", "IMPROVE", "CONTROL"}
    assert metrics["DEFINE"]["phase_number"] == 0
    summaries = list(tmp_path.rglob("DMAIC_SUMMARY_*.json"))
    assert len(summaries) == 1
    saved = json.loads(summaries[0].read_text(encoding="utf-8"))
    assert saved["overall_status"] == "IN_PROGRESS"
    assert saved["completion_percentage"] == 0.0
    assert saved["phases"]["DEFINE"]["phase_number"] == 0


def test_reconciliation_orchestration_invokes_every_stage_once(tmp_path):
    mod = _master()
    system = mod.MasterReconciliationSystem(tmp_path)
    names = [
        "fix_python_unicode_errors",
        "generate_dmaic_metrics_per_phase",
        "reconcile_markdown_files",
        "create_markdown_as_code",
        "create_index_and_helpers",
        "update_victory_conditions",
        "generate_final_report",
    ]
    calls = []
    for name in names:
        setattr(system, name, lambda label=name: calls.append(label))
    system.run_full_reconciliation()
    assert calls == names
    assert any("RECONCILIATION COMPLETE" in msg for msg in system.reconciliation_log)


def test_pipeline_no_source_execution_without_mocked_runner(tmp_path):
    mod = _pipeline()
    system = mod.IntegrationPipelineTest(tmp_path)
    script = tmp_path / "safe.py"
    script.write_text("raise RuntimeError('not executed')\n", encoding="utf-8")
    with patch.object(
        mod.subprocess,
        "run",
        return_value=SimpleNamespace(returncode=0, stdout="checked\n", stderr=""),
    ) as called:
        report = system.test_top_level_script(script)
    assert called.call_count == 1
    assert report["status"] == "SUCCESS"
    assert report["exit_code"] == 0
    assert report["stdout_lines"] == 2
    assert report["io_validated"] is False


def test_pipeline_nonzero_exit_and_runner_exception_never_pass(tmp_path):
    mod = _pipeline()
    system = mod.IntegrationPipelineTest(tmp_path)
    script = tmp_path / "safe.py"
    script.write_text("pass\n", encoding="utf-8")
    with patch.object(
        mod.subprocess,
        "run",
        return_value=SimpleNamespace(
            returncode=12,
            stdout="",
            stderr="invalid",
        ),
    ):
        failed = system.test_top_level_script(script)
    assert failed["status"] == "FAILED"
    assert failed["exit_code"] == 12
    with patch.object(mod.subprocess, "run", side_effect=OSError("offline")):
        error = system.test_top_level_script(script)
    assert error["status"] == "ERROR"
    assert "offline" in error["error"]


def test_pipeline_core_partial_stdout_counters_fail_closed(tmp_path):
    mod = _pipeline()
    system = mod.IntegrationPipelineTest(tmp_path)
    source = tmp_path / "core" / "input_manager.py"
    source.parent.mkdir()
    source.write_text("pass\n", encoding="utf-8")
    stdout = "TESTS_RUN:4\nTESTS_PASSED:3\nIO_OPERATIONS:2\n"
    with patch.object(
        mod.subprocess,
        "run",
        return_value=SimpleNamespace(returncode=0, stdout=stdout, stderr=""),
    ):
        report = system.test_core_module_with_io(source)
    assert report["status"] == "FAILED"
    assert (report["tests_run"], report["tests_passed"]) == (4, 3)
    assert report["io_operations"] == 2
    assert report["io_validated"] is True


def test_pipeline_core_all_stdout_counters_pass(tmp_path):
    mod = _pipeline()
    system = mod.IntegrationPipelineTest(tmp_path)
    source = tmp_path / "core" / "input_manager.py"
    source.parent.mkdir()
    source.write_text("pass\n", encoding="utf-8")
    with patch.object(
        mod.subprocess,
        "run",
        return_value=SimpleNamespace(
            returncode=0,
            stdout="TESTS_RUN:4\nTESTS_PASSED:4\nIO_OPERATIONS:2\n",
            stderr="",
        ),
    ):
        report = system.test_core_module_with_io(source)
    assert report["status"] == "SUCCESS"


def test_pipeline_invalid_telemetry_is_not_promoted_to_success(tmp_path):
    mod = _pipeline()
    system = mod.IntegrationPipelineTest(tmp_path)
    source = tmp_path / "core" / "dmaic_manager.py"
    source.parent.mkdir()
    source.write_text("pass\n", encoding="utf-8")
    with patch.object(
        mod.subprocess,
        "run",
        return_value=SimpleNamespace(
            returncode=0,
            stdout="TESTS_RUN:not-a-number",
            stderr="",
        ),
    ):
        bad = system.test_core_module_with_io(source)
    assert bad["status"] == "ERROR"
    with pytest.raises(ValueError):
        system._parse_test_output("TESTS_RUN:not-a-number")


def test_pipeline_report_and_cleanup_are_restricted_to_owned_paths(tmp_path):
    mod = _pipeline()
    system = mod.IntegrationPipelineTest(tmp_path)
    system.results = [
        {
            "status": "SUCCESS",
            "io_validated": True,
            "tests_run": 2,
            "tests_passed": 2,
            "io_operations": 1,
        },
        {
            "status": "FAILED",
            "io_validated": False,
            "tests_run": 1,
            "tests_passed": 0,
            "io_operations": 0,
        },
    ]
    system.save_report()
    reports = list((tmp_path / "output").rglob("integration_pipeline_report_*.json"))
    assert len(reports) == 1
    stats = json.loads(reports[0].read_text(encoding="utf-8"))["summary"]
    assert stats["total_files"] == 2
    assert stats["successful"] == 1
    assert stats["ci_cd_ready"] is False
    owned = tmp_path / "owned-to-clean"
    owned.mkdir()
    system.temp_dirs = [owned]
    system.cleanup()
    assert not owned.exists()
    assert reports[0].exists()


def test_pipeline_outputs_only_include_files_created_during_script(tmp_path):
    mod = _pipeline()
    system = mod.IntegrationPipelineTest(tmp_path)
    system.master_doc_dir.mkdir()
    started_at = time.time()
    unrelated = system.master_doc_dir / "unrelated-fresh.json"
    unrelated.write_text("{}", encoding="utf-8")
    os.utime(unrelated, (started_at - 1, started_at - 1))
    generated = system.master_doc_dir / "script-output.json"
    generated.write_text("{}", encoding="utf-8")
    os.utime(generated, (started_at + 1, started_at + 1))
    output = system._check_output_files(started_at)
    assert "script-output.json" in output
    assert "unrelated-fresh.json" not in output
