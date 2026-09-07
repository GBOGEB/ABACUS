from __future__ import annotations

import pytest

from DMAIC_V3.core.twelve_cluster_orchestrator import TwelveClusterOrchestrator


def _echo(value):
    return value


def _fail():
    raise RuntimeError("adversarial failure")


def _orchestrator() -> TwelveClusterOrchestrator:
    return TwelveClusterOrchestrator(
        max_workers=2,
        use_keb=False,
        use_gbogeb=False,
        task_timeout_seconds=2.0,
    )


def test_representative_all_mapped_phases_execute_and_preserve_results():
    orchestrator = _orchestrator()

    def factory(phase: str):
        return [
            {"task_id": f"{phase}-a", "func": _echo, "args": (f"{phase}:a",)},
            {"task_id": f"{phase}-b", "func": _echo, "args": (f"{phase}:b",)},
        ]

    result = orchestrator.run_phases_with_hooks(iteration=1, phase_task_factory=factory)

    assert result["success"] is True
    assert result["final_status"] == "completed"
    assert result["phases_run"] == list(orchestrator.PHASE_SEQUENCE)
    assert result["total_tasks_executed"] == 2 * len(orchestrator.PHASE_SEQUENCE)
    assert result["total_tasks_failed"] == 0
    assert len(result["temporal_events"]) == 2 * len(orchestrator.PHASE_SEQUENCE)

    for phase in orchestrator.PHASE_SEQUENCE:
        phase_result = result["phase_results"][phase]
        assert phase_result["success"] is True
        assert phase_result["tasks_executed"] == 2
        assert phase_result["tasks_failed"] == 0
        assert phase_result["results_map"][f"{phase}-a"] == f"{phase}:a"
        assert phase_result["results_map"][f"{phase}-b"] == f"{phase}:b"


def test_adversarial_unknown_phase_fails_closed():
    orchestrator = _orchestrator()
    with pytest.raises(ValueError, match="Unknown or unmapped phase"):
        orchestrator.execute_phase_parallel("phase99", [{"task_id": "x"}], iteration=1)


def test_adversarial_task_failure_is_counted_and_phase_fails_closed():
    orchestrator = _orchestrator()
    result = orchestrator.execute_phase_parallel(
        "phase3",
        [
            {"task_id": "good", "func": _echo, "args": ("ok",)},
            {"task_id": "bad", "func": _fail},
        ],
        iteration=1,
    )

    assert result["success"] is False
    assert result["tasks_executed"] == 1
    assert result["tasks_failed"] == 1
    assert result["results_map"]["good"] == "ok"
    assert "bad" not in result["results_map"]


def test_adversarial_empty_population_is_stable_zero_delta_success():
    orchestrator = _orchestrator()
    first = orchestrator.execute_phase_parallel("phase1", [], iteration=1)
    second = orchestrator.execute_phase_parallel("phase1", [], iteration=1)

    expected = {
        "success": True,
        "tasks_executed": 0,
        "tasks_failed": 0,
        "clusters_used": 0,
        "results_map": {},
        "execution_time": 0.0,
    }
    assert first == expected
    assert second == expected


def test_cluster_contract_is_complete_unique_and_phase_bound():
    orchestrator = _orchestrator()
    contract = orchestrator.get_cluster_contract()

    assert len(contract) == 12
    ids = [item["cluster_id"] for item in contract]
    assert ids == list(range(1, 13))
    assert len(set(item["name"] for item in contract)) == 12
    assert set(item["phase"] for item in contract) == set(orchestrator.PHASE_SEQUENCE)
