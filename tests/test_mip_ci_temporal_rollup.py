"""Positive and adversarial tests for exact-SHA temporal CI comparisons."""

from __future__ import annotations

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tools.mip_ci_temporal_rollup import INPUT_SCHEMA, OUTCOMES, main, rollup

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
HASH = "d" * 64
HASH_ALT = "e" * 64
QUEUE_BASIS = "job.created_at -> job.started_at"


def wave(n, *, sha=None, success=20, failure=0, pending=0,
         queue_samples=25, queue_p95=90, lines=80, branches=30, coverage=True):
    sha = sha or {1: SHA_A, 2: SHA_B, 3: SHA_C}.get(n, SHA_A)
    total = success + failure + pending
    outcomes = {k: 0 for k in OUTCOMES}
    outcomes["success"] = success
    outcomes["failure"] = failure
    return {
        "wave": n, "source_sha": sha,
        "observed_at": f"2026-10-{n + 10:02d}T12:00:00Z",
        "run_attempts": [[n * 1000 + i, 1] for i in range(total)],
        "telemetry": {
            "schema": "abacus.mip.ci-wave-telemetry.v2",
            "repository": "GBOGEB/ABACUS", "source_sha": sha,
            "workflow_records_observed": total,
            "workflow_terminal_by_outcome": outcomes,
            "workflow_nonterminal": pending, "workflow_unclassified": 0,
            "queue_samples": queue_samples, "queue_seconds_p95": queue_p95,
            "queue_basis": QUEUE_BASIS, "jobs_observed": 30,
            "merge_authorized": False,
            "independent_gates": {"admission": "HOLD"},
        },
        "coverage": ({
            "source_sha": sha, "scope_sha256": HASH,
            "config_sha256": HASH, "artifact_sha256": HASH,
            "tool_version": "coverage.py 7.x",
            "eligible_lines": 100, "covered_lines": lines,
            "eligible_branches": 40, "covered_branches": branches,
        } if coverage else None),
    }


def fixture():
    return {
        "schema": INPUT_SCHEMA, "repository": "GBOGEB/ABACUS",
        "cohort": {
            "workflow_set_sha256": HASH,
            "test_selection_sha256": HASH,
            "runner_matrix_sha256": HASH,
        },
        "observations": [wave(1), wave(2, lines=88, branches=34, queue_p95=60)],
        "forecasts": [],
    }


