import hashlib
import importlib.util
import io
import json
import pathlib
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

PATH = pathlib.Path(__file__).resolve().parents[1] / "tools/mip2/mip_wave_pulse.py"
SPEC = importlib.util.spec_from_file_location("mip_wave_pulse", PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)
S = "a" * 40
T = "b" * 40


def record(status="OPEN"):
    return {
        "schema": MOD.SCHEMA,
        "repository": "GBOGEB/ABACUS",
        "base_sha": S,
        "head_sha": T,
        "wave_id": "W1",
        "roots": [
            {
                "root_id": "R1",
                "owner": "MIP",
                "status": status,
                "fingerprints": ["F1", "F1"],
            }
        ],
        "workers": [{"root_id": "R1", "run_id": 12, "job_id": 34}],
        "tests": {"passed": 3, "failed": 0, "skipped": 0},
        "first_reds": [
            {"root_id": "R1", "fingerprint": "F1", "classification": "inherited"}
        ],
        "admission": {"merge_admitted": False},
        "worker_hours": 2,
    }


class WavePulseTests(unittest.TestCase):
    def test_no_unearned_closure(self):
        r, b = MOD.pulse(record())
        self.assertEqual(b["formal_verified_closures"], 0)
        self.assertEqual(b["fingerprint_manifestations"], 2)
        self.assertEqual(r["coverage"]["status"], "UNKNOWN")
        self.assertEqual(r["disposition"], "P0_HOLD")

    def test_duplicate_root_fails(self):
        x = record()
        x["roots"].append(dict(x["roots"][0]))
        with self.assertRaises(ValueError):
            MOD.pulse(x)

    def test_unattributed_first_red_fails(self):
        x = record()
        x["first_reds"][0]["root_id"] = "absent"
        with self.assertRaises(ValueError):
            MOD.pulse(x)

    def test_closure_requires_exact_main_proof(self):
        x = record("ROOT_CLOSED")
        with self.assertRaises(ValueError):
            MOD.pulse(x)
        x["admission"] = {"merge_admitted": True, "verified_main_sha": S}
        x["roots"][0]["closure_proof"] = {
            "main_sha": S,
            "native_run_url": "https://github.com/example/run/1",
            "artifact_sha256": "c" * 64,
        }
        _, backlog = MOD.pulse(x)
        self.assertEqual(backlog["formal_verified_closures"], 0)
        self.assertEqual(backlog["declared_root_closures"], 1)
        self.assertEqual(backlog["closure_disposition"], "UNVERIFIED_DECLARED_CLOSURE")

    def test_coverage_comparability_and_yield(self):
        x = record()
        base = {
            "scope": "combined-main",
            "config_id": "cfg1",
            "source_sha": S,
            "scope_manifest_sha256": "c" * 64,
            "covered_lines": 60,
            "total_lines": 100,
            "covered_branches": 20,
            "total_branches": 50,
        }
        head = dict(base, source_sha=T, covered_lines=65, covered_branches=22)
        x["coverage"] = {"before": base, "after": head}
        result, _ = MOD.pulse(x)
        self.assertEqual(result["coverage"]["delta_lines"], 5)
        self.assertEqual(result["coverage"]["delta_branches"], 2)
        self.assertEqual(result["coverage_yield"]["new_lines_per_hour"], 2.5)
        head["config_id"] = "other"
        self.assertEqual(MOD.pulse(x)[0]["coverage"]["status"], "INCOMPARABLE")

    def test_same_counts_different_eligible_cohort_withheld(self):
        base = {
            "scope": "combined-main",
            "config_id": "cfg1",
            "source_sha": S,
            "scope_manifest_sha256": "c" * 64,
            "covered_lines": 60,
            "total_lines": 100,
            "covered_branches": 20,
            "total_branches": 50,
        }
        candidate = dict(
            base,
            source_sha=T,
            scope_manifest_sha256="d" * 64,
            covered_lines=90,
        )
        result = MOD.coverage_delta(base, candidate)
        self.assertEqual(result["status"], "INCOMPARABLE")

    def test_missing_or_malformed_cohort_digest_fails_closed(self):
        baseline = {
            "scope": "combined-main",
            "config_id": "cfg1",
            "source_sha": S,
            "scope_manifest_sha256": "c" * 64,
            "covered_lines": 60,
            "total_lines": 100,
            "covered_branches": 20,
            "total_branches": 50,
        }
        candidate = dict(baseline, source_sha=T)
        del candidate["scope_manifest_sha256"]
        with self.assertRaisesRegex(ValueError, "incomplete coverage"):
            MOD.coverage_delta(baseline, candidate)
        candidate["scope_manifest_sha256"] = "bad"
        with self.assertRaisesRegex(ValueError, "eligibility scope fingerprint"):
            MOD.coverage_delta(baseline, candidate)

    def test_coverage_source_shas_must_bind_to_wave(self):
        base = {
            "scope": "combined-main",
            "config_id": "cfg1",
            "source_sha": S,
            "scope_manifest_sha256": "c" * 64,
            "covered_lines": 60,
            "total_lines": 100,
            "covered_branches": 20,
            "total_branches": 50,
        }
        candidate = dict(base, source_sha=T, covered_lines=62)
        wave = record()
        wave["coverage"] = {"before": base, "after": candidate}
        report, _ = MOD.pulse(wave)
        self.assertEqual(report["coverage"]["before_covered"], 80)
        self.assertEqual(report["coverage"]["after_covered"], 82)
        self.assertEqual(report["coverage"]["eligible"], 150)
        candidate["source_sha"] = S
        with self.assertRaisesRegex(ValueError, "candidate SHA"):
            MOD.pulse(wave)
        candidate["source_sha"] = T
        base["source_sha"] = T
        with self.assertRaisesRegex(ValueError, "baseline SHA"):
            MOD.pulse(wave)

    def test_canonical_coverage_record(self):
        report = {
            "meta": {"branch_coverage": True},
            "files": {
                "src/a.py": {
                    "executed_lines": [1],
                    "missing_lines": [2],
                    "executed_branches": [[1, 2]],
                    "missing_branches": [[1, 3]],
                    "summary": {
                        "covered_lines": 1,
                        "num_statements": 2,
                        "covered_branches": 1,
                        "num_branches": 2,
                    },
                }
            },
        }
        before = MOD.canonical_coverage_record(report, S, "cohort", "cfg")
        self.assertEqual(before["covered_lines"], 1)
        self.assertEqual(before["total_branches"], 2)
        after = MOD.canonical_coverage_record(report, T, "cohort", "cfg")
        self.assertEqual(
            before["scope_manifest_sha256"],
            after["scope_manifest_sha256"],
        )
        self.assertEqual(MOD.coverage_delta(before, after)["status"], "COMPARABLE")
        report["files"]["src/a.py"]["missing_lines"] = [3]
        changed = MOD.canonical_coverage_record(report, T, "cohort", "cfg")
        self.assertEqual(MOD.coverage_delta(before, changed)["status"], "INCOMPARABLE")
        report["files"]["src/a.py"]["missing_lines"] = [2]
        report["files"]["src/a.py"]["summary"]["num_statements"] = 3
        with self.assertRaisesRegex(ValueError, "summary and eligible IDs"):
            MOD.canonical_coverage_record(report, T, "cohort", "cfg")

    def test_canonical_coverage_rejects_duplicate_arc_and_missing_source(self):
        report = {
            "meta": {"branch_coverage": True},
            "files": {
                "src/a.py": {
                    "executed_lines": [1],
                    "missing_lines": [],
                    "executed_branches": [[1, 2]],
                    "missing_branches": [[1, 2]],
                    "summary": {
                        "covered_lines": 1,
                        "num_statements": 1,
                        "covered_branches": 1,
                        "num_branches": 2,
                    },
                }
            },
        }
        with self.assertRaisesRegex(ValueError, "duplicate branch"):
            MOD.canonical_coverage_record(report, S, "cohort", "cfg")
        report["files"]["src/a.py"]["missing_branches"] = [[1, 3]]
        with self.assertRaisesRegex(ValueError, "selected path missing"):
            MOD.canonical_coverage_record(
                report, S, "cohort", "cfg", selected_paths=["not-there.py"]
            )
        report["meta"]["branch_coverage"] = False
        with self.assertRaisesRegex(ValueError, "branch coverage required"):
            MOD.canonical_coverage_record(report, S, "cohort", "cfg")

    def test_missing_tests_fail(self):
        x = record()
        x["tests"].pop("passed")
        with self.assertRaises(ValueError):
            MOD.pulse(x)

    def test_forged_admission_cannot_promote_wave(self):
        payload = record("ROOT_CLOSED")
        payload["admission"] = {
            "merge_admitted": True,
            "verified_main_sha": S,
        }
        payload["roots"][0]["closure_proof"] = {
            "main_sha": S,
            "native_run_url": "https://github.com/example/not-authenticated",
            "artifact_sha256": "c" * 64,
        }
        result, backlog = MOD.pulse(payload)
        self.assertEqual(backlog["formal_verified_closures"], 0)
        self.assertEqual(result["disposition"], "P0_HOLD")
        self.assertFalse(result["merge_admitted"])
        self.assertTrue(result["declared_merge_admitted"])
        self.assertEqual(result["tests_receipt_trust"], "INPUT_DECLARED_NOT_JUNIT")

    def test_negative_bool_worker_ids_rejected(self):
        for field in ("run_id", "job_id"):
            with self.subTest(field=field):
                data = record()
                data["workers"][0][field] = True
                with self.assertRaisesRegex(ValueError, "positive native"):
                    MOD.pulse(data)

    def test_duplicate_worker_receipt_rejected(self):
        data = record()
        data["workers"].append(dict(data["workers"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate worker"):
            MOD.pulse(data)

    def test_cross_head_worker_receipt_rejected(self):
        data = record()
        data["workers"][0]["source_sha"] = S
        with self.assertRaisesRegex(ValueError, "SHA not bound"):
            MOD.pulse(data)

    def test_forged_first_red_fingerprint_rejected(self):
        data = record()
        data["first_reds"][0]["fingerprint"] = "NOT_IN_ROOT"
        with self.assertRaisesRegex(ValueError, "unattributed first-red"):
            MOD.pulse(data)

    def test_coverage_denominator_growth_not_gain(self):
        data = record()
        start = {
            "scope": "matched",
            "config_id": "same",
            "source_sha": S,
            "scope_manifest_sha256": "c" * 64,
            "covered_lines": 4,
            "total_lines": 10,
            "covered_branches": 2,
            "total_branches": 4,
        }
        end = dict(
            start,
            source_sha=T,
            covered_lines=14,
            total_lines=20,
            covered_branches=5,
            total_branches=7,
        )
        data["coverage"] = {"before": start, "after": end}
        report, backlog = MOD.pulse(data)
        self.assertEqual(report["coverage"]["status"], "INCOMPARABLE")
        self.assertEqual(report["coverage_yield"]["status"], "UNKNOWN")
        self.assertEqual(backlog["formal_verified_closures"], 0)

    def test_large_root_stress_deterministic(self):
        data = record()
        data["roots"] = [
            {
                "root_id": f"R{i:04d}",
                "owner": "STRESS",
                "status": "OPEN",
                "fingerprints": [f"F{i:04d}"],
            }
            for i in range(800)
        ]
        data["workers"] = []
        data["first_reds"] = []
        before = MOD.pulse(data)
        after = MOD.pulse(data)
        self.assertEqual(before, after)
        self.assertEqual(before[1]["distinct_root_counts"]["open"], 800)
        self.assertEqual(before[1]["formal_verified_closures"], 0)

    def test_cli_emits_source_bound_repeatable_receipts(self):
        payload = record()
        with tempfile.TemporaryDirectory() as work:
            source = pathlib.Path(work) / "wave-input.json"
            target = pathlib.Path(work) / "wave-output"
            source.write_text(json.dumps(payload), encoding="utf-8")
            argv = [
                "mip_wave_pulse",
                "--input",
                str(source),
                "--output-dir",
                str(target),
            ]
            stdout = io.StringIO()
            with mock.patch.object(sys, "argv", argv), redirect_stdout(stdout):
                MOD.main()
            report_path = target / "mip_wave_pulse.json"
            backlog_path = target / "mip_backlog_delta.json"
            report_bytes = report_path.read_bytes()
            backlog_bytes = backlog_path.read_bytes()
            report = json.loads(report_bytes)
            backlog = json.loads(backlog_bytes)
            self.assertEqual(
                report["input_sha256"],
                hashlib.sha256(source.read_bytes()).hexdigest(),
            )
            self.assertEqual(report["disposition"], "P0_HOLD")
            self.assertEqual(report["coverage"]["status"], "UNKNOWN")
            self.assertEqual(backlog["formal_verified_closures"], 0)
            self.assertEqual(json.loads(stdout.getvalue())["result"], "P0_HOLD")
            with mock.patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()):
                MOD.main()
            self.assertEqual(report_path.read_bytes(), report_bytes)
            self.assertEqual(backlog_path.read_bytes(), backlog_bytes)

    def test_cli_rejects_malformed_input_without_receipt(self):
        with tempfile.TemporaryDirectory() as work:
            source = pathlib.Path(work) / "invalid.json"
            target = pathlib.Path(work) / "wave-output"
            source.write_text(json.dumps({"schema": MOD.SCHEMA}), encoding="utf-8")
            argv = [
                "mip_wave_pulse",
                "--input",
                str(source),
                "--output-dir",
                str(target),
            ]
            with mock.patch.object(sys, "argv", argv):
                with self.assertRaisesRegex(ValueError, "missing repository"):
                    MOD.main()
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
