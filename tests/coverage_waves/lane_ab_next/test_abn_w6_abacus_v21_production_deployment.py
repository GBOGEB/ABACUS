"""Behaviour tests for abacus_v21_production_deployment.py (gap lines)."""

import json
import runpy

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load(
    "abacus_v21_production_deployment.py",
    name="abn_w6_abacus_v21_production_deployment",
)


@pytest.fixture
def dep(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return mod.ProductionDeployment()


def test_init_state(dep, tmp_path):
    assert (tmp_path / "ABACUS_V21_PRODUCTION_DEPLOYMENT").is_dir()
    assert dep.results["status"] == "INITIATED"
    assert dep.deployment_config["rollback_enabled"] is True


def test_pre_deployment_checks_all_pass(dep):
    checks = dep.pre_deployment_checks()
    assert checks["status"] == "COMPLETED"
    assert checks["all_passed"] is True
    assert len(checks["checks"]) == 5
    assert {c["status"] for c in checks["checks"]} == {"PASSED"}
    assert all("timestamp" in c for c in checks["checks"])


def test_plan_and_green_deploy(dep):
    plan = dep.create_deployment_plan()
    assert [p["phase"] for p in plan["phases"]] == [1, 2, 3, 4, 5]
    assert plan["total_duration"] == "45 minutes"
    green = dep.deploy_green_environment()
    assert green["status"] == "COMPLETED"
    assert len(green["steps"]) == 5


def test_health_smoke_traffic_rollback_monitoring(dep):
    assert dep.execute_health_checks()["status"] == "ALL_HEALTHY"
    smoke = dep.execute_smoke_tests()
    assert smoke["total"] == 5 and smoke["passed"] == 5
    switch = dep.gradual_traffic_switch()
    assert [s["traffic_percentage"] for s in switch["stages"]] == [10, 25, 50, 100]
    rollback = dep.create_rollback_plan()
    assert len(rollback["procedure"]) == 5
    assert rollback["total_rollback_time"] == "< 5 minutes"
    mon = dep.post_deployment_monitoring()
    assert [m["category"] for m in mon["metrics"]] == [
        "Performance",
        "Reliability",
        "Business",
    ]


def test_generate_deployment_report(dep):
    report = dep.generate_deployment_report()
    assert report["deployment_id"].startswith("PROD-")
    assert report["summary"]["rollback_triggered"] is False
    assert len(report["next_steps"]) == 5


def test_markdown_report_with_empty_results(dep):
    md = dep.generate_markdown_report()
    assert "**Deployment ID**: N/A" in md
    assert "No health checks recorded" in md
    assert "**Enabled**: False" in md
    assert "**Dashboard**: N/A" in md
    assert "- **Services Deployed**: 0" in md


def test_format_helpers(dep):
    dep.results["phases"] = [{"name": "A", "status": "OK"}, {}]
    phases = dep._format_phases()
    assert "### Phase 1: A" in phases
    assert "### Phase 2: Unknown" in phases
    assert "**Status**: N/A" in phases
    dep.results["health_checks"] = [{"name": "H", "status": "UP"}, {}]
    assert dep._format_health_checks() == "**H**: UP\n**Unknown**: N/A"
    assert dep._format_next_steps(["x", "y"]) == "1. x\n2. y"
    assert dep._format_next_steps([]) == ""


def test_execute_deployment_end_to_end(dep, tmp_path, capsys):
    dep.execute_deployment()
    out = capsys.readouterr().out
    assert "DEPLOYMENT COMPLETED SUCCESSFULLY" in out
    assert "Smoke tests: 5/5 passed" in out
    assert "5. Schedule post-mortem meeting" in out
    out_dir = tmp_path / "ABACUS_V21_PRODUCTION_DEPLOYMENT"
    saved = json.loads(
        (out_dir / "production_deployment.json").read_text(encoding="utf-8")
    )
    assert saved["status"] == "SUCCESS"
    assert len(saved["phases"]) == 4
    assert saved["deployment_plan"]["strategy"] == "blue-green"
    md = (out_dir / "PRODUCTION_DEPLOYMENT_REPORT.md").read_text(encoding="utf-8")
    assert "**Health Check Validation**: ALL_HEALTHY" in md
    assert "### Phase 4: Traffic Switch" in md
    assert "**Total Rollback Time**: < 5 minutes" in md
    assert "https://monitoring.abacus.local/production" in md


def test_main_function_and_block(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    mod.main()
    assert "PRODUCTION DEPLOYMENT" in capsys.readouterr().out
    runpy.run_path(mod.__file__, run_name="__main__")
    assert "DEPLOYMENT COMPLETED SUCCESSFULLY" in capsys.readouterr().out
