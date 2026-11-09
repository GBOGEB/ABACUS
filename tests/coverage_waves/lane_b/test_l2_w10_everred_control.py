"""Lane-B wave 10: everred_v3 KPI history chain, recurrence sentinels and CLI."""

import json
import sys
import types

import pytest

from ._l2_loader import load

FLOCK_CALLS = []

fake_fcntl = types.SimpleNamespace(
    LOCK_EX=2, LOCK_UN=8, LOCK_SH=1, flock=lambda fd, op: FLOCK_CALLS.append(op)
)
mt = load("tools/everred_v3/src/metrics.py")
ev = load("tools/everred_v3/src/everred.py", deps={"fcntl": fake_fcntl, "metrics": mt})
ctl = load("tools/everred_v3/src/control.py", deps={"fcntl": fake_fcntl, "everred": ev})

A = "a" * 40
REPO = "GBOGEB/ABACUS"


def _snapshot(**overrides):
    snap = {
        "schema": "abacus.everred.snapshot.v3",
        "events_count": 2,
        "coverage_scopes": {
            "broad": {
                "covered": 5,
                "eligible": 10,
                "sha": A,
                "config_id": "cfg",
                "value": 50.0,
                "extra": "dropped",
            },
            "alpha": {"covered": 1},
        },
        "metrics_derived": {
            "occurrence_amplification": 2.0,
            "consumer_replay_coverage_pct": 10.0,
            "recurrence_rate_pct": 0.0,
            "queue_wait_mean_seconds": 3.5,
            "security_comparable_pairs": [["x", "y"]],
            "coverage_comparable_pairs": None,
        },
    }
    snap.update(overrides)
    return snap


LEDGER = [{"id": "evt-0001", "kind": "note"}, {"id": "evt-0002", "kind": "coverage"}]


def _pulse(pid="p-1"):
    return {"pulse_id": pid, "value": pid}


# ----------------------------------------------------------- history_record


def test_history_record_projects_snapshot():
    rec = ctl.history_record(_snapshot(), LEDGER)
    assert rec["schema"] == "abacus.everred.kpi.pulse.v1"
    assert rec["ledger_fingerprint"] == ev.digest(LEDGER)
    assert rec["source_event_count"] == 2
    assert list(rec["coverage"]) == ["alpha", "broad"]
    assert rec["coverage"]["broad"] == {
        "covered": 5,
        "eligible": 10,
        "sha": A,
        "config_id": "cfg",
        "value": 50.0,
    }
    assert rec["coverage"]["alpha"]["eligible"] is None
    assert rec["occurrence_amplification"] == 2.0
    assert rec["queue_wait_mean_seconds"] == 3.5
    assert rec["security_comparable_pairs"] == [["x", "y"]]
    assert rec["coverage_comparable_pairs"] == []
    expected_id = ev.digest([rec["ledger_fingerprint"], 2, rec["coverage"]])[:24]
    assert rec["pulse_id"] == expected_id


def test_history_record_defaults_for_sparse_snapshot():
    snap = {"schema": "abacus.everred.snapshot.v3"}
    rec = ctl.history_record(snap, [])
    assert rec["coverage"] == {}
    assert rec["recurrence_rate_pct"] is None
    assert rec["security_comparable_pairs"] == []
    assert rec["source_event_count"] == 0


@pytest.mark.parametrize(
    "snap, ledger, msg",
    [
        ({"schema": "v2"}, [], "bad snapshot"),
        (_snapshot(), None, "missing source event ledger"),
        (_snapshot(), {"id": "x"}, "missing source event ledger"),
    ],
)
def test_history_record_rejections(snap, ledger, msg):
    with pytest.raises(ev.InvalidEvidence, match=msg):
        ctl.history_record(snap, ledger)


# ------------------------------------------------------- history read/write


def test_append_and_read_history_chain(tmp_path):
    path = tmp_path / "sub" / "kpi.jsonl"
    FLOCK_CALLS.clear()
    assert ctl.read_history(path) == []
    assert ctl.append_history(path, _pulse("p-1")) == "APPENDED"
    assert ctl.append_history(path, _pulse("p-2")) == "APPENDED"
    assert FLOCK_CALLS == [2, 8, 2, 8]
    assert path.with_suffix(".jsonl.lock").exists()
    assert ctl.read_history(path) == [_pulse("p-1"), _pulse("p-2")]
    rows = [json.loads(x) for x in path.read_text().splitlines()]
    assert rows[0]["prev_hash"] == "GENESIS"
    assert rows[1]["prev_hash"] == rows[0]["hash"]


def test_append_history_is_idempotent(tmp_path):
    path = tmp_path / "kpi.jsonl"
    ctl.append_history(path, _pulse())
    FLOCK_CALLS.clear()
    assert ctl.append_history(path, _pulse()) == "ALREADY_RECORDED"
    assert FLOCK_CALLS == [2, 8]
    assert len(path.read_text().splitlines()) == 1


def test_append_history_on_blank_file_starts_at_genesis(tmp_path):
    path = tmp_path / "kpi.jsonl"
    path.write_text("\n\n")
    assert ctl.read_history(path) == []
    assert ctl.append_history(path, _pulse()) == "APPENDED"
    row = json.loads([x for x in path.read_text().splitlines() if x][0])
    assert row["prev_hash"] == "GENESIS"
    assert ctl.read_history(path) == [_pulse()]


