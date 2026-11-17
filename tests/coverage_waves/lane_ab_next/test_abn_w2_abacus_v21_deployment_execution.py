"""Behaviour tests for abacus_v21_deployment_execution.py."""

import json
import logging
import runpy

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

mod = load("abacus_v21_deployment_execution.py", name="abn_w2_deploy_exec")

TEMPORAL_SRC = (
    "from datetime import datetime\n"
    "class FileMetadata:\n    timestamp = None\n    created_at = None\n"
    "class FolderMetadata:\n    modified_at = None\n"
    "class ExecutionMetadata:\n    pass\n"
)
DOW_SRC = "ABACUS-UNIFIED\nABACUS-v031\nABACUS-v032\n"


def _populate(root):
    core = root / "DMAIC_V3" / "core"
    core.mkdir(parents=True)
    (core / "recursive_engine.py").write_bytes(b"def recursive():\n    pass\n")
    (core / "temporal_metadata_engine.py").write_bytes(TEMPORAL_SRC.encode())
    (root / "DOW_DEPLOYMENT_ORCHESTRATOR.py").write_bytes(DOW_SRC.encode())
    for version in ("ABACUS-UNIFIED", "ABACUS-v031", "ABACUS-v032"):
        vdir = root / version
        vdir.mkdir()
        (vdir / "a.py").write_bytes(b"x = 1\n")
        (vdir / "README.md").write_bytes(b"# doc\n")
    rec_dir = root / "ABACUS-v032" / "recursive_engine"
    rec_dir.mkdir()
    (rec_dir / "engine.py").write_bytes(b"y = 2\n")
    report_dir = root / "ABACUS_V21_MIGRATION_OUTPUT"
    report_dir.mkdir()
    data = {"phases": {"phase_1": {}, "phase_8": {"readiness_score": 87.5}}}
    (report_dir / "ABACUS_V21_MIGRATION_REPORT.json").write_bytes(
        json.dumps(data).encode()
    )


def test_init_creates_output_dir_and_status(tmp_path):
    dep = mod.ABACUSv21Deployment(tmp_path)
    assert dep.deployment_output == tmp_path / "ABACUS_V21_DEPLOYMENT_OUTPUT"
    assert dep.deployment_output.is_dir()
    assert dep.deployment_status["version"] == "2.1"
    assert dep.deployment_status["deployment_steps"] == {}
    # second construction tolerates the existing dir
    mod.ABACUSv21Deployment(tmp_path)


def test_init_defaults_to_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    dep = mod.ABACUSv21Deployment()
    assert dep.workspace_root == tmp_path
    assert (tmp_path / "ABACUS_V21_DEPLOYMENT_OUTPUT").is_dir()


def test_verify_dow_orchestrator_present_and_missing(tmp_path):
    dep = mod.ABACUSv21Deployment(tmp_path)
    missing = dep._verify_dow_orchestrator()
    assert missing["dow_orchestrator_exists"] is False
    assert "dow_orchestrator_size" not in missing

    (tmp_path / "DOW_DEPLOYMENT_ORCHESTRATOR.py").write_bytes(b"a\nb\nc\n")
    found = dep._verify_dow_orchestrator()
    assert found["dow_orchestrator_exists"] is True
    assert found["dow_orchestrator_size"] == 6
    assert found["dow_orchestrator_lines"] == 3


def test_deploy_versions_mixed(tmp_path):
    (tmp_path / "ABACUS-v031").mkdir()
    (tmp_path / "ABACUS-v031" / "m.py").write_bytes(b"")
    (tmp_path / "ABACUS-v031" / "sub").mkdir()
    (tmp_path / "ABACUS-v031" / "sub" / "n.py").write_bytes(b"")
    dep = mod.ABACUSv21Deployment(tmp_path)
    result = dep._deploy_abacus_versions()
    assert result["versions_deployed"] == ["ABACUS-v031"]
    assert result["deployment_status"]["ABACUS-v031"]["status"] == "deployed"
    assert result["deployment_status"]["ABACUS-v031"]["python_files"] == 2
    assert result["deployment_status"]["ABACUS-UNIFIED"]["status"] == "not_found"
    assert result["deployment_status"]["ABACUS-v032"]["status"] == "not_found"


