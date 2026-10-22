"""W77-A: source-bound first execution for five legacy configuration generators.

All artifacts are produced inside a disposable temporary workspace.  Generated
deployment YAML, backup plans and role definitions are DOCUMENTS, not approval
to deploy, restore, write GitHub content or issue a security waiver.
"""
from __future__ import annotations

import importlib
import json
import os
import pathlib
import sys
import tempfile
import unittest
from contextlib import contextmanager

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SOURCES = {
    "abacus_v21_cicd_pipeline_setup": ("CICDPipelineSetup", "ABACUS_V21_CICD_PIPELINE"),
    "abacus_v21_backup_recovery": ("BackupRecovery", "ABACUS_V21_BACKUP"),
    "abacus_v21_monitoring_integration": (
        "MonitoringIntegration", "ABACUS_V21_MONITORING"
    ),
    "abacus_v21_security_hardening": ("SecurityHardening", "ABACUS_V21_SECURITY"),
    "abacus_v21_environment_preparation": (
        "EnvironmentPreparation", "ABACUS_V21_ENVIRONMENT_PREP"
    ),
}


@contextmanager
def temporary_workspace():
    before = pathlib.Path.cwd()
    with tempfile.TemporaryDirectory(prefix="w77-legacy-config-") as folder:
        os.chdir(folder)
        try:
            yield pathlib.Path(folder)
        finally:
            os.chdir(before)


def instantiate(module_name):
    module = importlib.import_module(module_name)
    class_name, output_name = SOURCES[module_name]
    obj = getattr(module, class_name)()
    assert obj.output_dir.name == output_name
    assert obj.output_dir.is_dir()
    return obj


class W77LegacyConfigurationTests(unittest.TestCase):
    def test_all_five_instances_write_only_to_isolated_workspace(self):
        with temporary_workspace() as root:
            for source in SOURCES:
                with self.subTest(source=source):
                    obj = instantiate(source)
                    self.assertTrue((root / obj.output_dir).is_dir())
                    self.assertFalse(obj.results.get("merge_authorized", False))
                    self.assertFalse(obj.results.get("owner_acceptance", False))

    def test_github_actions_rendered_as_data_not_executed(self):
        with temporary_workspace():
            obj = instantiate("abacus_v21_cicd_pipeline_setup")
            receipt = obj.create_github_actions_workflow()
            self.assertEqual(receipt["status"], "CREATED")
            p = pathlib.Path(receipt["details"]["workflow_file"])
            self.assertTrue(p.is_file())
            text = p.read_text(encoding="utf-8")
            self.assertIn("jobs:", text)
            self.assertIn("pull_request", text)
            self.assertNotIn("github_pat_", text)

    def test_jenkins_and_gitlab_files_are_templates(self):
        with temporary_workspace():
            obj = instantiate("abacus_v21_cicd_pipeline_setup")
            first = obj.create_jenkins_pipeline()
            second = obj.create_gitlab_ci_config()
            self.assertEqual(first["status"], "CREATED")
            self.assertEqual(second["status"], "CREATED")
            self.assertIn("pipeline {", pathlib.Path(
                first["details"]["jenkinsfile"]).read_text(encoding="utf-8"))
            self.assertEqual(len(list(obj.output_dir.glob("*"))) >= 2, True)

    def test_backup_policy_retention_and_copy_configuration(self):
        with temporary_workspace():
            obj = instantiate("abacus_v21_backup_recovery")
            receipt = obj.create_backup_strategy()
            self.assertEqual(receipt["status"], "CREATED")
            policy = json.loads(pathlib.Path(
                receipt["details"]["config_file"]).read_text(encoding="utf-8"))
            self.assertEqual(policy["backup_types"]["full_backup"]["retention_days"], 30)
            self.assertEqual(
                policy["backup_verification"]["integrity_check"], "sha256"
            )
            self.assertFalse(obj.results.get("native_restore_verified", False))

    def test_recovery_plan_is_a_template_not_an_actual_restore(self):
        with temporary_workspace():
            obj = instantiate("abacus_v21_backup_recovery")
            result = obj.create_recovery_procedures()
            self.assertEqual(result["status"], "CREATED")
            self.assertTrue(list(obj.output_dir.glob("*.json")))
            self.assertNotIn("restored_bytes", result)

    def test_monitoring_config_has_no_live_receiver_attestation(self):
        with temporary_workspace():
            obj = instantiate("abacus_v21_monitoring_integration")
            for method in ("create_logging_config", "create_metrics_config",
                           "create_alert_rules", "create_dashboard_config"):
                with self.subTest(method=method):
                    receipt = getattr(obj, method)()
                    self.assertEqual(receipt["status"], "CREATED")
            self.assertGreaterEqual(len(list(obj.output_dir.iterdir())), 4)
            self.assertNotIn("native_receiver_job_id", obj.results)

    def test_monitoring_health_check_script_not_executed(self):
        with temporary_workspace():
            obj = instantiate("abacus_v21_monitoring_integration")
            receipt = obj.create_health_check_script()
            self.assertEqual(receipt["status"], "CREATED")
            self.assertNotIn("operational_health_verified", obj.results)

    def test_security_rbac_template_only(self):
        with temporary_workspace():
            obj = instantiate("abacus_v21_security_hardening")
            receipt = obj.create_rbac_config()
            self.assertEqual(receipt["status"], "CREATED")
            cfg = json.loads(pathlib.Path(
                receipt["details"]["config_file"]).read_text(encoding="utf-8"))
            self.assertIn("admin", cfg["roles"])
            self.assertIn("viewer", cfg["roles"])
            self.assertFalse(obj.results.get("security_waiver", False))

    def test_secrets_template_uses_placeholders_not_real_credentials(self):
        with temporary_workspace():
            obj = instantiate("abacus_v21_security_hardening")
            receipt = obj.create_secrets_management()
            self.assertEqual(receipt["status"], "CREATED")
            template = (obj.output_dir / ".env.template").read_text(
                encoding="utf-8")
            self.assertIn("<vault:", template)
            self.assertIn("DO NOT commit actual secrets", template)
            self.assertNotIn("native_secret_rotation_verified", obj.results)

    def test_environment_python_identity_is_observation(self):
        with temporary_workspace():
            obj = instantiate("abacus_v21_environment_preparation")
            receipt = obj.check_python_environment()
            self.assertEqual(receipt["name"], "Python Environment")
            self.assertIn("python_version", receipt["details"])
            self.assertFalse(obj.results.get("merge_authorized", False))

    def test_environment_required_directories_are_local(self):
        with temporary_workspace() as root:
            obj = instantiate("abacus_v21_environment_preparation")
            receipt = obj.check_required_directories()
            self.assertEqual(receipt["status"], "PASS")
            self.assertTrue((root / "logs").is_dir())
            self.assertTrue((root / "backups").is_dir())
            self.assertEqual(len(receipt["details"]["created"]) +
                             len(receipt["details"]["existing"]), 9)

    def test_configuration_templates_do_not_imply_cicd_security_acceptance(self):
        with temporary_workspace():
            for source in (
                    "abacus_v21_cicd_pipeline_setup",
                    "abacus_v21_backup_recovery",
                    "abacus_v21_monitoring_integration",
                    "abacus_v21_security_hardening",
                    "abacus_v21_environment_preparation"):
                obj = instantiate(source)
                with self.subTest(source=source):
                    self.assertNotIn("independent_approval", obj.results)
                    self.assertNotIn("qps_owner_accepted", obj.results)


if __name__ == "__main__":
    unittest.main()
