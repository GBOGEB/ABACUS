"""Read-only CODE PURPLE portfolio CI diff, first-red, and coverage triage.

Offline input is native run/job evidence, not a synthetic green check. Live mode
fetches pull requests, exact-head runs and attempt-scoped jobs; it never reruns,
waives, approves, edits source, or authorizes merges. Logs are optional local
GitHub job exports, never assumed from a missing payload.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict
from http.client import HTTPSConnection
from pathlib import Path
from urllib.parse import urlencode

REPO = "GBOGEB/ABACUS"
SCHEMA = "abacus.mip.portfolio-native.v1"
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
TERMINAL = {"success", "failure", "cancelled", "skipped", "timed_out", "neutral", "action_required", "stale", "startup_failure"}
LOW_LIMIT = 0.75
MAX_LOG_BYTES = 200_000
MAX_PAGES = 20


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def pos(value):
    return type(value) is int and value > 0


def sha(value):
    return isinstance(value, str) and HEX40.fullmatch(value) is not None


def first_red(job):
    """Candidate signature and optional native source line; no causal closure."""
    failed_steps = [s for s in job.get("steps", []) if s.get("conclusion") == "failure"]
    step = min(failed_steps, key=lambda s: s.get("number", 10**9)) if failed_steps else None
    excerpt = job.get("log_excerpt") or ""
    require(isinstance(excerpt, str) and len(excerpt) <= MAX_LOG_BYTES, "invalid bounded log excerpt")
    rules = (
        (r"No matching distribution found for\s+([A-Za-z][A-Za-z0-9_.-]*)", "PIP"),
        (r"unclassified workflows?", "GOVERNANCE_INVENTORY"),
        (r"(?:Safety is red|safety check.*exit code 64)", "SAFETY"),
        (r"(?:black new-debt ratchet failed|Per-tool black new-debt)", "BLACK"),
        (r"(?:restricted term in content|A10.*BLOCK)", "A10"),
        (r"(?:HTTP (?:502|503)|502 Bad Gateway).*?(?:Docker|docker|manifest|registry)|Docker.*?HTTP (?:502|503)", "DOCKER_REGISTRY"),
        (r"pull access denied for test-app", "DOCKER_FIXTURE"),
    )
    fingerprint = None
    for pattern, label in rules:
        match = re.search(pattern, excerpt, flags=re.IGNORECASE | re.DOTALL)
        if match:
            fingerprint = (f"{label}:{match.group(1).lower()}" if label == "PIP" else label)
            break
    source = re.search(r"(?<![A-Za-z0-9_])([A-Za-z0-9_./\\-]+\.py):([1-9][0-9]*)(?::[0-9]+)?", excerpt)
    location = {"file": source.group(1).replace("\\", "/"), "line": int(source.group(2))} if source else None
    return {
        "job_id": job["id"], "failed_step": step.get("name") if step else None,
        "failed_step_number": step.get("number") if step else None,
        "root_candidate": fingerprint, "root_confirmed": False,
        "source_location": location,
        "debug_url": f"https://github.com/{REPO}/actions/runs/{job['run_id']}/job/{job['id']}",
        "log_observed": bool(excerpt),
    }


def check_coverage(c, head):
    if c is None:
        return []
    require(isinstance(c, dict) and c.get("source_sha") == head, "unbound coverage head")
    require(isinstance(c.get("files"), list), "coverage files required")
    rows, seen = [], set()
    for v in c["files"]:
        require(isinstance(v, dict), "coverage file object required")
        path = v.get("path")
        require(isinstance(path, str) and path and ".." not in Path(path).parts and path not in seen,
                "invalid or duplicate coverage path")
        seen.add(path)
        stmts, miss = v.get("statements"), v.get("missing")
        branches, missing_branches = v.get("branches", 0), v.get("missing_branches", 0)
        require(all(type(i) is int and i >= 0 for i in (stmts, miss, branches, missing_branches))
                and miss <= stmts and missing_branches <= branches, "invalid coverage numerator/denominator")
        total = stmts + branches
        ratio = (total - miss - missing_branches) / total if total else None
        rows.append({"path": path, "statements": stmts, "covered_statements": stmts - miss,
                     "branches": branches, "covered_branches": branches - missing_branches,
                     "coverage": round(ratio, 6) if ratio is not None else None,
                     "missing_total": miss + missing_branches,
                     "priority": ("ZERO" if ratio == 0 else "LOW" if ratio is not None and ratio < LOW_LIMIT else "OTHER")})
    return rows


def parse_snapshot(payload):
    require(isinstance(payload, dict) and payload.get("schema") == SCHEMA and payload.get("repository") == REPO,
            "unsupported portfolio schema or repository")
    observations = payload.get("observations")
    require(isinstance(observations, list), "observations must be a list")
    seen = set()
    output = []
    for obs in observations:
        require(isinstance(obs, dict) and pos(obs.get("pr")) and sha(obs.get("head_sha")),
                "PR and source identity required")
        require(pos(obs.get("run_id")) and pos(obs.get("attempt")), "native run attempt required")
        key = (obs["run_id"], obs["attempt"])
        require(key not in seen, "duplicate native run attempt")
        seen.add(key)
        require(isinstance(obs.get("workflow"), str) and obs["workflow"].strip(), "workflow name required")
        status, outcome = obs.get("status"), obs.get("conclusion")
        require(status in ("completed", "queued", "in_progress", "pending", "waiting", "requested"),
                "invalid run status")
        require((outcome in TERMINAL if status == "completed" else outcome is None),
                "run terminal status/conclusion mismatch")
        jobs = obs.get("jobs")
        require(isinstance(jobs, list), "observed native job list required")
        job_ids, reds = set(), []
        for job in jobs:
            require(isinstance(job, dict) and pos(job.get("id")) and job.get("run_id") == obs["run_id"]
                    and job.get("attempt") == obs["attempt"] and job.get("head_sha") == obs["head_sha"],
                    "native job run/attempt/head mismatch")
            require(job["id"] not in job_ids, "duplicate job id")
            job_ids.add(job["id"])
            require(job.get("status") in ("completed", "queued", "in_progress", "pending", "waiting"),
                    "invalid job status")
            require((job.get("conclusion") in TERMINAL if job["status"] == "completed"
                     else job.get("conclusion") is None), "job outcome mismatch")
            steps = job.get("steps", [])
            require(isinstance(steps, list) and all(isinstance(s, dict) for s in steps), "invalid job steps")
            if job["conclusion"] == "failure":
                reds.append(first_red(job))
        if outcome == "success":
            require(bool(jobs) and all(j["status"] == "completed" and
                    j["conclusion"] not in ("failure", "timed_out", "action_required")
                    for j in jobs), "workflow green contradicted by native jobs")
        coverage = check_coverage(obs.get("coverage"), obs["head_sha"])
        output.append({"pr": obs["pr"], "head_sha": obs["head_sha"], "run_id": obs["run_id"],
                       "attempt": obs["attempt"], "workflow": obs["workflow"], "status": status,
                       "conclusion": outcome, "jobs_observed": len(jobs), "first_red": reds,
                       "coverage": coverage})
    return output


def combine_history(previous, current):
    """Append-only observation lineage; refreshed nonterminal attempts may complete."""
    require(isinstance(previous, dict) and isinstance(current, dict)
            and all(v.get("schema") == SCHEMA and v.get("repository") == REPO
                    for v in (previous, current)), "incompatible history snapshots")
    rows = {}
    for snapshot in (previous, current):
        for row in snapshot.get("observations", []):
            key = (row.get("run_id"), row.get("attempt"))
            if key in rows:
                old = rows[key]
                require(old.get("pr") == row.get("pr")
                        and old.get("head_sha") == row.get("head_sha")
                        and old.get("workflow") == row.get("workflow"),
                        "run attempt was rebound to a different source")
                if old.get("status") == "completed":
                    require(row.get("status") == "completed"
                            and old.get("conclusion") == row.get("conclusion"),
                            "terminal historical attempt cannot change")
                    continue
            rows[key] = row
    return {"schema": SCHEMA, "repository": REPO, "observations": list(rows.values()),
            "pr_heads": current.get("pr_heads", previous.get("pr_heads")),
            "history_deduplicated_attempts": len(rows)}


def analyze(payload):
    records = parse_snapshot(payload)
    current_heads = payload.get("pr_heads")
    stale = []
    if current_heads is not None:
        require(isinstance(current_heads, list), "native current PR heads must be a list")
        seen_prs = set()
        for item in current_heads:
            require(isinstance(item, dict) and pos(item.get("pr")) and sha(item.get("head_sha"))
                    and item["pr"] not in seen_prs, "invalid or repeated current PR head")
            seen_prs.add(item["pr"])
            if not any(x["pr"] == item["pr"] and x["head_sha"] == item["head_sha"]
                       for x in records):
                stale.append({"pr": item["pr"], "current_head": item["head_sha"],
                              "status": "NO_NATIVE_RUN_FOR_CURRENT_HEAD", "admission": "HOLD"})
    roots = Counter(f["root_candidate"] for row in records for f in row["first_red"] if f["root_candidate"])
    groups = defaultdict(list)
    for row in records:
        groups[(row["pr"], row["workflow"])].append(row)
    transitions, retry_candidates = [], []
    for (pr, workflow), waves in sorted(groups.items()):
        ordered = sorted(waves, key=lambda w: (w["run_id"], w["attempt"]))
        for before, after in zip(ordered, ordered[1:]):
            was = sorted({f["root_candidate"] for f in before["first_red"] if f["root_candidate"]})
            now = sorted({f["root_candidate"] for f in after["first_red"] if f["root_candidate"]})
            if after["status"] != "completed":
                change = "CENSORED"
            elif before["head_sha"] != after["head_sha"]:
                change = "NEW_HEAD_ROOT_TRANSITION" if was != now else "NEW_HEAD_ROOT_PERSISTS"
            elif was == now and was:
                change = "UNCHANGED_HEAD_SAME_FIRST_RED"
            elif was != now:
                change = "SAME_HEAD_RETRY_RESULT_CHANGED"
            else:
                change = "NO_ATTRIBUTABLE_ROOT_COMPARISON"
            transitions.append({"pr": pr, "workflow": workflow, "before": [before["run_id"], before["attempt"]],
                                "after": [after["run_id"], after["attempt"]], "classification": change,
                                "before_roots": was, "after_roots": now, "source_changed": before["head_sha"] != after["head_sha"]})
        latest = ordered[-1]
        observed_attempts = [w for w in ordered if w["run_id"] == latest["run_id"]]
        roots_here = {f["root_candidate"] for f in latest["first_red"]}
        if (latest["status"] == "completed" and latest["conclusion"] == "failure"
                and latest["attempt"] == 1 and len(observed_attempts) == 1
                and roots_here == {"DOCKER_REGISTRY"}):
            retry_candidates.append({"pr": pr, "workflow": workflow,
                                     "run_id": latest["run_id"], "head_sha": latest["head_sha"],
                                     "reason": "transient_registry_candidate_one_retry_max",
                                     "execute": False})
    coverage = [{"pr": x["pr"], "head_sha": x["head_sha"], "run_id": x["run_id"],
                 "attempt": x["attempt"], **item} for x in records for item in x["coverage"]
                if item["priority"] in ("ZERO", "LOW")]
    coverage.sort(key=lambda x: (0 if x["priority"] == "ZERO" else 1, -x["missing_total"], x["path"]))
    n_success = sum(x["conclusion"] == "success" for x in records)
    n_fail = sum(x["conclusion"] == "failure" for x in records)
    n_pending = sum(x["status"] != "completed" for x in records)
    n_covered = sum(bool(x["first_red"]) for x in records)
    n_attributed = sum(any(f["root_candidate"] for f in x["first_red"]) for x in records)
    return {
        "schema": "abacus.mip.portfolio-diagnostics.v1", "repository": REPO,
        "metrics": {"native_run_attempts": len(records), "success": n_success, "failure": n_fail,
                    "nonterminal": n_pending, "other_terminal": len(records)-n_success-n_fail-n_pending,
                    "first_red_jobs": sum(len(x["first_red"]) for x in records),
                    "failed_runs_with_jobs_observed": n_covered,
                    "failed_runs_with_candidate_fingerprint": n_attributed,
                    "distinct_root_candidates_not_confirmed": len(roots),
                    "coverage_zero_low_file_observations": len(coverage),
                    "current_head_census_observed": len(current_heads) if current_heads is not None else None,
                    "current_heads_without_matching_run": len(stale) if current_heads is not None else None},
        "root_candidates_by_manifestation": dict(sorted(roots.items())),
        "transitions": transitions, "coverage_priority": coverage, "stale_current_heads": stale,
        "guarded_retry_candidates": retry_candidates, "executed_reruns": 0,
        "accepted_root_closures": None, "main_coverage_delta": None,
        "merge_authorized": False, "admission": "HOLD",
    }


def github_get(path, *, token):
    require(isinstance(path, str) and path.startswith(f"/repos/{REPO}/")
            and ".." not in path and "#" not in path and "\n" not in path,
            "unsupported GitHub path")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "abacus-mip-portfolio-readonly",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = "Bearer " + token
    connection = HTTPSConnection("api.github.com", timeout=25)
    try:
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        require(response.status == 200, f"GitHub native HTTP {response.status}")
        return json.load(response)
    finally:
        connection.close()


def collect_live(*, token, max_prs=100, max_runs_per_pr=2, getter=github_get):
    """Bounded complete pages; no workflow re-dispatch or token persistence."""
    require(pos(max_prs) and max_prs <= 500 and pos(max_runs_per_pr) and max_runs_per_pr <= 10,
            "bounded max_prs/max_runs_per_pr required")
    items = []
    for page in range(1, 6):
        path = f"/repos/{REPO}/pulls?" + urlencode({"state": "open", "per_page": 100, "page": page})
        batch = getter(path, token=token)
        require(isinstance(batch, list), "GitHub PR page invalid")
        items.extend(batch)
        if len(items) >= max_prs or len(batch) < 100:
            break
    observations = []
    pr_heads = []
    for pr in items[:max_prs]:
        number, head = pr.get("number"), pr.get("head", {}).get("sha")
        require(pos(number) and sha(head), "invalid native PR identity")
        pr_heads.append({"pr": number, "head_sha": head})
        path = f"/repos/{REPO}/actions/runs?" + urlencode({"head_sha": head, "event": "pull_request", "per_page": 100, "page": 1})
        run_result = getter(path, token=token)
        require(isinstance(run_result, dict) and isinstance(run_result.get("workflow_runs"), list),
                "native runs response invalid")
        native = run_result["workflow_runs"]
        require(len(native) <= 100, "native runs page invalid")
        for run in native[:max_runs_per_pr]:
            run_id, attempt = run.get("id"), run.get("run_attempt")
            require(pos(run_id) and pos(attempt) and run.get("head_sha") == head,
                    "foreign or missing workflow head")
            jobs = []
            total = None
            for page in range(1, MAX_PAGES + 1):
                endpoint = f"/repos/{REPO}/actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100&page={page}"
                response = getter(endpoint, token=token)
                require(isinstance(response, dict) and type(response.get("total_count")) is int
                        and isinstance(response.get("jobs"), list), "native jobs response invalid")
                if total is None:
                    total = response["total_count"]
                    require(0 <= total <= MAX_PAGES * 100, "native jobs over capacity")
                require(response["total_count"] == total, "native jobs changed during pagination")
                jobs.extend(response["jobs"])
                require(len(jobs) <= total, "native jobs larger than census")
                if len(jobs) == total:
                    break
                require(response["jobs"], "partial native jobs page")
            require(len(jobs) == total, "incomplete job census")
            normalized = []
            for j in jobs:
                require(j.get("run_id") == run_id and j.get("head_sha") == head,
                        "cross-head native job")
                normalized.append({"id": j["id"], "run_id": run_id, "attempt": attempt,
                                   "head_sha": head, "name": j.get("name"),
                                   "status": j.get("status"), "conclusion": j.get("conclusion"),
                                   "steps": j.get("steps") or []})
            observations.append({"pr": number, "head_sha": head, "run_id": run_id,
                                 "attempt": attempt, "workflow": run.get("name") or "unknown-workflow",
                                 "status": run.get("status"), "conclusion": run.get("conclusion"),
                                 "jobs": normalized, "coverage": None})
    return {"schema": SCHEMA, "repository": REPO, "observations": observations, "pr_heads": pr_heads,
            "source": "native-gh-rest-readonly", "runs_page_cap_per_pr": max_runs_per_pr,
            "pr_cap": max_prs, "all_prs_proven_enumerated": len(items) < max_prs}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--input", type=Path)
    mode.add_argument("--live", action="store_true")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--snapshot-out", type=Path)
    p.add_argument("--previous", type=Path)
    p.add_argument("--max-prs", type=int, default=100)
    p.add_argument("--max-runs-per-pr", type=int, default=2)
    args = p.parse_args(argv)
    if args.live:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        require(bool(token), "GitHub read token required for live mode")
        payload = collect_live(token=token, max_prs=args.max_prs, max_runs_per_pr=args.max_runs_per_pr)
    else:
        require(args.input.is_file() and not args.input.is_symlink(), "native snapshot file required")
        payload = json.loads(args.input.read_text(encoding="utf-8"))
    if args.previous is not None:
        require(args.previous.is_file() and not args.previous.is_symlink(),
                "previous native snapshot file required")
        payload = combine_history(json.loads(args.previous.read_text(encoding="utf-8")), payload)
    result = analyze(payload)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    if args.snapshot_out is not None:
        require(args.snapshot_out != args.out, "snapshot and report paths differ")
        args.snapshot_out.parent.mkdir(parents=True, exist_ok=True)
        args.snapshot_out.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["metrics"], sort_keys=True))
    print("admission=HOLD; executed_reruns=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
