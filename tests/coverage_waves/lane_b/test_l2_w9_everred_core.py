"""Lane-B wave 9: everred_v3 evidence ledger (validation, hash chain, locking, CLI)."""

import copy
import json
import os
import sys
import types

import pytest

from ._l2_loader import load

FLOCK_CALLS = []

fake_fcntl = types.SimpleNamespace(
    LOCK_EX=2, LOCK_UN=8, flock=lambda fd, op: FLOCK_CALLS.append(op)
)
mt = load("tools/everred_v3/src/metrics.py")
ev = load("tools/everred_v3/src/everred.py", deps={"fcntl": fake_fcntl, "metrics": mt})

A, B, C = "a" * 40, "b" * 40, "c" * 40
REPO = "GBOGEB/ABACUS"
GATES_PASS = {g: "PASS" for g in ev.ADMISSION_GATES}


def _event(kind="note", eid="evt-0001", **overrides):
    e = {
        "schema": ev.SCHEMA,
        "kind": kind,
        "id": eid,
        "occurred_at": "2026-10-01T00:00:00Z",
        "repo": REPO,
        "provenance": "observed",
        "evidence": {},
    }
    e.update(overrides)
    return e


def _coverage(eid="cov-0001", sha=A, **evidence):
    values = {
        "scope": "broad",
        "unit": "lines",
        "covered": 5,
        "eligible": 10,
        "config_id": "cfg",
    }
    values.update(evidence)
    return _event("coverage", eid, sha=sha, evidence=values)


def _lease(eid="lease-001", root="root-1", key="k1", paths=("src/a",), repo=REPO):
    return _event(
        "lease_acquired",
        eid,
        repo=repo,
        sha=A,
        root_id=root,
        evidence={
            "principal": "worker",
            "idempotency_key": key,
            "paths": list(paths),
            "authorized": True,
        },
    )


def _release(eid="rel-0001", root="root-1", acquired="lease-001"):
    return _event(
        "lease_released", eid, root_id=root, evidence={"acquired_event_id": acquired}
    )


def _admission(decision="HOLD", gates=None):
    return _event(
        "admission",
        "adm-0001",
        sha=A,
        evidence={"gates": dict(gates or GATES_PASS), "decision": decision},
    )


# --- primitives -----------------------------------------------------------------------------------


def test_stable_json_digest_and_valid_sha():
    assert ev.stable_json({"b": 1, "a": "é"}) == '{"a":"é","b":1}'
    assert ev.digest({"x": 1}) == ev.digest({"x": 1})
    assert len(ev.digest([])) == 64
    with pytest.raises(ValueError):
        ev.stable_json(float("nan"))
    assert ev.valid_sha(A) is True
    assert ev.valid_sha("A" * 40) is False
    assert ev.valid_sha(None) is False
    ev.require(True, "unused")
    with pytest.raises(ev.InvalidEvidence, match="boom"):
        ev.require(False, "boom")
    assert issubclass(ev.InvalidEvidence, ValueError)


@pytest.mark.parametrize(
    "a,b,expected",
    [
        ("src/a", "src/a/", True),
        ("src/a/b", "src/a", True),
        ("src/a", "src/a/b", True),
        ("src/a", "src/ab", False),
        ("docs", "src", False),
    ],
)
def test_overlap(a, b, expected):
    assert ev.overlap(a, b) is expected


# --- validate_event -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "event",
    [
        _event(),
        _event("verification", sha=A),
        _coverage(),
        _coverage(covered=None, eligible=None),
        _admission("HOLD"),
        _admission("HOLD", {**GATES_PASS, "security": "RED"}),
        _lease(),
        _event(occurred_at="2026-10-01T00:00:00+02:00", provenance="manual"),
    ],
)
def test_validate_event_accepts(event):
    assert ev.validate_event(event) is None


def _mutate(base, path, value):
    e = copy.deepcopy(base)
    target = e
    for key in path[:-1]:
        target = target[key]
    if value is KeyError:
        del target[path[-1]]
    else:
        target[path[-1]] = value
    return e


