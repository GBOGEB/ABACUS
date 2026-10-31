"""Evidence-qualified W31 convergence and adaptive expansion state machine.

A repeated GET of one GitHub run is *never* another wave. A plateau requires
three distinct, completed, source-changing engineering pulses with comparable
coverage cohorts. Governance and accepted roots are independent from coverage.
No write, review, merge, credential, Crew or engineering-root authority.
"""

from __future__ import annotations

import math
import re
from typing import Any

SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")


class ConvergenceProofError(ValueError):
    """Evidence is missing, nonterminal or not source-comparable."""


def _positive_int(value: Any, label: str, minimum: int = 1) -> int:
    if type(value) is not int or value < minimum:
        raise ConvergenceProofError(f"{label}: expected integer >= {minimum}")
    return value


def _sha(value: Any, label: str, expression: re.Pattern) -> str:
    if not isinstance(value, str) or not expression.fullmatch(value):
        raise ConvergenceProofError(f"{label}: exact hash required")
    return value


def _observation(row: dict) -> dict:
    if not isinstance(row, dict):
        raise ConvergenceProofError("wave: expected object")
    result = dict(row)
    _positive_int(row.get("wave"), "wave")
    _positive_int(row.get("run_id"), "run_id")
    _positive_int(row.get("run_attempt"), "run_attempt")
    _sha(row.get("source_sha"), "source_sha", SHA40)
    _sha(row.get("artifact_digest"), "artifact_digest", SHA64)
    _sha(row.get("configuration_digest"), "configuration_digest", SHA64)
    _sha(row.get("cohort_digest"), "cohort_digest", SHA64)
    if not isinstance(row.get("source_slice"), str) or not row["source_slice"].strip():
        raise ConvergenceProofError(
            "source_slice: unique source-work identity required"
        )
    _positive_int(row.get("eligible"), "eligible")
    _positive_int(row.get("covered"), "covered", 0)
    if row["covered"] > row["eligible"]:
        raise ConvergenceProofError("covered exceeds eligible")
    for field in (
        "job_expected",
        "job_success",
        "test_passed",
        "test_failed",
        "test_skipped",
        "cases_added",
    ):
        _positive_int(row.get(field), field, 0)
    if row["job_expected"] < 1 or row["job_success"] > row["job_expected"]:
        raise ConvergenceProofError("native job population is missing or inconsistent")
    if (
        row.get("terminal") is not True
        or row.get("head_stable") is not True
        or row["job_success"] != row["job_expected"]
        or row["test_passed"] == 0
        or row["test_failed"] != 0
        or row["test_skipped"] != 0
    ):
        raise ConvergenceProofError("terminal exact-head full-pass proof unavailable")
    if not isinstance(row.get("first_red_signatures"), list) or any(
        not isinstance(x, str) or not x for x in row["first_red_signatures"]
    ):
        raise ConvergenceProofError("first-red identity must be explicit list")
    if len(set(row["first_red_signatures"])) != len(row["first_red_signatures"]):
        raise ConvergenceProofError("duplicate first-red signature")
    if not isinstance(row.get("root_dispositions_complete"), bool):
        raise ConvergenceProofError("root disposition observation must be explicit")
    queue = row.get("queue_p95_seconds")
    if queue is not None and (
        type(queue) not in (int, float) or not math.isfinite(queue) or queue < 0
    ):
        raise ConvergenceProofError("runner queue p95 invalid; UNKNOWN must be null")
    if row.get("attempted_new_behavior") is not True:
        raise ConvergenceProofError(
            "repeat without an independent engineering attack is not convergence"
        )
    return result


