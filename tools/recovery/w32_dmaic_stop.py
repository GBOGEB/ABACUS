"""W32 bounded DMAIC scale/stop and one-sided defect-rate evidence.

Six-Sigma-like 3.4 DPMO is a specified defect-rate *benchmark*, not an
assertion of normal six-sigma process capability, Cp/Cpk, certification or
formal governance acceptance. Independent, observed opportunity populations
must be demonstrated; an unmeasured defect is UNKNOWN, never zero.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")
DPMO_TARGET = 3.4
CONFIDENCE = 0.95
MIN_STABLE_TRANSITIONS = 3
MIN_INDEPENDENT_WINDOWS = 5
MAX_FRESH_NATIVE_CELLS = 6


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def zero_defect_upper_dpmo(n, confidence=CONFIDENCE):
    """Exact one-sided binomial upper bound when n independent trials have 0 defects."""
    require(type(n) is int and n > 0, "missing independent opportunity denominator")
    require(type(confidence) is float and 0 < confidence < 1, "invalid confidence")
    return (1 - math.exp(math.log(1 - confidence) / n)) * 1_000_000


def min_zero_defect_trials(dpmo=DPMO_TARGET, confidence=CONFIDENCE):
    require(0 < dpmo < 1_000_000, "invalid DPMO target")
    return math.ceil(math.log(1 - confidence) / math.log1p(-dpmo / 1_000_000))


def _check(w):
    require(isinstance(w, dict), "invalid wave evidence")
    for name, regex in (("head_sha", SHA40), ("source_sha256", SHA64)):
        require(
            isinstance(w.get(name), str) and bool(regex.fullmatch(w[name])),
            "invalid " + name,
        )
    for name in ("wave_id", "scope_id"):
        require(
            isinstance(w.get(name), str) and bool(w[name].strip()), "invalid " + name
        )
    for name in (
        "eligible",
        "covered",
        "terminal_jobs",
        "successful_jobs",
        "pending_jobs",
        "unknown_roots",
    ):
        require(type(w.get(name)) is int and w[name] >= 0, "invalid " + name)
    require(
        w["eligible"] > 0 and w["covered"] <= w["eligible"],
        "invalid coverage denominator",
    )
    require(
        w["successful_jobs"] <= w["terminal_jobs"],
        "native successes exceed terminal jobs",
    )
    roots = w.get("open_root_ids")
    require(
        isinstance(roots, list) and all(isinstance(v, str) and bool(v) for v in roots),
        "open-root inventory unavailable",
    )
    require(len(roots) == len(set(roots)), "duplicate root IDs")
    require(type(w.get("receipt_verified")) is bool, "receipt status unknown")
    q = w.get("queue_p95_seconds")
    require(
        q is None or (type(q) in (int, float) and math.isfinite(q) and q >= 0),
        "invalid native queue p95",
    )
    defects, n = w.get("quality_defects"), w.get("quality_opportunities")
    require(
        (defects is None and n is None)
        or (type(defects) is int and type(n) is int and 0 <= defects <= n and n > 0),
        "invalid quality opportunities",
    )
    cid = w.get("cohort_id")
    require(
        cid is None or (isinstance(cid, str) and bool(cid)),
        "invalid independent cohort identity",
    )
    require(
        type(w.get("cohort_verified", False)) is bool, "invalid cohort verification"
    )


def _flat(w):
    return (
        w["covered"],
        w["eligible"],
        tuple(sorted(w["open_root_ids"])),
        w["unknown_roots"],
    )


def _matching(waves):
    return len({(w["source_sha256"], w["scope_id"], w["eligible"]) for w in waves}) == 1


def _quality(waves):
    eligible = [
        w
        for w in waves
        if w["receipt_verified"]
        and w.get("cohort_verified") is True
        and w.get("cohort_id") is not None
        and w.get("quality_opportunities") is not None
    ]
    ids = [w["cohort_id"] for w in eligible]
    require(len(ids) == len(set(ids)), "duplicate quality cohort reused")
    opportunities = sum(w["quality_opportunities"] for w in eligible)
    defects = sum(w["quality_defects"] for w in eligible)
    upper = (
        zero_defect_upper_dpmo(opportunities)
        if opportunities and defects == 0
        else None
    )
    target_met_on_reported_cohorts = (
        len(eligible) >= MIN_INDEPENDENT_WINDOWS
        and defects == 0
        and upper is not None
        and upper <= DPMO_TARGET
    )
    return {
        "independent_cohorts_claimed_with_receipts": len(eligible),
        "defects": defects if eligible else None,
        "opportunities": opportunities if eligible else None,
        "one_sided_95_upper_dpmo_zero_only": (
            round(upper, 6) if upper is not None else None
        ),
        "required_zero_defect_opportunities_95": min_zero_defect_trials(),
        "reported_cohort_3_4_dpmo_target_met": target_met_on_reported_cohorts,
        "independent_sampling_externally_attested": None,
        "formal_six_sigma_certification": False,
    }


def decide(payload):
    require(isinstance(payload, dict), "invalid controller request")
    waves = payload.get("waves")
    require(isinstance(waves, list), "missing ordered wave ledger")
    for w in waves:
        _check(w)
    ids = [w["wave_id"] for w in waves]
    require(len(ids) == len(set(ids)), "wave identity reused")
    quality = _quality(waves)
    status = "HOLD_NO_DATA"
    plateau_streak = 0
    coverage_delta = None
    roots_delta = None
    current = waves[-1] if waves else None
    if current is not None:
        if len(waves) > 1 and _matching(waves[-2:]):
            coverage_delta = current["covered"] - waves[-2]["covered"]
            roots_delta = len(current["open_root_ids"]) - len(
                waves[-2]["open_root_ids"]
            )
        for pos in range(len(waves) - 1, 0, -1):
            cur, prior = waves[pos], waves[pos - 1]
            comparable = _matching((prior, cur))
            telemetry_valid = (
                cur["queue_p95_seconds"] is not None
                and prior["queue_p95_seconds"] is not None
            )
            drift = abs(cur["queue_p95_seconds"] - prior["queue_p95_seconds"]) / max(
                1.0, prior["queue_p95_seconds"]
            )
            clean = (
                cur["receipt_verified"]
                and prior["receipt_verified"]
                and cur["pending_jobs"] == prior["pending_jobs"] == 0
                and cur["unknown_roots"] == prior["unknown_roots"] == 0
                and cur["terminal_jobs"] > 0
                and prior["terminal_jobs"] > 0
            )
            if (
                comparable
                and clean
                and telemetry_valid
                and drift <= 0.05
                and _flat(cur) == _flat(prior)
            ):
                plateau_streak += 1
            else:
                break
        if current["pending_jobs"] > 0:
            status = "HOLD_QUEUE_SATURATED"
        elif not current["receipt_verified"] or current["terminal_jobs"] == 0:
            status = "HOLD_NATIVE_PROOF_MISSING"
        elif current["unknown_roots"] > 0:
            status = "HOLD_UNCLASSIFIED_FIRST_RED"
        elif len(waves) >= 2 and not _matching(waves[-2:]):
            status = "RESET_UNMATCHED_COVERAGE_SCOPE"
        elif coverage_delta is not None and coverage_delta < 0:
            status = "STOP_COVERAGE_REGRESSION"
        elif plateau_streak >= MIN_STABLE_TRANSITIONS:
            status = "STOP_LOCAL_PLATEAU"
        elif current["queue_p95_seconds"] is None:
            status = "HOLD_LATENCY_UNKNOWN"
        elif current["queue_p95_seconds"] > 900:
            status = "HOLD_QUEUE_PRESSURE"
        elif len(current["open_root_ids"]) > 0:
            status = "REPAIR_EXISTING_ROOTS_FIRST"
        elif current["successful_jobs"] / current["terminal_jobs"] < 0.95:
            status = "REPAIR_FIRST_RED_BEFORE_FANOUT"
        else:
            status = "EXPAND_BOUNDED_DISJOINT_SLICE"
    return {
        "schema": "abacus.w32.dmaic-adaptive-stop.v1",
        "ordered_waves": len(waves),
        "current_head": current["head_sha"] if current else None,
        "decision": status,
        "matched_coverage_delta": coverage_delta,
        "observed_root_count_delta_not_formal_closure": roots_delta,
        "consecutive_zero_value_transitions": plateau_streak,
        "observed_local_plateau": plateau_streak >= MIN_STABLE_TRANSITIONS,
        "dmaic_control_candidate": plateau_streak >= MIN_STABLE_TRANSITIONS,
        "dmaic_stable_and_six_sigma_certified": False,
        "max_next_native_cells": (
            MAX_FRESH_NATIVE_CELLS if status == "EXPAND_BOUNDED_DISJOINT_SLICE" else 0
        ),
        "quality_bound": quality,
        "confidence_model": "fixed_horizon_exact_one_sided_binomial_zero_defect",
        "capacity_limit_applies_per_wave": True,
        "predictions_require_new_immutable_wave_receipts": True,
        "merge_admission": "HOLD",
        "authority_transfer": False,
        "security_waiver": False,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args(argv)
    result = decide(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
