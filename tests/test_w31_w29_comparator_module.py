"""W31 W29 comparator CLI must run under the source-root module namespace."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/w29-cbd-temporal-matched-coverage.yml"
# numpy==1.26.4 is pinned in the workflow, so ssot/python_versions.yaml caps it
# to the numpy-1x-pin lane (3.11-3.12); the former 3.10 cell was EOL and removed.
LANE = json.loads(
    (ROOT / "ssot/python_versions.lanes.json").read_text(encoding="utf-8")
)["lanes"]["numpy-1x-pin"]


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

    def test_lane_interpreter_and_os_cells_retained(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(text.count("os: ubuntu-latest"), len(LANE["versions"]))
        self.assertEqual(text.count("os: windows-latest"), 1)
        for v in LANE["versions"]:
            self.assertIn(f"python: '{v}'", text)
        self.assertNotIn("python: '3.10'", text)

    def test_strict_comparator_does_not_skip_manifest_on_failure(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("continue-on-error: true", text)
        self.assertIn("w29-evidence-manifest.json", text)


if __name__ == "__main__":
    unittest.main()