def _row(pulse, prev="GENESIS"):
    return {
        "pulse": pulse,
        "prev_hash": prev,
        "hash": ev.digest({"pulse": pulse, "prev_hash": prev}),
    }


def _lines(*rows):
    return "\n".join(json.dumps(r) for r in rows) + "\n"


_GOOD = _row(_pulse("p-1"))


@pytest.mark.parametrize(
    "content, msg",
    [
        ("{bad\n", "invalid KPI history line"),
        (_lines({"pulse": "str"}), "missing/duplicate KPI pulse"),
        (_lines({"pulse": {"x": 1}}), "missing/duplicate KPI pulse"),
        (_lines({}), "missing/duplicate KPI pulse"),
        (
            _lines(_GOOD, _row(_pulse("p-1"), _GOOD["hash"])),
            "missing/duplicate KPI pulse",
        ),
        (_lines(dict(_GOOD, prev_hash="X")), "hash mismatch line 1"),
        (_lines(dict(_GOOD, hash="0" * 64)), "hash mismatch line 1"),
        (_lines(_GOOD, _row(_pulse("p-2"))), "hash mismatch line 2"),
    ],
)
def test_read_history_rejections(tmp_path, content, msg):
    path = tmp_path / "kpi.jsonl"
    path.write_text(content)
    with pytest.raises(ev.InvalidEvidence, match=msg):
        ctl.read_history(path)


def test_append_history_releases_lock_on_corrupt_history(tmp_path):
    path = tmp_path / "kpi.jsonl"
    path.write_text("{bad\n")
    FLOCK_CALLS.clear()
    with pytest.raises(ev.InvalidEvidence, match="invalid KPI history line"):
        ctl.append_history(path, _pulse())
    assert FLOCK_CALLS == [2, 8]


# ------------------------------------------------------- recurrence_alerts


def _e(kind, eid, rid="root-1", state=None, prov="observed", sha=None):
    e = {"kind": kind, "id": eid, "root_id": rid, "provenance": prov}
    if state is not None:
        e["evidence"] = {"state": state}
    if sha:
        e["sha"] = sha
    return e


def test_recurrence_alerts_after_closed_root():
    events = [
        _e("recurrence", "r-0", rid="root-1"),
        _e("closure", "c-1", state="CLOSED"),
        _e("closure", "c-open", rid="root-2", state="OPEN"),
        _e("recurrence", "r-other", rid="root-2"),
        _e("note", "n-1", rid=None),
        _e("recurrence", "r-1", sha=A),
        _e("recurrence", "r-1", sha=A),
        _e("closure", "c-2", rid="root-3", state="CLOSED", prov="imported"),
        _e("recurrence", "r-3", rid="root-3"),
        _e("closure", "c-nostate", rid="root-4"),
        _e("recurrence", "r-4", rid="root-4"),
    ]
    alerts = ctl.recurrence_alerts(events)
    assert [a["trigger_occurrence_id"] for a in alerts] == ["r-1", "r-3"]
    first, second = alerts
    assert first["alert_id"] == ev.digest(["root-1", "c-1", "r-1"])[:24]
    assert first["historical_closure_id"] == "c-1"
    assert first["source_sha"] == A
    assert first["authenticated"] is True
    assert first["severity"] == "REVIEW_REQUIRED"
    assert first["notified"] is False
    assert second["authenticated"] is False
    assert second["source_sha"] is None


def test_recurrence_alerts_unauthenticated_recurrence():
    events = [
        _e("closure", "c-1", state="CLOSED"),
        _e("recurrence", "r-1", prov="imported"),
    ]
    (alert,) = ctl.recurrence_alerts(events)
    assert alert["authenticated"] is False


def test_recurrence_alerts_empty():
    assert ctl.recurrence_alerts([]) == []


# --------------------------------------------------------------------- CLI


def _note(eid):
    return {
        "schema": ev.SCHEMA,
        "kind": "note",
        "id": eid,
        "occurred_at": "2026-10-01T00:00:00Z",
        "repo": REPO,
        "provenance": "observed",
        "evidence": {},
    }


def _run_main(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "everred", ev)
    ledger = tmp_path / "ledger.jsonl"
    history = tmp_path / "out" / "kpi.jsonl"
    alerts = tmp_path / "alerts.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "control",
            "--ledger",
            str(ledger),
            "--history",
            str(history),
            "--alerts",
            str(alerts),
        ],
    )
    ctl.main()
    return ledger, history, alerts


def test_main_with_missing_ledger(monkeypatch, tmp_path, capsys):
    _, history, alerts = _run_main(monkeypatch, tmp_path)
    out = capsys.readouterr().out
    assert "KPI history: APPENDED" in out
    assert "Recurrence alerts: 0 notification transport not configured" in out
    assert json.loads(alerts.read_text()) == {
        "schema": "abacus.everred.alerts.v1",
        "alerts": [],
    }
    (pulse,) = ctl.read_history(history)
    assert pulse["source_event_count"] == 0


def test_main_with_ledger_is_idempotent(monkeypatch, tmp_path, capsys):
    ledger = tmp_path / "ledger.jsonl"
    ev.append_event(ledger, _note("evt-0001"))
    _run_main(monkeypatch, tmp_path)
    capsys.readouterr()
    _, history, _ = _run_main(monkeypatch, tmp_path)
    assert "KPI history: ALREADY_RECORDED" in capsys.readouterr().out
    (pulse,) = ctl.read_history(history)
    assert pulse["source_event_count"] == 1