def evaluate(
    history: list[dict],
    *,
    target_pct: float = 95.0,
    consecutive_no_change: int = 3,
    queue_limit: float = 900.0,
) -> dict:
    """Classify evidence, not test intensity. No predicted coverage is returned.

    A completed engineering wave has a distinct source SHA, run ID, artifact,
    source slice, matching config/cohort/denominator, and evidence of a genuine
    new behavioral attack. Three *zero-delta transitions* need four waves.
    These rules avoid N->N+1 aliases and A->B->A source replays.
    """
    _positive_int(consecutive_no_change, "consecutive_no_change")
    if (
        not isinstance(target_pct, (float, int))
        or isinstance(target_pct, bool)
        or not 0 < target_pct <= 100
    ):
        raise ConvergenceProofError("target_pct must be in (0,100]")
    if (
        type(queue_limit) not in (int, float)
        or not math.isfinite(queue_limit)
        or queue_limit <= 0
    ):
        raise ConvergenceProofError("queue_limit invalid")
    if not isinstance(history, list):
        raise ConvergenceProofError("history must be list")
    if not history:
        return {
            "state": "AWAIT_FIRST_TERMINAL_OBSERVATION",
            "verified_waves": 0,
            "no_change_streak": 0,
            "next_action": "Collect terminal exact-head proof",
            "stop_engineering_wave": False,
            "governed_merge_credit": None,
        }
    try:
        rows = [_observation(r) for r in history]
    except ConvergenceProofError as exc:
        return {
            "state": "EVIDENCE_BLOCKED",
            "verified_waves": 0,
            "no_change_streak": 0,
            "blocker": str(exc),
            "next_action": "Repair source-owned first-red or complete terminal receipts",
            "stop_engineering_wave": False,
            "governed_merge_credit": None,
        }
    for field in ("wave", "run_id", "source_sha", "artifact_digest", "source_slice"):
        values = [r[field] for r in rows]
        if len(values) != len(set(values)):
            raise ConvergenceProofError(
                f"reused {field}: repeated check is not a new wave"
            )
    waves = [x["wave"] for x in rows]
    if waves != list(range(waves[0], waves[-1] + 1)):
        raise ConvergenceProofError("wave IDs must increase consecutively without gaps")
    for field in ("eligible", "configuration_digest", "cohort_digest"):
        if len({x[field] for x in rows}) != 1:
            return {
                "state": "INCOMPARABLE_COHORT",
                "verified_waves": len(rows),
                "no_change_streak": 0,
                "cohort_difference": field,
                "next_action": "Remeasure baseline and candidate on an identical eligible cohort",
                "stop_engineering_wave": False,
                "governed_merge_credit": None,
            }
    latest = rows[-1]
    plateau = 0
    changes = []
    for before, after in zip(rows, rows[1:]):
        change = after["covered"] - before["covered"]
        changes.append(change)
        plateau = plateau + 1 if change == 0 else 0
    percentage = 100 * latest["covered"] / latest["eligible"]
    queue = latest["queue_p95_seconds"]
    queue_safe = queue is not None and queue <= queue_limit
    if changes and changes[-1] < 0:
        state, next_action = (
            "COVERAGE_REGRESSION",
            "Repair and retest regression before scaling",
        )
    elif latest["first_red_signatures"]:
        state, next_action = (
            "FIRST_RED_UNRESOLVED",
            "Repair the observed first-red, then rerun exact head",
        )
    elif percentage >= target_pct:
        state, next_action = (
            "SOURCE_TARGET_REACHED",
            "Switch to next measured uncovered source family",
        )
    elif plateau >= consecutive_no_change:
        state, next_action = (
            "COHORT_PLATEAU_CONFIRMED",
            "Switch to independent uncovered cohort; do not infer program completion",
        )
    elif queue is None:
        state, next_action = (
            "QUEUE_PROOF_UNKNOWN",
            "Retain one observation lane until terminal runner clocks exist",
        )
    elif not queue_safe:
        state, next_action = (
            "CAPACITY_PRESSURE",
            "Decelerate; limit to one read-only lane",
        )
    elif changes and changes[-1] > 0:
        state, next_action = (
            "MEASURABLE_PROGRESS",
            "Continue next disjoint behavioral slice",
        )
    else:
        state, next_action = (
            "NOT_YET_CONVERGED",
            "Attempt next bounded source-owned slice",
        )
    # The scoped source cohort may converge while merger governance or causal
    # roots remain unresolved. That is not program closure or merge authority.
    stop_slice = state in {"SOURCE_TARGET_REACHED", "COHORT_PLATEAU_CONFIRMED"}
    return {
        "schema": "codepurple.wave_convergence.v1",
        "state": state,
        "next_action": next_action,
        "verified_waves": len(rows),
        "last_source_sha": latest["source_sha"],
        "last_run_id": latest["run_id"],
        "cohort_digest": latest["cohort_digest"],
        "configuration_digest": latest["configuration_digest"],
        "eligible": latest["eligible"],
        "covered": latest["covered"],
        "covered_percent": round(percentage, 6),
        "uncovered": latest["eligible"] - latest["covered"],
        "delta_covered_by_wave": changes,
        "no_change_streak": plateau,
        "consecutive_no_change_required": consecutive_no_change,
        "queue_p95_seconds": queue,
        "queue_qualified": queue_safe,
        "suggested_readonly_lanes": (
            3 if queue_safe and not latest["first_red_signatures"] else 1
        ),
        "root_dispositions_complete": latest["root_dispositions_complete"],
        "stop_this_source_slice": stop_slice,
        "stop_entire_program": False,
        "governed_merge_credit": None,
        "authenticated_crew_launches": None,
        "accepted_root_closures": None,
        "note": "Equal repeated observations from one SHA/run do not count as engineering wave convergence",
    }
