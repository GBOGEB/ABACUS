"""Adversarial regression tranche for repeat-aware native workflow census."""

from __future__ import annotations

import copy
import unittest

from tools.mip2.workflow_family_metrics import summarize_families


def run(rid, wf, state="completed", conclusion="success", attempt=1):
    return {
        "id": rid,
        "workflow_id": wf,
        "run_attempt": attempt,
        "status": state,
        "conclusion": conclusion,
    }


def qps_cohort():
    # N23-like population, not impersonating independently signed native data.
    result = [run(i, 350890474) for i in range(1, 13)]
    result.extend(run(100 + i, 1000 + i) for i in range(19))
    result.extend(run(200 + i, 2000 + i, conclusion="failure") for i in range(4))
    result.extend(run(300 + i, 3000 + i, conclusion="cancelled") for i in range(2))
    return result


class FamilyMetricsTests(unittest.TestCase):
    def test_qps_fanout_does_not_create_twelve_families(self):
        r = summarize_families(qps_cohort())
        self.assertEqual((r["total_runs"], r["distinct_workflows"]), (37, 26))
        self.assertEqual(r["repeated_executions"], 11)
        self.assertEqual(r["success_excess_from_repeat_runs"], 11)
        self.assertEqual(r["success_after_one_per_family_cap"], 20)
        self.assertEqual(r["run_success"], 31)
        self.assertEqual(r["family_clean_success"], 20)
        self.assertEqual(r["run_failure"], 4)
        self.assertEqual(r["run_cancelled"], 2)
        self.assertIsNone(r["workflow_testcase_count"])
        self.assertFalse(r["merge_authority"])

    def test_fully_successful_single_run(self):
        r = summarize_families([run(1, 2)])
        self.assertEqual(r["family_clean_success_fraction"], 1)
        self.assertEqual(r["success_excess_from_repeat_runs"], 0)
        self.assertEqual(r["terminal_runs"], 1)

    def test_all_queued_has_unknown_terminal_success_fraction(self):
        r = summarize_families([run(1, 2, "queued", None)])
        self.assertIsNone(r["success_over_terminal_runs"])
        self.assertEqual(r["run_nonterminal"], 1)
        self.assertEqual(r["family_clean_success"], 0)

    def test_mixed_success_and_failure_same_family_not_green(self):
        r = summarize_families([run(1, 2), run(3, 2, conclusion="failure")])
        self.assertEqual(r["family_any_failure"], 1)
        self.assertEqual(r["family_clean_success"], 0)
        self.assertEqual(r["success_excess_from_repeat_runs"], 0)

    def test_mixed_green_and_queued_same_family_not_green(self):
        r = summarize_families([run(1, 2), run(3, 2, "in_progress", None)])
        self.assertEqual(r["family_with_nonterminal"], 1)
        self.assertEqual(r["family_clean_success"], 0)

    def test_duplicate_success_success_and_cancel_cap(self):
        r = summarize_families(
            [run(1, 2), run(2, 2), run(3, 2, conclusion="cancelled")]
        )
        self.assertEqual(r["success_excess_from_repeat_runs"], 1)
        self.assertEqual(r["family_any_cancelled"], 1)
        self.assertEqual(r["family_clean_success"], 0)

    def test_repeated_failed_runs_do_not_fake_success_excess(self):
        r = summarize_families(
            [run(1, 2, conclusion="failure"), run(2, 2, conclusion="failure")]
        )
        self.assertEqual(r["success_excess_from_repeat_runs"], 0)
        self.assertEqual(r["family_any_failure"], 1)
        self.assertEqual(r["run_failure"], 2)

    def test_timeout_action_required_startup_failure_classified_red(self):
        rows = [
            run(i + 1, i + 1, conclusion=s)
            for i, s in enumerate(("timed_out", "action_required", "startup_failure"))
        ]
        r = summarize_families(rows)
        self.assertEqual(r["run_failure"], 3)
        self.assertEqual(r["family_any_failure"], 3)

    def test_skipped_neutral_separate_from_failure(self):
        r = summarize_families(
            [run(1, 2, conclusion="skipped"), run(2, 3, conclusion="neutral")]
        )
        self.assertEqual(r["run_other_terminal"], 2)
        self.assertEqual(r["run_failure"], 0)
        self.assertEqual(r["terminal_runs"], 2)

    def test_every_allowed_open_state_is_not_terminal(self):
        for i, state in enumerate(
            ("queued", "pending", "in_progress", "requested", "waiting"), 1
        ):
            with self.subTest(state=state):
                r = summarize_families([run(i, i, state, None)])
                self.assertEqual(r["run_nonterminal"], 1)
                self.assertIsNone(r["success_over_terminal_runs"])

    def test_completed_missing_conclusion_rejected(self):
        with self.assertRaisesRegex(ValueError, "completed run"):
            summarize_families([run(1, 2, conclusion=None)])

    def test_unrecognized_terminal_rejected(self):
        with self.assertRaisesRegex(ValueError, "recognized conclusion"):
            summarize_families([run(1, 2, conclusion="test_culled")])

    def test_open_run_cannot_claim_success(self):
        with self.assertRaisesRegex(ValueError, "cannot have a conclusion"):
            summarize_families([run(1, 2, "queued", "success")])

    def test_bad_state_rejected(self):
        with self.assertRaisesRegex(ValueError, "unrecognized"):
            summarize_families([run(1, 2, "sleeping", None)])

    def test_empty_population_rejected(self):
        with self.assertRaisesRegex(ValueError, "nonempty"):
            summarize_families([])

    def test_tuple_population_rejected(self):
        with self.assertRaisesRegex(ValueError, "nonempty"):
            summarize_families((run(1, 2),))

    def test_nonmapping_run_rejected(self):
        with self.assertRaisesRegex(ValueError, "object"):
            summarize_families([None])

    def test_ids_must_be_positive(self):
        for field in ("id", "workflow_id", "run_attempt"):
            with self.subTest(field=field):
                row = run(1, 2)
                row[field] = 0
                with self.assertRaisesRegex(ValueError, "positive integers"):
                    summarize_families([row])

    def test_bool_identity_rejected(self):
        row = run(True, 2)
        with self.assertRaisesRegex(ValueError, "positive integers"):
            summarize_families([row])

    def test_duplicate_run_identity_rejected_even_when_attempt_differs(self):
        with self.assertRaisesRegex(ValueError, "duplicate run"):
            summarize_families([run(1, 2), run(1, 3, attempt=2)])

    def test_stable_run_manifest_sorted_by_workflow_and_run(self):
        r = summarize_families(
            [run(3, 12, attempt=2), run(1, 11), run(2, 12, attempt=1)]
        )
        self.assertEqual([x["workflow_id"] for x in r["manifest"]], [11, 12])
        self.assertEqual(r["manifest"][1]["run_ids"], [2, 3])
        self.assertEqual(r["manifest"][1]["attempts_observed"], [1, 2])

    def test_manifests_classify_mixed_statuses_without_promoting(self):
        r = summarize_families(
            [run(1, 2, conclusion="failure"), run(2, 2, "queued", None), run(3, 2)]
        )
        m = r["manifest"][0]
        self.assertEqual((m["success"], m["failure"], m["nonterminal"]), (1, 1, 1))
        self.assertFalse(m["clean_success"])
        self.assertTrue(r["repeat_adjusted_is_diagnostic_only"])
        self.assertIsNone(r["matched_statement_coverage"])
        self.assertIsNone(r["verified_root_closure"])

    def test_repeat_excess_counts_distinct_families(self):
        r = summarize_families([run(1, 2), run(2, 2), run(3, 4), run(4, 4), run(5, 4)])
        self.assertEqual(r["families_with_repeats"], 2)
        self.assertEqual(r["repeated_executions"], 3)


if __name__ == "__main__":
    unittest.main()
