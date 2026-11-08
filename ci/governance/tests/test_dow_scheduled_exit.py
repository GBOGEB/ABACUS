"""DOW scheduled steps must not turn real Python failures into green runs.

This suite runs a fake Python executable, never the production orchestrator.
It is deliberately included in CI Workflow Governance's unittest discovery.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github/workflows/dow-scheduled.yml"


def step_script(name: str) -> str:
    source = WORKFLOW.read_text(encoding="utf-8")
    pattern = rf"(?m)^      - name: {re.escape(name)}\n        run: \|\n((?:          [^\n]*\n)+)"
    match = re.search(pattern, source)
    if not match:
        raise AssertionError(f"Missing literal Bash run block for {name!r}")
    return "\n".join(line[10:] for line in match.group(1).splitlines()) + "\n"


class DowScheduledExitContract(unittest.TestCase):
    STEPS = {
        "Run tests": "-m pytest DMAIC_V3/tests/",
        "Run DMAIC Pipeline": "DMAIC_V3/full_pipeline_orchestrator.py",
    }

    def run_stubbed(self, name: str, exit_code: int) -> tuple[int, str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stub = root / "python"
            stub.write_text(
                "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$DOW_STUB_LOG\"\n"
                "exit \"$DOW_STUB_EXIT\"\n",
                encoding="utf-8",
            )
            stub.chmod(0o755)
            log = root / "invocations.txt"
            env = os.environ.copy()
            env.update(
                {
                    "PATH": str(root) + os.pathsep + env.get("PATH", ""),
                    "DOW_STUB_EXIT": str(exit_code),
                    "DOW_STUB_LOG": str(log),
                }
            )
            result = subprocess.run(
                ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", step_script(name)],
                cwd=root,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            invocations = log.read_text(encoding="utf-8") if log.exists() else ""
            return result.returncode, invocations

    def test_both_python_failures_propagate_as_terminal_red(self):
        for name, expected_args in self.STEPS.items():
            with self.subTest(step=name):
                result, invocations = self.run_stubbed(name, 37)
                self.assertEqual(37, result)
                self.assertEqual(expected_args, invocations.strip())

    def test_both_python_successes_remain_green(self):
        for name, expected_args in self.STEPS.items():
            with self.subTest(step=name):
                result, invocations = self.run_stubbed(name, 0)
                self.assertEqual(0, result)
                self.assertEqual(expected_args, invocations.strip())

    def test_no_failure_swallowing_in_execution_steps(self):
        for name in self.STEPS:
            with self.subTest(step=name):
                script = step_script(name)
                self.assertIn("set -euo pipefail", script)
                self.assertNotRegex(script, r"\|\|\s*(?:echo|true)\b")
                self.assertNotIn("set +e", script)

    def test_failure_diagnostics_are_kept_and_notified(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertRegex(source, r"- name: Upload execution logs\n        if: always\(\)")
        self.assertRegex(source, r"- name: Notify on failure\n        if: failure\(\)")


if __name__ == "__main__":
    unittest.main()
