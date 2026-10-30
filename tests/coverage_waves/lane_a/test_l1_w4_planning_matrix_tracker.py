"""Lane A wave 4: DMAIC_V3.core.planning_matrix_tracker."""

import json

import pytest

from DMAIC_V3.core import planning_matrix_tracker as pmt

TODO_NAME = "TODO_V3.1_2025-11-10.yaml"

TODO_YAML = """\
implementation:
  - id: impl_a
    description: Build A
    priority: high
    iteration: 2
    estimated_hours: 5
  - task: Build B without id
  - just a string
  - id: impl_c
    description: Build C
    dependencies: [impl_a]
notes: not a list
"""


@pytest.fixture
def tracker(tmp_path):
    return pmt.PlanningMatrixTracker(tmp_path)


def _write_phase(root, iteration, phase, data):
    phase_dir = root / iteration / phase
    phase_dir.mkdir(parents=True)
    payload = json.dumps(data).encode()
    (phase_dir / (phase + ".json")).write_bytes(payload)


def test_planning_item_dataclass_fields():
    item = pmt.PlanningItem(
        "i1",
        "d",
        "PLANNED",
        "HIGH",
        "testing",
        1,
        None,
        1.5,
        None,
        [],
        None,
        "t",
        None,
        None,
    )
    assert item.id == "i1" and item.dependencies == [] and item.actual_hours is None


def test_fresh_tracker_defaults(tracker, tmp_path):
    assert tracker.matrix["version"] == "3.3.0"
    assert tracker.matrix["planned"] == []
    assert tracker.history == []
    assert tracker.todo_file == tmp_path / TODO_NAME
    assert tracker.get_completion_percentage() == 0.0


def test_loads_existing_matrix_and_history(tmp_path):
    matrix = {"planned": [{"id": "x"}], "actual": [], "current": {}, "possible": []}
    (tmp_path / "planning_matrix.json").write_bytes(json.dumps(matrix).encode())
    (tmp_path / "planning_history.json").write_bytes(b'[{"iteration": 1}]')
    tracker = pmt.PlanningMatrixTracker(tmp_path)
    assert tracker.matrix["planned"] == [{"id": "x"}]
    assert tracker.history == [{"iteration": 1}]


def test_load_todo_missing_file(tracker):
    assert tracker.load_from_todo_yaml() == {
        "planned": [],
        "error": "TODO file not found",
    }


def test_load_todo_parses_items_and_saves(tracker, tmp_path):
    (tmp_path / TODO_NAME).write_bytes(TODO_YAML.encode())
    result = tracker.load_from_todo_yaml()
    assert result["planned_count"] == 3
    items = {i["id"]: i for i in result["planned_items"]}
    assert items["impl_a"]["priority"] == "HIGH"
    assert items["impl_a"]["planned_iteration"] == 2
    assert items["impl_a"]["estimated_hours"] == 5
    # second item: generated id, description falls back to task, defaults
    assert items["implementation_1"]["description"] == "Build B without id"
    assert items["implementation_1"]["priority"] == "MEDIUM"
    assert items["implementation_1"]["planned_iteration"] == 1
    assert items["implementation_1"]["estimated_hours"] == 2.0
    assert items["impl_c"]["dependencies"] == ["impl_a"]
    assert all(i["status"] == "PLANNED" for i in result["planned_items"])
    saved = json.loads((tmp_path / "planning_matrix.json").read_bytes())
    assert len(saved["planned"]) == 3


def test_load_todo_unknown_description(tracker, tmp_path):
    (tmp_path / TODO_NAME).write_bytes(b"cat:\n  - id: z\n")
    item = tracker.load_from_todo_yaml()["planned_items"][0]
    assert item["description"] == "Unknown"


def test_load_todo_error_is_reported(tracker, tmp_path):
    (tmp_path / TODO_NAME).write_bytes(b"cat:\n  - id: z\n    priority: 3\n")
    result = tracker.load_from_todo_yaml()
    assert result["planned"] == []
    assert "upper" in result["error"]


def test_scan_actual_state(tracker, tmp_path):
    out = tmp_path / "out"
    _write_phase(
        out, "iteration_1", "phase1_define", {"timestamp": "T", "duration_seconds": 3}
    )
    _write_phase(out, "iteration_2", "phase2_measure", {"success": False})
    (out / "iteration_2" / "phase3_empty").mkdir()
    (out / "iteration_x").mkdir()
    (out / "iteration_").mkdir()
    (out / "iterationfoo").mkdir()
    result = tracker.scan_actual_state(out)
    assert result["actual_count"] == 2
    by_id = {i["id"]: i for i in result["actual_items"]}
    first = by_id["iter1_phase1_define"]
    assert first["description"] == "Phase1 Define completed"
    assert first["timestamp"] == "T" and first["duration"] == 3
    assert first["success"] is True
    assert by_id["iter2_phase2_measure"]["success"] is False
    assert by_id["iter2_phase2_measure"]["iteration"] == 2


def _seed(tracker, planned, actual_ids):
    tracker.matrix["planned"] = planned
    tracker.matrix["actual"] = [{"id": a, "description": a} for a in actual_ids]


