"""Tests for ABACUS-v032/execute_full_dmaic_phases_0_to_8.py, a CI entrypoint that re-exports v033 main.

The real v033 module is replaced by a stub in sys.modules so nothing runs the
full DMAIC loop or rewraps sys.stdout.
"""

import runpy
import sys
import types

import pytest

from tests.coverage_waves.lane_a._load import REPO, load

REL = "ABACUS-v032/execute_full_dmaic_phases_0_to_8.py"
TARGET = "execute_full_dmaic_phases_0_to_9_v033"


@pytest.fixture
def stub_main(monkeypatch):
    fake = types.ModuleType(TARGET)
    calls = []

    def main():
        calls.append(1)
        return 7

    fake.main = main
    monkeypatch.setitem(sys.modules, TARGET, fake)
    return fake, calls


def test_reexports_v033_main(stub_main):
    fake, calls = stub_main
    mod = load(REL, name="l1_w9_execute_full_dmaic_phases_0_to_8")
    assert mod.main is fake.main
    assert calls == []


def test_dunder_main_exits_with_v033_status(stub_main):
    fake, calls = stub_main
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(REPO / REL), run_name="__main__")
    assert exc.value.code == 7
    assert calls == [1]
