"""Hash-chained KPI history and recurrence sentinels (no automatic merge/waiver)."""

from __future__ import annotations

import argparse
import fcntl
import json
import pathlib

from everred import InvalidEvidence, digest, stable_json


def history_record(snapshot, ledger_events):
    if snapshot.get("schema") != "abacus.everred.snapshot.v3":
        raise InvalidEvidence("bad snapshot")
    if not isinstance(ledger_events, list):
        raise InvalidEvidence("missing source event ledger")
    source = digest([{"id": x["id"], "kind": x["kind"]} for x in ledger_events])
    coverage = {
        k: {m: v.get(m) for m in ("covered", "eligible", "sha", "config_id", "value")}
        for k, v in sorted(snapshot.get("coverage_scopes", {}).items())
    }
    metric = snapshot.get("metrics_derived", {})
    return {
        "schema": "abacus.everred.kpi.pulse.v1",
        "pulse_id": digest([source, snapshot.get("events_count"), coverage])[:24],
        "ledger_fingerprint": source,
        "source_event_count": len(ledger_events),
        "provenance": "HISTORICAL_OR_SOURCE_REPORTED_UNLESS_AUTHENTICATED",
        "coverage": coverage,
        "occurrence_amplification": metric.get("occurrence_amplification"),
        "consumer_replay_coverage_pct": metric.get("consumer_replay_coverage_pct"),
        "recurrence_rate_pct": metric.get("recurrence_rate_pct"),
        "queue_wait_mean_seconds": metric.get("queue_wait_mean_seconds"),
        "security_comparable_pairs": metric.get("security_comparable_pairs") or [],
        "coverage_comparable_pairs": metric.get("coverage_comparable_pairs") or [],
    }


def read_history(path):
    if not path.exists():
        return []
    seen = set()
    prev = "GENESIS"
    out = []
    for lno, line in enumerate(path.read_text().splitlines(), 1):
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError as ex:
            raise InvalidEvidence("invalid KPI history line") from ex
        payload = row.get("pulse")
        ident = payload.get("pulse_id") if isinstance(payload, dict) else None
        if not ident or ident in seen:
            raise InvalidEvidence("missing/duplicate KPI pulse")
        if row.get("prev_hash") != prev or row.get("hash") != digest(
            {"pulse": payload, "prev_hash": prev}
        ):
            raise InvalidEvidence(f"KPI history hash mismatch line {lno}")
        prev = row["hash"]
        seen.add(ident)
        out.append(payload)
    return out


def append_history(path, pulse):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(path.suffix + ".lock").open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            previous = read_history(path)
            if pulse["pulse_id"] in {x["pulse_id"] for x in previous}:
                return "ALREADY_RECORDED"
            prev = "GENESIS"
            if path.exists():
                lines = [l for l in path.read_text().splitlines() if l]
                if lines:
                    prev = json.loads(lines[-1])["hash"]
            row = {
                "pulse": pulse,
                "prev_hash": prev,
                "hash": digest({"pulse": pulse, "prev_hash": prev}),
            }
            with path.open("a") as f:
                f.write(stable_json(row) + "\n")
            return "APPENDED"
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def recurrence_alerts(events):
    """Only emit candidate alerts on a new observed recurrence after a closed root.

    Closure/recurrence events are source claims, not proof global control.
    """
    last_closure = {}
    alerts = []
    seen = set()
    for e in events:
        kind = e.get("kind")
        rid = e.get("root_id")
        if not rid:
            continue
        if kind == "closure" and e.get("evidence", {}).get("state") == "CLOSED":
            last_closure[rid] = e
        if kind == "recurrence" and rid in last_closure:
            root = last_closure[rid]
            if e["id"] in seen:
                continue
            seen.add(e["id"])
            alerts.append(
                {
                    "schema": "abacus.everred.alert.v1",
                    "alert_id": digest([rid, root["id"], e["id"]])[:24],
                    "root_id": rid,
                    "severity": "REVIEW_REQUIRED",
                    "trigger_occurrence_id": e["id"],
                    "historical_closure_id": root["id"],
                    "source_sha": e.get("sha"),
                    "authenticated": e.get("provenance") == "observed"
                    and root.get("provenance") == "observed",
                    "disposition": "REOPEN_CAUSAL_INVESTIGATION_NOT_AUTO_REPAIR",
                    "notified": False,
                }
            )
    return alerts


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ledger", default="data/ledger.jsonl")
    p.add_argument("--history", default="data/kpi_history.jsonl")
    p.add_argument("--alerts", default="data/alerts.json")
    a = p.parse_args()
    from everred import read_ledger, snapshot

    events = read_ledger(pathlib.Path(a.ledger))
    pulse = history_record(snapshot(events), events)
    print("KPI history:", append_history(pathlib.Path(a.history), pulse))
    alerts = recurrence_alerts(events)
    pathlib.Path(a.alerts).write_text(
        json.dumps({"schema": "abacus.everred.alerts.v1", "alerts": alerts}, indent=2)
        + "\n"
    )
    print("Recurrence alerts:", len(alerts), "notification transport not configured")


if __name__ == "__main__":
    main()
