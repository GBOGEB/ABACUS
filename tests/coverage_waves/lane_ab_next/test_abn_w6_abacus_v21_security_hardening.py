"""Gap tests for abacus_v21_security_hardening.py (policies, report, main)."""

import json
import runpy

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("abacus_v21_security_hardening.py", name="abn_w6_security_hardening")
MOD_PATH = mod.__file__


def _read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture
def sh(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return mod.SecurityHardening()


def test_env_template_holds_only_vault_references(sh):
    result = sh.create_secrets_management()
    assert result["details"]["secret_categories"] == 4
    template = (sh.output_dir / ".env.template").read_text(encoding="utf-8")
    value_lines = [
        line
        for line in template.splitlines()
        if "=" in line and not line.startswith("#")
    ]
    refs = [line for line in value_lines if "<vault:" in line]
    assert len(refs) == 8
    assert "APP_ENV=production" in value_lines


def test_security_policies_counts_categories(sh):
    result = sh.create_security_policies()
    assert result["message"] == "Security policies created"
    assert result["details"]["policy_categories"] == 4
    policies = _read_json(result["details"]["config_file"])
    rules = policies["network_security"]["firewall_rules"]
    assert [r["action"] for r in rules] == ["ALLOW", "ALLOW", "DENY"]
    assert policies["data_security"]["encryption_in_transit"]["tls_version"] == "1.3"


def test_audit_logging_config(sh):
    result = sh.create_audit_logging()
    assert result["details"]["event_categories"] == 5
    audit = _read_json(result["details"]["config_file"])
    assert audit["retention"]["compliance_logs"] == 2555
    assert audit["alerting"]["thresholds"]["failed_logins"] == 5


def test_security_checklist_counts_tasks(sh):
    result = sh.create_security_checklist()
    assert result["details"]["categories"] == 6
    assert result["details"]["total_tasks"] == 30
    assert result["message"] == "Security checklist created with 30 tasks"
    checklist = _read_json(result["details"]["config_file"])
    statuses = {t["status"] for c in checklist["categories"] for t in c["tasks"]}
    assert statuses == {"PENDING"}


def test_generate_recommendations(sh):
    recs = sh.generate_recommendations()
    assert len(recs) == 8
    assert sum(1 for r in recs if r["priority"] == "CRITICAL") == 3
    assert recs[-1]["category"] == "TRAINING"


def test_run_hardening_writes_results_and_report(sh, capsys):
    sh.run_hardening()
    out = capsys.readouterr().out
    assert "Stage 2.4: Security Hardening" in out
    assert "Security Hardening Complete" in out
    saved = _read_json(sh.output_dir / "security_hardening_results.json")
    assert len(saved["access_controls"]) == 1
    assert len(saved["secrets_management"]) == 1
    assert len(saved["security_measures"]) == 2
    assert len(saved["audit_logs"]) == 1
    assert len(saved["recommendations"]) == 8
    report = (sh.output_dir / "SECURITY_HARDENING_REPORT.md").read_text(
        encoding="utf-8"
    )
    assert "### [CREATED] RBAC Configuration" in report
    assert "### [CREATED] Secrets Management" in report
    assert "### [CREATED] Security Checklist" in report
    assert "### [CREATED] Audit Logging" in report
    assert "### [CRITICAL] Enable Multi-Factor Authentication" in report
    assert "Stage 2.5: Backup & Recovery" in report


def test_generate_report_with_empty_results(sh):
    sh.generate_report()
    report = (sh.output_dir / "SECURITY_HARDENING_REPORT.md").read_text(
        encoding="utf-8"
    )
    assert "## Access Controls" in report
    assert "[CREATED]" not in report


def test_main_entrypoint_runs_hardening(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    runpy.run_path(MOD_PATH, run_name="__main__")
    assert "Security Hardening Complete" in capsys.readouterr().out
    assert (tmp_path / "ABACUS_V21_SECURITY" / "rbac_config.json").is_file()
