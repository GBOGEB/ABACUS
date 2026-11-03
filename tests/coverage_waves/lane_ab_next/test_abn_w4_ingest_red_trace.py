"""Behaviour tests for tools/everred_v3/scripts/ingest_red_trace.py.

The real ``everred`` ledger module imports ``fcntl`` (Unix-only), so a small
in-memory stub providing exactly the attributes this adapter uses is injected.
"""

import json
import re
import runpy
import sys
import types

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

REL = "tools/everred_v3/scripts/ingest_red_trace.py"
SCRIPT = REPO_ROOT / REL
REPO = "GBOGEB/ABACUS"
A, B, C, D = "a" * 40, "b" * 40, "c" * 40, "d" * 40


class _Invalid(ValueError):
    pass


def _make_stub():
    stub = types.ModuleType("everred")
    stub.SCHEMA = "abacus.everred.event.v3"
    stub.InvalidEvidence = _Invalid
    stub.validated = []

    def valid_sha(value):
        return isinstance(value, str) and bool(re.fullmatch("[0-9a-f]{40}", value))

    def validate_event(event):
        for key in ("schema", "id", "kind", "repo", "occurred_at", "evidence"):
            if key not in event:
                raise _Invalid("missing " + key)
        stub.validated.append(event["id"])

    def read_ledger(path):
        lines = path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def append_events_batch(path, events):
        with path.open("a", encoding="utf-8") as handle:
            for event in events:
                handle.write(json.dumps(event, sort_keys=True) + "\n")
        return len(events)

    stub.valid_sha = valid_sha
    stub.validate_event = validate_event
    stub.read_ledger = read_ledger
    stub.append_events_batch = append_events_batch
    return stub


STUB = _make_stub()
_saved_path = list(sys.path)
mod = load(REL, name="abn_ingest_red_trace", deps={"everred": STUB})
sys.path[:] = _saved_path


def _brk(sha, run, at="2026-10-01T00:00:00Z", **extra):
    doc = dict(first_red_sha=sha, first_red_run=run, first_red_at=at)
    doc.update(extra)
    return doc


def _report():
    workflows = [
        dict(
            name="CI Tests",
            path=".github/workflows/ci.yml",
            **{"class": "GREEN_TO_RED"},
            pinned_historical_ids=[123],
            current="RED",
            stale=True,
            latest=dict(sha=B, at="2026-10-05T00:00:00Z"),
            latest_age_days=5,
            red_episodes=[
                dict(recovery_sha=None),
                dict(
                    recovery_sha=C,
                    recovered_at="2026-10-06T00:00:00Z",
                    recovery_run=77,
                    first_red_sha=A,
                    red_hours=12,
                ),
            ],
            **{
                "break": _brk(
                    A,
                    11,
                    last_green_sha=D,
                    suspect_commit_count=2,
                    red_streak_runs=4,
                    failing=[dict(job="pytest", steps=["setup", "run"])],
                )
            },
        ),
        dict(
            name="Lint",
            path=".github/workflows/lint.yml",
            **{"class": "EVERRED"},
            current="RED",
            first_red=dict(sha=A, run_id=12, at="2026-10-01T01:00:00Z"),
        ),
        dict(
            name="Flaky One",
            path=".github/workflows/flaky.yml",
            **{"class": "FLAKY"},
            current="RED",
            pinned_historical_ids=["artifact-9"],
            **{"break": _brk(C, 21)},
        ),
        dict(
            name="Flaky Green",
            path="f2.yml",
            **{"class": "FLAKY"},
            current="GREEN",
            stale=True,
            red_episodes=[],
        ),
        dict(name="No Trace", path="n.yml", **{"class": "GREEN_TO_RED"}),
        dict(
            name="Bad Sha",
            path="b.yml",
            **{"class": "EVERRED"},
            first_red=dict(sha="nothex", run_id=1, at="t"),
        ),
        dict(
            name="Green",
            path="g.yml",
            **{"class": "GREEN"},
            current="GREEN",
            red_episodes=[dict(recovery_sha="XYZ")],
        ),
    ]
    return dict(
        schema=mod.SOURCE_SCHEMA,
        authority=dict(merge_authorized=False),
        repository=REPO,
        digest_sha256="f" * 64,
        workflows=workflows,
    )


def test_slug():
    assert mod.slug("  CI / Tests (py3.11) ") == "CI-Tests-py3-11"
    assert len(mod.slug("x" * 100)) == 48


def test_ev_optional_fields():
    bare = mod._ev("id1", "note", REPO, "t", None, {})
    assert "sha" not in bare and "root_id" not in bare
    assert bare["schema"] == STUB.SCHEMA and bare["provenance"] == "observed"
    full = mod._ev("id2", "occurrence", REPO, "t", A, {"k": 1}, root_id="R")
    assert full["sha"] == A and full["root_id"] == "R"


