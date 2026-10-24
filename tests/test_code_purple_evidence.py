import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Load by path: an installed third-party ``scripts`` package can shadow the repo's.
_spec = importlib.util.spec_from_file_location(
    "code_purple_evidence", ROOT / "scripts" / "code_purple_evidence.py"
)
ev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ev)

POLICY = json.loads(
    (ROOT / "config" / "governance" / "code_purple_mach_policy.json").read_text(
        encoding="utf-8"
    )
)
HEAD = "41ba0ab47b5ab7f8c503b3a9e9e99bf668101e6a"
OLD_HEAD = "23b06e2606ea3200ef512b0e1deba6a96a1428c8"
MERGE = "94a3c281e947dba8aed85a831a67ffc55309080a"
MAIN_0 = "44caccf716a7c20693a2911566289bfc75ea81d9"
HUMAN = [
    {"login": "alice", "user_type": "User", "state": "APPROVED", "commit_id": HEAD}
]

GREEN = {
    "author": "GBOGEB",
    "head_sha": HEAD,
    "observed_head_sha": HEAD,
    "required_checks_enforced": True,
    "canary_rejected": True,
    "lanes": {name: "success" for name in POLICY["required_lanes"]},
    "reviews": [
        {
            "login": "copilot",
            "user_type": "Bot",
            "state": "COMMENTED",
            "commit_id": HEAD,
        }
    ],
    "mergeable": True,
    "unresolved_threads": 0,
}


def evidence(**overrides):
    return dict(GREEN, **overrides)


class AdmissionTests(unittest.TestCase):
    def test_all_gates_met_is_candidate(self):
        self.assertEqual(ev.admission_verdict("II", GREEN, POLICY), ev.GO)

    def test_observed_green_on_a_stale_head_is_not_admissible(self):
        verdict = ev.admission_verdict(
            "II", evidence(observed_head_sha=OLD_HEAD), POLICY
        )
        self.assertEqual(verdict, "HOLD_EXACT_HEAD")

    def test_unknown_protection_holds_and_is_not_assumed_false(self):
        verdict = ev.admission_verdict(
            "II", evidence(required_checks_enforced=None), POLICY
        )
        self.assertEqual(verdict, "HOLD_UNKNOWN_REQUIRED_CHECKS_ENFORCED")

    def test_missing_field_holds(self):
        bad = dict(GREEN)
        del bad["canary_rejected"]
        self.assertEqual(
            ev.admission_verdict("II", bad, POLICY), "HOLD_UNKNOWN_CANARY_REJECTED"
        )

    def test_unrejected_canary_holds(self):
        verdict = ev.admission_verdict("II", evidence(canary_rejected=False), POLICY)
        self.assertEqual(verdict, "HOLD_NO_REJECTED_CANARY")

    def test_unenforced_checks_hold(self):
        verdict = ev.admission_verdict(
            "II", evidence(required_checks_enforced=False), POLICY
        )
        self.assertEqual(verdict, "HOLD_CHECKS_NOT_ENFORCED")

    def test_red_or_nonterminal_lane_holds(self):
        lane = POLICY["required_lanes"][0]
        for state, expected in (
            ("failure", "HOLD_RED_LANE"),
            ("in_progress", "HOLD_NONTERMINAL_LANE"),
        ):
            lanes = dict(GREEN["lanes"], **{lane: state})
            self.assertEqual(
                ev.admission_verdict("II", evidence(lanes=lanes), POLICY), expected
            )

    def test_review_flag_cannot_be_forged(self):
        forged = evidence(reviews=[], automated_review_at_head=True)
        self.assertEqual(
            ev.admission_verdict("II", forged, POLICY), "HOLD_AUTOMATED_REVIEW"
        )

    def test_review_on_old_head_does_not_count(self):
        old = [
            {
                "login": "copilot",
                "user_type": "Bot",
                "state": "COMMENTED",
                "commit_id": OLD_HEAD,
            }
        ]
        self.assertEqual(
            ev.admission_verdict("II", evidence(reviews=old), POLICY),
            "HOLD_AUTOMATED_REVIEW",
        )

    def test_unknown_reviews_hold(self):
        self.assertEqual(
            ev.admission_verdict("II", evidence(reviews=None), POLICY),
            "HOLD_UNKNOWN_REVIEWS",
        )

    def test_mach_i_rejects_bot_comment_review(self):
        self.assertEqual(
            ev.admission_verdict("I", GREEN, POLICY), "HOLD_INDEPENDENT_REVIEW"
        )

    def test_mach_i_rejects_self_approval_and_bot_approval(self):
        for login, kind in (("GBOGEB", "User"), ("copilot", "Bot")):
            review = [
                {
                    "login": login,
                    "user_type": kind,
                    "state": "APPROVED",
                    "commit_id": HEAD,
                }
            ]
            self.assertEqual(
                ev.admission_verdict("I", evidence(reviews=review), POLICY),
                "HOLD_INDEPENDENT_REVIEW",
            )

    def test_mach_i_accepts_independent_human_approval_at_head(self):
        review = [
            {
                "login": "alice",
                "user_type": "User",
                "state": "APPROVED",
                "commit_id": HEAD,
            }
        ]
        self.assertEqual(
            ev.admission_verdict("I", evidence(reviews=review), POLICY), ev.GO
        )

    def test_unknown_level_and_garbage_fail_closed(self):
        self.assertEqual(
            ev.admission_verdict("IX", GREEN, POLICY), "HOLD_UNKNOWN_LEVEL"
        )
        self.assertEqual(
            ev.admission_verdict("II", evidence(lanes="oops"), POLICY),
            "HOLD_EVIDENCE_ERROR",
        )


