"""Smoke and fail-closed tests for standalone V2 protocol."""
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("handover_v2_core", HERE / "build_handover.py")
core = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(core)


class HandoverV2Smoke(unittest.TestCase):
    def test_known_digest(self):
        self.assertEqual(core.sha256(b"abc"),
                         "ba7816bf8f01cfea414140de5dae2223b00361a"
                         "396177a9cb410ff61f20015ad")

    def test_canonical_order_deterministic(self):
        self.assertEqual(core.canonical({"b": 2, "a": 1}),
                         core.canonical({"a": 1, "b": 2}))

    def test_unsafe_parent_path(self):
        with self.assertRaises(ValueError):
            core.valid_relpath("raw/../private.txt")

    def test_absolute_path(self):
        with self.assertRaises(ValueError):
            core.valid_relpath("/etc/passwd")

    def test_missing_path_prefix(self):
        with self.assertRaises(ValueError):
            core.valid_relpath("file.txt")

    def test_action_cycle_rejected(self):
        actions = {
            "A": {"order": 1, "depends_on": ["B"]},
            "B": {"order": 2, "depends_on": ["A"]},
        }
        with self.assertRaises(ValueError):
            core.validate_graph(actions)

    def test_comparability_rejects_changed_test_selection(self):
        def metric(selection, source):
            return {
                "id": "coverage", "state": "MEASURED",
                "measure_type": "RATIO",
                "numerator": 8, "denominator": 10,
                "basis": {
                    "scope_id": "sample", "paths": ["source.py"],
                    "unit_definition": "statements",
                    "instrumentor": "coverage.py",
                    "instrumentor_version": "7.16.2",
                    "configuration_sha256": "a" * 64,
                    "selection": selection,
                },
            }
        old = metric("tests/test_a.py", "a" * 40)
        new = metric("tests/test_b.py", "b" * 40)
        comparison = core.comparability(old, new, "coverage", "C1")
        self.assertEqual(comparison["status"], "INELIGIBLE")
        self.assertIn("Different selection", comparison["reasons"])
        self.assertIsNone(comparison["delta_percentage_points"])
        new["basis"]["selection"] = old["basis"]["selection"]
        self.assertEqual(
            core.comparability(old, new, "coverage", "C1")["status"], "COMPARABLE")

    def test_noncausal_pct(self):
        self.assertEqual(core.pct(49, 50), "98.00%")

    def test_admission_rejects_empty_required_gate_set(self):
        authority = {"merge_decision": "APPROVED",
                     "effective_branch_protection": "EFFECTIVE",
                     "independent_approval": "ESTABLISHED"}
        for gates in ({}, {"optional": {"required_for_admission": False,
                                       "status": "PASS"}}):
            with self.subTest(gates=gates):
                with self.assertRaisesRegex(ValueError, "at least one required gate"):
                    core.validate_admission_gates(authority, gates)
        core.validate_admission_gates(authority, {
            "native": {"required_for_admission": True, "status": "PASS"}})
        with self.assertRaisesRegex(ValueError, "required PASS gates"):
            core.validate_admission_gates(authority, {
                "native": {"required_for_admission": True, "status": "FAIL"}})
        authority["merge_decision"] = "HOLD"
        core.validate_admission_gates(authority, {})


if __name__ == "__main__":
    unittest.main()


def test_zz_g_ab_red_canary():
    """Throwaway red canary (method vector D); never merge."""
    assert False
