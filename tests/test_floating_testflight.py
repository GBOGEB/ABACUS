"""Adversarial local controls: forecasting never earns native admission."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.triage import floating_testflight as flight

SHA = "a" * 40
SEL = "tests/test_floating_testflight.py"
T1 = "2026-10-19T09:00:00Z"
T2 = "2026-10-19T09:05:00Z"


def frozen(pulse=1):
    return flight.forecast(SHA, pulse, SEL, now=T1)


def observed(pulse=1, *, covered=10, branches=2, state="GREEN", run=100):
    value = {
        "schema": flight.OBS_SCHEMA,
        "repository": "GBOGEB/ABACUS", "head_sha": SHA,
        "observed_at": f"2026-10-19T09:{pulse:02d}:00Z",
        "pulse": pulse, "selection_sha256": flight.selection_hash(SEL),
        "tests": {"executed": 3, "passed": 3, "failed": 0,
                  "errors": 0, "skipped": 0},
        "terminal": True, "test_state": state,
        "gate_outcomes": {
            "syntax": "PASS", "hook": "PASS", "pytest": "PASS",
            "source_scope": "PASS",
        },
        "native_conclusion": "success",
        "coverage": {
            "scope_sha256": "b" * 64, "config_sha256": "c" * 64,
            "statements": {"covered": covered, "eligible": 10},
            "branches": {"covered": branches, "eligible": 2},
        },
        "run_id": run, "run_attempt": 1,
        "merge_admission": "HOLD",
    }
    return value


class LocalTestflightTests(unittest.TestCase):
    def test_forecast_is_sealed_before_observation(self):
        row = frozen()
        flight.validate_forecast(row)
        self.assertIsNone(row["prediction"]["branch_fraction"])
        self.assertEqual(row["target_pulses"], [1, 2])
        self.assertEqual(row["merge_admission"], "HOLD")
        row["prediction"]["branch_fraction"] = 1.0
        with self.assertRaisesRegex(ValueError, "seal mismatch"):
            flight.validate_forecast(row)

    def test_forecast_rejects_future_leakage(self):
        with self.assertRaisesRegex(ValueError, "before its baseline"):
            flight.forecast(SHA, 2, SEL, observed(), now=T1)

    def test_forecast_uses_only_prior_matched_selection(self):
        earlier = observed()
        earlier["observed_at"] = "2026-10-18T09:00:00Z"
        x = flight.forecast(SHA, 2, SEL, earlier, now=T1)
        self.assertEqual(x["prediction"]["test_pass_fraction"], 1.0)
        self.assertEqual(x["prediction"]["branch_fraction"], 1.0)
        with self.assertRaisesRegex(ValueError, "selection"):
            flight.forecast(SHA, 2, SEL + " extra", earlier, now=T1)

    def test_immutable_file_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "frozen.json"
            flight.write_new(path, frozen())
            with self.assertRaises(FileExistsError):
                flight.write_new(path, frozen())

    def test_junit_is_counted_not_assumed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "junit.xml"
            path.write_text(
                '<testsuite><testcase classname="a" name="good"/>'
                '<testcase classname="b" name="bad"><failure/></testcase>'
                '<testcase classname="c" name="later"><skipped/></testcase>'
                '</testsuite>', encoding="utf-8")
            out = flight.read_junit(path)
            self.assertEqual(out["counts"],
                             {"executed": 3, "passed": 1, "failed": 1,
                              "errors": 0, "skipped": 1})
            self.assertEqual(out["failure_occurrences"], 1)
            self.assertIsNone(out["distinct_root_ids"])

    def test_missing_junit_is_unknown(self):
        self.assertIsNone(flight.read_junit(Path("/nonexistent-native.xml")))
        r = flight.observe(frozen(), None, None, head=SHA, selection=SEL, now=T2)
        self.assertFalse(r["terminal"])
        self.assertEqual(r["test_state"], "UNKNOWN")
        self.assertIsNone(r["coverage"])
        self.assertIsNone(r["job_id"])

    def test_observe_counts_and_signed_forecast_error(self):
        old = observed()
        old["observed_at"] = "2026-10-18T09:00:00Z"
        f = flight.forecast(SHA, 2, SEL, old, now=T1)
        junit = {"counts": {"executed": 2, "passed": 1, "failed": 1,
                            "errors": 0, "skipped": 0},
                 "failure_fingerprints": ["x::test"], "failure_occurrences": 1}
        cov = {"statements": {"covered": 8, "eligible": 10},
               "branches": {"covered": 1, "eligible": 2},
               "scope_sha256": "b" * 64, "config_sha256": "c" * 64}
        r = flight.observe(f, junit, cov, head=SHA, selection=SEL, now=T2,
                           run_id=42, run_attempt=1,
                           gate_outcomes={
                               "syntax": "PASS", "hook": "PASS",
                               "pytest": "FAIL", "source_scope": "PASS",
                           },
                           native_conclusion="pending")
        self.assertEqual(r["test_state"], "RED")
        self.assertEqual(r["gate_outcomes"]["pytest"], "FAIL")
        self.assertEqual(r["native_conclusion"], "pending")
        self.assertEqual(r["forecast_errors_signed"]["test_pass_fraction"], -0.5)
        self.assertEqual(r["forecast_errors_signed"]["branch_fraction"], -0.5)
        self.assertEqual(r["first_red_occurrences"], 1)
        self.assertIsNone(r["verified_root_ids"])

    def test_observe_rejects_wrong_head_and_selection(self):
        with self.assertRaisesRegex(ValueError, "source SHA"):
            flight.observe(frozen(), None, None, head="b" * 40,
                           selection=SEL, now=T2)
        with self.assertRaisesRegex(ValueError, "selection"):
            flight.observe(frozen(), None, None, head=SHA,
                           selection=SEL + " changed", now=T2)

    def test_measured_coverage_scope_and_zero_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.py").write_text("x = 3\n", encoding="utf-8")
            (root / "b.py").write_text("y = 2\n", encoding="utf-8")
            path = root / "cov.json"
            payload = {
                "meta": {"branch_coverage": True, "version": "7.16.2"},
                "totals": {"num_statements": 3, "covered_lines": 1,
                           "num_branches": 2, "covered_branches": 1},
                "files": {
                    "a.py": {"summary": {"num_statements": 2, "covered_lines": 1,
                                         "num_branches": 2}},
                    "b.py": {"summary": {"num_statements": 1, "covered_lines": 0,
                                         "num_branches": 0}},
                },
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            out = flight.measured_coverage(path, root)
            self.assertEqual(out["zero_covered_paths"], ["b.py"])
            self.assertEqual(out["branches"], {"covered": 1, "eligible": 2})
            old_scope = out["scope_sha256"]
            (root / "a.py").write_text("x = 4\n", encoding="utf-8")
            self.assertNotEqual(flight.measured_coverage(path, root)["scope_sha256"],
                                old_scope)

    def test_coverage_rejects_escape_and_boolean(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "cov.json"
            path.write_text(json.dumps({
                "totals": {"covered_lines": True, "num_statements": 1},
                "files": {},
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "coverage"):
                flight.measured_coverage(path, root)
            path.write_text(json.dumps({
                "totals": {}, "files": {
                    "../escape.py": {"summary": {"num_statements": 1,
                                                 "covered_lines": 0}}
                },
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "escapes root"):
                flight.measured_coverage(path, root)

    def test_matched_separate_statement_and_branch_deltas(self):
        a, b = observed(1, covered=5, branches=1), observed(2, covered=7, branches=2)
        result = flight.compare(a, b)
        self.assertTrue(result["population_comparable"])
        self.assertEqual(result["metrics"]["statements"]["covered_delta"], 2)
        self.assertEqual(result["metrics"]["branches"]["delta_pp"], 50)

    def test_scope_change_forbids_false_coverage_gain(self):
        a, b = observed(1), observed(2)
        b["coverage"]["scope_sha256"] = "e" * 64
        result = flight.compare(a, b)
        self.assertFalse(result["population_comparable"])
        self.assertIsNone(result["metrics"]["statements"]["delta_pp"])

    def test_control_requires_four_distinct_native_terminal_pulses(self):
        history = [observed(i, run=100 + i) for i in (1, 2, 3, 4)]
        self.assertEqual(flight.control(history)["state"], "QUIET_WATCH_CANDIDATE")
        self.assertFalse(flight.control(history)["phase_two_authorized"])
        self.assertEqual(flight.control(history[:-1])["state"],
                         "CONTINUE_MEASUREMENT")
        history[-1]["run_id"] = history[-2]["run_id"]
        with self.assertRaisesRegex(ValueError, "reused"):
            flight.control(history)

    def test_control_restarts_for_coverage_regression_anywhere_in_window(self):
        history = [
            observed(1, covered=10),
            observed(2, covered=9, run=102),
            observed(3, covered=10, run=103),
            observed(4, covered=10, run=104),
        ]
        self.assertEqual(flight.control(history)["state"],
                         "RESTART_COVERAGE_REGRESSION")

    def test_control_requires_every_gate_and_native_attempt_to_pass(self):
        history = [observed(i, run=100 + i) for i in (1, 2, 3, 4)]
        history[1]["gate_outcomes"]["hook"] = "FAIL"
        self.assertEqual(flight.control(history)["state"], "RESTART_FAILED_GATE")
        history[1]["gate_outcomes"]["hook"] = "PASS"
        history[1]["native_conclusion"] = "cancelled"
        self.assertEqual(flight.control(history)["state"],
                         "RESTART_FAILED_NATIVE_ATTEMPT")
        history[1]["native_conclusion"] = "unverified"
        self.assertEqual(flight.control(history)["state"],
                         "HOLD_UNVERIFIED_NATIVE_CONCLUSION")

    def test_control_holds_for_missing_or_skipped_gate_evidence(self):
        history = [observed(i, run=100 + i) for i in (1, 2, 3, 4)]
        history[0]["gate_outcomes"].pop("source_scope")
        self.assertEqual(flight.control(history)["state"],
                         "HOLD_UNVERIFIED_GATE_OUTCOMES")
        history[0]["gate_outcomes"]["source_scope"] = "PASS"
        history[0]["test_state"] = "GREEN_WITH_SKIPS"
        self.assertEqual(flight.control(history)["state"],
                         "RESTART_UNHEALTHY_TESTS")

    def test_control_does_not_trust_green_label_over_failed_counts(self):
        history = [observed(i, run=100 + i) for i in (1, 2, 3, 4)]
        history[0]["tests"]["passed"] = 2
        history[0]["tests"]["failed"] = 1
        self.assertEqual(flight.control(history)["state"], "RESTART_FIRST_RED")

    def test_stop_not_allowed_below_target(self):
        history = [observed(i, covered=9, run=100 + i) for i in (1, 2, 3, 4)]
        self.assertEqual(flight.control(history)["state"],
                         "RERANK_UNCOVERED_OPPORTUNITIES")

    def test_regression_and_first_red_restart(self):
        history = [observed(1), observed(2, covered=8, run=102)]
        self.assertEqual(flight.control(history)["state"],
                         "RESTART_COVERAGE_REGRESSION")
        history[1]["test_state"] = "RED"
        self.assertEqual(flight.control(history)["state"], "RESTART_FIRST_RED")

    def test_review_does_not_invent_native_artifact(self):
        row = flight.markdown_review(frozen(), None, None)
        self.assertIn("No merger", row)
        self.assertIn("HOLD", row)
        self.assertNotIn("ZIP bytes verified", row)


    def test_rollup_canonical_import_is_measured_and_fail_closed(self):
        from tools.triage import mip_pulse_rollup as pulse

        self.assertEqual(pulse.SCHEMA, "codepurple.mip.floating-pulse.v1")
        with self.assertRaisesRegex(ValueError, "no pulses"):
            pulse.rollup([])
        with self.assertRaisesRegex(ValueError, "pulse schema"):
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "bad.json"
                path.write_text('{"schema":"wrong"}', encoding="utf-8")
                pulse.read_pulse(path)

    def test_cli_forecast_observe_review_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "unit.py").write_text("x = 1\\n", encoding="utf-8")
            (root / "junit.xml").write_text(
                '<testsuite><testcase classname="t" name="positive"/></testsuite>',
                encoding="utf-8")
            (root / "coverage.json").write_text(json.dumps({
                "meta": {"branch_coverage": True, "version": "7.16.2"},
                "totals": {"num_statements": 1, "covered_lines": 1,
                           "num_branches": 0, "covered_branches": 0},
                "files": {"unit.py": {"summary": {
                    "num_statements": 1, "covered_lines": 1,
                    "num_branches": 0}}},
            }), encoding="utf-8")
            fore = root / "frozen.json"
            result = root / "observed.json"
            review = root / "review.md"
            with mock.patch.object(flight, "check_head", return_value=SHA):
                self.assertEqual(flight.main([
                    "forecast", "--head", SHA, "--pulse", "12",
                    "--selection", SEL, "--out", str(fore)]), 0)
                self.assertEqual(flight.main([
                    "observe", "--forecast", str(fore), "--root", str(root),
                    "--junit", str(root / "junit.xml"), "--selection", SEL,
                    "--coverage", str(root / "coverage.json"),
                    "--out", str(result)]), 0)
            self.assertEqual(flight.main([
                "review", "--forecast", str(fore),
                "--observation", str(result), "--out", str(review)]), 0)
            actual = json.loads(result.read_text())
            self.assertEqual(actual["tests"]["passed"], 1)
            self.assertEqual(actual["coverage"]["statements"]["covered"], 1)
            self.assertIn("HOLD", review.read_text())
            with self.assertRaises(FileExistsError):
                flight.write_new(fore, frozen())

    def test_missing_covered_file_does_not_forge_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "coverage.json"
            path.write_text(json.dumps({
                "totals": {"num_statements": 4, "covered_lines": 2},
                "files": {"missing.py": {"summary": {
                    "num_statements": 4, "covered_lines": 2}}},
            }), encoding="utf-8")
            result = flight.measured_coverage(path, root)
            self.assertEqual(result["status"], "UNRESOLVED_SOURCE_PATH")
            self.assertIsNone(result["scope_sha256"])
            self.assertIsNone(result["zero_covered_paths"])

    def test_unqualified_prior_scope_scores_unknown_not_success(self):
        old = observed(1)
        old["observed_at"] = "2026-10-18T09:00:00Z"
        p = flight.forecast(SHA, 2, SEL, old, now=T1)
        j = {"counts": {"executed": 3, "passed": 3, "failed": 0,
                        "errors": 0, "skipped": 0}, "failure_fingerprints": [],
             "failure_occurrences": 0}
        changed = {"statements": {"eligible": 10, "covered": 10},
                   "branches": {"eligible": 2, "covered": 2},
                   "scope_sha256": "e" * 64, "config_sha256": "c" * 64}
        actual = flight.observe(p, j, changed, head=SHA, selection=SEL, now=T2)
        self.assertEqual(actual["forecast_comparability"],
                         "WITHHELD_SCOPE_OR_PRIOR_MISMATCH")
        self.assertTrue(all(v is None for v in
                            actual["forecast_errors_signed"].values()))

    def test_local_run_cannot_enter_quiet_control(self):
        rows = [observed(i, run=100 + i) for i in (1, 2, 3, 4)]
        rows[0]["run_id"] = None
        decision = flight.control(rows)
        self.assertEqual(decision["state"], "CONTINUE_MEASUREMENT")
        self.assertFalse(decision["native_identities_structurally_present"])



if __name__ == "__main__":
    unittest.main()
