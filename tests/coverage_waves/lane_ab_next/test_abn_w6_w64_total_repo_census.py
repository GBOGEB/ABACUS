"""Gap tests for tools/w64_total_repo_census.py.

``subprocess.run`` is replaced by fakes, so no git process is spawned and the
scanner only walks a tiny ``tmp_path`` tree, never the real repository.
"""

import json
from pathlib import Path

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("tools/w64_total_repo_census.py", name="abn_w6_w64_total_repo_census")


class _Result:
    def __init__(self, stdout):
        self.stdout = stdout


def _tree(tmp_path):
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / ".git").mkdir()
    (root / "src" / "a.py").write_bytes(b"print(1)\n")
    (root / "src" / "a_copy.py").write_bytes(b"print(2)\n")
    (root / "archive").mkdir()
    (root / "archive" / "a.md").write_bytes(b"old\n")
    (root / ".git" / "HEAD").write_bytes(b"ref\n")
    return root


def _fail_with(exc):
    def fake(*args, **kwargs):
        raise exc

    return fake


def test_tracked_files_uses_git_ls_files_output(monkeypatch, tmp_path):
    calls = []

    def fake(cmd, **kwargs):
        calls.append((cmd, kwargs["cwd"]))
        return _Result("src/a.py\n\n  \ndocs/b.md\n")

    monkeypatch.setattr(mod.subprocess, "run", fake)
    assert mod.tracked_files(tmp_path) == [Path("src/a.py"), Path("docs/b.md")]
    assert calls == [(["git", "ls-files"], tmp_path)]


def test_tracked_files_falls_back_to_walk_on_oserror(monkeypatch, tmp_path):
    root = _tree(tmp_path)
    monkeypatch.setattr(mod.subprocess, "run", _fail_with(OSError("no git")))
    files = [p.as_posix() for p in mod.tracked_files(root)]
    assert files == ["archive/a.md", "src/a.py", "src/a_copy.py"]


def test_tracked_files_falls_back_on_called_process_error(monkeypatch, tmp_path):
    root = _tree(tmp_path)
    err = mod.subprocess.CalledProcessError(128, ["git", "ls-files"])
    monkeypatch.setattr(mod.subprocess, "run", _fail_with(err))
    assert len(mod.tracked_files(root)) == 3


def test_sha256_file_reads_in_chunks(tmp_path):
    target = tmp_path / "f.bin"
    target.write_bytes(b"abc")
    assert mod.sha256_file(target) == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_category_for_source_schema_doc_and_other():
    assert mod.category_for(Path("x/run.SH")) == "source_or_script"
    assert mod.category_for(Path("x/conf.toml")) == "schema_or_config"
    assert mod.category_for(Path("x/readme.rst")) == "documentation"
    assert mod.category_for(Path("x/blob.dat")) == "other"
    assert mod.category_for(Path("deep/ssot/x.dat")) == "ssot"


def test_build_census_marks_duplicates_and_missing_files(monkeypatch, tmp_path):
    root = _tree(tmp_path)
    listing = "src/a.py\nsrc/a_copy.py\narchive/a.md\nbuild/a.json\nghost.py\n"
    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: _Result(listing))
    census = mod.build_census(root)
    assert census["asset_count"] == 5
    by_path = {asset["path"]: asset for asset in census["assets"]}
    assert by_path["src/a.py"]["duplicate_family_candidate"] == "a"
    assert by_path["src/a_copy.py"]["duplicate_family_candidate"] == "a"
    assert "duplicate_family_candidate" not in by_path["archive/a.md"]
    assert "duplicate_family_candidate" not in by_path["build/a.json"]
    assert "duplicate_family_candidate" not in by_path["ghost.py"]
    assert by_path["archive/a.md"]["classification"] == "dormant"
    assert by_path["build/a.json"]["classification"] == "generated"
    assert by_path["build/a.json"]["sha256"] is None
    assert by_path["ghost.py"]["sha256"] is None
    assert len(by_path["src/a.py"]["sha256"]) == 64
    assert census["duplicate_family_candidates"] == ["a"]
    assert census["duplicate_family_candidate_count"] == 1
    assert census["by_category"]["source_or_script"] == 3
    assert census["by_classification"]["active_candidate"] == 3


def test_main_relative_out_resolves_under_root(monkeypatch, tmp_path, capsys):
    root = _tree(tmp_path)
    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: _Result("src/a.py\n"))
    rc = mod.main(["--root", str(root), "--out", "receipts/census.json"])
    assert rc == 0
    out = root.resolve() / "receipts" / "census.json"
    printed = json.loads(capsys.readouterr().out)
    assert printed == {"asset_count": 1, "out": str(out)}
    assert json.loads(out.read_text(encoding="utf-8"))["asset_count"] == 1


def test_main_absolute_out_is_used_verbatim(monkeypatch, tmp_path, capsys):
    root = _tree(tmp_path)
    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: _Result(""))
    out = tmp_path / "elsewhere" / "c.json"
    assert mod.main(["--root", str(root), "--out", str(out)]) == 0
    assert json.loads(capsys.readouterr().out)["out"] == str(out)
    assert json.loads(out.read_text(encoding="utf-8"))["assets"] == []
