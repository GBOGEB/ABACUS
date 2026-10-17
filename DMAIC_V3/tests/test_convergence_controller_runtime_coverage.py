"""Behavioral C4 coverage for convergence change and iteration control."""

import json
import os

from DMAIC_V3.convergence.change_detector import ChangeDetector, FileChange
from DMAIC_V3.convergence.iterative_controller import (
    IterationMetrics,
    IterativeController,
)


PHASES = [
    "phase0_init",
    "phase1_define",
    "phase2_measure",
    "phase3_analyze",
    "phase4_improve",
    "phase5_control",
]


def test_change_detector_lifecycle_preserves_added_modified_deleted_identity(tmp_path):
    workspace = tmp_path / "repo"
    state = tmp_path / "state"
    tracked = workspace / "nested"
    tracked.mkdir(parents=True)
    target = tracked / "source.py"
    target.write_text("value = 1\n", encoding="utf-8")

    detector = ChangeDetector(workspace, state)
    first = detector.detect_changes([target])
    assert [(row.path, row.change_type) for row in first] == [
        ("nested/source.py", "added")
    ]
    assert detector.get_change_summary()["added"] == 1
    assert detector.get_changed_files({".py"}) == ["nested/source.py"]
    assert detector.has_changes() is True

    original = target.stat().st_mtime
    target.write_text("value = 200\n", encoding="utf-8")
    os.utime(target, (original + 3, original + 3))
    second = detector.detect_changes([target])
    assert [(row.path, row.change_type) for row in second] == [
        ("nested/source.py", "modified")
    ]

    target.unlink()
    third = detector.detect_changes([])
    assert [(row.path, row.change_type) for row in third] == [
        ("nested/source.py", "deleted")
    ]
    assert detector.get_change_summary()["deleted"] == 1
    assert detector.get_changed_files() == []


def test_change_detector_legacy_windows_snapshot_does_not_create_phantom_change(tmp_path):
    workspace = tmp_path / "repo"
    state = tmp_path / "state"
    tracked = workspace / "DMAIC_V3"
    tracked.mkdir(parents=True)
    target = tracked / "same.py"
    target.write_text("same = True\n", encoding="utf-8")
    detector = ChangeDetector(workspace, state)

    detector.snapshot_file.write_text(
        json.dumps(
            {
                "DMAIC_V3\\same.py": {
                    "size": target.stat().st_size,
                    "mtime": target.stat().st_mtime,
                }
            }
        ),
        encoding="utf-8",
    )

    assert list(detector.load_previous_snapshot()) == ["DMAIC_V3/same.py"]
    assert detector.detect_changes([target]) == []


def test_change_detector_snapshot_hash_filters_and_fail_closed_state(tmp_path):
    workspace = tmp_path / "repo"
    state = tmp_path / "state"
    workspace.mkdir()
    good = workspace / "good.txt"
    good.write_text("payload", encoding="utf-8")
    missing = workspace / "missing.txt"

    detector = ChangeDetector(workspace, state)
    snapshot = detector.create_snapshot([good, missing])
    assert list(snapshot) == ["good.txt"]
    assert len(snapshot["good.txt"]["hash"]) == 64
    assert detector.compute_file_hash(workspace) == ""

    assert detector.get_change_summary() == {
        "total": 0,
        "added": 0,
        "modified": 0,
        "deleted": 0,
    }
    assert detector.has_changes() is True

    detector.snapshot_file.write_text("[]", encoding="utf-8")
    assert detector.load_previous_snapshot() == {}
    detector.changes_file.write_text("{bad json", encoding="utf-8")
    assert detector.get_changed_files() == []
    assert detector.get_change_summary()["total"] == 0
    assert detector.has_changes() is True


def test_file_change_auto_timestamp_and_explicit_timestamp():
    generated = FileChange(path="x.py", change_type="added")
    explicit = FileChange(path="y.py", change_type="deleted", timestamp="fixed")
    assert generated.timestamp
    assert explicit.timestamp == "fixed"