class ReviewIdentityTests(unittest.TestCase):
    """Regression tests for the Codex review findings on PR 2423."""

    def test_human_comment_is_not_an_automated_review(self):
        for review in (
            {"login": "alice", "user_type": "User", "state": "COMMENTED"},
            {"login": "GBOGEB", "user_type": "User", "state": "APPROVED"},
            {"login": "mystery", "user_type": None, "state": "COMMENTED"},
            {"login": "mystery", "state": "COMMENTED"},
        ):
            reviews = [dict(review, commit_id=HEAD)]
            self.assertEqual(
                ev.admission_verdict("II", evidence(reviews=reviews), POLICY),
                "HOLD_AUTOMATED_REVIEW",
                review,
            )

    def test_organization_actor_counts_as_automated(self):
        org = [{"login": "ci", "user_type": "Organization", "commit_id": HEAD}]
        self.assertEqual(
            ev.admission_verdict("II", evidence(reviews=org), POLICY), ev.GO
        )

    def test_mach_i_needs_known_human_identity_and_known_author(self):
        no_type = [dict(HUMAN[0], user_type=None)]
        self.assertEqual(
            ev.admission_verdict("I", evidence(reviews=no_type), POLICY),
            "HOLD_INDEPENDENT_REVIEW",
        )
        self.assertEqual(
            ev.admission_verdict("I", evidence(reviews=HUMAN, author=None), POLICY),
            "HOLD_INDEPENDENT_REVIEW",
        )

    def test_mach_i_unresolved_threads(self):
        for threads, expected in (
            (None, "HOLD_UNKNOWN_UNRESOLVED_THREADS"),
            ("0", "HOLD_UNKNOWN_UNRESOLVED_THREADS"),
            (2, "HOLD_UNRESOLVED_THREADS"),
        ):
            self.assertEqual(
                ev.admission_verdict(
                    "I", evidence(reviews=HUMAN, unresolved_threads=threads), POLICY
                ),
                expected,
                threads,
            )

    def test_classify_reviews_reports_each_identity(self):
        def kind(reviews):
            return ev.classify_reviews(reviews, HEAD, "GBOGEB")

        self.assertEqual(kind(None), "unknown")
        self.assertEqual(kind([]), "none")
        self.assertEqual(kind(HUMAN), "human_approval")
        self.assertEqual(kind(GREEN["reviews"]), "automated_review")
        other = [{"login": "alice", "user_type": "User", "commit_id": HEAD}]
        self.assertEqual(kind(other), "other_review")


