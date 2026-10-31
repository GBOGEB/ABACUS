"""W31 W29 comparator CLI must run under the source-root module namespace."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/w29-cbd-temporal-matched-coverage.yml"


class NativeW29EntrypointTests(unittest.TestCase):
    def test_relative_script_mode_is_forbidden(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python -m tools.recovery.w29_temporal_native_compare", text)
        self.assertNotIn("python tools/recovery/w29_temporal_native_compare.py", text)

    def test_pinned_module_import_is_resolvable_from_repository_root(self):
        command = [
            sys.executable,
            "-m",
            "tools.recovery.w29_temporal_native_compare",
            "--help",
        ]
        run = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, check=False, timeout=20
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("--exact-head", run.stdout)

    def test_no_coverage_or_sha_guard_omitted(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        for required in (
            "--before-cov",
            "--after-cov",
            "--before-junit",
            "--after-junit",
            "--exact-head",
            "--out w29-matched-coverage.json",
            "if-no-files-found: error",
            "git rev-parse HEAD",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_four_interpreter_and_os_cells_retained(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(text.count("os: ubuntu-latest"), 3)
        self.assertEqual(text.count("os: windows-latest"), 1)
        for v in ("python: '3.10'", "python: '3.11'", "python: '3.12'"):
            self.assertIn(v, text)

    def test_strict_comparator_does_not_skip_manifest_on_failure(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("continue-on-error: true", text)
        self.assertIn("w29-evidence-manifest.json", text)


if __name__ == "__main__":
    unittest.main()
