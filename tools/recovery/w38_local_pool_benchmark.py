"""W38 bounded local pool MIP: repeated two-family, 1/2/4 worker census.

This native local experiment never provisions runners, remotely dispatches,
merges, grants review or predicts hosted fleet capacity. The I/O proxy uses
sleep to make waiting concurrency observable; the CPU proxy uses pure Python
work and may not scale under the interpreter GIL. Both are test workloads,
not representative production tasks. 3 repeats are descriptive, not Six Sigma.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.execution_backbone import ExecutionBackbone

SCHEMA = "abacus.w38.local_pool_mip.v1"
SIZES = (1, 2, 4)
FAMILIES = ("IO_WAIT_PROXY", "PYTHON_CPU_PROXY")
ADMISSION = "HOLD"


def need(ok, msg):
    if not ok:
        raise ValueError(msg)


def b(raw):
    return (
        json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    ).encode("utf-8")


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def pct(values, p):
    if not values:
        return None
    x = sorted(values)
    return x[math.ceil(p * len(x)) - 1]


def _job(family, ticks):
    if family == "IO_WAIT_PROXY":
        time.sleep(ticks / 1000)
        return ticks
    if family == "PYTHON_CPU_PROXY":
        x = 5
        for i in range(ticks * 200):
            x = (x * 33 + i) % 999983
        return x
    raise ValueError("UNKNOWN_FAMILY")


def one(family, workers, *, tasks=48, delay_ms=16):
    """Run a fresh fixed-denominator trial with native local task objects."""
    need(family in FAMILIES and workers in SIZES, "UNBOUNDED_FAMILY_OR_WORKERS")
    need(
        type(tasks) is int
        and 8 <= tasks <= 100
        and type(delay_ms) is int
        and 1 <= delay_ms <= 100,
        "UNBOUNDED_TEST_PAYLOAD",
    )
    back = ExecutionBackbone(max_workers=workers, max_memory_mb=256)
    for i in range(tasks):
        back.schedule_task(
            family + "-" + str(i), _job, priority=i % 6, args=(family, delay_ms)
        )
    tic = time.perf_counter()
    back.start()
    back.stop(wait=True, timeout=30.0)
    secs = time.perf_counter() - tic
    met = back.get_metrics()
    need(
        met["tasks_submitted"] == tasks
        and met["tasks_executed"] == tasks
        and met["tasks_failed"] == 0
        and met["outstanding_work"] == 0
        and met["queue_wait_sample_n"] == tasks
        and met["service_sample_n"] == tasks
        and met["peak_running"] <= workers
        and met["remote_runner_capacity_slots"] is None
        and met["remote_dispatch_enabled"] is False,
        "POOL_TRIAL_INCOMPLETE_OR_UNAUTHENTIC",
    )
    return {
        "family": family,
        "configured_local_workers": workers,
        "eligible_tasks": tasks,
        "completed_tasks": met["tasks_executed"],
        "failures": met["tasks_failed"],
        "elapsed_s": round(secs, 6),
        "throughput_jobs_per_s": round(tasks / max(secs, 1e-9), 4),
        "throughput_per_configured_worker_s": round(
            tasks / max(secs * workers, 1e-9), 4
        ),
        "queue_wait_p95_s": met["queue_wait_p95_seconds"],
        "service_p95_s": met["service_p95_seconds"],
        "queue_wait_sample_n": met["queue_wait_sample_n"],
        "service_sample_n": met["service_sample_n"],
        "peak_running": met["peak_running"],
        "remote_runner_capacity_slots": None,
    }


def summarize(raw):
    need(type(raw) is dict and raw.get("schema") == SCHEMA, "WRONG_MIP_SCHEMA")
    trials = raw.get("trials")
    repeat = raw.get("repeats")
    need(
        type(repeat) is int and repeat >= 3 and repeat <= 5,
        "INSUFFICIENT_REPEATED_PULSES",
    )
    tasks = raw.get("tasks_per_trial")
    need(type(tasks) is int and tasks > 0 and tasks <= 100, "WRONG_TASK_DENOMINATOR")
    need(
        type(trials) is list and len(trials) == repeat * len(FAMILIES) * len(SIZES),
        "INCOMPLETE_MIP_GRID",
    )
    group = {}
    for r in trials:
        fam, workers = r.get("family"), r.get("configured_local_workers")
        need(
            fam in FAMILIES
            and workers in SIZES
            and r.get("eligible_tasks") == tasks
            and r.get("completed_tasks") == tasks
            and r.get("failures") == 0
            and r.get("queue_wait_sample_n") == tasks
            and r.get("service_sample_n") == tasks
            and type(r.get("elapsed_s")) in (int, float)
            and r["elapsed_s"] > 0
            and r.get("remote_runner_capacity_slots") is None,
            "MISMATCHED_MIP_POPULATION_OR_FALSE_CAPACITY",
        )
        group.setdefault((fam, workers), []).append(r)
    need(
        all(
            len(group.get((family, size), [])) == repeat
            for family in FAMILIES
            for size in SIZES
        ),
        "UNBALANCED_COHORT",
    )
    out = []
    for family in FAMILIES:
        baseline = statistics.median(r["elapsed_s"] for r in group[family, 1])
        for workers in SIZES:
            cells = group[family, workers]
            median = statistics.median(r["elapsed_s"] for r in cells)
            workerspeed = baseline / median
            efficiency = workerspeed / workers
            queue_p95_med = statistics.median(r["queue_wait_p95_s"] for r in cells)
            out.append(
                {
                    "family": family,
                    "configured_local_workers": workers,
                    "completed_over_eligible": {
                        "numerator": tasks * repeat,
                        "denominator": tasks * repeat,
                    },
                    "repeat_n": repeat,
                    "median_wall_s": round(median, 5),
                    "p95_wall_s": round(pct([r["elapsed_s"] for r in cells], 0.95), 5),
                    "median_queue_wait_p95_s": round(queue_p95_med, 5),
                    "median_local_service_p95_s": round(
                        statistics.median(r["service_p95_s"] for r in cells), 5
                    ),
                    "speedup_vs_1_worker": round(workerspeed, 4),
                    "efficiency_vs_1_worker": round(efficiency, 4),
                    "marginal_wall_improvement_pct": round(
                        100 * (1 - median / baseline), 4
                    ),
                    "real_hosted_runner_capacity": None,
                }
            )
    return {
        "schema": "abacus.w38.local_pool_metrics.v1",
        "grid": out,
        "population": {
            "independent_families": 2,
            "configured_pool_sizes": list(SIZES),
            "repeats_per_cell": repeat,
            "tasks_per_trial": tasks,
            "full_trial_denominator": len(trials),
            "task_execution_denominator": tasks * len(trials),
        },
        "inference": "CONTROLLED_LOCAL_PROXY_ONLY_NOT_GITHUB_RUNNER_OR_PRODUCTION_THROUGHPUT",
        "repeats_not_six_sigma": True,
        "capacity_escalation_authorized": False,
        "merge_admission": "HOLD",
        "remote_dispatch_enabled": False,
        "formal_root_closures": None,
    }


def execute(*, repeats=3, tasks=48, delay_ms=16):
    need(type(repeats) is int and 3 <= repeats <= 5, "INSUFFICIENT_REPEATS")
    trials = []
    # Interleave family/pool/repeat rather than exhausting one pool first.
    # Still descriptive; no randomized trial or production causal claim.
    for repeat in range(repeats):
        for family in FAMILIES:
            for workers in SIZES:
                rec = one(family, workers, tasks=tasks, delay_ms=delay_ms)
                rec["repeat_index"] = repeat + 1
                trials.append(rec)
    raw = {
        "schema": SCHEMA,
        "repeats": repeats,
        "tasks_per_trial": tasks,
        "delay_ms": delay_ms,
        "trials": trials,
    }
    report = summarize(raw)
    report["raw_trial_sha256"] = sha256(b(raw))
    return raw, report


def emit(out, raw, report, *, head, run_id, attempt):
    need(
        type(head) is str
        and len(head) == 40
        and all(ch in "0123456789abcdef" for ch in head),
        "SOURCE_SHA_REQUIRED",
    )
    need(
        type(run_id) is int and run_id > 0 and type(attempt) is int and attempt > 0,
        "NATIVE_RUN_ATTEMPT_REQUIRED",
    )
    out.mkdir(parents=True, exist_ok=True)
    files = {"W38_TRIALS.json": b(raw), "W38_MIP_METRICS.json": b(report)}
    for path, content in files.items():
        (out / path).write_bytes(content)
    receipt = {
        "schema": "abacus.w38.local_pool.receipt.v1",
        "head_sha": head,
        "run_id": run_id,
        "attempt": attempt,
        "origin": "LOCAL_NATIVE_PYTHON_POOL_BENCHMARK",
        "admission": "HOLD",
        "remote_dispatch_enabled": False,
        "remote_capacity": None,
        "sha256": {name: sha256(value) for name, value in files.items()},
    }
    (out / "W38_SHA256.json").write_bytes(b(receipt))
    return receipt


def verify(out, head):
    doc = json.loads((out / "W38_SHA256.json").read_bytes())
    need(
        doc.get("head_sha") == head
        and doc.get("admission") == "HOLD"
        and doc.get("remote_dispatch_enabled") is False
        and doc.get("remote_capacity") is None,
        "FALSIFIED_POOL_PROOF",
    )
    need(
        set(doc.get("sha256", {})) == {"W38_TRIALS.json", "W38_MIP_METRICS.json"},
        "MISSING_POOL_RECEIPTS",
    )
    for path, d in doc["sha256"].items():
        need(
            (out / path).is_file() and sha256((out / path).read_bytes()) == d,
            "POOL_RECEIPT_SHA_DRIFT",
        )
    raw = json.loads((out / "W38_TRIALS.json").read_bytes())
    derived = summarize(raw)
    received = json.loads((out / "W38_MIP_METRICS.json").read_bytes())
    need(
        received.get("raw_trial_sha256") == sha256(b(raw))
        and all(received.get(key) == value for key, value in derived.items()),
        "POOL_METRIC_REPLAY_DRIFT",
    )
    return doc


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--head", required=True)
    p.add_argument("--run-id", type=int, required=True)
    p.add_argument("--attempt", type=int, required=True)
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--tasks", type=int, default=48)
    p.add_argument("--delay-ms", type=int, default=16)
    p.add_argument("--verify-only", action="store_true")
    args = p.parse_args()
    if not args.verify_only:
        trials, report = execute(
            repeats=args.repeats, tasks=args.tasks, delay_ms=args.delay_ms
        )
        emit(
            args.out,
            trials,
            report,
            head=args.head,
            run_id=args.run_id,
            attempt=args.attempt,
        )
    print(json.dumps(verify(args.out, args.head), sort_keys=True))


if __name__ == "__main__":
    main()