class UpperLadderReviewForgeryTests(unittest.TestCase):
    """MACH-III and MACH-IV must not trust caller-supplied review booleans."""

    def with_active(self, section):
        return dict(POLICY, **{section: dict(POLICY[section], active=True)})

    def mach_iii(self, **overrides):
        base = evidence(
            core_functional_checks=True,
            effective_ruleset_compliance=True,
            source_bound_receipt=True,
            security_severities=["P3"],
            deferred_findings_complete=True,
            exception={
                "reason": "P3 deferral",
                "authorized_actor": "GBOGEB",
                "expiry": "2026-10-24T20:00:00Z",
                "source_sha": HEAD,
                "minutes": 45,
            },
        )
        return dict(base, **overrides)

    def test_non_owner_cannot_forge_required_reviews(self):
        forged = self.mach_iii(
            author="someone-else", reviews=[], required_reviews_satisfied=True
        )
        self.assertEqual(
            ev.admission_verdict("III", forged, self.with_active("mach_iii")),
            "HOLD_REVIEW",
        )

    def test_non_owner_with_real_human_approval_passes(self):
        real = self.mach_iii(author="someone-else", reviews=HUMAN)
        self.assertEqual(
            ev.admission_verdict("III", real, self.with_active("mach_iii")), ev.GO
        )

    def step(self, base, merge, **overrides):
        return evidence(level="II", base_sha=base, merge_sha=merge, **overrides)

    def train(self, *steps):
        return {
            "main_before": MAIN_0,
            "train": list(steps),
            "main_after": steps[-1]["merge_sha"],
            "post_train_lanes": {
                name: "success" for name in POLICY["merge_train"]["post_train_lanes"]
            },
        }

    def test_train_step_cannot_forge_automated_review(self):
        forged = self.step(MAIN_0, MERGE, reviews=[], automated_review_at_head=True)
        self.assertEqual(
            ev.admission_verdict(
                "IV", self.train(forged), self.with_active("merge_train")
            ),
            "HOLD_STEP_1_HOLD_AUTOMATED_REVIEW",
        )

    def test_train_step_must_pass_pregates(self):
        stale = self.step(MAIN_0, MERGE, observed_head_sha=OLD_HEAD)
        self.assertEqual(
            ev.admission_verdict(
                "IV", self.train(stale), self.with_active("merge_train")
            ),
            "HOLD_STEP_1_HOLD_EXACT_HEAD",
        )

    def test_genuine_train_verifies(self):
        step = self.step(MAIN_0, MERGE)
        self.assertEqual(
            ev.admission_verdict(
                "IV", self.train(step), self.with_active("merge_train")
            ),
            "GO_TRAIN_VERIFIED",
        )

    def test_empty_or_missing_train_holds(self):
        for train in (None, []):
            self.assertEqual(
                ev.admission_verdict(
                    "IV", {"train": train}, self.with_active("merge_train")
                ),
                "HOLD_EMPTY_TRAIN",
            )


class MergeVerifiedTests(unittest.TestCase):
    RECORD = {
        "verdict": ev.GO,
        "admitted_head": HEAD,
        "merged_head": HEAD,
        "merge_sha": MERGE,
        "merge_sha_readback": MERGE,
    }

    def test_verified(self):
        self.assertTrue(ev.merge_verified(self.RECORD))

    def test_each_break_unverifies(self):
        for key, value in (
            ("verdict", "HOLD_RED_LANE"),
            ("merged_head", OLD_HEAD),
            ("merge_sha_readback", OLD_HEAD),
            ("merge_sha_readback", None),
            ("verdict", None),
        ):
            self.assertFalse(ev.merge_verified(dict(self.RECORD, **{key: value})), key)


