"""Pure, non-admitting, repeat-aware GitHub workflow cohort accounting.

This module never equates workflow executions with tests, coverage, repairs,
independent evidence or governed merges. API census completeness is a separate
upstream obligation; these calculations apply only to the supplied run rows.
"""
from __future__ import annotations

from collections import Counter, defaultdict

TERMINAL = frozenset({
    "success", "failure", "cancelled", "skipped", "neutral",
    "timed_out", "action_required", "startup_failure",
})
OPEN = frozenset({"queued", "pending", "in_progress", "requested", "waiting"})
FAILURES = frozenset({"failure", "timed_out", "action_required", "startup_failure"})


def _positive_integer(value):
    return type(value) is int and value > 0


def summarize_families(runs):
    """Return a non-causal breakdown by *workflow identity*, not test case.

    Repeated successful runs contribute to gross run success, but beyond the
    first success per workflow ID they are separately identified so that
    repeated QPS fan-out cannot masquerade as a broad quality improvement.
    """
    if not isinstance(runs, list) or not runs:
        raise ValueError("a nonempty native run list is required")

    families = defaultdict(list)
    seen = set()
    tally = Counter()
    for row in runs:
        if not isinstance(row, dict):
            raise ValueError("every run must be an object")
        rid, wf, attempt = (row.get("id"), row.get("workflow_id"),
                            row.get("run_attempt"))
        if not all(_positive_integer(v) for v in (rid, wf, attempt)):
            raise ValueError("run, workflow and attempt IDs must be positive integers")
        if rid in seen:
            raise ValueError("duplicate run identity in supplied cohort")
        seen.add(rid)
        status, conclusion = row.get("status"), row.get("conclusion")
        if status == "completed":
            if conclusion not in TERMINAL:
                raise ValueError("completed run missing recognized conclusion")
            outcome = conclusion
        elif status in OPEN:
            if conclusion is not None:
                raise ValueError("nonterminal run cannot have a conclusion")
            outcome = "nonterminal"
        else:
            raise ValueError("unrecognized workflow execution state")
        families[wf].append((rid, attempt, outcome))
        tally[outcome] += 1

    manifest = []
    family_clean_success = 0
    family_any_failure = 0
    family_any_cancelled = 0
    family_with_nonterminal = 0
    repeat_success_excess = 0
    repeated_executions = 0
    for wf, members in sorted(families.items()):
        c = Counter(outcome for _, _, outcome in members)
        count = len(members)
        if c["success"] == count:
            family_clean_success += 1
        if sum(c[x] for x in FAILURES):
            family_any_failure += 1
        if c["cancelled"]:
            family_any_cancelled += 1
        if c["nonterminal"]:
            family_with_nonterminal += 1
        repeated_executions += count - 1
        repeat_success_excess += max(c["success"] - 1, 0)
        manifest.append({
            "workflow_id": wf,
            "run_count": count,
            "success": c["success"],
            "failure": sum(c[x] for x in FAILURES),
            "cancelled": c["cancelled"],
            "nonterminal": c["nonterminal"],
            "other_terminal": c["skipped"] + c["neutral"],
            "run_ids": sorted(rid for rid, _, _ in members),
            "attempts_observed": sorted({attempt for _, attempt, _ in members}),
            "clean_success": c["success"] == count,
        })

    count = len(runs)
    distinct = len(families)
    terminal = count - tally["nonterminal"]
    return {
        "status": "READ_ONLY_GITHUB_RUN_COHORT_NOT_TEST_COVERAGE",
        "total_runs": count,
        "distinct_workflows": distinct,
        "repeated_executions": repeated_executions,
        "families_with_repeats": sum(m["run_count"] > 1 for m in manifest),
        "run_success": tally["success"],
        "run_failure": sum(tally[x] for x in FAILURES),
        "run_cancelled": tally["cancelled"],
        "run_nonterminal": tally["nonterminal"],
        "run_other_terminal": tally["skipped"] + tally["neutral"],
        "terminal_runs": terminal,
        "success_over_all_runs": round(tally["success"] / count, 6),
        "success_over_terminal_runs": (
            round(tally["success"] / terminal, 6) if terminal else None
        ),
        "family_clean_success": family_clean_success,
        "family_any_failure": family_any_failure,
        "family_any_cancelled": family_any_cancelled,
        "family_with_nonterminal": family_with_nonterminal,
        "family_clean_success_fraction": round(family_clean_success / distinct, 6),
        "success_excess_from_repeat_runs": repeat_success_excess,
        "success_after_one_per_family_cap": tally["success"] - repeat_success_excess,
        "repeat_adjusted_is_diagnostic_only": True,
        "workflow_testcase_count": None,
        "matched_statement_coverage": None,
        "verified_root_closure": None,
        "merge_authority": False,
        "manifest": manifest,
    }