@pytest.mark.parametrize(
    "event,message",
    [
        ("notadict", "event must be object"),
        (_mutate(_event(), ["schema"], "v2"), "wrong schema"),
        (_mutate(_event(), ["kind"], "bogus"), "invalid kind"),
        (_mutate(_event(), ["id"], "abc"), "event id missing"),
        (_mutate(_event(), ["id"], 12345), "event id missing"),
        (_mutate(_event(), ["occurred_at"], "2026-10-01"), "timestamp missing"),
        (_mutate(_event(), ["occurred_at"], 5), "timestamp missing"),
        (_mutate(_event(), ["occurred_at"], "2026-13-01T00:00"), "timestamp invalid"),
        (_mutate(_event(), ["repo"], "ABACUS"), "repo missing"),
        (_mutate(_event(), ["provenance"], "guess"), "provenance missing"),
        (_mutate(_event(), ["provenance"], None), "provenance missing"),
        (_mutate(_event(), ["evidence"], []), "evidence object missing"),
        (_event("runtime"), "exact 40-char SHA required"),
        (_event("security_census", sha="abc"), "exact 40-char SHA required"),
        (_coverage(scope="all"), "coverage scope missing"),
        (_coverage(unit="pct"), "coverage unit missing"),
        (_coverage(covered=11), "invalid coverage denominator"),
        (_coverage(covered=-1), "invalid coverage denominator"),
        (_coverage(covered=0, eligible=0), "invalid coverage denominator"),
        (_coverage(covered=True), "invalid coverage denominator"),
        (_coverage(covered=None), "invalid coverage denominator"),
        (_coverage(config_id=""), "coverage config identity missing"),
        (_coverage(config_id=3), "coverage config identity missing"),
        (_mutate(_admission(), ["evidence", "gates"], []), "gates required"),
        (
            _mutate(_admission(), ["evidence", "gates", "security"], KeyError),
            "missing admission gates",
        ),
        (
            _mutate(_admission(), ["evidence", "gates", "security"], "GREEN"),
            "invalid gate state",
        ),
        (
            _admission("ADMIT", {**GATES_PASS, "coverage": "UNKNOWN"}),
            "fail-closed: cannot admit",
        ),
        (_admission("ADMIT"), "offline ledger cannot authenticate"),
        (_mutate(_lease(), ["root_id"], ""), "lease identity incomplete"),
        (
            _mutate(_lease(), ["evidence", "principal"], None),
            "lease identity incomplete",
        ),
        (
            _mutate(_lease(), ["evidence", "idempotency_key"], KeyError),
            "lease identity incomplete",
        ),
        (_mutate(_lease(), ["sha"], "x"), "lease expected head SHA missing"),
        (_mutate(_lease(), ["evidence", "paths"], []), "lease paths missing"),
        (_mutate(_lease(), ["evidence", "paths"], "src"), "lease paths missing"),
        (_lease(paths=("",)), "unsafe lease path"),
        (_lease(paths=("/etc",)), "unsafe lease path"),
        (_lease(paths=("src/../x",)), "unsafe lease path"),
        (_mutate(_lease(), ["evidence", "paths"], [3]), "unsafe lease path"),
        (_mutate(_lease(), ["evidence", "authorized"], "yes"), "explicitly authorized"),
    ],
)
def test_validate_event_rejections(event, message):
    with pytest.raises(ev.InvalidEvidence, match=message):
        ev.validate_event(event)


# --- validate_cross_events ------------------------------------------------------------------------


def test_cross_events_lease_lifecycle():
    ev.validate_cross_events(
        [
            _lease(),
            _lease("lease-002", "root-2", "k2", ("docs",)),
            _lease("lease-003", "root-3", "k3", ("src/a",), repo="GBOGEB/OTHER"),
            _release(),
            _lease("lease-004", "root-1", "k4", ("src/a/b",)),
            _event(),
        ]
    )


