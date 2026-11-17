"""Gap tests for abacus_v21_backup_recovery.py (scripts, report, main)."""

import json
import runpy

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("abacus_v21_backup_recovery.py", name="abn_w6_backup_recovery")
MOD_PATH = mod.__file__


@pytest.fixture
def br(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return mod.BackupRecovery()


def test_disaster_recovery_plan_writes_json(br):
    result = br.create_disaster_recovery_plan()
    assert result["status"] == "CREATED"
    assert result["details"]["dr_sites"] == 2
    assert result["message"] == "Disaster recovery plan created"
    with open(result["details"]["config_file"], encoding="utf-8") as fh:
        plan = json.load(fh)
    assert plan["failover_procedures"]["automatic_failover"]["enabled"] is True
    assert plan["testing_schedule"]["backup_restore_test"] == "monthly"


def test_backup_scripts_written_without_chmod_warning(br):
    result = br.create_backup_scripts()
    assert result["message"] == "Backup and restore scripts created"
    assert "chmod_warning" not in result["details"]
    with open(result["details"]["backup_script"], encoding="utf-8") as fh:
        backup = fh.read()
    with open(result["details"]["restore_script"], encoding="utf-8") as fh:
        restore = fh.read()
    assert backup.startswith("#!/bin/bash")
    assert "sha256sum *.tar.gz" in backup
    assert "RESTORE_TIMESTAMP" in restore
    assert br.results["recommendations"] == []


def test_backup_scripts_chmod_failure_adds_recommendation(br, monkeypatch):
    def deny(*_args, **_kwargs):
        raise OSError("denied")

    monkeypatch.setattr(mod.os, "chmod", deny)
    result = br.create_backup_scripts()
    assert "denied" in result["details"]["chmod_warning"]
    recs = br.results["recommendations"]
    assert len(recs) == 1
    assert recs[0]["category"] == "PERMISSIONS"
    assert "denied" in recs[0]["action"]


def test_generate_recommendations_priorities():
    recs = mod.BackupRecovery.generate_recommendations(None)
    assert len(recs) == 6
    assert [r["priority"] for r in recs[:2]] == ["CRITICAL", "CRITICAL"]
    assert recs[-1]["category"] == "DOCUMENTATION"


def test_run_backup_setup_writes_results_and_report(br, capsys):
    br.run_backup_setup()
    out = capsys.readouterr().out
    assert "Stage 2.5: Backup & Recovery" in out
    assert "Backup & Recovery Setup Complete" in out
    out_dir = br.output_dir
    with open(out_dir / "backup_recovery_results.json", encoding="utf-8") as fh:
        saved = json.load(fh)
    assert len(saved["backup_strategies"]) == 2
    assert len(saved["recovery_procedures"]) == 1
    assert len(saved["disaster_recovery"]) == 1
    assert len(saved["recommendations"]) == 6
    report = (out_dir / "BACKUP_RECOVERY_REPORT.md").read_text(encoding="utf-8")
    assert "### [CREATED] Backup Strategy" in report
    assert "### [CREATED] Recovery Procedures" in report
    assert "### [CREATED] Disaster Recovery Plan" in report
    assert "### [CRITICAL] Implement 3-2-1 Backup Rule" in report
    assert "Stage 2.6: Production Deployment" in report


def test_generate_report_with_empty_results(br):
    br.generate_report()
    report = (br.output_dir / "BACKUP_RECOVERY_REPORT.md").read_text(encoding="utf-8")
    assert "## Backup Strategies" in report
    assert "[CREATED]" not in report


def test_main_entrypoint_runs_setup(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    runpy.run_path(MOD_PATH, run_name="__main__")
    assert "Backup & Recovery Setup Complete" in capsys.readouterr().out
    assert (tmp_path / "ABACUS_V21_BACKUP" / "restore.sh").is_file()
