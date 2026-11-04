"""Targeted fail-closed edge coverage for the V2 handover core.

This is a stacked test-only change. It grants no admission or merge authority.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "handover_v2_edge_core", ROOT / "tools/handover_v2/build_handover.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("V2 core module is unavailable")
core = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(core)


class TestHandoverV2FailClosedEdges(unittest.TestCase):
    def test_markdown_cell_escaping(self):
        self.assertEqual(core.safe_md("A|B\nC"), "A\\|B C")

    def test_safe_relative_path_and_malformed_paths(self):
        self.assertEqual(str(core.valid_relpath("raw/source.txt")), "raw/source.txt")
        for unsafe in ("raw\\source.txt", "raw//source.txt", "raw/x\x00.txt"):
            with self.subTest(path=repr(unsafe)):
                with self.assertRaisesRegex(ValueError, "Unsafe archive path"):
                    core.valid_relpath(unsafe)

    def test_duplicate_ids_fail_closed(self):
        rows = [{"id": "A"}, {"id": "A"}]
        with self.assertRaisesRegex(ValueError, "Duplicate task ID"):
            core.must_unique(rows, "task")
        self.assertEqual(core.must_unique([{"id": "A"}], "task"), {"A": {"id": "A"}})

    def test_dependency_graph_accepts_valid_order_and_repeated_ancestor(self):
        actions = {
            "A": {"id": "A", "order": 1, "depends_on": []},
            "B": {"id": "B", "order": 2, "depends_on": ["A"]},
            "C": {"id": "C", "order": 3, "depends_on": ["A"]},
            "D": {"id": "D", "order": 4, "depends_on": ["B", "C"]},
        }
        self.assertIsNone(core.validate_graph(actions))

    def test_unknown_dependency_rejected(self):
        actions = {"A": {"id": "A", "order": 1, "depends_on": ["missing"]}}
        with self.assertRaisesRegex(ValueError, "unknown dependency"):
            core.validate_graph(actions)

    def test_duplicate_action_order_rejected(self):
        actions = {
            "A": {"id": "A", "order": 1, "depends_on": []},
            "B": {"id": "B", "order": 1, "depends_on": []},
        }
        with self.assertRaisesRegex(ValueError, "Duplicate action order"):
            core.validate_graph(actions)

    def test_backward_dependency_order_rejected(self):
        actions = {
            "A": {"id": "A", "order": 2, "depends_on": []},
            "B": {"id": "B", "order": 1, "depends_on": ["A"]},
        }
        with self.assertRaisesRegex(ValueError, "Dependency cannot run after"):
            core.validate_graph(actions)

    def test_required_gate_and_protection_fail_closed(self):
        authority = {
            "merge_decision": "APPROVED",
            "effective_branch_protection": "UNKNOWN",
            "independent_approval": "ESTABLISHED",
        }
        gates = {"native": {"required_for_admission": True, "status": "PASS"}}
        with self.assertRaisesRegex(ValueError, "Admission cannot proceed"):
            core.validate_admission_gates(authority, gates)
        authority["effective_branch_protection"] = "EFFECTIVE"
        gates["native"]["status"] = "PENDING"
        with self.assertRaisesRegex(ValueError, "required PASS gates"):
            core.validate_admission_gates(authority, gates)


if __name__ == "__main__":
    unittest.main()
