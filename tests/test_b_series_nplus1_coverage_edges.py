"""Exercise legitimate N+1 evidence rejects and CLI output on frozen source.

These are behavioral tests, not fabricated native receipts or a security waiver.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import b_series_nplus1_metrics as adapter  # noqa: E402

BASE = ROOT / "docs/ci/B_SERIES_NATIVE_NPLUS1_20261017.json"


class NPlusOneCoverageEdges(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.valid = json.loads(BASE.read_text(encoding="utf-8"))

    def test_unrecognized_extension_fails_closed(self):
        data = copy.deepcopy(self.valid)
        data["extension"] = "UNREVIEWED_SOURCE"
        with self.assertRaisesRegex(
            adapter.core.EvidenceError, "wrong N\\+1 evidence extension"
        ):
            adapter.extend(data)

    def test_unbound_frozen_three_pulse_lineage_fails_closed(self):
        data = copy.deepcopy(self.valid)
        data["versioned_from"] = "docs/ci/untrusted.json"
        with self.assertRaisesRegex(
            adapter.core.EvidenceError, "frozen N-2 to N source"
        ):
            adapter.extend(data)

    def test_missing_scanner_blob_fails_closed(self):
        data = copy.deepcopy(self.valid)
        data["observations"][0]["b1_scanner_blob_sha"] = ""
        with self.assertRaisesRegex(
            adapter.core.EvidenceError, "source/configuration binding"
        ):
            adapter.extend(data)

    def test_cli_emits_deterministic_source_bound_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = pathlib.Path(tmp)
            original = folder / "native-source.json"
            output = folder / "metrics" / "nplus1.json"
            original.write_text(json.dumps(self.valid), encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = adapter.main(
                    ["--input", str(original), "--out", str(output)]
                )
            self.assertEqual(code, 0)
            self.assertTrue(output.is_file())
            receipt = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(receipt["pulses"]), 4)
            self.assertEqual(receipt["merge_admission"], "HOLD")
            self.assertIsNone(receipt["formal_root_closures"])
            self.assertEqual(receipt["forecast"]["point_estimate"], 139)
            self.assertIn("DESCRIPTIVE_FOUR_PULSE", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
