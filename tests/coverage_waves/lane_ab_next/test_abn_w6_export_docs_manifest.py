"""Behaviour tests for scripts/export_docs_manifest.py (git mocked)."""

import json
from types import SimpleNamespace

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("scripts/export_docs_manifest.py", name="abn_w6_export_docs_manifest")


def _fake_git(monkeypatch, raw, calls=None):
    def fake_run(cmd, cwd=None, capture_output=False, check=False):
        if calls is not None:
            calls.append((cmd, cwd))
        return SimpleNamespace(stdout=raw, returncode=0)

    monkeypatch.setattr(mod.subprocess, "run", fake_run)


def _make(repo, *rels):
    for rel in rels:
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"# x\n")


def test_tracked_markdown_sorted_filters_non_md(tmp_path, monkeypatch):
    _make(tmp_path, "docs/b/z.md", "docs/a.md")
    calls = []
    _fake_git(monkeypatch, b"docs/b/z.md\0docs/img.png\0docs/a.md\0", calls)
    assert mod.tracked_markdown(tmp_path) == ["docs/a.md", "docs/b/z.md"]
    assert calls[0][0][:3] == ["git", "ls-files", "-z"]
    assert calls[0][1] == tmp_path


def test_truncated_manifest_rejected(tmp_path, monkeypatch):
    _fake_git(monkeypatch, b"docs/a.md")
    with pytest.raises(ValueError, match="TRUNCATED_NUL_GIT_MANIFEST"):
        mod.tracked_markdown(tmp_path)


def test_empty_manifest_rejected(tmp_path, monkeypatch):
    _fake_git(monkeypatch, b"")
    with pytest.raises(ValueError, match="NO_TRACKED_MARKDOWN_SOURCES"):
        mod.tracked_markdown(tmp_path)


def test_only_non_markdown_rejected(tmp_path, monkeypatch):
    _fake_git(monkeypatch, b"docs/a.txt\0\0")
    with pytest.raises(ValueError, match="NO_TRACKED_MARKDOWN_SOURCES"):
        mod.tracked_markdown(tmp_path)


@pytest.mark.parametrize(
    "raw",
    [b"top.md\0", b"other/a.md\0", b"docs/../a.md\0"],
)
def test_unsafe_paths_rejected(tmp_path, monkeypatch, raw):
    _fake_git(monkeypatch, raw)
    with pytest.raises(ValueError, match="UNSAFE_TRACKED_SOURCE_PATH"):
        mod.tracked_markdown(tmp_path)


def test_missing_source_rejected(tmp_path, monkeypatch):
    _fake_git(monkeypatch, b"docs/ghost.md\0")
    with pytest.raises(ValueError, match="MISSING_OR_SYMLINKED_SOURCE"):
        mod.tracked_markdown(tmp_path)


def test_directory_source_rejected(tmp_path, monkeypatch):
    (tmp_path / "docs" / "dir.md").mkdir(parents=True)
    _fake_git(monkeypatch, b"docs/dir.md\0")
    with pytest.raises(ValueError, match="MISSING_OR_SYMLINKED_SOURCE"):
        mod.tracked_markdown(tmp_path)


def test_casefold_collision_rejected(tmp_path, monkeypatch):
    _make(tmp_path, "docs/Readme.md")
    monkeypatch.setattr(mod.Path, "is_file", lambda self: True)
    _fake_git(monkeypatch, b"docs/Readme.md\0docs/README.md\0")
    with pytest.raises(ValueError, match="OUTPUT_PATH_COLLISION"):
        mod.tracked_markdown(tmp_path)


def test_write_manifest_and_main(tmp_path, monkeypatch, capsys):
    _make(tmp_path, "docs/a.md", "docs/sub/b.md")
    _fake_git(monkeypatch, b"docs/sub/b.md\0docs/a.md\0")
    out = tmp_path / "nested" / "manifest.bin"
    rc = mod.main(["--repo", str(tmp_path), "--out", str(out)])
    assert rc == 0
    assert out.read_bytes() == b"docs/a.md\0docs/sub/b.md\0"
    report = json.loads(capsys.readouterr().out)
    assert report["tracked_markdown_count"] == 2
    assert report["expected_artifact_count"] == 4
    assert report["path_encoding"] == "UTF8_NUL"
    assert report["formal_publication_credit"] == 0
