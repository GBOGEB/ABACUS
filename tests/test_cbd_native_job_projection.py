"""Negative and positive tests for source-bound native CBD! job projections."""

import copy
import json
import unittest
from pathlib import Path

from scripts import cbd_native_job_projection as native

ROOT = Path(__file__).resolve().parents[1] / "docs" / "ci"
SOURCES = (
    ROOT / "CBD_NATIVE_16SUITE_JOBS_A_20261017.json",
    ROOT / "CBD_NATIVE_16SUITE_JOBS_B_20261017.json",
)


class NativeJobProjectionTests(unittest.TestCase):
    """Exercise denominators, first-red visibility and fail-closed authority."""

    def setUp(self):
        self.documents = [
            json.loads(path.read_text(encoding="utf-8")) for path in SOURCES
        ]

    def test_native_sample_denominators_are_source_bound(self):
        metrics = native.project(self.documents)["metrics"]
        self.assertEqual(metrics["sampled_run_ids"], 16)
        self.assertEqual(metrics["sampled_prs"], 16)
        self.assertEqual(metrics["expected_job_records_first_page"], 303)
        self.assertEqual(metrics["fetched_job_records_first_page"], 303)
        self.assertTrue(metrics["jobs_collection_complete"])
        self.assertEqual(metrics["failed_job_manifestations"], 40)
        self.assertEqual(metrics["failed_step_observations"], 43)
        self.assertEqual(metrics["non_summary_failed_jobs"], 26)
        self.assertEqual(metrics["downstream_summary_failed_jobs"], 14)
        self.assertEqual(metrics["runs_with_failed_jobs"], 15)
        self.assertEqual(metrics["nonterminal_jobs"], 2)
        self.assertEqual(metrics["observed_run_attempt_groups"], 16)

    def test_job_family_counts_are_not_assumed_causes(self):
        report = native.project(self.documents)
        groups = {
            item["symptom_family"]: item for item in report["candidate_job_families"]
        }
        self.assertEqual(groups["SECURITY"]["failed_jobs"], 15)
        self.assertEqual(groups["QUALITY"]["failed_jobs"], 10)
        self.assertEqual(groups["COVERAGE"]["failed_jobs"], 1)
        self.assertEqual(groups["DOWNSTREAM_SUMMARY"]["failed_jobs"], 14)
        for item in groups.values():
            self.assertIsNone(item["confirmed_causal_root"])
            self.assertFalse(item["disjoint_repair_authorized"])
        self.assertIsNone(report["metrics"]["matched_branch_coverage"])
        self.assertIsNone(report["metrics"]["matched_changed_line_coverage"])
        self.assertIsNone(report["metrics"]["accepted_bd_closures"])

    def test_deterministic_projection_does_not_mutate_inputs(self):
        prior = copy.deepcopy(self.documents)
        one = native.project(self.documents)
        two = native.project(self.documents)
        self.assertEqual(prior, self.documents)
        self.assertEqual(one, two)

    def test_forged_merge_authority_is_rejected(self):
        self.documents[0]["authority"]["merge_admission"] = "PASS"
        with self.assertRaises(ValueError):
            native.project(self.documents)

    def test_forged_security_waiver_is_rejected(self):
        self.documents[1]["authority"]["security_waiver"] = True
        with self.assertRaises(ValueError):
            native.project(self.documents)

    def test_changed_head_invalidates_job_evidence(self):
        self.documents[0]["runs"][0]["source_head_sha"] = "f" * 40
        with self.assertRaises(ValueError):
            native.project(self.documents)

    def test_bad_job_attempt_rejected(self):
        self.documents[0]["runs"][0]["jobs"][0]["run_attempt"] = True
        with self.assertRaises(ValueError):
            native.project(self.documents)

    def test_duplicate_job_id_rejected(self):
        jobs = self.documents[0]["runs"][0]["jobs"]
        jobs[1]["job_id"] = jobs[0]["job_id"]
        with self.assertRaises(ValueError):
            native.project(self.documents)

    def test_duplicate_run_id_rejected(self):
        self.documents[1]["runs"][0]["run_id"] = self.documents[0]["runs"][0]["run_id"]
        with self.assertRaises(ValueError):
            native.project(self.documents)

    def test_missing_job_denominator_rejected(self):
        self.documents[0]["runs"][0]["job_total"] = 0
        with self.assertRaises(ValueError):
            native.project(self.documents)

    def test_missing_page_is_incomplete_not_green(self):
        self.documents[0]["runs"][0]["jobs"].pop()
        metrics = native.project(self.documents)["metrics"]
        self.assertFalse(metrics["jobs_collection_complete"])
        self.assertEqual(metrics["expected_job_records_first_page"], 303)
        self.assertEqual(metrics["fetched_job_records_first_page"], 302)
        self.assertIsNone(metrics["accepted_bd_closures"])

    def test_nonterminal_job_may_not_claim_success(self):
        job = self.documents[0]["runs"][0]["jobs"][0]
        job["status"] = "queued"
        job["conclusion"] = "success"
        with self.assertRaises(ValueError):
            native.project(self.documents)

    def test_nonfailed_job_cannot_have_failed_steps(self):
        run = self.documents[0]["runs"][0]
        good = next(job for job in run["jobs"] if job["conclusion"] == "success")
        good["failed_steps"] = [{"step_number": 1, "step_name": "false red"}]
        with self.assertRaises(ValueError):
            native.project(self.documents)

    def test_unclassified_failing_job_is_reader_only(self):
        run = self.documents[0]["runs"][0]
        failed = next(job for job in run["jobs"] if job["conclusion"] == "failure")
        failed["job_name"] = "Future unknown native gate"
        result = native.project(self.documents)
        group = next(
            item
            for item in result["candidate_job_families"]
            if item["symptom_family"] == "UNCLASSIFIED_JOB:Future unknown native gate"
        )
        self.assertEqual(group["priority"], "READER")
        self.assertFalse(group["disjoint_repair_authorized"])

    def test_failed_job_without_failed_step_is_still_red(self):
        run = self.documents[0]["runs"][0]
        failed = next(job for job in run["jobs"] if job["conclusion"] == "failure")
        failed["failed_steps"] = []
        result = native.project(self.documents)
        self.assertEqual(result["metrics"]["failed_job_manifestations"], 40)
        self.assertEqual(result["metrics"]["failed_step_observations"], 42)

    def test_run_attempt_is_native_not_default_one(self):
        result = native.project(self.documents)
        attempts = {row["run_attempt"] for row in result["failed_job_evidence"]}
        self.assertIn(2, attempts)
        self.assertIn(1, attempts)

    def test_empty_document_list_rejected(self):
        with self.assertRaises(ValueError):
            native.project([])

    def test_failed_step_needs_positive_unique_number(self):
        run = self.documents[0]["runs"][0]
        failed = next(job for job in run["jobs"] if job["failed_steps"])
        failed["failed_steps"][0]["step_number"] = 0
        with self.assertRaises(ValueError):
            native.project(self.documents)


if __name__ == "__main__":
    unittest.main()
