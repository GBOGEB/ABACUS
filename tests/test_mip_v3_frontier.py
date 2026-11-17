"""Synthetic MIP V3 advisory DAG, BT and budget guard tests."""

import importlib.util
import unittest
from pathlib import Path

FILE = Path(__file__).resolve().parents[1] / "tools" / "triage" / "mip_v3_frontier.py"
SPEC = importlib.util.spec_from_file_location("mip_v3_frontier", FILE)
mip = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mip)


def task(name, **changes):
    row = {
        "id": name,
        "state": "pending",
        "kind": "read_only",
        "pool": "cpu",
        "risk": "LOW",
        "depends_on": [],
        "paths": [f"src/{name}.py"],
        "cost_minutes": 10,
        "expected_gain": None,
        "missing_opportunities": None,
        "evidence_ref": None,
    }
    row.update(changes)
    return row


def payload(rows=None, gates=None, pairs=None):
    return {
        "schema": mip.SCHEMA,
        "source_sha": "a" * 40,
        "capacity": {
            "max_workers": 2,
            "budget_minutes": 30,
            "pool_slots": {"cpu": 2},
        },
        "tasks": rows if rows is not None else [task("a"), task("b")],
        "gates": gates if gates is not None else [],
        "comparisons": pairs if pairs is not None else [],
    }


def pair(index, a, b, *, context="matched"):
    return {
        "pair_id": f"pair-{index}",
        "winner": a,
        "loser": b,
        "status": "NATIVE_MATCHED",
        "metric_id": "root-closures-per-hour",
        "cohort_id": context,
    }


class FrontierTest(unittest.TestCase):
    def test_ready_respects_hard_dependency(self):
        rows = [task("a", state="done"), task("b", depends_on=["a"])]
        out = mip.plan(payload(rows))
        self.assertEqual(out["ready_frontier"], ["b"])
        self.assertEqual(out["topological_order"], ["a", "b"])

    def test_unmet_dependency_is_not_ranking(self):
        rows = [task("a"), task("b", depends_on=["a"])]
        out = mip.plan(payload(rows))
        self.assertEqual(out["ready_frontier"], ["a"])
        self.assertEqual(out["not_ready_reasons"]["b"], "UPSTREAM_UNVERIFIED")

    def test_reverse_pressure_p0_over_p1(self):
        rows = [task("a"), task("b"), task("c")]
        gates = [
            {"id": "security", "criticality": "P0", "requires": ["b"]},
            {"id": "doc", "criticality": "P1", "requires": ["a"]},
        ]
        out = mip.plan(payload(rows, gates))
        self.assertEqual(out["rankings"]["reverse_pressure"][0], "b")
        self.assertEqual(out["reverse_pressure_scores"]["b"]["immediate"]["P0"], 1)

    def test_partial_unblock_not_full_credit(self):
        rows = [task("a"), task("b")]
        gates = [{"id": "security", "criticality": "P0", "requires": ["a", "b"]}]
        out = mip.plan(payload(rows, gates))
        self.assertEqual(out["reverse_pressure_scores"]["a"]["immediate"]["P0"], 0)
        self.assertEqual(out["reverse_pressure_scores"]["a"]["partial"]["P0"], 1)

    def test_cycle_rejected(self):
        rows = [task("a", depends_on=["b"]), task("b", depends_on=["a"])]
        with self.assertRaisesRegex(ValueError, "cyclic"):
            mip.plan(payload(rows))

    def test_done_with_unfinished_parent_rejected(self):
        rows = [task("a"), task("b", state="done", depends_on=["a"])]
        with self.assertRaisesRegex(ValueError, "inconsistent done"):
            mip.plan(payload(rows))

    def test_mutation_never_dispatched(self):
        rows = [task("a", kind="mutation"), task("b", kind="approval")]
        out = mip.plan(payload(rows))
        self.assertEqual(out["ready_frontier"], [])
        self.assertFalse(out["mutation_authorized"])

    def test_parent_child_lease_overlap(self):
        rows = [task("a", paths=["src"]), task("b", paths=["src/b.py"])]
        out = mip.plan(payload(rows))
        self.assertEqual(len(out["selected_read_only_proposals"]["selected"]), 1)
        self.assertEqual(
            out["selected_read_only_proposals"]["reasons"]["b"],
            "DISJOINT_LEASE_CONFLICT",
        )

    def test_unknown_cost_never_free_capacity(self):
        rows = [task("a", cost_minutes=None), task("b")]
        out = mip.plan(payload(rows))
        self.assertEqual(out["selected_read_only_proposals"]["selected"], ["b"])
        self.assertEqual(
            out["selected_read_only_proposals"]["reasons"]["a"],
            "DEFER_UNKNOWN_COST",
        )

    def test_budget_keeps_capacity_bound(self):
        rows = [task("a", cost_minutes=20), task("b", cost_minutes=20)]
        out = mip.plan(payload(rows))
        self.assertEqual(len(out["selected_read_only_proposals"]["selected"]), 1)
        self.assertEqual(out["selected_read_only_proposals"]["estimated_minutes"], 20)

    def test_bt_unobserved_falls_back(self):
        out = mip.plan(payload([task("a"), task("b"), task("c")]))
        self.assertIsNone(out["rankings"]["bt"])
        self.assertTrue(out["bt"]["status"].startswith("BT_"))

    def test_bt_matched_cyclic_panel(self):
        rows = [task("a"), task("b"), task("c")]
        pairs = [
            pair(1, "a", "b"),
            pair(2, "b", "a"),
            pair(3, "b", "c"),
            pair(4, "c", "b"),
            pair(5, "c", "a"),
            pair(6, "a", "c"),
        ]
        out = mip.plan(payload(rows, pairs=pairs))
        self.assertEqual(out["bt"]["status"], "BT_FITTED_DESCRIPTIVE_NOT_AUTHENTICATED")
        self.assertEqual(set(out["rankings"]["bt"]), {"a", "b", "c"})

    def test_bt_separated_panel_stays_unknown(self):
        rows = [task("a"), task("b"), task("c")]
        pairs = [
            pair(1, "a", "b"),
            pair(2, "a", "b"),
            pair(3, "a", "c"),
            pair(4, "b", "c"),
            pair(5, "a", "b"),
            pair(6, "b", "c"),
        ]
        out = mip.plan(payload(rows, pairs=pairs))
        self.assertEqual(out["bt"]["status"], "BT_UNIDENTIFIABLE_SEPARATION")

    def test_bt_mixed_cohort_rejected(self):
        rows = [task("a"), task("b"), task("c")]
        pairs = [
            pair(1, "a", "b"),
            pair(2, "b", "a"),
            pair(3, "b", "c"),
            pair(4, "c", "b", context="other"),
            pair(5, "c", "a"),
            pair(6, "a", "c"),
        ]
        out = mip.plan(payload(rows, pairs=pairs))
        self.assertEqual(out["bt"]["status"], "BT_MIXED_OR_MISSING_CONTEXT")

    def test_size_cap_not_expected_gain(self):
        rows = [
            task("a", missing_opportunities=100, expected_gain=None),
            task("b", missing_opportunities=10, expected_gain=2),
        ]
        out = mip.plan(payload(rows))
        self.assertEqual(out["rankings"]["size_cap_only"][0], "a")
        self.assertIsNone(out["reverse_pressure_scores"]["a"]["efficiency"])

    def test_unknown_governance_stays_hold(self):
        out = mip.plan(payload())
        self.assertFalse(out["dispatch_authorized"])
        self.assertEqual(out["merge_admission"], "HOLD")


