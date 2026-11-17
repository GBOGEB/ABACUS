"""Behaviour tests for scripts/archive_handover.py.

``ROOT`` and ``OUT_DIR`` are redirected into ``tmp_path`` so every archive is
built under the test's temporary directory.
"""

import json
import sys
import tarfile
from zipfile import ZipFile

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("scripts/archive_handover.py", name="abn_archive_handover")


@pytest.fixture
def root(tmp_path, monkeypatch):
    base = tmp_path / "repo"
    (base / "docs" / "sub").mkdir(parents=True)
    (base / "docs" / "a.md").write_bytes(b"alpha\n")
    (base / "docs" / "sub" / "b.md").write_bytes(b"beta\n")
    (base / "docs" / "skip.log").write_bytes(b"log\n")
    monkeypatch.setattr(mod, "ROOT", base)
    monkeypatch.setattr(mod, "OUT_DIR", base / "handover")
    return base


def _rel(files, base):
    return sorted(f.relative_to(base).as_posix() for f in files)


def test_expand_globs_returns_sorted_unique_files_only(root):
    files = mod.expand_globs(["docs/**/*", "docs/*.md", "nothing/*.x"])
    assert _rel(files, root) == ["docs/a.md", "docs/skip.log", "docs/sub/b.md"]


def test_expand_exclusions_drops_matching_files(root):
    files = mod.expand_globs(["docs/**/*"])
    kept = mod.expand_exclusions(files, ["docs/*.log"])
    assert _rel(kept, root) == ["docs/a.md", "docs/sub/b.md"]


def test_load_spec_applies_include_and_exclude(root, tmp_path):
    spec = tmp_path / "GLOOB.yaml"
    spec.write_text(
        "bundle:\n  include:\n    - docs/**/*\n  exclude:\n    - docs/sub/*\n",
        encoding="utf-8",
    )
    assert _rel(mod.load_spec(spec), root) == ["docs/a.md", "docs/skip.log"]


def test_load_spec_handles_missing_bundle_and_null_lists(root, tmp_path):
    empty = tmp_path / "empty.yaml"
    empty.write_text("other: 1\n", encoding="utf-8")
    assert mod.load_spec(empty) == []
    nulls = tmp_path / "nulls.yaml"
    nulls.write_text("bundle:\n  include:\n  exclude:\n", encoding="utf-8")
    assert mod.load_spec(nulls) == []


def test_load_copy_list_ignores_blank_and_comment_lines(root, tmp_path):
    copy = tmp_path / "COPY_GLOBS.txt"
    copy.write_text("# comment\n\n   docs/*.md  \n", encoding="utf-8")
    assert _rel(mod.load_copy_list(copy), root) == ["docs/a.md"]


def test_write_zip_and_targz_store_repo_relative_names(root, tmp_path):
    files = mod.expand_globs(["docs/**/*.md"])
    zip_path = tmp_path / "out" / "x.zip"
    tgz_path = tmp_path / "out2" / "x.tar.gz"
    mod.write_zip(files, zip_path)
    mod.write_targz(files, tgz_path)
    with ZipFile(zip_path) as zf:
        assert sorted(zf.namelist()) == ["docs/a.md", "docs/sub/b.md"]
        assert zf.read("docs/a.md") == b"alpha\n"
    with tarfile.open(tgz_path, "r:gz") as tf:
        names = sorted(n.replace("\\", "/") for n in tf.getnames())
    assert names == ["docs/a.md", "docs/sub/b.md"]


def test_main_with_spec_builds_both_archives(root, tmp_path, monkeypatch, capsys):
    spec = tmp_path / "spec.yaml"
    spec.write_text("bundle:\n  include:\n    - docs/*.md\n", encoding="utf-8")
    argv = ["prog", "--spec", str(spec), "--copy", str(tmp_path / "no.txt")]
    monkeypatch.setattr(sys, "argv", argv + ["--name", "BUNDLE"])
    assert mod.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 1
    assert payload["root"] == str(root)
    assert payload["zip"] == str(root / "handover" / "BUNDLE.zip")
    assert (root / "handover" / "BUNDLE.zip").is_file()
    assert (root / "handover" / "BUNDLE.tar.gz").is_file()


def test_main_falls_back_to_copy_list_with_default_name(
    root, tmp_path, monkeypatch, capsys
):
    copy = tmp_path / "copy.txt"
    copy.write_text("docs/sub/*.md\n", encoding="utf-8")
    argv = ["prog", "--spec", str(tmp_path / "none.yaml"), "--copy", str(copy)]
    monkeypatch.setattr(sys, "argv", argv)
    assert mod.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 1
    assert payload["tar_gz"].endswith("DMAIC_V3_3_HANDOVER_ALL.tar.gz")


def test_main_default_paths_missing_returns_2(root, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["prog"])
    assert mod.main() == 2
    out = capsys.readouterr().out
    assert "No spec or copy list found" in out
    assert "GLOOB.yaml" in out
    assert "COPY_GLOBS.txt" in out


def test_main_no_matches_returns_1(root, tmp_path, monkeypatch, capsys):
    copy = tmp_path / "copy.txt"
    copy.write_text("missing/*.zzz\n", encoding="utf-8")
    argv = ["prog", "--spec", str(tmp_path / "none.yaml"), "--copy", str(copy)]
    monkeypatch.setattr(sys, "argv", argv)
    assert mod.main() == 1
    assert "nothing to archive" in capsys.readouterr().out
    assert not (root / "handover").exists()
