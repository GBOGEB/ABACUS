"""Behaviour tests for tools/everred_v3/scripts/seed.py.

seed.py does all its work at import: it deletes the repository ledger file and
appends historical events through ``everred.append_event``. The real
``everred`` imports ``fcntl`` (Unix-only), so it is stubbed in memory, and
``Path.exists``/``Path.unlink`` are patched for the ledger path only during the
import so the repository file is never touched. sys.path is restored.
"""

import contextlib
import io
import pathlib
import sys
import types

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

REL = "tools/everred_v3/scripts/seed.py"
SHA = "e9f34b22967064c779891a4d2ac40541f370e812"


def _make_everred():
    stub = types.ModuleType("everred")
    stub.events = []

    def append_event(path, event):
        stub.events.append((path, event))

    stub.append_event = append_event
    return stub


def _load_seed(name, ledger_exists):
    stub = _make_everred()
    removed = []
    real_exists = pathlib.Path.exists
    real_unlink = pathlib.Path.unlink

    def fake_exists(self, *args, **kwargs):
        if self.name == "ledger.jsonl":
            return ledger_exists
        return real_exists(self, *args, **kwargs)

    def fake_unlink(self, *args, **kwargs):
        if self.name == "ledger.jsonl":
            removed.append(self)
            return None
        return real_unlink(self, *args, **kwargs)

    saved_path = list(sys.path)
    buffer = io.StringIO()
    try:
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(pathlib.Path, "exists", fake_exists)
            patch.setattr(pathlib.Path, "unlink", fake_unlink)
            with contextlib.redirect_stdout(buffer):
                module = load(REL, name=name, deps={"everred": stub})
    finally:
        sys.path[:] = saved_path
    return module, stub, removed, buffer.getvalue()


mod, STUB, REMOVED, OUTPUT = _load_seed("abn_w5_seed", ledger_exists=True)


def test_existing_ledger_is_removed_before_seeding():
    assert REMOVED == [mod.path]
    assert mod.path.name == "ledger.jsonl"
    assert mod.path.parent.name == "data"
    assert mod.path.parent.parent == mod.P


def test_seeds_fourteen_sequential_historical_events():
    events = [event for _, event in STUB.events]
    assert len(events) == 14
    assert mod.i == 14
    assert [e["id"] for e in events] == [
        "HIST-1914-" + str(n).zfill(3) for n in range(1, 15)
    ]
    assert all(path == mod.path for path, _ in STUB.events)
    for event in events:
        assert event["schema"] == "abacus.everred.event.v3"
        assert event["repo"] == "GBOGEB/ABACUS"
        assert event["provenance"] == "historical_source"
        assert event["occurred_at"] == "2026-10-14T08:04:49Z"
    kinds = [e["kind"] for e in events]
    assert kinds.count("verification") == 3
    assert kinds.count("coverage") == 3
    assert kinds.count("security_census") == 3
    assert kinds.count("root_candidate") == 2
    assert kinds[-1] == "admission"
    assert events[-1]["evidence"]["decision"] == "HOLD"


def test_root_candidates_carry_root_id_not_sha():
    events = [event for _, event in STUB.events]
    roots = [e for e in events if e["kind"] == "root_candidate"]
    assert [r["root_id"] for r in roots] == [
        "CANDIDATE-DMAIC-1914",
        "CANDIDATE-SAFETY-1914",
    ]
    assert all("sha" not in r for r in roots)
    others = [e for e in events if e["kind"] != "root_candidate"]
    assert all(e["sha"] == SHA for e in others)


def test_prints_summary():
    assert OUTPUT.strip().startswith("seeded 14 historical events to ")
    assert OUTPUT.strip().endswith("ledger.jsonl")


def test_missing_ledger_is_not_removed():
    module, stub, removed, output = _load_seed("abn_w5_seed_fresh", False)
    assert removed == []
    assert len(stub.events) == 14
    assert module.i == 14
    assert "seeded 14" in output


def test_add_increments_counter_and_passes_extra_fields(monkeypatch):
    captured = []
    monkeypatch.setattr(mod, "i", 41)
    monkeypatch.setattr(mod, "append_event", lambda p, e: captured.append((p, e)))
    mod.add("occurrence", {"test": "t"}, sha="f" * 40, note="x")
    assert mod.i == 42
    path, event = captured[0]
    assert path == mod.path
    assert event["id"] == "HIST-1914-042"
    assert event["kind"] == "occurrence"
    assert event["evidence"] == {"test": "t"}
    assert event["sha"] == "f" * 40
    assert event["note"] == "x"
