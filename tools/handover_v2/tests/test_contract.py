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

    def test_noncausal_pct(self):
        self.assertEqual(core.pct(49, 50), "98.00%")


if __name__ == "__main__":
    unittest.main()
