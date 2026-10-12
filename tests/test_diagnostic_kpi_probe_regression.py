"""Regression tests for the narrowly repaired diagnostic KPI command helper."""

import ast
import contextlib
import io
import os
import runpy
import shlex
import subprocess
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch


ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "scripts" / "diagnostic_kpi_probe.py"


class DiagnosticKpiProbeTests(unittest.TestCase):
    """Check the helper with all top-level network/process activity mocked."""

    @classmethod
    def setUpClass(cls):
        source = PROBE.read_text(encoding="utf-8")
        ast.parse(source, filename=str(PROBE))
        response = MagicMock()
        response.__enter__.return_value.status = 200
        with (
            patch.object(urllib.request, "urlopen", return_value=response),
            patch.object(os.path, "exists", return_value=False),
            patch.object(subprocess, "run", return_value=Mock(returncode=0)),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            namespace = runpy.run_path(str(PROBE), run_name="probe_regression")
        cls.cmd_helper = staticmethod(namespace["cmd"])

    def test_probe_parses_without_real_network_or_processes(self):
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
