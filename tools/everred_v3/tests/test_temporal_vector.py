"""Negative controls for origin-independent EVERRED temporal model."""
import copy
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from temporal_vector import SCHEMA, analyze

A, B, C = ("a" * 40, "b" * 40, "c" * 40)
GATES = {"required_checks": "PASS", "security": "PASS",
         "independent_review": "PASS", "effective_protection": "PASS"}


def metric(sha, n, denominator=11):
    return {"state": "MEASURED", "value": n, "unit": "finding_occurrences",
            "basis": {"scope": "four-files", "config": "ruff-0.17.0",
                      "denominator": denominator},
            "source": {"sha": sha, "run_id": 123, "job_id": 456}}


def state(sha, ordinal, cycle, n):
    return {"repository": "GBOGEB/ABACUS", "sha": sha,
            "revision_ordinal": ordinal, "recovery_cycle": cycle,
            "coordinates": {"ruff": metric(sha, n)}, "admission": dict(GATES)}


def fixture():
    return {"schema": SCHEMA, "origin_ordinal": 10,
            "states": [state(A, 10, 0, 11), state(B, 11, 0, 2),
                       state(C, 12, 1, 0)]}


class TemporalKernel(unittest.TestCase):
    def test_rebasing_preserves_deltas(self):
        p = fixture()
        a = analyze(p)["repositories"]["GBOGEB/ABACUS"]
        p["origin_ordinal"] = -100
        b = analyze(p)["repositories"]["GBOGEB/ABACUS"]
        self.assertEqual(a["deltas"], b["deltas"])
        self.assertEqual([0, 1, 2], [x["k"] for x in a["indices"]])
        self.assertEqual([110, 111, 112], [x["k"] for x in b["indices"]])

    def test_sparse_difference_matrix(self):
        x = analyze(fixture())["repositories"]["GBOGEB/ABACUS"]
        self.assertEqual([-9, -2], [d["coordinates"]["ruff"]["delta"] for d in x["deltas"]])
        self.assertEqual([[0, 0], [0, 1]], [d["cycle_transition"] for d in x["deltas"]])
        self.assertEqual(2, len(x["difference_matrix_sparse"]))

    def test_denominator_mismatch_unknown(self):
        p = fixture()
        p["states"][1]["coordinates"]["ruff"]["basis"]["denominator"] = 12
        x = analyze(p)["repositories"]["GBOGEB/ABACUS"]["deltas"][0]["coordinates"]["ruff"]
        self.assertEqual(("UNKNOWN", None), (x["status"], x["delta"]))

    def test_absent_observation_not_zero(self):
        p = fixture()
        p["states"][1]["coordinates"]["ruff"] = {"state": "UNKNOWN", "value": None}
        x = analyze(p)["repositories"]["GBOGEB/ABACUS"]["deltas"]
        self.assertTrue(all(y["coordinates"]["ruff"]["status"] == "UNKNOWN" for y in x))

    def test_admission_gates_noncompensatory(self):
        p = fixture()
        p["states"][1]["admission"]["security"] = "UNKNOWN"
        x = analyze(p)
        self.assertEqual("HOLD", x["repositories"]["GBOGEB/ABACUS"]["indices"][1]["admission"])
        self.assertFalse(x["merge_authorized"])
        self.assertFalse(x["authority_transfer"])

    def test_forged_sha_rejected(self):
        p = fixture()
        p["states"][1]["coordinates"]["ruff"]["source"]["sha"] = A
        with self.assertRaises(ValueError):
            analyze(p)

    def test_boolean_measurement_rejected(self):
        p = fixture()
        p["states"][1]["coordinates"]["ruff"]["value"] = True
        with self.assertRaises(ValueError):
            analyze(p)

    def test_duplicate_revision_rejected(self):
        p = fixture()
        p["states"][1]["revision_ordinal"] = 10
        with self.assertRaises(ValueError):
            analyze(p)

    def test_cycle_regression_rejected(self):
        p = fixture()
        p["states"][0]["recovery_cycle"] = 5
        with self.assertRaises(ValueError):
            analyze(p)

    def test_independent_repository_clocks(self):
        p = fixture()
        other = state("d" * 40, 10, 0, 99)
        other["repository"] = "GBOGEB/CODEX"
        p["states"].append(other)
        x = analyze(p)["repositories"]
        self.assertEqual([], x["GBOGEB/CODEX"]["deltas"])


if __name__ == "__main__":
    unittest.main()