def test_health_checks_on_empty_workspace(tmp_path):
    dep = mod.ABACUSv21Deployment(tmp_path)
    assert dep._check_recursive_engine_health() == {
        "components_found": 0,
        "components": [],
    }
    temporal = dep._check_temporal_engine_health()
    assert temporal["temporal_engine_found"] is False
    assert "has_datetime" not in temporal
    dow = dep._check_dow_integration_health()
    assert dow["dow_orchestrator_found"] is False
    assert "has_abacus_unified" not in dow
    assert dep._check_knowledge_preservation_health() == {
        "total_artifacts": 0,
        "versions": {},
    }


def test_health_checks_on_populated_workspace(tmp_path):
    _populate(tmp_path)
    dep = mod.ABACUSv21Deployment(tmp_path)
    rec = dep._check_recursive_engine_health()
    assert rec["components_found"] == 2
    temporal = dep._check_temporal_engine_health()
    assert temporal["has_datetime"] is True
    assert temporal["has_timestamp"] is True
    assert temporal["has_metadata_classes"] is True
    dow = dep._check_dow_integration_health()
    assert dow["has_abacus_unified"] is True
    assert dow["has_abacus_v031"] is True
    assert dow["has_abacus_v032"] is True
    know = dep._check_knowledge_preservation_health()
    # v032 holds a.py, README.md and recursive_engine/engine.py
    assert know["versions"]["ABACUS-v032"]["total_artifacts"] == 3
    assert know["versions"]["ABACUS-UNIFIED"] == {
        "python_files": 1,
        "documentation_files": 1,
        "total_artifacts": 2,
    }
    assert know["total_artifacts"] == 7


def test_dow_health_alternate_markers(tmp_path):
    (tmp_path / "DOW_DEPLOYMENT_ORCHESTRATOR.py").write_bytes(b"ABACUS_UNIFIED only")
    dep = mod.ABACUSv21Deployment(tmp_path)
    dow = dep._check_dow_integration_health()
    assert dow["has_abacus_unified"] is True
    assert dow["has_abacus_v031"] is False
    assert dow["has_abacus_v032"] is False


def test_monitor_system_health_records_unhealthy(tmp_path, monkeypatch):
    dep = mod.ABACUSv21Deployment(tmp_path)

    def boom():
        raise RuntimeError("engine offline")

    monkeypatch.setattr(dep, "_check_temporal_engine_health", boom)
    result = dep._monitor_system_health()
    checks = result["health_checks"]
    assert checks["temporal_engine"] == {
        "status": "unhealthy",
        "error": "engine offline",
    }
    assert checks["recursive_engine"]["status"] == "healthy"
    assert checks["dow_integration"]["status"] == "healthy"
    assert dep.deployment_status["health_checks"] is result


def test_validate_production_metrics_with_and_without_report(tmp_path):
    dep = mod.ABACUSv21Deployment(tmp_path)
    missing = dep._validate_production_metrics()
    assert missing["metrics"] == {"migration_completed": False}

    _populate(tmp_path)
    found = dep._validate_production_metrics()
    assert found["metrics"]["migration_completed"] is True
    assert found["metrics"]["deployment_readiness"] == 87.5
    assert found["metrics"]["total_phases"] == 2
    assert dep.deployment_status["production_metrics"] is found


def test_validate_production_metrics_defaults_readiness(tmp_path):
    out = tmp_path / "ABACUS_V21_MIGRATION_OUTPUT"
    out.mkdir()
    (out / "ABACUS_V21_MIGRATION_REPORT.json").write_bytes(b"{}")
    dep = mod.ABACUSv21Deployment(tmp_path)
    metrics = dep._validate_production_metrics()["metrics"]
    assert metrics["deployment_readiness"] == 0
    assert metrics["total_phases"] == 0


