"""Fail-closed, descriptive N/N+1/N+2 CI telemetry reader.

Consumes source-bound v2 projections from the canonical MIP CI worker (#2033).
This is an offline comparison, not a GitHub acquisition, independent REX,
statistical PCA certification, causal closure, or merge-admission authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

INPUT_SCHEMA = "abacus.mip.ci-temporal-input.v1"
OUTPUT_SCHEMA = "abacus.mip.ci-temporal-rollup.v1"
SOURCE_SCHEMA = "abacus.mip.ci-wave-telemetry.v2"
HEX40 = re.compile(r"^[a-f0-9]{40}$")
HEX64 = re.compile(r"^[a-f0-9]{64}$")
OUTCOMES = (
    "success", "failure", "neutral", "cancelled", "skipped", "timed_out",
    "action_required", "stale", "startup_failure",
)
MAX_WAVES = 200
MAX_FILE_BYTES = 2_000_000
MIN_QUEUE_SAMPLES = 20


def require(predicate, message):
    if not predicate:
        raise ValueError(message)


def integer(value, *, minimum=0):
    return type(value) is int and value >= minimum


def utc(value):
    require(isinstance(value, str) and value.endswith("Z"), "UTC Z timestamp required")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid observed UTC timestamp") from exc
    require(stamp.utcoffset().total_seconds() == 0, "timestamp must be UTC")
    return stamp


def hex_value(value, pattern, label):
    require(isinstance(value, str) and pattern.fullmatch(value) is not None,
            "invalid " + label)


def check_coverage(coverage, source_sha):
    if coverage is None:
        return None
    require(isinstance(coverage, dict), "coverage must be an object or null")
    require(coverage.get("source_sha") == source_sha, "coverage SHA mismatch")
    for key in ("scope_sha256", "config_sha256", "artifact_sha256"):
        hex_value(coverage.get(key), HEX64, key)
    require(isinstance(coverage.get("tool_version"), str)
            and coverage["tool_version"].strip(), "coverage tool version required")
    for part in ("lines", "branches"):
        covered = coverage.get("covered_" + part)
        eligible = coverage.get("eligible_" + part)
        require(integer(eligible) and integer(covered)
                and covered <= eligible, "invalid " + part + " coverage counts")
    return coverage


def check_observation(obs, cohort):
    require(isinstance(obs, dict), "wave observation must be object")
    require(integer(obs.get("wave"), minimum=1), "positive integer wave required")
    sha = obs.get("source_sha")
    hex_value(sha, HEX40, "source SHA")
    stamp = utc(obs.get("observed_at"))
    attempts = obs.get("run_attempts")
    require(isinstance(attempts, list) and attempts, "native run:attempt identities required")
    identities = []
    for pair in attempts:
        require(isinstance(pair, list) and len(pair) == 2
                and all(integer(v, minimum=1) for v in pair),
                "invalid run:attempt pair")
        identities.append(tuple(pair))
    require(len(identities) == len(set(identities)), "duplicate native run attempt")
    t = obs.get("telemetry")
    require(isinstance(t, dict) and t.get("schema") == SOURCE_SCHEMA
            and t.get("source_sha") == sha and t.get("repository") == cohort["repository"],
            "telemetry schema, repository or exact SHA mismatch")
    n = t.get("workflow_records_observed")
    require(integer(n, minimum=1) and n == len(identities),
            "workflow total not reconciled to run:attempt selection")
    outcomes = t.get("workflow_terminal_by_outcome")
    require(isinstance(outcomes, dict) and set(outcomes) == set(OUTCOMES)
            and all(integer(outcomes[key]) for key in OUTCOMES),
            "terminal outcomes incomplete or invalid")
    pending = t.get("workflow_nonterminal")
    unclassified = t.get("workflow_unclassified")
    require(integer(pending) and integer(unclassified)
            and sum(outcomes.values()) + pending + unclassified == n,
            "workflow outcome totals do not reconcile")
    require(t.get("merge_authorized") is False
            and isinstance(t.get("independent_gates"), dict)
            and t["independent_gates"].get("admission") == "HOLD",
            "source projection does not preserve governance HOLD")
    jobs = t.get("jobs_observed")
    require(integer(jobs), "invalid jobs observed")
    samples = t.get("queue_samples")
    require(integer(samples) and samples <= jobs, "invalid queue denominator")
    p95 = t.get("queue_seconds_p95")
    require((p95 is None if samples == 0 else
             type(p95) in (float, int) and 0 <= p95 < float("inf")),
            "queue p95 absent or invalid")
    require(isinstance(t.get("queue_basis"), str) and t["queue_basis"],
            "queue basis required")
    queue_sources = t.get("queue_source_counts")
    require(isinstance(queue_sources, dict) and set(queue_sources) == {
        "job_created_at", "workflow_run_created_at_fallback"
    } and all(integer(value) for value in queue_sources.values())
            and sum(queue_sources.values()) == samples,
            "queue provenance counts must reconcile to measured samples")
    coverage = check_coverage(obs.get("coverage"), sha)
    finished = pending == 0 and unclassified == 0
    return {
        "wave": obs["wave"], "source_sha": sha, "observed_at": obs["observed_at"],
        "timestamp": stamp, "attempts": identities,
        "terminal": finished, "workflow_count": n,
        "success_fraction": round(outcomes["success"] / n, 9) if finished else None,
        "success_count": outcomes["success"],
        "failure_count": outcomes["failure"],
        "remaining_pending": pending + unclassified,
        "queue_samples": samples, "queue_p95_seconds": p95,
        "queue_basis": t["queue_basis"],
        "queue_native_timestamp_samples": queue_sources["job_created_at"],
        "queue_fallback_timestamp_samples": queue_sources[
            "workflow_run_created_at_fallback"
        ],
        "queue_native_timestamp_fraction": (
            round(queue_sources["job_created_at"] / samples, 6)
            if samples else None
        ),
        "coverage": coverage,
    }


def coverage_delta(before, after, dimension):
    a, b = before["coverage"], after["coverage"]
    if a is None or b is None:
        return None, "missing coverage numerator/denominator"
    for key in ("scope_sha256", "config_sha256", "tool_version"):
        if a[key] != b[key]:
            return None, "unmatched coverage " + key
    denom = "eligible_" + dimension
    count = "covered_" + dimension
    if a[denom] != b[denom] or a[denom] == 0:
        return None, "different or empty coverage denominator"
    return round((b[count] - a[count]) * 100 / a[denom], 6), None


def compare(before, after):
    completed = before["terminal"] and after["terminal"]
    same_workflows = before["workflow_count"] == after["workflow_count"]
    success_delta = None
    if completed and same_workflows:
        success_delta = round(
            (after["success_fraction"] - before["success_fraction"]) * 100, 6
        )
    queue_delta = None
    if (completed and same_workflows
            and before["queue_basis"] == after["queue_basis"]
            and before["queue_fallback_timestamp_samples"] == 0
            and after["queue_fallback_timestamp_samples"] == 0
            and min(before["queue_samples"], after["queue_samples"])
            >= MIN_QUEUE_SAMPLES):
        queue_delta = round(
            after["queue_p95_seconds"] - before["queue_p95_seconds"], 6
        )
    line_delta, line_reason = coverage_delta(before, after, "lines")
    branch_delta, branch_reason = coverage_delta(before, after, "branches")
    return {
        "from_wave": before["wave"], "to_wave": after["wave"],
        "workflow_success_delta_pp": success_delta,
        "workflow_comparability": (
            "descriptive_only" if success_delta is not None
            else "nonterminal_or_workflow_denominator_mismatch"
        ),
        "queue_p95_delta_seconds": queue_delta,
        "queue_comparability": (
            "descriptive_only_not_independent" if queue_delta is not None
            else "nonterminal_or_small_or_mismatched_queue_cohort_or_fallback_timing"
        ),
        "line_coverage_candidate_delta_pp": line_delta,
        "line_reason": line_reason,
        "branch_coverage_candidate_delta_pp": branch_delta,
        "branch_reason": branch_reason,
        "accepted_main_coverage_delta_pp": None,
        "verified_formal_root_closures": None,
    }


def check_forecast(row, by_wave):
    require(isinstance(row, dict) and row.get("method") == "persistence-v1",
            "unsupported persisted forecast")
    issued, target = row.get("issued_wave"), row.get("target_wave")
    require(integer(issued, minimum=1) and integer(target, minimum=1)
            and target in (issued + 1, issued + 2) and issued in by_wave,
            "invalid forecast horizons or absent issuing wave")
    source = by_wave[issued]
    require(row.get("issued_source_sha") == source["source_sha"],
            "forecast issuance SHA mismatch")
    stamp = utc(row.get("issued_at"))
    require(stamp >= source["timestamp"], "forecast before source observation")
    if target in by_wave:
        require(stamp < by_wave[target]["timestamp"],
                "future leakage: forecast issued after target observed")
    prediction = row.get("prediction")
    require(type(prediction) in (int, float)
            and 0 <= prediction <= 1 and source["success_fraction"] is not None
            and abs(prediction - source["success_fraction"]) < 1e-9,
            "forecast differs from predeclared persistence estimator")
    return {
        "issued_wave": issued, "target_wave": target,
        "issued_source_sha": source["source_sha"],
        "issued_at": row["issued_at"], "method": row["method"],
        "prediction": prediction,
        "actual": by_wave[target]["success_fraction"] if target in by_wave else None,
    }


def rollup(payload):
    require(isinstance(payload, dict) and payload.get("schema") == INPUT_SCHEMA,
            "unsupported temporal input schema")
    require(payload.get("repository") == "GBOGEB/ABACUS", "wrong repository")
    cohort = payload.get("cohort")
    require(isinstance(cohort, dict), "explicit comparable cohort required")
    for key in ("workflow_set_sha256", "test_selection_sha256",
                "runner_matrix_sha256"):
        hex_value(cohort.get(key), HEX64, "cohort " + key)
    cohort = dict(cohort, repository=payload["repository"])
    waves = payload.get("observations")
    require(isinstance(waves, list) and 1 <= len(waves) <= MAX_WAVES,
            "bounded nonempty wave sequence required")
    parsed = []
    observed_attempts = set()
    for raw in waves:
        row = check_observation(raw, cohort)
        if parsed:
            require(row["wave"] == parsed[-1]["wave"] + 1,
                    "waves must be consecutive ordered states")
            require(row["timestamp"] > parsed[-1]["timestamp"],
                    "observation clock not monotone")
        for identity in row["attempts"]:
            require(identity not in observed_attempts,
                    "native run attempt reused across waves")
            observed_attempts.add(identity)
        parsed.append(row)

    by_wave = {row["wave"]: row for row in parsed}
    persisted = payload.get("forecasts", [])
    require(isinstance(persisted, list), "forecasts must be a list")
    seen_forecasts = set()
    scored = []
    validated_forecasts = []
    for raw in persisted:
        forecast = check_forecast(raw, by_wave)
        key = (forecast["issued_wave"], forecast["target_wave"])
        require(key not in seen_forecasts, "duplicate immutable forecast key")
        seen_forecasts.add(key)
        validated_forecasts.append(forecast)
        if forecast["actual"] is not None:
            scored.append(abs(forecast["prediction"] - forecast["actual"]))

    comparisons = [compare(a, b) for a, b in zip(parsed, parsed[1:])]
    latest = parsed[-1]
    proposals = []
    if latest["success_fraction"] is not None:
        proposals = [{
            "issued_wave": latest["wave"],
            "target_wave": latest["wave"] + lag,
            "issued_source_sha": latest["source_sha"],
            "method": "persistence-v1",
            "proposed_prediction": latest["success_fraction"],
            "state": "UNISSUED; persist with a real issued_at before target is observed",
        } for lag in (1, 2)]

    return {
        "schema": OUTPUT_SCHEMA,
        "repository": payload["repository"],
        "cohort": {k: cohort[k] for k in (
            "workflow_set_sha256", "test_selection_sha256", "runner_matrix_sha256"
        )},
        "waves_observed": len(parsed),
        "native_run_attempts_structurally_bound": len(observed_attempts),
        "rows": [{k: v for k, v in row.items()
                  if k not in ("timestamp", "attempts", "coverage")}
                 for row in parsed],
        "comparisons": comparisons,
        "persisted_forecasts": validated_forecasts,
        "forecasts_scored": len(scored),
        "forecast_mae": round(sum(scored) / len(scored), 9) if scored else None,
        "proposed_n_plus_1_n_plus_2": proposals,
        "native_artifact_bytes_authenticated": None,
        "temporal_independence_proven": None,
        "pca_maturity": "HOLD_UNQUALIFIED_INDEPENDENT_OBSERVATIONS",
        "statistical_significance_claimed": False,
        "accepted_bd_root_closures": None,
        "rex_authenticated": None,
        "authority_transfer": False,
        "security_waiver": False,
        "merge_authorized": False,
        "admission": "HOLD",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    options = parser.parse_args(argv)
    require(options.input.resolve() != options.out.resolve(), "input/output path collision")
    require(options.input.is_file() and not options.input.is_symlink()
            and 0 < options.input.stat().st_size <= MAX_FILE_BYTES,
            "missing, linked or oversized input")
    raw = options.input.read_bytes()
    output = rollup(json.loads(raw))
    options.out.parent.mkdir(parents=True, exist_ok=True)
    options.out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print("rollup_sha256=" + hashlib.sha256(options.out.read_bytes()).hexdigest())
    print("waves=" + str(output["waves_observed"]))
    print("admission=" + output["admission"])


if __name__ == "__main__":
    main()
