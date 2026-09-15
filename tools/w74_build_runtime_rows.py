#!/usr/bin/env python3
"""Build W74 runtime rows from real GitHub matrix jobs and probe receipts."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_receipts(root: Path) -> list[dict]:
    receipts = []
    for path in sorted(root.rglob("PROBE_RECEIPT.json")):
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipt["_path"] = path.as_posix()
        receipts.append(receipt)
    if not receipts:
        raise ValueError("no W74 probe receipts found")
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

    jobs = json.loads(Path(args.jobs_json).read_text(encoding="utf-8"))["jobs"]
    jobs_by_name = {job["name"]: job for job in jobs}
    run_created = parse_time(args.run_created_at)
    rows = []

    for receipt in load_receipts(Path(args.probe_root)):
        sha = str(receipt["source_sha"])
        label = str(receipt["matrix_label"])
        job_name = f"w74-runtime-{label}"
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
        state = "PASS" if conclusion == "success" else "FAIL"
        rows.append(
            {
                "row_id": f"RUN-W74-{sha[:12]}",
                "observation_class": "runtime",
                "source_repo": args.repo,
                "source_sha": sha,
                "evidence_reference": (
                    f"https://api.github.com/repos/{args.repo}/actions/runs/"
                    f"{args.run_id}/jobs"
                ),
                "authority_class": "derived_operational_analysis",
                "execution_state": state,
                "runner_allocated_fraction": 1.0,
                "job_count": 1,
                "steps_executed_total": len(steps),
                "queue_seconds_mean": round(
                    max((started - run_created).total_seconds(), 0.0), 6
                ),
                "execute_seconds_total": round(
                    max((completed - started).total_seconds(), 0.0), 6
                ),
                "evidence_emit_count": 1,
                "probe_receipt": receipt["_path"],
                "runner_id": runner_id,
                "job_id": int(job["id"]),
            }
        )

    shas = [row["source_sha"] for row in rows]
    if len(rows) < 5 or len(set(shas)) != len(rows):
        raise ValueError("W74 requires >=5 unique exact-SHA runtime observations")
    if any(row["execution_state"] != "PASS" for row in rows):
        raise ValueError("W74 runtime matrix contains a failed execution")

    rows.sort(key=lambda row: row["source_sha"])
    Path(args.out).write_text(
        json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"rows": len(rows), "distinct_source_shas": len(set(shas))}))


if __name__ == "__main__":
    main()
