"""Deterministic, read-only MIP testflight DAG and exact-head retest planner.

This module schedules *recommendations*, not GitHub Actions or workers.
It cannot authenticate Crew, accept REX, grant review, or authorize merge.
Every source claim is pinned; absent data stays UNKNOWN, never a green/zero.
Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime
from pathlib import Path

SCHEMA = "abacus.mip.testflight-input.v1"
OUTPUT = "abacus.mip.testflight-plan.v1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
KINDS = (
    "static", "negative", "unit", "integration", "api", "gui",
    "package", "security", "governance", "a10", "coverage", "artifact",
    "debug", "federation", "rex", "full_ci", "root_census",
)
KIND_RANK = {k: n for n, k in enumerate(KINDS)}
PRIORITIES = {"P0": 0, "P1": 1, "P2": 2}
STATUS = {"completed", "queued", "in_progress", "waiting", "pending", "requested"}
CONCLUSIONS = {
    "success", "failure", "cancelled", "skipped", "timed_out", "neutral",
    "action_required", "stale", "startup_failure",
}
CASE_STATES = {"PASS", "FAIL", "ERROR", "SKIP"}


def _sha(value, name, length=40):
    pattern = HEX40 if length == 40 else HEX64
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise ValueError("invalid exact " + name)
    return value


def _positive(value, name):
    if type(value) is not int or value <= 0:
        raise ValueError(name + " must be a positive integer")
    return value


def _path(value):
    if (type(value) is not str or not value or value.startswith("/")
            or "\\" in value or "\x00" in value or value.endswith("/")
            or any(p in ("", ".", "..") for p in value.split("/"))):
        raise ValueError("unsafe or noncanonical relative path")
    return value


def _path_overlap(left, right):
    """Cross-platform conservative lexical file/directory lease overlap.

    Case folding protects Windows runners. Symlink/realpath identity cannot
    be authenticated by this read-only planner.
    """
    a, b = left.casefold(), right.casefold()
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def _list_unique(value, name, *, max_items=1000):
    if type(value) is not list or len(value) > max_items:
        raise ValueError(name + " must be a bounded list")
    if any(type(x) is not str for x in value) or len(set(value)) != len(value):
        raise ValueError(name + " contains invalid or duplicate identities")
    return value


def _tasks(payload):
    entries = payload.get("tasks")
    if type(entries) is not list or not entries or len(entries) > 200:
        raise ValueError("nonempty bounded tasks list required")
    by_id = {}
    for row in entries:
        if type(row) is not dict:
            raise ValueError("task object required")
        name = row.get("id")
        if type(name) is not str or ID.fullmatch(name) is None or name in by_id:
            raise ValueError("invalid or duplicate task ID")
        kind = row.get("kind")
        if kind not in KINDS:
            raise ValueError("unsupported task kind")
        required = row.get("required")
        if type(required) is not bool:
            raise ValueError("explicit boolean required flag needed")
        priority = row.get("priority")
        if priority not in PRIORITIES:
            raise ValueError("unknown priority")
        mode = row.get("mode", "LOCAL_TEST")
        if mode not in ("LOCAL_TEST", "REMOTE_OBSERVE", "CONTROLLED_MUTATION"):
            raise ValueError("unsupported execution mode")
        if mode == "REMOTE_OBSERVE" and kind != "federation":
            raise ValueError("remote observational jobs must be federation type")
        if kind == "rex" and mode != "CONTROLLED_MUTATION":
            raise ValueError("REX is not executable by this scheduler")
        deps = _list_unique(row.get("needs", []), "task dependencies", max_items=200)
        paths = _list_unique(row.get("paths", []), "task paths")
        for p in paths:
            _path(p)
        axes = _list_unique(row.get("axes", ["default"]), "matrix axes", max_items=40)
        if not axes or any(not ID.fullmatch(x) for x in axes):
            raise ValueError("nonempty valid matrix axes required")
        estimate = row.get("estimate_seconds")
        if estimate is not None and (type(estimate) not in (int, float)
                                     or not math.isfinite(estimate) or estimate <= 0
                                     or estimate > 1_000_000):
            raise ValueError("invalid non-evidence duration estimate")
        by_id[name] = dict(row, id=name, kind=kind, needs=deps, paths=paths,
                           axes=axes, mode=mode, required=required,
                           priority=priority, estimate_seconds=estimate)
    for name, row in by_id.items():
        if name in row["needs"] or any(dep not in by_id for dep in row["needs"]):
            raise ValueError("self dependency or missing upstream task")
    return by_id


def _waves(tasks, max_parallel):
    """Only read-only tasks can enter proposed batches, never mutation tasks."""
    _positive(max_parallel, "max_parallel")
    if max_parallel > 16:
        raise ValueError("unsupported parallelism cap")
    # Perform cycle detection across the *entire* DAG, including withheld tasks.
    remaining, observed = set(tasks), set()
    while remaining:
        ready = {k for k in remaining if set(tasks[k]["needs"]) <= observed}
        if not ready:
            raise ValueError("cyclic test or control dependency DAG")
        observed.update(ready)
        remaining -= ready
    blocked = {k for k, t in tasks.items() if t["mode"] == "CONTROLLED_MUTATION"}
    while True:
        new = blocked | {
            k for k, t in tasks.items() if set(t["needs"]) & blocked
        }
        if new == blocked:
            break
        blocked = new
    waiting, finished = set(tasks) - blocked, set()
    waves = []
    while waiting:
        ready = [tasks[k] for k in waiting if set(tasks[k]["needs"]) <= finished]
        if not ready:
            raise ValueError("unresolvable read-only test dependency")
        ready.sort(key=lambda t: (PRIORITIES[t["priority"]], KIND_RANK[t["kind"]], t["id"]))
        # Pack independent tasks into bounded parallel batches. A simple
        # max_parallel slice is unsafe: sibling tasks can claim the same
        # file, a parent directory, or a Windows case-folded path alias.
        remaining_ready = ready[:]
        batches = []
        while remaining_ready:
            selected, leased, deferred = [], [], []
            for task in remaining_ready:
                collision = any(
                    _path_overlap(path, other)
                    for path in task["paths"] for other in leased
                )
                if len(selected) < max_parallel and not collision:
                    selected.append(task)
                    leased.extend(task["paths"])
                else:
                    deferred.append(task)
            batches.append(selected)
            remaining_ready = deferred
        waves.append({
            "wave": len(waves) + 1,
            "batches": [[t["id"] for t in batch] for batch in batches],
            "task_ids": [t["id"] for t in ready],
            "predicted_wall_seconds": (
                sum(max(t["estimate_seconds"] for t in batch) for batch in batches)
                if all(t["estimate_seconds"] is not None for t in ready) else None
            ),
            "timing_class": "UNVALIDATED_ESTIMATE_NOT_NATIVE_DURATION",
            "lease_model": "CASEFOLDED_LEXICAL_PLAN_NOT_AUTHENTICATED",
        })
        finished.update(t["id"] for t in ready)
        waiting.difference_update(finished)
    return waves, sorted(blocked)


def _parse_native_timestamp(value):
    # Python 3.9 does not natively accept a terminal "Z"; keep UTC semantics.
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _interval_seconds(start, end):
    if start is None or end is None:
        return None
    if type(start) is not str or type(end) is not str:
        raise ValueError("invalid native timestamp type")
    try:
        t0 = _parse_native_timestamp(start)
        t1 = _parse_native_timestamp(end)
        interval = (t1 - t0).total_seconds()
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid native timestamp") from exc
    if not math.isfinite(interval) or interval < 0:
        raise ValueError("negative or nonfinite native interval")
    return interval


def _native_timing(j):
    queue = _interval_seconds(j.get("created_at"), j.get("started_at"))
    runtime = _interval_seconds(j.get("started_at"), j.get("completed_at"))
    elapsed = _interval_seconds(j.get("created_at"), j.get("completed_at"))
    if (j.get("status") != "completed" and j.get("completed_at") is not None):
        raise ValueError("nonterminal job has completed_at timestamp")
    if (queue is not None and runtime is not None and elapsed is not None
            and abs(queue + runtime - elapsed) > 0.001):
        raise ValueError("contradictory native timing timestamps")
    return {"queue_seconds": queue, "runtime_seconds": runtime}


def _nearest_rank(values, percentile):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(1, math.ceil(len(ordered) * percentile / 100)) - 1]


def _jobs(entries, expected_sha, tasks, name):
    if type(entries) is not list or len(entries) > 300:
        raise ValueError(name + " must be a bounded list")
    by_task = {}
    seen = set()
    for j in entries:
        if type(j) is not dict:
            raise ValueError("native job object required")
        task = j.get("task_id")
        axis = j.get("axis", "default")
        if task not in tasks or axis not in tasks[task]["axes"]:
            raise ValueError("unknown task or undeclared matrix axis")
        _sha(j.get("source_sha"), "job source SHA")
        if j["source_sha"] != expected_sha:
            raise ValueError("stale or mixed job source SHA")
        ident = tuple(_positive(j.get(k), k) for k in ("run_id", "run_attempt", "job_id"))
        if ident in seen:
            raise ValueError("duplicate native run/attempt/job identity")
        seen.add(ident)
        if j.get("status") not in STATUS:
            raise ValueError("unknown native job status")
        conclusion = j.get("conclusion")
        if (j["status"] == "completed") != (conclusion in CONCLUSIONS):
            raise ValueError("missing or contradictory native terminal conclusion")
        checkout = j.get("checkout_sha")
        if checkout is not None:
            _sha(checkout, "checkout SHA")
        if j.get("receipt_source_sha") is not None:
            _sha(j["receipt_source_sha"], "artifact receipt source SHA")
        key = (task, axis)
        if key in by_task:
            raise ValueError("ambiguous native selection for task and axis")
        _native_timing(j)
        by_task[key] = j
    return by_task


def _task_result(task, selected, source_sha):
    selected_rows = [selected.get((task["id"], axis)) for axis in task["axes"]]
    if not any(selected_rows):
        return "NEEDS_EXACT_HEAD_RUN"
    if any(row is None for row in selected_rows):
        return "MISSING_REQUIRED_MATRIX_AXIS"
    if any(row.get("checkout_sha") != source_sha for row in selected_rows):
        return "UNVERIFIED_CHECKOUT_IDENTITY"
    if any(row["status"] != "completed" for row in selected_rows):
        return "PENDING_NATIVE_JOBS"
    if any(row["conclusion"] in ("failure", "timed_out", "startup_failure", "action_required")
           for row in selected_rows):
        return "OBSERVED_RED"
    if any(row["conclusion"] != "success" for row in selected_rows):
        return "NOT_PROVEN_GREEN"
    return "EXACT_HEAD_TEST_JOBS_GREEN"


def _cases(block, expected_sha, name):
    if block is None:
        return None
    if type(block) is not dict or block.get("source_sha") != expected_sha:
        raise ValueError(name + " must match declared exact source")
    for field in ("selection_digest", "environment_digest", "definition_digest"):
        _sha(block.get(field), name + " " + field, 64)
    if type(block.get("complete")) is not bool:
        raise ValueError("explicit case-collection completeness required")
    cases = block.get("cases")
    if type(cases) is not list or len(cases) > 100_000:
        raise ValueError("bounded test case list required")
    index = {}
    for case in cases:
        if type(case) is not dict:
            raise ValueError("invalid test case")
        case_id, result = case.get("id"), case.get("outcome")
        if type(case_id) is not str or not case_id or case_id in index or result not in CASE_STATES:
            raise ValueError("missing/duplicate test identity or invalid case outcome")
        duration = case.get("duration_seconds")
        if duration is not None and (type(duration) not in (int, float)
                                     or not math.isfinite(duration) or duration < 0):
            raise ValueError("invalid native testcase duration")
        index[case_id] = result
    if block["complete"] and not cases:
        raise ValueError("zero collected tests cannot be certified complete")
    return block, index


def _case_transitions(prior, current):
    if prior is None or current is None:
        return {"state": "UNKNOWN", "comparable": None, "events": None,
                "reason": "complete native per-test cohorts not supplied"}
    before, b = prior
    after, a = current
    if not before["complete"] or not after["complete"]:
        return {"state": "UNKNOWN", "comparable": None, "events": None,
                "reason": "incomplete test collection"}
    fields = ("selection_digest", "environment_digest", "definition_digest")
    comparable = all(before[f] == after[f] for f in fields)
    events = []
    for name in sorted(set(b) | set(a)):
        left = b.get(name, "NOT_COLLECTED")
        right = a.get(name, "NOT_COLLECTED")
        if left == right:
            continue
        if right == "NOT_COLLECTED":
            kind = "TEST_DISAPPEARED"
        elif left == "NOT_COLLECTED":
            kind = "NEW_TEST_RED" if right in ("FAIL", "ERROR") else "NEW_TEST_ADDED"
        elif left == "PASS" and right in ("FAIL", "ERROR"):
            kind = "PREVIOUS_GREEN_NOW_RED" if comparable else "RED_UNMATCHED_COHORT"
        elif left in ("FAIL", "ERROR") and right == "PASS":
            kind = "RED_CLEARED_TEST_ONLY"
        elif left == "PASS" and right == "SKIP":
            kind = "PASS_TO_SKIP_TEST_OBLIGATION_LOSS"
        else:
            kind = "OTHER_TEST_TRANSITION"
        events.append({"test_id": name, "prior": left, "current": right,
                       "kind": kind, "accepted_root_closure": None})
    return {"state": "OBSERVED", "comparable": comparable, "events": events,
            "reason": None if comparable else "mismatched case selection/environment/definition"}


def compile_plan(payload):
    """Validate inputs then propose test waves; no side effects or claims of launch."""
    if type(payload) is not dict or payload.get("schema") != SCHEMA:
        raise ValueError("unsupported input schema")
    if payload.get("repository") != "GBOGEB/ABACUS":
        raise ValueError("ABACUS-local planning only")
    source_sha = _sha(payload.get("source_sha"), "head SHA")
    previous_sha = _sha(payload.get("previous_sha"), "previous SHA")
    _sha(payload.get("base_sha"), "base SHA")
    if previous_sha == source_sha:
        raise ValueError("distinct temporal source SHAs required")
    changed = _list_unique(payload.get("changed_paths"), "changed paths")
    for p in changed:
        _path(p)
    tasks = _tasks(payload)
    waves, withheld = _waves(tasks, payload.get("max_parallel", 2))
    current = _jobs(payload.get("current_jobs", []), source_sha, tasks, "current_jobs")
    previous = _jobs(payload.get("previous_jobs", []), previous_sha, tasks, "previous_jobs")
    cases = _case_transitions(
        _cases(payload.get("previous_cases"), previous_sha, "previous_cases"),
        _cases(payload.get("current_cases"), source_sha, "current_cases"),
    )
    entries = []
    for task in sorted(tasks.values(), key=lambda t: (PRIORITIES[t["priority"]], KIND_RANK[t["kind"]], t["id"])):
        result = _task_result(task, current, source_sha)
        prior = _task_result(task, previous, previous_sha)
        receipt_values = [current[(task["id"], axis)].get("receipt_source_sha")
                          for axis in task["axes"] if (task["id"], axis) in current]
        if any(v != source_sha for v in receipt_values if v is not None):
            receipt_identity = "MISMATCH_REJECT_ARTIFACT_SOURCE"
        elif receipt_values and all(v == source_sha for v in receipt_values):
            receipt_identity = "DECLARED_MATCH_BYTES_UNVERIFIED"
        else:
            receipt_identity = "UNKNOWN"
        if task["mode"] == "CONTROLLED_MUTATION":
            decision = "WITHHELD_REQUIRES_SEPARATE_AUTHORITY"
        elif task["id"] in withheld:
            decision = "BLOCKED_BEHIND_WITHHELD_AUTHORITY"
        elif receipt_identity == "MISMATCH_REJECT_ARTIFACT_SOURCE":
            decision = "REPAIR_SOURCE_RECEIPT_IDENTITY"
        elif result == "OBSERVED_RED":
            decision = "FIRST_RED_TRIAGE"
        elif result == "EXACT_HEAD_TEST_JOBS_GREEN":
            decision = "OBSERVED_TEST_GREEN_NOT_ADMISSION"
        elif not task["required"] and not task["paths"] and not changed:
            decision = "OPTIONAL_REVIEW_NO_AUTO_SKIP"
        else:
            decision = "EXACT_HEAD_RETEST_OR_EVIDENCE_REQUIRED"
        if prior == "EXACT_HEAD_TEST_JOBS_GREEN" and result == "OBSERVED_RED":
            transition = "PREVIOUS_GREEN_NOW_RED_JOB"
        elif prior == "OBSERVED_RED" and result == "EXACT_HEAD_TEST_JOBS_GREEN":
            transition = "PREVIOUS_RED_NOW_GREEN_JOB"
        elif result == "OBSERVED_RED":
            transition = "CURRENT_RED_BASELINE_UNKNOWN_OR_RED"
        else:
            transition = "NO_VERIFIED_JOB_TRANSITION"
        entries.append({
            "id": task["id"], "kind": task["kind"], "priority": task["priority"],
            "required": task["required"], "mode": task["mode"],
            "needs": task["needs"], "axes": task["axes"],
            "paths_intersect_changed": bool(set(task["paths"]) & set(changed)) if task["paths"] else None,
            "previous": prior, "current": result, "transition": transition,
            "artifact_receipt_identity": receipt_identity,
            "decision": decision, "native_job_evidence": [
                {k: current[(task["id"], axis)].get(k) for k in
                 ("source_sha", "checkout_sha", "receipt_source_sha", "run_id", "run_attempt", "job_id", "status", "conclusion")}
                for axis in task["axes"] if (task["id"], axis) in current
            ],
        })
    timing = [_native_timing(j) for j in current.values()]
    queue_samples = [x["queue_seconds"] for x in timing if x["queue_seconds"] is not None]
    runtime_samples = [x["runtime_seconds"] for x in timing if x["runtime_seconds"] is not None]
    return {
        "schema": OUTPUT, "repository": payload["repository"],
        "base_sha": payload["base_sha"], "previous_sha": previous_sha,
        "source_sha": source_sha, "changed_paths_count": len(changed),
        "waves": waves, "withheld_task_ids": withheld,
        "task_count": len(entries), "tasks": entries,
        "native_queue_samples": len(queue_samples),
        "native_runtime_samples": len(runtime_samples),
        "queue_seconds_p50": _nearest_rank(queue_samples, 50),
        "queue_seconds_p95": _nearest_rank(queue_samples, 95),
        "runtime_seconds_p50": _nearest_rank(runtime_samples, 50),
        "runtime_seconds_p95": _nearest_rank(runtime_samples, 95),
        "timing_inference": "DESCRIPTIVE_ONLY_NOT_INDEPENDENT_STABILITY_CYCLES",
        "test_case_comparison": cases,
        "native_current_job_observations": len(current),
        "independent_stable_cycles": None, "spc_control_limit": None,
        "accepted_root_closures": None, "crew_launch_authenticated": None,
        "accepted_rex_receipts": None, "merge_authorized": False,
        "security_waiver": False, "authority_transfer": False,
        "admission": "HOLD", "dispatch": "NOT_PERFORMED_READ_ONLY_PLAN",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    opts = parser.parse_args()
    result = compile_plan(json.loads(Path(opts.input).read_text(encoding="utf-8")))
    Path(opts.output).write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("proposed waves:", len(result["waves"]), "tasks:", result["task_count"], "admission: HOLD")


if __name__ == "__main__":
    main()