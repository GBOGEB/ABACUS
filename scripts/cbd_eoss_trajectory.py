"""Governed EOSS N+3 trajectory: matched coverage, descriptive stability and clocks.

No CI dispatch, cache installation, causal-root promotion or merge admission.
Distinguishes test-selection expansion from changed source/instrumentation scopes.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime
from statistics import median

SOURCE_SCHEMA = "code-purple.eoss.trajectory-input.v1"
OUTPUT_SCHEMA = "code-purple.eoss.trajectory-output.v1"
WAVES = ("N5", "W7", "W8", "W9")
HEX40 = re.compile(r"[a-f0-9]{40}\Z")
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
TOLERANCE_PP = 0.5


def need(predicate, reason):
    if not predicate:
        raise ValueError(reason)


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def number(value, minimum=0):
    return type(value) in (float, int) and math.isfinite(value) and value >= minimum


def hex_digest(value, expression, reason):
    need(isinstance(value, str) and expression.fullmatch(value), reason)
    return value


def timestamp(value):
    need(isinstance(value, str) and value.endswith("Z"), "UTC Z observation required")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid UTC observation calendar date") from exc
    need(
        stamp.utcoffset() is not None and stamp.utcoffset().total_seconds() == 0,
        "UTC timestamp required",
    )
    return stamp


def coverage(data):
    need(isinstance(data, dict), "coverage proof missing")
    for key in ("source_content_sha256", "scope_sha256", "config_sha256"):
        hex_digest(data.get(key), HEX64, "coverage identity " + key)
    need(
        isinstance(data.get("tool_version"), str) and data["tool_version"].strip(),
        "coverage tool identity missing",
    )
    for family in ("statements", "branches"):
        eligible = data.get("eligible_" + family)
        hit = data.get("covered_" + family)
        need(
            integer(eligible, 1) and integer(hit) and hit <= eligible,
            "invalid " + family + " coverage numerator or denominator",
        )
    return data


def observation(item, expected_wave):
    need(
        isinstance(item, dict) and item.get("wave") == expected_wave,
        "wave order or name mismatch",
    )
    hex_digest(item.get("head_sha"), HEX40, "invalid bound head SHA")
    stamp = timestamp(item.get("observed_at"))
    need(
        item.get("evidence_tier") == "LOCAL_REPRODUCIBILITY",
        "scope cannot be promoted into native admission",
    )
    need(
        item.get("authority")
        == {"admission": "HOLD", "security_waiver": False, "authority_transfer": False},
        "authority must remain HOLD",
    )
    tests = item.get("tests")
    need(isinstance(tests, dict), "test denominator missing")
    for key in ("collected", "passed", "failed", "skipped"):
        need(integer(tests.get(key)), "invalid test count " + key)
    need(
        tests["collected"] == tests["passed"] + tests["failed"] + tests["skipped"],
        "collected test denominator mismatch",
    )
    c = coverage(item.get("coverage"))
    clock = item.get("clock")
    if clock is not None:
        need(
            isinstance(clock, dict) and clock.get("basis") == "LOCAL_MONOTONIC_WALL",
            "unqualified timing basis",
        )
        hex_digest(clock.get("workload_sha256"), HEX64, "clock workload key missing")
        hex_digest(clock.get("host_sha256"), HEX64, "clock host key missing")
        samples = clock.get("duration_ms")
        need(
            isinstance(samples, list)
            and len(samples) >= 3
            and all(number(v, 0.000001) for v in samples),
            "at least three positive monotonic duration samples required",
        )
    b = item.get("historical_backlog")
    need(
        isinstance(b, dict)
        and b.get("n0_total") == 253
        and integer(b.get("observed_run_ids"))
        and b["observed_run_ids"] <= 253
        and b.get("formal_roots_closed") is None,
        "historical N0/causal claim drift",
    )
    return {
        "wave": expected_wave,
        "source_sha": item["head_sha"],
        "timestamp": stamp,
        "observed_at": item["observed_at"],
        "evidence_tier": item["evidence_tier"],
        "tests": dict(tests),
        "coverage": dict(c),
        "clock": clock,
        "historical_backlog": dict(b),
    }


def coverage_pair(before, after):
    left, right = before["coverage"], after["coverage"]
    for key in (
        "source_content_sha256",
        "scope_sha256",
        "config_sha256",
        "tool_version",
        "eligible_statements",
        "eligible_branches",
    ):
        if left[key] != right[key]:
            return {
                "qualified": False,
                "reason": "changed " + key,
                "statement_delta_pp": None,
                "branch_delta_pp": None,
            }
    return {
        "qualified": True,
        "reason": "same source/scope/config/denominator",
        "statement_delta_pp": round(
            100
            * (right["covered_statements"] - left["covered_statements"])
            / left["eligible_statements"],
            6,
        ),
        "branch_delta_pp": round(
            100
            * (right["covered_branches"] - left["covered_branches"])
            / left["eligible_branches"],
            6,
        ),
    }


def classify(comparisons):
    need(len(comparisons) == 3, "requires three consecutive wave comparisons")
    if not all(x["qualified"] for x in comparisons):
        return {
            "state": "INSUFFICIENT_MATCHED_COVERAGE_PAIRS",
            "matched_pairs": sum(x["qualified"] for x in comparisons),
            "branch_second_difference_pp": None,
            "certified_convergence": False,
        }
    values = [x["branch_delta_pp"] for x in comparisons]
    lines = [x["statement_delta_pp"] for x in comparisons]
    if any(x < -TOLERANCE_PP for x in values + lines):
        state = "REGRESSION_OBSERVED"
    elif all(abs(x) <= TOLERANCE_PP for x in values + lines):
        state = "DESCRIPTIVE_STABLE_PLATEAU"
    elif any(x > TOLERANCE_PP for x in values[:1] + lines[:1]) and all(
        abs(x) <= TOLERANCE_PP for x in values[1:] + lines[1:]
    ):
        state = "APPROACHING_PLATEAU_AFTER_GAIN"
    elif values[0] < values[1] < values[2] and all(x >= 0 for x in values):
        state = "DESCRIPTIVE_ACCELERATING_BRANCH_GAINS"
    else:
        state = "CHANGING_OR_UNQUALIFIED_STABILITY"
    return {
        "state": state,
        "matched_pairs": 3,
        "branch_second_difference_pp": [
            round(values[1] - values[0], 6),
            round(values[2] - values[1], 6),
        ],
        "branch_deltas_pp": values,
        "statement_deltas_pp": lines,
        "plateau_tolerance_pp": TOLERANCE_PP,
        "certified_convergence": False,
    }


def clock_comparison(before, after):
    left, right = before["clock"], after["clock"]
    if left is None or right is None:
        return {
            "qualified": False,
            "reason": "missing local clock sample",
            "median_wall_delta_ms": None,
        }
    for key in ("basis", "workload_sha256", "host_sha256"):
        if left[key] != right[key]:
            return {
                "qualified": False,
                "reason": "changed clock " + key,
                "median_wall_delta_ms": None,
            }
    return {
        "qualified": True,
        "reason": "matched local workload and host",
        "median_wall_delta_ms": round(
            median(right["duration_ms"]) - median(left["duration_ms"]), 6
        ),
        "github_runner_acceleration_certified": False,
    }


def run(payload):
    need(
        isinstance(payload, dict) and payload.get("schema") == SOURCE_SCHEMA,
        "trajectory input schema mismatch",
    )
    need(payload.get("repository") == "GBOGEB/ABACUS", "wrong source repository")
    rows = payload.get("observations")
    need(
        isinstance(rows, list) and len(rows) == 4, "N5 baseline plus W7/W8/W9 required"
    )
    parsed = [observation(item, wave) for item, wave in zip(rows, WAVES)]
    need(
        all(
            left["timestamp"] < right["timestamp"]
            for left, right in zip(parsed, parsed[1:])
        ),
        "non-monotonic observation clock",
    )
    cov = [
        dict(from_wave=a["wave"], to_wave=b["wave"], **coverage_pair(a, b))
        for a, b in zip(parsed, parsed[1:])
    ]
    timing = [
        dict(from_wave=a["wave"], to_wave=b["wave"], **clock_comparison(a, b))
        for a, b in zip(parsed, parsed[1:])
    ]
    forecasts = payload.get("forecasts", [])
    need(isinstance(forecasts, list), "forecast array required")
    scored = []
    seen = set()
    lookup = {p["wave"]: p for p in parsed}
    for f in forecasts:
        need(
            isinstance(f, dict) and f.get("issued_wave") in lookup,
            "forecast issuer must have a real wave",
        )
        need(
            f.get("target_wave") in ("W7", "W8", "W9", "W10"), "unsupported target wave"
        )
        issuer = lookup[f["issued_wave"]]
        need(
            f.get("issued_head_sha") == issuer["source_sha"],
            "forecast source head drift",
        )
        when = timestamp(f.get("issued_at"))
        need(when >= issuer["timestamp"], "forecast issued before source observation")
        identity = (f["issued_wave"], f["target_wave"])
        need(identity not in seen, "duplicate immutable forecast key")
        seen.add(identity)
        need(
            number(f.get("predicted_branch_pct")) and f["predicted_branch_pct"] <= 100,
            "forecast prediction outside percent bounds",
        )
        target = lookup.get(f["target_wave"])
        if target is not None:
            need(when < target["timestamp"], "forecast future leakage")
        scored.append(
            {
                "issued_wave": f["issued_wave"],
                "target_wave": f["target_wave"],
                "prediction": f["predicted_branch_pct"],
                "actual": (
                    round(
                        100
                        * target["coverage"]["covered_branches"]
                        / target["coverage"]["eligible_branches"],
                        6,
                    )
                    if target is not None
                    and target["coverage"]["source_content_sha256"]
                    == issuer["coverage"]["source_content_sha256"]
                    else None
                ),
                "admissible_as_independent_forecast": False,
            }
        )
    return {
        "schema": OUTPUT_SCHEMA,
        "repository": payload["repository"],
        "baseline": "N5",
        "waves": list(WAVES),
        "observations": [
            {
                "wave": o["wave"],
                "head_sha": o["source_sha"],
                "observed_at": o["observed_at"],
                "tests": o["tests"],
                "statement_percent": round(
                    100
                    * o["coverage"]["covered_statements"]
                    / o["coverage"]["eligible_statements"],
                    6,
                ),
                "branch_percent": round(
                    100
                    * o["coverage"]["covered_branches"]
                    / o["coverage"]["eligible_branches"],
                    6,
                ),
                "backlog_run_ids_read": o["historical_backlog"]["observed_run_ids"],
                "local_clock_p50_ms": (
                    round(median(o["clock"]["duration_ms"]), 6) if o["clock"] else None
                ),
            }
            for o in parsed
        ],
        "coverage_pairs": cov,
        "trajectory": classify(cov),
        "clock_pairs": timing,
        "forecasts": scored,
        "forecast_mae_pp": (
            round(
                sum(
                    abs(x["prediction"] - x["actual"])
                    for x in scored
                    if x["actual"] is not None
                )
                / sum(x["actual"] is not None for x in scored),
                6,
            )
            if any(x["actual"] is not None for x in scored)
            else None
        ),
        "growth_in_tests_passed": parsed[-1]["tests"]["passed"]
        - parsed[0]["tests"]["passed"],
        "n0_runs_remaining": 253 - parsed[-1]["historical_backlog"]["observed_run_ids"],
        "unknown_new_roots": None,
        "main_coverage_uplift_pp": None,
        "github_runner_speedup_seconds": None,
        "independent_sample_assumption_proven": False,
        "authority": {
            "admission": "HOLD",
            "security_waiver": False,
            "authority_transfer": False,
        },
        "source_digest_sha256": hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }
