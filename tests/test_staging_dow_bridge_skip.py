"""G-AB-STAGING-DOW (#2721): staging/test_integration_bridge.py is collected
and skipped with a recorded reason when the external DOW package is absent.

pytest.ini excludes staging/ via norecursedirs, so no CI step collects the
file directly. This test runs a separate pytest process on that one file and
asserts the outcome, so the main CI test step records it.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_TEST = REPO_ROOT / "staging" / "test_integration_bridge.py"
REASON = "G-AB-STAGING-DOW: external DOW package not installed in CI"


def _run_bridge_suite() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(BRIDGE_TEST.relative_to(REPO_ROOT)),
            "-o",
            "addopts=",
            "-p",
            "no:cacheprovider",
            "-rs",
            "-q",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=120,
    )


def _check_bridge_outcome(dow_installed: bool, returncode: int, output: str) -> None:
    if dow_installed:
        # DOW importable: the bridge suite must actually run and pass.
        assert returncode == 0, output
        assert "passed" in output, output
        assert "skipped" not in output, output
        return
    # A module-level skip collects no items, so pytest exits 5 (NO_TESTS_COLLECTED).
    assert returncode in (0, 5), output
    assert "1 skipped" in output, output
    assert REASON in output, output


def test_staging_dow_bridge_skips_or_runs():
    """Run the bridge file in both cases: skip with reason, or pass with DOW."""
    result = _run_bridge_suite()
    _check_bridge_outcome(
        importlib.util.find_spec("DOW") is not None,
        result.returncode,
        result.stdout + result.stderr,
    )


def test_check_bridge_outcome_rejects_skip_when_dow_installed():
    skipped = "1 skipped SKIPPED [1] " + REASON
    with pytest.raises(AssertionError):
        _check_bridge_outcome(True, 5, skipped)
    _check_bridge_outcome(True, 0, "1 passed in 0.1s")
    _check_bridge_outcome(False, 5, skipped)
    with pytest.raises(AssertionError):
        _check_bridge_outcome(False, 1, "1 failed")
