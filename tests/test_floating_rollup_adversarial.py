"""Negative and reverse pulse controls; fixtures never native attestation."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.triage import mip_pulse_rollup as model
from tests.test_mip_pulse_rollup import receipt


def measured(value):
    with tempfile.TemporaryDirectory() as directory:
        p = Path(directory) / "pulse.json"
        p.write_text(json.dumps(value), encoding="utf-8")
        return model.read_pulse(p)


class AdditionalPulseGuards(unittest.TestCase):
    def test_read_exact_receipt_retains_unknown_authority(self):
        value = measured(receipt(0))
        self.assertEqual(value["head_sha"], "a" * 40)
        self.assertIsNone(value.get("native"))
        self.assertEqual(value["governance"]["merge_admission"], "HOLD")

    def test_rejects_invalid_schema_and_unverifiable_sources(self):
        changes = [
            lambda x: x.update(schema="unknown"),
            lambda x: x.update(repository="GBOGEB/CODEX"),
            lambda x: x.update(head_sha="short"),
            lambda x: x.update(population_sha256="0"),
            lambda x: x.update(instrumentation_sha256="0"),
            lambda x: x.update(observed_at="not UTC"),
            lambda x: x.update(root_reds_open=-1),
        ]
        for index, change in enumerate(changes):
            with self.subTest(index=index):
                p = receipt(0)
                change(p)
                with self.assertRaises(ValueError):
                    measured(p)

    def test_coverage_counts_fail_closed(self):
        invalid = [
            (True, 100), (-1, 100), (101, 100), (0, True),
        ]
        for covered, eligible in invalid:
            with self.subTest(covered=covered, eligible=eligible):
                r = receipt(0)
                r["coverage"]["statements"] = {
                    "covered": covered, "eligible": eligible
                }
                with self.assertRaises(ValueError):
                    measured(r)

    def test_disjoint_workers_reject_parent_child_paths(self):
        r = receipt(0)
        r["workers"] = [
            {"owner": "alpha", "paths": ["src"], "queue_seconds": 1},
            {"owner": "beta", "paths": ["src/submodule.py"],
             "execution_seconds": 1},
        ]
        with self.assertRaisesRegex(ValueError, "overlapping"):
            measured(r)

    def test_disjoint_workers_reject_unsafe_platform_paths(self):
        for path in ("../secrets", "src/./a.py", "C:/secret",
                     "src\\windows.py", "src//a.py", "/etc/shadow"):
            with self.subTest(path=path):
                r = receipt(0)
                r["workers"][0]["paths"] = [path]
                with self.assertRaisesRegex(ValueError, "unsafe path"):
                    measured(r)

    def test_duplicate_owner_and_nonfinite_effort_fails(self):
        r = receipt(0)
        r["workers"].append({"owner": "source-a", "paths": ["else.py"]})
        with self.assertRaisesRegex(ValueError, "duplicate worker owner"):
            measured(r)
        r = receipt(0)
        r["workers"][0]["execution_seconds"] = float("inf")
        with self.assertRaisesRegex(ValueError, "latency"):
            measured(r)

    def test_component_denominator_swap_not_comparable(self):
        a, b = receipt(0), receipt(1)
        b["coverage"]["statements"]["eligible"] = 98
        b["coverage"]["branches"]["eligible"] = 22
        pair = model.transition(a, b)
        self.assertFalse(pair["population_comparable"])
        self.assertIsNone(pair["coverage_gain_pp"])
        self.assertIsNone(pair["statement_gain_pp"])

    def test_branch_regression_cannot_be_masked_by_line_gain(self):
        a, b = receipt(0, covered=10), receipt(1, covered=20)
        a["coverage"]["branches"]["covered"] = 6
        b["coverage"]["branches"]["covered"] = 5
        move = model.transition(a, b)
        self.assertGreater(move["coverage_gain_pp"], 0)
        self.assertLess(move["branch_gain_pp"], 0)
        self.assertEqual(model.rollup([a, b])["control"],
                         "RESTART_COVERAGE_REGRESSION")

    def test_non_saturated_stagnation_is_reranking(self):
        states = [receipt(i) for i in range(4)]
        result = model.rollup(states)
        self.assertEqual(result["control"], "RERANK_UNCOVERED")
        self.assertFalse(result["source_scope_saturated"])
        self.assertFalse(result["phase_two_authorized"])

    def test_saturation_without_native_ids_stays_on_hold(self):
        states = [receipt(i, covered=100) for i in range(4)]
        for item in states:
            item["coverage"]["branches"]["covered"] = 20
        result = model.rollup(states)
        self.assertEqual(result["control"], "HOLD_UNVERIFIED_NATIVE_IDENTITIES")
        self.assertFalse(result["phase_two_authorized"])

    def test_increasing_open_root_reds_restart_before_quiet_watch(self):
        states = [receipt(i, covered=100, roots=i) for i in range(4)]
        for n, item in enumerate(states):
            item["coverage"]["branches"]["covered"] = 20
            item["native"] = {"run_id": 300 + n, "attempt": 1}
        self.assertEqual(model.rollup(states)["control"],
                         "RESTART_ROOT_RED_INCREASE")

    def test_all_four_receipts_require_healthy_terminal_test_outcomes(self):
        states = [receipt(i, covered=100) for i in range(4)]
        for n, item in enumerate(states):
            item["coverage"]["branches"]["covered"] = 20
            item["native"] = {"run_id": 300 + n, "attempt": 1}
        states[0]["tests"]["skipped"] = 1
        states[0]["tests"]["passed"] = 9
        self.assertEqual(model.rollup(states)["control"],
                         "RESTART_SKIPPED_TESTS")
        states[0]["tests"] = {
            "executed": 10, "passed": 10, "failed": 0,
            "errors": 0, "skipped": 0,
        }
        states[0]["terminal"] = False
        self.assertEqual(model.rollup(states)["control"],
                         "HOLD_UNVERIFIED_TEST_OUTCOMES")
        with self.assertRaisesRegex(ValueError, "test outcomes missing"):
            measured({key: value for key, value in receipt(0).items()
                      if key != "tests"})

    def test_native_identities_allow_candidate_not_authority(self):
        states = [receipt(i, covered=100) for i in range(4)]
        for n, item in enumerate(states):
            item["coverage"]["branches"]["covered"] = 20
            item["native"] = {"run_id": 300 + n, "attempt": 1}
        result = model.rollup(states)
        self.assertEqual(result["control"], "QUIET_WATCH_CANDIDATE")
        self.assertTrue(result["native_identities_structurally_present"])
        self.assertFalse(result["native_identities_independently_verified"])
        self.assertFalse(result["release_ready"])
        self.assertFalse(result["phase_two_authorized"])

    def test_repeated_native_attempt_blocks_quiet(self):
        states = [receipt(i, covered=100) for i in range(4)]
        for item in states:
            item["coverage"]["branches"]["covered"] = 20
            item["native"] = {"run_id": 300, "attempt": 1}
        self.assertEqual(model.rollup(states)["control"],
                         "HOLD_UNVERIFIED_NATIVE_IDENTITIES")

    def test_p95_worker_seconds_has_nearest_rank_and_null_unknown(self):
        self.assertIsNone(model.p95([]))
        self.assertEqual(model.p95([1, 2, 3, 20]), 20)
        s = model.snapshot(receipt(0))
        self.assertEqual(s["p95_queue_seconds"], 1)
        self.assertEqual(s["p95_execution_seconds"], 2)
        self.assertEqual(s["triage"]["unknown"], 2)

    def test_cli_keeps_merge_authority_false(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            rows = []
            for i in range(2):
                inp = root / f"pulse{i}.json"
                inp.write_text(json.dumps(receipt(i)), encoding="utf-8")
                rows.append(str(inp))
            path = root / "report.json"
            model.main(rows + ["--out", str(path)])
            result = json.loads(path.read_text())
            self.assertEqual(result["pulse_count"], 2)
            self.assertFalse(result["formal_coverage_credit"])
            self.assertFalse(result["release_ready"])


if __name__ == "__main__":
    unittest.main()
