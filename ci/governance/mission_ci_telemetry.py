"""Read-only exact-SHA GitHub Actions census, with bounded federation fan-out.

The report is telemetry, never a required-check waiver or merge authority.
"""

import argparse
import hashlib
import json
import os
import re
import statistics
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path

SCHEMA = "mission.control.ci-telemetry.v1"
SHA = re.compile(r"^[0-9a-f]{40}$")
REPO = re.compile(r"^GBOGEB/[A-Za-z0-9_.-]+$")
FAMILIES = {
    "MIP": ("mip", "test admission"),
    "DMAIC": ("dmaic",),
    "PCA_BT": ("pca", "bradley-terry", "bt-rank"),
    "REX": ("rex",),
    "LDAB_LLDB": ("ldab", "lldb", "debug"),
    "CENSUS": ("census", "inventory"),
    "THREE_P": ("3p*", "3pr", "3pc"),
    "MISSION_CONTROL": ("mission control", "missioncontrol"),
}
TERMINAL = {"completed"}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def parse_utc(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        return None
    return parsed


def elapsed(start, end):
    a, b = parse_utc(start), parse_utc(end)
    return round((b - a).total_seconds(), 3) if a and b and b >= a else None


def family(name):
    lower = name.lower()
    return next(
        (k for k, words in FAMILIES.items() if any(w in lower for w in words)), "OTHER"
    )


def percentile(values, share):
    if len(values) < 5:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * share
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return round(ordered[low] + (ordered[high] - ordered[low]) * (position - low), 3)


def job_metrics(jobs):
    statuses = Counter()
    queue = []
    active = []
    intervals = []
    unique = set()
    for job in jobs:
        require(isinstance(job, dict), "invalid job")
        ident = job.get("id")
        require(isinstance(ident, int) and ident not in unique, "duplicate job")
        unique.add(ident)
        status = job.get("status", "unknown")
        statuses[status] += 1
        if status != "completed" or job.get("conclusion") == "skipped":
            continue
        q = elapsed(job.get("created_at"), job.get("started_at"))
        d = elapsed(job.get("started_at"), job.get("completed_at"))
        if q is not None:
            queue.append(q)
        if d is not None:
            active.append(d)
        start = parse_utc(job.get("started_at"))
        stop = parse_utc(job.get("completed_at"))
        if start and stop and stop >= start:
            intervals.append((start, stop))
    events = []
    for start, stop in intervals:
        events.extend(((start, 1), (stop, -1)))
    # Finish before start at the same instant: no fake overlap.
    events.sort(key=lambda pair: (pair[0], pair[1]))
    concurrency = 0
    peak = 0
    for _, change in events:
        concurrency += change
        peak = max(peak, concurrency)
    return {
        "sampled_jobs": len(jobs),
        "status_counts": dict(sorted(statuses.items())),
        "skipped_jobs_excluded": sum(
            j.get("status") == "completed" and j.get("conclusion") == "skipped"
            for j in jobs
        ),
        "terminal_jobs_with_queue": len(queue),
        "terminal_jobs_with_runtime": len(active),
        "queue_total_s_sample": round(sum(queue), 3) if queue else None,
        "execution_total_s_sample": round(sum(active), 3) if active else None,
        "queue_p50_s": round(statistics.median(queue), 3) if len(queue) >= 5 else None,
        "queue_p95_s": percentile(queue, 0.95),
        "execution_p50_s": (
            round(statistics.median(active), 3) if len(active) >= 5 else None
        ),
        "execution_p95_s": percentile(active, 0.95),
        "peak_concurrent_jobs_sample": peak if intervals else None,
        "timing_class": "JOB_API_OBSERVED_SAMPLE",
        "unmeasured": [
            "dependency_download",
            "installation",
            "test_body",
            "upload",
            "runner_boot",
        ],
    }


def summarize(repo, sha, response, job_records, max_jobs_runs):
    require(isinstance(repo, str) and REPO.fullmatch(repo), "invalid repo")
    require(isinstance(sha, str) and SHA.fullmatch(sha), "invalid SHA")
    require(isinstance(response, dict), "invalid run response")
    records = response.get("workflow_runs")
    total = response.get("total_count")
    require(isinstance(records, list) and type(total) is int, "bad API run result")
    require(total >= len(records), "API count discrepancy")
    identifiers = set()
    manifest = []
    states = Counter()
    by_family = {}
    terminal = 0
    for run in records:
        require(run.get("head_sha") == sha, "run source SHA mismatch")
        number = run.get("id")
        require(type(number) is int and number not in identifiers, "duplicate run ID")
        identifiers.add(number)
        manifest.append(
            {
                "run_id": number,
                "workflow_id": run.get("workflow_id"),
                "name": run.get("name"),
                "status": run.get("status"),
                "conclusion": run.get("conclusion"),
            }
        )
        state = run.get("status", "unknown")
        conclusion = run.get("conclusion") or "none"
        states[state + "/" + conclusion] += 1
        terminal += int(state in TERMINAL)
        key = family(run.get("name") or "")
        if key not in by_family:
            by_family[key] = Counter()
        by_family[key][state + "/" + conclusion] += 1
    require(set(job_records).issubset(identifiers), "jobs not from listed runs")
    all_jobs = []
    for run_id in sorted(job_records):
        for job in job_records[run_id]:
            require(job.get("run_id") == run_id, "cross-run job mismatch")
            all_jobs.append(job)
    metrics = job_metrics(all_jobs)
    return {
        "schema": SCHEMA,
        "repo": repo,
        "sha": sha,
        "run_count": len(records),
        "api_total_run_count": total,
        "run_census_complete": total == len(records),
        "terminal_run_count": terminal,
        "run_states": dict(sorted(states.items())),
        "run_manifest": manifest,
        "family_run_states": {
            k: dict(sorted(v.items())) for k, v in sorted(by_family.items())
        },
        "job_sampling": {
            "selected_run_count": len(job_records),
            "sampling_limit": max_jobs_runs,
            "sample_complete": len(job_records) == len(records),
        },
        "job_metrics": metrics,
        "coverage_delta_pp": None,
        "distinct_root_closures": None,
        "rex_accepted_returns": None,
        "merge_admitted": False,
        "provenance": "LIVE_GITHUB_API_READ_ONLY",
        "limits": [
            "Run first page only; incomplete when API total exceeds page",
            "Job timings sampled by bounded number of runs",
            "Queue time uses job timestamps, not workflow run_started_at",
            "No per-step install or download timing without step telemetry",
            "Grouping by workflow name is a routing hint, not family proof",
            "No MIP/REX root closure or coverage credit from CI status",
        ],
    }


def api_get(url, token):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response)


