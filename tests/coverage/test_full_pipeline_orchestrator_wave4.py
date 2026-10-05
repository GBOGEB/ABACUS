from types import SimpleNamespace

from DMAIC_V3.full_pipeline_orchestrator import (
    FullPipelineOrchestrator,
    Phase7AdvancedAnalytics,
    Phase8RecursiveOptimization,
)


class _Phase:
    def __init__(self, result):
        self.result = result

    def execute(self, iteration):
        return self.result


def _orchestrator():
    obj = object.__new__(FullPipelineOrchestrator)
    obj.execution_log = []
    obj.statistics = {
        "phases": {},
        "agents": {},
        "orchestration": {
            "total_phases": 0,
            "successful_phases": 0,
            "failed_phases": 0,
            "total_duration_seconds": 0,
        },
    }
    return obj


def test_deprecated_phase_stubs_return_success():
    cfg = SimpleNamespace()
    state = SimpleNamespace()

    ok7, result7 = Phase7AdvancedAnalytics(cfg, state).execute(3)
    ok8, result8 = Phase8RecursiveOptimization(cfg, state).execute(4)

    assert ok7 is True
    assert result7["status"] == "DEPRECATED"
    assert result7["iteration"] == 3
    assert ok8 is True
    assert result8["status"] == "DEPRECATED"
    assert result8["iteration"] == 4


def test_execute_phase_with_tracking_handles_tuple_and_dict_results():
    orch = _orchestrator()

    success1, result1 = orch._execute_phase_with_tracking(
        _Phase((True, {"phase": "tuple"})), "Tuple Phase", 1
    )
    success2, result2 = orch._execute_phase_with_tracking(
        _Phase({"phase": "dict"}), "Dict Phase", 2
    )

    assert success1 is True
    assert result1 == {"phase": "tuple"}
    assert success2 is True
    assert result2 == {"phase": "dict"}
    assert orch.statistics["orchestration"]["total_phases"] == 2
    assert orch.statistics["orchestration"]["successful_phases"] == 2
    assert orch.statistics["phases"]["Tuple Phase"]["executions"] == 1


def test_execute_phase_with_tracking_records_failure_and_exception():
    orch = _orchestrator()

    success, result = orch._execute_phase_with_tracking(
        _Phase((False, {"phase": "failed"})), "Failed Phase", 1
    )
    assert success is False
    assert result["phase"] == "failed"

    class _Crash:
        def execute(self, iteration):
            raise RuntimeError("boom")

    success, result = orch._execute_phase_with_tracking(_Crash(), "Crash Phase", 2)

    assert success is False
    assert result == {"error": "boom"}
    assert orch.statistics["orchestration"]["failed_phases"] == 2
