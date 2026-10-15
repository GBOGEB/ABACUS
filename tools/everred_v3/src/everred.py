#!/usr/bin/env python3
"""EVERRED v3 evidence ledger: append-only, integrity-checked, fail closed.
No external dependencies. Historical import is not an authorization mechanism.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import pathlib
import re
import tempfile
from typing import Any

from metrics import compute_metrics

SCHEMA = "abacus.everred.event.v3"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ALLOWED = {
    "occurrence",
    "signature",
    "root_candidate",
    "root_confirmed",
    "lease_acquired",
    "lease_released",
    "repair",
    "verification",
    "replay",
    "security_census",
    "coverage",
    "governance",
    "runtime",
    "admission",
    "recurrence",
    "closure",
    "note",
}
ADMISSION_GATES = (
    "exact_head_ci",
    "security",
    "coverage",
    "workflow_governance",
    "branch_protection",
    "independent_review",
    "review_conversations",
)


class InvalidEvidence(ValueError):
    pass


def stable_json(obj: Any) -> str:
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def digest(obj: Any) -> str:
    return hashlib.sha256(stable_json(obj).encode("utf-8")).hexdigest()


def valid_sha(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA_RE.fullmatch(value))


def require(condition: bool, msg: str) -> None:
    if not condition:
        raise InvalidEvidence(msg)


def validate_event(e: dict) -> None:
    require(isinstance(e, dict), "event must be object")
    require(e.get("schema") == SCHEMA, "wrong schema")
    require(e.get("kind") in ALLOWED, "invalid kind")
    require(isinstance(e.get("id"), str) and len(e["id"]) > 3, "event id missing")
    require(
        isinstance(e.get("occurred_at"), str) and "T" in e["occurred_at"],
        "timestamp missing",
    )
    try:
        dt.datetime.fromisoformat(e["occurred_at"].replace("Z", "+00:00"))
    except ValueError as ex:
        raise InvalidEvidence("timestamp invalid") from ex
    require(isinstance(e.get("repo"), str) and "/" in e["repo"], "repo missing")
    require(
        isinstance(e.get("provenance"), str)
        and e["provenance"] in ("observed", "historical_source", "proposed", "manual"),
        "provenance missing",
    )
    require(isinstance(e.get("evidence"), dict), "evidence object missing")
    if e["kind"] in (
        "verification",
        "coverage",
        "security_census",
        "governance",
        "runtime",
        "admission",
    ):
        require(valid_sha(e.get("sha")), "exact 40-char SHA required for this event")
    if e["kind"] == "coverage":
        ev = e["evidence"]
        require(
            ev.get("scope") in ("focused", "broad", "changed_lines", "other"),
            "coverage scope missing",
        )
        require(
            ev.get("unit") in ("lines", "statements", "branches", "combined"),
            "coverage unit missing",
        )
        n, d = ev.get("covered"), ev.get("eligible")
        require(
            (n is None and d is None)
            or (type(n) is int and type(d) is int and 0 <= n <= d and d > 0),
            "invalid coverage denominator",
        )
        require(
            isinstance(ev.get("config_id"), str) and bool(ev["config_id"]),
            "coverage config identity missing",
        )
    if e["kind"] == "admission":
        require(isinstance(e["evidence"].get("gates"), dict), "gates required")
        require(
            all(g in e["evidence"]["gates"] for g in ADMISSION_GATES),
            "missing admission gates",
        )
        require(
            all(
                x in ("PASS", "RED", "UNKNOWN") for x in e["evidence"]["gates"].values()
            ),
            "invalid gate state",
        )
        if e["evidence"].get("decision") == "ADMIT":
            require(
                all(e["evidence"]["gates"][g] == "PASS" for g in ADMISSION_GATES),
                "fail-closed: cannot admit without all passing gates",
            )
            raise InvalidEvidence(
                "offline ledger cannot authenticate admission authority; record HOLD or use external server-side admission"
            )
    if e["kind"] == "lease_acquired":
        ev = e["evidence"]
        require(
            e.get("root_id") and ev.get("principal") and ev.get("idempotency_key"),
            "lease identity incomplete",
        )
        require(valid_sha(e.get("sha")), "lease expected head SHA missing")
        require(
            isinstance(ev.get("paths"), list) and bool(ev["paths"]),
            "lease paths missing",
        )
        for path in ev["paths"]:
            require(
                isinstance(path, str)
                and len(path) > 0
                and not path.startswith("/")
                and ".." not in path.split("/"),
                "unsafe lease path",
            )
        require(
            ev.get("authorized") is True, "mutation lease must be explicitly authorized"
        )


def overlap(a: str, b: str) -> bool:
    a = a.rstrip("/")
    b = b.rstrip("/")
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def read_ledger(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    entries = []
    prev = "GENESIS"
    ids = set()
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as ex:
            raise InvalidEvidence(f"bad JSON line {line_no}") from ex
        event = row.get("event")
        require(isinstance(event, dict), f"no event line {line_no}")
        validate_event(event)
        require(event["id"] not in ids, f"duplicate event id line {line_no}")
        ids.add(event["id"])
        require(row.get("prev_hash") == prev, f"broken hash chain line {line_no}")
        expected = digest({"event": event, "prev_hash": prev})
        require(row.get("hash") == expected, f"tampered event line {line_no}")
        prev = expected
        entries.append(event)
    validate_cross_events(entries)
    return entries


def validate_cross_events(events: list[dict]) -> None:
    active = {}
    keys = set()
    for e in events:
        ev = e["evidence"]
        rid = e.get("root_id")
        if e["kind"] == "lease_acquired":
            key = ev["idempotency_key"]
            require(key not in keys, "duplicate idempotency key")
            keys.add(key)
            for lease in active.values():
                if e["repo"] == lease["repo"] and any(
                    overlap(a, b) for a in ev["paths"] for b in lease["paths"]
                ):
                    raise InvalidEvidence("overlapping canonical path leases")
            require(rid not in active, "duplicate active owner for root")
            active[rid] = {"repo": e["repo"], "paths": ev["paths"], "event_id": e["id"]}
        if e["kind"] == "lease_released":
            require(rid in active, "lease release without active lease")
            require(
                ev.get("acquired_event_id") == active[rid]["event_id"],
                "lease release mismatch",
            )
            del active[rid]


def _append_unlocked(path: pathlib.Path, event: dict) -> dict:
    validate_event(event)
    previous = read_ledger(path)
    require(event["id"] not in {x["id"] for x in previous}, "duplicate event id")
    validate_cross_events(previous + [event])
    prev_hash = "GENESIS"
    if path.exists():
        lines = [x for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
        if lines:
            prev_hash = json.loads(lines[-1])["hash"]
    row = {
        "event": event,
        "prev_hash": prev_hash,
        "hash": digest({"event": event, "prev_hash": prev_hash}),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as out:
        out.write(stable_json(row) + "\n")
    return row


def append_event(path: pathlib.Path, event: dict) -> dict:
    # Local POSIX lock serializes concurrent workers; distributed jobs additionally
    # require an external branch/lease CAS on the authoritative service.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(path.suffix + ".lock").open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            return _append_unlocked(path, event)
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def append_events_batch(path: pathlib.Path, events: list[dict]) -> int:
    """All-or-nothing batch append under one POSIX lock, no partially accepted run.

    Existing bytes are retained verbatim; only a complete verified successor
    hash chain is atomically published. Requires a single shared POSIX volume.
    """
    require(isinstance(events, list) and bool(events), "empty native event batch")
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with lock_path.open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            previous = read_ledger(path)
            ids = {e["id"] for e in previous}
            require(
                not any(e.get("id") in ids for e in events),
                "native batch contains existing event ID",
            )
            require(
                len({e.get("id") for e in events}) == len(events),
                "native batch contains duplicate event ID",
            )
            for e in events:
                validate_event(e)
            validate_cross_events(previous + events)
            original = path.read_bytes() if path.exists() else b""
            require(
                not original or original.endswith(b"\n"),
                "ledger has incomplete final line",
            )
            prev = "GENESIS"
            if original:
                prev = json.loads(original.splitlines()[-1])["hash"]
            added = []
            for e in events:
                row = {
                    "event": e,
                    "prev_hash": prev,
                    "hash": digest({"event": e, "prev_hash": prev}),
                }
                added.append(stable_json(row) + "\n")
                prev = row["hash"]
            fd, name = tempfile.mkstemp(prefix=".everred-ledger-", dir=path.parent)
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(original)
                    f.write("".join(added).encode("utf-8"))
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(name, path)
            finally:
                if os.path.exists(name):
                    os.unlink(name)
            return len(events)
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def coverage_rate(e: dict) -> float | None:
    v = e["evidence"]
    n = v.get("covered")
    d = v.get("eligible")
    return (
        round(100 * n / d, 2) if type(n) is int and type(d) is int and d > 0 else None
    )


def snapshot(events: list[dict]) -> dict:
    roots = {}
    occurrences = []
    coverage = []
    security = []
    admissions = []
    other = []
    for e in events:
        kind = e["kind"]
        rid = e.get("root_id")
        if kind in ("root_candidate", "root_confirmed") and rid:
            roots[rid] = {
                "id": rid,
                "title": e["evidence"].get("title", rid),
                "state": "CONFIRMED" if kind == "root_confirmed" else "CANDIDATE",
                "owner": e["evidence"].get("owner", "UNASSIGNED"),
                "cause": e["evidence"].get("cause", "UNKNOWN"),
                "applicable_consumers": e["evidence"].get("applicable_consumers"),
                "source": e["evidence"].get("url"),
                "provenance": e["provenance"],
            }
        elif kind == "occurrence":
            occurrences.append(e)
        elif kind == "coverage":
            coverage.append({**e, "rate": coverage_rate(e)})
        elif kind == "security_census":
            security.append(e)
        elif kind == "admission":
            admissions.append(e)
        else:
            other.append(e)
    base_sha = next(
        (e["sha"] for e in coverage if e["evidence"].get("scope") == "broad"), None
    )

    # Only infer exact data from recorded receipts. Never interpret raw scanner count as burndown.
    items = [
        {
            "name": "confirmed_roots",
            "value": sum(1 for r in roots.values() if r["state"] == "CONFIRMED"),
            "denominator": None,
            "status": "OBSERVED" if roots else "UNKNOWN",
            "scope": "ledger",
        }
    ]
    by_scope = {}
    for e in coverage:
        key = e["evidence"]["scope"] + ":" + e["evidence"]["unit"]
        by_scope[key] = {
            "value": e["rate"],
            "covered": e["evidence"].get("covered"),
            "eligible": e["evidence"].get("eligible"),
            "sha": e["sha"],
            "config_id": e["evidence"]["config_id"],
            "run_id": e["evidence"].get("run_id"),
            "reported_combined": e["evidence"].get("reported_combined"),
            "provenance": e["provenance"],
        }
    return {
        "schema": "abacus.everred.snapshot.v3",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "mode": "HISTORICAL_EVIDENCE_NOT_LIVE",
        "repository": "GBOGEB/ABACUS",
        "base_sha": base_sha,
        "events_count": len(events),
        "root_count": len(roots),
        "roots": list(roots.values()),
        "metrics_derived": compute_metrics(events, roots),
        "occurrences": occurrences,
        "coverage_scopes": by_scope,
        "security_scans": security,
        "admissions": admissions,
        "other_events": other,
        "kpis": items,
        "kpi_unknowns": [
            "occurrence_amplification",
            "root_fanout",
            "recurrence_rate",
            "consumer_replay_coverage",
            "root_lead_time",
            "queue_wait_time",
            "security_fingerprint_burndown",
            "governed_admission_ratio",
            "ldab_active_sessions",
            "rhel_verified_jobs",
            "cross_pr_replay_rate",
        ],
        "disclaimer": "Imported records are historical evidence only. Snapshot does not confer merge or security authority.",
    }


def main():
    p = argparse.ArgumentParser(
        description="EVERRED append-only evidence ingestion and snapshot builder"
    )
    p.add_argument("command", choices=["verify", "append", "snapshot"])
    p.add_argument("--ledger", default="data/ledger.jsonl")
    p.add_argument("--event")
    p.add_argument("--output", default="data/snapshot.json")
    a = p.parse_args()
    ledger = pathlib.Path(a.ledger)
    if a.command == "append":
        require(a.event is not None, "--event required")
        e = json.loads(pathlib.Path(a.event).read_text(encoding="utf-8"))
        print(stable_json(append_event(ledger, e)))
    elif a.command == "verify":
        print(f"VALID {len(read_ledger(ledger))} events")
    else:
        s = snapshot(read_ledger(ledger))
        pathlib.Path(a.output).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.output).write_text(
            json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Snapshot {a.output}: {s['events_count']} events")


if __name__ == "__main__":
    main()