def snapshot(repo, sha, token, max_jobs_runs=15, get=api_get):
    require(REPO.fullmatch(repo) and SHA.fullmatch(sha), "invalid target")
    require(
        type(max_jobs_runs) is int and 0 <= max_jobs_runs <= 40,
        "invalid sampling limit",
    )
    base = "https://api.github.com/repos/" + repo + "/actions"
    runs = get(base + "/runs?head_sha=" + sha + "&per_page=100", token)
    checked = runs.get("workflow_runs", [])
    require(isinstance(checked, list), "malformed GitHub API response")
    jobs = {}
    # Prefer completed runs: terminal observations are interpretable.
    selected = [r for r in checked if r.get("status") == "completed"][:max_jobs_runs]
    for run in selected:
        result = get(base + "/runs/" + str(run["id"]) + "/jobs?per_page=100", token)
        values = result.get("jobs", [])
        require(isinstance(values, list), "malformed job response")
        jobs[run["id"]] = values
    report = summarize(repo, sha, runs, jobs, max_jobs_runs)
    report["job_sampling"]["job_page_limit"] = 100
    report["job_sampling"]["possible_truncation"] = any(
        len(v) == 100 for v in jobs.values()
    )
    return report


def make_markdown(report):
    rows = [
        "# Mission Control CI telemetry",
        "",
        "Read-only exact-SHA sample; not a merge or recovery authorization.",
        "",
        "| Measurement | Observed |",
        "|---|---:|",
        "| Repository | `" + report["repo"] + "` |",
        "| Source SHA | `" + report["sha"] + "` |",
        "| Workflow runs returned | " + str(report["run_count"]) + " |",
        "| Run census complete | " + str(report["run_census_complete"]) + " |",
        "| Terminal runs | " + str(report["terminal_run_count"]) + " |",
        "| Jobs sampled | " + str(report["job_metrics"]["sampled_jobs"]) + " |",
    ]
    for field in (
        "queue_p50_s",
        "queue_p95_s",
        "execution_p50_s",
        "execution_p95_s",
        "peak_concurrent_jobs_sample",
    ):
        value = report["job_metrics"][field]
        rows.append(
            "| "
            + field
            + " | "
            + (str(value) if value is not None else "UNKNOWN")
            + " |"
        )
    rows.extend(["", "## Run states", ""])
    for key, value in sorted(report["run_states"].items()):
        rows.append("- " + key + ": " + str(value))
    rows.extend(["", "Coverage/root closure/REX: UNKNOWN; no synthetic gains.", ""])
    return "\n".join(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--target", action="append", required=True, help="GBOGEB/repo@40hexsha"
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-jobs-runs", type=int, default=15)
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    require(bool(token), "read-only GitHub token missing")
    records = []
    for target in args.target:
        require(target.count("@") == 1, "target missing @SHA")
        repo, sha = target.split("@", 1)
        # An inaccessible federated target is UNKNOWN, not a zero-valued census.
        try:
            records.append(snapshot(repo, sha, token, args.max_jobs_runs))
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            records.append(
                {
                    "repo": repo,
                    "sha": sha,
                    "status": "UNKNOWN",
                    "reason": "API_UNAVAILABLE_OR_UNAUTHORIZED",
                    "http_status": getattr(exc, "code", None),
                }
            )
    path = Path(args.output_dir)
    path.mkdir(parents=True, exist_ok=True)
    package = {
        "schema": SCHEMA,
        "observations": records,
        "federation_verified_breadth": sum("run_count" in r for r in records),
        "admission_authority": False,
    }
    source = json.dumps(package, indent=2, sort_keys=True) + "\n"
    (path / "mission_ci_snapshot.json").write_text(source, encoding="utf-8")
    (path / "mission_ci_snapshot.sha256").write_text(
        hashlib.sha256(source.encode()).hexdigest() + "\n", encoding="utf-8"
    )
    complete = [r for r in records if "job_metrics" in r]
    if complete:
        (path / "mission_ci_summary.md").write_text(
            "\n---\n".join(make_markdown(r) for r in complete), encoding="utf-8"
        )
    print(
        json.dumps(
            {
                "observed_repos": len(complete),
                "targets": len(records),
                "admission_authority": False,
            }
        )
    )


if __name__ == "__main__":
    main()