@pytest.mark.parametrize(
    "events,message",
    [
        ([_lease(), _lease("lease-002", "root-2", "k1", ("x",))], "duplicate idem"),
        (
            [_lease(), _lease("lease-002", "root-2", "k2", ("src",))],
            "overlapping canonical path leases",
        ),
        (
            [_lease(), _lease("lease-002", "root-1", "k2", ("docs",))],
            "duplicate active owner",
        ),
        ([_release()], "lease release without active lease"),
        ([_lease(), _release(acquired="other")], "lease release mismatch"),
    ],
)
def test_cross_events_rejections(events, message):
    with pytest.raises(ev.InvalidEvidence, match=message):
        ev.validate_cross_events(events)


# --- ledger read / append -------------------------------------------------------------------------


def _row(event, prev):
    return {
        "event": event,
        "prev_hash": prev,
        "hash": ev.digest({"event": event, "prev_hash": prev}),
    }


def test_read_ledger_missing_and_valid(tmp_path):
    path = tmp_path / "ledger.jsonl"
    assert ev.read_ledger(path) == []
    first = _row(_event(eid="evt-0001"), "GENESIS")
    second = _row(_event(eid="evt-0002"), first["hash"])
    path.write_text(
        ev.stable_json(first) + "\n\n   \n" + ev.stable_json(second) + "\n",
        encoding="utf-8",
    )
    assert [e["id"] for e in ev.read_ledger(path)] == ["evt-0001", "evt-0002"]


def _bad_ledgers():
    first = _row(_event(eid="evt-0001"), "GENESIS")
    dup = _row(_event(eid="evt-0001"), first["hash"])
    broken = _row(_event(eid="evt-0002"), "nothash")
    tampered = dict(_row(_event(eid="evt-0002"), first["hash"]), hash="f" * 64)
    released = _row(_release(), "GENESIS")
    return [
        (["{not json"], "bad JSON line 1"),
        ([ev.stable_json({"event": "x"})], "no event line 1"),
        ([ev.stable_json({"event": _event(kind="nope")})], "invalid kind"),
        ([ev.stable_json(first), ev.stable_json(dup)], "duplicate event id line 2"),
        ([ev.stable_json(first), ev.stable_json(broken)], "broken hash chain line 2"),
        ([ev.stable_json(first), ev.stable_json(tampered)], "tampered event line 2"),
        ([ev.stable_json(released)], "lease release without active lease"),
    ]


@pytest.mark.parametrize("lines,message", _bad_ledgers())
def test_read_ledger_rejections(tmp_path, lines, message):
    path = tmp_path / "ledger.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(ev.InvalidEvidence, match=message):
        ev.read_ledger(path)


def test_append_event_builds_chain_and_locks(tmp_path):
    path = tmp_path / "nested" / "ledger.jsonl"
    FLOCK_CALLS.clear()
    row1 = ev.append_event(path, _event(eid="evt-0001"))
    assert row1["prev_hash"] == "GENESIS"
    assert FLOCK_CALLS == [fake_fcntl.LOCK_EX, fake_fcntl.LOCK_UN]
    assert (tmp_path / "nested" / "ledger.jsonl.lock").exists()
    row2 = ev.append_event(path, _event(eid="evt-0002"))
    assert row2["prev_hash"] == row1["hash"]
    assert len(ev.read_ledger(path)) == 2


def test_append_event_unlocks_on_failure(tmp_path):
    path = tmp_path / "ledger.jsonl"
    ev.append_event(path, _event(eid="evt-0001"))
    FLOCK_CALLS.clear()
    with pytest.raises(ev.InvalidEvidence, match="duplicate event id"):
        ev.append_event(path, _event(eid="evt-0001"))
    assert FLOCK_CALLS == [fake_fcntl.LOCK_EX, fake_fcntl.LOCK_UN]
    with pytest.raises(ev.InvalidEvidence, match="lease release without"):
        ev.append_event(path, _release())
    with pytest.raises(ev.InvalidEvidence, match="wrong schema"):
        ev.append_event(path, _event(schema="x"))


def test_append_unlocked_whitespace_only_file_starts_at_genesis(tmp_path):
    path = tmp_path / "ledger.jsonl"
    path.write_text("\n  \n", encoding="utf-8")
    assert ev._append_unlocked(path, _event())["prev_hash"] == "GENESIS"


