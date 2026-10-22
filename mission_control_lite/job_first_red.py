"""Exact-head terminal-job first-red observations, not causal attribution."""

from collections import Counter

CONCLUSIONS = frozenset(
    {
        "success",
        "failure",
        "cancelled",
        "skipped",
        "neutral",
        "timed_out",
        "action_required",
    }
)


def _sha(value):
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(char in "0123456789abcdef" for char in value)
    )


def summarize(head_sha, run_heads, jobs):
    """Join terminal jobs to run source identities without awarding closures."""
    if not _sha(head_sha):
        raise ValueError("canonical exact head SHA required")
    if not isinstance(run_heads, dict) or not isinstance(jobs, list):
        raise ValueError("run-head mapping and job list required")
    if any(type(key) is not int or not _sha(value) for key, value in run_heads.items()):
        raise ValueError("invalid run-head mapping")
    if any(value != head_sha for value in run_heads.values()):
        raise ValueError("run-head drift")
    seen = set()
    candidates = Counter()
    failed = 0
    observed = 0
    records = []
    for job in jobs:
        if not isinstance(job, dict):
            raise ValueError("job must be a record")
        job_id = job.get("id")
        run_id = job.get("run_id")
        if (
            type(job_id) is not int
            or job_id < 1
            or type(run_id) is not int
            or run_id not in run_heads
            or job_id in seen
        ):
            raise ValueError("duplicate, unbound or invalid job ID")
        seen.add(job_id)
        name = job.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("missing job name")
        if job.get("status") != "completed" or job.get("conclusion") not in CONCLUSIONS:
            raise ValueError("nonterminal job")
        steps = job.get("steps", [])
        if not isinstance(steps, list):
            raise ValueError("invalid steps")
        step_numbers = set()
        failing_steps = []
        for step in steps:
            if not isinstance(step, dict):
                raise ValueError("invalid step")
            number, label = step.get("number"), step.get("name")
            if (
                type(number) is not int
                or number < 1
                or number in step_numbers
                or not isinstance(label, str)
                or not label
            ):
                raise ValueError("invalid or duplicate step identity")
            step_numbers.add(number)
            if step.get("conclusion") == "failure":
                if step.get("status") != "completed":
                    raise ValueError("nonterminal failed step")
                failing_steps.append((number, label))
        first_step = None
        if job["conclusion"] == "failure":
            failed += 1
            if failing_steps:
                first_step = min(failing_steps)[1]
                candidates[(name, first_step)] += 1
                observed += 1
        records.append(
            {
                "run_id": run_id,
                "job_id": job_id,
                "job_name": name,
                "result": job["conclusion"],
                "first_failed_step": first_step,
            }
        )
    return {
        "schema": "mcl.job-first-red.v1",
        "source_sha": head_sha,
        "runs_in_scope": len(run_heads),
        "terminal_jobs": len(records),
        "failed_jobs": failed,
        "first_red_observed_jobs": observed,
        "first_red_unknown_jobs": failed - observed,
        "first_red_observed_fraction": observed / failed if failed else None,
        "candidate_groups": [
            {"job_name": name, "step_name": step, "manifestations": count}
            for (name, step), count in sorted(
                candidates.items(), key=lambda pair: (-pair[1], pair[0])
            )
        ],
        "records": sorted(records, key=lambda row: (row["run_id"], row["job_id"])),
        "root_cause_confirmed": False,
        "verified_root_closures": 0,
        "merge_admission": "HOLD",
        "note": "Failed-step candidates are not authenticated causal roots.",
    }
