"""Exact-head, graph fan-out and UNKNOWN regression controls for DOW telemetry."""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from dow_gate_telemetry import (
    affected, build, coverage, job_census, load, main, markdown, mermaid,
    run_state, select_runs, workflow_dag, workflow_gate,
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


    def test_load_optional_and_invalid_json_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(load(root, "missing.json"))
            (root / "receipt.json").write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not a JSON object"):
                load(root, "receipt.json")
            (root / "receipt.json").write_text('{"ok": true}', encoding="utf-8")
            self.assertEqual(load(root, "receipt.json"), {"ok": True})

    def test_run_state_all_nonterminal_and_unsupported(self):
        self.assertEqual(run_state({"status": "queued"}), "QUEUED")
        self.assertEqual(run_state({"status": "in_progress"}), "RUNNING")
        self.assertEqual(run_state({"status": "completed", "conclusion": "cancelled"}), "CANCELLED")
        self.assertEqual(run_state({"status": "completed", "conclusion": "neutral"}), "NEUTRAL")
        self.assertEqual(run_state({"status": "completed", "conclusion": "failure"}), "FAIL")
        self.assertEqual(run_state({"status": "completed", "conclusion": "unknown"}), "UNKNOWN")

    def test_workflow_gate_negative_state_priority(self):
        name = ("Gate",)
        for state, conclusion, expected in (
            ("completed", "failure", "FAIL"),
            ("completed", "action_required", "HOLD"),
            ("queued", None, "NONTERMINAL"),
            ("in_progress", None, "NONTERMINAL"),
            ("completed", "skipped", "NOT_PROVED"),
            ("completed", "neutral", "NOT_PROVED"),
            ("completed", "unclassified", "UNKNOWN"),
        ):
            with self.subTest(state=state, conclusion=conclusion):
                item = run("Gate", 77, HEAD, state=state, result=conclusion)
                self.assertEqual(
                    workflow_gate({"Gate": item}, name, True)["status"],
                    expected,
                )
        self.assertEqual(workflow_gate({}, name, False)["status"], "UNKNOWN")
        self.assertEqual(workflow_gate({}, name, True)["status"], "NOT_OBSERVED")

    def test_run_index_rejects_bad_identity_and_pagination(self):
        item = run("CI/CD Test Suite", 12, HEAD)
        mutations = [
            ({"total_count": 0, "workflow_runs": [item]}, "pagination"),
            ({"total_count": 1, "workflow_runs": [None]}, "Malformed"),
            ({"total_count": 1, "workflow_runs": [dict(item, name="")]}, "identity"),
            ({"total_count": 1, "workflow_runs": [dict(item, id="12")]}, "Run ID"),
            ({"total_count": 1, "workflow_runs": [dict(item, run_attempt="1")]}, "Run ID"),
            ({"total_count": 1, "workflow_runs": [dict(item, html_url="bogus")]}, "URL"),
        ]
        for payload, message in mutations:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    select_runs(payload, HEAD)
        older = dict(item, id=11, created_at="2026-10-13T00:00:00Z")
        selected, complete = select_runs(
            {"total_count": 2, "workflow_runs": [older, item]}, HEAD
        )
        self.assertTrue(complete)
        self.assertEqual(selected["CI/CD Test Suite"]["id"], 12)
        self.assertEqual(select_runs(None, HEAD), ({}, False))

    def test_dag_bad_structures_and_missing_source(self):
        for source in ("[]", "jobs: []", "jobs:\n  A: bad\n"):
            with self.subTest(source=source):
                with self.assertRaisesRegex(ValueError, "jobs absent|Malformed job"):
                    workflow_dag(source)
        with self.assertRaisesRegex(ValueError, "Unknown workflow dependency"):
            workflow_dag("jobs:\n  A:\n    needs: [MISSING]\n")
        with self.assertRaisesRegex(ValueError, "Unknown DOW job"):
            affected(workflow_dag(YAML), "missing")
        dag = workflow_dag("jobs:\n  A: {}\n  B:\n    needs: A\n")
        self.assertEqual(affected(dag, "A"), ["B"])

    def test_dow_job_receipt_validation_and_latest_job(self):
        dag = workflow_dag(YAML)
        dow = run("DOW + Recursive DMAIC - Unified CD Pipeline", 921, MAIN)
        row = {"id": 123, "name": "Lint & Validate", "status": "completed",
               "conclusion": "failure", "html_url": "https://github.com/ok"}
        mutations = [
            ({"total_count": 0, "jobs": [row]}, "denominator"),
            ({"total_count": 1, "jobs": [None]}, "Invalid job ID"),
            ({"total_count": 1, "jobs": [dict(row, run_id=777)]}, "Foreign run"),
            ({"total_count": 1, "jobs": [dict(row, name=None)]}, "Unnamed job"),
        ]
        for payload, message in mutations:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    job_census(payload, dow, dag)
        newer = dict(row, id=124, status="completed", conclusion="success")
        data = job_census(
            {"total_count": 2, "jobs": [row, newer]}, dow, dag
        )
        self.assertEqual(data["jobs"]["lint-and-validate"]["job_id"], 124)
        self.assertEqual(data["jobs"]["lint-and-validate"]["status"], "PASS")
        self.assertEqual(data["jobs"]["ci-ubuntu"]["status"], "NOT_OBSERVED")

    def test_coverage_wrong_base_duplicate_and_diff_provenance(self):
        receipt = {
            "kind": "diff", "sha": HEAD, "base_sha": MAIN,
            "covered": 87, "eligible": 100,
            "scope_id": "changed-lines", "config_sha256": "c" * 64,
            "run_id": 10, "artifact_id": 12,
        }
        self.assertEqual(
            coverage({"receipts": [receipt]}, HEAD, "diff", MAIN)["numerator"],
            87,
        )
        self.assertEqual(
            coverage({"receipts": [receipt]}, HEAD, "diff", "d" * 40)["status"],
            "UNKNOWN",
        )
        self.assertEqual(
            coverage({"receipts": [receipt, receipt]}, HEAD, "diff", MAIN)["status"],
            "UNKNOWN",
        )
        with self.assertRaisesRegex(ValueError, "receipts must be a list"):
            coverage({"receipts": "incorrect"}, HEAD, "diff", MAIN)
        with self.assertRaisesRegex(ValueError, "provenance"):
            coverage({"receipts": [dict(receipt, artifact_id=None)]},
                     HEAD, "diff", MAIN)

    def test_cli_writes_three_evidence_outputs_without_runtime_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = root / "snapshots"
            out = root / "outputs"
            snapshot.mkdir()
            (snapshot / "branch.json").write_text(
                json.dumps({"commit": {"sha": MAIN}, "protected": False}),
                encoding="utf-8",
            )
            for name in ("main-runs.json", "head-runs.json"):
                (snapshot / name).write_text(
                    json.dumps({"total_count": 0, "workflow_runs": []}),
                    encoding="utf-8",
                )
            workflow = root / "dow.yml"
            workflow.write_text(YAML, encoding="utf-8")
            args = [
                "dow_gate_telemetry.py", "--snapshot-dir", str(snapshot),
                "--workflow", str(workflow), "--main-sha", MAIN,
                "--head-sha", HEAD, "--output-dir", str(out),
            ]
            with patch.object(sys, "argv", args), redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 0)
            payload = json.loads(
                (out / "remaining-gates.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["source"]["main_sha"], MAIN)
            self.assertEqual(payload["gates"]["ci-rhel-9"]["status"], "UNKNOWN")
            self.assertFalse(payload["admission"]["merge_authorized"])
            self.assertIn("flowchart LR",
                          (out / "remaining-gates.mmd").read_text())
            self.assertIn("Highest dependency fan-out",
                          (out / "remaining-gates.md").read_text())

    def test_markdown_includes_native_identifiers_and_distinct_denominators(self):
        report = inputs()
        report["gates"]["lint-and-validate"].update({
            "job_id": 391, "status": "FAIL", "downstream_count": 6,
        })
        report["gates"]["canonical_main_coverage"].update({
            "numerator": 80, "denominator": 100,
        })
        report["gates"]["bd_distinct_roots"]["closed"] = 2
        out = markdown(report)
        self.assertIn("job 391", out)
        self.assertIn("80/100", out)
        self.assertIn("closed roots 2", out)
        self.assertIn("potential descendants 6", out)



    def test_concurrent_pages_are_partial_not_false_terminal(self):
        first = run("CI/CD Test Suite", 20, HEAD)
        second = run("Security Scan — Ruff", 21, HEAD)
        unstable = {
            "total_count": 2,
            "source_complete": False,
            "workflow_runs": [first, second],
        }
        selected, complete = select_runs(unstable, HEAD)
        self.assertFalse(complete)
        self.assertEqual(len(selected), 2)
        result = inputs(head_runs=unstable)
        self.assertEqual(result["gates"]["security"]["status"], "UNKNOWN")

    def test_dow_partial_jobs_do_not_overstate_runner_completion(self):
        dag = workflow_dag(YAML)
        origin = run("DOW + Recursive DMAIC - Unified CD Pipeline", 31, MAIN)
        snapshot = {
            "total_count": 1,
            "source_complete": False,
            "jobs": [
                {"id": 201, "name": "Lint & Validate",
                 "status": "completed", "conclusion": "failure"},
                {"id": 202, "name": "CI - RHEL 8",
                 "status": "completed", "conclusion": "skipped"},
            ],
        }
        result = job_census(snapshot, origin, dag)
        self.assertEqual(result["completeness"], "PARTIAL")
        self.assertEqual(result["jobs"]["lint-and-validate"]["status"], "FAIL")
        self.assertEqual(result["jobs"]["ci-rhel-8"]["status"], "SKIPPED")
        self.assertEqual(result["jobs"]["ci-rhel-9"]["status"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
