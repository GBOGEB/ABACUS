"""W31 admission readback negative/reverse/force-trip unit controls."""

import copy
import unittest

from ci.governance import w31_admission_readback as admission

SHA = "b" * 40
REQUIRED = ["PR Feedback Gate", "policy-and-inventory", "ABACUS compatibility gate"]


def sample():
    return {
        "exact_head": SHA,
        "default_branch": "main",
        "pr_author": "GBOGEB",
        "expected_status_contexts": REQUIRED,
        "ruleset": {
            "enforcement": "active",
            "rules": [
                {
                    "type": "pull_request",
                    "parameters": {
                        "required_approving_review_count": 0,
                        "dismiss_stale_reviews_on_push": True,
                        "require_last_push_approval": False,
                        "required_review_thread_resolution": False,
                    },
                }
            ],
            "bypass_actors": [
                {"actor_id": i, "actor_type": "Integration", "bypass_mode": "always"}
                for i in range(6)
            ],
        },
        "check_runs": [],
        "reviews": [],
        "branch_protection_readback": None,
        "rejected_red_canary": None,
    }


def with_green_configuration():
    row = sample()
    pr = row["ruleset"]["rules"][0]["parameters"]
    pr.update(
        required_approving_review_count=1,
        require_last_push_approval=True,
        required_review_thread_resolution=True,
    )
    row["ruleset"]["rules"].append(
        {
            "type": "required_status_checks",
            "parameters": {
                "required_status_checks": [{"context": name} for name in REQUIRED]
            },
        }
    )
    row["ruleset"]["bypass_actors"] = []
    row["check_runs"] = [
        {"name": name, "head_sha": SHA, "status": "completed", "conclusion": "success"}
        for name in REQUIRED
    ]
    row["reviews"] = [
        {
            "state": "APPROVED",
            "login": "independent-user",
            "account_type": "User",
            "permission": "write",
            "head_sha": SHA,
        }
    ]
    row["branch_protection_readback"] = {"resolved": True}
    row["rejected_red_canary"] = True
    return row


class AdmissionReadbackTests(unittest.TestCase):
    def test_real_ruleset_shape_is_not_elevated(self):
        out = admission.observe(sample())
        self.assertEqual(out["merge_admission"], "HOLD")
        self.assertEqual(out["always_bypass_integrations"], 6)
        self.assertIn("REVIEW_MINIMUM_NOT_CONFIGURED", out["blockers"])
        self.assertIn("REQUIRED_CHECK_CONTEXTS_INCOMPLETE", out["blockers"])
        self.assertIn("EFFECTIVE_PROTECTION_UNKNOWN", out["blockers"])

    def test_supplied_green_values_still_cannot_attest_human_or_canary(self):
        out = admission.observe(with_green_configuration())
        self.assertEqual(out["eligible_review_metadata_candidates"], 1)
        self.assertIsNone(out["eligible_human_approval_independently_verified"])
        self.assertIsNone(out["rejected_red_canary_source_verified"])
        self.assertEqual(out["merge_admission"], "HOLD")
        self.assertEqual(out["formal_credit_delta"], 0)

    def test_comment_not_approval(self):
        row = with_green_configuration()
        row["reviews"][0]["state"] = "COMMENTED"
        out = admission.observe(row)
        self.assertIn("INDEPENDENT_REVIEW_NOT_OBSERVED", out["blockers"])

    def test_bot_cannot_attest_independent_review(self):
        row = with_green_configuration()
        row["reviews"][0]["account_type"] = "Bot"
        self.assertEqual(
            admission.observe(row)["eligible_review_metadata_candidates"], 0
        )

    def test_owner_self_review_never_qualifies(self):
        row = with_green_configuration()
        row["reviews"][0]["login"] = "GBOGEB"
        self.assertEqual(
            admission.observe(row)["eligible_review_metadata_candidates"], 0
        )

    def test_stale_review_head_never_qualifies(self):
        row = with_green_configuration()
        row["reviews"][0]["head_sha"] = "a" * 40
        self.assertEqual(
            admission.observe(row)["eligible_review_metadata_candidates"], 0
        )

    def test_missing_write_permission_denies_candidate(self):
        row = with_green_configuration()
        row["reviews"][0]["permission"] = "read"
        self.assertEqual(
            admission.observe(row)["eligible_review_metadata_candidates"], 0
        )

    def test_queue_is_not_terminal_success(self):
        row = with_green_configuration()
        row["check_runs"][0]["status"] = "queued"
        row["check_runs"][0]["conclusion"] = None
        out = admission.observe(row)
        self.assertEqual(out["check_run_counts"]["nonterminal"], 1)
        self.assertIn("CHECK_NOT_GREEN:PR Feedback Gate", out["blockers"])

    def test_failed_check_retains_red(self):
        row = with_green_configuration()
        row["check_runs"][0]["conclusion"] = "failure"
        out = admission.observe(row)
        self.assertEqual(out["check_run_counts"]["failure"], 1)
        self.assertIn("CHECK_NOT_GREEN:PR Feedback Gate", out["blockers"])

    def test_missing_required_check_is_distinct_unknown(self):
        row = with_green_configuration()
        row["check_runs"].pop(0)
        self.assertIn(
            "CHECK_RESULT_MISSING:PR Feedback Gate", admission.observe(row)["blockers"]
        )

    def test_wrong_source_check_refused(self):
        row = with_green_configuration()
        row["check_runs"][0]["head_sha"] = "a" * 40
        with self.assertRaisesRegex(ValueError, "foreign-head"):
            admission.observe(row)

    def test_duplicate_check_name_fails_closed(self):
        row = with_green_configuration()
        row["check_runs"].append(copy.deepcopy(row["check_runs"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate check"):
            admission.observe(row)

    def test_missing_red_canary_blocks(self):
        row = with_green_configuration()
        row["rejected_red_canary"] = None
        self.assertIn(
            "REJECTED_RED_CANARY_UNPROVEN", admission.observe(row)["blockers"]
        )

    def test_missing_branch_protection_readback_blocks(self):
        row = with_green_configuration()
        row["branch_protection_readback"] = None
        self.assertIn(
            "EFFECTIVE_PROTECTION_UNKNOWN", admission.observe(row)["blockers"]
        )

    def test_bypass_actor_disqualifies_unexceptioned_rules(self):
        row = with_green_configuration()
        row["ruleset"]["bypass_actors"] = [
            {"actor_id": 17, "actor_type": "Integration", "bypass_mode": "always"}
        ]
        self.assertIn("ALWAYS_BYPASS_INTEGRATIONS", admission.observe(row)["blockers"])

    def test_missing_rule_or_requested_context_blocks(self):
        row = with_green_configuration()
        row["ruleset"]["rules"][1]["parameters"]["required_status_checks"].pop(0)
        self.assertIn(
            "REQUIRED_CHECK_CONTEXTS_INCOMPLETE", admission.observe(row)["blockers"]
        )

    def test_missing_head_rejected(self):
        row = with_green_configuration()
        row["exact_head"] = "not-a-sha"
        with self.assertRaisesRegex(ValueError, "invalid exact-head"):
            admission.observe(row)

    def test_branch_name_stale_rejected(self):
        row = with_green_configuration()
        row["default_branch"] = "develop"
        with self.assertRaisesRegex(ValueError, "default branch"):
            admission.observe(row)


if __name__ == "__main__":
    unittest.main()
