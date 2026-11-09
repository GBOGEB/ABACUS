"""W52: observable positive/negative behavior for two zero-covered executors.

Only temporary workspaces and injected engines are used; mock QPS measurements
must never be mistaken for engineering or deployment evidence.
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


def _load(relative: str):
    name = "w52_execution_" + relative.replace("/", "_").replace(".", "_")
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {relative}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    # quick_output_analysis.py prepends to sys.path at import; isolate that.
    with patch.object(sys, "path", list(sys.path)):
        spec.loader.exec_module(module)
    return module


def _postdeploy():
    module = _load("DMAIC_V3/orchestrators/dmaic_postdeploy.py")
    instance = object.__new__(module.PostDeployOrchestrator)
    instance.steps = []
    instance.dow_engine = None
    instance.keb_engine = None
    return instance


def test_quick_output_missing_directory_returns_typed_error(tmp_path):
    module = _load("DMAIC_V3/quick_output_analysis.py")
    missing = module.analyze_iteration(tmp_path / "absent")
    assert missing["error"] == "Directory not found"
    assert missing["total_files"] == 0


def test_quick_output_counts_nested_bytes_without_root_file_false_count(tmp_path):
    module = _load("DMAIC_V3/quick_output_analysis.py")
    root = tmp_path / "iteration_1"
    (root / "measure" / "nested").mkdir(parents=True)
    (root / "analyze").mkdir()
    (root / "measure" / "nested" / "receipt.json").write_bytes(b"proof")
    (root / "analyze" / "metrics.json").write_bytes(b"123456")
    (root / "ignored-root.txt").write_bytes(b"not a phase")
    result = module.analyze_iteration(root)
    assert result["total_files"] == 2
    assert result["total_size_bytes"] == 11
    assert set(result["phases"]) == {"analyze", "measure"}
    assert result["phases"]["measure"]["file_count"] == 1
    assert result["phases"]["analyze"]["file_count"] == 1


def test_quick_output_json_load_positive_and_corrupt_file(tmp_path):
    module = _load("DMAIC_V3/quick_output_analysis.py")
    path = tmp_path / "state.json"
    path.write_text('{"phase": "measure"}', encoding="utf-8")
    assert module.load_json_file(path) == {"phase": "measure"}
    path.write_text("{corrupt", encoding="utf-8")
    assert "error" in module.load_json_file(path)
    assert "error" in module.load_json_file(tmp_path / "missing.json")


def test_quick_output_entrypoint_missing_and_complete_fixture(
    tmp_path, monkeypatch, capsys
):
    module = _load("DMAIC_V3/quick_output_analysis.py")
    monkeypatch.chdir(tmp_path)
    assert module.main() == 1
    assert "not found" in capsys.readouterr().out

    output = tmp_path / "DMAIC_V3_OUTPUT"
    measure = output / "iteration_1" / "measure"
    measure.mkdir(parents=True)
    (measure / "result.json").write_text("{}", encoding="utf-8")
    (output / "agent_registry.json").write_text(
        json.dumps({"version": "fixture", "agents": {"a": {"category": "analysis"}}}),
        encoding="utf-8",
    )
    (measure.parent / "orchestration_statistics.json").write_text(
        json.dumps(
            {
                "orchestration": {
                    "total_phases": 1,
                    "successful_phases": 1,
                    "failed_phases": 0,
                    "total_duration_seconds": 0.1,
                }
            }
        ),
        encoding="utf-8",
    )
    assert module.main() == 0
    output_text = capsys.readouterr().out
    assert "Found 1 iterations" in output_text
    assert "AGENT REGISTRY" in output_text
    assert "STATISTICS" in output_text


def test_postdeploy_fallback_ingestion_and_incremental_accounting(tmp_path):
    runner = _postdeploy()
    standard = runner.ingest_workspace(tmp_path, incremental=False)
    assert standard["status"] == "success"
    assert standard["metrics_summary"]["total_documents"] == 6
    assert standard["metrics_summary"]["total_qplant_cases"] == 2
    assert standard["metrics_summary"]["knowledge_entries"] == 15
    assert standard["ingestion_steps"]["dashboard_links"]["links_generated"] == 6
    assert standard["total_duration"] >= 0
    assert "new_files" not in standard

    incremental = runner.ingest_workspace(tmp_path, incremental=True)
    assert incremental["is_incremental"] is True
    assert incremental["documents_indexed"] == len(incremental["new_files"]) == 2
    assert incremental["total_documents"] == 6


def test_postdeploy_injected_engines_use_bounded_contracts(tmp_path):
    runner = _postdeploy()
    runner.dow_engine = SimpleNamespace(
        classify_documents=lambda path: {"total_documents": 3}
    )
    runner.keb_engine = SimpleNamespace(
        extract_metrics=lambda path: {
            "qplant_cases_processed": 1,
            "cryo_metrics": {"synthetic_case": {"status": "fixture"}},
        }
    )
    result = runner.ingest_workspace(tmp_path)
    assert result["ingestion_steps"]["dow_classification"]["documents_classified"] == 3
    assert result["ingestion_steps"]["keb_metrics_extraction"]["cases_processed"] == 1
    assert result["ingestion_steps"]["keb_metrics_extraction"]["metrics_extracted"] == 2
    assert result["metrics_summary"]["total_documents"] == 3


def test_postdeploy_raised_engine_error_is_not_reported_as_success(tmp_path):
    runner = _postdeploy()

    def failing_engine(path):
        raise RuntimeError("injected E2E failure")

    runner.dow_engine = SimpleNamespace(classify_documents=failing_engine)
    with pytest.raises(RuntimeError, match="injected E2E failure"):
        runner.ingest_workspace(tmp_path)