def _item(item_id, priority="MEDIUM", status="PLANNED", deps=None):
    return {
        "id": item_id,
        "description": "do " + item_id,
        "priority": priority,
        "category": "c",
        "status": status,
        "dependencies": deps or [],
    }


def test_determine_current_state_buckets(tracker, tmp_path):
    planned = [
        _item("done"),
        _item("blk", status="BLOCKED"),
        _item("wip", status="IN_PROGRESS"),
        _item("todo"),
    ]
    _seed(tracker, planned, ["done"])
    state = tracker.determine_current_state()
    assert [i["id"] for i in state["completed"]] == ["done"]
    assert [i["id"] for i in state["blocked"]] == ["blk"]
    assert [i["id"] for i in state["in_progress"]] == ["wip"]
    assert [i["id"] for i in state["pending"]] == ["todo"]
    assert tracker.get_completion_percentage() == 25.0
    saved = json.loads((tmp_path / "planning_matrix.json").read_bytes())
    assert saved["current"]["completed"][0]["id"] == "done"


def test_calculate_possible_next_ready_and_blocked(tracker):
    planned = [
        _item("base"),
        _item("free"),
        _item("after_base", deps=["base"]),
        _item("after_free", deps=["free", "other"]),
    ]
    _seed(tracker, planned, ["base"])
    tracker.determine_current_state()
    result = tracker.calculate_possible_next()
    assert result["possible_count"] == 3
    assert result["ready_count"] == 2
    by_id = {p["id"]: p for p in result["possible_items"]}
    # all() over an empty dependency list is True, so this reason wins
    assert by_id["free"]["reason"] == "All dependencies completed"
    assert by_id["after_base"]["ready"] is True
    assert by_id["after_free"]["ready"] is False
    assert by_id["after_free"]["reason"] == "Blocked by: free, other"
    assert by_id["after_free"]["estimated_hours"] == 2.0
    # ready items sort before blocked ones
    assert result["possible_items"][-1]["id"] == "after_free"


def check_production_defect_possible_next_sorts_high_priority_last(tracker):
    """Priority strings sort reverse-alphabetically (MEDIUM > LOW > HIGH)."""
    # Reproduction of a production_defect (see WAVE_LEDGER.jsonl). Named check_*
    # so the governed suite does not collect it: a pinned defect must never block
    # the fix. Run on demand: pytest -o python_functions=check_* <this file>
    tracker.matrix["current"] = {
        "completed": [],
        "pending": [_item("low", priority="LOW"), _item("high", priority="HIGH")],
    }
    items = tracker.calculate_possible_next()["possible_items"]
    assert [i["id"] for i in items] == ["low", "high"]


def check_production_defect_fresh_tracker_report_crashes(tracker):
    """Default matrix sets 'current' to a list; report code calls .get() on it."""
    # Reproduction of a production_defect (see WAVE_LEDGER.jsonl). Named check_*
    # so the governed suite does not collect it: a pinned defect must never block
    # the fix. Run on demand: pytest -o python_functions=check_* <this file>
    with pytest.raises(AttributeError, match="get"):
        tracker.generate_report()


def test_generate_report_contents(tracker):
    planned = [_item("a", priority="HIGH"), _item("b", deps=["zz"])]
    _seed(tracker, planned, ["a"])
    tracker.determine_current_state()
    tracker.calculate_possible_next()
    report = tracker.generate_report()
    assert "Total Planned: 2" in report
    assert "  [HIGH] do a" in report
    assert "Total Completed: 1" in report
    assert "  [OK] a" in report
    assert "Completed: 1" in report and "Pending: 1" in report
    assert "Ready to Start: 0" in report
    tracker.matrix["possible"] = [
        {"ready": True, "priority": "LOW", "description": "go"},
        {"ready": False, "priority": "LOW", "description": "wait"},
    ]
    report = tracker.generate_report()
    assert "Ready to Start: 1" in report
    assert "[LOW] go" in report and "wait" not in report


def test_save_snapshot_appends_history(tracker, tmp_path):
    tracker.save_snapshot(3)
    tracker.save_snapshot(4)
    history = json.loads((tmp_path / "planning_history.json").read_bytes())
    assert [h["iteration"] for h in history] == [3, 4]
    assert history[0]["matrix"]["version"] == "3.3.0"


def test_main_runs_end_to_end(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / TODO_NAME).write_bytes(b"cat:\n  - id: iter1_phase1\n")
    _write_phase(tmp_path / "DMAIC_V3_OUTPUT", "iteration_1", "phase1", {})
    # pre-seed 'current' as a dict so the report path works on this matrix
    seed = {"planned": [], "actual": [], "current": {}, "possible": []}
    (tmp_path / "planning_matrix.json").write_bytes(json.dumps(seed).encode())
    pmt.main()
    out = capsys.readouterr().out
    assert "Loaded 1 planned items" in out
    assert "Found 1 completed items" in out
    assert "Completion: 100.0%" in out


def test_main_without_output_dir(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    seed = {"planned": [], "actual": [], "current": {}, "possible": []}
    (tmp_path / "planning_matrix.json").write_bytes(json.dumps(seed).encode())
    pmt.main()
    out = capsys.readouterr().out
    assert "Loaded 0 planned items" in out
    assert "completed items" not in out
    assert "Completion: 0.0%" in out
