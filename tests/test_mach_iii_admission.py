import unittest

from scripts.mach_iii_admission import decide

BASE = {
    "exact_head": True,
    "core_functional_checks": True,
    "effective_ruleset_compliance": True,
    "source_bound_receipt": True,
    "security_severities": [],
    "required_reviews_satisfied": True,
    "mergeable": True,
}


class AdmissionTests(unittest.TestCase):
    def test_inactive_is_hold(self):
        self.assertEqual(decide(BASE, {"active": False}), "HOLD_POLICY_NOT_ACTIVE")

    def test_p0_p1_and_unknown_block(self):
        for level in ("P0", "P1", "UNKNOWN"):
            with self.subTest(level=level):
                self.assertEqual(
                    decide(dict(BASE, security_severities=[level]), {"active": True}),
                    "HOLD_SECURITY",
                )

    def test_p2_p3_need_record(self):
        self.assertEqual(
            decide(dict(BASE, security_severities=["P2"]), {"active": True}),
            "HOLD_DEFERRAL_RECORD",
        )
        self.assertEqual(
            decide(
                dict(BASE, security_severities=["P3"], deferred_findings_complete=True),
                {"active": True},
            ),
            "GO_CANDIDATE_RECHECK_HEAD",
        )

    def test_required_review_cannot_be_deferred(self):
        self.assertEqual(
            decide(dict(BASE, required_reviews_satisfied=False), {"active": True}),
            "HOLD_REVIEW",
        )

    def test_unknown_ruleset_blocks(self):
        self.assertEqual(
            decide(dict(BASE, effective_ruleset_compliance=None), {"active": True}),
            "HOLD_REQUIRED",
        )


if __name__ == "__main__":
    unittest.main()
