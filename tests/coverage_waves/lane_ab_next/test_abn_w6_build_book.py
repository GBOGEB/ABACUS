"""Behaviour tests for scripts/build_book.py main() (pandoc mocked)."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("scripts/build_book.py", name="abn_w6_build_book")


def _sources(root):
    for name in mod.BOOK_SOURCES:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"# s\n")


def _fake_pandoc(monkeypatch, fail_formats=()):
    calls = []

    def fake_run(cmd, capture_output=False, text=False):
        out = next(a for a in cmd if a.startswith("--output=")).split("=", 1)[1]
        fmt = next(a for a in cmd if a.startswith("--to=")).split("=", 1)[1]
        calls.append(fmt)
        if fmt in fail_formats:
            return SimpleNamespace(returncode=1, stderr="boom " + fmt)
        Path(out).write_bytes(b"artifact")
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    return calls


def test_main_missing_sources_exits_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "DMAIC V3 Book Builder v" + mod.__version__ in out
    assert "Missing source files" in out
    assert (tmp_path / "build").is_dir()


def test_main_all_builds_succeed(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _sources(tmp_path)
    calls = _fake_pandoc(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 0
    assert calls == ["pdf", "html5", "epub3"]
    out = capsys.readouterr().out
    assert "All builds complete!" in out
    assert "build/DMAIC_V3_BOOK.epub" in out
    assert out.count("SUCCESS") == 3


def test_main_some_builds_fail(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _sources(tmp_path)
    _fake_pandoc(monkeypatch, fail_formats=("html5",))
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "boom html5" in out
    assert "Some builds failed" in out
    assert "HTML       ❌ FAILED" in out
    assert "PDF        ✅ SUCCESS" in out
