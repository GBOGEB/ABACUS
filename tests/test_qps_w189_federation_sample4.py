import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "controls/QPS_W189_FEDERATION_SAMPLE4_CURRENT_v1.json"
MATRIX = ROOT / "triage/w189/QPS_W189_CROSS_SURFACE_FEATURE_MATRIX_v0.1.json"
PAIRWISE = ROOT / "triage/w189/QPS_W189_PAIRWISE_DISPOSITION_LEDGER_v0.1.json"
CENSUS = ROOT / "triage/w189/QPS_W189_FEDERATION_FLEET_CENSUS_v0.1.json"


class TestW189FederationSample4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.control = json.loads(CONTROL.read_text())
        cls.matrix = json.loads(MATRIX.read_text())
        cls.pairwise = json.loads(PAIRWISE.read_text())
        cls.census = json.loads(CENSUS.read_text())

    def test_namespace_collision_guard(self):
        self.assertTrue(self.control["namespace"]["w188"].startswith("OCCUPIED_"))
        self.assertEqual(self.control["wave"], "W189")

    def test_real_repaired_runtime(self):
        v = self.control["observed_runtime"]["exact_hash_mirror_pass"]
        self.assertEqual(v["run_id"], 34868622367)
        self.assertGreater(v["runner_id"], 0)
        self.assertEqual(v["result"], "PASS")

    def test_sample4_is_candidate_not_accepted(self):
        self.assertEqual(sum(r["accepted_sample"] for r in self.matrix["rows"]), 3)
        s4 = next(r for r in self.matrix["rows"] if r["sample_id"] == "FED-SAMPLE-004-W184F-N200-MIRROR")
        self.assertEqual(s4["accepted_sample"], 0)
        self.assertEqual(s4["depth_ratio"], 0.875)

    def test_pca_stability_is_partial_and_withheld(self):
        s = self.matrix["candidate_n4_stability"]
        self.assertGreater(s["pc1_loading_congruence_abs"], 0.99)
        self.assertLess(s["pc2_loading_congruence_abs"], 0.20)
        self.assertTrue(s["state"].startswith("COMPUTABLE_WITHHELD_"))

    def test_repeated_transport_bt_component(self):
        c = self.pairwise["bt_gate"]["repeated_comparable_component"]
        self.assertEqual(c["observed_comparisons"], 2)
        self.assertTrue(c["graph_connected"])
        self.assertEqual(c["unregularized_mle_state"], "SEPARATED_2_TO_0_NO_FINITE_MLE")
        self.assertTrue(c["fit_state"].startswith("WITHHELD_"))

    def test_global_bt_still_withheld(self):
        self.assertFalse(self.pairwise["bt_gate"]["global_connected_comparison_graph"])
        self.assertTrue(self.pairwise["bt_gate"]["global_fit_state"].startswith("WITHHELD_"))

    def test_fleet_denominators_remain_null(self):
        d = self.census["denominator_model"]
        self.assertIsNone(d["accessible_repository_universe"]["value"])
        self.assertIsNone(d["mission_relevant_governed_surface_universe"]["value"])

    def test_zero_formal_credit(self):
        self.assertTrue(all(v == 0 for v in self.control["formal_credit_delta"].values()))

    def test_validator_and_pca(self):
        v = subprocess.run([sys.executable, str(ROOT / "scripts/qps_w189_validate_federation_sample4.py")], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(v.returncode, 0, v.stdout + v.stderr)
        p = subprocess.run([sys.executable, str(ROOT / "scripts/qps_w189_compute_pca_stability.py")], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()