def test_events_from_report_mapping():
    events = mod.events_from_report(_report())
    by_id = {e["id"]: e for e in events}
    kinds = sorted(e["kind"] for e in events)
    assert kinds == [
        "note",
        "occurrence",
        "occurrence",
        "occurrence",
        "root_candidate",
        "root_candidate",
        "verification",
    ]
    occ = by_id["RT-OCC-ABACUS-CI-Tests-" + A[:12]]
    assert occ["root_id"] == "RT-ROOT-ABACUS-" + A[:12]
    assert occ["evidence"]["failing"] == ["pytest: setup, run"]
    assert occ["evidence"]["url"].endswith("/actions/runs/11")
    assert occ["evidence"]["run_id"] == "11"
    assert occ["evidence"]["stale"] is True
    lint = by_id["RT-OCC-ABACUS-Lint-" + A[:12]]
    assert lint["occurred_at"] == "2026-10-01T01:00:00Z"
    assert lint["evidence"]["pinned_historical_ids"] == []
    assert lint["evidence"]["failing"] == []

    shared = by_id["RT-ROOT-ABACUS-" + A[:12]]
    assert shared["evidence"]["title"].startswith("Shared break root: 2 workflows")
    assert shared["evidence"]["cause"] == "UNKNOWN"
    assert shared["evidence"]["cause_basis"] is None
    assert shared["evidence"]["applicable_consumers"] == ["CI Tests", "Lint"]
    assert shared["evidence"]["source_digest"] == "f" * 64

    single = by_id["RT-ROOT-ABACUS-" + C[:12]]
    assert single["evidence"]["title"] == "Flaky One red from " + C[:8]
    assert single["evidence"]["cause"] == "PINNED_HISTORICAL_EVIDENCE"
    assert "hard-codes" in single["evidence"]["cause_basis"]

    note = by_id["RT-STALE-ABACUS-CI-Tests-" + B[:12]]
    assert note["evidence"]["age_days"] == 5
    ver = by_id["RT-VER-ABACUS-CI-Tests-" + C[:12]]
    assert ver["evidence"]["status"] == "PASS"
    assert ver["evidence"]["recovers_first_red_sha"] == A
    assert ver["evidence"]["run_id"] == "77"
    assert set(STUB.validated) >= set(by_id)


def test_events_from_report_rejects_schema_and_authority():
    with pytest.raises(_Invalid, match="not a gogreen"):
        mod.events_from_report(dict(schema="other"))
    with pytest.raises(_Invalid, match="merge authority"):
        mod.events_from_report(dict(schema=mod.SOURCE_SCHEMA))
    bad = dict(schema=mod.SOURCE_SCHEMA, authority=dict(merge_authorized=True))
    with pytest.raises(_Invalid, match="merge authority"):
        mod.events_from_report(bad)


def _write(path, doc):
    path.write_bytes(json.dumps(doc).encode("utf-8"))
    return path


def test_main_dry_run_without_ledger(tmp_path, capsys):
    rep = _write(tmp_path / "rt.json", _report())
    ledger = tmp_path / "missing" / "ledger.jsonl"
    mod.main(["--input", str(rep), "--ledger", str(ledger)])
    out = json.loads(capsys.readouterr().out)
    assert out["events"] == 7 and out["new"] == 7
    assert out["already_present"] == 0
    assert out["applied"] is False
    assert out["kinds"]["occurrence"] == 3
    assert not ledger.exists()


def test_main_apply_output_and_idempotence(tmp_path, capsys):
    rep = _write(tmp_path / "rt.json", _report())
    ledger = tmp_path / "ledger.jsonl"
    first = json.dumps(dict(id="RT-ROOT-ABACUS-" + C[:12]))
    ledger.write_bytes((first + "\n\n").encode("utf-8"))
    batch = tmp_path / "batch.json"
    argv = ["--input", str(rep), "--ledger", str(ledger), "--output", str(batch)]
    mod.main(argv + ["--apply"])
    out = json.loads(capsys.readouterr().out)
    assert out["new"] == 6 and out["already_present"] == 1
    assert out["applied"] is True
    written = json.loads(batch.read_text(encoding="utf-8"))
    assert len(written) == 6
    assert len(STUB.read_ledger(ledger)) == 7

    mod.main(argv + ["--apply"])
    again = json.loads(capsys.readouterr().out)
    assert again["new"] == 0 and again["applied"] is False
    assert again["kinds"] == {}
    assert json.loads(batch.read_text(encoding="utf-8")) == []


def test_main_requires_input():
    with pytest.raises(SystemExit):
        mod.main([])


def test_run_as_script(tmp_path, capsys, monkeypatch):
    rep = _write(tmp_path / "rt.json", _report())
    ledger = tmp_path / "l.jsonl"
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setitem(sys.modules, "everred", _make_stub())
    argv = [str(SCRIPT), "--input", str(rep), "--ledger", str(ledger)]
    monkeypatch.setattr(sys, "argv", argv)
    runpy.run_path(str(SCRIPT), run_name="__main__")
    assert json.loads(capsys.readouterr().out)["status"] == "PASS"
