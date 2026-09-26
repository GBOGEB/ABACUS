import json
from datetime import datetime
from types import SimpleNamespace

import pytest

from DMAIC_V3.core.state import (
    IterationState,
    PhaseState,
    PhaseStatus,
    StateManager,
)


@pytest.fixture
def manager(tmp_path):
    return StateManager(tmp_path / "state")


@pytest.mark.unit
def test_phase_and_iteration_defaults_are_isolated():
    first = PhaseState("p1", 1, PhaseStatus.PENDING)
    second = PhaseState("p2", 2, PhaseStatus.PENDING)
    iteration = IterationState(1, "2026-09-26T00:00:00")

    first.checkpoint_data["x"] = 1
    first.metrics["m"] = 2

    assert second.checkpoint_data == {}
    assert second.metrics == {}
    assert iteration.phases == {}


@pytest.mark.unit
def test_compute_hash_is_stable_for_dict_order_and_supports_other_values(manager):
    assert manager.compute_hash({"b": 2, "a": 1}) == manager.compute_hash({"a": 1, "b": 2})
    assert manager.compute_hash("hello") == manager.compute_hash("hello")
    assert manager.compute_hash(123) != manager.compute_hash(124)


@pytest.mark.unit
def test_iteration_phase_lifecycle_checkpoint_and_cached_result(manager):
    manager.start_iteration(7)
    assert manager.current_iteration.iteration_number == 7
    assert manager.current_iteration.status == "running"
    assert manager.state_file.exists()

    input_data = {"scope": "alpha"}
    manager.start_phase("phase1", 1, input_data)
    phase = manager.current_iteration.phases["phase1"]
    assert phase.status is PhaseStatus.RUNNING
    assert phase.input_hash == manager.compute_hash(input_data)
    assert manager.load_checkpoint("missing") is None

    manager.save_checkpoint("phase1", {"cursor": 3})
    manager.save_checkpoint("phase1", {"verified": True})
    assert manager.load_checkpoint("phase1") == {"cursor": 3, "verified": True}
    assert manager.is_phase_completed("phase1") is False
    assert manager.can_skip_phase("phase1", input_data) is False
    assert manager.get_phase_result("phase1") is None

    manager.end_phase(
        "phase1",
        PhaseStatus.COMPLETED,
        output_data={"result": "ok"},
        metrics={"checks": 4},
    )

    assert manager.is_phase_completed("phase1") is True
    assert manager.can_skip_phase("phase1", input_data) is True
    assert manager.can_skip_phase("phase1", {"scope": "changed"}) is False

    result = manager.get_phase_result("phase1")
    assert result["metrics"] == {"checks": 4}
    assert result["checkpoint_data"] == {"cursor": 3, "verified": True}
    assert result["output_hash"] == manager.compute_hash({"result": "ok"})
    assert manager.current_iteration.phases["phase1"].duration_seconds >= 0

    manager.end_iteration("completed")
    assert manager.current_iteration is None
    assert len(manager.execution_history) == 1
    assert manager.execution_history[0].status == "completed"


@pytest.mark.unit
def test_phase_errors_resume_point_and_guards(manager):
    assert manager.load_checkpoint("p") is None
    assert manager.is_phase_completed("p") is False
    assert manager.get_resume_point() is None

    with pytest.raises(RuntimeError, match="No active iteration"):
        manager.start_phase("p", 1)
    with pytest.raises(RuntimeError, match="No active iteration"):
        manager.end_phase("p", PhaseStatus.FAILED)
    with pytest.raises(RuntimeError, match="No active iteration"):
        manager.save_checkpoint("p", {})

    manager.start_iteration(1)

    with pytest.raises(RuntimeError, match="Phase missing not started"):
        manager.end_phase("missing", PhaseStatus.FAILED)
    with pytest.raises(RuntimeError, match="Phase missing not started"):
        manager.save_checkpoint("missing", {})

    manager.start_phase("phase2", 2)
    manager.end_phase("phase2", PhaseStatus.FAILED, error="boom")
    manager.start_phase("phase1", 1)

    assert manager.get_resume_point() == 1
    assert manager.current_iteration.phases["phase2"].error_message == "boom"


