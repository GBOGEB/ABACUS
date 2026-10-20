"""Read-only B-family temporal hierarchy from pinned native GitHub observations.

No GitHub calls or mutation. Output is NOT admission or causal-root closure.
Composite weights measure execution receipt completeness, not security/quality.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "abacus.bseries.native-pulses.v1"
OUT_SCHEMA = "abacus.bseries.temporal-report.v1"
SHA = re.compile(r"[0-9a-f]{40}\Z")
WEIGHTS = {"b0": 0.40, "b1": 0.20, "dab": 0.15, "fanin": 0.25}


class EvidenceError(ValueError):
    """Reject unbound, duplicated and malformed run evidence."""


def _integer(value, name, *, min_value=0):
    if type(value) is not int or value < min_value:
        raise EvidenceError(f"{name}: invalid integer")
    return value


def _timestamp(value):
    if not isinstance(value, str):
        raise EvidenceError("missing observation clock")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("invalid observation clock") from exc
    if parsed.tzinfo is None:
        raise EvidenceError("observation clock is missing timezone")
    return parsed.astimezone(timezone.utc)


def _fraction(numerator, denominator):
    if denominator is None or denominator <= 0 or numerator is None:
        return None
    return numerator / denominator


def validate(doc):
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise EvidenceError("invalid source schema")
    if doc.get("scope") != "GBOGEB/ABACUS/.github/workflows/mip-coverage-evidence.yml":
        raise EvidenceError("unexpected workflow or repository")
    if doc.get("authority_transfer") is not False:
        raise EvidenceError("authority invariant")
    if doc.get("sampling") != "PINNED_CONVENIENCE_SAMPLE_NONREPRESENTATIVE":
        raise EvidenceError("sample design not declared")
    rows = doc.get("observations")
    if not isinstance(rows, list) or not rows:
        raise EvidenceError("observations required")
    ids, clocks = set(), []
    for row in rows:
        if not isinstance(row, dict):
            raise EvidenceError("invalid observation")
        sha = row.get("source_sha")
        if not isinstance(sha, str) or not SHA.fullmatch(sha):
            raise EvidenceError("unbound source SHA")
        run = _integer(row.get("run_id"), "run_id", min_value=1)
        _integer(row.get("pr"), "pr", min_value=1)
        if run in ids:
            raise EvidenceError("reused native run identity")
        ids.add(run)
        attempt = row.get("run_attempt")
        if attempt is not None:
            _integer(attempt, "run_attempt", min_value=1)
        n = _integer(row.get("job_total"), "job_total", min_value=1)
        k = _integer(row.get("job_success"), "job_success")
        if k > n:
            raise EvidenceError("successful jobs exceed eligible jobs")
        for name in ("b0_test_job_id", "b1_job_id", "b0_coverage_artifact_id", "b1_artifact_id"):
            _integer(row.get(name), name, min_value=1)
        for name in ("b0_tests_passed", "b0_tests_failed", "b0_tests_skipped",
                     "b1_unguarded", "dab_proposal_jobs_success", "dab_proposal_jobs_total"):
            _integer(row.get(name), name)
        if row["dab_proposal_jobs_success"] > row["dab_proposal_jobs_total"]:
            raise EvidenceError("DAB numerator exceeds denominator")
        if type(row.get("fanin_success")) is not bool:
            raise EvidenceError("fan-in outcome not boolean")
        if row.get("authenticated_crew_launch") is not None or row.get("root_closure_count") is not None:
            raise EvidenceError("native B-series cannot assert Crew launch or root closure")
        duration = row.get("b0_test_duration_seconds")
        if type(duration) not in (int, float) or not math.isfinite(duration) or duration <= 0:
            raise EvidenceError("invalid test duration")
        if row.get("b1_schema") != "abacus-ci-false-green-census/1.1.0":
            raise EvidenceError("B1 scanner schema drift")
        clocks.append(_timestamp(row.get("observation_at")))
    if clocks != sorted(clocks) or len(set(clocks)) != len(clocks):
        raise EvidenceError("non-monotonic or duplicate observation clocks")
    return rows


def _family_scores(row):
    return {
        "b0": _fraction(row["job_success"], row["job_total"]),
        "b1": 1.0 if row["b1_job_id"] and row["b1_artifact_id"] else None,
        "dab": _fraction(row["dab_proposal_jobs_success"], row["dab_proposal_jobs_total"]),
        "fanin": 1.0 if row["fanin_success"] else 0.0,
    }


def _composite(scores):
    if any(scores.get(k) is None for k in WEIGHTS):
        return None  # missing dimensions do not redistribute their weights
    return round(100 * sum(WEIGHTS[k] * scores[k] for k in WEIGHTS), 4)


def build(doc):
    rows = validate(doc)
    pulses = []
    for row in rows:
        scores = _family_scores(row)
        pulses.append({
            "pulse": row["pulse"], "pr": row["pr"], "source_sha": row["source_sha"],
            "run_id": row["run_id"], "run_attempt": row["run_attempt"],
            "clock": row["observation_at"],
            "job_success": [row["job_success"], row["job_total"]],
            "job_success_pct": round(100 * scores["b0"], 4),
            "b1_unguarded_count": row["b1_unguarded"],
            "tests_passed": row["b0_tests_passed"],
            "tests_failed": row["b0_tests_failed"],
            "tests_skipped": row["b0_tests_skipped"],
            "test_duration_seconds": row["b0_test_duration_seconds"],
            "dab_jobs": [row["dab_proposal_jobs_success"], row["dab_proposal_jobs_total"]],
            "producer_receipt_completeness_index": _composite(scores),
            "native_job_id": row["b0_test_job_id"], "b1_job_id": row["b1_job_id"],
            "coverage_artifact_id": row["b0_coverage_artifact_id"],
            "b1_artifact_id": row["b1_artifact_id"],
            "admission": "HOLD",
        })
    durations = [p["test_duration_seconds"] for p in pulses]
    median = statistics.median(durations)
    mad = statistics.median(abs(t - median) for t in durations)
    b1_values = [p["b1_unguarded_count"] for p in pulses]
    comparable_b1 = (
        all(row["b1_config_fingerprint"] is not None for row in rows)
        and len({row["b1_config_fingerprint"] for row in rows}) == 1
    )
    run_success = sum(p["job_success"][0] == p["job_success"][1] for p in pulses)
    return {
        "schema": OUT_SCHEMA, "source_schema": SCHEMA, "scope": doc["scope"],
        "sample_design": doc["sampling"],
        "hierarchy": {
            "federation": {"observed": None, "reason": "No federation census"},
            "repo": {"name": "GBOGEB/ABACUS", "global_ci_share": None,
                     "reason": "Sample does not enumerate all workflows"},
            "workflow": {"name": "MIP B0 Test Admission and Coverage Evidence",
                         "run_sample": len(pulses),
                         "families": ["B0", "B1", "DAB_READ_ONLY", "B0_FANIN"]},
            "leaves": ["B0 job outcome", "B0 tests", "B0 duration",
                       "B1 census", "DAB proposal jobs", "B0 fan-in"],
        },
        "pulses": pulses,
        "execution_composite": {
            "name": "PRODUCER_RECEIPT_COMPLETENESS_ONLY",
            "weights": WEIGHTS,
            "index_series": [p["producer_receipt_completeness_index"] for p in pulses],
            "interpretation": "Evidence-producer execution readiness only; NOT risk reduction, coverage gain, admission or root closure",
        },
        "three_pulse_metrics": {
            "sampled_run_success": [run_success, len(pulses)],
            "sampled_run_success_rate": _fraction(run_success, len(pulses)),
            "b1_raw_counts": b1_values,
            "b1_comparable_velocity": (
                0.0 if comparable_b1 and len(b1_values) > 1 and len(set(b1_values)) == 1
                else None
            ),
            "b1_forecast_error": None,
            "duration_median_seconds": median,
            "duration_mad_seconds": round(mad, 3),
            "test_count_growth_rate": None,
            "test_count_acceleration": None,
            "test_population_comparability": "NOT_MATCHED_DIFFERENT_SOURCE_HEADS",
            "b1_config_comparability": "MATCHED" if comparable_b1 else "UNVERIFIED_CONFIG_DIGEST",
            "branch_coverage_delta": None,
            "main_coverage_delta": None,
            "root_leverage": None,
            "accepted_yield": None,
        },
        "forecast": {
            "target": "next_B1_unguarded_count",
            "point_estimate": b1_values[-1] if comparable_b1 else None,
            "state": "WITHHELD_UNTIL_CONFIG_MATCHED_AND_PROSPECTIVELY_TIMESTAMPED",
            "forecast_error": None,
        },
        "unknown_families": ["B2", "B3", "B4", "B5", "B6_PLUS"],
        "unknown_families_meaning": "Not observed as named jobs in this canonical B0 workflow; global presence unverified",
        "authenticated_crew_launches": None, "formal_root_closures": None,
        "merge_admission": "HOLD", "authority_transfer": False, "security_waiver": False,
    }


def render_markdown(report):
    lines = [
        "# B-series three-pulse temporal metric readout", "",
        "**Read-only native historical sample.** Not an admission or fleet-wide rate.", "",
        "| Pulse | PR | Native run | B0 jobs | B1 findings | Passed | Duration s | Evidence index |",
        "|:--|--:|--:|--:|--:|--:|--:|--:|",
    ]
    for p in report["pulses"]:
        lines.append(
            f"| {p['pulse']} | #{p['pr']} | {p['run_id']} | "
            f"{p['job_success'][0]}/{p['job_success'][1]} | "
            f"{p['b1_unguarded_count']} | {p['tests_passed']} | "
            f"{p['test_duration_seconds']:.2f} | "
            f"{p['producer_receipt_completeness_index']:.2f} |"
        )
    lines.extend([
        "", "## Interpretation", "",
        "- B0 and DAB execution remain green in this selected sample.",
        "- B1 reports 139 unguarded constructs per scan; B1 PASS does not mean zero findings.",
        "- Test counts and runtimes across distinct heads are descriptive, NOT matched velocity.",
        "- The native run/job/artifact provenance and source SHAs are in companion JSON.",
        "- Composite index is execution-receipt completeness, not a quality/security score.",
        "- Missing B2+ named stages in this workflow is not proof of global absence.",
        "- No Crew launch, accepted root closure, waiver, or main coverage uplift inferred.", "",
    ])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--markdown-out", type=Path, required=True)
    args = parser.parse_args(argv)
    result = build(json.loads(args.input.read_text(encoding="utf-8")))
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_out.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps({"status": "OBSERVED_SAMPLE_ONLY", "pulses": len(result["pulses"]), "admission": result["merge_admission"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
