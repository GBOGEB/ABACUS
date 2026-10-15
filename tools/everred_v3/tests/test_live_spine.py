"""Synthetic GitHub transport tests: current source cannot inherit old green."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from live_spine import collect, latest_runs, main_head, open_prs

A = "a" * 40
B = "b" * 40


class FakeReader:
    def __init__(self):
        self.head = A
        self.run = {
            "total_count": 1,
            "workflow_runs": [{
                "id": 18, "head_sha": B, "head_branch": "worker",
                "name": "smoke-test", "status": "completed",
                "conclusion": "success", "created_at": "2026-10-15T00:00:00Z",
                "pull_requests": [{"number": 1994}],
            }],
        }

    def get(self, route):
        if route.endswith("/git/ref/heads/main"):
            return {"object": {"sha": self.head}}
        if "/pulls?" in route:
            return ([{
                "number": 1994, "head": {"sha": B, "ref": "worker"},
                "base": {"sha": self.head},
            }] if "page=1" in route else [])
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
        _, history = latest_runs(
            api, "GBOGEB/ABACUS", A, branch="main"
        )
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
        self.assertEqual(
            revised["comparison"]["state"], "SAME_HEADS_EVIDENCE_CHANGED"
        )

    def test_main_move_causes_new_revision(self):
        api = FakeReader()
        prior = collect(api, "GBOGEB/ABACUS")
        api.head = B
        current = collect(api, "GBOGEB/ABACUS", prior=prior)
        self.assertEqual(
            current["comparison"]["state"],
            "SOURCE_REVISION_OR_PR_SET_CHANGED",
        )

    def test_missing_native_listing_is_not_stable(self):
        api = FakeReader()
        api.run["total_count"] = 200
        x = collect(api, "GBOGEB/ABACUS")
        self.assertFalse(x["inventory_complete"])
        self.assertFalse(x["observations"][1]["ci"]["listing_complete"])

    def test_wrong_head_run_fails_closed(self):
        api = FakeReader()
        api.run["workflow_runs"][0]["head_sha"] = A
        with self.assertRaisesRegex(ValueError, "SHA mismatch"):
            collect(api, "GBOGEB/ABACUS")


if __name__ == "__main__":
    unittest.main()
