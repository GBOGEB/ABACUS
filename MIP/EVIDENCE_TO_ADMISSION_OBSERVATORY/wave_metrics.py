"""Evidence-only CODE PURPLE adaptive wave sizing and N progression.

No merge, dispatch, approval or engineering-root authority is present here.
The historical W007 cohort is a calibration example, not a main/diff uplift.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from math import ceil, isfinite
from pathlib import Path
from typing import Any

from elastic_wave_governor import evaluate as evaluate_elastic_wave
from wave_convergence import evaluate as evaluate_engineering_convergence

SHA = re.compile(r"^[0-9a-f]{40}$")
ROOT = Path(__file__).resolve().parent


class ProofError(ValueError):
    """Reject malformed or incomparable evidence rather than assume zero."""


def _integer(value: Any, name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ProofError(f"{name} must be integer >= {minimum}")
    return value


def _sha(value: Any) -> str:
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise ProofError("Exact 40-character source SHA required")
    return value


def _job_receipts(observation: dict) -> tuple[int, int]:
    jobs = observation.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        raise ProofError("Missing exact-head native job receipts")
    seen = set()
    for job in jobs:
        if not isinstance(job, dict):
            raise ProofError("Malformed native job")
        jid, run = _integer(job.get("job_id"), "job_id", 1), _integer(
            job.get("run_id"), "run_id", 1
        )
        if jid in seen:
            raise ProofError("Duplicate native job identity")
        seen.add(jid)
        if (
            run != observation["run_id"]
            or job.get("head_sha") != observation["head_sha"]
        ):
            raise ProofError("Native job not pinned to observed run and SHA")
        if job.get("conclusion") not in {
            "success",
            "failure",
            "cancelled",
            "skipped",
            None,
        }:
            raise ProofError("Unexpected job conclusion")
        if job.get("conclusion") == "success":
            if not isinstance(job.get("artifact_sha256"), str) or not re.fullmatch(
                r"[0-9a-f]{64}", job["artifact_sha256"]
            ):
                raise ProofError("Successful job lacks artifact SHA-256")
            _integer(job.get("artifact_id"), "artifact_id", 1)
    return len(jobs), sum(x.get("conclusion") == "success" for x in jobs)


def qualify_observation(obs: dict) -> dict:
    if not isinstance(obs, dict):
        raise ProofError("Observation must be a dictionary")
    result = dict(obs)
    _sha(obs.get("head_sha"))
    _integer(obs.get("wave"), "wave", 0)
    _integer(obs.get("run_id"), "run_id", 1)
    denominator = _integer(
        obs.get("eligible_opportunities"), "eligible_opportunities", 1
    )
    covered = _integer(obs.get("covered_opportunities"), "covered_opportunities")
    if covered > denominator:
        raise ProofError("Covered opportunities exceed denominator")
    cases = _integer(obs.get("cases_per_job"), "cases_per_job", 1)
    if not isinstance(obs.get("cohort_id"), str) or not obs["cohort_id"].strip():
        raise ProofError("Missing cohort identity")
    if (
        not isinstance(obs.get("configuration_id"), str)
        or not obs["configuration_id"].strip()
    ):
        raise ProofError("Missing scan/test configuration")
    count, successful = _job_receipts(obs)
    expected = _integer(obs.get("expected_jobs"), "expected_jobs", 1)
    if count > expected:
        raise ProofError("More native jobs than contracted cells")
    result["jobs_observed"] = count
    result["jobs_success"] = successful
    result["fully_qualified"] = count == expected and successful == expected
    result["execution_count"] = (
        cases * successful if result["fully_qualified"] else None
    )
    result["covered_percent"] = (
        round(100 * covered / denominator, 6) if result["fully_qualified"] else None
    )
    result["uncovered_opportunities"] = (
        denominator - covered if result["fully_qualified"] else None
    )
    return result


def _round(x: float) -> float:
    if not isfinite(x):
        raise ProofError("Non-finite metric")
    return round(x, 6)


def matched_progress(observations: list[dict]) -> dict:
    """Comparable *fixed opportunity* observational pulses, not a causal effect.

    Nonuniform wave distances are accounted for: N+1 to N+3 is two wave
    slots, N+3 to N+4 is one. No wall-clock acceleration is inferred.
    """
    if not isinstance(observations, list) or not observations:
        raise ProofError("At least one native observation required")
    accepted = [qualify_observation(o) for o in observations]
    waves = [o["wave"] for o in accepted]
    if waves != sorted(set(waves)):
        raise ProofError("Wave order must increase strictly")
    eligible = accepted[0]["eligible_opportunities"]
    cohort = accepted[0]["cohort_id"]
    config = accepted[0]["configuration_id"]
    if any(
        o["eligible_opportunities"] != eligible
        or o["cohort_id"] != cohort
        or o["configuration_id"] != config
        for o in accepted
    ):
        raise ProofError("Cohort or eligible denominator/config changed")
    if any(not o["fully_qualified"] for o in accepted):
        raise ProofError("Cannot compare nonterminal or missing-artifact native cells")
    pulses = []
    for pos, obs in enumerate(accepted):
        row = {
            "wave": obs["wave"],
            "source_sha": obs["head_sha"],
            "run_id": obs["run_id"],
            "url": f"https://github.com/GBOGEB/ABACUS/actions/runs/{obs['run_id']}",
            "native_jobs": obs["jobs_success"],
            "planned_jobs": obs["expected_jobs"],
            "cases_per_job": obs["cases_per_job"],
            "native_test_executions": obs["execution_count"],
            "covered": obs["covered_opportunities"],
            "eligible": eligible,
            "uncovered": obs["uncovered_opportunities"],
            "coverage_percent": obs["covered_percent"],
            "delta_covered": None,
            "delta_pp": None,
            "wave_span": None,
            "gain_pp_per_wave": None,
            "cases_added_per_job": None,
            "new_covered_per_added_case": None,
        }
        if pos:
            earlier = accepted[pos - 1]
            n = obs["covered_opportunities"] - earlier["covered_opportunities"]
            case_delta = obs["cases_per_job"] - earlier["cases_per_job"]
            span = obs["wave"] - earlier["wave"]
            row.update(
                {
                    "delta_covered": n,
                    "delta_pp": _round(100 * n / eligible),
                    "wave_span": span,
                    "gain_pp_per_wave": _round(100 * n / eligible / span),
                    "cases_added_per_job": case_delta,
                    "new_covered_per_added_case": (
                        _round(n / case_delta) if case_delta > 0 else None
                    ),
                }
            )
        pulses.append(row)
    rates = [p["gain_pp_per_wave"] for p in pulses if p["gain_pp_per_wave"] is not None]
    direction = "INSUFFICIENT_MATCHED_PULSES"
    change = None
    if len(rates) > 1:
        change = _round(rates[-1] - rates[-2])
        direction = (
            "DECELERATING_GAIN"
            if change < 0
            else "ACCELERATING_GAIN" if change > 0 else "STABLE_GAIN"
        )
    last = pulses[-1]
    return {
        "schema": "codepurple.matched_wave_metrics.v1",
        "cohort_id": cohort,
        "configuration_id": config,
        "fixed_opportunity_denominator": eligible,
        "cohort_qualification": "SAME_MODULE_AND_COUNT_NOT_BLOB_IDENTICAL",
        "causal_coverage_uplift": None,
        "repository_main_coverage_uplift": None,
        "observations": pulses,
        "gain_rate_trend": direction,
        "rate_change_pp_per_wave": change,
        "remaining_uncovered_opportunities": last["uncovered"],
        "ceiling_reached": last["uncovered"] == 0,
        "next_behavioral_focus": (
            "EXPAND_TO_SEPARATE_UNCOVERED_SOURCE_SLICE"
            if last["uncovered"] == 0
            else "TARGET_UNCOVERED_BRANCHES_AND_NEGATIVE_PATHS"
        ),
        "warnings": [
            "Wave-normalized rates are NOT wall-clock acceleration",
            "No unverified root/ASH or main/diff credit",
        ],
    }


def rank_source_slices(candidates: list[dict], max_source_paths: int = 2) -> dict:
    """Bounded source-owner ranking. Incomplete input is not a low-risk zero.

    Read-only scouts may rank candidates, but no ranked proposal may mutate code.
    Score = newly uncovered eligible opportunities per planned changed file.
    Risk markers prioritize first-red and adversarial tests; they are not a
    probabilistic defect-elimination forecast.
    """
    if not isinstance(candidates, list):
        raise ProofError("Candidates must be a list")
    _integer(max_source_paths, "max_source_paths", 1)
    ready, withheld, leased = [], [], set()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise ProofError("Candidate must be a dictionary")
        family = candidate.get("family")
        paths = candidate.get("paths")
        if not isinstance(family, str) or not family:
            raise ProofError("Missing source family")
        if (
            not isinstance(paths, list)
            or not paths
            or len(paths) > max_source_paths
            or any(
                not isinstance(p, str)
                or not p
                or p.startswith("/")
                or ".." in p.split("/")
                for p in paths
            )
        ):
            withheld.append(
                {"family": family, "reason": "SOURCE_LEASE_TOO_WIDE_OR_INVALID"}
            )
            continue
        if any(p in leased for p in paths):
            withheld.append({"family": family, "reason": "OVERLAPPING_SOURCE_LEASE"})
            continue
        uncovered = candidate.get("uncovered")
        denominator = candidate.get("eligible")
        source_sha = candidate.get("source_sha")
        if (
            type(uncovered) is not int
            or type(denominator) is not int
            or denominator <= 0
            or not 0 <= uncovered <= denominator
            or not isinstance(source_sha, str)
            or not SHA.fullmatch(source_sha)
        ):
            withheld.append(
                {"family": family, "reason": "MISSING_COMPARABLE_SOURCE_METRIC"}
            )
            continue
        if uncovered == 0:
            withheld.append({"family": family, "reason": "MEASURED_COHORT_AT_CEILING"})
            continue
        score = uncovered / len(paths)
        ready.append(
            {
                "family": family,
                "paths": paths,
                "uncovered": uncovered,
                "eligible": denominator,
                "source_sha": source_sha,
                "first_red": candidate.get("first_red") is True,
                "opportunities_per_changed_file": _round(score),
                "mode": "READ_ONLY_RECON_ONLY",
            }
        )
        leased.update(paths)
    ready.sort(
        key=lambda x: (
            not x["first_red"],
            -x["opportunities_per_changed_file"],
            x["family"],
        )
    )
    return {
        "qualified_readonly_candidates": ready,
        "withheld": withheld,
        "max_disjoint_candidates": min(3, len(ready)),
        "remote_worker_launches": None,
        "source_write_permitted": False,
    }


def adaptive_slice_policy(snapshot: dict, progress: dict) -> dict:
    """Bounded parallel read-only scaling with noncompensating governance HOLD."""
    main = snapshot.get("main") or {}
    b0 = (snapshot.get("workflows") or {}).get("b0") or {}
    coverage = (snapshot.get("coverage") or {}).get("measured") or {}
    gov = snapshot.get("governance") or {}
    errors = snapshot.get("census_errors") or []
    stable = main.get("head_stable") is True
    main_sha = main.get("sha")
    exact_b0 = (
        isinstance(main_sha, str)
        and SHA.fullmatch(main_sha)
        and b0.get("sha") == main_sha
        and b0.get("status") == "completed"
        and b0.get("conclusion") == "success"
    )
    native_receipt = (
        coverage.get("sha") == main_sha
        and coverage.get("status") == "MEASURED_ON_EXACT_MAIN_SHA"
    )
    missing = []
    if not stable:
        missing.append("A_B_A_MAIN_UNVERIFIED")
    if not exact_b0:
        missing.append("EXACT_MAIN_B0_NOT_TERMINAL_GREEN")
    if not native_receipt:
        missing.append("CURRENT_MAIN_COVERAGE_ARTIFACT_MISSING")
    if errors:
        missing.append("CENSUS_PARTIAL_OR_FAILED")
    # Admission is explicitly noncompensating, even if every test is green.
    policy = (gov.get("required_approvals"), gov.get("required_check_rules"))
    if (
        type(policy[0]) is not int
        or policy[0] < 1
        or type(policy[1]) is not int
        or policy[1] < 1
    ):
        missing.append("OWNER_GITHUB_RULES_NOT_ENFORCED")
    if gov.get("negative_canary_rejected") is not True:
        missing.append("NEGATIVE_RED_CANARY_NOT_PROVEN")
    queue_p95 = b0.get("queue_p95_seconds")
    if type(queue_p95) not in (int, float) or not isfinite(queue_p95) or queue_p95 < 0:
        missing.append("RUNNER_QUEUE_P95_UNKNOWN")
        queue_control = False
    else:
        queue_control = queue_p95 <= 900
        if not queue_control:
            missing.append("RUNNER_QUEUE_P95_ABOVE_900_SECONDS")
    qualified_frontier = (
        stable and exact_b0 and native_receipt and not errors and queue_control
    )
    root = (snapshot.get("issues") or {}).get("accepted_roots_closed")
    recommended = 3 if qualified_frontier else 1
    remaining = progress.get("remaining_uncovered_opportunities")
    if type(remaining) is not int:
        raise ProofError("Missing scope numerator")
    if remaining == 0:
        next_slice = "NEXT_DISTINCT_SOURCE_FAMILY_OR_DIFF_COHORT"
        minimum = "Pick uncovered eligible modules with verified denominator + risk, not more W007 coverage-only cases"
    else:
        next_slice = "SAME_COHORT_NEGATIVE_REVERSE_FAULT_INJECTION"
        minimum = f"Exercise {remaining} verified uncovered opportunities before expanding scope"
    return {
        "schema": "codepurple.wave_scale_policy.v1",
        "read_only_parallel_lanes_max": recommended,
        "source_mutation_parallel_lanes_max": 1,
        "source_mutation_enabled": False,
        "merge_admission": "HOLD",
        "governed_merge_credit": None,
        "authenticated_crew_launch_credit": None,
        "accepted_causal_root_closed": root if type(root) is int else None,
        "measurement_frontier_qualified": bool(qualified_frontier),
        "admission_blockers": [
            x for x in missing if x.startswith("OWNER_") or "CANARY" in x
        ],
        "measurement_blockers": [
            x for x in missing if not (x.startswith("OWNER_") or "CANARY" in x)
        ],
        "next_slice": next_slice,
        "minimum_next_wave": minimum,
        "scale_up_condition": "Exact stable main + native artifact + complete required gate receipts; no errors",
        "scale_down_condition": "Head moved, terminal first-red, missing receipt, or uncontrolled queue",
        "predicted_coverage_pp": None,
        "prediction_state": "NOT_STATISTICALLY_QUALIFIED",
        "forecast": {
            "scope": "BOUNDED_EXECUTION_TARGET_NOT_PROBABILISTIC",
            "next_readonly_lanes_if_proven": 3,
            "current_readonly_lanes": recommended,
            "eligible_next_source_families_min": 1,
            "eligible_next_source_families_max": 3,
        },
    }


def build_wave_receipt(snapshot: dict, history: dict) -> dict:
    progress = matched_progress(history.get("observations"))
    policy = adaptive_slice_policy(snapshot, progress)
    try:
        frontier_doc = json.loads(
            (ROOT / "source_frontier.json").read_text(encoding="utf-8")
        )
        frontier_rank = rank_source_slices(frontier_doc.get("candidates", []))
        source_frontier = {
            "coverage_observed_main_sha": frontier_doc.get(
                "coverage_observed_main_sha"
            ),
            "source_blob_recheck_main_sha": frontier_doc.get(
                "independent_blob_recheck_main_sha"
            ),
            "coverage_total_opportunities": frontier_doc.get(
                "coverage_total_opportunities"
            ),
            "source_candidates": frontier_doc.get("candidates"),
            "ranked": frontier_rank,
            "arithmetic_max_contribution_pp": frontier_doc.get(
                "arithmetic_max_contribution_pp_on_frozen_52200_denominator"
            ),
            "current_main_candidate_freshness": "NEEDS_EXACT_CURRENT_HEAD_BLOB_RECHECK",
            "qualified_current_main_coverage_uplift": None,
        }
    except (OSError, ValueError, TypeError, ProofError) as e:
        source_frontier = {
            "status": "CANDIDATE_PROOF_UNAVAILABLE",
            "error": str(e)[:100],
            "source_candidates": None,
        }
    # Only accepted, terminal, non-replayed engineering waves are eligible.
    # Historical N0/queued events are retained in provenance but excluded.
    try:
        engineering = json.loads(
            (ROOT / "engineering_wave_history.json").read_text(encoding="utf-8")
        )
        engineering_result = evaluate_engineering_convergence(
            engineering.get("observations", []),
            target_pct=engineering.get("target_coverage_percent", 95.0),
            consecutive_no_change=engineering.get("consecutive_no_change_required", 3),
        )
    except (OSError, ValueError, TypeError) as exc:
        engineering_result = {
            "state": "CONVERGENCE_PROOF_UNAVAILABLE",
            "error": str(exc)[:120],
            "stop_entire_program": False,
        }
    # W33 is pinned to an older exact-head focused test run, not the moving
    # main head. Never interpret a cached candidate evaluation as fresh B0.
    try:
        elastic_input = json.loads(
            (ROOT / "w33_verified_focused_input.json").read_text(encoding="utf-8")
        )
        elastic_result = evaluate_elastic_wave(elastic_input)
        elastic_result["measurement_freshness"] = (
            "HISTORICAL_FOCUSED_SOURCE_HEAD_NOT_EXACT_CURRENT_MAIN"
        )
        elastic_result["source_head_equals_current_main"] = elastic_input[
            "snapshot_source_sha"
        ] == snapshot.get("main", {}).get("sha")
    except (OSError, ValueError, TypeError) as exc:
        elastic_result = {
            "state": "W33_CONTROLLER_INPUT_UNQUALIFIED",
            "error": str(exc)[:180],
            "governed_merge_admission": "HOLD",
        }
    return {
        "schema": "codepurple.adaptive_wave_receipt.v1",
        "elastic_controller": elastic_result,
        "main_sha": snapshot.get("main", {}).get("sha"),
        "current_main_coverage_sha": (
            snapshot.get("coverage", {}).get("measured") or {}
        ).get("sha"),
        "historical_focus": progress,
        "scale_policy": policy,
        "source_frontier": source_frontier,
        "engineering_convergence": engineering_result,
        "root_census_owner": "https://github.com/GBOGEB/ABACUS/issues/1929",
        "admission_owner": "https://github.com/GBOGEB/ABACUS/issues/1860",
        "dispatch_owner": "https://github.com/GBOGEB/CODEX/issues/977",
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=ROOT / "evidence.json")
    parser.add_argument("--history", type=Path, default=ROOT / "wave_history.json")
    parser.add_argument("--out", type=Path, default=ROOT / "wave.latest.json")
    args = parser.parse_args(argv)
    receipt = build_wave_receipt(
        json.loads(args.snapshot.read_text(encoding="utf-8")),
        json.loads(args.history.read_text(encoding="utf-8")),
    )
    args.out.write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"WAVE_POLICY main={receipt['main_sha']} readonly_lanes={receipt['scale_policy']['read_only_parallel_lanes_max']} "
        f"covered={receipt['historical_focus']['observations'][-1]['covered']}/"
        f"{receipt['historical_focus']['fixed_opportunity_denominator']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
