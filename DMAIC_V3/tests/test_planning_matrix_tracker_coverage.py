import json

import pytest
import yaml

from DMAIC_V3.core import planning_matrix_tracker as pmt
from DMAIC_V3.core.planning_matrix_tracker import PlanningMatrixTracker


@pytest.mark.unit
def test_defaults_and_reload_roundtrip(tmp_path):
    tracker = PlanningMatrixTracker(tmp_path)

    assert tracker.matrix["version"] == "3.3.0"
    assert tracker.matrix["planned"] == []
    assert tracker.history == []

    tracker.matrix["planned"] = [{"id": "p1"}]
    tracker.history.append({"iteration": 1, "matrix": {"planned": [{"id": "p1"}]}})
    tracker._save_matrix()
    tracker._save_history()

    reloaded = PlanningMatrixTracker(tmp_path)
    assert reloaded.matrix["planned"] == [{"id": "p1"}]
    assert reloaded.history[0]["iteration"] == 1


@pytest.mark.unit
def test_load_from_todo_yaml_handles_missing_and_parses_lists(tmp_path):
    tracker = PlanningMatrixTracker(tmp_path)

    missing = tracker.load_from_todo_yaml()
    assert missing == {"planned": [], "error": "TODO file not found"}

    tracker.todo_file.write_text(
        yaml.safe_dump(
            {
                "implementation": [
                    {
                        "id": "impl-1",
                        "description": "Implement thing",
                        "priority": "high",
                        "iteration": 3,
                        "estimated_hours": 4.5,
                        "dependencies": ["dep-1"],
                    },
                    {"task": "Fallback description"},
                ],
                "metadata": {"owner": "ignored"},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = tracker.load_from_todo_yaml()
    assert result["planned_count"] == 2
    first, second = result["planned_items"]
    assert first["id"] == "impl-1"
    assert first["priority"] == "HIGH"
    assert first["planned_iteration"] == 3
    assert first["estimated_hours"] == 4.5
    assert first["dependencies"] == ["dep-1"]
    assert second["description"] == "Fallback description"
    assert second["priority"] == "MEDIUM"
    assert tracker.matrix_file.exists()


@pytest.mark.unit
def test_load_from_todo_yaml_returns_error_for_bad_yaml(tmp_path):
    tracker = PlanningMatrixTracker(tmp_path)
    tracker.todo_file.write_text("broken: [1,\n", encoding="utf-8")

    result = tracker.load_from_todo_yaml()

    assert "error" in result
    assert result["planned"] == []


@pytest.mark.unit
def test_scan_actual_state_reads_valid_iterations_and_skips_malformed(tmp_path):
    tracker = PlanningMatrixTracker(tmp_path)
    output = tmp_path / "DMAIC_V3_OUTPUT"

    valid_phase = output / "iteration_2" / "phase1"
    valid_phase.mkdir(parents=True)
    (valid_phase / "phase1.json").write_text(
        json.dumps(
            {
                "timestamp": "2026-09-26T00:00:00",
                "duration_seconds": 1.25,
                "success": True,
            }
        ),
        encoding="utf-8",
    )

    default_success_phase = output / "iteration_2" / "phase2"
    default_success_phase.mkdir(parents=True)
    (default_success_phase / "phase2.json").write_text(
        json.dumps({"timestamp": "2026-09-26T00:01:00"}),
        encoding="utf-8",
    )

    malformed = output / "iteration_x" / "phase9"
    malformed.mkdir(parents=True)
    (malformed / "phase9.json").write_text("{}", encoding="utf-8")

    ignored = output / "iteration_3" / "phase3"
    ignored.mkdir(parents=True)

    result = tracker.scan_actual_state(output)

    assert result["actual_count"] == 2
    ids = {item["id"] for item in result["actual_items"]}
    assert ids == {"iter2_phase1", "iter2_phase2"}
    assert all(item["status"] == "COMPLETED" for item in result["actual_items"])
    assert next(item for item in result["actual_items"] if item["id"] == "iter2_phase2")["success"] is True
    assert tracker.matrix["actual"] == result["actual_items"]


@pytest.mark.unit
def test_determine_current_state_classifies_all_statuses(tmp_path):
    tracker = PlanningMatrixTracker(tmp_path)
    tracker.matrix["planned"] = [
        {"id": "done", "status": "PLANNED"},
        {"id": "blocked", "status": "BLOCKED"},
        {"id": "doing", "status": "IN_PROGRESS"},
        {"id": "later", "status": "PLANNED"},
    ]
    tracker.matrix["actual"] = [{"id": "done"}]

    current = tracker.determine_current_state()

    assert [item["id"] for item in current["completed"]] == ["done"]
    assert [item["id"] for item in current["blocked"]] == ["blocked"]
    assert [item["id"] for item in current["in_progress"]] == ["doing"]
    assert [item["id"] for item in current["pending"]] == ["later"]
    assert tracker.matrix["current"] == current


@pytest.mark.unit
def test_calculate_possible_next_marks_ready_and_blocked(tmp_path):
    tracker = PlanningMatrixTracker(tmp_path)
    tracker.matrix["current"] = {
        "completed": [{"id": "dep-ok"}],
        "in_progress": [],
        "blocked": [],
        "pending": [
            {
                "id": "ready-with-dep",
                "description": "Ready",
                "priority": "HIGH",
                "category": "implementation",
                "estimated_hours": 1.0,
                "dependencies": ["dep-ok"],
            },
            {
                "id": "ready-no-deps",
                "description": "No deps",
                "priority": "MEDIUM",
                "category": "testing",
                "dependencies": [],
            },
            {
                "id": "blocked",
                "description": "Blocked",
                "priority": "LOW",
                "category": "integration",
                "estimated_hours": 3.0,
                "dependencies": ["missing"],
            },
        ],
    }

    result = tracker.calculate_possible_next()

    by_id = {item["id"]: item for item in result["possible_items"]}
    assert result["possible_count"] == 3
    assert result["ready_count"] == 2
    assert by_id["ready-with-dep"]["ready"] is True
    assert by_id["ready-with-dep"]["reason"] == "All dependencies completed"
    assert by_id["ready-no-deps"]["ready"] is True
    assert by_id["ready-no-deps"]["estimated_hours"] == 2.0
    assert by_id["blocked"]["ready"] is False
    assert by_id["blocked"]["reason"] == "Blocked by: missing"


@pytest.mark.unit
def test_report_snapshot_and_completion_percentage(tmp_path):
    tracker = PlanningMatrixTracker(tmp_path)

    assert tracker.get_completion_percentage() == 0.0

    tracker.matrix["planned"] = [
        {"id": "a", "priority": "HIGH", "description": "A"},
        {"id": "b", "priority": "LOW", "description": "B"},
    ]
    tracker.matrix["actual"] = [{"id": "a", "description": "A completed"}]
    tracker.matrix["current"] = {
        "completed": [tracker.matrix["planned"][0]],
        "in_progress": [],
        "pending": [tracker.matrix["planned"][1]],
        "blocked": [],
    }
    tracker.matrix["possible"] = [
        {
            "id": "b",
            "priority": "LOW",
            "description": "B",
            "ready": True,
        }
    ]

    report = tracker.generate_report()
    assert "PLANNING MATRIX REPORT" in report
    assert "Total Planned: 2" in report
    assert "Total Completed: 1" in report
    assert "Ready to Start: 1" in report
    assert tracker.get_completion_percentage() == 50.0

    tracker.save_snapshot(7)
    persisted = json.loads(tracker.history_file.read_text(encoding="utf-8"))
    assert persisted[-1]["iteration"] == 7
    assert persisted[-1]["matrix"]["planned"][0]["id"] == "a"


@pytest.mark.unit
def test_main_exercises_cli_style_flow(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    (tmp_path / "TODO_V3.1_2025-11-10.yaml").write_text(
        yaml.safe_dump(
            {
                "testing": [
                    {
                        "id": "iter1_phase1",
                        "task": "Validate phase 1",
                        "priority": "high",
                        "dependencies": [],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    phase = tmp_path / "DMAIC_V3_OUTPUT" / "iteration_1" / "phase1"
    phase.mkdir(parents=True)
    (phase / "phase1.json").write_text(
        json.dumps({"timestamp": "2026-09-26T00:00:00", "success": True}),
        encoding="utf-8",
    )

    pmt.main()

    out = capsys.readouterr().out
    assert "Loaded 1 planned items" in out
    assert "Found 1 completed items" in out
    assert "Completed: 1" in out
    assert "Completion: 100.0%" in out
    assert (tmp_path / "planning_matrix.json").exists()
