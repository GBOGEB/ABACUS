"""Behaviour tests for tools/everred_v3/scripts/ci_latency_report.py."""

import json
import runpy
import sys
import types

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

REL = "tools/everred_v3/scripts/ci_latency_report.py"
SCRIPT = REPO_ROOT / REL
REPO = "GBOGEB/ABACUS"
SHA = "d" * 40

cl = load("tools/everred_v3/src/ci_latency.py", name="abn_clr_ci_latency")


class UnconfiguredReader:
    def run_and_jobs(self, repo, run_id, sha):
        raise AssertionError("reader must be patched by the test")


_fake_ingest = types.ModuleType("abn_clr_native_ingest")
_fake_ingest.GitHubReadOnly = UnconfiguredReader

_saved_path = list(sys.path)
mod = load(
    REL,
    name="abn_ci_latency_report",
    deps={"ci_latency": cl, "native_ingest": _fake_ingest},
)
sys.path[:] = _saved_path


def _native(run_id, workflow="CI", event="pull_request", status="completed"):
    run = {
        "id": run_id,
        "head_sha": SHA,
        "repository": {"full_name": REPO},
        "run_attempt": 1,
        "status": status,
        "conclusion": "failure",
        "name": workflow,
        "event": event,
        "created_at": "2026-10-01T10:00:00Z",
        "updated_at": "2026-10-01T10:10:00Z",
    }
    jobs = [
        {
            "id": run_id * 10,
            "run_id": run_id,
            "status": "completed",
            "name": "tests",
            "conclusion": "failure",
            "created_at": "2026-10-01T10:00:30Z",
            "started_at": "2026-10-01T10:01:00Z",
            "completed_at": "2026-10-01T10:05:00Z",
            "steps": [
                {
                    "name": "Run pytest",
                    "started_at": "2026-10-01T10:02:00Z",
                    "completed_at": "2026-10-01T10:04:00Z",
                }
            ],
        }
    ]
    return run, jobs


def _reader_class(table, calls):
    class Reader:
        def run_and_jobs(self, repo, run_id, sha):
            calls.append((repo, run_id, sha))
            return table[run_id]

    return Reader


def _args(tmp_path, run_ids):
    return types.SimpleNamespace(
        repo=REPO,
        sha=SHA,
        run_id=run_ids,
        output=tmp_path / "nested" / "receipt.json",
    )


@pytest.mark.parametrize(
    "run_ids,reason",
    [
        ([], "between one and 30"),
        (None, "between one and 30"),
        (list(range(1, 32)), "between one and 30"),
        ([4, 5, 4], "duplicate native run IDs"),
    ],
)
def test_run_rejects_bad_run_id_lists(tmp_path, run_ids, reason):
    with pytest.raises(ValueError, match=reason):
        mod.run(_args(tmp_path, run_ids))


def test_run_writes_digest_bound_receipt(tmp_path, capsys, monkeypatch):
    calls = []
    table = {7: _native(7), 8: _native(8)}
    monkeypatch.setattr(mod, "GitHubReadOnly", _reader_class(table, calls))
    args = _args(tmp_path, [7, 8])
    mod.run(args)
    assert calls == [(REPO, 7, SHA), (REPO, 8, SHA)]
    raw = args.output.read_text(encoding="utf-8")
    receipt = json.loads(raw)
    assert receipt["schema"] == cl.SCHEMA + ".batch"
    assert receipt["merge_admission"] == "HOLD"
    assert receipt["security_waiver"] is False
    assert [r["run_id"] for r in receipt["run_receipts"]] == [7, 8]
    assert receipt["run_receipts"][0]["state"] == "MEASURED"
    assert receipt["run_receipts"][0]["workflow_wall_seconds"] == 600.0
    assert receipt["cohort"]["status"] == "DESCRIPTIVE_ONLY"
    assert receipt["cohort"]["eligible_runs"] == 2
    body = {k: v for k, v in receipt.items() if k != "sha256"}
    assert receipt["sha256"] == cl.digest_receipt(body)
    printed = json.loads(capsys.readouterr().out)
    assert printed == {
        "batch_digest": receipt["sha256"],
        "runs": 2,
        "source_sha": SHA,
        "state": "DESCRIPTIVE_ONLY",
    }


def test_run_mixed_workflows_is_incomparable(tmp_path, capsys, monkeypatch):
    table = {1: _native(1), 2: _native(2, workflow="Docs")}
    monkeypatch.setattr(mod, "GitHubReadOnly", _reader_class(table, []))
    mod.run(_args(tmp_path, [1, 2]))
    assert json.loads(capsys.readouterr().out)["state"] == "INCOMPARABLE_COHORT"


def test_run_propagates_native_validation_error(tmp_path, monkeypatch):
    table = {3: _native(3, status="in_progress")}
    monkeypatch.setattr(mod, "GitHubReadOnly", _reader_class(table, []))
    args = _args(tmp_path, [3])
    with pytest.raises(ValueError, match="nonterminal run"):
        mod.run(args)
    assert not args.output.exists()


def test_main_parses_arguments(tmp_path, capsys, monkeypatch):
    calls = []
    monkeypatch.setattr(mod, "GitHubReadOnly", _reader_class({9: _native(9)}, calls))
    out = tmp_path / "r.json"
    argv = ["prog", "--repo", REPO, "--sha", SHA, "--run-id", "9", "--output"]
    monkeypatch.setattr(sys, "argv", argv + [str(out)])
    mod.main()
    assert calls == [(REPO, 9, SHA)]
    assert json.loads(out.read_text(encoding="utf-8"))["source_sha"] == SHA
    assert json.loads(capsys.readouterr().out)["runs"] == 1


def test_main_requires_run_id(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["prog", "--repo", REPO, "--sha", SHA])
    with pytest.raises(SystemExit) as info:
        mod.main()
    assert info.value.code == 2
    assert "--run-id" in capsys.readouterr().err


def test_script_entry_point(tmp_path, capsys, monkeypatch):
    calls = []
    fake = types.ModuleType("native_ingest")
    fake.GitHubReadOnly = _reader_class({5: _native(5)}, calls)
    monkeypatch.setitem(sys.modules, "native_ingest", fake)
    monkeypatch.setitem(sys.modules, "ci_latency", cl)
    monkeypatch.setattr(sys, "path", list(sys.path))
    out = tmp_path / "e.json"
    argv = [str(SCRIPT), "--repo", REPO, "--sha", SHA, "--run-id", "5"]
    monkeypatch.setattr(sys, "argv", argv + ["--output", str(out)])
    runpy.run_path(str(SCRIPT), run_name="__main__")
    assert calls == [(REPO, 5, SHA)]
    assert json.loads(capsys.readouterr().out)["state"] == "DESCRIPTIVE_ONLY"
    assert out.exists()
