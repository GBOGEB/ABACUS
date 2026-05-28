#!/usr/bin/env python3
"""
Task Tracker V2.3.0
DMAIC-based task management for the V2.3 system
Tracks the 15 V2.3 tasks with priority, phase, and status metadata
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

__version__ = "v2.3.0"
__date__ = "2025-11-11"

# Default task database location (relative to repo root)
_DEFAULT_DB = Path(__file__).resolve().parent.parent / "tracking_v2.3" / "tasks" / "tasks.json"

# Valid status values
_STATUSES = {"pending", "in_progress", "completed", "blocked", "skipped"}


def _load_db(db_path: Path) -> Dict[str, Any]:
    """Load the task database, creating it if absent."""
    if db_path.exists():
        with open(db_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return {"version": __version__, "tasks": [], "last_updated": None}


def _save_db(db: Dict[str, Any], db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db["last_updated"] = datetime.now().isoformat()
    with open(db_path, "w", encoding="utf-8") as fh:
        json.dump(db, fh, indent=2)


def _find_task(tasks: List[Dict], task_id: str) -> Optional[Dict]:
    for task in tasks:
        if task.get("id") == task_id:
            return task
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class TaskTrackerV23:
    """V2.3 Task tracker with DMAIC-structured task management."""

    def __init__(self, db_path: Path = None):
        self.db_path = Path(db_path) if db_path else _DEFAULT_DB
        self.version = __version__

    def list_tasks(self, status_filter: str = None) -> List[Dict]:
        """Return all tasks, optionally filtered by status."""
        db = _load_db(self.db_path)
        tasks = db.get("tasks", [])
        if status_filter:
            tasks = [t for t in tasks if t.get("status") == status_filter]
        return tasks

    def add_task(
        self,
        task_id: str,
        title: str,
        phase: str,
        priority: int = 3,
        description: str = "",
    ) -> Dict:
        """Add a new task. Returns the created task dict."""
        db = _load_db(self.db_path)
        if _find_task(db["tasks"], task_id):
            raise ValueError(f"Task '{task_id}' already exists")
        task = {
            "id": task_id,
            "title": title,
            "phase": phase,
            "priority": priority,
            "description": description,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "completed_at": None,
        }
        db["tasks"].append(task)
        _save_db(db, self.db_path)
        return task

    def update_status(self, task_id: str, status: str) -> Dict:
        """Update the status of an existing task."""
        if status not in _STATUSES:
            raise ValueError(f"Invalid status '{status}'. Choose from: {_STATUSES}")
        db = _load_db(self.db_path)
        task = _find_task(db["tasks"], task_id)
        if not task:
            raise KeyError(f"Task '{task_id}' not found")
        task["status"] = status
        task["updated_at"] = datetime.now().isoformat()
        if status == "completed":
            task["completed_at"] = datetime.now().isoformat()
        _save_db(db, self.db_path)
        return task

    def get_summary(self) -> Dict[str, Any]:
        """Return a summary of task counts by status."""
        tasks = self.list_tasks()
        counts: Dict[str, int] = {s: 0 for s in _STATUSES}
        for task in tasks:
            s = task.get("status", "pending")
            counts[s] = counts.get(s, 0) + 1
        total = len(tasks)
        completed = counts.get("completed", 0)
        return {
            "total": total,
            "completed": completed,
            "progress_pct": round(completed / total * 100, 1) if total else 0.0,
            "by_status": counts,
            "version": self.version,
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Task Tracker V2.3 — manage V2.3 tasks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--db", default=str(_DEFAULT_DB), help="Path to tasks.json database")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="List all tasks")
    sub.add_parser("summary", help="Show completion summary")

    add_p = sub.add_parser("add", help="Add a new task")
    add_p.add_argument("id", help="Unique task ID (e.g. T-001)")
    add_p.add_argument("title", help="Short task title")
    add_p.add_argument("phase", help="DMAIC phase (Define/Measure/Analyze/Improve/Control)")
    add_p.add_argument("--priority", type=int, default=3, choices=[1, 2, 3, 4, 5])
    add_p.add_argument("--description", default="")

    upd_p = sub.add_parser("update", help="Update task status")
    upd_p.add_argument("id", help="Task ID to update")
    upd_p.add_argument("status", choices=sorted(_STATUSES))

    return parser


def main(argv: List[str] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    tracker = TaskTrackerV23(db_path=args.db)

    if args.command == "list" or args.command is None:
        tasks = tracker.list_tasks()
        if not tasks:
            print("No tasks found.")
        for t in tasks:
            print(f"[{t['status'].upper():10s}] {t['id']} | P{t['priority']} | {t['title']}")
        return 0

    if args.command == "summary":
        s = tracker.get_summary()
        print(f"Total tasks : {s['total']}")
        print(f"Completed   : {s['completed']}")
        print(f"Progress    : {s['progress_pct']}%")
        for status, count in sorted(s["by_status"].items()):
            print(f"  {status:12s}: {count}")
        return 0

    if args.command == "add":
        task = tracker.add_task(
            args.id, args.title, args.phase, args.priority, args.description
        )
        print(f"Added task: {task['id']} — {task['title']}")
        return 0

    if args.command == "update":
        task = tracker.update_status(args.id, args.status)
        print(f"Updated {task['id']} → {task['status']}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
