"""Behaviour tests for scripts/hash_update.py."""

import hashlib
import json
import sys

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("scripts/hash_update.py", name="abn_hash_update")


def _index(tmp_path, artefacts):
    idx = tmp_path / "index.json"
    idx.write_text(json.dumps({"artefacts": artefacts}), encoding="utf-8")
    return idx


def test_sha256_file_matches_hashlib(tmp_path):
    f = tmp_path / "x.bin"
    f.write_bytes(b"payload")
    assert mod.sha256_file(f) == hashlib.sha256(b"payload").hexdigest()


def test_main_updates_stale_hash_and_warns_missing(tmp_path, monkeypatch, capsys):
    good = tmp_path / "good.txt"
    good.write_bytes(b"good")
    stale = tmp_path / "stale.txt"
    stale.write_bytes(b"new content")
    good_hash = hashlib.sha256(b"good").hexdigest()
    new_hash = hashlib.sha256(b"new content").hexdigest()
    idx = _index(
        tmp_path,
        [
            {"path": str(good), "hash": good_hash},
            {"path": str(stale), "hash": "old"},
            {"path": str(tmp_path / "gone.txt")},
        ],
    )
    monkeypatch.setattr(sys, "argv", ["prog", "--index", str(idx)])
    mod.main()
    out = capsys.readouterr().out
    assert "[WARN] missing" in out
    assert "gone.txt" in out
    assert "[UPDATE]" in out
    assert new_hash[:12] in out
    assert "[WROTE]" in out
    data = json.loads(idx.read_text(encoding="utf-8"))
    hashes = [a.get("hash") for a in data["artefacts"]]
    assert hashes == [good_hash, new_hash, None]


def test_main_reports_ok_when_hashes_current(tmp_path, monkeypatch, capsys):
    f = tmp_path / "a.txt"
    f.write_bytes(b"a")
    digest = hashlib.sha256(b"a").hexdigest()
    idx = _index(tmp_path, [{"path": str(f), "hash": digest}])
    before = idx.read_bytes()
    monkeypatch.setattr(sys, "argv", ["prog", "--index", str(idx)])
    mod.main()
    assert "[OK] hashes up to date" in capsys.readouterr().out
    assert idx.read_bytes() == before


def test_main_index_without_artefacts_is_ok(tmp_path, monkeypatch, capsys):
    idx = tmp_path / "index.json"
    idx.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["prog", "--index", str(idx)])
    mod.main()
    assert "[OK]" in capsys.readouterr().out
