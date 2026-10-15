"""Structural, negative and dimensional controls for queue-pressure pulses."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "feedback_queue_trends.py"
SPEC = importlib.util.spec_from_file_location("feedback_queue_trends", PATH)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)
SHA = "a" * 40


def row(n, created="2026-10-15T08:15:00Z"):
    return {"id": n, "name": "PR Feedback Gate Evaluator", "event": "workflow_run",
            "head_sha": SHA, "created_at": created}


def receipt(at, total=6, main=2, runs=None, complete=True):
    runs = [row(1), row(2)] if runs is None else runs
    sample = len(runs)
    return {"schema": mod.INPUT_SCHEMA, "source_repository": "GBOGEB/ABACUS",
            "main_sha": SHA, "observed_at": at,
            "repo_queued_total": total, "main_queued_total": main,
            "main_sample_complete": complete, "main_sample_size": main if complete else sample,
            "main_feedback_workflow_run_sample": sample,
            "main_feedback_queued_total": sample if complete else None,
            "feedback_runs": runs, "admission": "HOLD",
            "authority_transfer": False, "remote_mutation_authorized": False}


def pair():
    return receipt("2026-10-15T08:17:00Z"), receipt("2026-10-15T08:18:00Z", total=8,
                                                       main=3, runs=[row(2), row(3), row(4)])


class TrendTests(unittest.TestCase):
    def test_queue_delta_and_rate(self):
        a, b = pair()
        x = mod.compare(a, b)
        self.assertEqual(x["queue_net_delta"], 2)
        self.assertEqual(x["queue_net_delta_per_minute"], 2)
        self.assertEqual(x["main_queue_delta"], 1)
        self.assertEqual(x["main_feedback"]["net_delta"], 1)
        self.assertEqual(x["main_feedback"]["observed_entered"], 2)
        self.assertEqual(x["main_feedback"]["observed_exited"], 1)
        self.assertEqual(x["root_closure"][:7], "UNKNOWN")

    def test_queue_age_percentiles(self):
        a, b = pair()
        x = mod.compare(a, b)["age_feedback_at_latest_pulse"]
        self.assertEqual(x["state"], "MEASURED")
        self.assertEqual(x["p50_seconds"], 180)
        self.assertEqual(x["p95_seconds"], 180)

    def test_partial_census_is_not_extrapolated(self):
        a, b = pair()
        b["main_sample_complete"] = False
        b["main_sample_size"] = 2
        b["feedback_runs"] = [row(2), row(3)]
        b["main_feedback_workflow_run_sample"] = 2
        b["main_feedback_queued_total"] = None
        x = mod.compare(a, b)
        self.assertEqual(x["main_feedback"]["state"], "UNKNOWN")
        self.assertIsNone(x["main_feedback"]["net_delta"])
        self.assertEqual(x["age_feedback_at_latest_pulse"]["state"], "UNKNOWN")

    def test_count_is_not_equivalent_to_job_throughput(self):
        a, b = pair()
        x = mod.compare(a, b)
        self.assertIn("UNKNOWN", x["throughput"])
        self.assertIn("not_completion", x["main_feedback"]["churn_semantics"])

    def test_reject_moved_sha(self):
        a, b = pair()
        b["main_sha"] = "b" * 40
        b["feedback_runs"] = [{**z, "head_sha": "b" * 40} for z in b["feedback_runs"]]
        with self.assertRaisesRegex(ValueError, "different main SHAs"):
            mod.compare(a, b)

    def test_reject_non_chronological(self):
        a, b = pair()
        b["observed_at"] = a["observed_at"]
        with self.assertRaisesRegex(ValueError, "strictly greater"):
            mod.compare(a, b)

    def test_reject_non_utc(self):
        a, b = pair()
        b["observed_at"] = "2026-10-15T10:18:00+02:00"
        with self.assertRaisesRegex(ValueError, "UTC"):
            mod.compare(a, b)

    def test_reject_invalid_utf8_date(self):
        a, b = pair()
        b["observed_at"] = "not-a-dateZ"
        with self.assertRaises(ValueError):
            mod.compare(a, b)

    def test_reject_other_repo(self):
        a, b = pair()
        b["source_repository"] = "GBOGEB/CODEX"
        with self.assertRaisesRegex(ValueError, "different source"):
            mod.compare(a, b)

    def test_reject_invalid_counts(self):
        a, b = pair()
        b["repo_queued_total"] = True
        with self.assertRaises(ValueError):
            mod.compare(a, b)

    def test_reject_main_greater_than_repo(self):
        a, b = pair()
        b["repo_queued_total"] = 1
        with self.assertRaises(ValueError):
            mod.compare(a, b)

    def test_reject_duplicate_ids(self):
        a, b = pair()
        b["feedback_runs"][0]["id"] = 3
        with self.assertRaises(ValueError):
            mod.compare(a, b)

    def test_reject_wrong_workflow_name(self):
        a, b = pair()
        b["feedback_runs"][0]["name"] = "another gate"
        with self.assertRaises(ValueError):
            mod.compare(a, b)

    def test_reject_fake_check_pass(self):
        a, b = pair()
        b["admission"] = "PASS"
        with self.assertRaises(ValueError):
            mod.compare(a, b)

    def test_reject_sample_consistency(self):
        a, b = pair()
        b["main_sample_size"] = 2
        with self.assertRaises(ValueError):
            mod.compare(a, b)

    def test_future_age_not_measured(self):
        a, b = pair()
        b["feedback_runs"][1]["created_at"] = "2026-10-15T08:19:00Z"
        x = mod.compare(a, b)
        self.assertEqual(x["age_feedback_at_latest_pulse"]["state"], "UNKNOWN")

    def test_missing_age_not_measured(self):
        a, b = pair()
        b["feedback_runs"][0].pop("created_at")
        x = mod.compare(a, b)
        self.assertEqual(x["age_feedback_at_latest_pulse"]["state"], "UNKNOWN")

    def test_zero_feedback_queue(self):
        a = receipt("2026-10-15T08:17:00Z", total=3, main=0, runs=[])
        b = receipt("2026-10-15T08:18:00Z", total=4, main=0, runs=[])
        x = mod.compare(a, b)
        self.assertEqual(x["main_feedback"]["net_delta"], 0)
        self.assertEqual(x["age_feedback_at_latest_pulse"]["state"], "NO_OBSERVATIONS")

    def test_output_sha256(self):
        a, b = pair()
        with tempfile.TemporaryDirectory() as d:
            mod.emit(a, b, Path(d))
            m = json.loads((Path(d) / "manifest.json").read_text())
            self.assertEqual(m["sha256"]["trends.json"],
                             hashlib.sha256((Path(d) / "trends.json").read_bytes()).hexdigest())

    def test_deterministic_emit(self):
        a, b = pair()
        rev = copy.deepcopy(b)
        rev["feedback_runs"].reverse()
        with tempfile.TemporaryDirectory() as left, tempfile.TemporaryDirectory() as right:
            mod.emit(a, b, Path(left))
            mod.emit(a, rev, Path(right))
            self.assertEqual((Path(left) / "trends.json").read_bytes(),
                             (Path(right) / "trends.json").read_bytes())


    def test_reject_bad_schema(self):
        a, b = pair()
        b["schema"] = "untrusted.fixture"
        with self.assertRaises(ValueError):
            mod.compare(a, b)

    def test_reject_missing_repo(self):
        a, b = pair()
        b.pop("source_repository")
        with self.assertRaises(ValueError):
            mod.compare(a, b)

    def test_reject_invalid_sha(self):
        a, b = pair()
        b["main_sha"] = "abc"
        with self.assertRaises(ValueError):
            mod.compare(a, b)

    def test_reject_missing_completeness(self):
        a, b = pair()
        b.pop("main_sample_complete")
        with self.assertRaises(ValueError):
            mod.compare(a, b)

    def test_reject_sampling_over_count(self):
        a, b = pair()
        b["main_queued_total"] = 1
        with self.assertRaises(ValueError):
            mod.compare(a, b)

    def test_reject_more_feedback_than_sample(self):
        a, b = pair()
        b["main_feedback_workflow_run_sample"] = 4
        with self.assertRaises(ValueError):
            mod.compare(a, b)

    def test_reject_forged_feedback_total(self):
        a, b = pair()
        b["main_feedback_queued_total"] = 99
        with self.assertRaises(ValueError):
            mod.compare(a, b)

    def test_reject_partial_total_credit(self):
        a, b = pair()
        b["main_sample_complete"] = False
        b["main_sample_size"] = 2
        b["feedback_runs"] = b["feedback_runs"][:2]
        b["main_feedback_workflow_run_sample"] = 2
        # Attempt to retain false full-population claim on a partial sample.
        with self.assertRaises(ValueError):
            mod.compare(a, b)

    def test_reject_incomplete_feedback_list(self):
        a, b = pair()
        b["feedback_runs"] = b["feedback_runs"][:1]
        with self.assertRaises(ValueError):
            mod.compare(a, b)

    def test_reject_invalid_feedback_row(self):
        a, b = pair()
        b["feedback_runs"][0] = None
        with self.assertRaises(ValueError):
            mod.compare(a, b)

    def test_reject_boolean_run_id(self):
        a, b = pair()
        b["feedback_runs"][0]["id"] = True
        with self.assertRaises(ValueError):
            mod.compare(a, b)

    def test_reject_wrong_event_type(self):
        a, b = pair()
        b["feedback_runs"][0]["event"] = "push"
        with self.assertRaises(ValueError):
            mod.compare(a, b)

    def test_reject_authority_transfer(self):
        a, b = pair()
        b["authority_transfer"] = True
        with self.assertRaises(ValueError):
            mod.compare(a, b)

    def test_reject_remote_mutation_authority(self):
        a, b = pair()
        b["remote_mutation_authorized"] = True
        with self.assertRaises(ValueError):
            mod.compare(a, b)

    def test_age_quantile_rank(self):
        a, b = pair()
        # Increasing oldest-to-newest ages: 180, 120, and 60 seconds.
        b["feedback_runs"][0]["created_at"] = "2026-10-15T08:15:00Z"
        b["feedback_runs"][1]["created_at"] = "2026-10-15T08:16:00Z"
        b["feedback_runs"][2]["created_at"] = "2026-10-15T08:17:00Z"
        x = mod.compare(a, b)["age_feedback_at_latest_pulse"]
        self.assertEqual(x["p50_seconds"], 120)
        self.assertEqual(x["p95_seconds"], 180)

    def test_cli_roundtrip(self):
        a, b = pair()
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            old = root / "old.json"
            new = root / "new.json"
            old.write_text(json.dumps(a))
            new.write_text(json.dumps(b))
            output = root / "output"
            done = subprocess.run([sys.executable, str(PATH), "--previous", str(old),
                                   "--current", str(new), "--out", str(output)],
                                  check=True, capture_output=True, text=True)
            self.assertEqual(json.loads(done.stdout)["main_feedback"]["state"], "MEASURED")
            self.assertTrue((output / "manifest.json").exists())


    def test_cli_main_entrypoint_under_coverage(self):
        a, b = pair()
        import contextlib
        import io
        import runpy
        import sys
        from unittest import mock
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            old, new, out = root / "before.json", root / "after.json", root / "out"
            old.write_text(json.dumps(a))
            new.write_text(json.dumps(b))
            argv = [str(PATH), "--previous", str(old), "--current", str(new), "--out", str(out)]
            buff = io.StringIO()
            with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(buff):
                runpy.run_path(str(PATH), run_name="__main__")
            self.assertEqual(json.loads(buff.getvalue())["queue_net_delta"], 2)
            self.assertTrue((out / "manifest.json").is_file())


if __name__ == "__main__":
    unittest.main()
