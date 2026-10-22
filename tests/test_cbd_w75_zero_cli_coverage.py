"""CBD W75: second disjoint zero-covered cohort with genuine CLI behavior.

Exact baseline 7e9564f955dc00de23a7fba446d776e076758a8e.
No real DOW/CD/engineering deployment or private source may be touched:
all CLI output is scoped to tmp_path and unknown values stay unknown.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import types
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(relative):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(
        "cbd_w75_" + "_".join(path.with_suffix("").relative_to(ROOT).parts), path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dow_structure_complete_partial_invalid_and_missing(tmp_path):
    m = load("DMAIC_V3/validate_dow_structure.py")
    full = tmp_path / "valid.json"
    full.write_text(
        json.dumps(
            {
                "metadata": {},
                "recursive_hooks": [],
                "convergence_metrics": {},
                "knowledge_gain": {},
            }
        )
    )
    good, checks = m.validate_dow_structure(full)
    assert good and len(checks) == 4 and all(checks.values())
    full.write_text(json.dumps({"metadata": {}}))
    good, checks = m.validate_dow_structure(full)
    assert good is False and checks["metadata"] is True
    assert checks["recursive_hooks"] is False
    full.write_text("{ broken", encoding="utf-8")
    assert m.validate_dow_structure(full) == (False, {})
    assert m.validate_dow_structure(tmp_path / "nonexistent.json") == (False, {})


@pytest.mark.parametrize(
    "cohort,exit_code",
    [
        ("missing", 1),
        ("empty", 1),
        ("all_good", 0),
        ("mixed", 1),
    ],
)
def test_dow_structure_cli_exit_codes(tmp_path, monkeypatch, cohort, exit_code, capsys):
    m = load("DMAIC_V3/validate_dow_structure.py")
    target = tmp_path / "native"
    if cohort != "missing":
        target.mkdir()
    if cohort in {"all_good", "mixed"}:
        (target / "good.json").write_text(
            json.dumps(
                {
                    "metadata": {},
                    "recursive_hooks": {},
                    "convergence_metrics": {},
                    "knowledge_gain": {},
                }
            )
        )
    if cohort == "mixed":
        (target / "bad.json").write_text("{}")
    monkeypatch.setattr(sys, "argv", ["validate_dow_structure.py", str(target)])
    with pytest.raises(SystemExit) as stopped:
        m.main()
    assert stopped.value.code == exit_code
    assert "DOW STRUCTURE VALIDATION" in capsys.readouterr().out


def test_quick_output_analysis_iteration_and_json_error(tmp_path):
    old = list(sys.path)
    try:
        m = load("DMAIC_V3/quick_output_analysis.py")
    finally:
        sys.path[:] = old
    nonexistent = tmp_path / "missing"
    assert m.analyze_iteration(nonexistent)["error"] == "Directory not found"
    phase = tmp_path / "iteration_01" / "phase_a"
    phase.mkdir(parents=True)
    (phase / "report.json").write_text("{}")
    (tmp_path / "iteration_01" / "irrelevant.txt").write_text("ignored")
    r = m.analyze_iteration(phase.parent)
    assert r["total_files"] == 1 and r["total_size_bytes"] == 2
    assert r["phases"]["phase_a"]["file_count"] == 1
    good = phase / "report.json"
    assert m.load_json_file(good) == {}
    good.write_text("{oops")
    assert "error" in m.load_json_file(good)
    assert "error" in m.load_json_file(tmp_path / "none")


def test_quick_output_cli_empty_and_populated(tmp_path, monkeypatch, capsys):
    old = list(sys.path)
    try:
        m = load("DMAIC_V3/quick_output_analysis.py")
    finally:
        sys.path[:] = old
    monkeypatch.chdir(tmp_path)
    assert m.main() == 1
    root = tmp_path / "DMAIC_V3_OUTPUT"
    phase = root / "iteration_1" / "phaseA"
    phase.mkdir(parents=True)
    (phase / "note.txt").write_text("source safe")
    (root / "agent_registry.json").write_text(
        json.dumps(
            {"version": "test", "agents": {"a": {"category": "core", "name": "A"}}}
        )
    )
    (root / "iteration_1" / "orchestration_statistics.json").write_text(
        json.dumps(
            {
                "orchestration": {
                    "total_phases": 2,
                    "successful_phases": 2,
                    "failed_phases": 0,
                    "total_duration_seconds": 1.2,
                }
            }
        )
    )
    assert m.main() == 0
    assert "STATISTICS" in capsys.readouterr().out


def test_deployment_dashboard_and_cli_are_non_destructive(
    tmp_path, monkeypatch, capsys
):
    m = load("DOW_DEPLOYMENT_ORCHESTRATOR.py")
    testdir = tmp_path / "DMAIC_V3" / "tests"
    testdir.mkdir(parents=True)
    (testdir / "test_synthetic.py").write_text("# synthetic")
    agentdir = tmp_path / "local_mcp" / "agents"
    agentdir.mkdir(parents=True)
    (agentdir / "dow_synthetic.py").write_text("# synthetic")
    with (
        mock.patch.object(m, "__file__", str(tmp_path / "runner.py")),
        mock.patch.object(m, "LOG_DIR", tmp_path / "dashboard_output"),
    ):
        assert m.generate_dashboard() == 0
        receipt = json.loads((m.LOG_DIR / "latest.json").read_text())
        assert receipt["components"]["dmaic_test_files"] == 1
        assert receipt["components"]["dow_agents"] == 1
        assert (m.LOG_DIR / "dashboard.md").exists()
        monkeypatch.setattr(sys, "argv", ["runner.py"])
        assert m.main() == 0  # Help does not trigger any additional write.
        monkeypatch.setattr(sys, "argv", ["runner.py", "--dashboard"])
        assert m.main() == 0
    assert "Dashboard generated" in capsys.readouterr().out


def test_qplant_compat_exports_and_provider_missing():
    m = load("qplant_presentation_engine/__init__.py")
    provider = types.SimpleNamespace(render=lambda: "OK")
    with mock.patch.object(m, "import_module", return_value=provider) as loader:
        assert m.__getattr__("render")() == "OK"
        assert "render" in m.__dir__()
        loader.assert_called_with("src.qplant_presentation_engine")
    with mock.patch.object(m, "import_module", side_effect=ModuleNotFoundError):
        with pytest.raises(ModuleNotFoundError):
            m.__getattr__("unknown")


@pytest.mark.parametrize("path", ["core/keb/__init__.py", "core/keb/keb.py"])
def test_legacy_keb_compat_is_alias_only_and_no_execution(path):
    fake = types.ModuleType("core.execution_backbone")
    sentinel = type("SyntheticBackbone", (), {})
    fake.ExecutionBackbone = sentinel
    with mock.patch.dict(sys.modules, {"core.execution_backbone": fake}):
        m = load(path)
    assert m.ExecutionBackbone is sentinel
    assert m.LegacyExecutionBackbone is sentinel
    assert m.__all__ == ["ExecutionBackbone", "LegacyExecutionBackbone"]


def load_metrics_collector_safely():
    # Source startup conditionally reconfigures sys.stdout and sets an encoding
    # environment variable: isolate both rather than mutating pytest capture.
    fake_stdout = types.SimpleNamespace()
    with mock.patch.object(sys, "stdout", fake_stdout), mock.patch.dict(os.environ):
        return load("fast_metrics_collector.py")


def test_fast_metrics_empty_cohort_yields_zero_not_division_by_zero(
    tmp_path, monkeypatch
):
    m = load_metrics_collector_safely()
    workspace = tmp_path / "empty"
    workspace.mkdir()
    monkeypatch.chdir(tmp_path)
    a = m.FastMetricsCollector(workspace, output_suffix="empty")
    v = a.collect_fast_metrics()
    assert v["summary"]["total_files"] == 0
    assert v["summary"]["version_header_percentage"] == 0
    assert v["summary"]["estimated_import_issues"] == 0
    assert list(
        (tmp_path / "DMAIC_INTEGRATION_OUTPUT/cicd_github").glob("metrics_empty_*.json")
    )


def test_fast_metrics_duplicate_nonempty_and_version_headers(tmp_path, monkeypatch):
    m = load_metrics_collector_safely()
    workspace = tmp_path / "synthetic"
    workspace.mkdir()
    (workspace / "one.py").write_text("__version__ = '1.0'\n", encoding="utf-8")
    (workspace / "two.py").write_text("__version__ = '1.0'\n", encoding="utf-8")
    (workspace / "three.py").write_text("from ...mod import x\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    v = m.FastMetricsCollector(workspace, output_suffix="seed").collect_fast_metrics()
    assert v["summary"]["total_files"] == 3
    assert v["summary"]["duplicate_groups"] == 1
    assert v["summary"]["duplicate_files"] == 1
    assert v["summary"]["files_with_version_headers"] == 2
    assert v["summary"]["estimated_import_issues"] >= 1
    assert not v["summary"].get("source_authority_promoted", False)
