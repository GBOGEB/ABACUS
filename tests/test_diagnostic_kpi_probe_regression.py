"""Regression tests for the narrowly repaired diagnostic KPI command helper."""

import ast
import shlex
import subprocess
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "scripts" / "diagnostic_kpi_probe.py"


class DiagnosticKpiProbeTests(unittest.TestCase):
    """Check syntax and command behavior without running probe side effects."""

    @classmethod
    def setUpClass(cls):
        source = PROBE.read_text(encoding="utf-8")
        compile(source, str(PROBE), "exec")
        parsed = ast.parse(source, filename=str(PROBE))
        functions = [
            node
            for node in parsed.body
            if isinstance(node, ast.FunctionDef) and node.name == "cmd"
        ]
        if len(functions) != 1:
            raise AssertionError("exactly one cmd helper is required")
        module = ast.Module(body=functions, type_ignores=[])
        namespace = {"shlex": shlex, "subprocess": subprocess}
        exec(compile(module, str(PROBE), "exec"), namespace)
        cls.cmd_helper = staticmethod(namespace["cmd"])

    def test_probe_parses_without_executing_network_or_processes(self):
        self.assertTrue(PROBE.is_file())

    def test_string_command_is_split_and_timeout_is_bounded(self):
        with patch.object(subprocess, "run", return_value=Mock(returncode=0)) as run:
            self.assertEqual(self.cmd_helper("git status --porcelain"), 0)
        run.assert_called_once_with(
            ["git", "status", "--porcelain"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=120,
        )

    def test_sequence_command_remains_a_sequence(self):
        command = ["python", "-m", "compileall", "-q", "scripts"]
        with patch.object(subprocess, "run", return_value=Mock(returncode=0)) as run:
            self.assertEqual(self.cmd_helper(command), 0)
        run.assert_called_once_with(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=120,
        )

    def test_failed_command_is_not_silently_successful(self):
        with patch.object(subprocess, "run", return_value=Mock(returncode=7)):
            with self.assertRaisesRegex(RuntimeError, "nonzero"):
                self.cmd_helper("git status")


if __name__ == "__main__":
    unittest.main()
