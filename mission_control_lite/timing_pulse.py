"""Wall-time and phase telemetry; read-only and nonadmitting.

Native phase durations and hosted-run queuing are deliberately separate.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import time
from pathlib import Path

SCHEMA = "mcl.timing.v1"


def _instant(value):
    if not isinstance(value, str):
        raise ValueError("missing timestamp")
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc


def _seconds(before, after):
    start = _instant(before)
    end = _instant(after)
    if start.utcoffset() is None or end.utcoffset() is None:
        raise ValueError("naive timestamps are not admissible")
    elapsed = (end - start).total_seconds()
    if elapsed < 0:
        raise ValueError("non-monotone event timestamps")
    return round(elapsed, 3)


def completed_run_metrics(run, job):
    """Summarise REST run/job snapshots after both are terminal."""
    if run.get("status") != "completed" or job.get("status") != "completed":
        raise ValueError("nonterminal run/job")
    if run.get("id") != job.get("run_id"):
        raise ValueError("mixed run/job provenance")
    source_sha = run.get("head_sha")
    if not isinstance(source_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise ValueError("missing or invalid run SHA")
    created, started, ended = (
        run.get("created_at"), run.get("run_started_at"), run.get("updated_at")
    )
    job_started, job_ended = job.get("started_at"), job.get("completed_at")
    wall = _seconds(created, ended)
    queue = _seconds(created, started)
    pre_job = _seconds(started, job_started)
    execution = _seconds(job_started, job_ended)
    after_job = _seconds(job_ended, ended)
    parts = queue + pre_job + execution + after_job
    if abs(parts - wall) > 0.005:
        raise ValueError("run timeline does not reconcile")
    steps = []
    for item in job.get("steps", []):
        if not item.get("started_at") or not item.get("completed_at"):
            continue
        steps.append({
            "name": item.get("name"),
            "seconds": _seconds(item["started_at"], item["completed_at"]),
            "conclusion": item.get("conclusion"),
        })
    return {
        "schema": SCHEMA, "source_sha": run["head_sha"],
        "run_id": str(run["id"]), "job_id": str(job["id"]),
        "wall_seconds": wall, "run_queue_seconds": queue,
        "run_to_job_seconds": pre_job, "job_seconds": execution,
        "finalization_seconds": after_job,
        "non_job_seconds": round(wall - execution, 3),
        "runner_fraction": round(execution / wall, 6) if wall else None,
        "steps": steps, "merge_admission": "HOLD",
    }


def measure(output, phase, command):
    """Run a native subprocess; persist duration even on test failure."""
    if not phase or not command:
        raise ValueError("phase and command required")
    path = Path(output)
    previous = json.loads(path.read_text()) if path.exists() else []
    if not isinstance(previous, list) or any(
        not isinstance(r, dict) or r.get("phase") == phase for r in previous
    ):
        raise ValueError("duplicate phase or invalid metrics")
    clock = time.perf_counter_ns()
    try:
        completed = subprocess.run(command, check=False)
        rc = completed.returncode
    except OSError:
        rc = 127
    elapsed = round((time.perf_counter_ns() - clock) / 1_000_000_000, 6)
    previous.append({"phase": phase, "duration_seconds": elapsed,
                     "exit_code": rc})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(previous, sort_keys=True, indent=2) + "\n")
    return rc


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    m = sub.add_parser("measure")
    m.add_argument("--output", type=Path, required=True)
    m.add_argument("--phase", required=True)
    m.add_argument("command", nargs=argparse.REMAINDER)
    r = sub.add_parser("reconcile")
    r.add_argument("--run-json", type=Path, required=True)
    r.add_argument("--job-json", type=Path, required=True)
    r.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "measure":
        cmd = args.command
        if cmd and cmd[0] == "--":
            cmd = cmd[1:]
        sys.exit(measure(args.output, args.phase, cmd))
    data = completed_run_metrics(
        json.loads(args.run_json.read_text()), json.loads(args.job_json.read_text())
    )
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: data[k] for k in (
        "source_sha", "wall_seconds", "non_job_seconds", "job_seconds"
    )}))


if __name__ == "__main__":
    main()
