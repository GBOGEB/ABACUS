"""Behaviour tests for scripts/preview_diff.py."""

import hashlib
import json
import sys
from pathlib import Path

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("scripts/preview_diff.py", name="abn_preview_diff")


def _index(tmp_path, artefacts):
    idx = tmp_path / "index.json"
    idx.write_text(json.dumps({"artefacts": artefacts}), encoding="utf-8")
    return idx


def _run(monkeypatch, idx, *extra):
    monkeypatch.setattr(sys, "argv", ["prog", "--index", str(idx), *extra])
    with pytest.raises(SystemExit) as exc:
        mod.main()
    return exc.value.code


def test_sha256_file_and_load_index(tmp_path):
    f = tmp_path / "f.bin"
    f.write_bytes(b"abc")
    assert mod.sha256_file(f) == hashlib.sha256(b"abc").hexdigest()
    idx = _index(tmp_path, [{"path": "p"}])
    assert mod.load_index(idx) == {"artefacts": [{"path": "p"}]}


def test_main_exit_zero_when_all_match(tmp_path, monkeypatch, capsys):
    f = tmp_path / "ok.txt"
    f.write_bytes(b"ok")
    idx = _index(
        tmp_path,
        [
            {"path": str(f), "hash": hashlib.sha256(b"ok").hexdigest()},
            {"path": str(tmp_path / "missing.txt"), "hash": "x"},
            {"path": str(f), "hash": ""},
        ],
    )
    assert _run(monkeypatch, idx, "--mode", "in") == 0
    out = capsys.readouterr().out
    assert "[WARN] missing" in out
    assert "[INFO] no recorded hash" in out
    assert "[DIFF]" not in out


def test_main_exit_one_on_changed_text(tmp_path, monkeypatch, capsys):
    f = tmp_path / "t.txt"
    f.write_bytes(b"changed")
    idx = _index(tmp_path, [{"path": str(f), "hash": "deadbeef"}])
    assert _run(monkeypatch, idx) == 1
    out = capsys.readouterr().out
    assert "[DIFF]" in out
    assert "t.txt" in out
    assert "run hash_update after review" in out


def test_main_reports_unreadable_content(tmp_path, monkeypatch, capsys):
    f = tmp_path / "b.bin"
    f.write_bytes(b"\x00\x01")
    idx = _index(tmp_path, [{"path": str(f), "hash": "deadbeef"}])

    def unreadable(self, *args, **kwargs):
        raise OSError("unreadable")

    monkeypatch.setattr(mod, "load_index", lambda p: json.loads(p.read_bytes()))
    monkeypatch.setattr(Path, "read_text", unreadable)
    assert _run(monkeypatch, idx, "--mode", "out") == 1
    assert "(binary or unreadable content changed)" in capsys.readouterr().out


def test_main_rejects_invalid_mode(tmp_path, monkeypatch, capsys):
    idx = _index(tmp_path, [])
    assert _run(monkeypatch, idx, "--mode", "sideways") == 2
    assert "invalid choice" in capsys.readouterr().err