def test_iteration_recording_persists_runtime_fields_and_reload(tmp_path):
    controller = IterativeController(tmp_path / "repo", tmp_path / "out", max_iterations=4)

    controller.record_iteration(
        iteration=1,
        files_processed=100,
        changes_detected=20,
        phases_executed=PHASES,
        execution_time=2.5,
    )
    assert len(controller.iteration_history) == 1
    first = controller.iteration_history[0]
    assert first.execution_time_seconds == 2.5
    assert first.maturity_level == controller.determine_maturity_level(
        first.convergence_score, 1
    )

    controller.record_iteration(
        iteration=2,
        files_processed=100,
        changes_detected=2,
        phases_executed=PHASES,
        execution_time=1.5,
    )
    status = controller.get_convergence_status()
    assert status["current_iteration"] == 2
    assert status["total_files_processed"] == 200
    assert status["total_changes_detected"] == 22
    assert status["total_execution_time"] == 4.0

    restored = IterativeController(tmp_path / "repo", tmp_path / "out", max_iterations=4)
    restored.load_history()
    assert [row.iteration for row in restored.iteration_history] == [1, 2]
    assert restored.iteration_history[-1].execution_time_seconds == 1.5
    report = restored.generate_convergence_report()
    assert "Iteration 2:" in report
    assert "Time: 1.50s" in report


def test_iteration_continue_stop_and_convergence_paths(tmp_path, monkeypatch):
    controller = IterativeController(tmp_path / "repo", tmp_path / "out", max_iterations=3)

    assert controller.should_continue_iteration(1) == (True, "Initial iteration")
    assert controller.should_continue_iteration(3)[0] is False

    monkeypatch.setattr(controller.change_detector, "has_changes", lambda: False)
    assert controller.should_continue_iteration(2) == (
        False,
        "No changes detected since last iteration",
    )

    monkeypatch.setattr(controller.change_detector, "has_changes", lambda: True)
    controller.iteration_history = [
        IterationMetrics(iteration=1, files_processed=100, changes_detected=20),
        IterationMetrics(
            iteration=2,
            files_processed=100,
            changes_detected=1,
            maturity_level="developing",
        ),
    ]
    assert controller._is_converged() is True
    assert controller.should_continue_iteration(2) == (False, "System has converged")

    controller.iteration_history[-1].changes_detected = 20
    assert controller._is_converged() is False
    assert controller.should_continue_iteration(2) == (
        True,
        "Changes detected, continuing iteration 2",
    )

    controller.iteration_history[-1].maturity_level = "mature"
    assert controller._is_converged() is True


def test_convergence_score_and_maturity_thresholds_are_bounded(tmp_path):
    controller = IterativeController(tmp_path / "repo", tmp_path / "out")

    zero_files = controller.calculate_convergence_score(0, 0, PHASES)
    assert zero_files == 0.85

    controller.iteration_history = [
        IterationMetrics(iteration=1, files_processed=100, changes_detected=50),
        IterationMetrics(iteration=2, files_processed=100, changes_detected=40),
    ]
    improving = controller.calculate_convergence_score(100, 10, PHASES)
    non_improving = controller.calculate_convergence_score(100, 60, PHASES)
    assert improving > non_improving
    assert 0.0 <= non_improving <= 1.0
    assert 0.0 <= improving <= 1.0

    assert controller.determine_maturity_level(0.95, 4) == "converged"
    assert controller.determine_maturity_level(0.75, 3) == "mature"
    assert controller.determine_maturity_level(0.45, 2) == "developing"
    assert controller.determine_maturity_level(0.1, 1) == "initial"


def test_convergence_status_and_empty_report_fail_closed(tmp_path):
    controller = IterativeController(tmp_path / "repo", tmp_path / "out")
    assert controller.get_convergence_status() == {
        "is_converged": False,
        "maturity_level": "initial",
    }
    assert controller.generate_convergence_report() == "No iterations completed yet."

    controller.convergence_file.write_text("{bad json", encoding="utf-8")
    assert controller.get_convergence_status() == {
        "is_converged": False,
        "maturity_level": "initial",
    }

    controller.metrics_file.write_text("{bad json", encoding="utf-8")
    controller.load_history()
    assert controller.iteration_history == []
