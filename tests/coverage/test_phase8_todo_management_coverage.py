from __future__ import annotations

import json

from DMAIC_V3.phases.phase8_todo_management import TODOTracker


def test_register_todo_persists_defaults_and_statistics(tmp_path):
    tracker = TODOTracker(tmp_path)
    todo = {
        "phase": "phase8",
        "description": "Close coverage gap",
        "timestamp": "2026-10-04T20:00:00",
        "agent": "coverage",
    }
    todo_id = tracker.register_todo(todo)
    registry = json.loads(tracker.global_registry_path.read_text(encoding="utf-8"))
    stored = registry["todos"][0]
    assert todo_id == stored["todo_id"]
    assert stored["status"] == "pending"
    assert stored["priority"] == "medium"
    assert registry["total_todos"] == 1
    assert registry["statistics"]["by_status"] == {"pending": 1}
    assert registry["statistics"]["completion_rate"] == 0.0


def test_tracker_filters_updates_and_deduplicates_registry(tmp_path):
    tracker = TODOTracker(tmp_path)
    first = {
        "phase": "phase1", "description": "Define scope", "timestamp": "t1",
        "priority": "high", "agent": "alpha",
    }
    second = {
        "phase": "phase2", "description": "Measure baseline", "timestamp": "t2",
        "priority": "low", "status": "completed", "agent": "beta",
    }
    first_id = tracker.register_todo(first)
    second_id = tracker.register_todo(second)
    assert [t["todo_id"] for t in tracker.get_todos_by_priority("high")] == [first_id]
    assert [t["todo_id"] for t in tracker.get_todos_by_phase("phase2")] == [second_id]
    tracker.update_todo_status(first_id, "done")
    assert [t["todo_id"] for t in tracker.get_todos_by_status("done")] == [first_id]
    first_update = dict(first, status="completed")
    assert tracker.register_todo(first_update) == first_id
    registry = json.loads(tracker.global_registry_path.read_text(encoding="utf-8"))
    assert registry["total_todos"] == 2
    assert registry["statistics"]["completion_rate"] == 100.0


def test_statistics_handles_unknown_fields_and_empty_input(tmp_path):
    tracker = TODOTracker(tmp_path)
    assert tracker._calculate_statistics([])["completion_rate"] == 0.0
    stats = tracker._calculate_statistics([
        {"status": "done", "priority": "high", "phase": "p1", "agent": "a1"},
        {"status": "pending"},
    ])
    assert stats["by_status"] == {"done": 1, "pending": 1}
    assert stats["by_priority"] == {"high": 1, "unknown": 1}
    assert stats["completion_rate"] == 50.0
