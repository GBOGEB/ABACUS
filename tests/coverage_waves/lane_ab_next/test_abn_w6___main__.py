"""Behaviour tests for src/qplant_presentation_engine/__main__.py."""

import runpy
import sys

import pytest

from src.qplant_presentation_engine import __main__ as entry
from src.qplant_presentation_engine import main as main_mod


def test_entry_reexports_main():
    assert entry.main is main_mod.main


def test_run_as_main_raises_system_exit_with_main_code(monkeypatch):
    monkeypatch.setattr(main_mod, "main", lambda: 7)
    # Execute a fresh copy as __main__; the cached module is restored afterwards.
    monkeypatch.delitem(sys.modules, entry.__name__, raising=False)
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("src.qplant_presentation_engine.__main__", run_name="__main__")
    assert exc.value.code == 7
