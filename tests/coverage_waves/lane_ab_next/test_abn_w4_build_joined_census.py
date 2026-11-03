"""Behaviour tests for tools/everred_v3/scripts/build_joined_census.py.

The script does all its work at import time and writes next to itself, so it
is executed inside each test with ``everred``/``joined_census`` stubs and
``Path.write_text`` redirected to an in-memory capture (no repo writes).
"""

import json
import pathlib
import sys
import types

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

REL = "tools/everred_v3/scripts/build_joined_census.py"
NAME = "abn_build_joined_census"


def _stubs(events, join_impl=None):
    everred = types.ModuleType("everred")
    everred.read_calls = []

    def read_ledger(path):
        everred.read_calls.append(path)
        return events

    everred.read_ledger = read_ledger
    joined = types.ModuleType("joined_census")

    def join(evts):
        return dict(run_group_count=len(evts), groups=[e["id"] for e in evts])

    joined.join = join_impl or join
    return everred, joined


def _run(monkeypatch, events, join_impl=None):
    writes = []

    def fake_write_text(self, data, *args, **kwargs):
        writes.append((self, data))
        return len(data)

    monkeypatch.setattr(pathlib.Path, "write_text", fake_write_text)
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setitem(sys.modules, NAME, types.ModuleType(NAME))
    everred, joined = _stubs(events, join_impl)
    mod = load(REL, name=NAME, deps={"everred": everred, "joined_census": joined})
    return mod, everred, writes


def test_builds_and_writes_joined_native(monkeypatch, capsys):
    events = [dict(id="E1"), dict(id="E2"), dict(id="E3")]
    mod, everred, writes = _run(monkeypatch, events)
    root = REPO_ROOT / "tools" / "everred_v3"
    assert mod.P == root
    assert everred.read_calls == [root / "data" / "ledger.jsonl"]
    assert len(writes) == 1
    target, data = writes[0]
    assert target == root / "data" / "joined_native.json"
    assert data.endswith("}\n")
    assert json.loads(data) == dict(run_group_count=3, groups=["E1", "E2", "E3"])
    assert data.index('"groups"') < data.index('"run_group_count"')
    assert capsys.readouterr().out.strip() == "Joined run groups: 3"
    assert mod.result["run_group_count"] == 3


def test_empty_ledger(monkeypatch, capsys):
    _, _, writes = _run(monkeypatch, [])
    assert json.loads(writes[0][1])["run_group_count"] == 0
    assert "Joined run groups: 0" in capsys.readouterr().out


def test_join_failure_writes_nothing(monkeypatch, capsys):
    def boom(events):
        raise ValueError("invalid ledger")

    with pytest.raises(ValueError, match="invalid ledger"):
        _run(monkeypatch, [dict(id="E1")], join_impl=boom)
    assert capsys.readouterr().out == ""
