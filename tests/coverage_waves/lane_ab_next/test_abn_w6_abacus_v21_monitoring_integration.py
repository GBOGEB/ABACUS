"""Gap tests for abacus_v21_monitoring_integration.py (run, report, main)."""

import ast
import json
import runpy

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("abacus_v21_monitoring_integration.py", name="abn_w6_monitoring_integration")
MOD_PATH = mod.__file__


@pytest.fixture
def mon(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return mod.MonitoringIntegration()


def test_generate_recommendations(mon):
    recs = mon.generate_recommendations()
    assert len(recs) == 5
    assert [r["category"] for r in recs][:3] == [
        "OBSERVABILITY",
        "ALERTING",
        "MONITORING",
    ]


def test_health_check_script_is_valid_python(mon):
    result = mon.create_health_check_script()
    assert result["message"] == "Health check script created"
    with open(result["details"]["script_file"], encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    assert {"check_core_modules", "check_directories", "main"} <= names


def test_run_integration_writes_results_and_report(mon, capsys):
    mon.run_integration()
    out = capsys.readouterr().out
    assert "Stage 2.3: Monitoring Integration" in out
    assert "Monitoring Integration Complete" in out
    with open(
        mon.output_dir / "monitoring_integration_results.json", encoding="utf-8"
    ) as fh:
        saved = json.load(fh)
    assert len(saved["monitoring_systems"]) == 3
    assert len(saved["alerts"]) == 1
    assert len(saved["dashboards"]) == 1
    assert len(saved["recommendations"]) == 5
    report = (mon.output_dir / "MONITORING_INTEGRATION_REPORT.md").read_text(
        encoding="utf-8"
    )
    assert "### [CREATED] Logging Configuration" in report
    assert "### [CREATED] Alert Rules" in report
    assert "### [CREATED] Dashboard Configuration" in report
    assert "### [HIGH] Implement Distributed Tracing" in report
    assert "### [MEDIUM] Centralize Log Aggregation" in report


def test_report_maps_non_high_priority_to_medium(mon):
    mon.results["recommendations"] = [
        dict(priority="LOW", title="T", category="C", description="D", action="A")
    ]
    mon.generate_report()
    report = (mon.output_dir / "MONITORING_INTEGRATION_REPORT.md").read_text(
        encoding="utf-8"
    )
    assert "### [MEDIUM] T" in report
    assert "[CREATED]" not in report


def test_main_entrypoint_runs_integration(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    runpy.run_path(MOD_PATH, run_name="__main__")
    assert "Monitoring Integration Complete" in capsys.readouterr().out
    assert (tmp_path / "ABACUS_V21_MONITORING" / "health_check.py").is_file()
