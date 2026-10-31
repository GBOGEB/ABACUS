"""Gap tests for abacus_v21_cicd_pipeline_setup.py (deploy script, report, main)."""

import json
import runpy

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("abacus_v21_cicd_pipeline_setup.py", name="abn_w6_cicd_pipeline_setup")
MOD_PATH = mod.__file__


@pytest.fixture
def cicd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return mod.CICDPipelineSetup()


def test_deployment_script_written(cicd):
    result = cicd.create_deployment_script()
    assert result["message"] == "Deployment script created"
    assert "chmod_warning" not in result["details"]
    with open(result["details"]["script_file"], encoding="utf-8") as fh:
        text = fh.read()
    assert text.startswith("#!/bin/bash")
    assert "python abacus_v21_smoke_tests.py" in text


def test_deployment_script_chmod_failure(cicd, monkeypatch):
    def deny(*_args, **_kwargs):
        raise OSError("read-only fs")

    monkeypatch.setattr(mod.os, "chmod", deny)
    result = cicd.create_deployment_script()
    assert result["message"] == "Deployment script created (permissions not updated)"
    assert "read-only fs" in result["details"]["chmod_warning"]


def test_requirements_file(cicd):
    result = cicd.create_requirements_file()
    assert result["message"] == "Requirements file created"
    with open(result["details"]["requirements_file"], encoding="utf-8") as fh:
        lines = [ln for ln in fh.read().splitlines() if ln and not ln.startswith("#")]
    assert lines == [
        "pyyaml>=6.0",
        "pytest>=7.0.0",
        "pytest-cov>=4.0.0",
        "build>=0.10.0",
        "twine>=4.0.0",
    ]


def test_generate_recommendations(cicd):
    recs = cicd.generate_recommendations()
    assert [r["priority"] for r in recs] == ["HIGH", "HIGH", "HIGH", "MEDIUM", "MEDIUM"]


def test_run_setup_writes_results_and_report(cicd, capsys):
    cicd.run_setup()
    out = capsys.readouterr().out
    assert "Stage 2.2: CI/CD Pipeline Setup" in out
    assert "CI/CD Pipeline Setup Complete" in out
    with open(cicd.output_dir / "cicd_pipeline_results.json", encoding="utf-8") as fh:
        saved = json.load(fh)
    assert len(saved["pipelines"]) == 3
    assert len(saved["configurations"]) == 2
    assert len(saved["recommendations"]) == 5
    report = (cicd.output_dir / "CICD_PIPELINE_REPORT.md").read_text(encoding="utf-8")
    assert "### [CREATED] Deployment Script" in report
    assert "### [CREATED] Requirements File" in report
    assert "### [HIGH] Implement Automated Testing" in report
    assert "### [MEDIUM] Add Pipeline Monitoring" in report
    assert "Stage 2.3: Monitoring Integration" in report


def test_report_maps_non_high_priority_to_medium(cicd):
    cicd.results["recommendations"] = [
        dict(priority="LOW", title="T", category="C", description="D", action="A")
    ]
    cicd.generate_report()
    report = (cicd.output_dir / "CICD_PIPELINE_REPORT.md").read_text(encoding="utf-8")
    assert "### [MEDIUM] T" in report
    assert "[CREATED]" not in report


def test_main_entrypoint_runs_setup(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    runpy.run_path(MOD_PATH, run_name="__main__")
    assert "CI/CD Pipeline Setup Complete" in capsys.readouterr().out
    assert (tmp_path / "ABACUS_V21_CICD_PIPELINE" / "deploy.sh").is_file()
