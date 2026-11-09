import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Load by path: an installed third-party ``scripts`` package can shadow the repo's.
_spec = importlib.util.spec_from_file_location(
    "code_purple_mach_admission", ROOT / "scripts" / "code_purple_mach_admission.py"
)
mach = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mach)

POLICY = json.loads(
    (ROOT / "config" / "governance" / "code_purple_mach_policy.json").read_text(
        encoding="utf-8"
    )
)
LANES = {name: "success" for name in POLICY["required_lanes"]}
MAIN_0 = "44caccf716a7c20693a2911566289bfc75ea81d9"
MERGE_2367 = "94a3c281e947dba8aed85a831a67ffc55309080a"
MERGE_2376 = "ee06553646a1d93cfb34c8d306c19f100ffb239b"

STEP = {
    "author": "GBOGEB",
    "exact_head": True,
    "required_checks_enforced": True,
    "lanes": LANES,
    "automated_review_at_head": True,
    "mergeable": True,
}


def with_active(section, **extra):
    return dict(POLICY, **{section: dict(POLICY[section], active=True, **extra)})


class MachIITests(unittest.TestCase):
    def test_green_owner_pr_is_candidate(self):
        self.assertEqual(mach.decide("II", STEP, POLICY), "GO_CANDIDATE_RECHECK_HEAD")

    def test_waiver_only_covers_listed_owners(self):
        self.assertEqual(
            mach.decide("II", dict(STEP, author="someone-else"), POLICY),
            "HOLD_WAIVER_NOT_APPLICABLE",
        )

    def test_waiver_requires_enforced_checks(self):
        # 2026-10-23 state: approvals waived, but no required_status_checks rule.
        self.assertEqual(
            mach.decide("II", dict(STEP, required_checks_enforced=False), POLICY),
            "HOLD_CHECKS_NOT_ENFORCED",
        )

    def test_red_and_nonterminal_lanes_hold(self):
        red = dict(LANES, **{"CI - ABACUS Matrix": "failure"})
        self.assertEqual(
            mach.decide("II", dict(STEP, lanes=red), POLICY), "HOLD_RED_LANE"
        )
        for state in (None, "queued", "action_required"):
            with self.subTest(state=state):
                pending = dict(LANES, **{"CI/CD Test Suite": state})
                self.assertEqual(
                    mach.decide("II", dict(STEP, lanes=pending), POLICY),
                    "HOLD_NONTERMINAL_LANE",
                )

    def test_missing_automated_review_holds(self):
        self.assertEqual(
            mach.decide("II", dict(STEP, automated_review_at_head=None), POLICY),
            "HOLD_AUTOMATED_REVIEW",
        )


class MachIIITests(unittest.TestCase):
    EVIDENCE = {
        "author": "GBOGEB",
        "head_sha": "a" * 40,
        "exact_head": True,
        "core_functional_checks": True,
        "effective_ruleset_compliance": True,
        "source_bound_receipt": True,
        "security_severities": ["P3"],
        "deferred_findings_complete": True,
        "mergeable": True,
        "exception": {
            "reason": "P3 deferral",
            "authorized_actor": "GBOGEB",
            "expiry": "2026-10-23T09:00:00Z",
            "source_sha": "a" * 40,
            "minutes": 45,
        },
    }

    def test_inactive_policy_holds(self):
        self.assertEqual(
            mach.decide("III", self.EVIDENCE, POLICY), "HOLD_POLICY_NOT_ACTIVE"
        )

    def test_solo_waiver_satisfies_review(self):
        self.assertEqual(
            mach.decide("III", self.EVIDENCE, with_active("mach_iii")),
            "GO_CANDIDATE_RECHECK_HEAD",
        )

    def test_non_owner_still_needs_review(self):
        self.assertEqual(
            mach.decide(
                "III",
                dict(self.EVIDENCE, author="someone-else"),
                with_active("mach_iii"),
            ),
            "HOLD_REVIEW",
        )

    def test_exception_window_and_record(self):
        long_window = dict(
            self.EVIDENCE, exception=dict(self.EVIDENCE["exception"], minutes=90)
        )
        self.assertEqual(
            mach.decide("III", long_window, with_active("mach_iii")),
            "HOLD_EXCEPTION_WINDOW",
        )
        self.assertEqual(
            mach.decide(
                "III", dict(self.EVIDENCE, exception={}), with_active("mach_iii")
            ),
            "HOLD_EXCEPTION_RECORD",
        )

    def test_exception_bound_to_head(self):
        moved = dict(self.EVIDENCE, head_sha="b" * 40)
        self.assertEqual(
            mach.decide("III", moved, with_active("mach_iii")), "HOLD_EXACT_HEAD"
        )

    def test_security_still_blocks(self):
        p1 = dict(self.EVIDENCE, security_severities=["P1"])
        self.assertEqual(
            mach.decide("III", p1, with_active("mach_iii")), "HOLD_SECURITY"
        )


