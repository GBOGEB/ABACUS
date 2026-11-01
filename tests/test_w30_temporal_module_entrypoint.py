"""Regression for the W29 cross-platform ModuleNotFoundError first red.

The entrypoint must be executed as a module from repository root, retaining
'scripts' importability. An isolated script-path invocation loses that context.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows" / "w29-cbd-temporal-matched-coverage.yml"


def test_module_entrypoint_can_import_temporal_contract():
    result = subprocess.run(
        [sys.executable, "-m", "tools.recovery.w29_temporal_native_compare", "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert "--before-cov" in result.stdout
    assert "--exact-head" in result.stdout


def test_native_workflow_does_not_reintroduce_script_path_import_failure():
    source = WF.read_text(encoding="utf-8")
    assert "python -m tools.recovery.w29_temporal_native_compare" in source
    assert "python tools/recovery/w29_temporal_native_compare.py" not in source
    assert "tests/test_w30_temporal_module_entrypoint.py" in source
    assert "persist-credentials: false" in source
    assert "Fail closed on JUnit provenance" in source
