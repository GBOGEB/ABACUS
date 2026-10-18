"""Fail-closed regression tests for N+i exact-SHA workflow telemetry."""
import copy
import unittest

from tools.mip2.mip_nplus_observatory import rollup, matched_workflow_flip, as_markdown

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
                         ["counts"]["RECOVERED_FAILURE_OUTCOME"], 1)
        self.assertEqual(result["comparisons"][1]["matched_workflows"]
                         ["counts"].get("RECOVERED_FAILURE_OUTCOME", 0), 0)
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

    def test_cancelled_is_not_a_new_failure_or_repair(self):
        x = sample()
        x["waves"][1]["runs"][1]["status"] = "completed"
        x["waves"][1]["runs"][1]["conclusion"] = "cancelled"
        c = rollup(x)["comparisons"]
        self.assertEqual(c[0]["matched_workflows"]["counts"]
                         .get("NEW_FAILURE_OUTCOME", 0), 0)
        self.assertEqual(c[1]["matched_workflows"]["counts"]
                         .get("RECOVERED_FAILURE_OUTCOME", 0), 0)
        self.assertEqual(c[1]["matched_workflows"]["counts"]
                         ["NONFAILURE_OUTCOME_TRANSITION"], 1)

    def test_no_auto_scale_authority(self):
        x = sample()
        result = rollup(x)
        self.assertIsNone(result["scaling"]["mutation_lanes_authorized"])
        self.assertFalse(result["merge_authorized"])
        self.assertFalse(result["native_artifact_bytes_reauthenticated"])


    def test_repeat_family_manifest_does_not_inflate_distinct_workflows(self):
        x = sample()
        # Wave N21: 2 workflow identities and three executions.
        duplicated = copy.deepcopy(x["waves"][0]["runs"][1])
        duplicated["id"] = 13
        duplicated["conclusion"] = "success"
        x["waves"][0]["runs"].append(duplicated)
        x["waves"][0]["native_total_count"] += 1
        result = rollup(x)
        fam = result["waves"][0]["workflow_family_accounting"]
        self.assertEqual(fam["total_runs"], 3)
        self.assertEqual(fam["distinct_workflows"], 2)
        self.assertEqual(fam["repeated_executions"], 1)
        self.assertEqual(fam["families_with_repeats"], 1)
        self.assertEqual(fam["run_success"], 2)
        self.assertEqual(fam["family_clean_success"], 1)
        self.assertEqual(fam["success_excess_from_repeat_runs"], 1)
        self.assertIsNone(fam["workflow_testcase_count"])

    def test_render_denominators_are_full_population(self):
        report = as_markdown(rollup(sample()))
        self.assertIn("Green families", report)
        self.assertIn("Success/all", report)
        self.assertIn("Repeat-adjusted counts are diagnostic only", report)
        self.assertIn("2/2", report)

    def test_latest_progress_distinguishes_repeats(self):
        x = sample()
        y = copy.deepcopy(x["waves"][2]["runs"][1])
        y["id"] = 33
        x["waves"][2]["runs"].append(y)
        x["waves"][2]["native_total_count"] += 1
        result = rollup(x)
        self.assertEqual(result["progress"]["latest_distinct_workflows"], 2)
        self.assertEqual(result["progress"]["latest_clean_workflow_families"], 1)
        self.assertEqual(result["progress"]["latest_repeated_run_excess"], 1)
        self.assertEqual(result["progress"]["latest_repeat_success_excess"], 1)
        self.assertIsNone(result["progress"]["latest_workflow_testcase_count"])

    def test_repeated_failed_workflow_does_not_count_as_extra_success(self):
        x = sample()
        new = copy.deepcopy(x["waves"][0]["runs"][0])
        new["id"] = 13
        x["waves"][0]["runs"].append(new)
        x["waves"][0]["native_total_count"] += 1
        fam = rollup(x)["waves"][0]["workflow_family_accounting"]
        self.assertEqual(fam["repeat_success_excess"] if "repeat_success_excess" in fam
                         else fam["success_excess_from_repeat_runs"], 0)
        self.assertEqual(fam["run_failure"], 2)
        self.assertEqual(fam["family_any_failure"], 1)

    def test_corrupt_nonterminal_cannot_be_reclassified_by_helper(self):
        x = sample()
        x["waves"][1]["runs"][1]["conclusion"] = "success"
        with self.assertRaisesRegex(ValueError, "nonterminal with conclusion"):
            rollup(x)


if __name__ == "__main__":
    unittest.main()
