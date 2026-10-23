"""W77-C: deployment, postdeployment and session source first-touch tests.

Only template-generation, simulated checks and local session reports are called.
Never invoke execute_deployment, execute_validation, live traffic switching,
remote authentication, actual rollback, or a PDF subprocess.
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


@contextmanager
def workspace():
    previous = pathlib.Path.cwd()
    with tempfile.TemporaryDirectory(prefix="w77-release-sim-") as folder:
        os.chdir(folder)
        try:
            yield pathlib.Path(folder)
        finally:
            os.chdir(previous)


class W77LegacyReleaseAndSessionTests(unittest.TestCase):
    def test_deployment_strategy_initialized_but_not_dispatched(self):
        with workspace():
            cls = importlib.import_module(
                "abacus_v21_production_deployment"
            ).ProductionDeployment
            obj = cls()
            self.assertEqual(obj.deployment_config["strategy"], "blue-green")
            self.assertTrue(obj.deployment_config["rollback_enabled"])
            self.assertEqual(obj.results["status"], "INITIATED")
            self.assertNotIn("native_deployment_attestation", obj.results)

    def test_simulated_predeployment_checks_not_real_security_proof(self):
        with workspace():
            obj = importlib.import_module(
                "abacus_v21_production_deployment"
            ).ProductionDeployment()
            simulated = obj.pre_deployment_checks()
            self.assertEqual(simulated["status"], "COMPLETED")
            self.assertEqual(len(simulated["checks"]), 5)
            self.assertTrue(simulated["all_passed"])
            # The legacy fixture reports PASSED without contacting an endpoint;
            # do not call this a production readiness or Safety waiver receipt.
            self.assertNotIn("endpoint_probe_sha256", simulated)
            self.assertNotIn("security_waiver", simulated)

    def test_deployment_plan_has_distinct_stages_with_no_real_traffic(self):
        with workspace():
            obj = importlib.import_module(
                "abacus_v21_production_deployment"
            ).ProductionDeployment()
            plan = obj.create_deployment_plan()
            self.assertEqual(plan["strategy"], "blue-green")
            self.assertEqual(len(plan["phases"]), 5)
            self.assertEqual([p["phase"] for p in plan["phases"]], [1, 2, 3, 4, 5])
            self.assertNotIn("actual_traffic_shift_percent", plan)

    def test_deployment_formatter_zero_and_negative_inputs_are_explicit(self):
        with workspace():
            obj = importlib.import_module(
                "abacus_v21_production_deployment"
            ).ProductionDeployment()
            zero = obj._format_summary({})
            self.assertIn("Services Deployed**: 0", zero)
            nonzero = obj._format_summary(
                {"services_deployed": 3, "rollback_triggered": True}
            )
            self.assertIn("Services Deployed**: 3", nonzero)
            self.assertIn("Rollback Triggered**: True", nonzero)
            self.assertNotIn("approved", nonzero.lower())

    def test_deployment_next_steps_are_numbered_not_executed(self):
        with workspace():
            obj = importlib.import_module(
                "abacus_v21_production_deployment"
            ).ProductionDeployment()
            self.assertEqual(
                obj._format_next_steps(["dry review", "independent gate"]),
                "1. dry review\n2. independent gate",
            )
            self.assertEqual(obj._format_next_steps([]), "")

    def test_postdeployment_simulated_health_is_not_authenticated(self):
        with workspace():
            obj = importlib.import_module(
                "abacus_v21_postdeployment_validation"
            ).PostDeploymentValidation()
            result = obj.validate_production_health()
            self.assertIn(result["status"], ("ALL_HEALTHY",))
            self.assertGreater(len(result["checks"]), 0)
            self.assertEqual(obj.results["status"], "INITIATED")
            self.assertNotIn("observed_native_receiver_id", result)

    def test_postdeployment_historical_security_claim_not_a_waiver(self):
        with workspace():
            obj = importlib.import_module(
                "abacus_v21_postdeployment_validation"
            ).PostDeploymentValidation()
            security = obj.validate_security_measures()
            self.assertGreater(len(security["checks"]), 0)
            self.assertNotIn("github_security_job_id", security)
            self.assertNotIn("security_waiver_approved", security)

    def test_postdeployment_formatters_preserve_unknown_defaults(self):
        with workspace():
            obj = importlib.import_module(
                "abacus_v21_postdeployment_validation"
            ).PostDeploymentValidation()
            self.assertIn("Health Status**: N/A", obj._format_summary({}))
            self.assertIn("N/A", obj._format_health_status())

    def test_session_empty_metrics_are_not_successful(self):
        with workspace() as root:
            module = importlib.import_module("abacus_v21_session_tuple_analyzer")
            obj = module.SessionTupleAnalyzer(workspace_root=root)
            obj._analyze_intents()
            self.assertIsNone(obj.session_metadata.primary_intent)
            obj._calculate_session_metrics()
            self.assertIs(
                obj.session_metadata.overall_outcome,
                module.ConversationOutcome.PARTIAL_SUCCESS,
            )
            self.assertEqual(obj.session_metadata.total_tuples, 0)

    def test_session_synthetic_three_tuple_population_is_not_live_chat(self):
        with workspace() as root:
            module = importlib.import_module("abacus_v21_session_tuple_analyzer")
            obj = module.SessionTupleAnalyzer(workspace_root=root)
            obj._extract_conversation_tuples()
            self.assertEqual(len(obj.conversation_tuples), 3)
            self.assertEqual(obj.session_metadata.total_tuples, 3)
            obj._analyze_intents()
            self.assertIs(
                obj.session_metadata.primary_intent, module.ConversationIntent.MIGRATION
            )
            obj._calculate_session_metrics()
            self.assertIs(
                obj.session_metadata.overall_outcome,
                module.ConversationOutcome.IN_PROGRESS,
            )
            self.assertNotIn("github_signed_provenance", obj.__dict__)

    def test_session_local_json_report_has_exact_synthetic_counts(self):
        with workspace() as root:
            module = importlib.import_module("abacus_v21_session_tuple_analyzer")
            obj = module.SessionTupleAnalyzer(workspace_root=root)
            obj._extract_conversation_tuples()
            obj._generate_json_report()
            path = obj.output_dir / "session_analysis_report.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["summary"]["total_tuples"], 3)
            self.assertEqual(len(data["conversation_tuples"]), 3)
            self.assertNotIn("root_closure_authorized", data)


if __name__ == "__main__":
    unittest.main()
