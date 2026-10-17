"""Fail-closed tests for the read-only B-family objective registry."""
import json
import pathlib
import unittest

REGISTRY = pathlib.Path(__file__).resolve().parents[1] / "config" / "metric_hierarchy_registry.json"


class MetricHierarchyRegistry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_namespaces_are_unique_and_explicit(self):
        ids = [row["id"] for row in self.doc["b_family"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("MIP.B1", ids)
        self.assertIn("BANDIT.B1", ids)
        self.assertNotIn("MIP.B2", ids)

    def test_child_reuse_does_not_become_independent_credit(self):
        b1 = next(row for row in self.doc["b_family"] if row["id"] == "MIP.B1")
        self.assertEqual(b1["parent"], "MIP.B0")
        self.assertIn(["MIP.B0", "MIP.B1"], self.doc["rollup_rules"]["forbidden_overlap"])

    def test_objective_weights_sum_one_and_are_diagnostic(self):
        for objective in self.doc["objectives"]:
            self.assertAlmostEqual(sum(objective["weights"].values()), 1.0)
            self.assertEqual(objective["status"], "UNSCORED")
            self.assertTrue(objective["hard_gates"])

    def test_historical_bandit_partition_reconciles(self):
        b = self.doc["historical_bandit"]
        self.assertEqual(sum(b["full_lanes"].values()), b["full_findings"])
        self.assertNotEqual(b["configured_findings"], b["full_findings"])

    def test_native_run_and_worker_credit_separated(self):
        sample = self.doc["observed_sample"]
        self.assertEqual((sample["b0_success"], sample["b0_observed_runs"]), (13, 14))
        self.assertEqual((sample["b0_jobs_success"], sample["b0_jobs_total"]), (180, 182))
        self.assertIsNone(self.doc["current"]["authenticated_Crew_launches"])

    def test_hard_gates_and_authority_are_never_waived(self):
        self.assertEqual(self.doc["merge_admission"], "HOLD")
        self.assertIs(self.doc["authority_transfer"], False)
        self.assertIs(self.doc["security_waiver"], False)
        self.assertIsNone(self.doc["current"]["accepted_main_coverage_delta"])
        self.assertIsNone(self.doc["current"]["formal_roots_closed"])


if __name__ == "__main__":
    unittest.main()
