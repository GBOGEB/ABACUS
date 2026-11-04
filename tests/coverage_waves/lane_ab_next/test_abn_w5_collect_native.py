"""Behaviour tests for tools/everred_v3/scripts/collect_native.py.

The real ``everred`` ledger imports ``fcntl`` (Unix-only) and ``native_ingest``
talks to the GitHub API, so both are replaced by in-memory stubs that exist
only while the script is imported. The script's sys.path insertion is undone.
"""

import json
import sys
import types

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

SHA = "e" * 40


def _make_everred():
    stub = types.ModuleType("everred")
    stub.batches = []

    def append_events_batch(path, events):
        stub.batches.append((path, list(events)))
        return len(events)

    stub.append_events_batch = append_events_batch
    return stub


def _make_native():
    stub = types.ModuleType("native_ingest")
    stub.calls = []

    class GitHubReadOnly:
        pass

    def collect_native(repo, sha, run_id, plan, reader):
        stub.calls.append((repo, sha, run_id, plan, reader))
        return [dict(id="NAT-" + str(n), sha=sha) for n in range(len(plan) + 1)]

    stub.GitHubReadOnly = GitHubReadOnly
    stub.collect_native = collect_native
    return stub


EVERRED = _make_everred()
NATIVE = _make_native()
_saved_path = list(sys.path)
mod = load(
    "tools/everred_v3/scripts/collect_native.py",
    name="abn_w5_collect_native",
    deps={"everred": EVERRED, "native_ingest": NATIVE},
)
sys.path[:] = _saved_path


@pytest.fixture(autouse=True)
def _reset_stubs():
    EVERRED.batches.clear()
    NATIVE.calls.clear()


def _run(monkeypatch, *args):
    argv = ["collect_native", "--repo", "GBOGEB/ABACUS", "--sha", SHA]
    monkeypatch.setattr(sys, "argv", argv + list(args))
    mod.main()


def test_dry_run_writes_batch_without_ledger(tmp_path, monkeypatch, capsys):
    out = tmp_path / "nested" / "batch.json"
    _run(monkeypatch, "--run-id", "42", "--output", str(out))
    doc = json.loads(out.read_text())
    assert doc == {
        "schema": "abacus.everred.native.batch.v1",
        "events": [dict(id="NAT-0", sha=SHA)],
    }
    repo, sha, run_id, plan, reader = NATIVE.calls[0]
    assert (repo, sha, run_id, plan) == ("GBOGEB/ABACUS", SHA, 42, [])
    assert isinstance(reader, NATIVE.GitHubReadOnly)
    assert EVERRED.batches == []
    assert capsys.readouterr().out.strip() == (
        "Collected 1 events at " + SHA + ": DRY_RUN_ONLY"
    )


def test_artifact_plan_and_apply_ledger(tmp_path, monkeypatch, capsys):
    plan = [{"job": "a"}, {"job": "b"}]
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))
    out = tmp_path / "batch.json"
    ledger = tmp_path / "ledger.jsonl"
    _run(
        monkeypatch,
        "--run-id",
        "7",
        "--artifact-plan",
        str(plan_path),
        "--output",
        str(out),
        "--apply-ledger",
        "--ledger",
        str(ledger),
    )
    assert NATIVE.calls[0][3] == plan
    events = json.loads(out.read_text())["events"]
    assert len(events) == 3
    assert EVERRED.batches == [(ledger, events)]
    assert capsys.readouterr().out.strip().endswith(": LEDGER_APPLIED")


def test_run_id_must_be_integer(tmp_path, monkeypatch, capsys):
    with pytest.raises(SystemExit) as info:
        _run(monkeypatch, "--run-id", "abc", "--output", str(tmp_path / "o.json"))
    assert info.value.code == 2
    assert "invalid int value" in capsys.readouterr().err
    assert NATIVE.calls == []
