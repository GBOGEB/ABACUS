"""Behaviour tests for scripts/emit_keb_runtime_status.py.

The wrapper imports its sibling ``emit_execution_backbone_runtime_status`` by
bare name; that sibling needs ``core.execution_backbone``, so a stub sibling is
supplied instead of running a real backbone pulse.
"""

import runpy
import sys
import types

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

SIBLING = "emit_execution_backbone_runtime_status"


def _make_sibling(exit_code=0):
    stub = types.ModuleType(SIBLING)
    calls = []

    def build(timeout_seconds=5.0):
        calls.append(timeout_seconds)
        return {"status": "ok", "timeout": timeout_seconds}

    def main():
        calls.append("main")
        return exit_code

    stub.build_execution_backbone_runtime_status = build
    stub.main = main
    stub.calls = calls
    return stub


_SIBLING_STUB = _make_sibling()
mod = load(
    "scripts/emit_keb_runtime_status.py",
    name="abn_w4_emit_keb_runtime_status",
    deps={SIBLING: _SIBLING_STUB},
)


def test_reexports_sibling_functions():
    assert mod.main is _SIBLING_STUB.main
    assert (
        mod.build_execution_backbone_runtime_status
        is _SIBLING_STUB.build_execution_backbone_runtime_status
    )


def test_keb_alias_delegates_to_backbone_builder():
    assert mod.build_keb_runtime_status is mod.build_execution_backbone_runtime_status
    out = mod.build_keb_runtime_status(timeout_seconds=0.5)
    assert out == {"status": "ok", "timeout": 0.5}
    assert 0.5 in _SIBLING_STUB.calls


def test_bare_sibling_name_does_not_leak():
    assert sys.modules.get(SIBLING) is not _SIBLING_STUB


def test_dunder_main_raises_systemexit_with_main_return(monkeypatch):
    stub = _make_sibling(exit_code=3)
    monkeypatch.setitem(sys.modules, SIBLING, stub)
    path = str(REPO_ROOT / "scripts" / "emit_keb_runtime_status.py")
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(path, run_name="__main__")
    assert exc.value.code == 3
    assert stub.calls == ["main"]
