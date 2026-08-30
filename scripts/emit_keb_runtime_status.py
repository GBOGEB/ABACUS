#!/usr/bin/env python3
"""Emit a small KEB runtime evidence report for DOW/KEB governance scoring."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "reports" / "keb_runtime_status.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.keb import KEB


def _feedback_task(events: List[Dict[str, Any]], direction: str, payload: str) -> Dict[str, str]:
    event = {
        "direction": direction,
        "payload": payload,
        "status": "acknowledged",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    events.append(event)
    return event


def _wait_for_completion(keb: KEB, expected_tasks: int, timeout_seconds: float) -> str:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        metrics = keb.get_metrics()
        completed = metrics["tasks_executed"] + metrics["tasks_failed"]
        if completed >= expected_tasks and metrics["queue_size"] == 0:
            return "completed"
        time.sleep(0.02)
    return "timeout"


def build_keb_runtime_status(timeout_seconds: float = 5.0) -> Dict[str, Any]:
    """Run a minimal KEB pulse and return queue/execution/feedback evidence."""
    feedback_events: List[Dict[str, Any]] = []
    keb = KEB(max_workers=2, max_memory_mb=256)

    started_at = datetime.now(timezone.utc).isoformat()
    keb.start()
    try:
        keb.schedule_task(
            "dow_to_keb_feedback",
            _feedback_task,
            priority=1,
            args=(feedback_events, "DOW_TO_KEB", "runtime evidence accepted"),
        )
        keb.schedule_task(
            "keb_to_dow_feedback",
            _feedback_task,
            priority=2,
            args=(feedback_events, "KEB_TO_DOW", "feedback loop closed"),
        )
        completion_status = _wait_for_completion(keb, expected_tasks=2, timeout_seconds=timeout_seconds)
        running_metrics = keb.get_metrics()
    finally:
        keb.stop(wait=True, timeout=timeout_seconds)

    final_metrics = keb.get_metrics()
    expected_directions = {"DOW_TO_KEB", "KEB_TO_DOW"}
    observed_directions = {event["direction"] for event in feedback_events}
    bridge_complete = expected_directions <= observed_directions
    task_complete = final_metrics["tasks_executed"] == 2 and final_metrics["tasks_failed"] == 0

    return {
        "schema_version": "0.1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "started_at": started_at,
        "status": "ok" if completion_status == "completed" and bridge_complete and task_complete else "attention",
        "completion_status": completion_status,
        "runtime": {
            "max_workers": final_metrics["max_workers"],
            "max_memory_mb": final_metrics["max_memory_mb"],
            "running_after_stop": final_metrics["running"],
        },
        "queue": {
            "tasks_submitted": final_metrics["tasks_submitted"],
            "tasks_executed": final_metrics["tasks_executed"],
            "tasks_failed": final_metrics["tasks_failed"],
            "queue_size_after_dispatch": running_metrics["queue_size"],
            "queue_size_after_stop": final_metrics["queue_size"],
        },
        "feedback_loop": {
            "directions_expected": sorted(expected_directions),
            "directions_observed": sorted(observed_directions),
            "events": feedback_events,
            "complete": bridge_complete,
        },
        "dmaic": {
            "define": "KEB runtime pulse must prove queue execution and bidirectional feedback, not only code presence.",
            "measure": "Capture submitted/executed/failed counts, queue depth and DOW/KEB directions.",
            "analyze": "Flag attention when either direction is missing or the queue fails to drain.",
            "improve": "Use this lightweight report as the next SSOT-style penetration probe.",
            "control": "Keep the emitted JSON generated, reproducible and excluded from source commits.",
        },
    }


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    args = parser.parse_args(argv)

    report = build_keb_runtime_status(timeout_seconds=args.timeout_seconds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
