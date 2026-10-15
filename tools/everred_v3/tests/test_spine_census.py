"""Coverage pie growth, source provenance and negative controls."""

import copy
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

import spine_census as spine

A = "a" * 40
B = "b" * 40
X = "a" * 64


def coverage(sha, statements, missing_s, branches, missing_b):
    identity = {
        "repository": "GBOGEB/ABACUS",
        "sha": sha,
        "run_id": 100,
        "artifact_id": 200,
        "artifact_sha256": X,
        "workflow_sha256": X,
        "config_sha256": X,
    }
    data = {
        "meta": {"version": "7.16.2"},
        "files": {
            "scripts/test.py": {
                "summary": {
                    "num_statements": statements,
                    "missing_lines": missing_s,
                    "num_branches": branches,
                    "missing_branches": missing_b,
                }
            }
        },
    }
    receipt = {
        "schema": "bandit.coverage.receipt.v1",
        "exact_head_sha": sha,
        "producer_run_id": "100",
        "tests": 101,
        "failures": 0,
        "errors": 0,
        "source_scope": ["scripts/test.py"],
        "selected_modules_totals": {
            "covered_lines": statements - missing_s,
            "eligible_lines": statements,
            "covered_branches": branches - missing_b,
            "eligible_branches": branches,
        },
    }
    return spine.coverage_snapshot(data, receipt, identity)


