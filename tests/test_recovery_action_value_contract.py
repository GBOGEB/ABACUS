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
        self.assertIsNone(m["docs_after_count"])
        self.assertIsNone(m["docs_reduction_count"])
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
        self.assertIn('r.before_findings===11&&r.after_findings===0', self.html)

    def test_main_coverage_is_measured_not_baseline_comparable(self):
        m = self.data["coverage"]["current_main_measured"]
        self.assertEqual(m["exact_main_sha"], self.data["baseline"]["main_sha"])
        self.assertEqual(m["job_conclusion"], "success")
        self.assertEqual(m["covered_lines"], 17088)
        self.assertEqual(m["num_statements"], 30735)
        self.assertEqual(m["covered_branches"], 4200)
        self.assertEqual(m["num_branches"], 8290)
        combined = 100 * (m["covered_lines"] + m["covered_branches"]) / (
            m["num_statements"] + m["num_branches"]
        )
        self.assertAlmostEqual(m["percent_combined_covered"], combined, places=2)
        self.assertEqual(m["scope_vs_historical_main"], "NOT_RECONCILED")
        self.assertIsNone(m["comparable_delta_to_36_85_pp"])
        self.assertIsNone(self.data["coverage"]["current_main_comparable_pct"])
        self.assertIn("historical comparison NOT COMPARABLE", self.html)

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
