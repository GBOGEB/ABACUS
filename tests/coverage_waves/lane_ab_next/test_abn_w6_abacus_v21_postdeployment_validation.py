"""Behaviour tests for abacus_v21_postdeployment_validation.py (gap lines)."""

import json
import runpy
from datetime import datetime

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load(
    "abacus_v21_postdeployment_validation.py",
    name="abn_w6_abacus_v21_postdeployment_validation",
)


@pytest.fixture
def val(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return mod.PostDeploymentValidation()


def test_init_state(val, tmp_path):
    assert (tmp_path / "ABACUS_V21_POSTDEPLOYMENT_VALIDATION").is_dir()
    assert val.results["stage"] == "2.7"
    assert val.results["status"] == "INITIATED"


def test_production_health(val):
    health = val.validate_production_health()
    assert health["status"] == "ALL_HEALTHY"
    assert [c["category"] for c in health["checks"]] == [
        "Application Health",
        "Infrastructure Health",
        "External Services",
    ]


def test_smoke_tests_totals_consistent(val):
    tests = val.run_production_smoke_tests()
    suites = tests["test_suites"]
    assert tests["passed"] == sum(s["passed"] for s in suites)
    assert tests["failed"] == 0
    assert tests["total_tests"] == tests["passed"]
    assert tests["status"] == "ALL_PASSED"


def test_performance_security_monitoring_backup(val):
    assert val.validate_performance_metrics()["name"] == (
        "Performance Metrics Validation"
    )
    security = val.validate_security_measures()
    assert security["vulnerabilities_found"] == 0
    mon = val.validate_monitoring_systems()
    assert mon["dashboard_url"].startswith("https://")
    backup = val.validate_backup_systems()
    assert backup["status"] == "ALL_OPERATIONAL"


def test_baseline_next_review_is_seven_days_later(val):
    baseline = val.generate_production_baseline()
    est = datetime.fromisoformat(baseline["established_at"])
    nxt = datetime.fromisoformat(baseline["next_review"])
    assert 6.9 < (nxt - est).total_seconds() / 86400 < 7.1
    assert baseline["metrics"]["throughput"]["requests_per_second"] == 1500


def test_validation_report(val):
    report = val.generate_validation_report()
    assert report["validation_id"].startswith("VAL-")
    assert report["summary"]["failed_validations"] == 0
    assert report["next_phase"]["phase"] == "3.1"


def test_markdown_report_with_empty_results(val):
    md = val.generate_markdown_report()
    assert "**Validation ID**: N/A" in md
    assert "No smoke test data available" in md
    assert "No monitoring data available" in md
    assert "No backup data available" in md
    assert "**Vulnerabilities Found**: 0" in md
    assert "**Phase**: N/A" in md


def test_format_helpers_skip_non_matching_validations(val):
    val.results["validations"] = [{"name": "Other"}]
    assert val._format_smoke_tests() == "No smoke test data available"
    assert val._format_monitoring_systems() == "No monitoring data available"
    assert val._format_backup_systems() == "No backup data available"
    assert val._format_recommendations(["a", "b"]) == "1. a\n2. b"


def test_execute_validation_end_to_end(val, tmp_path, capsys):
    val.execute_validation()
    out = capsys.readouterr().out
    assert "POST-DEPLOYMENT VALIDATION COMPLETED" in out
    assert "Name: Performance Optimization" in out
    out_dir = tmp_path / "ABACUS_V21_POSTDEPLOYMENT_VALIDATION"
    saved = json.loads(
        (out_dir / "postdeployment_validation.json").read_text(encoding="utf-8")
    )
    assert saved["status"] == "SUCCESS"
    assert len(saved["validations"]) == 6
    md = (out_dir / "POSTDEPLOYMENT_VALIDATION_REPORT.md").read_text(encoding="utf-8")
    passed = saved["validations"][1]["passed"]
    assert "**Passed**: {}".format(passed) in md
    assert "**Dashboard**: https://monitoring.abacus.local/production" in md
    assert "**Status**: ALL_OPERATIONAL" in md
    assert "**Priority**: HIGH" in md


def test_main_function_and_block(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    mod.main()
    assert "POST-DEPLOYMENT VALIDATION" in capsys.readouterr().out
    runpy.run_path(mod.__file__, run_name="__main__")
    assert "Validation Summary" in capsys.readouterr().out