# --- append_events_batch --------------------------------------------------------------------------


def test_batch_new_and_existing_ledger(tmp_path):
    path = tmp_path / "sub" / "ledger.jsonl"
    FLOCK_CALLS.clear()
    assert ev.append_events_batch(path, [_event(eid="evt-0001"), _lease()]) == 2
    assert FLOCK_CALLS == [fake_fcntl.LOCK_EX, fake_fcntl.LOCK_UN]
    before = path.read_bytes()
    assert ev.append_events_batch(path, [_release(), _event(eid="evt-0003")]) == 2
    after = path.read_bytes()
    assert after.startswith(before)
    assert [e["id"] for e in ev.read_ledger(path)] == [
        "evt-0001",
        "lease-001",
        "rel-0001",
        "evt-0003",
    ]
    leftovers = [p.name for p in path.parent.iterdir() if p.name.startswith(".ever")]
    assert leftovers == []


@pytest.mark.parametrize(
    "events,message",
    [
        ([], "empty native event batch"),
        ("notalist", "empty native event batch"),
        ([_event(eid="evt-0001")], "native batch contains existing event ID"),
        (
            [_event(eid="evt-0002"), _event(eid="evt-0002")],
            "native batch contains duplicate event ID",
        ),
        ([_event(eid="evt-0002", kind="bogus")], "invalid kind"),
        ([_release()], "lease release without active lease"),
    ],
)
def test_batch_rejections(tmp_path, events, message):
    path = tmp_path / "ledger.jsonl"
    ev.append_events_batch(path, [_event(eid="evt-0001")])
    original = path.read_bytes()
    with pytest.raises(ev.InvalidEvidence, match=message):
        ev.append_events_batch(path, events)
    assert path.read_bytes() == original


def test_batch_rejects_incomplete_final_line(tmp_path):
    path = tmp_path / "ledger.jsonl"
    path.write_text(ev.stable_json(_row(_event(), "GENESIS")), encoding="utf-8")
    FLOCK_CALLS.clear()
    with pytest.raises(ev.InvalidEvidence, match="incomplete final line"):
        ev.append_events_batch(path, [_event(eid="evt-0002")])
    assert FLOCK_CALLS == [fake_fcntl.LOCK_EX, fake_fcntl.LOCK_UN]


def test_batch_removes_temp_file_when_publish_fails(tmp_path, monkeypatch):
    def boom(src, dst):
        raise OSError("replace failed")

    fake_os = types.SimpleNamespace(
        fdopen=os.fdopen,
        fsync=os.fsync,
        replace=boom,
        path=os.path,
        unlink=os.unlink,
    )
    monkeypatch.setattr(ev, "os", fake_os)
    path = tmp_path / "ledger.jsonl"
    with pytest.raises(OSError, match="replace failed"):
        ev.append_events_batch(path, [_event()])
    assert not path.exists()
    assert [p.name for p in tmp_path.iterdir()] == ["ledger.jsonl.lock"]


# --- coverage_rate / snapshot ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "evidence,expected",
    [
        ({"covered": 1, "eligible": 3}, 33.33),
        ({"covered": None, "eligible": None}, None),
        ({"covered": 1, "eligible": 0}, None),
        ({"covered": 1.0, "eligible": 2}, None),
        ({"covered": 1, "eligible": True}, None),
    ],
)
def test_coverage_rate(evidence, expected):
    assert ev.coverage_rate({"evidence": evidence}) == expected


