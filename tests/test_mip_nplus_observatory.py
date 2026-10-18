"""Fail-closed regression tests for N+i exact-SHA workflow telemetry."""
import copy
import unittest

from tools.mip2.mip_nplus_observatory import rollup, matched_workflow_flip

def sample():
    a, b, c = "a" * 40, "b" * 40, "c" * 40
    def run(sha, rid, wf, state, conclusion):
        return {"id": rid, "workflow_id": wf, "run_attempt": 1,
                "head_sha": sha, "event": "push", "status": state,
                "conclusion": conclusion}
    def wave(n, sha, rows):
        return {"wave": f"N{n}", "source_sha": sha,
                "source_role": "HISTORICAL_MAIN_HEAD",
                "api_url": "https://api.github.com/repos/GBOGEB/ABACUS/actions/runs"
                           f"?head_sha={sha}&event=push&per_page=100",
                "native_total_count": len(rows), "runs": rows}
    return {"schema": "abacus.nplus.native-ci-intake.v1",
            "repository": "GBOGEB/ABACUS",
            "provenance": "LIVE_GITHUB_CONNECTOR_READ_ONLY",
            "waves": [
                wave(21, a, [run(a, 11, 10, "completed", "failure"),
                             run(a, 12, 20, "completed", "success")]),
                wave(22, b, [run(b, 21, 10, "completed", "success"),
                             run(b, 22, 20, "queued", None)]),
                wave(23, c, [run(c, 31, 10, "queued", None),
                             run(c, 32, 20, "completed", "success")]),
            ]}


class NPlusTests(unittest.TestCase):
    def test_three_pulses_with_qualifying_change_and_queue(self):
        result = rollup(sample())
        self.assertEqual(result["progress"]["latest_terminal"], 1)
        self.assertEqual(result["progress"]["latest_denominator"], 2)
        self.assertEqual(result["comparisons"][0]["matched_workflows"]
                         ["counts"]["RECOVERED"], 1)
        self.assertEqual(result["comparisons"][1]["matched_workflows"]
                         ["counts"].get("RECOVERED", 0), 0)
        self.assertIsNone(result["progress"]["verified_root_closure_delta"])
        self.assertEqual(result["progress"]["p0_admission"], "HOLD")
        self.assertEqual(result["progress"]["stability_decision"],
                         "INSUFFICIENT_INDEPENDENT_SERIES")

    def test_reject_nonterminal_with_success_conclusion(self):
        x = sample()
        x["waves"][2]["runs"][0]["conclusion"] = "success"
        with self.assertRaisesRegex(ValueError, "nonterminal with conclusion"):
            rollup(x)

    def test_reject_mixed_sha(self):
        x = sample()
        x["waves"][1]["runs"][0]["head_sha"] = "a" * 40
        with self.assertRaisesRegex(ValueError, "mixed SHA"):
            rollup(x)

    def test_reject_truncated_census(self):
        x = sample()
        x["waves"][0]["native_total_count"] = 3
        with self.assertRaisesRegex(ValueError, "truncated"):
            rollup(x)

    def test_reject_reused_run_id(self):
        x = sample()
        x["waves"][2]["runs"][0]["id"] = 11
        with self.assertRaisesRegex(ValueError, "same run observed twice"):
            rollup(x)

    def test_reject_out_of_order_waves(self):
        x = sample()
        x["waves"][1]["wave"] = "N24"
        with self.assertRaisesRegex(ValueError, "consecutive"):
            rollup(x)

    def test_reject_fabricated_terminal_zero_conclusion(self):
        x = sample()
        x["waves"][2]["runs"][0]["status"] = "completed"
        with self.assertRaisesRegex(ValueError, "invalid terminal"):
            rollup(x)

    def test_duplicate_workflow_family_is_excluded(self):
        x = sample()
        r = copy.deepcopy(x["waves"][1]["runs"][0])
        r["id"] = 23
        x["waves"][1]["runs"].append(r)
        x["waves"][1]["native_total_count"] += 1
        result = rollup(x)
        self.assertEqual(result["comparisons"][0]["matched_workflows"]
                         ["counts"]["duplicate_family_excluded"], 1)

    def test_no_auto_scale_authority(self):
        x = sample()
        result = rollup(x)
        self.assertIsNone(result["scaling"]["mutation_lanes_authorized"])
        self.assertFalse(result["merge_authorized"])
        self.assertFalse(result["native_artifact_bytes_reauthenticated"])


if __name__ == "__main__":
    unittest.main()
