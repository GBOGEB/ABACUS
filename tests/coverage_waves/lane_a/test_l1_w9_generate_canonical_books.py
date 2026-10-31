"""Tests for ABACUS-v032/generate_canonical_books.py (stub book generator)."""

import os
import runpy

import pytest

from tests.coverage_waves.lane_a._load import REPO, load

REL = "ABACUS-v032/generate_canonical_books.py"
mod = load(REL, name="l1_w9_generate_canonical_books")


def test_output_dir_is_next_to_script():
    expected = (REPO / "ABACUS-v032" / "output" / "books").resolve()
    assert os.path.realpath(mod.OUTPUT_DIR) == os.path.realpath(str(expected))


def test_main_creates_output_dir(tmp_path, monkeypatch, capsys):
    target = tmp_path / "out" / "books"
    monkeypatch.setattr(mod, "OUTPUT_DIR", str(target))
    assert mod.main() == 0
    assert target.is_dir()
    assert mod.main() == 0  # idempotent
    assert "[OK] Canonical books generated" in capsys.readouterr().out


def test_dunder_main_exits_zero(monkeypatch):
    made = []
    monkeypatch.setattr("os.makedirs", lambda path, exist_ok=False: made.append(path))
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(REPO / REL), run_name="__main__")
    assert exc.value.code == 0
    assert len(made) == 1 and made[0].endswith("books")
