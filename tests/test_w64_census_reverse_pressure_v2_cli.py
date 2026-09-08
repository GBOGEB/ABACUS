from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_w64_v2_cli_imports_when_executed_from_repo_root() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "tools/w64_census_reverse_pressure_v2.py", "--help"],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--census" in result.stdout
    assert "--out" in result.stdout
