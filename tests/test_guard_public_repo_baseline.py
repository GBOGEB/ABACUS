"""Tests for the hash-pinned baseline in scripts/guard_public_repo.py (U16, #2505)."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "guard_public_repo",
    Path(__file__).resolve().parents[1] / "scripts" / "guard_public_repo.py",
)
guard = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(guard)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    img = tmp_path / "docs" / "old.png"
    img.parent.mkdir(parents=True)
    img.write_bytes(b"\x89PNG original")
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps(
            {"files": {"docs/old.png": hashlib.sha256(img.read_bytes()).hexdigest()}}
        )
    )
    monkeypatch.setattr(guard, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(guard, "BASELINE_PATH", baseline)
    monkeypatch.setattr(guard.load_baseline, "__defaults__", (baseline,))
    monkeypatch.setattr(guard.is_baselined, "__defaults__", (tmp_path,))
    return tmp_path


def test_baselined_file_passes(repo):
    assert guard.main(["guard", "docs/old.png"]) == 0


def test_new_binary_blocked(repo, capsys):
    (repo / "docs" / "new.png").write_bytes(b"new")
    assert guard.main(["guard", "docs/old.png", "docs/new.png"]) == 1
    err = capsys.readouterr().err
    assert "binary artifacts are not allowed" in err
    assert "docs/new.png" in err and "docs/old.png" not in err


def test_modified_baselined_file_blocked(repo):
    (repo / "docs" / "old.png").write_bytes(b"\x89PNG tampered")
    assert guard.main(["guard", "docs/old.png"]) == 1


def test_missing_baseline_fails_closed(repo):
    (repo / "baseline.json").unlink()
    assert guard.main(["guard", "docs/old.png"]) == 1


def test_non_binary_unaffected(repo):
    assert guard.main(["guard", "README.md"]) == 0


def test_committed_baseline_covers_tree():
    baseline = guard.load_baseline()
    assert len(baseline) >= 1
    for path in baseline:
        assert guard.is_baselined(path, baseline), path
