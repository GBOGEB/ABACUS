#!/usr/bin/env python3
"""Build W75 repeated runtime rows with explicit timing decomposition."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

JOB_RE = re.compile(r"^w75-r(?P<repeat>[1-3])-(?P<label>h[1-5])$")
SHA40 = re.compile(r"^[0-9a-f]{40}$")


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_receipts(root: Path) -> list[dict]:
    receipts = []
    for path in sorted(root.rglob("PROBE_RECEIPT.json")):
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipt["_path"] = path.as_posix()
        receipts.append(receipt)
    if not receipts:
        raise ValueError("no W75 probe receipts found")
    return receipts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs-json", required=True)
    parser.add_argument("--probe-root", required=True)
    parser.add_argument("--run-created-at", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    payload = json.loads(Path(args.jobs_json).read_text(encoding="utf-8"))
    jobs = payload["jobs"]
    jobs_by_name = {str(job["name"]): job for job in jobs}
    run_created = parse_time(args.run_created_at)
    rows = []

    for receipt in load_receipts(Path(args.probe_root)):
        sha = str(receipt["source_sha"])
        label = str(receipt["matrix_label"])
        repeat = int(receipt["repeat"])
        if not SHA40.fullmatch(sha):
            raise ValueError(f"invalid source SHA: {sha}")
        job_name = f"w75-r{repeat}-{label}"
        if not JOB_RE.fullmatch(job_name):
            raise ValueError(f"invalid W75 job identity: {job_name}")
        job = jobs_by_name.get(job_name)
        if job is None:
            raise ValueError(f"missing job metadata for {job_name}")

        started = parse_time(job["started_at"])
        completed = parse_time(job["completed_at"])
        runner_id = int(job.get("runner_id") or 0)
        steps = [
            step
            for step in (job.get("steps") or [])
            if step.get("conclusion") not in {None, "skipped"}
        ]
        if runner_id <= 0 or not steps:
            raise ValueError(f"{job_name}: NOT_EXECUTED runner/step gate")
        conclusion = str(job.get("conclusion") or "").lower()
        if conclusion != "success":
            raise ValueError(f"{job_name}: execution did not succeed")

        queue_seconds = max((started - run_created).total_seconds(), 0.0)
        wall_seconds = max((completed - started).total_seconds(), 0.0)
        intrinsic = float(receipt["probe_execute_seconds"])
        if intrinsic < 0:
            raise ValueError(f"{job_name}: negative intrinsic probe time")
        overhead = max(wall_seconds - intrinsic, 0.0)
        rows.append(
            {
                "row_id": f"RUN-W75-R{repeat}-{sha[:12]}",
                "observation_class": "runtime",
                "source_repo": args.repo,
                "source_sha": sha,
                "repeat": repeat,
                "matrix_label": label,
                "execution_state": "PASS",
                "runner_allocated_fraction": 1.0,
                "job_count": 1,
                "steps_executed_total": len(steps),
                "queue_seconds_mean": round(queue_seconds, 6),
                "execute_seconds_total": round(wall_seconds, 6),
                "probe_execute_seconds": round(intrinsic, 6),
                "orchestration_overhead_seconds": round(overhead, 6),
                "evidence_emit_count": 1,
                "runner_id": runner_id,
                "job_id": int(job["id"]),
                "probe_receipt": receipt["_path"],
                "evidence_reference": (
                    f"https://api.github.com/repos/{args.repo}/actions/runs/"
                    f"{args.run_id}/jobs"
                ),
                "authority_class": "derived_operational_analysis",
            }
        )

    if len(rows) != 15:
        raise ValueError(f"W75 requires exactly 15 rows, observed {len(rows)}")
    keys = {(row["source_sha"], row["repeat"]) for row in rows}
    if len(keys) != 15:
        raise ValueError("W75 requires unique SHA x repeat observations")
    sha_counts = Counter(row["source_sha"] for row in rows)
    if len(sha_counts) != 5 or set(sha_counts.values()) != {3}:
        raise ValueError("W75 requires five exact SHAs with three repeats each")
    repeat_counts = Counter(row["repeat"] for row in rows)
    if repeat_counts != Counter({1: 5, 2: 5, 3: 5}):
        raise ValueError("W75 repeat balance is not 5/5/5")

    rows.sort(key=lambda row: (row["repeat"], row["source_sha"]))
    Path(args.out).write_text(
        json.dumps(rows, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "rows": len(rows),
                "distinct_source_shas": len(sha_counts),
                "repeats": dict(sorted(repeat_counts.items())),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
