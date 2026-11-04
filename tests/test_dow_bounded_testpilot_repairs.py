"""Behavioral regressions for DOW TestPilot-first-red source corrections.

Exercise existing command-line contracts instead of just checking code style.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PREVIEW = ROOT / "scripts" / "preview_diff.py"
RECURSIVE = ROOT / "scripts" / "recursive_build.py"


def invoke(script: Path, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("modified", [False, True])
def test_preview_diff_preserves_hash_comparison_exit_contract(tmp_path, modified):
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("initial\n", encoding="utf-8")
    original = hashlib.sha256(artifact.read_bytes()).hexdigest()
    index = tmp_path / "index.json"
    index.write_text(
        json.dumps({"artefacts": [{"path": str(artifact), "hash": original}]}),
        encoding="utf-8",
    )
    if modified:
        artifact.write_text("changed\n", encoding="utf-8")
    outcome = invoke(PREVIEW, "--index", str(index), cwd=tmp_path)
    assert outcome.returncode == (1 if modified else 0), outcome.stderr
    assert ("[DIFF]" in outcome.stdout) == modified


def test_preview_diff_missing_artifact_still_warns_not_fail(tmp_path):
    index = tmp_path / "index.json"
    index.write_text(
        json.dumps({"artefacts": [{"path": str(tmp_path / "absent"), "hash": "abc"}]}),
        encoding="utf-8",
    )
    outcome = invoke(PREVIEW, "--index", str(index), cwd=tmp_path)
    assert outcome.returncode == 0
    assert "[WARN] missing" in outcome.stdout


@pytest.mark.parametrize("missing", [False, True])
def test_recursive_build_smoke_preserves_missing_artifact_exit(tmp_path, missing):
    artifact = tmp_path / "artifact.txt"
    if not missing:
        artifact.write_text("present\n", encoding="utf-8")
    index = tmp_path / "index.json"
    index.write_text(
        json.dumps({"artefacts": [{"path": str(artifact)}]}),
        encoding="utf-8",
    )
    result = invoke(RECURSIVE, "--smoke", "--index", str(index), cwd=tmp_path)
    assert result.returncode == (1 if missing else 0), result.stderr
    assert ("missing artefacts" in result.stdout) == missing


def test_recursive_build_json_metrics_preserve_source_scope(tmp_path):
    artifact = tmp_path / "asset.txt"
    artifact.write_text("ok", encoding="utf-8")
    index = tmp_path / "index.json"
    output = tmp_path / "metrics.json"
    index.write_text(
        json.dumps({"artefacts": [{"path": str(artifact)}]}), encoding="utf-8"
    )
    result = invoke(
        RECURSIVE, "--index", str(index), "--out", str(output), cwd=tmp_path
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["counts"] == {"artefacts": 1, "missing": 0}
    assert data["missing"] == []
    assert len(data["date"]) == 10
