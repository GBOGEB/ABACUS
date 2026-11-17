"""Fail-closed source and HTML contracts for the recovery-action value view."""

from __future__ import annotations

import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "docs/data/recovery_action_value_v1.json"
VIEW = ROOT / "docs/ci/recovery_action_value.html"
SHA = re.compile(r"^[0-9a-f]{40}$")


class Markup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            self.ids.append(values["id"])
        if tag == "a":
            self.hrefs.append(values.get("href"))


class RecoveryActionValueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(RECEIPT.read_text(encoding="utf-8"))
        cls.html = VIEW.read_text(encoding="utf-8")
        cls.dom = Markup()
        cls.dom.feed(cls.html)

    def test_baseline_exact_sha_and_distinct_run_job(self):
        d = self.data
        self.assertEqual(d["schema"], "abacus.recovery.action-value.v1")
        self.assertTrue(SHA.fullmatch(d["baseline"]["main_sha"]))
        self.assertTrue(SHA.fullmatch(d["candidates"]["documentation"]["head_sha"]))
        self.assertGreater(d["baseline"]["docs"]["run_id"], 0)
        self.assertGreater(d["baseline"]["docs"]["job_id"], 0)
        self.assertEqual(d["baseline"]["docs"]["finding_count"], 13)
        self.assertEqual(sum(d["baseline"]["docs"]["findings_by_rule"].values()), 13)

    def test_current_unknown_and_no_fabricated_acceptance(self):
        d = self.data
        m = d["metrics_contract"]
        self.assertEqual(m["docs_after_count"], 0)
        self.assertEqual(m["docs_reduction_count"], 13)
        self.assertEqual(m["docs_native_verify"], "VERIFIED_EXACT_HEAD_PR_NOT_MAIN")
        self.assertEqual(m["docs_verified_job_id"], 115941877977)
        self.assertIsNone(m["verified_unblocked_downstream_jobs"])
        self.assertIsNone(m["verified_closed_bd_roots"])
        self.assertIsNone(m["verified_authenticated_crew_launches"])
        self.assertIsNone(m["accepted_rex_returns"])
        self.assertFalse(d["coverage"]["scope_parity_verified"])
        self.assertIsNone(d["coverage"]["current_main_comparable_pct"])
        self.assertIsNone(d["coverage"]["current_pr_diff_comparable_pct"])
        self.assertFalse(d["governance"]["security_waiver"])
        self.assertFalse(d["governance"]["authority_transfer"])
        self.assertEqual(d["governance"]["observed_enforced_rule_count"], 0)

    def test_native_docs_receipt_is_pr_scoped_not_current_main(self):
        d = self.data["candidates"]["documentation"]
        self.assertEqual(d["comparison_status"], "VERIFIED_TERMINAL_EXACT_HEAD_PR_ONLY")
        self.assertEqual(d["workflow_run_id"], 38589957927)
        self.assertEqual(d["job_id"], 115941877977)
        self.assertEqual(d["workflow_run_conclusion"], "success")
        self.assertEqual(d["job_conclusion"], "success")
        self.assertEqual(d["after_findings"], 0)
        self.assertTrue(SHA.fullmatch(d["head_sha"]))
        self.assertIn("const recorded=c.comparison_status===", self.html)
        self.assertIsNone(self.data["metrics_contract"]["verified_closed_bd_roots"])

    def test_native_scoped_ruff_receipt_is_not_full_dow_clearance(self):
        r = self.data["candidates"]["dow_ruff"]
        self.assertEqual(r["tool"], "ruff==0.17.0")
        self.assertTrue(SHA.fullmatch(r["head_sha"]))
        self.assertEqual(r["before_findings"], 11)
        self.assertEqual(r["after_findings"], 0)
        self.assertEqual(r["opened_occurrences"], 0)
        self.assertEqual(r["resolved_occurrences"], 11)
        self.assertEqual(r["net_reduction"], 11)
        self.assertEqual(len(r["identical_scoped_paths"]), 4)
        self.assertEqual(len(r["formatting_identical_paths"]), 3)
        self.assertEqual(r["formatting_before"]["trailing_whitespace_lines"], 9)
        self.assertEqual(r["formatting_after"]["trailing_whitespace_lines"], 0)
        self.assertEqual(r["formatting_before"]["missing_final_newline_files"], 2)
        self.assertEqual(r["formatting_after"]["missing_final_newline_files"], 0)
        self.assertEqual(r["focused_regression_pass"], 6)
        self.assertEqual(r["mainwide_precommit"], "NOT_VERIFIED")
        self.assertTrue(r["artifact_zip_sha256"])
        self.assertIsNone(
            self.data["metrics_contract"]["verified_unblocked_downstream_jobs"]
        )
        self.assertIn("r.before_findings===11&&r.after_findings===0", self.html)

    def test_main_coverage_is_measured_not_baseline_comparable(self):
        m = self.data["coverage"]["measured_main_at_sha"]
        self.assertEqual(m["exact_main_sha"], self.data["baseline"]["main_sha"])
        self.assertEqual(m["job_conclusion"], "success")
        self.assertEqual(m["covered_lines"], 17088)
        self.assertEqual(m["num_statements"], 30735)
        self.assertEqual(m["covered_branches"], 4200)
        self.assertEqual(m["num_branches"], 8290)
        combined = (
            100
            * (m["covered_lines"] + m["covered_branches"])
            / (m["num_statements"] + m["num_branches"])
        )
        self.assertAlmostEqual(m["percent_combined_covered"], combined, places=2)
        self.assertEqual(m["scope_vs_historical_main"], "NOT_RECONCILED")
        self.assertIsNone(m["comparable_delta_to_36_85_pp"])
        self.assertIsNone(self.data["coverage"]["current_main_comparable_pct"])
        self.assertAlmostEqual(
            self.data["coverage"]["latest_main_measured_pct"], 54.65392575180766
        )
        current = self.data["coverage"]["current_main_measured"]
        self.assertEqual(
            current["exact_main_sha"], self.data["coverage"]["latest_main_readback_sha"]
        )
        self.assertEqual(current["covered_lines"], 17158)
        self.assertEqual(current["num_statements"], 30815)
        self.assertEqual(current["covered_branches"], 4233)
        self.assertEqual(current["num_branches"], 8324)
        self.assertEqual(
            current["source_additions"], ["scripts/dow_first_red_census.py"]
        )
        self.assertEqual(current["existing_file_coverage_changed_count"], 0)
        cohort = self.data["coverage"]["sequential_main_comparison"]
        self.assertAlmostEqual(cohort["delta_percentage_points"], 0.1042780900523752)
        self.assertEqual(cohort["common_files"], 298)
        self.assertFalse(cohort["same_source_denominator"])
        self.assertIn("currentMeasure.exact_main_sha===liveSha", self.html)
        self.assertIn("liveSha===m.exact_main_sha", self.html)
        self.assertIn("main advanced since measured source", self.html)
        self.assertIn("historical comparison NOT COMPARABLE", self.html)

    def test_current_main_reds_do_not_erase_pr_scoped_repairs(self):
        d = self.data["current_main_first_reds"]
        self.assertEqual(
            d["exact_main_sha"], self.data["coverage"]["latest_main_readback_sha"]
        )
        self.assertEqual(d["docs"]["finding_count"], 33)
        self.assertEqual(len(d["docs"]["files"]), 2)
        self.assertIsNone(d["docs"]["verified_after_count"])
        self.assertEqual(d["workflow_governance"]["unclassified_workflow_count"], 2)
        self.assertIsNone(d["workflow_governance"]["verified_after_count"])
        self.assertEqual(d["docs"]["candidate_pr"], 1972)
        self.assertEqual(d["workflow_governance"]["candidate_pr"], 1973)
        self.assertEqual(self.data["metrics_contract"]["docs_reduction_count"], 13)
        self.assertIn("liveSha===reds.exact_main_sha", self.html)
        self.assertIn("separate from #1966", self.html)

    def test_p0_ruleset_is_partial_and_not_merge_authority(self):
        g = self.data["governance"]["recovery_observation"]
        self.assertEqual(g["schema"], "abacus.p0.ruleset-readback.v1")
        self.assertTrue(SHA.fullmatch(g["observed_main_sha"]))
        self.assertTrue(g["branch_protected"])
        self.assertEqual(g["ruleset_id"], 24494381)
        self.assertEqual(g["ruleset_rule_count"], 3)
        self.assertEqual(g["ruleset_bypass_actor_count"], 0)
        self.assertEqual(g["required_approvals"], 1)
        self.assertFalse(g["required_status_checks_present_in_observed_ruleset"])
        self.assertIsNone(g["independent_review_receipt"])
        self.assertEqual(g["admission"], "HOLD")
        self.assertIn("main protected=true", self.html)
        self.assertIn("required CI checks NOT observed", self.html)
        self.assertIn('active.enforcement!=="active"', self.html)
        self.assertIn("liveSha===gov.observed_main_sha", self.html)
        self.assertIn("#governance", self.dom.hrefs)
        self.assertIn("governance", self.dom.ids)

    def test_dow_root_count_distinct_from_downstream_skip(self):
        d = self.data["baseline"]["dow"]
        self.assertEqual(d["failed_hook_count"], 3)
        self.assertEqual(len(d["failure_signatures"]), 3)
        self.assertEqual(len(d["skipped_jobs"]), 6)
        self.assertEqual(d["observed_downstream_skipped"], 6)

    def test_unique_ids_and_navigation_targets(self):
        self.assertEqual(len(self.dom.ids), len(set(self.dom.ids)))
        for anchor in ("summary", "docs", "dow", "coverage", "provenance"):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, self.dom.ids)
                self.assertIn("#" + anchor, self.dom.hrefs)
        self.assertIn('aria-live="polite"', self.html)
        self.assertIn("prefers-reduced-motion", self.html)

    def test_native_success_requires_run_and_job_identity(self):
        code = self.html
        for guard in (
            "run.head_sha!==c.head_sha",
            "run.name!==c.workflow_name",
            'run.status!=="completed"',
            'run.conclusion!=="success"',
            "jobs.total_count!==jobs.jobs.length",
            "candidates.length!==1",
            'j.conclusion!=="success"',
            "j.head_sha!==c.head_sha",
        ):
            with self.subTest(guard=guard):
                self.assertIn(guard, code)
        self.assertIn('put("after",0)', code)

    def test_no_mutation_and_no_automatic_merging(self):
        self.assertNotIn("method:'POST'", self.html)
        self.assertNotIn('method:"POST"', self.html)
        self.assertNotIn('method:"PATCH"', self.html)
        self.assertIn("PR-side clearance is not current-main clearance", self.html)
        self.assertIn("No automatic admission", self.html)


if __name__ == "__main__":
    unittest.main()
