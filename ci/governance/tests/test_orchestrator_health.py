"""Negative controls: orchestrator health must follow the observed upstream result.

Covers report RC11: background_orchestrator.yml's health job used to emit
constant "healthy/active" values whatever the orchestrate job did.
"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.ci import orchestrator_health as health

WORKFLOW = (
    Path(__file__).resolve().parents[3]
    / ".github"
    / "workflows"
    / "background_orchestrator.yml"
)
ALL_OK = {"init": "success", "validation": "success", "pipeline": "success"}


class DeriveHealthTests(unittest.TestCase):
    def test_all_expected_steps_succeed_is_healthy(self):
        record = health.derive_health("success", ALL_OK, ["init", "pipeline"])
        self.assertEqual("HEALTHY", record["orchestrator_status"])
        self.assertEqual([], record["causes"])

    def test_failed_upstream_stage_is_failed_with_its_identity(self):
        steps = dict(ALL_OK, pipeline="failure")
        record = health.derive_health("failure", steps, ["init", "pipeline"])
        self.assertEqual("FAILED", record["orchestrator_status"])
        self.assertIn("orchestrate job failure", record["causes"])
        self.assertIn("step pipeline failure", record["causes"])

    def test_failed_init_skips_later_steps_and_is_failed(self):
        steps = {"init": "failure", "validation": "skipped", "pipeline": "skipped"}
        record = health.derive_health("failure", steps, ["init", "validation"])
        self.assertEqual("FAILED", record["orchestrator_status"])
        self.assertIn("step init failure", record["causes"])

    def test_cancelled_job_is_failed(self):
        record = health.derive_health("cancelled", ALL_OK, ["init"])
        self.assertEqual("FAILED", record["orchestrator_status"])

    def test_expected_step_that_did_not_run_is_degraded(self):
        steps = dict(ALL_OK, pipeline="skipped")
        record = health.derive_health("success", steps, ["init", "pipeline"])
        self.assertEqual("DEGRADED", record["orchestrator_status"])
        self.assertIn("step pipeline did not run (skipped)", record["causes"])

    def test_unexpected_skipped_step_is_still_healthy(self):
        steps = dict(ALL_OK, validation="skipped", pipeline="skipped")
        record = health.derive_health("success", steps, ["init"])
        self.assertEqual("HEALTHY", record["orchestrator_status"])

    def test_missing_or_unknown_job_result_is_unknown_not_healthy(self):
        for result in ("", None, "neutral"):
            with self.subTest(result=result):
                record = health.derive_health(result, ALL_OK, ["init"])
                self.assertEqual("UNKNOWN", record["orchestrator_status"])

    def test_components_are_not_claimed_active(self):
        record = health.derive_health("success", ALL_OK, ["init"])
        self.assertEqual(
            {"dow": None, "keb": None, "gbogeb": None}, record["components"]
        )


class CliTests(unittest.TestCase):
    def _run(self, *argv: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "health.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = health.main([*argv, "--out", str(out)])
            self.assertEqual(0, code)
            return json.loads(out.read_text(encoding="utf-8"))

    def test_cli_writes_derived_record(self):
        record = self._run(
            "--job-result",
            "failure",
            "--step",
            "init=success",
            "--expect",
            "init",
            "--step",
            "pipeline=failure",
            "--expect",
            "pipeline",
            "--run-id",
            "42",
        )
        self.assertEqual("FAILED", record["orchestrator_status"])
        self.assertEqual("42", record["run_id"])

    def test_cli_rejects_expectation_without_observation(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                health.main(["--job-result", "success", "--expect", "init"])


class WorkflowWiringTests(unittest.TestCase):
    def setUp(self):
        self.doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        self.health_steps = self.doc["jobs"]["health_check"]["steps"]

    def test_health_job_has_no_constant_healthy_claims(self):
        text = yaml.safe_dump(self.doc["jobs"]["health_check"])
        self.assertNotIn("'healthy'", text)
        self.assertNotIn("_active': True", text)
        self.assertNotIn("✅ Active", WORKFLOW.read_text(encoding="utf-8"))

    def test_health_is_derived_from_orchestrate_outputs(self):
        outputs = self.doc["jobs"]["orchestrate"]["outputs"]
        step_ids = {step.get("id") for step in self.doc["jobs"]["orchestrate"]["steps"]}
        for name in ("init_orchestrator", "validation_suite", "background_pipeline"):
            self.assertIn(name, step_ids)
            self.assertTrue(any(name in value for value in outputs.values()))
        (derive,) = [s for s in self.health_steps if s.get("id") == "health"]
        self.assertIn("scripts/ci/orchestrator_health.py", derive["run"])
        self.assertEqual("${{ needs.orchestrate.result }}", derive["env"]["JOB_RESULT"])

    def test_unhealthy_status_fails_the_health_job(self):
        last = self.health_steps[-1]
        self.assertIn('test "$STATUS" = HEALTHY', last["run"])
        self.assertNotIn("if", last)


if __name__ == "__main__":
    unittest.main()
