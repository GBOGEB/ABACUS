"""Negative controls for the Bandit scanner-completeness contract."""
from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts.ci import bandit_report_guard as guard


def sample() -> dict:
    return {
        "results": [],
        "errors": [],
        "metrics": {"_totals": {"loc": 4}, "./test.py": {"loc": 4}},
    }


class BanditReceiptGuardTests(unittest.TestCase):
    def test_valid_zero_findings_does_not_mean_zero_scanned_files(self):
        self.assertEqual((1, 0), guard.validate_report(sample()))

    def test_reject_scanner_error_even_when_findings_are_empty(self):
        report = sample()
        report["errors"] = [{"filename": "test.py", "reason": "AST parser error"}]
        with self.assertRaisesRegex(ValueError, "1 source files unscanned"):
            guard.validate_report(report)

    def test_reject_unknown_error_inventory(self):
        report = sample()
        report.pop("errors")
        with self.assertRaisesRegex(ValueError, "errors array"):
            guard.validate_report(report)

    def test_reject_zero_scanned_files(self):
        report = sample()
        report["metrics"].pop("./test.py")
        with self.assertRaisesRegex(ValueError, "zero source files"):
            guard.validate_report(report)

    def test_reject_missing_findings_or_totals(self):
        for key in ("results", "metrics"):
            with self.subTest(key=key):
                report = sample()
                report.pop(key)
                with self.assertRaises(ValueError):
                    guard.validate_report(report)

    def test_cli_fails_closed_on_malformed_and_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "bandit.json"
            with contextlib.redirect_stderr(io.StringIO()):
                target.write_text("{not json", encoding="utf-8")
                self.assertEqual(2, guard.main([str(target)]))
                target.write_text(json.dumps({**sample(), "errors": [{"reason": "crash"}]}), encoding="utf-8")
                self.assertEqual(2, guard.main([str(target)]))
            with contextlib.redirect_stdout(io.StringIO()):
                target.write_text(json.dumps(sample()), encoding="utf-8")
                self.assertEqual(0, guard.main([str(target)]))


if __name__ == "__main__":
    unittest.main()