class SpineCensusTests(unittest.TestCase):
    def test_denominator_growth_cannot_fake_old_debt_closure(self):
        old = coverage(A, 94, 26, 46, 11)
        new = coverage(B, 98, 1, 50, 1)
        delta = spine.compare_coverage(old, new)
        branch = delta["families"]["branches"]
        self.assertEqual("SOURCE_DENOMINATOR_EVOLVED", delta["status"])
        self.assertEqual(branch["eligible_net_delta"], 4)
        self.assertEqual(branch["covered_net_delta"], 14)
        self.assertEqual(branch["uncovered_net_delta"], -10)
        self.assertIsNone(branch["previously_uncovered_now_covered"])
        self.assertFalse(delta["causal_coverage_gain_credited"])
        self.assertEqual(branch["additional_covered_for_goal"], 0)

    def test_new_branches_can_reduce_coverage_percentage(self):
        before = coverage(A, 50, 0, 10, 0)
        after = coverage(B, 70, 5, 20, 8)
        result = spine.compare_coverage(before, after)
        self.assertEqual(result["families"]["branches"]["eligible_net_delta"], 10)
        self.assertEqual(result["families"]["branches"]["after_pct"], 60)
        self.assertEqual(
            result["families"]["branches"]["additional_covered_for_goal"], 6
        )

    def test_profile_change_is_descriptive_only(self):
        old = coverage(A, 94, 26, 46, 11)
        new = coverage(B, 98, 1, 50, 1)
        new["source"]["config_sha256"] = "b" * 64
        self.assertEqual(
            spine.compare_coverage(old, new)["status"],
            "PROFILE_CHANGED_DESCRIPTIVE_ONLY",
        )

    def test_same_source_numeric_drift_is_not_stability(self):
        old = coverage(A, 94, 26, 46, 11)
        new = coverage(A, 94, 25, 46, 11)
        self.assertEqual(
            spine.compare_coverage(old, new)["status"],
            "SAME_SOURCE_METRIC_DRIFT",
        )

    def test_invalid_scope_and_mismatched_native_sha_rejected(self):
        item = coverage(A, 94, 26, 46, 11)
        self.assertEqual(item["source"]["sha"], A)
        d = {
            "meta": {"version": "7.16.2"},
            "files": {
                "scripts/test.py": {
                    "summary": {
                        "num_statements": 10,
                        "missing_lines": 0,
                        "num_branches": 2,
                        "missing_branches": 0,
                    }
                }
            },
        }
        r = {
            "schema": "bandit.coverage.receipt.v1",
            "exact_head_sha": B,
            "producer_run_id": "100",
        }
        with self.assertRaisesRegex(ValueError, "head differs"):
            spine.coverage_snapshot(d, r, item["source"])

    def test_boolean_covered_and_missing_counts_rejected(self):
        item = coverage(A, 94, 26, 46, 11)
        item["totals"]["branches"]["covered"] = True
        with self.assertRaisesRegex(ValueError, "coverage family"):
            spine.compare_coverage(item, item)

    def test_ldab_discovery_never_becomes_runtime(self):
        report = {
            "repository": "GBOGEB/ABACUS",
            "head_sha": A,
            "verification": "PASS",
            "ldab_telemetry": {
                "schema": "mip.ldab.telemetry.v1",
                "repository": "GBOGEB/ABACUS",
                "source_sha": A,
                "source_census": {
                    "root": {
                        "candidate_file_count": 13,
                        "inventory_complete": True,
                        "evidence_level": "SOURCE_DISCOVERY_ONLY",
                    }
                },
                "runtime": {
                    "abacus_native_debug_sessions": None,
                    "authenticated_port_leases": None,
                    "ldab_verified_repairs": None,
                },
            },
        }
        x = spine.ldab_snapshot(report, "GBOGEB/ABACUS", A, artifact_sha256=X)
        self.assertIsNone(x["native_debug_sessions"])
        self.assertEqual(x["root_candidate_files"], 13)
        with self.assertRaisesRegex(ValueError, "stale"):
            spine.ldab_snapshot(report, "GBOGEB/ABACUS", B, artifact_sha256=X)
        forged = copy.deepcopy(report)
        forged["ldab_telemetry"]["runtime"]["abacus_native_debug_sessions"] = 3
        with self.assertRaisesRegex(ValueError, "source discovery"):
            spine.ldab_snapshot(forged, "GBOGEB/ABACUS", A, artifact_sha256=X)

    def test_n_plus_one_stability_requires_identical_observed_state(self):
        original = {
            "schema": spine.SCHEMA,
            "repository": "GBOGEB/ABACUS",
            "observed_at": "2026-10-15T00:00:00Z",
            "main_sha": A,
            "inventory_complete": True,
            "active_heads": [{"number": 1990, "sha": B}],
            "observations": [{"id": 1, "status": "completed"}],
        }
        next_read = copy.deepcopy(original)
        next_read["observed_at"] = "2026-10-15T01:00:00Z"
        self.assertEqual(
            spine.state_fingerprint(original), spine.state_fingerprint(next_read)
        )
        self.assertEqual(
            spine.compare_pulses(original, next_read)["state"],
            "N_PLUS_1_EQUALS_N_OBSERVED_STATE",
        )
        next_read["observations"][0]["status"] = "failure"
        self.assertEqual(
            spine.compare_pulses(original, next_read)["state"],
            "SAME_HEADS_EVIDENCE_CHANGED",
        )
        next_read["active_heads"][0]["sha"] = A
        self.assertEqual(
            spine.compare_pulses(original, next_read)["state"],
            "SOURCE_REVISION_OR_PR_SET_CHANGED",
        )

    def test_new_observer_receipt_is_not_a_source_change(self):
        old = {
            "schema": spine.SCHEMA,
            "repository": "GBOGEB/ABACUS",
            "main_sha": A,
            "inventory_complete": True,
            "active_heads": [{"number": 99, "sha": B}],
            "observations": [
                {
                    "pr_number": 99,
                    "source_sha": B,
                    "ci": {
                        "current_window_complete": True,
                        "matched_runs": [
                            {
                                "id": 10,
                                "name": "Full CI",
                                "event": "pull_request",
                                "status": "completed",
                                "conclusion": "success",
                            },
                            {
                                "id": 11,
                                "name": "EVERRED V3 Governed Control Plane",
                                "event": "pull_request",
                                "status": "completed",
                                "conclusion": "success",
                            },
                        ],
                    },
                    "producers": {
                        "coverage": {
                            **coverage(B, 98, 1, 50, 1),
                            "workflow_conclusion": "success",
                        },
                        "ldab": {
                            "state": "UNKNOWN_NO_EXACT_HEAD_LDAB",
                            "source_sha": B,
                        },
                    },
                }
            ],
        }
        new = copy.deepcopy(old)
        new["observations"][0]["ci"]["matched_runs"][0]["id"] = 20
        new["observations"][0]["ci"]["matched_runs"][1]["id"] = 21
        new["observations"][0]["producers"]["coverage"]["source"]["artifact_id"] = 22
        result = spine.compare_pulses(old, new)
        self.assertEqual(result["state"], "N_PLUS_1_EQUALS_N_OBSERVED_STATE")
        self.assertFalse(result["material_state_changed"])
        self.assertTrue(result["new_evidence_receipts"])
        self.assertFalse(result["full_history_claim"])
        new["observations"][0]["ci"]["matched_runs"][0]["conclusion"] = "failure"
        self.assertEqual(
            spine.compare_pulses(old, new)["state"],
            "SAME_HEADS_EVIDENCE_CHANGED",
        )
        new = copy.deepcopy(old)
        new["observations"][0]["producers"]["coverage"]["totals"]["branches"][
            "eligible"
        ] += 1
        self.assertEqual(
            spine.compare_pulses(old, new)["state"],
            "SAME_HEADS_EVIDENCE_CHANGED",
        )

    def test_incomplete_inventory_does_not_assert_stability(self):
        original = {
            "schema": spine.SCHEMA,
            "repository": "GBOGEB/ABACUS",
            "main_sha": A,
            "inventory_complete": False,
        }
        with self.assertRaisesRegex(ValueError, "incomplete inventory"):
            spine.compare_pulses(original, original)


if __name__ == "__main__":
    unittest.main()
