"""Native B0 three-pulse evidence projection, without invented independent trials.

Each record is a specific GitHub run attempt at an exact commit. Repeated first-red
test identities can be de-duplicated, but are not independently sampled causal roots.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

SHA = re.compile(r"[0-9a-f]{40}")
RUN_NAMES = {
    "B0 canonical coverage producer",
    "B0 report-only admission census",
}
FIRST_RED = (
    "tests/test_cbd_e2e_temporal.py::"
    "test_skipped_clock_anomaly_is_one_cluster_ten_manifestations"
)
AUTHORITY = {
    "merge_admission": "HOLD",
    "security_waiver": False,
    "independent_review": "UNKNOWN",
    "source_owner_repair": "PR_2107_ONLY",
    "fleet_closure": None,
    "coverage_delta": None,
}


def require(condition, reason):
    """Fail closed on source, attempts and denominator inconsistencies."""
    if not condition:
        raise ValueError(reason)


def timestamp(value):
    require(isinstance(value, str), "timestamp missing")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp malformed") from exc
    require(dt.utcoffset() is not None, "timestamp lacks timezone")
    return dt


def validate(data):
    """Validate all first-page native receipts and their explicit limitations."""
    require(
        isinstance(data, dict)
        and data.get("schema") == "cbd.b0.source_bound_pulses.v1",
        "bad schema",
    )
    require(data.get("repository") == "GBOGEB/ABACUS", "wrong repository")
    require(data.get("authority") == AUTHORITY, "authority promoted")
    require(
        data.get("scope")
        == "SELECTED_FIVE_NATIVE_EXACT_HEAD_B0_RUNS_NONRANDOM_NONATOMIC",
        "scope misrepresented",
    )
    records = data.get("records")
    require(
        isinstance(records, list) and len(records) == 5,
        "expected five native source-bound receipts",
    )
    unique_runs, unique_prs, red = set(), set(), 0
    for row in records:
        require(isinstance(row, dict), "invalid receipt row")
        pr, rid, attempt = row.get("pr"), row.get("run_id"), row.get("run_attempt")
        sha = row.get("source_sha")
        require(
            type(pr) is int and pr > 0 and pr not in unique_prs, "invalid duplicate PR"
        )
        unique_prs.add(pr)
        require(
            type(rid) is int and rid > 0 and rid not in unique_runs,
            "invalid duplicate run",
        )
        unique_runs.add(rid)
        require(type(attempt) is int and attempt > 0, "invalid run attempt")
        require(
            isinstance(sha, str) and SHA.fullmatch(sha), "invalid exact source head"
        )
        require(
            row.get("workflow") == "MIP B0 Test Admission and Coverage Evidence",
            "unrecognized workflow",
        )
        require(
            row.get("run_status") == "completed", "nonterminal run cannot be counted"
        )
        conclusion = row.get("conclusion")
        require(conclusion in ("success", "failure"), "unqualified workflow conclusion")
        created, updated = timestamp(row.get("created_at")), timestamp(
            row.get("updated_at")
        )
        require(updated >= created, "inverted workflow timestamps")
        total, good = row.get("job_total"), row.get("success_jobs")
        failed = row.get("failed_jobs")
        require(
            type(total) is int
            and total > 0
            and type(good) is int
            and good >= 0
            and isinstance(failed, list)
            and total == good + len(failed),
            "native terminal job denominator mismatch",
        )
        require(
            (conclusion == "success") == (len(failed) == 0),
            "run/job outcome contradiction",
        )
        failed_ids = set()
        for job in failed:
            require(
                type(job.get("id")) is int
                and job["id"] > 0
                and job["id"] not in failed_ids,
                "duplicate native job",
            )
            failed_ids.add(job["id"])
            require(job.get("name") in RUN_NAMES, "unclassified failed job")
            require(
                isinstance(job.get("steps"), list)
                and job["steps"]
                and all(isinstance(s, str) and s for s in job["steps"]),
                "missing native failed steps",
            )
        names = {job["name"] for job in failed}
        require(
            names == RUN_NAMES if conclusion == "failure" else names == set(),
            "downstream summary not separated from producer",
        )
        signature = row.get("first_red_case")
        require(
            signature == FIRST_RED if conclusion == "failure" else signature is None,
            "first-red test identity unqualified",
        )
        test = row.get("test_summary")
        if test is not None:
            require(
                isinstance(test, dict)
                and all(
                    type(test.get(k)) is int and test[k] >= 0
                    for k in ("passed", "failed", "skipped")
                ),
                "invalid test denominator",
            )
            require(
                (test["failed"] > 0) == (conclusion == "failure"),
                "test outcome contradicts B0",
            )
        if conclusion == "failure":
            red += 1
    require(red == 3, "source census changed; requalify counts")
    return records


def project(data):
    """Count exact native manifestations and explicit independent unknowns."""
    rows = validate(data)
    observed = Counter()
    signatures = Counter()
    timeline = []
    for row in rows:
        failure = row["conclusion"] == "failure"
        observed[row["conclusion"]] += 1
        observed["job_success"] += row["success_jobs"]
        observed["job_failed"] += len(row["failed_jobs"])
        observed["first_red_producer"] += int(failure)
        observed["dependent_summary"] += int(failure)
        if failure:
            signatures[row["first_red_case"]] += 1
        created = timestamp(row["created_at"])
        updated = timestamp(row["updated_at"])
        timeline.append(
            {
                "pr": row["pr"],
                "source_sha": row["source_sha"],
                "run_id": row["run_id"],
                "attempt": row["run_attempt"],
                "role": row["role"],
                "conclusion": row["conclusion"],
                "jobs_success": row["success_jobs"],
                "jobs_failed": len(row["failed_jobs"]),
                "test_summary": row["test_summary"],
                "created_to_last_update_ms": int(
                    (updated - created).total_seconds() * 1000
                ),
                "actual_queue_wait_ms": None,
                "first_red_signature": row["first_red_case"],
            }
        )
    repair = next(r for r in timeline if r["pr"] == 2107)
    baseline = next(r for r in timeline if r["pr"] == 2104)
    require(
        repair["conclusion"] == "success" and baseline["conclusion"] == "failure",
        "repair verdict does not support comparison",
    )
    observed["native_job_records"] = observed["job_success"] + observed["job_failed"]
    require(observed["native_job_records"] == 65, "unexpected sampled job denominator")
    return {
        "schema": "cbd.b0.pulse_projection.v1",
        "sampled_runs": 5,
        "sampled_native_jobs": observed["native_job_records"],
        "native_successful_jobs": observed["job_success"],
        "native_failed_jobs": observed["job_failed"],
        "workflow_successes": observed["success"],
        "workflow_failures": observed["failure"],
        "failed_first_red_producer_jobs": observed["first_red_producer"],
        "downstream_summary_failures": observed["dependent_summary"],
        "distinct_failing_test_signatures": len(signatures),
        "failing_test_manifestations": sum(signatures.values()),
        "first_red_cases": dict(sorted(signatures.items())),
        "baseline_to_owned_repair": {
            "old_pr": baseline["pr"],
            "new_pr": repair["pr"],
            "old_source_sha": baseline["source_sha"],
            "new_source_sha": repair["source_sha"],
            "old_b0_conclusion": baseline["conclusion"],
            "new_b0_conclusion": repair["conclusion"],
            "old_success_jobs": baseline["jobs_success"],
            "new_success_jobs": repair["jobs_success"],
            "workflow_result_changed_to_pass": True,
            "same_head_trial": False,
            "population_effect_size": None,
            "main_merge": False,
        },
        "timeline": sorted(timeline, key=lambda r: r["run_id"]),
        "integrated_feature_branch_qualified": None,
        "local_pre_push_stage_proven": None,
        "fresh_clone_parity_proven": None,
        "statement_coverage_percent": None,
        "branch_coverage_percent": None,
        "changed_line_coverage_percent": None,
        "security_governance_a10_admission": "HOLD",
        "independent_causal_root_count": None,
        "root_owner": "PR_2107_ONLY",
        "parent_feature_main_merge": False,
        "statistical_validity": {
            "nonrandom_nonatomic_selected_heads": True,
            "different_heads_not_independent_trials": True,
            "job_duration_not_ci_savings": True,
            "run_created_to_updated_not_runner_queue_time": True,
            "test_count_changes_not_line_coverage": True,
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    evidence = json.loads(args.source.read_text(encoding="utf-8"))
    result = project(evidence)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "sampled_runs",
                    "native_successful_jobs",
                    "native_failed_jobs",
                    "distinct_failing_test_signatures",
                )
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
