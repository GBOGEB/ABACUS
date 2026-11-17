"""Tests for ABACUS-v032/update_documentation_versions.py (stub updater)."""

import runpy

import pytest

from tests.coverage_waves.lane_a._load import REPO, load

REL = "ABACUS-v032/update_documentation_versions.py"
mod = load(REL, name="l1_w9_update_documentation_versions")


def test_main_reports_success(capsys):
    assert mod.main() == 0
    assert capsys.readouterr().out == "[OK] Documentation versions updated\n"


def test_dunder_main_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(REPO / REL), run_name="__main__")
    assert exc.value.code == 0
    assert "updated" in capsys.readouterr().out
