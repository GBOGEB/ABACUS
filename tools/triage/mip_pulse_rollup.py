#!/usr/bin/env python3
"""Read-only ABACUS floating-code MIP pulse telemetry (no merge/dispatch authority).

Inputs are source-owned JSON receipts. Numbers lacking qualified, matching
populations remain UNKNOWN; coverage gain is never inferred from deletion.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime
from pathlib import Path

SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")
SCHEMA = "codepurple.mip.floating-pulse.v1"


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def number(value, name):
    require(type(value) is int and value >= 0, "invalid " + name)
    return value


def read_pulse(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    require(isinstance(data, dict) and data.get("schema") == SCHEMA, "pulse schema")
    require(data.get("repository") == "GBOGEB/ABACUS", "repository mismatch")
    require(isinstance(data.get("head_sha"), str) and SHA40.fullmatch(data["head_sha"]), "head SHA")
    for key in ("population_sha256", "instrumentation_sha256"):
        require(isinstance(data.get(key), str) and SHA64.fullmatch(data[key]), key)
    when = data.get("observed_at")
    require(isinstance(when, str) and when.endswith("Z"), "UTC observation required")
    datetime.fromisoformat(when.replace("Z", "+00:00"))
    cov = data.get("coverage")
    require(isinstance(cov, dict), "coverage missing")
    for key in ("statements", "branches"):
        row = cov.get(key)
        require(isinstance(row, dict), "coverage family missing: " + key)
        eligible = number(row.get("eligible"), key + " eligible")
        covered = number(row.get("covered"), key + " covered")
        require(covered <= eligible, "covered exceeds eligible")
    triage = data.get("triage")
    if triage is not None:
        require(isinstance(triage, dict), "triage shape")
        keys = ("candidates", "linked", "orphan", "other_disposed", "unknown")
        values = [number(triage.get(k), "triage " + k) for k in keys]
        require(sum(values[1:]) == values[0], "triage candidates do not reconcile")
    roots = data.get("root_reds_open")
    if roots is not None:
        number(roots, "root reds")
    workers = data.get("workers", [])
    require(isinstance(workers, list), "workers must be list")
    owners = set()
    claimed = set()
    for w in workers:
        require(isinstance(w, dict) and isinstance(w.get("owner"), str) and w["owner"], "worker owner")
        require(w["owner"] not in owners, "duplicate worker owner")
        owners.add(w["owner"])
        paths = w.get("paths")
        require(isinstance(paths, list) and len(paths) > 0, "missing worker paths")
        for item in paths:
            require(
                isinstance(item, str) and item and not item.startswith("/")
                and "\\" not in item and ":" not in item
                and all(part not in ("", ".", "..") for part in item.split("/")),
                "unsafe path claim"
            )
            require(
                not any(
                    item == held or item.startswith(held + "/")
                    or held.startswith(item + "/")
                    for held in claimed
                ), "overlapping worker path: " + item
            )
            claimed.add(item)
        for metric in ("queue_seconds", "execution_seconds"):
            if w.get(metric) is not None:
                require(isinstance(w[metric], (int, float)) and not isinstance(w[metric], bool) and math.isfinite(w[metric]) and w[metric] >= 0, "invalid worker latency")
    gov = data.get("governance")
    require(isinstance(gov, dict) and gov.get("merge_admission") in ("HOLD", "PASS"), "governance missing")
    require(gov.get("security_waiver") is False, "security waiver not supported")
    return data


def percent(numerator, denominator):
    return round(100 * numerator / denominator, 6) if denominator else None


def p95(values):
    values = sorted(values)
    return values[math.ceil(0.95 * len(values)) - 1] if values else None


def snapshot(p):
    cov = p["coverage"]
    covered = sum(cov[k]["covered"] for k in ("statements", "branches"))
    eligible = sum(cov[k]["eligible"] for k in ("statements", "branches"))
    workers = p.get("workers", [])
    triage = p.get("triage")
    result = {
        "head_sha": p["head_sha"],
        "observed_at": p["observed_at"],
        "covered": covered, "eligible": eligible,
        "missing": eligible - covered, "combined_percent": percent(covered, eligible),
        "statement_percent": percent(cov["statements"]["covered"], cov["statements"]["eligible"]),
        "branch_percent": percent(cov["branches"]["covered"], cov["branches"]["eligible"]),
        "triage": triage, "root_reds_open": p.get("root_reds_open"),
        "disjoint_workers": len(workers),
        "p95_queue_seconds": p95([w["queue_seconds"] for w in workers if w.get("queue_seconds") is not None]),
        "p95_execution_seconds": p95([w["execution_seconds"] for w in workers if w.get("execution_seconds") is not None]),
        "merge_admission": p["governance"]["merge_admission"],
    }
    return result


def transition(a, b):
    x, y = snapshot(a), snapshot(b)
    same = (
        a["repository"] == b["repository"]
        and a["population_sha256"] == b["population_sha256"]
        and a["instrumentation_sha256"] == b["instrumentation_sha256"]
        and x["eligible"] == y["eligible"]
        and x["eligible"] > 0
        and all(
            a["coverage"][k]["eligible"] == b["coverage"][k]["eligible"]
            for k in ("statements", "branches")
        )
    )
    item = {
        "from_head": a["head_sha"], "to_head": b["head_sha"],
        "population_comparable": same,
        "coverage_gain_pp": None,
        "statement_gain_pp": None,
        "branch_gain_pp": None,
        "newly_covered_opportunities": None,
        "triage_resolved_delta": None,
        "root_reds_closed_net": None,
        "reason": "MATCHED" if same else "POPULATION_OR_INSTRUMENTOR_DRIFT",
    }
    if same:
        item["newly_covered_opportunities"] = y["covered"] - x["covered"]
        item["coverage_gain_pp"] = round(y["combined_percent"] - x["combined_percent"], 6)
        item["statement_gain_pp"] = round(
            y["statement_percent"] - x["statement_percent"], 6
        ) if x["statement_percent"] is not None else None
        item["branch_gain_pp"] = round(
            y["branch_percent"] - x["branch_percent"], 6
        ) if x["branch_percent"] is not None else None
    if a.get("triage") and b.get("triage") and a["population_sha256"] == b["population_sha256"]:
        def resolved(t):
            return t["linked"] + t["orphan"] + t["other_disposed"]
        item["triage_resolved_delta"] = resolved(b["triage"]) - resolved(a["triage"])
    if a.get("root_reds_open") is not None and b.get("root_reds_open") is not None and a.get("root_cohort_id") == b.get("root_cohort_id") and a.get("root_cohort_id"):
        item["root_reds_closed_net"] = a["root_reds_open"] - b["root_reds_open"]
    return item


def rollup(pulses):
    require(isinstance(pulses, list) and len(pulses) > 0, "no pulses")
    dates = [datetime.fromisoformat(p["observed_at"].replace("Z", "+00:00")) for p in pulses]
    require(all(a < b for a, b in zip(dates, dates[1:])), "pulses not strictly chronological")
    snaps = [snapshot(p) for p in pulses]
    moves = [transition(a, b) for a, b in zip(pulses, pulses[1:])]
    last = snaps[-1]
    matched = len(moves) >= 3 and all(
        m["population_comparable"] for m in moves[-3:]
    )
    regression = bool(moves and moves[-1]["population_comparable"] and any(
        moves[-1][key] is not None and moves[-1][key] < 0
        for key in ("statement_gain_pp", "branch_gain_pp")
    ))
    plateau = matched and all(
        m["statement_gain_pp"] is not None
        and m["branch_gain_pp"] is not None
        and 0 <= m["statement_gain_pp"] <= 0.05
        and 0 <= m["branch_gain_pp"] <= 0.05
        and m["triage_resolved_delta"] is not None
        and m["triage_resolved_delta"] <= 0
        and m["root_reds_closed_net"] is not None
        and m["root_reds_closed_net"] <= 0
        for m in moves[-3:]
    )
    saturated = (
        last["statement_percent"] == 100
        and last["branch_percent"] == 100
    )
    control = (
        "RESTART_COVERAGE_REGRESSION" if regression
        else "QUIET_WATCH_CANDIDATE" if plateau and saturated
        else "RERANK_UNCOVERED" if plateau
        else "MORE_COMPARABLE_PULSES_REQUIRED" if not matched
        else "CONTINUE_MEASURED_CONVERGENCE"
    )
    return {
        "schema": "codepurple.mip.floating-rollup.v1",
        "pulse_count": len(snaps),
        "latest": last, "history": snaps, "transitions": moves,
        "control": control,
        "phase_two_authorized": False,
        "source_scope_saturated": saturated,
        "release_ready": False,
        "formal_coverage_credit": False,
        "note": "Read-only descriptive telemetry. Native receipts, source population identity and governed admission require independent validation.",
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("pulses", nargs="+", help="chronologically ordered pulse JSON paths")
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)
    output = rollup([read_pulse(p) for p in args.pulses])
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(output, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
