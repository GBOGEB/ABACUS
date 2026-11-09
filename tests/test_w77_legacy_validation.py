"""W77-B: zero-to-positive validation of four legacy PRE-CD producers.

The scripts' historical simulated PASS flags are not native engineering,
hardware, repository-federation, or deployment acceptance.
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
    with tempfile.TemporaryDirectory(prefix="w77-validation-") as path:
        os.chdir(path)
        try:
            yield pathlib.Path(path)
        finally:
            os.chdir(previous)


def suite(module_name, class_name):
    cls = getattr(importlib.import_module(module_name), class_name)
    obj = cls()
    assert obj.output_dir.is_dir()
    return obj


class W77LegacyValidationTests(unittest.TestCase):
    def test_knowledge_index_is_written_locally(self):
        with workspace() as root:
            obj = suite(
                "abacus_v21_knowledge_preservation", "KnowledgePreservationSuite"
            )
            self.assertTrue(obj.generate_knowledge_index())
            self.assertTrue(list((root / obj.output_dir).rglob("*.json")))
            self.assertEqual(obj.failed, 0)
            self.assertGreaterEqual(obj.passed, 1)

    def test_knowledge_index_is_only_mock_catalogue_not_verified_sources(self):
        with workspace():
            obj = suite(
                "abacus_v21_knowledge_preservation", "KnowledgePreservationSuite"
            )
            obj.generate_knowledge_index()
            self.assertNotIn("source_blob_attested", obj.__dict__)
            self.assertNotIn("owner_acceptance", obj.__dict__)

    def test_dryrun_missing_tracker_is_failed_not_silent_green(self):
        with workspace():
            obj = suite("abacus_v21_dry_run_tests", "DryRunTestSuite")
            result = obj.test_dry_run_dow_workflows()
            self.assertFalse(result)
            self.assertEqual(obj.failed, 1)
            self.assertEqual(obj.results[-1]["status"], "FAIL")

    def test_dryrun_parses_local_tracker_with_stub_workflow(self):
        with workspace() as root:
            (root / "DOW_IMPLEMENTATION_TRACKER.json").write_text(
                '{"version":"synthetic"}', encoding="utf-8"
            )
            (root / "dmaic_v3_orchestrator.py").write_text(
                "def fake():\n    return True\n", encoding="utf-8"
            )
            obj = suite("abacus_v21_dry_run_tests", "DryRunTestSuite")
            self.assertTrue(obj.test_dry_run_dow_workflows())
            self.assertEqual(obj.results[-1]["workflows_tested"], 1)
            self.assertEqual(obj.results[-1]["workflows_passed"], 1)
            self.assertEqual(obj.results[-1]["status"], "PASS")
            self.assertNotIn("native_test_attestation", obj.results[-1])

    def test_dryrun_corrupt_tracker_cannot_gain_credit(self):
        with workspace():
            pathlib.Path("DOW_IMPLEMENTATION_TRACKER.json").write_text(
                "{corrupt", encoding="utf-8"
            )
            obj = suite("abacus_v21_dry_run_tests", "DryRunTestSuite")
            self.assertFalse(obj.test_dry_run_dow_workflows())
            self.assertEqual(obj.failed, 1)

    def test_bridge_missing_both_inputs_fails_closed(self):
        with workspace():
            obj = suite("abacus_v21_bridge_validation_tests", "BridgeValidationSuite")
            self.assertFalse(obj.test_dmaic_dow_bridge())
            self.assertEqual(obj.failed, 1)
            self.assertEqual(obj.results[-1]["status"], "FAIL")

    def test_bridge_synthetic_single_of_five_connections_not_five(self):
        with workspace() as root:
            parent = root / "DMAIC_V3_OUTPUT"
            (parent / "Define").mkdir(parents=True)
            (root / "DOW_IMPLEMENTATION_TRACKER.json").write_text(
                '{"stages":{"SYNTHETIC":{"state":"test-only"}}}', encoding="utf-8"
            )
            obj = suite("abacus_v21_bridge_validation_tests", "BridgeValidationSuite")
            self.assertTrue(obj.test_dmaic_dow_bridge())
            self.assertEqual(obj.results[-1]["connections"], 1)
            self.assertEqual(obj.results[-1]["bridge_score"], 20.0)
            self.assertNotIn("qps_owner_acceptance", obj.results[-1])

    def test_bridge_empty_stages_are_not_a_real_bridge(self):
        with workspace() as root:
            parent = root / "DMAIC_V3_OUTPUT"
            (parent / "Define").mkdir(parents=True)
            (root / "DOW_IMPLEMENTATION_TRACKER.json").write_text(
                '{"stages":{}}', encoding="utf-8"
            )
            obj = suite("abacus_v21_bridge_validation_tests", "BridgeValidationSuite")
            self.assertTrue(obj.test_dmaic_dow_bridge())
            self.assertEqual(obj.results[-1]["connections"], 0)
            self.assertEqual(obj.results[-1]["bridge_score"], 0.0)

    def test_feedback_empty_population_returns_zero_not_false_green(self):
        with workspace():
            obj = suite("abacus_v21_system_feedback", "SystemFeedbackGenerator")
            health = obj.analyze_system_health({})
            self.assertEqual(health["total_tests"], 0)
            self.assertEqual(health["pass_rate"], 0)
            self.assertEqual(health["health_status"], "POOR")
            self.assertEqual(health["stages_completed"], 0)

    def test_feedback_partial_pass_rate_correct(self):
        with workspace():
            obj = suite("abacus_v21_system_feedback", "SystemFeedbackGenerator")
            health = obj.analyze_system_health(
                {
                    "smoke": {"summary": {"total_tests": 3, "passed": 2, "failed": 1}},
                    "bridge": {"summary": {"total_tests": 1, "passed": 1, "failed": 0}},
                }
            )
            self.assertEqual(health["total_tests"], 4)
            self.assertEqual(health["total_passed"], 3)
            self.assertEqual(health["total_failed"], 1)
            self.assertEqual(health["pass_rate"], 75)
            self.assertEqual(health["health_status"], "FAIR")

    def test_feedback_collects_only_present_stage_reports(self):
        with workspace() as root:
            path = root / "ABACUS_V21_SMOKE_TEST_OUTPUT"
            path.mkdir()
            (path / "abacus_v21_smoke_test_report.json").write_text(
                '{"summary":{"total_tests":2,"passed":2}}', encoding="utf-8"
            )
            obj = suite("abacus_v21_system_feedback", "SystemFeedbackGenerator")
            items = obj.collect_test_results()
            self.assertEqual(len(items), 4)
            self.assertEqual(items["stage_1_3_smoke"]["summary"]["passed"], 2)
            self.assertEqual(items["stage_1_4_dry_run"], {})

    def test_feedback_corrupt_json_is_not_claimed_as_zero_failed(self):
        with workspace() as root:
            path = root / "ABACUS_V21_SMOKE_TEST_OUTPUT"
            path.mkdir()
            (path / "abacus_v21_smoke_test_report.json").write_text(
                "{malformed", encoding="utf-8"
            )
            obj = suite("abacus_v21_system_feedback", "SystemFeedbackGenerator")
            with self.assertRaises(json.JSONDecodeError):
                obj.collect_test_results()


if __name__ == "__main__":
    unittest.main()
