"""Adversarial first-red/coverage/worker-boundary tests (stdlib)."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "gogreen_first_red_wave",
    Path(__file__).resolve().parents[1] / "scripts" / "gogreen_first_red_wave.py",
)
assert SPEC and SPEC.loader
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)

A = "a" * 40
B = "b" * 40


def row(
    pr=2072,
    sha=A,
    run=38921508083,
    job_id=117042431431,
    workflow="CI - ABACUS Matrix",
    job="ABACUS - ubuntu-24.04 - Python 3.10",
    step="Install tooling",
):
    return {
        "pr": pr,
        "head_sha": sha,
        "run_id": run,
        "run_attempt": 1,
        "job_id": job_id,
        "step_number": 4,
        "workflow": workflow,
        "job": job,
        "first_red_step": step,
        "job_conclusion": "failure",
        "evidence_class": "GITHUB_NATIVE_JOB_STEP_METADATA",
        "run_url": f"https://github.com/GBOGEB/ABACUS/actions/runs/{run}",
    }


def sample():
    return {
        "schema": subject.SCHEMA,
        "repository": "GBOGEB/ABACUS",
        "source_heads": [{"pr": 2072, "head_sha": A}, {"pr": 2068, "head_sha": B}],
        "observations": [row(), row(2068, B, 38907755180, 116997318096)],
        "coverage": [],
        "coverage_comparisons": [],
        "merge_authorized": False,
        "security_waiver": False,
        "authority_transfer": False,
    }


def cov(pr, sha, covered=90, branches=8):
    return {
        "pr": pr,
        "source_sha": sha,
        "branch_mode": True,
        "tool_version": "coverage-7.13",
        "scope_id": "same-module-set",
        "test_selection": "test-same",
        "module_fingerprint": "sha256:known",
        "eligible_statements": 100,
        "covered_statements": covered,
        "eligible_branches": 10,
        "covered_branches": branches,
        "eligible_changed_lines": 20,
        "covered_changed_lines": 15,
    }


class FirstRedWave(unittest.TestCase):
    def test_real_native_readback_fixture_proves_six_candidate_buckets(self):
        fixture = (
            Path(__file__).resolve().parent
            / "fixtures"
            / "gogreen_n1_native_first_red_sample.json"
        )
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        result = subject.analyze(payload)
        self.assertEqual(result["source_heads_observed"], 6)
        self.assertEqual(result["observations_supplied"], 12)
        self.assertEqual(result["unique_native_failed_jobs"], 12)
        self.assertEqual(result["candidate_signature_count"], 6)
        self.assertEqual(result["candidate_ranking"][0]["pr_count"], 3)
        self.assertEqual(result["accepted_root_count"], 0)
        self.assertIsNone(result["forecast_verified_unblocked_prs"])

    def test_aliased_accepted_root_preserves_proven_root_pr_set(self):
        x = sample()
        x["source_heads"].append({"pr": 2083, "head_sha": A})
        for o in x["observations"]:
            o.update(
                root_id="ROOT101",
                root_owner="root owner",
                owner_disposition="ACCEPTED",
                root_evidence_url="https://github.com/GBOGEB/ABACUS/issues/2026",
            )
        alias = copy.deepcopy(x["observations"][0])
        alias["pr"] = 2083
        x["observations"].append(alias)
        res = subject.analyze(x)
        self.assertEqual(res["unique_native_failed_jobs"], 2)
        self.assertEqual(res["owner_accepted_roots"][0]["prs"], [2068, 2072, 2083])

    def test_real_native_python_install_signature_is_candidate_not_root(self):
        x = subject.analyze(sample())
        self.assertEqual(x["source_heads_observed"], 2)
        self.assertEqual(x["unique_native_failed_jobs"], 2)
        self.assertEqual(x["candidate_signature_count"], 1)
        self.assertEqual(x["candidate_ranking"][0]["pr_count"], 2)
        self.assertEqual(x["candidate_ranking"][0]["prs"], [2068, 2072])
        self.assertIsNone(x["candidate_ranking"][0]["causal_root_id"])
        self.assertEqual(x["owner_accepted_roots"], [])
        self.assertFalse(x["merge_authorized"])
        self.assertIsNone(x["current_main_coverage"])

    def test_evidence_duplicates_do_not_inflate_run_count(self):
        x = sample()
        x["observations"].append(copy.deepcopy(x["observations"][0]))
        p = subject.analyze(x)
        self.assertEqual(p["unique_native_failed_jobs"], 2)
        self.assertEqual(p["duplicates_deduplicated"], 1)

    def test_shared_native_run_alias_retains_both_prs_once(self):
        x = sample()
        x["source_heads"].append({"pr": 2083, "head_sha": A})
        alias = copy.deepcopy(x["observations"][0])
        alias["pr"] = 2083
        x["observations"].append(alias)
        y = subject.analyze(x)
        self.assertEqual(y["unique_native_failed_jobs"], 2)
        self.assertEqual(y["duplicates_deduplicated"], 1)
        self.assertEqual(y["candidate_ranking"][0]["pr_count"], 3)
        self.assertEqual(y["candidate_ranking"][0]["prs"], [2068, 2072, 2083])

    def test_conflicting_duplicate_native_identity_fails(self):
        x = sample()
        bad = copy.deepcopy(x["observations"][0])
        bad["first_red_step"] = "Different actual step"
        x["observations"].append(bad)
        with self.assertRaisesRegex(ValueError, "conflicting duplicate"):
            subject.analyze(x)

    def test_stale_head_is_rejected(self):
        x = sample()
        x["observations"][0]["head_sha"] = B
        with self.assertRaisesRegex(ValueError, "stale or foreign"):
            subject.analyze(x)

    def test_duplicate_pr_head_rejected(self):
        x = sample()
        x["source_heads"].append(copy.deepcopy(x["source_heads"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate PR"):
            subject.analyze(x)

    def test_short_sha_rejected(self):
        x = sample()
        x["source_heads"][0]["head_sha"] = "abc"
        with self.assertRaisesRegex(ValueError, "invalid PR/head"):
            subject.analyze(x)

    def test_source_authority_mutation_rejected(self):
        for field, value in (
            ("merge_authorized", True),
            ("authority_transfer", True),
            ("security_waiver", True),
        ):
            with self.subTest(field=field):
                x = sample()
                x[field] = value
                with self.assertRaisesRegex(ValueError, "authority"):
                    subject.analyze(x)

    def test_fabricated_accepted_root_rejected(self):
        x = sample()
        x["observations"][0]["root_id"] = "ROOT101"
        with self.assertRaisesRegex(ValueError, "owner accepted"):
            subject.analyze(x)

    def test_owner_approved_root_evidence_separately_classified(self):
        x = sample()
        for item in x["observations"]:
            item.update(
                root_id="ROOT101",
                root_owner="requirements-owner",
                owner_disposition="ACCEPTED",
                root_evidence_url="https://github.com/GBOGEB/ABACUS/issues/2026",
            )
        y = subject.analyze(x)
        self.assertEqual(y["accepted_root_count"], 1)
        self.assertEqual(
            y["owner_accepted_roots"][0]["potential_pr_unblock_upper_bound"], 2
        )
        self.assertIsNone(y["forecast_verified_unblocked_prs"])

    def test_downstream_summary_not_a_causal_root(self):
        x = sample()
        item = x["observations"][0]
        item.update(
            job="Full Red Proof Summary", first_red_step="Emit full-red summary"
        )
        p = subject.analyze(x)
        self.assertEqual(p["downstream_summary_jobs"], 1)
        self.assertEqual(p["candidate_signature_count"], 1)
        item.update(
            root_id="R01",
            root_owner="owner",
            owner_disposition="ACCEPTED",
            root_evidence_url="https://github.com/GBOGEB/ABACUS/issues/1929",
        )
        with self.assertRaisesRegex(ValueError, "downstream"):
            subject.analyze(x)

    def test_wrong_url_and_class_rejected(self):
        for field, value, regex in (
            ("run_url", "https://example.org/run", "URL"),
            ("evidence_class", "MODEL_GUESS", "evidence class"),
        ):
            with self.subTest(field=field):
                x = sample()
                x["observations"][0][field] = value
                with self.assertRaisesRegex(ValueError, regex):
                    subject.analyze(x)

    def test_pending_job_cannot_be_red_proof(self):
        x = sample()
        x["observations"][0]["job_conclusion"] = "skipped"
        with self.assertRaisesRegex(ValueError, "nonfailing"):
            subject.analyze(x)

    def test_negative_run_attempt_id(self):
        x = sample()
        x["observations"][0]["run_attempt"] = 0
        with self.assertRaisesRegex(ValueError, "run_attempt"):
            subject.analyze(x)

    def test_mixed_heads_in_same_run_attempt_rejected(self):
        x = sample()
        x["observations"][1]["run_id"] = x["observations"][0]["run_id"]
        x["observations"][1]["run_url"] = x["observations"][0]["run_url"]
        with self.assertRaisesRegex(ValueError, "mixed source heads"):
            subject.analyze(x)

    def test_coverage_comparable_delta_is_scope_bound(self):
        x = sample()
        x["coverage"] = [cov(2072, A, 80, 6), cov(2068, B, 90, 8)]
        x["coverage_comparisons"] = [{"baseline_pr": 2072, "candidate_pr": 2068}]
        res = subject.analyze(x)
        self.assertEqual(res["coverage_comparisons"][0]["status"], "MATCHED")
        self.assertEqual(res["coverage_comparisons"][0]["combined_delta_pp"], 10.9091)

    def test_coverage_module_drift_never_claims_increase(self):
        x = sample()
        r = cov(2068, B)
        r["module_fingerprint"] = "new-module-set"
        x["coverage"] = [cov(2072, A), r]
        x["coverage_comparisons"] = [{"baseline_pr": 2072, "candidate_pr": 2068}]
        res = subject.analyze(x)["coverage_comparisons"][0]
        self.assertEqual(res["status"], "INCOMPARABLE")
        self.assertIsNone(res["combined_delta_pp"])

    def test_coverage_stale_sha_rejected(self):
        x = sample()
        x["coverage"] = [cov(2072, B)]
        with self.assertRaisesRegex(ValueError, "coverage source/head"):
            subject.analyze(x)

    def test_coverage_overclaim_and_skip_branch_rejected(self):
        for kind in ("overclaim", "no_branch"):
            with self.subTest(kind=kind):
                x = sample()
                r = cov(2072, A)
                if kind == "overclaim":
                    r["covered_changed_lines"] = 21
                else:
                    r["branch_mode"] = False
                x["coverage"] = [r]
                with self.assertRaises(ValueError):
                    subject.analyze(x)

    def test_no_changed_lines_means_unknown_not_hundred(self):
        x = sample()
        r = cov(2072, A)
        r["eligible_changed_lines"] = 0
        r["covered_changed_lines"] = 0
        x["coverage"] = [r]
        self.assertIsNone(subject.analyze(x)["coverage"]["2072"]["changed_line_pct"])

    def test_four_readonly_scouts_and_zero_unleased_writers(self):
        x = sample()
        x["source_heads"] = [{"pr": i, "head_sha": A} for i in range(1, 8)]
        x["observations"] = [
            row(pr=i, sha=A, run=10000 + i, job_id=30000 + i, step=f"different_{i}")
            for i in range(1, 8)
        ]
        y = subject.analyze(x)
        self.assertEqual(len(y["proposed_read_only_scouts"]), 4)
        self.assertEqual(y["write_workers_without_owner_lease"], 0)
        self.assertTrue(
            all(not z["dispatch_authorized"] for z in y["proposed_read_only_scouts"])
        )

    def test_repeat_receipt_is_deterministic(self):
        x = sample()
        one = subject.canonical(subject.analyze(x))
        two = subject.canonical(subject.analyze(copy.deepcopy(x)))
        self.assertEqual(one, two)
        self.assertNotIn("authenticated_crew_launches", one)


if __name__ == "__main__":
    unittest.main()


class CLIRoundTrip(unittest.TestCase):
    def test_cli_emit_json_file_and_stdout_no_authority(self):
        import contextlib
        import io
        import tempfile

        with tempfile.TemporaryDirectory() as folder:
            inp = Path(folder) / "case.json"
            out = Path(folder) / "receipt.json"
            inp.write_text(json.dumps(sample()), encoding="utf-8")
            self.assertEqual(subject.main([str(inp), "--output", str(out)]), 0)
            receipt = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(receipt["unique_native_failed_jobs"], 2)
            self.assertFalse(receipt["merge_authorized"])
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                self.assertEqual(subject.main([str(inp)]), 0)
            self.assertEqual(json.loads(captured.getvalue()), receipt)


class BoundariesAndEntry(unittest.TestCase):
    def test_aliased_downstream_summary_retains_zero_causal_root(self):
        entry = row(job="Full Red Proof Summary", step="Emit full-red summary")
        x = sample()
        x["observations"] = [entry, copy.deepcopy(entry)]
        y = subject.analyze(x)
        self.assertEqual(y["unique_native_failed_jobs"], 1)
        self.assertEqual(y["downstream_summary_jobs"], 1)
        self.assertEqual(y["candidate_signature_count"], 0)
        self.assertEqual(y["accepted_root_count"], 0)

    def test_module_main_entrypoint_outputs_observation_without_authority(self):
        import contextlib
        import io
        import runpy
        import tempfile
        from unittest.mock import patch

        script = (
            Path(__file__).resolve().parents[1]
            / "scripts"
            / "gogreen_first_red_wave.py"
        )
        with tempfile.TemporaryDirectory() as folder:
            inp = Path(folder) / "input.json"
            inp.write_text(json.dumps(sample()), encoding="utf-8")
            output = io.StringIO()
            with patch("sys.argv", [str(script), str(inp)]):
                with contextlib.redirect_stdout(output):
                    with self.assertRaises(SystemExit) as done:
                        runpy.run_path(str(script), run_name="__main__")
            self.assertEqual(done.exception.code, 0)
            record = json.loads(output.getvalue())
            self.assertEqual(record["unique_native_failed_jobs"], 2)
            self.assertFalse(record["merge_authorized"])
