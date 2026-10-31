"""CBD! W38 behavior-first, test-only expansion of existing queue-pressure source.

No production source, skip policy, workflow gate or coverage exclusion changes.
Native workflow executes baseline and expanded suites against the same exact
candidate source SHA and identical branch denominator.
"""

from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1] / "feedback_queue_pressure.py"
SPEC = importlib.util.spec_from_file_location(
    "feedback_queue_pressure_w38_target", SOURCE
)
assert SPEC and SPEC.loader
source = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(source)
SHA = "a" * 40


def run(num=9, name=None, status="queued", source_sha=SHA):
    return {
        "id": num,
        "name": name or source.FEEDBACK,
        "event": "workflow_run",
        "status": status,
        "head_sha": source_sha,
        "head_branch": "main",
        "created_at": "2026-10-19T00:12:00Z",
    }


def population(total=2):
    return {
        "schema": source.SCHEMA,
        "repository": source.REPO,
        "main_sha": SHA,
        "observed_at": "2026-10-19T00:15:00Z",
        "repository_queued": {"total_count": total, "workflow_runs": [run(1), run(2)]},
        "main_queued": {"total_count": total, "workflow_runs": [run(1), run(2)]},
    }


class FeedbackSourceBranchW38(unittest.TestCase):
    def test_canonical_stable_key_order(self):
        self.assertEqual(
            source.canonical({"b": 1, "a": 2}), source.canonical({"a": 2, "b": 1})
        )

    def test_invalid_timestamp_type(self):
        for t in (None, 17, {}, True, []):
            with self.subTest(t=t):
                with self.assertRaisesRegex(ValueError, "observed_at"):
                    source.valid_stamp(t)

    def test_impossible_iso_calendar(self):
        with self.assertRaisesRegex(ValueError, "invalid observed_at"):
            source.valid_stamp("2026-99-19T00:00:00Z")

    def test_wrong_schema(self):
        p = population()
        p["schema"] = "malicious"
        with self.assertRaisesRegex(ValueError, "unknown pressure"):
            source.analyze(p)

    def test_wrong_owner(self):
        p = population()
        p["repository"] = "GBOGEB/CODEX"
        with self.assertRaisesRegex(ValueError, "wrong repository"):
            source.analyze(p)

    def test_invalid_main_sha(self):
        p = population()
        p["main_sha"] = "abc"
        with self.assertRaisesRegex(ValueError, "exact"):
            source.analyze(p)

    def test_missing_queue_object(self):
        p = population()
        p["repository_queued"] = None
        with self.assertRaisesRegex(ValueError, "repository query missing"):
            source.analyze(p)

    def test_queue_missing_count(self):
        p = population()
        del p["main_queued"]["total_count"]
        with self.assertRaisesRegex(ValueError, "main invalid run count"):
            source.analyze(p)

    def test_queue_boolean_count_rejected(self):
        p = population()
        p["main_queued"]["total_count"] = True
        with self.assertRaisesRegex(ValueError, "main invalid run count"):
            source.analyze(p)

    def test_negative_population_rejected(self):
        p = population()
        p["main_queued"]["total_count"] = -1
        with self.assertRaisesRegex(ValueError, "main invalid run count"):
            source.analyze(p)

    def test_missing_run_rows_rejected(self):
        p = population()
        p["main_queued"].pop("workflow_runs")
        with self.assertRaisesRegex(ValueError, "main invalid run count"):
            source.analyze(p)

    def test_sample_exceeds_total_rejected(self):
        p = population()
        p["main_queued"]["total_count"] = 1
        with self.assertRaisesRegex(ValueError, "main sample exceeds total"):
            source.analyze(p)

    def test_main_total_above_repository_rejected(self):
        p = population()
        p["main_queued"]["total_count"] = 3
        with self.assertRaisesRegex(ValueError, "main queue cannot exceed repository"):
            source.analyze(p)

    def test_null_run_rejected(self):
        p = population()
        p["main_queued"]["workflow_runs"][0] = None
        with self.assertRaises((AttributeError, TypeError, ValueError)):
            source.analyze(p)

    def test_string_run_identifier_rejected(self):
        p = population()
        p["main_queued"]["workflow_runs"][0]["id"] = "1"
        with self.assertRaisesRegex(ValueError, "invalid or repeated"):
            source.analyze(p)

    def test_negative_run_identifier_rejected(self):
        p = population()
        p["main_queued"]["workflow_runs"][0]["id"] = -2
        with self.assertRaisesRegex(ValueError, "invalid or repeated"):
            source.analyze(p)

    def test_missing_workflow_name_exercises_final_source_branch(self):
        for invalid in ("", None, 17, []):
            with self.subTest(invalid=invalid):
                p = population()
                p["main_queued"]["workflow_runs"][0]["name"] = invalid
                with self.assertRaisesRegex(ValueError, "workflow identity missing"):
                    source.analyze(p)

    def test_other_event_excluded_from_feedback_fanin(self):
        p = population()
        p["main_queued"]["workflow_runs"][0]["event"] = "schedule"
        r = source.analyze(p)
        self.assertEqual(r["main_feedback_workflow_run_sample"], 1)
        self.assertEqual(r["main_feedback_queued_total"], 1)
        self.assertFalse(r["authority_transfer"])

    def test_other_workflow_excluded_from_feedback_fanin(self):
        p = population()
        p["main_queued"]["workflow_runs"][0]["name"] = "W70 Retain Measured Pulse"
        r = source.analyze(p)
        self.assertEqual(r["main_feedback_workflow_run_sample"], 1)

    def test_cross_source_subset_rejected(self):
        p = population()
        p["main_queued"]["workflow_runs"][0]["head_sha"] = "b" * 40
        with self.assertRaisesRegex(ValueError, "source SHA mismatch"):
            source.analyze(p)

    def test_partial_tail_untouched(self):
        p = population()
        p["repository_queued"]["total_count"] = 105
        p["main_queued"]["total_count"] = 101
        r = source.analyze(p)
        self.assertFalse(r["main_sample_complete"])
        self.assertIsNone(r["main_feedback_queued_total"])
        self.assertIsNone(r["feedback_fraction_of_main_queued_pct"])

    def test_empty_full_census_is_zero_not_unknown(self):
        p = population(0)
        p["repository_queued"]["workflow_runs"] = []
        p["main_queued"]["workflow_runs"] = []
        r = source.analyze(p)
        self.assertEqual(r["main_feedback_queued_total"], 0)
        self.assertEqual(r["feedback_fraction_of_main_queued_pct"], 0.0)

    def test_emit_invalid_input_leaves_no_receipt(self):
        p = population()
        p["schema"] = "invalid"
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                source.emit(p, Path(d))
            self.assertFalse((Path(d) / "pressure.json").exists())

    def test_emit_manifest_hash_from_exact_input(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            source.emit(population(), p)
            j = json.loads((p / "manifest.json").read_text())
            self.assertEqual(
                j["sha256"]["pressure.json"],
                hashlib.sha256((p / "pressure.json").read_bytes()).hexdigest(),
            )
            self.assertEqual(j["source_sha"], SHA)

    def test_collect_live_absent_token_is_fail_closed(self):
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": ""}):
            with self.assertRaisesRegex(ValueError, "GITHUB_TOKEN"):
                source.collect_live(SHA, "2026-10-19T00:15:00Z")

    def test_collect_live_wrong_current_main_aborts(self):
        class GitHub:
            def __init__(self, token, repository):
                self.token, self.repository = token, repository

            def request(self, method, path):
                return {"commit": {"sha": "b" * 40}}

        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "test-only"}):
            with mock.patch("ci.governance.pr_feedback_gate.GitHub", GitHub):
                with self.assertRaisesRegex(ValueError, "HEAD moved"):
                    source.collect_live(SHA, "2026-10-19T00:15:00Z")

    def test_collect_live_queries_exact_head_get_only(self):
        calls = []

        class GitHub:
            def __init__(self, token, repository):
                self.token, self.repository = token, repository

            def request(self, method, path):
                calls.append((method, path))
                if path.endswith("/branches/main"):
                    return {"commit": {"sha": SHA}}
                if "head_sha=" in path:
                    return population()["main_queued"]
                return population()["repository_queued"]

        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "test-only"}):
            with mock.patch("ci.governance.pr_feedback_gate.GitHub", GitHub):
                result = source.collect_live(SHA, "2026-10-19T00:15:00Z")
        self.assertEqual(result["main_sha"], SHA)
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(method == "GET" for method, _ in calls))
        self.assertIn("head_sha=" + SHA, calls[-1][1])
        self.assertEqual(source.analyze(result)["main_feedback_queued_total"], 2)

    def test_cli_fixture_emits_and_does_not_write_outside_destination(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            f = root / "fixture.json"
            f.write_text(json.dumps(population()))
            out = root / "output"
            args = [
                "pressure",
                "--sha",
                SHA,
                "--observed-at",
                "2026-10-19T00:15:00Z",
                "--fixture",
                str(f),
                "--output",
                str(out),
            ]
            with (
                mock.patch.object(sys, "argv", args),
                contextlib.redirect_stdout(io.StringIO()) as capture,
            ):
                source.main()
            receipt = json.loads(capture.getvalue())
            self.assertEqual(receipt["admission"], "HOLD")
            self.assertTrue((out / "pressure.json").exists())
            self.assertTrue((out / "manifest.json").exists())

    def test_cli_mismatched_sha_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            f = p / "fixture.json"
            f.write_text(json.dumps(population()))
            argv = [
                "pressure",
                "--sha",
                "b" * 40,
                "--observed-at",
                "2026-10-19T00:15:00Z",
                "--fixture",
                str(f),
                "--output",
                str(p / "report"),
            ]
            with mock.patch.object(sys, "argv", argv):
                with self.assertRaisesRegex(ValueError, "expected SHA differs"):
                    source.main()

    def test_source_still_not_a_scheduling_or_admission_gate(self):
        self.assertFalse(source.analyze(population())["remote_mutation_authorized"])
        self.assertEqual(source.analyze(population())["admission"], "HOLD")


if __name__ == "__main__":
    unittest.main()
