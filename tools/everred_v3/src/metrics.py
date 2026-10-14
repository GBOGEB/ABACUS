"""Provable EVERRED KPIs. Missing scope, source identity or denominator stays UNKNOWN."""

from __future__ import annotations

import datetime as dt
from collections import defaultdict


def rate(n, d):
    return (
        round(100 * n / d, 2)
        if type(n) is int and type(d) is int and d > 0 and 0 <= n <= d
        else None
    )


def comparable_security(before: dict, after: dict) -> dict | None:
    """Require exact scanner/config/version/scope and source-bound fingerprint sets."""
    a, b = before.get("evidence", {}), after.get("evidence", {})
    required = (
        "scanner",
        "scope",
        "config_digest",
        "scanner_version",
        "rule_profile",
        "normalization_version",
    )
    if not before.get("sha") or not after.get("sha") or before["sha"] == after["sha"]:
        return None
    if any(
        not isinstance(a.get(k), str)
        or not a[k]
        or a[k] == "UNKNOWN"
        or a[k] != b.get(k)
        for k in required
    ):
        return None
    x, y = a.get("fingerprints"), b.get("fingerprints")
    if (
        not isinstance(x, list)
        or not isinstance(y, list)
        or not all(isinstance(t, str) and t for t in x + y)
    ):
        return None
    if len(x) != len(set(x)) or len(y) != len(set(y)):
        return None  # duplicate raw events are not a normalized finding census
    opened = set(y) - set(x)
    resolved = set(x) - set(y)
    return {
        "scanner": a["scanner"],
        "config_digest": a["config_digest"],
        "before_sha": before["sha"],
        "after_sha": after["sha"],
        "before": len(x),
        "after": len(y),
        "opened": len(opened),
        "resolved": len(resolved),
        "persisting": len(set(x) & set(y)),
        "net_change": len(opened) - len(resolved),
        "opened_ids": sorted(opened),
        "resolved_ids": sorted(resolved),
    }


def comparable_coverage(before: dict, after: dict) -> dict | None:
    a, b = before.get("evidence", {}), after.get("evidence", {})
    for k in (
        "scope",
        "unit",
        "config_id",
        "test_selection",
        "exclusions",
        "tool_version",
    ):
        if not isinstance(a.get(k), str) or a[k] in ("", "UNKNOWN") or a[k] != b.get(k):
            return None
    if (
        before.get("sha") == after.get("sha")
        or not before.get("sha")
        or not after.get("sha")
    ):
        return None
    r1, r2 = rate(a.get("covered"), a.get("eligible")), rate(
        b.get("covered"), b.get("eligible")
    )
    if r1 is None or r2 is None:
        return None
    return {
        "scope": a["scope"],
        "unit": a["unit"],
        "before_sha": before["sha"],
        "after_sha": after["sha"],
        "before_rate": r1,
        "after_rate": r2,
        "delta_percentage_points": round(r2 - r1, 2),
        "before": {"covered": a["covered"], "eligible": a["eligible"]},
        "after": {"covered": b["covered"], "eligible": b["eligible"]},
    }


def compute_metrics(events: list[dict], roots: dict) -> dict:
    scans = [e for e in events if e["kind"] == "security_census"]
    covers = [e for e in events if e["kind"] == "coverage"]
    burndown = []
    deltas = []
    for group, compare, out in (
        (scans, comparable_security, burndown),
        (covers, comparable_coverage, deltas),
    ):
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                if x := compare(group[i], group[j]):
                    out.append(x)
    confirmed = {r for r, d in roots.items() if d["state"] == "CONFIRMED"}
    occurrences = [
        e for e in events if e["kind"] == "occurrence" and e.get("root_id") in confirmed
    ]
    amp = round(len(occurrences) / len(confirmed), 2) if confirmed else None
    consumers = set()
    passed = set()
    for rid, d in roots.items():
        if rid not in confirmed:
            continue
        for c in d.get("applicable_consumers") or []:
            consumers.add((rid, c))
    for e in events:
        if (
            e["kind"] == "replay"
            and e.get("root_id") in confirmed
            and e.get("evidence", {}).get("status") == "PASS"
            and e.get("sha")
        ):
            passed.add((e["root_id"], e["evidence"].get("consumer_id")))
    replay = rate(len(consumers & passed), len(consumers)) if consumers else None
    closed = {
        e["root_id"]
        for e in events
        if e["kind"] == "closure"
        and e.get("root_id")
        and e.get("evidence", {}).get("state") == "CLOSED"
    }
    reopened = {
        e["root_id"]
        for e in events
        if e["kind"] == "recurrence" and e.get("root_id") in closed
    }
    rec = rate(len(reopened), len(closed)) if closed else None
    waits = []
    for e in events:
        if e["kind"] != "runtime":
            continue
        v = e["evidence"]
        t0 = v.get("dispatched_at")
        t1 = v.get("started_at")
        if not isinstance(t0, str) or not isinstance(t1, str):
            continue
        try:
            t0 = dt.datetime.fromisoformat(t0.replace("Z", "+00:00"))
            t1 = dt.datetime.fromisoformat(t1.replace("Z", "+00:00"))
            s = (t1 - t0).total_seconds()
            if s >= 0:
                waits.append(s)
        except (ValueError, TypeError):
            continue
    return {
        "occurrence_amplification": amp,
        "consumer_replay_coverage_pct": replay,
        "recurrence_rate_pct": rec,
        "queue_wait_mean_seconds": round(sum(waits) / len(waits), 1) if waits else None,
        "security_comparable_pairs": burndown,
        "coverage_comparable_pairs": deltas,
        "known_consumer_denominator": len(consumers) if consumers else None,
        "queue_wait_samples": len(waits),
        "method": "Only complete comparable evidence produces measured KPIs; absent denominator is null.",
    }
