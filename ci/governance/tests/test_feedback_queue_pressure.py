"""Negative controls for feedback fan-in queue telemetry."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "feedback_queue_pressure.py"
SPEC = importlib.util.spec_from_file_location("feedback_queue_pressure", SCRIPT)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)
SHA = "a" * 40


def item(number, name, event="workflow_run", head=SHA):
    return {
        "id": number,
        "name": name,
        "event": event,
        "status": "queued",
        "head_sha": head,
        "head_branch": "main",
        "created_at": "2026-10-15T08:17:01Z",
    }


def payload():
    return {
        "schema": mod.SCHEMA,
        "repository": mod.REPO,
        "main_sha": SHA,
        "observed_at": "2026-10-15T08:18:00Z",
        "repository_queued": {
            "total_count": 3,
            "workflow_runs": [
                item(100, mod.FEEDBACK),
                item(101, mod.FEEDBACK),
                item(102, "CI/CD Test Suite", "pull_request"),
            ],
        },
        "main_queued": {
            "total_count": 2,
            "workflow_runs": [item(100, mod.FEEDBACK), item(101, mod.FEEDBACK)],
        },
    }


class QueuePressureTests(unittest.TestCase):
    def test_full_sample_is_explained_not_inferred(self):
        x = mod.analyze(payload())
        self.assertEqual(x["main_feedback_queued_total"], 2)
        self.assertEqual(x["feedback_fraction_of_main_queued_pct"], 100.0)
        self.assertEqual(x["repo_queued_total"], 3)
        self.assertEqual(
            x["skip_eligibility"], "UNKNOWN_UNTIL_EXACT_OPEN_PR_LINKAGE_PROVEN"
        )
        self.assertEqual(x["root_closures"], 0)
        self.assertEqual(x["admission"], "HOLD")

    def test_partial_sample_blocks_extrapolation(self):
        p = payload()
        p["main_queued"]["total_count"] = 9
        p["repository_queued"]["total_count"] = 10
        x = mod.analyze(p)
        self.assertFalse(x["main_sample_complete"])
        self.assertIsNone(x["main_feedback_queued_total"])
        self.assertIsNone(x["feedback_fraction_of_main_queued_pct"])
        self.assertEqual(x["main_feedback_workflow_run_sample"], 2)

    def test_zero_queue_remains_zero_without_division(self):
        p = payload()
        p["main_queued"] = {"total_count": 0, "workflow_runs": []}
        p["repository_queued"] = {"total_count": 0, "workflow_runs": []}
        x = mod.analyze(p)
        self.assertEqual(x["main_feedback_queued_total"], 0)
        self.assertEqual(x["feedback_fraction_of_main_queued_pct"], 0.0)

    def test_wrong_sha_rejected(self):
        p = payload()
        p["main_queued"]["workflow_runs"][0]["head_sha"] = "b" * 40
        with self.assertRaisesRegex(ValueError, "SHA mismatch"):
            mod.analyze(p)

    def test_duplicate_run_id_rejected(self):
        p = payload()
        p["main_queued"]["workflow_runs"][1]["id"] = 100
        with self.assertRaisesRegex(ValueError, "repeated run"):
            mod.analyze(p)

    def test_queue_count_inconsistency_rejected(self):
        p = payload()
        p["repository_queued"]["total_count"] = 1
        with self.assertRaises(ValueError):
            mod.analyze(p)

    def test_nonqueued_row_rejected(self):
        p = payload()
        p["main_queued"]["workflow_runs"][0]["status"] = "completed"
        with self.assertRaises(ValueError):
            mod.analyze(p)

    def test_timezone_unknown_rejected(self):
        p = payload()
        p["observed_at"] = "2026-10-15T08:18:00+02:00"
        with self.assertRaises(ValueError):
            mod.analyze(p)

    def test_fake_boolean_id_rejected(self):
        p = payload()
        p["main_queued"]["workflow_runs"][0]["id"] = True
        with self.assertRaises(ValueError):
            mod.analyze(p)

    def test_manifest_binds_written_receipt(self):
        p = payload()
        with tempfile.TemporaryDirectory() as d:
            output = Path(d)
            x = mod.emit(p, output)
            m = json.loads((output / "manifest.json").read_text())
            import hashlib

            self.assertEqual(
                hashlib.sha256((output / "pressure.json").read_bytes()).hexdigest(),
                m["sha256"]["pressure.json"],
            )
            self.assertFalse(x["authority_transfer"])
            self.assertFalse(x["remote_mutation_authorized"])

    def test_order_invariant_byte_output(self):
        p = payload()
        q = copy.deepcopy(p)
        q["main_queued"]["workflow_runs"].reverse()
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            mod.emit(p, Path(a))
            mod.emit(q, Path(b))
            self.assertEqual(
                (Path(a) / "pressure.json").read_bytes(),
                (Path(b) / "pressure.json").read_bytes(),
            )


if __name__ == "__main__":
    unittest.main()