def test_snapshot_classifies_events():
    events = [
        _event("root_candidate", "root-ev1", root_id="R1", evidence={"title": "T"}),
        _event(
            "root_confirmed",
            "root-ev2",
            root_id="R2",
            provenance="manual",
            evidence={"owner": "me", "cause": "c", "url": "u"},
        ),
        _event("root_candidate", "root-ev3", evidence={}),
        _event("occurrence", "occ-0001", root_id="R2"),
        _coverage("cov-0001", sha=A, scope="focused"),
        _coverage("cov-0002", sha=B, scope="broad", run_id=7, reported_combined=1),
        _coverage("cov-0003", sha=C, scope="broad", unit="branches"),
        _event("security_census", "sec-0001", sha=A),
        _admission(),
        _event("note", "note-0001"),
    ]
    snap = ev.snapshot(events)
    assert snap["schema"] == "abacus.everred.snapshot.v3"
    assert snap["base_sha"] == B
    assert snap["events_count"] == 10
    assert snap["root_count"] == 2
    r1, r2 = snap["roots"]
    assert r1 == {
        "id": "R1",
        "title": "T",
        "state": "CANDIDATE",
        "owner": "UNASSIGNED",
        "cause": "UNKNOWN",
        "applicable_consumers": None,
        "source": None,
        "provenance": "observed",
    }
    assert r2["state"] == "CONFIRMED" and r2["title"] == "R2"
    assert (r2["owner"], r2["cause"], r2["source"]) == ("me", "c", "u")
    assert [e["id"] for e in snap["occurrences"]] == ["occ-0001"]
    assert [e["id"] for e in snap["security_scans"]] == ["sec-0001"]
    assert [e["id"] for e in snap["admissions"]] == ["adm-0001"]
    assert [e["id"] for e in snap["other_events"]] == ["root-ev3", "note-0001"]
    assert snap["coverage_scopes"]["broad:lines"] == {
        "value": 50.0,
        "covered": 5,
        "eligible": 10,
        "sha": B,
        "config_id": "cfg",
        "run_id": 7,
        "reported_combined": 1,
        "provenance": "observed",
    }
    assert set(snap["coverage_scopes"]) == {
        "focused:lines",
        "broad:lines",
        "broad:branches",
    }
    assert snap["kpis"][0]["value"] == 1
    assert snap["kpis"][0]["status"] == "OBSERVED"
    assert snap["metrics_derived"]["occurrence_amplification"] == 1.0
    assert snap["mode"] == "HISTORICAL_EVIDENCE_NOT_LIVE"
    assert "kpi_unknowns" in snap and "disclaimer" in snap


def test_snapshot_empty():
    snap = ev.snapshot([])
    assert snap["base_sha"] is None
    assert snap["roots"] == []
    assert snap["kpis"][0] == {
        "name": "confirmed_roots",
        "value": 0,
        "denominator": None,
        "status": "UNKNOWN",
        "scope": "ledger",
    }


def test_snapshot_without_broad_coverage_has_no_base():
    assert ev.snapshot([_coverage(scope="focused")])["base_sha"] is None


# --- main CLI -------------------------------------------------------------------------------------


def _run_main(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["everred.py", *argv])
    ev.main()


def test_main_append_verify_snapshot(tmp_path, monkeypatch, capsys):
    ledger = tmp_path / "ledger.jsonl"
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps(_coverage()), encoding="utf-8")
    _run_main(
        monkeypatch, "append", "--ledger", str(ledger), "--event", str(event_file)
    )
    row = json.loads(capsys.readouterr().out)
    assert row["prev_hash"] == "GENESIS" and row["event"]["id"] == "cov-0001"

    _run_main(monkeypatch, "verify", "--ledger", str(ledger))
    assert capsys.readouterr().out.strip() == "VALID 1 events"

    out = tmp_path / "out" / "snap.json"
    _run_main(monkeypatch, "snapshot", "--ledger", str(ledger), "--output", str(out))
    assert capsys.readouterr().out.strip() == f"Snapshot {out}: 1 events"
    assert json.loads(out.read_text(encoding="utf-8"))["base_sha"] == A


def test_main_append_requires_event(tmp_path, monkeypatch):
    with pytest.raises(ev.InvalidEvidence, match="--event required"):
        _run_main(monkeypatch, "append", "--ledger", str(tmp_path / "l.jsonl"))


def test_main_rejects_unknown_command(monkeypatch):
    with pytest.raises(SystemExit):
        _run_main(monkeypatch, "delete")