class FrontierLeaseAdversarialTest(unittest.TestCase):
    def test_casefolded_exact_file_alias_not_parallel(self):
        rows = [
            task("a", paths=["SRC/One.py"]),
            task("b", paths=["src/oNE.PY"]),
        ]
        result = mip.plan(payload(rows))["selected_read_only_proposals"]
        self.assertEqual(result["selected"], ["a"])
        self.assertEqual(result["reasons"]["b"], "DISJOINT_LEASE_CONFLICT")

    def test_casefolded_parent_child_prefix_not_parallel(self):
        rows = [
            task("a", paths=["SRC"]),
            task("b", paths=["src/module/file.py"]),
        ]
        result = mip.plan(payload(rows))["selected_read_only_proposals"]
        self.assertEqual(result["selected"], ["a"])
        self.assertEqual(result["reasons"]["b"], "DISJOINT_LEASE_CONFLICT")

    def test_reverse_casefolded_parent_child_prefix_not_parallel(self):
        rows = [
            task("a", paths=["src/module/file.py"]),
            task("b", paths=["SRC"]),
        ]
        result = mip.plan(payload(rows))["selected_read_only_proposals"]
        self.assertEqual(result["selected"], ["a"])
        self.assertEqual(result["reasons"]["b"], "DISJOINT_LEASE_CONFLICT")

    def test_prefix_boundary_keeps_distinct_paths_parallel(self):
        rows = [
            task("a", paths=["src/tool"]),
            task("b", paths=["src/toolkit"]),
        ]
        result = mip.plan(payload(rows))["selected_read_only_proposals"]
        self.assertEqual(result["selected"], ["a", "b"])

    def test_control_chars_cannot_inject_a_lease_name(self):
        candidates = (
            "src/\x00bad.py",
            "src/\nnewline.py",
            "src/\rreturn.py",
            "src/\tsecret.py",
            "src/\x7fdel.py",
            "src/../outside.py",
            "C:/Windows/system32",
            "src//alias",
            "src/./alias",
            "src\\windows.py",
        )
        for claim in candidates:
            with self.subTest(path=repr(claim)):
                with self.assertRaisesRegex(ValueError, "unsafe path claim"):
                    mip.plan(payload([task("a", paths=[claim])]))

    def test_collision_cannot_be_evaded_by_separate_worker_pool(self):
        rows = [
            task("a", paths=["SRC/main.py"], pool="cpu"),
            task("b", paths=["src/MAIN.PY"], pool="io"),
        ]
        value = payload(rows)
        value["capacity"]["pool_slots"]["io"] = 1
        result = mip.plan(value)["selected_read_only_proposals"]
        self.assertEqual(result["selected"], ["a"])
        self.assertEqual(result["reasons"]["b"], "DISJOINT_LEASE_CONFLICT")

    def test_reverse_alias_changes_candidate_to_conflict(self):
        control = mip.plan(
            payload(
                [
                    task("a", paths=["src/one"]),
                    task("b", paths=["docs/two"]),
                ]
            )
        )
        adversarial = mip.plan(
            payload(
                [
                    task("a", paths=["src/one"]),
                    task("b", paths=["SRC"]),
                ]
            )
        )
        self.assertEqual(
            control["selected_read_only_proposals"]["selected"], ["a", "b"]
        )
        self.assertEqual(adversarial["selected_read_only_proposals"]["selected"], ["a"])

    def test_lexical_proposal_cannot_claim_actual_worker_dispatch(self):
        doc = payload([task("a"), task("b")])
        result = mip.plan(doc)
        self.assertEqual(
            result["path_lease_model"],
            "CASEFOLDED_LEXICAL_PLAN_NOT_AUTHENTICATED",
        )
        self.assertFalse(result["dispatch_authorized"])
        self.assertFalse(result["mutation_authorized"])
        self.assertEqual(result["merge_admission"], "HOLD")


if __name__ == "__main__":
    unittest.main()