def test_monitor_recursive_engine_file_and_dir(tmp_path):
    dep = mod.ABACUSv21Deployment(tmp_path)
    empty = dep._monitor_recursive_engine()
    assert empty["performance_metrics"] == {}

    _populate(tmp_path)
    result = dep._monitor_recursive_engine()
    metrics = result["performance_metrics"]
    file_key = str(tmp_path / "DMAIC_V3" / "core" / "recursive_engine.py")
    dir_key = str(tmp_path / "ABACUS-v032" / "recursive_engine")
    assert metrics[file_key]["has_recursive_logic"] is True
    assert metrics[file_key]["lines"] == 2
    assert metrics[dir_key] == {"python_files": 1, "is_directory": True}
    assert dep.deployment_status["monitoring_results"]["recursive_engine"] is result


def test_validate_temporal_engine(tmp_path):
    dep = mod.ABACUSv21Deployment(tmp_path)
    missing = dep._validate_temporal_engine()
    assert missing["validation_results"] == {}

    _populate(tmp_path)
    result = dep._validate_temporal_engine()["validation_results"]
    assert result["datetime"] == {"count": 2, "validated": True}
    assert result["created_at"]["validated"] is True
    assert result["accessed_at"] == {"count": 0, "validated": False}
    assert result["metadata_classes"] == {
        "FileMetadata": True,
        "FolderMetadata": True,
        "ExecutionMetadata": True,
        "DigitalTwinState": False,
    }


def test_confirm_knowledge_preservation(tmp_path):
    dep = mod.ABACUSv21Deployment(tmp_path)
    empty = dep._confirm_knowledge_preservation()["preservation_status"]
    assert empty == {"total_artifacts": 0, "knowledge_lost": 0}

    _populate(tmp_path)
    status = dep._confirm_knowledge_preservation()["preservation_status"]
    assert status["ABACUS-v031"]["status"] == "preserved"
    assert status["ABACUS-v031"]["total_artifacts"] == 2
    assert status["total_artifacts"] == 7
    assert status["knowledge_lost"] == 0


def test_generate_report_writes_json_and_markdown(tmp_path):
    dep = mod.ABACUSv21Deployment(tmp_path)
    result = dep._generate_deployment_report()
    assert result["report_generated"] is True
    json_path = (
        tmp_path
        / "ABACUS_V21_DEPLOYMENT_OUTPUT"
        / ("ABACUS_V21_DEPLOYMENT_REPORT.json")
    )
    md_path = json_path.with_suffix(".md")
    assert result["report_path"] == str(json_path)
    assert result["markdown_report_path"] == str(md_path)
    assert json.loads(json_path.read_text(encoding="utf-8"))["version"] == "2.1"
    assert md_path.read_text(encoding="utf-8").startswith(
        "# ABACUS v2.1 Deployment Report"
    )


def test_generate_report_handles_write_failure(tmp_path, caplog):
    dep = mod.ABACUSv21Deployment(tmp_path)
    dep.deployment_output = tmp_path / "does" / "not" / "exist"
    with caplog.at_level(logging.ERROR):
        result = dep._generate_deployment_report()
    assert result["report_generated"] is False
    assert "error" in result
    assert "report_path" not in result
    assert "Failed to generate report" in caplog.text


