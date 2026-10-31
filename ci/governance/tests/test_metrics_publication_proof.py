"""Exact native job gates must not turn workflow green-by-skip into proof."""

import copy
import unittest

from ci.governance.metrics_publication_proof import JOB_NAME, qualify

SHA = "a" * 40
RUN = {
    "id": 39231364355,
    "run_attempt": 1,
    "head_sha": SHA,
    "status": "completed",
    "conclusion": "success",
}
PUBLISH = {
    "id": 117990038296,
    "run_id": RUN["id"],
    "name": JOB_NAME,
    "status": "completed",
    "conclusion": "skipped",
}
RECEIPT = {
    "source_sha": SHA,
    "run_id": RUN["id"],
    "run_attempt": 1,
    "job_id": PUBLISH["id"],
    "destination_pr_number": 42,
    "artifact_sha256": "b" * 64,
}


class MetricsPublicationProofTests(unittest.TestCase):
    def test_actual_native_green_by_skip_is_not_publication(self):
        q = qualify(RUN.copy(), [PUBLISH.copy()])
        self.assertEqual(q["qualifier"], "DEFERRED_SKIPPED_NO_PUBLICATION")
        self.assertFalse(q["proof_of_native_publication"])
        self.assertFalse(q["proof_of_required_status_admission"])

    def test_actual_failed_publish_job_is_red_even_if_other_jobs_green(self):
        fail_run = {**RUN, "id": 39230999906, "conclusion": "failure"}
        fail_job = {
            **PUBLISH,
            "id": 117989706278,
            "run_id": fail_run["id"],
            "conclusion": "failure",
        }
        q = qualify(fail_run, [fail_job])
        self.assertEqual(q["qualifier"], "NATIVE_PUBLICATION_FAILED")
        self.assertFalse(q["proof_of_native_publication"])

    def test_full_synthetic_receipt_still_does_not_approve_merge(self):
        good = {**PUBLISH, "conclusion": "success"}
        q = qualify(RUN, [good], RECEIPT)
        self.assertTrue(q["proof_of_native_publication"])
        self.assertFalse(q["proof_of_human_acceptance"])
        self.assertEqual(q["merge_admission"], "HOLD")

    def test_success_without_receipt_is_incomplete(self):
        q = qualify(RUN, [{**PUBLISH, "conclusion": "success"}])
        self.assertEqual(q["qualifier"], "SUCCESS_WITHOUT_BOUND_RECEIPT")

    def test_wrong_sha_receipt_rejected(self):
        r = {**RECEIPT, "source_sha": "b" * 40}
        with self.assertRaisesRegex(ValueError, "unbound"):
            qualify(RUN, [{**PUBLISH, "conclusion": "success"}], r)

    def test_run_identity_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "another native run"):
            qualify(RUN, [{**PUBLISH, "run_id": 1}])

    def test_duplicate_publication_jobs_rejected(self):
        jobs = [PUBLISH, {**PUBLISH, "id": 3}]
        with self.assertRaisesRegex(ValueError, "publication job"):
            qualify(RUN, jobs)

    def test_null_or_false_zero_run_identity_rejected(self):
        for value in (None, 0, True, "1"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "SHA/run/attempt"):
                    qualify({**RUN, "run_attempt": value}, [PUBLISH])

    def test_nonterminal_never_qualifies(self):
        q = qualify({**RUN, "status": "in_progress"}, [PUBLISH])
        self.assertEqual(q["qualifier"], "NONTERMINAL_NO_CREDIT")

    def test_skipped_cannot_be_promoted_by_synthetic_receipt(self):
        q = qualify(RUN, [PUBLISH], RECEIPT)
        self.assertFalse(q["proof_of_native_publication"])
        self.assertIsNone(q["credential_evidence"])


if __name__ == "__main__":
    unittest.main()
