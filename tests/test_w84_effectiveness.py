from abacus_runtime.w84_effectiveness import score


def test_missing_observation_defers():
    assert score({})["status"] == "DEFER_MISSING_OBSERVED_METRICS"


def positive_cycle():
    return {
        "parent_chain_complete": True,
        "execution_effort": 2,
        "accepted_atoms_before": 0,
        "accepted_atoms_after": 2,
        "dov_before": 0.0,
        "dov_after": 0.1,
        "recommendations_executed": 2,
        "recommendations_successful": 1,
        "retries": 1,
        "successful_repaired_tasks": 1,
        "residual_before": 6,
        "residual_after": 4,
        "debug_spine": {"runtime.error": 1},
    }


def test_parent_chain_must_complete_before_effectiveness_pass():
    cycle = positive_cycle()
    cycle["parent_chain_complete"] = False
    receipt = score(cycle)
    assert receipt["status"] == "DEFER_PARENT_CHAIN_INCOMPLETE"
    assert receipt["engineering_credit_delta"] == 0


def test_positive_cycle_scores_without_scheduler_or_engineering_credit():
    receipt = score(positive_cycle())
    assert receipt["status"] == "PASS_POSITIVE_EFFECTIVENESS"
    assert receipt["evidence_yield"] == 1.0
    assert receipt["pressure_reduction"] == 2.0
    assert receipt["adaptive_scheduler_credit"] is False
    assert receipt["engineering_credit_delta"] == 0