def test_markdown_report_renders_all_sections(tmp_path):
    dep = mod.ABACUSv21Deployment(tmp_path)
    dep.deployment_status["deployment_steps"] = {
        "step_1": {"name": "Good Step", "status": "completed", "timestamp": "T1"},
        "step_2": {"name": "Bad Step", "status": "failed", "timestamp": "T2"},
    }
    dep.deployment_status["health_checks"] = {
        "health_checks": {
            "alpha": {"status": "healthy"},
            "beta": {"status": "unhealthy"},
        }
    }
    dep.deployment_status["production_metrics"] = {
        "metrics": {"migration_completed": True, "deployment_readiness": 90}
    }
    dep.deployment_status["monitoring_results"] = {
        "recursive_engine": {
            "timestamp": "RT",
            "performance_metrics": {str(tmp_path / "eng.py"): {"lines": 4}},
        },
        "temporal_engine": {
            "timestamp": "TT",
            "validation_results": {
                "datetime": {"count": 3, "validated": True},
                "accessed_at": {"count": 0, "validated": False},
                "metadata_classes": {"FileMetadata": True},
            },
        },
    }
    report = dep._generate_markdown_report()
    assert "### Good Step" in report
    assert "**Status:** ✅ COMPLETED" in report
    assert "**Status:** ❌ FAILED" in report
    assert "- ✅ **alpha**: HEALTHY" in report
    assert "- ⚠️ **beta**: UNHEALTHY" in report
    assert "- **deployment_readiness**: 90" in report
    assert "**Timestamp:** RT" in report
    assert "- **eng.py**: {'lines': 4}" in report
    assert "**Timestamp:** TT" in report
    assert "- ✅ **datetime**: 3 occurrences" in report
    assert "- ❌ **accessed_at**: 0 occurrences" in report
    assert "metadata_classes" not in report


def test_markdown_report_without_optional_sections(tmp_path):
    dep = mod.ABACUSv21Deployment(tmp_path)
    for key in ("health_checks", "production_metrics", "monitoring_results"):
        del dep.deployment_status[key]
    report = dep._generate_markdown_report()
    assert "## System Health Checks" in report
    assert "**Timestamp:** " not in report
    assert "## Next Steps" in report


def test_execute_deployment_full_run(tmp_path, caplog):
    _populate(tmp_path)
    dep = mod.ABACUSv21Deployment(tmp_path)
    with caplog.at_level(logging.INFO):
        dep.execute_deployment()
    steps = dep.deployment_status["deployment_steps"]
    assert sorted(steps) == ["step_%d" % i for i in range(1, 9)]
    assert all(step["status"] == "completed" for step in steps.values())
    assert steps["step_8"]["result"]["report_generated"] is True
    assert "ABACUS v2.1 DEPLOYMENT EXECUTION" in caplog.text
    md = (
        tmp_path / "ABACUS_V21_DEPLOYMENT_OUTPUT" / "ABACUS_V21_DEPLOYMENT_REPORT.md"
    ).read_text(encoding="utf-8")
    # step 8 report is written before step 8 itself is recorded
    assert "### Confirm Knowledge Preservation" in md
    assert "### Generate Deployment Report" not in md
    assert "- **deployment_readiness**: 87.5" in md


def test_execute_deployment_records_failed_step(tmp_path, monkeypatch, caplog):
    dep = mod.ABACUSv21Deployment(tmp_path)

    def broken():
        raise ValueError("no versions")

    monkeypatch.setattr(dep, "_deploy_abacus_versions", broken)
    with caplog.at_level(logging.ERROR):
        dep.execute_deployment()
    step = dep.deployment_status["deployment_steps"]["step_2"]
    assert step["status"] == "failed"
    assert step["error"] == "no versions"
    assert "result" not in step
    assert dep.deployment_status["deployment_steps"]["step_3"]["status"] == (
        "completed"
    )
    assert "Deploy ABACUS Versions - FAILED: no versions" in caplog.text


def test_main_returns_zero_and_writes_reports(tmp_path, monkeypatch, caplog):
    monkeypatch.chdir(tmp_path)
    with caplog.at_level(logging.INFO):
        assert mod.main() == 0
    out = tmp_path / "ABACUS_V21_DEPLOYMENT_OUTPUT"
    assert (out / "ABACUS_V21_DEPLOYMENT_REPORT.json").is_file()
    assert "ABACUS v2.1 DEPLOYMENT COMPLETED" in caplog.text


def test_main_block_exits_zero(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = str(REPO_ROOT / "abacus_v21_deployment_execution.py")
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(path, run_name="__main__")
    assert exc.value.code == 0
    assert (tmp_path / "ABACUS_V21_DEPLOYMENT_OUTPUT").is_dir()
