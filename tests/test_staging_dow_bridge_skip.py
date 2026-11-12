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


@pytest.mark.skipif(
    importlib.util.find_spec("DOW") is not None,
    reason="DOW is installed; the bridge suite runs instead of skipping",
)
def test_staging_dow_bridge_skips_with_recorded_reason():
    result = subprocess.run(
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
    output = result.stdout + result.stderr
    # A module-level skip collects no items, so pytest exits 5 (NO_TESTS_COLLECTED).
    assert result.returncode in (0, 5), output
    assert "1 skipped" in output, output
    assert REASON in output, output
