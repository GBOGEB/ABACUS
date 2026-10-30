"""Governed scheduled-DAG negative/reverse tests (all observations synthetic)."""

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "cbd_scheduled_pulse", ROOT / "scripts" / "cbd_scheduled_pulse.py"
)
pulse = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pulse)


def fixture(queued=6, running=2):
    return {
        "schema": pulse.SCHEMA,
        "repository": "GBOGEB/ABACUS",
        "source_sha": "1" * 40,
        "capacity": {"queued": queued, "in_progress": running},
        "authority_transfer": False,
        "security_waiver": False,
        "merge_admission": "HOLD",
    }


class ScheduledDAGTests(unittest.TestCase):
    def test_weekday_methods_are_deterministic(self):
        self.assertEqual("gogreen", pulse.method_for_date("2026-10-19"))
        self.assertEqual("everred", pulse.method_for_date("2026-10-20"))
        self.assertEqual("code_purple", pulse.method_for_date("2026-10-24"))

    def test_auto_selects_go_green_with_readonly_envelope(self):
        result = pulse.plan(fixture(), "auto", "2026-10-19")
        self.assertEqual("gogreen", result["selected_method"])
        self.assertEqual("BOUNDED_READ_ONLY", result["gate"])
        self.assertEqual("gogreen", result["execute_mode"])
        self.assertEqual("HOLD", result["controls"]["merge_admission"])
        self.assertFalse(result["controls"]["rerun_requested"])

    def test_high_queue_produces_cold_plan_only(self):
        result = pulse.plan(fixture(653, 8), "everred", "2026-10-20")
        self.assertEqual("QUEUE_SATURATED", result["gate"])
        self.assertEqual("none", result["execute_mode"])
        self.assertEqual("COLD_PLAN_ONLY", result["dispatch_scope"])
        self.assertEqual(653, result["metrics"]["queued"])
        self.assertIsNone(result["metrics"]["main_coverage"])

    def test_missing_capacity_is_not_zero(self):
        result = pulse.plan(fixture(None, None), "gogreen")
        self.assertEqual("CAPACITY_UNKNOWN", result["gate"])
        self.assertIsNone(result["metrics"]["queued"])
        self.assertIsNone(result["metrics"]["in_progress"])
        self.assertEqual("none", result["execute_mode"])

    def test_exact_threshold_is_eligible_one_more_is_not(self):
        self.assertEqual(
            "BOUNDED_READ_ONLY", pulse.plan(fixture(40, 12), "everred")["gate"]
        )
        self.assertEqual(
            "QUEUE_SATURATED", pulse.plan(fixture(41, 12), "everred")["gate"]
        )
        self.assertEqual(
            "QUEUE_SATURATED", pulse.plan(fixture(40, 13), "everred")["gate"]
        )

    def test_full_never_schedules_without_real_manual_ack(self):
        blocked = pulse.plan(fixture(), "full", event="schedule", full_ack=True)
        self.assertEqual("FULL_REQUIRES_MANUAL_ACK", blocked["gate"])
        blocked = pulse.plan(fixture(), "full", event="workflow_dispatch")
        self.assertEqual("none", blocked["execute_mode"])
        permitted = pulse.plan(
            fixture(), "full", event="workflow_dispatch", full_ack=True
        )
        self.assertEqual("BOUNDED_READ_ONLY", permitted["gate"])
        self.assertFalse(permitted["controls"]["source_mutated"])
        self.assertFalse(permitted["controls"]["worker_launch_claimed"])

    def test_gogreen_and_everred_are_disjoint_stage_selections(self):
        g = pulse.plan(fixture(), "gogreen")
        e = pulse.plan(fixture(), "everred")
        g_ids = {p["atom"] for p in g["stages"] if p["selected"]}
        e_ids = {p["atom"] for p in e["stages"] if p["selected"]}
        self.assertEqual({"N0", "N3"}, g_ids)
        self.assertEqual({"N0", "N1", "N2"}, e_ids)

    def test_graph_dependencies_never_infer_approvals(self):
        result = pulse.plan(fixture(), "full", event="workflow_dispatch", full_ack=True)
        graph = result["dag"]
        self.assertTrue(any(x["target"] == "N5" for x in graph["edges"]))
        self.assertTrue(
            all(x["accepted_root_closures"] is None for x in result["stages"])
        )
        self.assertTrue(all(x["human_approval"] is None for x in result["stages"]))
        self.assertEqual(0, result["metrics"]["source_writers_without_lease"])

    def test_inverted_security_claim_rejected(self):
        for key, value in (
            ("security_waiver", True),
            ("authority_transfer", True),
            ("merge_admission", "PASS"),
        ):
            observation = fixture()
            observation[key] = value
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, "waiver"):
                    pulse.plan(observation)

    def test_negative_foreign_repo_and_bad_head_rejected(self):
        observation = fixture()
        observation["repository"] = "GBOGEB/CODEX"
        with self.assertRaisesRegex(ValueError, "repository"):
            pulse.plan(observation)
        observation = fixture()
        observation["source_sha"] = "old-rebased-head"
        with self.assertRaisesRegex(ValueError, "source SHA"):
            pulse.plan(observation)

    def test_boolean_capacity_rejected(self):
        observation = fixture(True, 0)
        with self.assertRaisesRegex(ValueError, "queued"):
            pulse.plan(observation)
        observation = fixture(0, False)
        with self.assertRaisesRegex(ValueError, "in-progress"):
            pulse.plan(observation)

    def test_reverse_fault_injection_never_promotes_main(self):
        original = pulse.plan(fixture(), "gogreen")
        changed = pulse.plan(fixture(653, 10), "gogreen")
        self.assertEqual("BOUNDED_READ_ONLY", original["gate"])
        self.assertEqual("QUEUE_SATURATED", changed["gate"])
        for result in (original, changed):
            self.assertIsNone(result["metrics"]["correct_merges"])
            self.assertEqual("HOLD", result["controls"]["merge_admission"])

    def test_bytes_and_hashes_deterministic(self):
        result = pulse.plan(fixture(), "code_purple")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            pulse.write(result, path)
            first = {f.name: f.read_bytes() for f in path.iterdir()}
            pulse.write(result, path)
            second = {f.name: f.read_bytes() for f in path.iterdir()}
            self.assertEqual(first, second)
            digests = json.loads(first["sha256.json"])
            for name, sha in digests.items():
                self.assertEqual(hashlib.sha256(first[name]).hexdigest(), sha)
            ledger = json.loads(first["ledger-proposal.jsonl"])
            self.assertEqual("NOT_CANONICAL_EVENT", ledger["authority"])
            self.assertEqual(0, ledger["root_closure_credit"])

    def test_bad_method_and_event_rejected(self):
        with self.assertRaisesRegex(ValueError, "method"):
            pulse.plan(fixture(), "merge_all")
        with self.assertRaisesRegex(ValueError, "event"):
            pulse.plan(fixture(), "gogreen", event="untrusted_webhook")

    def test_html_has_no_unescaped_source_claim(self):
        result = pulse.plan(fixture(), "gogreen")
        result["stages"][0]["title"] = "<script>alert(1)</script>"
        rendered = pulse.render_html(result)
        self.assertNotIn("<script>alert(1)</script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_cli_direct_entrypoint_with_github_output_receipt(self):
        import contextlib
        import io
        import runpy
        import sys
        from unittest import mock

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            observation = base / "snapshot.json"
            observation.write_text(json.dumps(fixture()), encoding="utf-8")
            destination = base / "output"
            github_output = base / "github-output.txt"
            argv = [
                str(ROOT / "scripts" / "cbd_scheduled_pulse.py"),
                "--observation",
                str(observation),
                "--output-dir",
                str(destination),
                "--method",
                "gogreen",
                "--utc-day",
                "2026-10-19",
                "--event",
                "workflow_dispatch",
                "--github-output",
                str(github_output),
            ]
            with mock.patch.object(sys, "argv", argv):
                with contextlib.redirect_stdout(io.StringIO()) as stream:
                    runpy.run_path(
                        str(ROOT / "scripts" / "cbd_scheduled_pulse.py"),
                        run_name="__main__",
                    )
            self.assertEqual("BOUNDED_READ_ONLY", json.loads(stream.getvalue())["gate"])
            self.assertIn("execute_mode=gogreen", github_output.read_text())
            self.assertTrue((destination / "sha256.json").exists())

    def test_cli_direct_entrypoint_without_github_output_stays_deferred(self):
        import contextlib
        import io
        import runpy
        import sys
        from unittest import mock

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            observation = base / "snapshot.json"
            observation.write_text(json.dumps(fixture(653, 8)), encoding="utf-8")
            destination = base / "output"
            argv = [
                str(ROOT / "scripts" / "cbd_scheduled_pulse.py"),
                "--observation",
                str(observation),
                "--output-dir",
                str(destination),
                "--method",
                "everred",
                "--utc-day",
                "2026-10-20",
                "--event",
                "schedule",
            ]
            with mock.patch.object(sys, "argv", argv):
                with contextlib.redirect_stdout(io.StringIO()) as stream:
                    runpy.run_path(
                        str(ROOT / "scripts" / "cbd_scheduled_pulse.py"),
                        run_name="__main__",
                    )
            report = json.loads(stream.getvalue())
            self.assertEqual("QUEUE_SATURATED", report["gate"])
            self.assertEqual(
                "none",
                json.loads((destination / "pulse-plan.json").read_text())[
                    "execute_mode"
                ],
            )


if __name__ == "__main__":
    unittest.main()