class CreditTests(unittest.TestCase):
    def test_housekeeping_closure_earns_no_engineering_credit(self):
        self.assertEqual(ev.engineering_credit("closed", "open"), "HOUSEKEEPING_ONLY")

    def test_open_issue_open_root_no_credit(self):
        self.assertEqual(ev.engineering_credit("open", "open"), "NONE")

    def test_unknown_root_is_unknown_not_zero(self):
        self.assertEqual(ev.engineering_credit("closed", "unknown"), "UNKNOWN")
        self.assertEqual(ev.engineering_credit("closed", "bogus"), "UNKNOWN")

    def test_accepted_closure_needs_verified_merge(self):
        self.assertEqual(ev.engineering_credit("closed", "accepted_closure"), "NONE")
        record = MergeVerifiedTests.RECORD
        self.assertEqual(
            ev.engineering_credit("closed", "accepted_closure", record), "CREDITED"
        )
        broken = dict(record, merge_sha_readback=None)
        self.assertEqual(
            ev.engineering_credit("closed", "accepted_closure", broken), "NONE"
        )


class NotificationTests(unittest.TestCase):
    QUIET = {"source_sha": OLD_HEAD, "first_red_id": "R-a"}

    def test_quiet_state_is_silent(self):
        self.assertEqual(ev.notifications(self.QUIET, self.QUIET), [])

    def test_pr2388_first_red_change_notifies_once(self):
        current = dict(
            self.QUIET,
            source_sha=HEAD,
            first_red_id="R-nameerror-phase8",
            blocking_first_red_changed=True,
            root_id="R-nameerror-phase8",
            next_action="restore imports",
        )
        alerts = ev.notifications(self.QUIET, current)
        self.assertEqual([a["kind"] for a in alerts], ["blocking_first_red"])
        self.assertEqual(alerts[0]["source_sha"], HEAD)
        self.assertIsNone(alerts[0]["numerator"])  # unknown stays None
        self.assertEqual(
            ev.notifications(self.QUIET, current, {alerts[0]["event_id"]}), []
        )

    def test_repeated_same_blocker_is_not_new(self):
        current = dict(self.QUIET, source_sha=HEAD, blocking_first_red_changed=True)
        self.assertEqual(ev.notifications(self.QUIET, current), [])  # id unchanged

    def test_coverage_none_does_not_crash_or_notify(self):
        current = dict(
            self.QUIET,
            matched_coverage_delta_verified=True,
            matched_coverage_delta=None,
            baseline_id="b1",
        )
        self.assertEqual(ev.notifications(self.QUIET, current), [])

    def test_coverage_needs_verified_matched_baseline_and_positive_delta(self):
        base = dict(
            self.QUIET,
            matched_coverage_delta_verified=True,
            matched_coverage_delta=1,
            baseline_id="b1",
            numerator=33580,
            denominator=46942,
        )
        self.assertEqual(
            [a["kind"] for a in ev.notifications(self.QUIET, base)],
            ["matched_coverage_gain"],
        )
        for change in (
            {"matched_coverage_delta_verified": False},
            {"matched_coverage_delta": 0},
            {"matched_coverage_delta": -3},
            {"baseline_id": None},
        ):
            self.assertEqual(ev.notifications(self.QUIET, dict(base, **change)), [])

    def test_merge_notifies_on_transition_only(self):
        current = dict(self.QUIET, governed_main_merge_verified=True, merge_sha=MERGE)
        self.assertTrue(ev.should_notify(self.QUIET, current))
        already = dict(self.QUIET, governed_main_merge_verified=True, merge_sha=MERGE)
        self.assertFalse(ev.should_notify(already, current))

    def test_second_verified_merge_notifies_again(self):
        first = dict(self.QUIET, governed_main_merge_verified=True, merge_sha=OLD_HEAD)
        second = dict(
            self.QUIET,
            source_sha=HEAD,
            governed_main_merge_verified=True,
            merge_sha=MERGE,
        )
        alerts = ev.notifications(first, second)
        self.assertEqual([a["kind"] for a in alerts], ["governed_main_merge"])
        # the same merge observed again is still deduplicated
        self.assertEqual(ev.notifications(first, second, {alerts[0]["event_id"]}), [])
        self.assertEqual(ev.notifications(second, second), [])

    def test_merge_without_merge_sha_is_silent(self):
        current = dict(self.QUIET, governed_main_merge_verified=True)
        self.assertFalse(ev.should_notify(self.QUIET, current))

    def test_todo_milestone(self):
        current = dict(
            self.QUIET, material_todo_milestone_newly_completed=True, todo_completed=2
        )
        alerts = ev.notifications(self.QUIET, current)
        self.assertEqual([a["kind"] for a in alerts], ["todo_milestone"])
        later = dict(current, todo_completed=3)
        self.assertNotEqual(
            alerts[0]["event_id"], ev.notifications(self.QUIET, later)[0]["event_id"]
        )

    def test_observation_without_source_sha_is_not_evidence(self):
        current = {"governed_main_merge_verified": True, "merge_sha": MERGE}
        self.assertEqual(ev.notifications(self.QUIET, current), [])


