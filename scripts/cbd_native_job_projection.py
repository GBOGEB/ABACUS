"""Read-only native job/step projection for source-bound CBD! failure cohorts.

Native job labels and failing steps are candidate symptoms, not causal roots.
No merge decision, worker dispatch, scanner bypass, or BD register mutation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

SHA = re.compile(r"[a-f0-9]{40}")
EXPECTED_AUTHORITY = {
    "merge_admission": "HOLD",
    "security_waiver": False,
    "authority_transfer": False,
    "dispatch": "NOT_LAUNCHED",
}
SUMMARY_JOB = "Full Red Proof Summary"
JOB_FAMILIES = {
    "Security Scanning": ("SECURITY", "P0"),
    "Code Quality Checks": ("QUALITY", "P1"),
    "Code Coverage": ("COVERAGE", "P1"),
    SUMMARY_JOB: ("DOWNSTREAM_SUMMARY", "DEPENDENT"),
}


def require(ok: bool, reason: str) -> None:
    """Raise on missing or contradictory evidence, never return a green default."""
    if not ok:
        raise ValueError(reason)


def digest(value: object) -> str:
    """Hash canonical JSON without relying on order of dictionary keys."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def validate(documents: list[dict]) -> list[dict]:
    """Validate source identity, job counts and nested failed-step evidence."""
    require(bool(documents), "missing native job documents")
    source_runs = []
    seen_runs = set()
    seen_jobs = set()
    for document in documents:
        require(isinstance(document, dict), "invalid document")
        require(
            document.get("schema") == "cbd.native_ci_job_snapshot.v1"
            and document.get("repository") == "GBOGEB/ABACUS",
            "invalid repository/schema",
        )
        require(
            document.get("authority") == EXPECTED_AUTHORITY,
            "authority promotion or waiver",
        )
        require(
            document.get("scope") == "NATIVE_LATEST_ATTEMPT_FIRST_PAGE_JOBS_PER_RUN",
            "unsupported collection scope",
        )
        rows = document.get("runs")
        require(isinstance(rows, list) and rows, "missing run rows")
        for run in rows:
            require(isinstance(run, dict), "invalid run")
            pr, run_id, source_sha = (
                run.get("pr"),
                run.get("run_id"),
                run.get("source_head_sha"),
            )
            require(
                type(pr) is int
                and pr > 0
                and type(run_id) is int
                and run_id > 0
                and isinstance(source_sha, str)
                and SHA.fullmatch(source_sha) is not None,
                "invalid run/PR head identity",
            )
            require(run_id not in seen_runs, "duplicate native run")
            seen_runs.add(run_id)
            require(run.get("workflow") == "CI/CD Test Suite", "wrong workflow")
            total = run.get("job_total")
            jobs = run.get("jobs")
            require(
                type(total) is int
                and total >= 0
                and isinstance(jobs, list)
                and len(jobs) <= total,
                "invalid native job denominator",
            )
            for job in jobs:
                require(isinstance(job, dict), "invalid job")
                job_id, attempt = job.get("job_id"), job.get("run_attempt")
                require(
                    type(job_id) is int
                    and job_id > 0
                    and job_id not in seen_jobs
                    and type(attempt) is int
                    and attempt > 0,
                    "duplicate/unknown native job identity or attempt",
                )
                seen_jobs.add(job_id)
                require(
                    job.get("head_sha") == source_sha,
                    "job head differs from PR source",
                )
                require(
                    isinstance(job.get("job_name"), str)
                    and bool(job["job_name"].strip()),
                    "missing job name",
                )
                status = job.get("status")
                conclusion = job.get("conclusion")
                require(
                    status in ("completed", "queued", "in_progress", "waiting", "pending")
                    and conclusion
                    in ("success", "failure", "cancelled", "skipped", None),
                    "unsupported job status",
                )
                require(
                    (status == "completed") == (conclusion is not None),
                    "nonterminal or terminal evidence contradiction",
                )
                failed_steps = job.get("failed_steps")
                require(isinstance(failed_steps, list), "missing step list")
                if conclusion != "failure":
                    require(not failed_steps, "failed step on nonfailed job")
                step_numbers = set()
                for step in failed_steps:
                    require(isinstance(step, dict), "invalid step")
                    number, name = step.get("step_number"), step.get("step_name")
                    require(
                        type(number) is int
                        and number > 0
                        and number not in step_numbers
                        and isinstance(name, str)
                        and bool(name.strip()),
                        "invalid/duplicate failed step",
                    )
                    step_numbers.add(number)
            source_runs.append(run)
    return source_runs


