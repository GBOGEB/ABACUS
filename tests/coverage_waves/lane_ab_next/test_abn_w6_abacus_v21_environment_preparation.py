"""Behaviour tests for abacus_v21_environment_preparation.py (gap lines)."""

import json
import runpy
import types

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load(
    "abacus_v21_environment_preparation.py",
    name="abn_w6_abacus_v21_environment_preparation",
)

CORE = [
    "execute_full_pipeline_sprint_dow.py",
    "dmaic_v3_orchestrator.py",
    "recursive_knowledge_engine.py",
    "temporal_session_analyzer.py",
]
CONFIGS = ["DOW_IMPLEMENTATION_TRACKER.json", "ABACUS_V21_PROGRESS_TRACKER.yaml"]


@pytest.fixture
def prep(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return mod.EnvironmentPreparation()


def _fake_sys(version_info):
    return types.SimpleNamespace(
        version="fake",
        executable="py",
        platform="plat",
        version_info=version_info,
    )


def test_init_state(prep, tmp_path):
    assert (tmp_path / "ABACUS_V21_ENVIRONMENT_PREP").is_dir()
    assert prep.results["stage"] == "2.1"
    assert prep.results["checks"] == []


def test_python_environment_compatible(prep, monkeypatch):
    monkeypatch.setattr(mod, "sys", _fake_sys((3, 11, 0)))
    check = prep.check_python_environment()
    assert check["status"] == "PASS"
    assert check["message"] == "Python 3.11 is compatible"
    assert check["details"]["platform"] == "plat"


def test_python_environment_old_version_warns(prep, monkeypatch):
    monkeypatch.setattr(mod, "sys", _fake_sys((3, 7, 9)))
    check = prep.check_python_environment()
    assert check["status"] == "WARN"
    assert "recommend 3.8+" in check["message"]


def test_required_directories_created_then_existing(prep, tmp_path):
    first = prep.check_required_directories()
    assert len(first["details"]["created"]) == 9
    assert first["details"]["existing"] == []
    assert (tmp_path / "logs").is_dir()
    second = prep.check_required_directories()
    assert second["details"]["created"] == []
    assert second["message"] == "Created 0 directories, 9 already exist"


def test_configuration_files_missing_and_present(prep, tmp_path):
    missing = prep.check_configuration_files()
    assert missing["status"] == "WARN"
    assert missing["message"] == "Missing 2 configuration files"
    for name in CONFIGS:
        (tmp_path / name).write_text("{}", encoding="utf-8")
    found = prep.check_configuration_files()
    assert found["status"] == "PASS"
    assert found["details"]["found"] == CONFIGS
    assert found["message"] == "All configuration files present"


def test_core_modules_missing_and_present(prep, tmp_path):
    (tmp_path / CORE[0]).write_text("", encoding="utf-8")
    partial = prep.check_core_modules()
    assert partial["status"] == "FAIL"
    assert partial["message"] == "Missing 3 core modules"
    for name in CORE[1:]:
        (tmp_path / name).write_text("", encoding="utf-8")
    full = prep.check_core_modules()
    assert full["status"] == "PASS"
    assert full["details"]["missing"] == []


def test_config_writers_produce_files(prep, tmp_path):
    out_dir = tmp_path / "ABACUS_V21_ENVIRONMENT_PREP"
    env = prep.create_environment_config()
    data = json.loads(
        (out_dir / "production_environment_config.json").read_text(encoding="utf-8")
    )
    assert data["environment"] == "production"
    assert (
        env["details"]["settings"]["settings"]["performance"]["parallel_workers"] == 4
    )
    checklist = prep.create_deployment_checklist()
    assert checklist["details"]["total_tasks"] == 15
    assert "15 tasks" in checklist["message"]
    assert (out_dir / "deployment_checklist.json").is_file()
    mon = prep.create_monitoring_config()
    assert mon["details"]["metrics_count"] == 3
    mdata = json.loads((out_dir / "monitoring_config.json").read_text(encoding="utf-8"))
    assert mdata["alerts"]["notification_rules"]["CRITICAL"]["throttle"] == 0


def test_generate_recommendations_priorities(prep):
    recs = prep.generate_recommendations()
    assert [r["priority"] for r in recs] == ["HIGH", "HIGH", "HIGH", "MEDIUM", "MEDIUM"]


def test_run_preparation_mixed_statuses(prep, tmp_path, capsys):
    (tmp_path / CONFIGS[0]).write_text("{}", encoding="utf-8")
    prep.run_preparation()
    out = capsys.readouterr().out
    assert "Environment Preparation Complete" in out
    assert "Results saved to:" in out
    out_dir = tmp_path / "ABACUS_V21_ENVIRONMENT_PREP"
    saved = json.loads(
        (out_dir / "environment_preparation_results.json").read_text(encoding="utf-8")
    )
    statuses = [c["status"] for c in saved["checks"]]
    assert statuses == ["PASS", "PASS", "WARN", "FAIL"]
    assert len(saved["configurations"]) == 3
    md = (out_dir / "ENVIRONMENT_PREPARATION_REPORT.md").read_text(encoding="utf-8")
    assert "### [WARN] Configuration Files" in md
    assert "### [FAIL] Core Modules" in md
    assert "### [PASS] Python Environment" in md
    assert "### [MEDIUM] Optimize Resource Allocation" in md
    assert "### [CREATED] Deployment Checklist" in md


def test_generate_report_low_priority_rendered_as_medium(prep, tmp_path):
    prep.results["recommendations"] = [
        dict(priority="LOW", title="T", category="C", description="D", action="A")
    ]
    prep.generate_report()
    md = tmp_path / "ABACUS_V21_ENVIRONMENT_PREP" / "ENVIRONMENT_PREPARATION_REPORT.md"
    assert "### [MEDIUM] T" in md.read_text(encoding="utf-8")


def test_main_block_runs(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    runpy.run_path(mod.__file__, run_name="__main__")
    assert "Environment Preparation Complete" in capsys.readouterr().out
    assert (tmp_path / "config").is_dir()
