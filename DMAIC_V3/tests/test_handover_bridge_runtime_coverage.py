"""Root and behavioral coverage for the DMAIC V3 handover bridge."""

from types import SimpleNamespace

from DMAIC_V3.core.handover_bridge import (
    HandoverBridge,
    IdempotentPhaseExecutor,
    integrate_phase4_opportunities,
)


def bridge():
    return HandoverBridge(config=object(), state_manager=object())


class DummyPhase:
    def __init__(self):
        self.calls = []

    def execute(self, iteration):
        self.calls.append(iteration)
        return True, {"value": iteration, "metrics": {"quality": 0.95}}


def test_executor_records_phase_and_metrics_once():
    b = bridge()
    b.begin_run("fixture-input")
    phase = DummyPhase()
    executor = IdempotentPhaseExecutor(phase, b, "measure")

    first = executor.execute(iteration=2, source="fixture")
    second = executor.execute(iteration=2, source="different-ignored-by-phase-cache")

    assert first == second == (True, {"value": 2, "metrics": {"quality": 0.95}})
    assert phase.calls == [2]

    records = [row for row in b.get_provenance_trail() if row["event"] == "phase"]
    assert len(records) == 1
    assert records[0]["phase"] == "measure"
    assert records[0]["iteration"] == 2
    assert records[0]["status"] == "success"
    assert records[0]["metrics"] == {"quality": 0.95}
    assert records[0]["inputs_hash"]
    assert records[0]["outputs_hash"]

    metrics = b.get_metrics_history()
    assert len(metrics) == 1
    assert metrics[0]["phase"] == "measure"
    assert metrics[0]["metrics"] == {"quality": 0.95}


def test_phase_cache_is_iteration_bound_and_resets_for_next_run():
    b = bridge()
    b.begin_run("first-input")
    phase = DummyPhase()
    executor = IdempotentPhaseExecutor(phase, b, "measure")

    # Auxiliary caller source is provenance only; it cannot re-run a phase.
    assert executor.execute(iteration=2, source="first") == executor.execute(
        iteration=2, source="replayed"
    )
    assert phase.calls == [2]

    # The iteration actually received by the phase is a behavioral input.
    executor.execute(iteration=3, source="new-iteration")
    assert phase.calls == [2, 3]
    assert [r["iteration"] for r in b.get_provenance_trail() if r["event"] == "phase"] == [2, 3]

    # Reusing a bridge for a new run cannot replay a previous run's cached result.
    b.begin_run("second-input")
    executor.execute(iteration=2, source="new-run")
    assert phase.calls == [2, 3, 2]
    assert [r["run_id"] for r in b.get_provenance_trail() if r["event"] == "phase"][-1] == b.run_id


def test_executor_records_failed_tuple_without_masking_status():
    b = bridge()
    b.begin_run("fixture-input")

    class FailedPhase:
        def execute(self, iteration):
            return False, {"metrics": {"errors": 1}}

    result = IdempotentPhaseExecutor(FailedPhase(), b, "analyze").execute(iteration=4)

    assert result == (False, {"metrics": {"errors": 1}})
    phase = next(row for row in b.get_provenance_trail() if row["event"] == "phase")
    assert phase["status"] == "failed"
    assert phase["metrics"] == {"errors": 1}


def test_plain_phase_result_records_success_and_empty_metrics():
    b = bridge()
    b.begin_run("fixture-input")

    class PlainPhase:
        def execute(self, iteration):
            return "done"

    assert IdempotentPhaseExecutor(PlainPhase(), b, "control").execute(iteration=1) == "done"
    phase = next(row for row in b.get_provenance_trail() if row["event"] == "phase")
    assert phase["status"] == "success"
    assert phase["metrics"] == {}


def test_iteration_stop_rules_cover_empty_max_converged_and_continue():
    b = bridge()
    assert b.should_stop_iteration([], []) == (False, "No history available")

    history = [{"quality_score": 0.5}, {"quality_score": 0.7}]
    stop, reason = b.should_stop_iteration(
        history,
        [{"type": "max_iterations", "value": 2}],
    )
    assert stop is True
    assert reason == "Max iterations reached: 2"

    stop, reason = b.should_stop_iteration(
        [{"quality_score": 0.5}, {"quality_score": 0.505}],
        [{"type": "convergence", "threshold": 0.01}],
    )
    assert stop is True
    assert "Converged" in reason

    assert b.should_stop_iteration(
        history,
        [{"type": "convergence", "threshold": 0.01}],
    ) == (False, "Continue iteration")


def test_convergence_analysis_covers_boundaries_and_result_shape():
    b = bridge()
    assert b.analyze_convergence([]) == {"converged": False, "reason": "No history"}
    assert b.analyze_convergence([{"quality_score": 1.0}]) == {
        "converged": False,
        "reason": "Insufficient data",
    }

    converged = b.analyze_convergence(
        [{"quality_score": 0.90}, {"quality_score": 0.905}, {"quality_score": 0.91}]
    )
    assert converged["converged"] is True
    assert converged["iterations"] == 3
    assert converged["final_score"] == 0.91
    assert abs(converged["avg_change"] - 0.005) < 1e-12

    moving = b.analyze_convergence(
        [{"quality_score": 0.1}, {"quality_score": 0.5}, {"quality_score": 0.9}]
    )
    assert moving["converged"] is False


def test_phase4_opportunity_integration_parses_and_matches_recommendations(tmp_path):
    source = tmp_path / "opportunities.md"
    source.write_text(
        "## OPP-001: Latency Reduction\n"
        "**Priority:** HIGH\n"
        "- Cache immutable inputs\n"
        "- Remove duplicate fetch\n",
        encoding="utf-8",
    )
    phase = SimpleNamespace()
    returned = integrate_phase4_opportunities(phase, source)

    assert returned is phase
    assert phase.opportunities == [
        {
            "id": "OPP-001",
            "title": "Latency Reduction",
            "priority": "HIGH",
            "actions": ["Cache immutable inputs", "Remove duplicate fetch"],
            "success_criteria": [],
        }
    ]

    integrated = phase.integrate_opportunities_with_recommendations(
        [
            {"issue_type": "latency_reduction", "id": "R1"},
            {"issue_type": "documentation", "id": "R2"},
        ]
    )
    assert integrated[0]["opportunity_id"] == "OPP-001"
    assert integrated[0]["related_recommendations"] == [
        {"issue_type": "latency_reduction", "id": "R1"}
    ]


def test_missing_phase4_opportunities_is_nonmutating(tmp_path):
    phase = SimpleNamespace(marker="same")
    assert integrate_phase4_opportunities(phase, tmp_path / "missing.md") is phase
    assert phase.marker == "same"
