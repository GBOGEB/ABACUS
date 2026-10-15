"""Fail-closed checks for wave/pulse history and unknown evidence."""

import hashlib
import importlib.util
import json
import sys
from unittest import mock
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "tools/mip2/mip_wave_history.py"
SPEC = importlib.util.spec_from_file_location("mip_wave_history", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
HEAD = "a" * 40


def fixture(directory, pulse="P01", wave="W1", sequence=1):
    """Build a valid, synthetic, explicitly non-admitted receipt."""
    receipt = {
        "schema": "abacus.mip.wave-pulse.v1",
        "repository": "GBOGEB/ABACUS",
        "head_sha": HEAD,
        "wave_id": wave,
        "merge_admitted": False,
        "disposition": "P0_HOLD",
        "coverage": {"status": "UNKNOWN"},
        "root_counts": {"open": 1, "root_closed": 0},
        "first_reds": [],
        "tests": {"passed": 6, "failed": 0, "skipped": 0},
    }
    name = f"{pulse}.json"
    source = directory / name
    source.write_text(json.dumps(receipt), encoding="utf-8")
    entry = {
        "wave_id": wave,
        "iteration_id": "I01",
        "pulse_id": pulse,
        "sequence": sequence,
        "source_kind": "SYNTHETIC_CONTROL",
        "run_id": 123,
        "job_id": None,
        "head_sha": HEAD,
        "receipt_path": name,
        "receipt_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }
    return receipt, entry


class HistoryTests(unittest.TestCase):
    """Assert deterministic, evidence-classified pulse history."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.receipt, self.entry = fixture(self.root)
        self.manifest = {
            "schema": MODULE.INPUT_SCHEMA,
            "repository": "GBOGEB/ABACUS",
            "records": [self.entry],
        }

    def run_history(self):
        """Evaluate the manifest without modifying its inputs."""
        return MODULE.evaluate(self.manifest, self.root)

    def rewrite_receipt(self):
        """Synchronize fixture bytes and declared digest."""
        source = self.root / "P01.json"
        source.write_text(json.dumps(self.receipt), encoding="utf-8")
        self.entry["receipt_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()

    def test_single_synthetic_is_not_formal_progress(self):
        result = self.run_history()
        self.assertEqual(result["synthetic_count"], 1)
        self.assertEqual(result["merge_admission"], "HOLD")
        self.assertEqual(result["formal_root_closures"], "UNKNOWN")
        self.assertEqual(result["pulses"][0]["coverage_delta_pp"], "UNKNOWN")

    def test_multiple_pulses_render_individual_rows(self):
        _, second = fixture(self.root, pulse="P02", sequence=2)
        self.manifest["records"] = [second, self.entry]
        result = self.run_history()
        rendered = MODULE.render_markdown(result)
        self.assertEqual(result["pulse_count"], 2)
        self.assertLess(rendered.index("P01"), rendered.index("P02"))
        self.assertIn("not verified JUnit", rendered)

    def test_wave_summary_counts_pulses_not_independent_runs(self):
        _, second = fixture(self.root, pulse="P02", sequence=2)
        self.manifest["records"].append(second)
        result = self.run_history()
        wave = result["waves"][0]
        self.assertEqual(wave["pulse_count"], 2)
        self.assertEqual(wave["distinct_run_ids"], 1)
        self.assertEqual(wave["synthetic_pulses"], 2)
        self.assertEqual(wave["open_root_observations"], [1, 1])
        self.assertEqual(wave["coverage_gains_verified"], "UNKNOWN")
        self.assertIn("Per-wave scale census", MODULE.render_markdown(result))

    def test_multiple_waves_are_not_cross_credited(self):
        _, second = fixture(self.root, pulse="P02", wave="W2")
        self.manifest["records"].append(second)
        result = self.run_history()
        self.assertEqual(len(result["waves"]), 2)
        self.assertEqual(result["waves"][0]["pulse_count"], 1)
        self.assertEqual(result["waves"][1]["root_closures_verified"], "UNKNOWN")

    def test_bad_digest_rejected(self):
        self.entry["receipt_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "bytes mismatch"):
            self.run_history()

    def test_changed_receipt_bytes_rejected(self):
        (self.root / "P01.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "bytes mismatch"):
            self.run_history()

    def test_duplicate_pulse_rejected(self):
        self.manifest["records"].append(dict(self.entry))
        with self.assertRaisesRegex(ValueError, "duplicate pulse"):
            self.run_history()

    def test_duplicate_sequence_rejected(self):
        _, second = fixture(self.root, pulse="P02", sequence=1)
        self.manifest["records"].append(second)
        with self.assertRaisesRegex(ValueError, "duplicate pulse"):
            self.run_history()

    def test_wrong_head_rejected(self):
        self.entry["head_sha"] = "c" * 40
        with self.assertRaisesRegex(ValueError, "receipt SHA mismatch"):
            self.run_history()

    def test_traversal_rejected(self):
        self.entry["receipt_path"] = "../P01.json"
        with self.assertRaisesRegex(ValueError, "unsafe or missing"):
            self.run_history()

    def test_missing_receipt_rejected(self):
        self.entry["receipt_path"] = "missing.json"
        with self.assertRaisesRegex(ValueError, "unsafe or missing"):
            self.run_history()

    def test_bad_native_run_id_rejected(self):
        self.entry["run_id"] = 0
        with self.assertRaisesRegex(ValueError, "invalid run ID"):
            self.run_history()

    def test_fake_merged_flag_rejected(self):
        self.receipt["merge_admitted"] = True
        self.rewrite_receipt()
        with self.assertRaisesRegex(ValueError, "independent verification"):
            self.run_history()

    def test_comparable_delta_displayed_but_not_attested(self):
        self.receipt["coverage"] = {"status": "COMPARABLE", "delta_pp": 1.25}
        self.rewrite_receipt()
        result = self.run_history()
        self.assertEqual(result["pulses"][0]["coverage_delta_pp"], 1.25)
        self.assertEqual(result["pulses"][0]["provenance_status"], "HASH_MATCH_LOCAL_ONLY")
        self.assertEqual(result["measured_main_gain_pp"], "UNKNOWN")

    def test_unverified_operational_not_trusted_by_name(self):
        self.entry["source_kind"] = "UNVERIFIED_OPERATIONAL"
        result = self.run_history()
        self.assertEqual(result["unverified_operational_count"], 1)
        self.assertEqual(result["pulses"][0]["authenticated_rex_receipts"], "UNKNOWN")

    def test_invalid_coverage_value_fails_closed(self):
        self.receipt["coverage"] = {"status": "COMPARABLE", "delta_pp": 110}
        self.rewrite_receipt()
        with self.assertRaisesRegex(ValueError, "invalid comparable delta"):
            self.run_history()

    def test_cli_emits_two_text_only_receipts(self):
        manifest_file = self.root / "input.json"
        out = self.root / "output"
        manifest_file.write_text(json.dumps(self.manifest), encoding="utf-8")
        argv = [
            "pulse-history",
            "--manifest", str(manifest_file),
            "--artifact-root", str(self.root),
            "--output-dir", str(out),
        ]
        with mock.patch.object(sys, "argv", argv):
            MODULE.main()
        report = json.loads((out / "mip_wave_history.json").read_text())
        text = (out / "mip_wave_history.md").read_text()
        self.assertEqual(report["pulse_count"], 1)
        self.assertIn("SYNTHETIC_CONTROL", text)
        self.assertIn("UNKNOWN", text)

    def test_cli_rejects_wrong_schema_without_outputs(self):
        manifest_file = self.root / "input.json"
        out = self.root / "output"
        manifest_file.write_text(json.dumps({"schema": "bad"}), encoding="utf-8")
        argv = [
            "pulse-history",
            "--manifest", str(manifest_file),
            "--artifact-root", str(self.root),
            "--output-dir", str(out),
        ]
        with mock.patch.object(sys, "argv", argv):
            with self.assertRaisesRegex(ValueError, "invalid history schema"):
                MODULE.main()
        self.assertFalse(out.exists())

    def test_output_is_deterministic(self):
        a = json.dumps(self.run_history(), sort_keys=True)
        b = json.dumps(self.run_history(), sort_keys=True)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
