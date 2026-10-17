"""Behavioral C3 coverage for handover idempotency and provenance."""

import json
from types import SimpleNamespace

from DMAIC_V3.core.handover_bridge import (
    HandoverBridge,
    IdempotentPhaseExecutor,
    integrate_phase4_opportunities,
)


def _bridge():
    return HandoverBridge(SimpleNamespace(), SimpleNamespace())


def test_wrap_phase_cache_is_bound_to_behavioral_inputs():
    bridge = _bridge()
    calls = []

    def execute(iteration, payload):
        calls.append((iteration, payload))
        return {"iteration": iteration, "payload": payload}

    first = bridge.wrap_phase("control", execute, 1, {"mode": "safe"})
    duplicate = bridge.wrap_phase("control", execute, 1, {"mode": "safe"})
    next_iteration = bridge.wrap_phase("control", execute, 2, {"mode": "safe"})
    changed_payload = bridge.wrap_phase("control", execute, 2, {"mode": "strict"})

    assert first == duplicate
    assert next_iteration["iteration"] == 2
    assert changed_payload["payload"]["mode"] == "strict"
    assert calls == [
        (1, {"mode": "safe"}),
        (2, {"mode": "safe"}),
        (2, {"mode": "strict"}),
    ]
    assert len(bridge._phase_cache) == 3


def test_idempotent_executor_uses_existing_action_and_metrics_ledgers():
    bridge = _bridge()
    bridge.begin_run("source-input")
    calls = []

    class Phase:
        def execute(self, iteration):
            calls.append(iteration)
            return True, {"phase": "improve", "metrics": {"score": iteration}}

    executor = IdempotentPhaseExecutor(Phase(), bridge, "improve")
    first = executor.execute(iteration=1, mode="bounded")
    duplicate = executor.execute(iteration=1, mode="bounded")
    second = executor.execute(iteration=2, mode="bounded")

    assert first == duplicate
    assert second[1]["metrics"]["score"] == 2
    assert calls == [1, 2]

    phases = [
        row for row in bridge.get_provenance_trail()
        if row.get("event") == "phase"
    ]
    assert [row["iteration"] for row in phases] == [1, 2]
    assert all(row["status"] == "success" for row in phases)
    assert all(len(row["inputs_hash"]) == 64 for row in phases)
    assert all(len(row["outputs_hash"]) == 64 for row in phases)
    assert [row["metrics"]["score"] for row in phases] == [1, 2]
    assert [row["metrics"]["score"] for row in bridge.get_metrics_history()] == [1, 2]


def test_idempotent_executor_records_failed_tuple_without_false_green():
    bridge = _bridge()
    bridge.begin_run("failure-input")

    class Phase:
        def execute(self, iteration):
            return False, {"phase": "measure", "metrics": {"errors": 1}}

    result = IdempotentPhaseExecutor(Phase(), bridge, "measure").execute(iteration=3)

    assert result[0] is False
    phase = [row for row in bridge.get_provenance_trail() if row.get("event") == "phase"][0]
    assert phase["status"] == "failed"
    assert phase["iteration"] == 3
    assert phase["metrics"] == {"errors": 1}
    assert bridge.get_metrics_history()[0]["metrics"] == {"errors": 1}


def test_stop_rules_and_convergence_cover_continue_and_stop_paths():
    bridge = _bridge()
    assert bridge.should_stop_iteration([], []) == (False, "No history available")

    history = [{"quality_score": 0.5}, {"quality_score": 0.5005}]
    stop, reason = bridge.should_stop_iteration(
        history,
        [{"type": "max_iterations", "value": 5}, {"type": "convergence", "threshold": 0.01}],
    )
    assert stop is True
    assert "Converged" in reason

    stop, reason = bridge.should_stop_iteration(
        [{"quality_score": 0.1}, {"quality_score": 0.4}],
        [{"type": "max_iterations", "value": 2}],
    )
    assert stop is True
    assert "Max iterations" in reason

    assert bridge.should_stop_iteration(
        [{"quality_score": 0.1}, {"quality_score": 0.4}],
        [{"type": "convergence", "threshold": 0.01}],
    ) == (False, "Continue iteration")

    assert bridge.analyze_convergence([]) == {"converged": False, "reason": "No history"}
    assert bridge.analyze_convergence([{"quality_score": 1.0}]) == {
        "converged": False,
        "reason": "Insufficient data",
    }
    converged = bridge.analyze_convergence(history)
    assert converged["converged"] is True
    assert converged["iterations"] == 2
    assert converged["final_score"] == 0.5005


def test_bridge_persistence_recent_rows_and_opportunity_integration(tmp_path):
    bridge = _bridge()
    bridge.begin_run("abcdef123456")
    bridge.log_action("define", "captured", {"root": "R1"})
    bridge.record_metrics("define", {"coverage": 0.8})
    bridge.finish_run("success", {"phases": 1})

    provenance_path = tmp_path / "provenance.json"
    metrics_path = tmp_path / "metrics.json"
    bridge.save_provenance(provenance_path)
    bridge.save_metrics(metrics_path)

    assert json.loads(provenance_path.read_text(encoding="utf-8"))[-1]["status"] == "success"
    assert json.loads(metrics_path.read_text(encoding="utf-8"))[0]["metrics"]["coverage"] == 0.8
    assert len(bridge.get_recent_runs(limit=2)) == 2
    assert bridge.get_recent_runs(limit=99) == bridge.get_provenance_trail()

    phase = SimpleNamespace()
    assert integrate_phase4_opportunities(phase, tmp_path / "missing.md") is phase

    source = tmp_path / "opportunities.md"
    source.write_text(
        "## OPP-001: Runtime error repair\n"
        "**Priority:** HIGH\n"
        "- Add regression test\n"
        "### OPP-002: Documentation clarity\n"
        "- Clarify handover\n",
        encoding="utf-8",
    )
    integrate_phase4_opportunities(phase, source)

    assert [row["id"] for row in phase.opportunities] == ["OPP-001", "OPP-002"]
    assert phase.opportunities[0]["priority"] == "HIGH"
    integrated = phase.integrate_opportunities_with_recommendations(
        [{"issue_type": "runtime_error"}, {"issue_type": "unrelated"}]
    )
    assert integrated[0]["related_recommendations"] == [{"issue_type": "runtime_error"}]
    assert integrated[1]["related_recommendations"] == []
