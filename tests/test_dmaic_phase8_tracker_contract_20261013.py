"""Phase 8 TODO tracker regression cases: statistics and status lookup."""

from pathlib import Path

import pytest

from DMAIC_V3.phases.phase8_todo_management import TODOTracker


@pytest.fixture
def tracker(tmp_path: Path):
    return TODOTracker(tmp_path)


def test_empty_statistics_are_safe(tracker):
    summary = tracker._calculate_statistics([])
    assert summary["total"] == 0
    assert summary["completion_rate"] == 0.0
    assert summary["by_status"] == {}
    assert summary["by_priority"] == {}


def test_mixed_todo_statistics_and_completion_aliases(tracker):
    todos = [
        {"status": "completed", "priority": "high", "phase": "define", "agent": "a"},
        {"status": "done", "priority": "high", "phase": "define", "agent": "b"},
        {"status": "pending", "priority": "low", "phase": "measure", "agent": "a"},
        {},
    ]
    result = tracker._calculate_statistics(todos)
    assert result["total"] == 4
    assert result["completion_rate"] == 50.0
    assert result["by_status"] == {
        "completed": 1,
        "done": 1,
        "pending": 1,
        "unknown": 1,
    }
    assert result["by_priority"] == {"high": 2, "low": 1, "unknown": 1}
    assert result["by_agent"] == {"a": 2, "b": 1, "unknown": 1}


@pytest.mark.parametrize(
    ("method", "query", "expected"),
    [
        ("get_todos_by_status", "pending", ["A"]),
        ("get_todos_by_priority", "high", ["A", "C"]),
        ("get_todos_by_phase", "measure", ["B", "C"]),
        ("get_todos_by_status", "missing", []),
    ],
)
def test_registry_filters_do_not_mutate_rows(
    tracker, monkeypatch, method, query, expected
):
    rows = [
        {"todo_id": "A", "status": "pending", "priority": "high", "phase": "define"},
        {"todo_id": "B", "status": "done", "priority": "low", "phase": "measure"},
        {"todo_id": "C", "status": "done", "priority": "high", "phase": "measure"},
    ]
    monkeypatch.setattr(tracker, "_load_global_registry", lambda: {"todos": rows})
    output = getattr(tracker, method)(query)
    assert [item["todo_id"] for item in output] == expected
    assert len(rows) == 3


@pytest.mark.parametrize(
    ("initial", "new", "expected"),
    [
        ("pending", "completed", 100.0),
        ("pending", "done", 100.0),
        ("completed", "pending", 0.0),
    ],
)
def test_status_transition_recomputes_registry_statistics(
    tracker, monkeypatch, initial, new, expected
):
    registry = {
        "todos": [{"todo_id": "T1", "status": initial, "priority": "high"}]
    }
    persisted = []
    monkeypatch.setattr(tracker, "_load_global_registry", lambda: registry)
    monkeypatch.setattr(
        "DMAIC_V3.phases.phase8_todo_management.safe_write_json",
        lambda data, path: persisted.append((data.copy(), path)),
    )
    tracker.update_todo_status("T1", new)
    assert registry["todos"][0]["status"] == new
    assert registry["statistics"]["completion_rate"] == expected
    assert persisted and persisted[0][1] == tracker.global_registry_path


def test_missing_todo_transition_keeps_rows_unchanged(tracker, monkeypatch):
    registry = {"todos": [{"todo_id": "T1", "status": "pending"}]}
    persisted = []
    monkeypatch.setattr(tracker, "_load_global_registry", lambda: registry)
    monkeypatch.setattr(
        "DMAIC_V3.phases.phase8_todo_management.safe_write_json",
        lambda data, path: persisted.append(path),
    )
    tracker.update_todo_status("missing", "completed")
    assert registry["todos"] == [{"todo_id": "T1", "status": "pending"}]
    assert registry["statistics"]["completion_rate"] == 0.0
    assert persisted == [tracker.global_registry_path]
