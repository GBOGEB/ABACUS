import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from model_readiness import bt_readiness, pca_readiness, reverse_pressure

SHA = "a" * 40


class EmpiricalPreflight(unittest.TestCase):
    def test_pca_valid_geometry_not_fit(self):
        data = {
            "schema": "abacus.everred.pca.panel.v1",
            "source_sha": SHA,
            "columns": ["a", "b"],
            "rows": [
                {"independent_unit": str(i), "values": [i, i * i]} for i in range(32)
            ],
        }
        result = pca_readiness(data)
        self.assertEqual(result["decision"], "FIT_ELIGIBLE_NOT_FITTED")
        self.assertFalse(result["merge_authorized"])
        data["rows"][1]["independent_unit"] = "0"
        self.assertIn("DEPENDENT_OR_DUPLICATED_UNITS", pca_readiness(data)["reasons"])
        data["rows"][1]["values"][1] = float("nan")
        self.assertIn("NONFINITE_OR_INCOMPLETE", pca_readiness(data)["reasons"])

    def test_pca_constant_rejected(self):
        data = {
            "schema": "abacus.everred.pca.panel.v1",
            "source_sha": SHA,
            "columns": ["a", "b"],
            "rows": [{"independent_unit": str(i), "values": [i, 3]} for i in range(32)],
        }
        self.assertIn("CONSTANT_VARIABLE", pca_readiness(data)["reasons"])

    def test_bt_connected_and_separated(self):
        pairs = [
            {
                "winner": "a" if i % 2 else "b",
                "loser": "b" if i % 2 else "a",
                "independent_unit": str(i),
            }
            for i in range(30)
        ]
        data = {
            "schema": "abacus.everred.bt.pairs.v1",
            "source_sha": SHA,
            "items": ["a", "b"],
            "comparisons": pairs,
        }
        self.assertEqual(bt_readiness(data)["decision"], "FIT_ELIGIBLE_NOT_FITTED")
        for pair in pairs:
            pair["winner"], pair["loser"] = "a", "b"
        self.assertIn("WIN_GRAPH_NOT_STRONGLY_CONNECTED", bt_readiness(data)["reasons"])
        pairs[1]["independent_unit"] = "0"
        self.assertIn("NONINDEPENDENT_PAIRS", bt_readiness(data)["reasons"])

    def test_reverse_pressure_known_paths_and_bad_edges(self):
        data = {
            "schema": "abacus.everred.blocking-dag.v1",
            "source_sha": SHA,
            "nodes": [
                {"id": "r", "type": "root", "causal_status": "CONFIRMED"},
                {"id": "g", "type": "gate", "mandatory": True},
            ],
            "edges": [{"from": "r", "to": "g", "causally_supported": True}],
        }
        result = reverse_pressure(data)
        self.assertEqual(result["decision"], "STRUCTURAL_DIAGNOSTIC_ONLY")
        self.assertEqual(result["root_impacts"][0]["reachable_mandatory_gates"], ["g"])
        data["edges"][0]["causally_supported"] = False
        self.assertIn("UNVERIFIED_EDGE", reverse_pressure(data)["reasons"])
        data["edges"][0]["causally_supported"] = True
        data["edges"].append({"from": "g", "to": "r", "causally_supported": True})
        self.assertIn("CYCLE", reverse_pressure(data)["reasons"])


if __name__ == "__main__":
    unittest.main()