class TemporalPulseTests(unittest.TestCase):
    def test_two_wave_scope_matched_deltas_and_proposals(self):
        result = rollup(fixture())
        change = result["comparisons"][0]
        self.assertEqual(change["line_coverage_candidate_delta_pp"], 8.0)
        self.assertEqual(change["branch_coverage_candidate_delta_pp"], 10.0)
        self.assertEqual(change["queue_p95_delta_seconds"], -30)
        self.assertEqual(change["workflow_success_delta_pp"], 0)
        self.assertIsNone(change["accepted_main_coverage_delta_pp"])
        self.assertEqual([x["target_wave"] for x in result["proposed_n_plus_1_n_plus_2"]], [3, 4])
        self.assertIsNone(result["forecast_mae"])
        self.assertEqual(result["admission"], "HOLD")
        self.assertIsNone(result["rex_authenticated"])

    def test_nonterminal_censored_no_success_or_queue_forecast(self):
        data = fixture()
        data["observations"][1] = wave(2, pending=1)
        result = rollup(data)
        self.assertIsNone(result["comparisons"][0]["workflow_success_delta_pp"])
        self.assertIsNone(result["comparisons"][0]["queue_p95_delta_seconds"])
        self.assertEqual(result["proposed_n_plus_1_n_plus_2"], [])
        self.assertEqual(result["rows"][1]["remaining_pending"], 1)

    def test_queue_small_n_unqualified(self):
        data = fixture()
        data["observations"][0]["telemetry"]["queue_samples"] = 12
        result = rollup(data)
        self.assertIsNone(result["comparisons"][0]["queue_p95_delta_seconds"])
        self.assertEqual(result["comparisons"][0]["queue_comparability"],
                         "nonterminal_or_small_or_mismatched_queue_cohort")

    def test_coverage_scope_changed_same_denominator_is_not_comparable(self):
        data = fixture()
        data["observations"][1]["coverage"]["scope_sha256"] = HASH_ALT
        out = rollup(data)["comparisons"][0]
        self.assertIsNone(out["line_coverage_candidate_delta_pp"])
        self.assertIn("scope_sha256", out["line_reason"])

    def test_coverage_config_and_tool_version_unqualified(self):
        for key, val in (("config_sha256", HASH_ALT), ("tool_version", "coverage 999")):
            with self.subTest(key=key):
                data = fixture()
                data["observations"][1]["coverage"][key] = val
                self.assertIsNone(rollup(data)["comparisons"][0]["branch_coverage_candidate_delta_pp"])

    def test_denominator_shift_unqualified(self):
        data = fixture()
        data["observations"][1]["coverage"]["eligible_lines"] = 105
        self.assertIsNone(rollup(data)["comparisons"][0]["line_coverage_candidate_delta_pp"])

    def test_missing_coverage_never_fabricates_zero(self):
        data = fixture()
        data["observations"][1]["coverage"] = None
        self.assertIsNone(rollup(data)["comparisons"][0]["line_coverage_candidate_delta_pp"])

    def test_reject_stale_source_SHA_and_forged_governance(self):
        for mutate in (
            lambda x: x["observations"][1]["telemetry"].update(source_sha=SHA_A),
            lambda x: x["observations"][1]["telemetry"].update(merge_authorized=True),
            lambda x: x["observations"][1]["telemetry"]["independent_gates"].update(admission="PASS"),
            lambda x: x["observations"][1]["coverage"].update(source_sha=SHA_A),
        ):
            data = fixture()
            mutate(data)
            with self.assertRaises(ValueError):
                rollup(data)

    def test_reject_duplicate_run_attempt_across_waves(self):
        data = fixture()
        data["observations"][1]["run_attempts"][0] = data["observations"][0]["run_attempts"][0]
        with self.assertRaises(ValueError):
            rollup(data)

    def test_reject_wrong_workflow_counts_and_negative_counts(self):
        for mutate in (
            lambda x: x["observations"][1]["telemetry"].update(workflow_records_observed=19),
            lambda x: x["observations"][1]["telemetry"].update(workflow_nonterminal=-1),
            lambda x: x["observations"][1]["telemetry"]["workflow_terminal_by_outcome"].update(success=21),
        ):
            data = fixture()
            mutate(data)
            with self.assertRaises(ValueError):
                rollup(data)

    def test_reject_wave_clock_rollback_or_skipped_wave(self):
        for field, value in (("wave", 5), ("observed_at", "2026-10-11T12:00:00Z")):
            data = fixture()
            data["observations"][1][field] = value
            with self.assertRaises(ValueError):
                rollup(data)

    def test_reject_corrupt_coverage_denominator_and_boolean(self):
        for count in (101, True, -1):
            data = fixture()
            data["observations"][0]["coverage"]["covered_lines"] = count
            with self.assertRaises(ValueError):
                rollup(data)

    def test_persistence_forecast_prior_issued_and_scored(self):
        data = fixture()
        data["observations"][1] = wave(2, success=18, failure=2)
        data["forecasts"] = [{
            "issued_wave": 1, "target_wave": 2,
            "issued_source_sha": SHA_A,
            "issued_at": "2026-10-11T12:01:00Z",
            "method": "persistence-v1", "prediction": 1.0,
        }]
        result = rollup(data)
        self.assertEqual(result["forecasts_scored"], 1)
        self.assertEqual(result["forecast_mae"], 0.1)
        self.assertEqual(result["comparisons"][0]["workflow_success_delta_pp"], -10.0)

    def test_forecast_future_leakage_and_retrofit_rejected(self):
        bad = [{
            "issued_wave": 1, "target_wave": 2,
            "issued_source_sha": SHA_A, "issued_at": "2026-10-12T13:00:00Z",
            "method": "persistence-v1", "prediction": 1.0,
        }, {
            "issued_wave": 1, "target_wave": 2,
            "issued_source_sha": SHA_A, "issued_at": "2026-10-11T12:01:00Z",
            "method": "persistence-v1", "prediction": 0.8,
        }]
        for forecast in bad:
            data = fixture()
            data["forecasts"] = [forecast]
            with self.assertRaises(ValueError):
                rollup(data)

    def test_invalid_utc_calendar_date_fails_closed(self):
        """Exercise the native parser rejection, not merely the Z suffix guard."""
        for bad in ("2026-13-12T12:00:00Z", "not-a-dateZ"):
            with self.subTest(bad=bad):
                data = fixture()
                data["observations"][1]["observed_at"] = bad
                with self.assertRaisesRegex(ValueError, "invalid observed UTC timestamp"):
                    rollup(data)

    def test_persisted_future_forecast_keeps_actual_unknown(self):
        """An issued forecast may await a genuinely unobserved target wave."""
        data = fixture()
        data["forecasts"] = [{
            "issued_wave": 2, "target_wave": 3,
            "issued_source_sha": SHA_B,
            "issued_at": "2026-10-12T12:01:00Z",
            "method": "persistence-v1", "prediction": 1.0,
        }]
        result = rollup(data)
        self.assertEqual(result["forecasts_scored"], 0)
        self.assertIsNone(result["forecast_mae"])
        self.assertIsNone(result["persisted_forecasts"][0]["actual"])
        self.assertFalse(result["merge_authorized"])

    def test_no_pca_or_formal_root_credit_from_multiple_jobs(self):
        data = fixture()
        data["observations"].append(wave(3, success=20))
        result = rollup(data)
        self.assertEqual(result["pca_maturity"], "HOLD_UNQUALIFIED_INDEPENDENT_OBSERVATIONS")
        self.assertIsNone(result["accepted_bd_root_closures"])
        self.assertIsNone(result["native_artifact_bytes_authenticated"])
        self.assertEqual(result["native_run_attempts_structurally_bound"], 60)


    def test_forecast_persistence_whitelists_fields(self):
        data = fixture()
        data["forecasts"] = [{
            "issued_wave": 1, "target_wave": 2,
            "issued_source_sha": SHA_A,
            "issued_at": "2026-10-11T12:01:00Z",
            "method": "persistence-v1", "prediction": 1.0,
            "untrusted_secret_field": "never republish",
        }]
        observed = rollup(data)["persisted_forecasts"][0]
        self.assertNotIn("untrusted_secret_field", observed)
        self.assertEqual(observed["actual"], 1.0)

    def test_no_duplicate_persisted_forecast(self):
        data = fixture()
        forecast = {
            "issued_wave": 1, "target_wave": 2,
            "issued_source_sha": SHA_A,
            "issued_at": "2026-10-11T12:01:00Z",
            "method": "persistence-v1", "prediction": 1.0,
        }
        data["forecasts"] = [forecast, copy.deepcopy(forecast)]
        with self.assertRaises(ValueError):
            rollup(data)

    def test_cli_replay_deterministic_json_and_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "in.json"
            output = Path(directory) / "out.json"
            source.write_text(json.dumps(fixture()))
            with redirect_stdout(io.StringIO()) as stdout:
                main(["--input", str(source), "--out", str(output)])
            original = output.read_bytes()
            self.assertEqual(json.loads(original)["admission"], "HOLD")
            self.assertIn("rollup_sha256=", stdout.getvalue())
            with redirect_stdout(io.StringIO()):
                main(["--input", str(source), "--out", str(output)])
            self.assertEqual(output.read_bytes(), original)

    def test_cli_refuses_symlink_and_same_input_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "in.json"
            source.write_text(json.dumps(fixture()))
            with self.assertRaises(ValueError):
                main(["--input", str(source), "--out", str(source)])
            link = Path(directory) / "linked.json"
            try:
                link.symlink_to(source)
            except OSError:
                self.skipTest("symlink unavailable")
            with self.assertRaises(ValueError):
                main(["--input", str(link), "--out", str(Path(directory) / "out.json")])


if __name__ == "__main__":
    unittest.main()

# These tests are intentionally defined above only when discovered by unittest.
