#!/usr/bin/env python3
"""MIP V3 read-only temporal pulse and frozen N+2 forecast diagnostics.

This parser cannot authenticate native GitHub evidence. It never dispatches,
promotes coverage, approves, changes admission rules, or merges.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path

SCHEMA = "codepurple.mip.temporal.v3"
FORECAST_SCHEMA = "codepurple.mip.forecast.v3"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")


def need(value, message):
    if not value:
        raise ValueError(message)


def integer(value, name, minimum=0):
    need(type(value) is int and value >= minimum, name + " must be integer")
    return value


def quantity(value, name):
    need(
        type(value) in (int, float) and math.isfinite(value) and value >= 0,
        name + " must be finite nonnegative",
    )
    return float(value)


def timestamp(value):
    need(isinstance(value, str) and value.endswith("Z"), "UTC time required")
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid UTC timestamp") from exc
    need(date.utcoffset().total_seconds() == 0, "UTC offset required")
    return date


def signed_quantity(value, name):
    need(type(value) in (int, float) and math.isfinite(value), name + " must be finite")
    return float(value)


def digest(value, kind=SHA64):
    need(isinstance(value, str) and bool(kind.fullmatch(value)), "invalid digest")
    return value


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def read(path):
    return json.loads(
        Path(path).read_text(encoding="utf-8"),
        object_pairs_hook=unique_pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError("invalid JSON constant")
        ),
    )


def safe_path(value):
    return (
        isinstance(value, str)
        and bool(value)
        and not value.startswith("/")
        and "\\" not in value
        and ":" not in value
        and all(x not in ("", ".", "..") for x in value.split("/"))
    )


def disjoint(workers):
    need(isinstance(workers, list), "worker list required")
    owners, claimed = set(), []
    durations = []
    for worker in workers:
        need(isinstance(worker, dict), "worker object required")
        name = worker.get("owner")
        need(
            isinstance(name, str) and bool(name) and name not in owners,
            "worker owner collision",
        )
        owners.add(name)
        paths = worker.get("paths")
        need(isinstance(paths, list) and bool(paths), "worker paths missing")
        for path in paths:
            need(safe_path(path), "unsafe worker path")
            need(
                not any(
                    path == held
                    or path.startswith(held + "/")
                    or held.startswith(path + "/")
                    for held in claimed
                ),
                "overlapping worker lease",
            )
            claimed.append(path)
        for key in ("queue_seconds", "execution_seconds", "review_seconds"):
            value = worker.get(key)
            if value is not None:
                quantity(value, key)
        if worker.get("execution_seconds") is not None:
            durations.append(float(worker["execution_seconds"]))
    return {"worker_count": len(workers), "measured_run_seconds": sum(durations)}


def validate_observation(row):
    need(isinstance(row, dict) and row.get("schema") == SCHEMA, "pulse schema mismatch")
    need(row.get("repository") == "GBOGEB/ABACUS", "repository mismatch")
    integer(row.get("pulse_index"), "pulse_index")
    digest(row.get("head_sha"), SHA40)
    for key in ("cohort_sha256", "instrumentation_sha256", "artifact_sha256"):
        digest(row.get(key))
    observed = timestamp(row.get("observed_at"))
    coverage = row.get("coverage")
    need(isinstance(coverage, dict), "coverage required")
    for family in ("statements", "branches"):
        pair = coverage.get(family)
        need(isinstance(pair, dict), family + " pair required")
        covered = integer(pair.get("covered"), "covered " + family)
        eligible = integer(pair.get("eligible"), "eligible " + family)
        need(covered <= eligible, "covered exceeds eligible")
    native = row.get("native")
    need(isinstance(native, dict), "native identity required")
    for key in ("run_id", "job_id", "attempt"):
        integer(native.get(key), key, minimum=1)
    need(native.get("terminal") is True, "nonterminal native pulse")
    need(native.get("conclusion") in ("success", "failure"), "native conclusion")
    roots = row.get("root_ids_open")
    if roots is not None:
        need(isinstance(roots, list) and len(set(roots)) == len(roots), "root list")
        need(all(isinstance(r, str) and bool(r) for r in roots), "root identities")
        digest(row.get("root_cohort_sha256"))
    disposition = row.get("disposition")
    if disposition is not None:
        need(isinstance(disposition, dict), "disposition shape")
        candidates = integer(disposition.get("candidates"), "candidates")
        resolved = integer(disposition.get("resolved"), "resolved")
        unknown = integer(disposition.get("unknown"), "unknown")
        need(resolved + unknown == candidates, "candidate cohort mismatch")
        digest(row.get("triage_cohort_sha256"))
    gov = row.get("governance")
    need(isinstance(gov, dict), "governance object missing")
    need(type(gov.get("merged_observed")) is bool, "merge observation required")
    need(
        gov.get("effective_controls_verified") in (True, False, None),
        "controls validation required",
    )
    need(gov.get("security_waiver") is False, "security waiver forbidden")
    worker = disjoint(row.get("workers", []))
    return {
        "pulse": row["pulse_index"],
        "at": observed,
        "covered": sum(coverage[k]["covered"] for k in ("statements", "branches")),
        "eligible": sum(coverage[k]["eligible"] for k in ("statements", "branches")),
        "head": row["head_sha"],
        "native_success": native["conclusion"] == "success",
        "merged_without_proof": (
            gov["merged_observed"] and gov["effective_controls_verified"] is not True
        ),
        "workers": worker,
    }


def comparable(a, b):
    return (
        a["cohort_sha256"] == b["cohort_sha256"]
        and a["instrumentation_sha256"] == b["instrumentation_sha256"]
        and all(
            a["coverage"][key]["eligible"] == b["coverage"][key]["eligible"]
            for key in ("statements", "branches")
        )
    )


def validate_forecast(item, by_index):
    need(
        isinstance(item, dict) and item.get("schema") == FORECAST_SCHEMA,
        "forecast schema",
    )
    issued_after = integer(item.get("issued_after"), "issued_after")
    target = integer(item.get("target_index"), "target_index")
    need(target in (issued_after + 1, issued_after + 2), "forecast outside N+2")
    need(issued_after in by_index, "forecast issuer absent")
    issued = timestamp(item.get("issued_at"))
    need(
        issued >= timestamp(by_index[issued_after]["observed_at"]),
        "forecast predates issuer",
    )
    if target in by_index:
        need(
            issued < timestamp(by_index[target]["observed_at"]),
            "hindsight forecast not allowed",
        )
    lower = signed_quantity(item.get("gain_lower"), "gain_lower")
    upper = signed_quantity(item.get("gain_upper"), "gain_upper")
    need(lower <= upper, "inverted interval")
    digest(item.get("issuer_head_sha"), SHA40)
    need(
        item["issuer_head_sha"] == by_index[issued_after]["head_sha"],
        "issuer head drift",
    )
    need(
        isinstance(item.get("rule_id"), str) and bool(item["rule_id"]),
        "forecast rule missing",
    )
    return item


def nearest_rank_95(values):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def rollup(observations, forecasts=None):
    need(isinstance(observations, list) and bool(observations), "observations required")
    checked = [validate_observation(row) for row in observations]
    by_index = {}
    seen_heads, seen_jobs, seen_artifacts = set(), set(), set()
    for row, chk in zip(observations, checked):
        index = chk["pulse"]
        need(index not in by_index, "repeated pulse index")
        by_index[index] = row
        need(chk["head"] not in seen_heads, "reused head is a poll, not new pulse")
        native = row["native"]
        identity = (native["run_id"], native["attempt"])
        need(identity not in seen_jobs, "replayed native run/job/attempt")
        need(row["artifact_sha256"] not in seen_artifacts, "reused evidence artifact")
        seen_heads.add(chk["head"])
        seen_jobs.add(identity)
        seen_artifacts.add(row["artifact_sha256"])
    indexes = [item["pulse"] for item in checked]
    need(
        all(y == x + 1 for x, y in zip(indexes, indexes[1:])),
        "non-consecutive pulse states",
    )
    need(
        all(y["at"] > x["at"] for x, y in zip(checked, checked[1:])),
        "nonmonotone observation times",
    )
    transitions = []
    for a, b, av, bv in zip(observations, observations[1:], checked, checked[1:]):
        matched = comparable(a, b) and av["native_success"] and bv["native_success"]
        delta = bv["covered"] - av["covered"] if matched else None
        root_delta = None
        if (
            a.get("root_ids_open") is not None
            and b.get("root_ids_open") is not None
            and a.get("root_cohort_sha256") == b.get("root_cohort_sha256")
        ):
            root_delta = len(a["root_ids_open"]) - len(b["root_ids_open"])
        disposition_delta = None
        if (
            a.get("disposition") is not None
            and b.get("disposition") is not None
            and a.get("triage_cohort_sha256") == b.get("triage_cohort_sha256")
        ):
            disposition_delta = (
                b["disposition"]["resolved"] - a["disposition"]["resolved"]
            )
        transitions.append(
            {
                "from_pulse": av["pulse"],
                "to_pulse": bv["pulse"],
                "matched": matched,
                "covered_delta": delta,
                "gain_pp": (
                    round(100 * delta / bv["eligible"], 6)
                    if matched and bv["eligible"]
                    else None
                ),
                "root_closed_net": root_delta,
                "dispositions_delta": disposition_delta,
            }
        )
    forecasts = [] if forecasts is None else forecasts
    need(isinstance(forecasts, list), "forecasts required as list")
    scored = []
    keys = set()
    for item in forecasts:
        row = validate_forecast(item, by_index)
        key = (row["issued_after"], row["target_index"], row["rule_id"])
        need(key not in keys, "duplicate immutable forecast")
        keys.add(key)
        steps = [
            x
            for x in transitions
            if row["issued_after"] < x["to_pulse"] <= row["target_index"]
        ]
        eligible = len(steps) == row["target_index"] - row["issued_after"] and all(
            x["covered_delta"] is not None for x in steps
        )
        delta = sum(x["covered_delta"] for x in steps) if eligible else None
        scored.append(
            {
                "issued_after": row["issued_after"],
                "target_index": row["target_index"],
                "rule_id": row["rule_id"],
                "actual_covered_delta": delta,
                "absolute_error": (
                    None
                    if delta is None
                    else round(
                        abs(delta - (row["gain_lower"] + row["gain_upper"]) / 2), 6
                    )
                ),
                "interval_hit": (
                    None
                    if delta is None
                    else row["gain_lower"] <= delta <= row["gain_upper"]
                ),
            }
        )
    regression = any(
        t["covered_delta"] is not None and t["covered_delta"] < 0 for t in transitions
    )
    plateau = len(transitions) >= 3 and all(
        t["matched"]
        and t["covered_delta"] == 0
        and t["root_closed_net"] is not None
        and t["root_closed_net"] <= 0
        and t["dispositions_delta"] is not None
        and t["dispositions_delta"] <= 0
        for t in transitions[-3:]
    )
    merged_unproved = any(row["merged_without_proof"] for row in checked)
    control = (
        "ESCALATE_MERGE_WITHOUT_PROOF"
        if merged_unproved
        else (
            "REPAIR_COVERAGE_REGRESSION"
            if regression
            else (
                "STOP_LOCAL_PLATEAU"
                if plateau
                else (
                    "NEED_COMPARABLE_NATIVE_EVIDENCE"
                    if not transitions or not transitions[-1]["matched"]
                    else "CONTINUE_OR_REALLOCATE"
                )
            )
        )
    )
    queue = [
        float(w["queue_seconds"])
        for row in observations
        for w in row.get("workers", [])
        if w.get("queue_seconds") is not None
    ]
    execute = [
        float(w["execution_seconds"])
        for row in observations
        for w in row.get("workers", [])
        if w.get("execution_seconds") is not None
    ]
    return {
        "schema": "codepurple.mip.temporal-rollup.v3",
        "pulse_count": len(checked),
        "forecast_ledger_sha256": hashlib.sha256(
            json.dumps(
                forecasts, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode("ascii")
        ).hexdigest(),
        "state_clock": indexes,
        "transitions": transitions,
        "frozen_forecast_scores": scored,
        "p95_queue_seconds": nearest_rank_95(queue),
        "p95_execution_seconds": nearest_rank_95(execute),
        "queue_sample_count": len(queue),
        "execution_sample_count": len(execute),
        "governance_red": merged_unproved,
        "control": control,
        "dispatch_authorized": False,
        "merge_admission": "HOLD",
        "formal_coverage_credit": False,
        "authority_transfer": False,
        "claim": "DESCRIPTIVE_ONLY_EXTERNAL_RECEIPT_AUTHENTICATION_REQUIRED",
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--forecasts", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    observations = read(args.observations)
    forecasts = read(args.forecasts) if args.forecasts else []
    out = rollup(observations, forecasts)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(out, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
