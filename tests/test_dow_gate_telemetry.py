"""Exact-head, graph fan-out and UNKNOWN regression controls for DOW telemetry."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from dow_gate_telemetry import (
    build, coverage, markdown, mermaid, select_runs, workflow_dag,
)

MAIN = "a" * 40
HEAD = "b" * 40
YAML = """
jobs:
  lint-and-validate:
    name: Lint & Validate
  ci-ubuntu:
    name: CI - Ubuntu
    needs: lint-and-validate
  ci-rhel-8:
    name: CI - RHEL 8
    needs: lint-and-validate
  ci-rhel-9:
    name: CI - RHEL 9
    needs: lint-and-validate
  dmaic-full-cycle:
    name: DMAIC Full Cycle
    needs: [ci-ubuntu, ci-rhel-8, ci-rhel-9]
  build-artifacts:
    name: Build Release Artifacts
    needs: dmaic-full-cycle
  release:
    name: Create GitHub Release
    needs: build-artifacts
"""


def run(name, number, sha, state="completed", result="success"):
    return {"name": name, "id": number, "head_sha": sha,
            "status": state, "conclusion": result,
            "created_at": "2026-10-14T15:00:00Z", "run_attempt": 1,
            "html_url": f"https://github.com/GBOGEB/ABACUS/actions/runs/{number}"}


def inputs(**overrides):
    kwargs = {
        "main_sha": MAIN, "head_sha": HEAD,
        "main_branch": {"commit": {"sha": MAIN}, "protected": False},
        "main_runs": {"total_count": 0, "workflow_runs": []},
        "head_runs": {"total_count": 0, "workflow_runs": []},
        "dow_jobs": None, "workflow": YAML,
    }
    kwargs.update(overrides)
    return build(**kwargs)


class RemainingGateTests(unittest.TestCase):
    def test_empty_producers_do_not_create_zeroes(self):
        result = inputs()
        self.assertEqual(result["gates"]["lint-and-validate"]["status"], "UNKNOWN")
        self.assertIsNone(result["gates"]["canonical_main_coverage"]["numerator"])
        self.assertIsNone(result["gates"]["changed_line_coverage"]["denominator"])
        self.assertIsNone(result["gates"]["bd_distinct_roots"]["closed"])
        self.assertIsNone(result["gates"]["crew_ldb_rex"]["authenticated_launches"])
        self.assertFalse(result["admission"]["merge_authorized"])
        self.assertEqual(result["gates"]["governance_owner"]["status"], "DEFERRED_OWNER_ACTION")

    def test_dow_dependency_centrality_six_distinct_descendants(self):
        result = inputs()
        self.assertEqual(result["critical_nodes"][0]["job_id"], "lint-and-validate")
        self.assertEqual(result["critical_nodes"][0]["potential_descendants"], 6)
        self.assertIn("J0 --> J1", mermaid(result))

    def test_native_skipped_remains_skipped(self):
        stages = [
            ("Lint & Validate", "failure"),
            ("CI - Ubuntu", "skipped"),
            ("CI - RHEL 8", "skipped"),
            ("CI - RHEL 9", "skipped"),
            ("DMAIC Full Cycle", "skipped"),
            ("Build Release Artifacts", "skipped"),
            ("Create GitHub Release", "skipped"),
        ]
        payload = {"total_count": 7, "jobs": [
            {"id": i + 100, "name": name, "status": "completed",
             "conclusion": outcome,
             "html_url": f"https://github.com/GBOGEB/ABACUS/actions/jobs/{i+100}"}
            for i, (name, outcome) in enumerate(stages)
        ]}
        result = inputs(
            main_runs={"total_count": 1, "workflow_runs": [run(
                "DOW + Recursive DMAIC - Unified CD Pipeline", 921, MAIN,
                result="failure")]},
            dow_jobs=payload,
        )
        self.assertEqual(result["gates"]["lint-and-validate"]["status"], "FAIL")
        self.assertEqual(result["gates"]["ci-rhel-8"]["status"], "SKIPPED")
        self.assertEqual(result["gates"]["ci-rhel-9"]["status"], "SKIPPED")
        self.assertEqual(result["gates"]["build-artifacts"]["status"], "SKIPPED")
        self.assertNotEqual(result["gates"]["dmaic-full-cycle"]["status"], "PASS")

    def test_queued_dow_does_not_infer_missing_runner_or_downstream(self):
        partial_jobs = {"total_count": 1, "jobs": [
            {"id": 555, "name": "Lint & Validate",
             "status": "queued", "conclusion": None}
        ]}
        result = inputs(
            main_runs={"total_count": 1, "workflow_runs": [run(
                "DOW + Recursive DMAIC - Unified CD Pipeline", 921, MAIN,
                state="queued", result=None)]},
            dow_jobs=partial_jobs,
        )
        self.assertEqual(result["gates"]["lint-and-validate"]["status"], "QUEUED")
        self.assertEqual(result["gates"]["ci-rhel-8"]["status"], "UNKNOWN")
        self.assertEqual(result["gates"]["ci-rhel-9"]["status"], "UNKNOWN")
        self.assertEqual(result["gates"]["build-artifacts"]["status"], "UNKNOWN")

    def test_security_needs_all_four_exact_head_producers(self):
        items = [
            run("Security Scan — Ruff", 1, HEAD),
            run("Semgrep", 2, HEAD),
            run("OSV-Scanner", 3, HEAD),
            run("DELTA_1 CodeQL", 4, HEAD),
        ]
        result = inputs(head_runs={"total_count": 4, "workflow_runs": items})
        self.assertEqual(result["gates"]["security"]["status"], "PASS")
        result = inputs(head_runs={"total_count": 4, "workflow_runs": items[:3]})
        self.assertEqual(result["gates"]["security"]["status"], "UNKNOWN")

    def test_stale_sha_and_main_drift_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "Main ref drift"):
            inputs(main_branch={"commit": {"sha": HEAD}, "protected": False})
        with self.assertRaisesRegex(ValueError, "Mixed-SHA"):
            inputs(head_runs={"total_count": 1, "workflow_runs": [run("CI/CD Test Suite", 1, MAIN)]})
        with self.assertRaisesRegex(ValueError, "40-character"):
            inputs(head_sha="short")

    def test_partial_page_never_proves_absence(self):
        result, complete = select_runs(
            {"total_count": 11, "workflow_runs": [run("Semgrep", 3, HEAD)]}, HEAD)
        self.assertFalse(complete)
        self.assertEqual(len(result), 1)
        self.assertEqual(inputs(head_runs={
            "total_count": 11, "workflow_runs": [run("Semgrep", 3, HEAD)]
        })["gates"]["full_ci"]["status"], "UNKNOWN")

    def test_comparable_coverage_requires_numerators_and_identity(self):
        row = {"sha": MAIN, "kind": "canonical", "covered": 20_651,
               "eligible": 38_223, "scope_id": "b0-combined",
               "config_sha256": "c" * 64, "run_id": 123, "artifact_id": 987}
        result = inputs(coverage_data={"receipts": [row]})
        self.assertEqual(result["gates"]["canonical_main_coverage"]["numerator"], 20_651)
        self.assertEqual(result["gates"]["canonical_main_coverage"]["denominator"], 38_223)
        self.assertIsNone(result["gates"]["changed_line_coverage"]["numerator"])
        with self.assertRaisesRegex(ValueError, "invalid units"):
            coverage({"receipts": [dict(row, eligible=0)]}, MAIN, "canonical")

    def test_dag_cycle_rejected(self):
        with self.assertRaisesRegex(ValueError, "Cycle"):
            workflow_dag("jobs:\n  A:\n    needs: B\n  B:\n    needs: A\n")

    def test_markdown_is_traceable_not_pass_rate(self):
        report = inputs()
        self.assertIn(MAIN, markdown(report))
        self.assertIn("not a pass rate", report["observation_completeness"]["meaning"])
        self.assertIn("UNKNOWN", markdown(report))


if __name__ == "__main__":
    unittest.main()
