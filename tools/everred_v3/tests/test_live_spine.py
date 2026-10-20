"""Synthetic GitHub transport tests: current source cannot inherit old green."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import live_spine as observer
from live_spine import collect, coverage_transitions, latest_runs, main_head, open_prs

A = "a" * 40
B = "b" * 40


class FakeReader:
    def __init__(self):
        self.head = A
        self.run = {
            "total_count": 1,
            "workflow_runs": [
                {
                    "id": 18,
                    "head_sha": B,
                    "head_branch": "worker",
                    "name": "smoke-test",
                    "event": "pull_request",
                    "status": "completed",
                    "conclusion": "success",
                    "created_at": "2026-10-15T00:00:00Z",
                    "pull_requests": [{"number": 1994}],
                }
            ],
        }

    def get(self, route):
        if route.endswith("/git/ref/heads/main"):
            return {"object": {"sha": self.head}}
        if "/pulls?" in route:
            return (
                [
                    {
                        "number": 1994,
                        "head": {"sha": B, "ref": "worker"},
                        "base": {"sha": self.head},
                    }
                ]
                if "page=1" in route
                else []
            )
        if "/actions/runs?" in route:
            if "head_sha=" + B in route:
                return self.run
            return {"total_count": 0, "workflow_runs": []}
        raise AssertionError("unexpected read: " + route)


class LiveSpineTests(unittest.TestCase):
    def test_current_api_readback_and_no_inherited_ci(self):
        api = FakeReader()
        self.assertEqual(main_head(api, "GBOGEB/ABACUS"), A)
        self.assertEqual(open_prs(api, "GBOGEB/ABACUS")[0]["sha"], B)
        _, history = latest_runs(api, "GBOGEB/ABACUS", A, branch="main")
        self.assertEqual(history["state"], "UNKNOWN_NO_RUN_AT_HEAD")
        pulse = collect(api, "GBOGEB/ABACUS")
        self.assertEqual(pulse["main_sha"], A)
        self.assertTrue(pulse["inventory_complete"])
        self.assertEqual(len(pulse["active_heads"]), 1)
        self.assertEqual(
            pulse["observations"][0]["producers"]["ldab"]["state"],
            "UNKNOWN_NO_EXACT_HEAD_LDAB",
        )
        self.assertEqual(
            pulse["comparison"]["state"], "FIRST_OBSERVATION_NOT_STABILITY"
        )

    def test_same_current_state_requires_prior_proof(self):
        api = FakeReader()
        previous = collect(api, "GBOGEB/ABACUS")
        next_pulse = collect(api, "GBOGEB/ABACUS", prior=previous)
        self.assertEqual(
            next_pulse["comparison"]["state"],
            "N_PLUS_1_EQUALS_N_OBSERVED_STATE",
        )
        api.run["workflow_runs"][0]["conclusion"] = "failure"
        revised = collect(api, "GBOGEB/ABACUS", prior=previous)
        self.assertEqual(revised["comparison"]["state"], "SAME_HEADS_EVIDENCE_CHANGED")

    def test_main_move_causes_new_revision(self):
        api = FakeReader()
        prior = collect(api, "GBOGEB/ABACUS")
        api.head = B
        current = collect(api, "GBOGEB/ABACUS", prior=prior)
        self.assertEqual(
            current["comparison"]["state"],
            "SOURCE_REVISION_OR_PR_SET_CHANGED",
        )

    def test_history_truncation_is_explicit_and_window_valid(self):
        api = FakeReader()
        api.run["total_count"] = 200
        x = collect(api, "GBOGEB/ABACUS")
        self.assertFalse(x["inventory_complete"])
        self.assertFalse(x["history_census_complete"])
        self.assertFalse(x["observations"][1]["ci"]["current_window_complete"])

    def test_inherited_run_ids_do_not_manufacture_state_change(self):
        api = FakeReader()
        previous = collect(api, "GBOGEB/ABACUS")
        api.run["workflow_runs"][0]["id"] = 91
        current = collect(api, "GBOGEB/ABACUS", prior=previous)
        self.assertEqual(
            current["comparison"]["state"],
            "N_PLUS_1_EQUALS_N_OBSERVED_STATE",
        )
        self.assertTrue(current["comparison"]["new_evidence_receipts"])

    def test_coverage_transitions_include_new_denominator(self):
        from spine_census import SCHEMA

        def metric(sha, covered, eligible, branches, branch_total):
            return {
                "schema": SCHEMA + ".coverage",
                "source": {
                    "repository": "GBOGEB/ABACUS",
                    "sha": sha,
                    "run_id": 42,
                    "artifact_id": 44,
                    "artifact_sha256": "a" * 64,
                    "workflow_sha256": "b" * 64,
                    "config_sha256": "c" * 64,
                },
                "tool_version": "7.16.2",
                "scope": ["scripts/bandit.py"],
                "totals": {
                    "statements": {"covered": covered, "eligible": eligible},
                    "branches": {"covered": branches, "eligible": branch_total},
                },
                "state": "MEASURED_SOURCE_BOUND_NOT_ADMISSION",
            }

        before = {
            "observations": [
                {
                    "pr_number": 99,
                    "source_sha": A,
                    "producers": {
                        "coverage": metric(A, 68, 94, 35, 46),
                    },
                }
            ]
        }
        after = {
            "observations": [
                {
                    "pr_number": 99,
                    "source_sha": B,
                    "producers": {
                        "coverage": metric(B, 97, 98, 49, 50),
                    },
                }
            ]
        }
        delta = coverage_transitions(before, after)
        self.assertEqual(len(delta), 1)
        self.assertEqual(
            delta[0]["measurement"]["status"],
            "SOURCE_DENOMINATOR_EVOLVED",
        )
        self.assertEqual(
            delta[0]["measurement"]["families"]["branches"]["eligible_net_delta"],
            4,
        )
        self.assertFalse(delta[0]["measurement"]["causal_coverage_gain_credited"])

    def test_pr_advance_during_pulse_is_rejected(self):
        class AdvancingReader(FakeReader):
            def __init__(self):
                super().__init__()
                self.pr_reads = 0

            def get(self, route):
                value = super().get(route)
                if "/pulls?" in route:
                    self.pr_reads += 1
                    if self.pr_reads == 2:
                        value[0]["head"]["sha"] = "c" * 40
                return value

        with self.assertRaisesRegex(ValueError, "PR heads advanced"):
            collect(AdvancingReader(), "GBOGEB/ABACUS")

    def test_one_source_race_is_retried_with_new_heads(self):
        class OneMove(FakeReader):
            def __init__(self):
                super().__init__()
                self.pr_reads = 0

            def get(self, route):
                response = super().get(route)
                if "/pulls?" in route:
                    self.pr_reads += 1
                    if self.pr_reads >= 2:
                        response[0]["head"]["sha"] = "c" * 40
                return response

        report = observer.collect_with_readback_retry(
            OneMove(), "GBOGEB/ABACUS", retries=1
        )
        self.assertEqual(report["collection_attempts"], 2)
        self.assertEqual(report["active_heads"][0]["sha"], "c" * 40)
        self.assertTrue(report["inventory_complete"])
        self.assertEqual(
            report["comparison"]["state"], "FIRST_OBSERVATION_NOT_STABILITY"
        )

    def test_wrong_head_run_fails_closed(self):
        api = FakeReader()
        api.run["workflow_runs"][0]["head_sha"] = A
        with self.assertRaisesRegex(ValueError, "SHA mismatch"):
            collect(api, "GBOGEB/ABACUS")


if __name__ == "__main__":
    unittest.main()