@pytest.mark.unit
def test_state_persists_and_reloads_complete_iteration(tmp_path):
    state_dir = tmp_path / "persist"
    writer = StateManager(state_dir)
    writer.start_iteration(3)
    writer.start_phase("phase3", 3, {"x": 1})
    writer.save_checkpoint("phase3", {"step": "saved"})
    writer.end_phase(
        "phase3",
        PhaseStatus.COMPLETED,
        output_data="done",
        metrics={"quality": 0.9},
    )

    reader = StateManager(state_dir)

    assert reader.current_iteration is not None
    phase = reader.current_iteration.phases["phase3"]
    assert phase.status is PhaseStatus.COMPLETED
    assert phase.checkpoint_data == {"step": "saved"}
    assert phase.metrics == {"quality": 0.9}
    assert reader.can_skip_phase("phase3", {"x": 1}) is True


@pytest.mark.unit
def test_execution_summary_for_current_and_history(manager):
    manager.start_iteration(4)
    manager.start_phase("p1", 1)
    manager.end_phase("p1", PhaseStatus.COMPLETED)
    manager.start_phase("p2", 2)

    summary = manager.get_execution_summary()
    assert summary["total_iterations"] == 0
    assert summary["current_iteration"]["iteration_number"] == 4
    assert summary["current_iteration"]["phases_completed"] == 1
    assert summary["current_iteration"]["phases_total"] == 2

    manager.end_iteration("failed")
    summary = manager.get_execution_summary()
    assert summary["total_iterations"] == 1
    assert summary["current_iteration"] is None
    assert summary["history"][0]["iteration_number"] == 4
    assert summary["history"][0]["status"] == "failed"


@pytest.mark.unit
def test_add_iteration_result_records_raw_and_summary_state(manager):
    metric = SimpleNamespace(to_dict=lambda: {"value": 9})
    knowledge = SimpleNamespace(to_dict=lambda: {"id": "kp-1"})
    start = datetime(2026, 9, 26, 12, 0, 0)
    end = datetime(2026, 9, 26, 12, 1, 0)
    result = SimpleNamespace(
        iteration=5,
        phases_completed=4,
        phases_failed=1,
        phases_skipped=0,
        total_duration_seconds=60.0,
        metrics={"score": metric},
        knowledge_packs=[knowledge],
        start_time=start,
        end_time=end,
        status="partial",
    )

    manager.add_iteration_result(result)

    assert manager.iteration_results[0]["iteration"] == 5
    assert manager.iteration_results[0]["metrics"] == {"score": {"value": 9}}
    assert manager.iteration_results[0]["knowledge_packs"] == [{"id": "kp-1"}]
    assert manager.execution_history[-1].iteration_number == 5
    assert manager.execution_history[-1].status == "partial"

    summary = manager.get_execution_summary()
    assert summary["iteration_results_count"] == 1


@pytest.mark.unit
def test_corrupt_state_file_fails_closed_without_crashing(tmp_path, capsys):
    state_dir = tmp_path / "corrupt"
    state_dir.mkdir()
    (state_dir / "execution_state.json").write_text("{not-json", encoding="utf-8")

    manager = StateManager(state_dir)

    captured = capsys.readouterr()
    assert "Could not load state" in captured.out
    assert manager.current_iteration is None
    assert manager.execution_history == []


@pytest.mark.unit
def test_serialization_shape_and_empty_input_hash_behavior(manager):
    manager.start_iteration(9)
    manager.start_phase("empty", 0, input_data={})
    phase = manager.current_iteration.phases["empty"]

    assert phase.input_hash is None

    payload = manager._serialize_state()
    assert payload["current_iteration"]["iteration_number"] == 9
    assert payload["current_iteration"]["phases"]["empty"]["status"] == "running"
    assert "last_updated" in payload

    raw = json.loads(manager.state_file.read_text(encoding="utf-8"))
    assert raw["current_iteration"]["phases"]["empty"]["phase_number"] == 0