class MachITests(unittest.TestCase):
    def test_approval_alone_is_not_enough(self):
        lane = POLICY["required_lanes"][0]
        red = dict(GREEN["lanes"], **{lane: "failure"})
        self.assertEqual(
            ev.admission_verdict("I", evidence(reviews=HUMAN, lanes=red), POLICY),
            "HOLD_RED_LANE",
        )
        self.assertEqual(
            ev.admission_verdict("I", evidence(reviews=HUMAN, lanes={}), POLICY),
            "HOLD_NONTERMINAL_LANE",
        )

    def test_unmergeable_holds(self):
        self.assertEqual(
            ev.admission_verdict("I", evidence(reviews=HUMAN, mergeable=None), POLICY),
            "HOLD_MERGEABILITY",
        )


class RealRulesetTests(unittest.TestCase):
    """24 Oct readback: ruleset 24494381 had no required_status_checks rule."""

    def test_green_ci_without_enforced_checks_still_holds(self):
        verdict = ev.admission_verdict(
            "II",
            evidence(required_checks_enforced=False, canary_rejected=False),
            POLICY,
        )
        self.assertEqual(verdict, "HOLD_CHECKS_NOT_ENFORCED")


class NotificationRobustnessTests(unittest.TestCase):
    QUIET = {"source_sha": HEAD}

    def test_first_observation_has_no_previous(self):
        current = dict(self.QUIET, governed_main_merge_verified=True, merge_sha=MERGE)
        self.assertEqual(
            [a["kind"] for a in ev.notifications(None, current)],
            ["governed_main_merge"],
        )
        self.assertEqual(ev.notifications(None, None), [])

    def test_non_numeric_delta_is_ignored_not_a_crash(self):
        for bad in ("5", True, [1], {"n": 1}):
            current = dict(
                self.QUIET,
                matched_coverage_delta_verified=True,
                matched_coverage_delta=bad,
                baseline_id="b1",
            )
            self.assertEqual(ev.notifications(self.QUIET, current), [], bad)


class CliTests(unittest.TestCase):
    def setUp(self):
        import tempfile

        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, self.dir, True)

    def write(self, name, data):
        path = self.dir / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return str(path)

    def run_cli(self, *argv):
        import contextlib
        import io

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = ev.main(list(argv))
        return code, out.getvalue()

    def test_admission_prints_verdict(self):
        policy = self.write("policy.json", POLICY)
        code, out = self.run_cli(
            "admission", "II", self.write("e.json", GREEN), "--policy", policy
        )
        self.assertEqual((code, out.strip()), (0, ev.GO))

    def test_notify_seen_file_prevents_repeat(self):
        prev = self.write("p.json", {"source_sha": OLD_HEAD})
        cur = self.write(
            "c.json",
            {
                "source_sha": HEAD,
                "governed_main_merge_verified": True,
                "merge_sha": MERGE,
            },
        )
        seen = str(self.dir / "seen.json")
        _, first = self.run_cli("notify", prev, cur, "--seen", seen)
        _, second = self.run_cli("notify", prev, cur, "--seen", seen)
        self.assertEqual(len(json.loads(first)), 1)
        self.assertEqual(json.loads(second), [])


if __name__ == "__main__":
    unittest.main()