class MachIVTests(unittest.TestCase):
    POST = {name: "success" for name in POLICY["merge_train"]["post_train_lanes"]}

    def train(self, *steps, main_after=MERGE_2376, post=None):
        return {
            "main_before": MAIN_0,
            "train": list(steps),
            "main_after": main_after,
            "post_train_lanes": self.POST if post is None else post,
        }

    def step(self, pr, base, merge, **overrides):
        return dict(
            STEP, pr=pr, level="II", base_sha=base, merge_sha=merge, **overrides
        )

    def test_inactive_policy_holds(self):
        self.assertEqual(
            mach.decide("IV", self.train(self.step(2367, MAIN_0, MERGE_2367)), POLICY),
            "HOLD_POLICY_NOT_ACTIVE",
        )

    def test_requalified_train_verifies(self):
        evidence = self.train(
            self.step(2367, MAIN_0, MERGE_2367), self.step(2376, MERGE_2367, MERGE_2376)
        )
        self.assertEqual(
            mach.decide("IV", evidence, with_active("merge_train")), "GO_TRAIN_VERIFIED"
        )

    def test_step_not_requalified_on_moved_main_holds(self):
        # 2026-10-23 burst: each PR was qualified against the old main, not the previous merge.
        evidence = self.train(
            self.step(2367, MAIN_0, MERGE_2367), self.step(2376, MAIN_0, MERGE_2376)
        )
        self.assertEqual(
            mach.decide("IV", evidence, with_active("merge_train")),
            "HOLD_STEP_2_STALE_BASE",
        )

    def test_burst_replay_holds_on_first_step(self):
        red = dict(LANES, **{"CI - ABACUS Matrix": "failure", "CI/CD Test Suite": None})
        first = self.step(
            2367, MAIN_0, MERGE_2367, required_checks_enforced=False, lanes=red
        )
        self.assertEqual(
            mach.decide("IV", self.train(first), with_active("merge_train")),
            "HOLD_STEP_1_HOLD_CHECKS_NOT_ENFORCED",
        )
        enforced = dict(first, required_checks_enforced=True)
        self.assertEqual(
            mach.decide("IV", self.train(enforced), with_active("merge_train")),
            "HOLD_STEP_1_HOLD_NONTERMINAL_LANE",
        )

    def test_red_post_train_main_holds(self):
        evidence = self.train(
            self.step(2367, MAIN_0, MERGE_2367),
            main_after=MERGE_2367,
            post=dict(self.POST, **{"CI - ABACUS Matrix": "failure"}),
        )
        self.assertEqual(
            mach.decide("IV", evidence, with_active("merge_train")),
            "HOLD_POST_TRAIN_RED_LANE",
        )

    def test_train_length_and_in_progress(self):
        long_train = self.train(*[self.step(n, MAIN_0, None) for n in range(6)])
        self.assertEqual(
            mach.decide("IV", long_train, with_active("merge_train")),
            "HOLD_TRAIN_TOO_LONG",
        )
        pending = self.train(
            self.step(2367, MAIN_0, MERGE_2367), self.step(2376, MERGE_2367, None)
        )
        self.assertEqual(
            mach.decide("IV", pending, with_active("merge_train")),
            "GO_NEXT_STEP_CANDIDATE",
        )

    def test_unknown_level_holds(self):
        self.assertEqual(mach.decide("V", STEP, POLICY), "HOLD_UNKNOWN_LEVEL")


if __name__ == "__main__":
    unittest.main()