def project(documents: list[dict]) -> dict:
    """Project independent-lane manifestations without causal-root promotion."""
    runs = validate(documents)
    by_family = defaultdict(
        lambda: {"prs": set(), "runs": set(), "jobs": 0, "steps": 0}
    )
    failures = []
    total_expected = 0
    total_fetched = 0
    pending_jobs = 0
    failed_jobs = 0
    failed_steps = 0
    summary_failures = 0
    non_summary_failures = 0
    runs_with_red = set()
    attempts = set()
    for run in runs:
        total_expected += run["job_total"]
        total_fetched += len(run["jobs"])
        for job in run["jobs"]:
            attempts.add((run["run_id"], job["run_attempt"]))
            if job["status"] != "completed":
                pending_jobs += 1
            if job["conclusion"] != "failure":
                continue
            failed_jobs += 1
            runs_with_red.add(run["run_id"])
            name = job["job_name"]
            family, priority = JOB_FAMILIES.get(
                name, ("UNCLASSIFIED_JOB:" + name, "READER")
            )
            is_summary = name == SUMMARY_JOB
            if is_summary:
                summary_failures += 1
            else:
                non_summary_failures += 1
            steps = job["failed_steps"]
            failed_steps += len(steps)
            bucket = by_family[(family, priority)]
            bucket["prs"].add(run["pr"])
            bucket["runs"].add(run["run_id"])
            bucket["jobs"] += 1
            bucket["steps"] += len(steps)
            failures.append(
                {
                    "pr": run["pr"],
                    "sha": run["source_head_sha"],
                    "run_id": run["run_id"],
                    "run_attempt": job["run_attempt"],
                    "job_id": job["job_id"],
                    "job_name": name,
                    "failed_steps": steps,
                    "downstream_summary": is_summary,
                    "causal_root_id": None,
                }
            )
    families = []
    for (family, priority), info in by_family.items():
        families.append(
            {
                "symptom_family": family,
                "priority": priority,
                "failed_jobs": info["jobs"],
                "observed_failed_steps": info["steps"],
                "affected_prs": sorted(info["prs"]),
                "distinct_failed_runs": len(info["runs"]),
                "confirmed_causal_root": None,
                "source_owner_approval": None,
                "disjoint_repair_authorized": False,
            }
        )
    families.sort(key=lambda r: (-r["failed_jobs"], r["symptom_family"]))
    return {
        "schema": "cbd.native_job_projection.v1",
        "scope": "NONATOMIC_NATIVE_FIRST_PAGE_LATEST_JOB_ATTEMPTS",
        "source_digests": sorted(digest(doc) for doc in documents),
        "authority": EXPECTED_AUTHORITY,
        "metrics": {
            "sampled_run_ids": len(runs),
            "sampled_prs": len({run["pr"] for run in runs}),
            "expected_job_records_first_page": total_expected,
            "fetched_job_records_first_page": total_fetched,
            "jobs_collection_complete": total_fetched == total_expected,
            "nonterminal_jobs": pending_jobs,
            "failed_job_manifestations": failed_jobs,
            "failed_step_observations": failed_steps,
            "non_summary_failed_jobs": non_summary_failures,
            "downstream_summary_failed_jobs": summary_failures,
            "runs_with_failed_jobs": len(runs_with_red),
            "observed_run_attempt_groups": len(attempts),
            "root_confirmed_count": None,
            "matched_changed_line_coverage": None,
            "matched_branch_coverage": None,
            "accepted_bd_closures": None,
        },
        "candidate_job_families": families,
        "failed_job_evidence": sorted(
            failures,
            key=lambda r: (r["pr"], r["run_id"], r["run_attempt"], r["job_id"]),
        ),
        "safety_contract": [
            "JOB_AND_FAILED_STEP_ARE_NOT_CAUSAL_ROOTS",
            "SUMMARY_JOB_DOES_NOT_DUPLICATE_UPSTREAM_FAILURE",
            "UNKNOWN_COVERAGE_DOES_NOT_BECOME_ZERO_OR_GREEN",
            "MIXED_RUN_ATTEMPTS_DO_NOT_BECOME_INDEPENDENT_TRIALS",
            "NO_DISPATCH_NO_WAIVER_NO_MERGE",
        ],
    }


def main() -> None:
    """Generate deterministic read-only projection from native job JSON."""
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, nargs="+")
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()
    documents = [
        json.loads(path.read_text(encoding="utf-8")) for path in arguments.source
    ]
    result = project(documents)
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result["metrics"], sort_keys=True))


if __name__ == "__main__":
    main()
