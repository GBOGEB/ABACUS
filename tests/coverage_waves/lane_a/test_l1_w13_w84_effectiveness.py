"""Lane A wave 13: abacus_runtime.w84_effectiveness scorer and CLI."""

import json
import sys

from abacus_runtime import w84_effectiveness as w84


def _cycle(**overrides):
    base = {
        "execution_effort": 2.0,
        "accepted_atoms_before": 1,
        "accepted_atoms_after": 5,
        "dov_before": 0,
        "dov_after": 2,
        "recommendations_executed": 4,
        "recommendations_successful": 3,
        "retries": 2,
        "successful_repaired_tasks": 1,
        "residual_before": 10,
        "residual_after": 4,
        "parent_chain_complete": True,
    }
    base.update(overrides)
    return base


def test_missing_metrics_deferred():
    result = w84.score({"execution_effort": 1})
    assert result["status"] == "DEFER_MISSING_OBSERVED_METRICS"
    assert "dov_before" in result["missing"]
    assert "execution_effort" not in result["missing"]


def test_parent_chain_not_true_deferred():
    result = w84.score(_cycle(parent_chain_complete="yes"))
    assert result["status"] == "DEFER_PARENT_CHAIN_INCOMPLETE"
    assert result["engineering_credit_delta"] == 0


def test_non_positive_effort_deferred():
    result = w84.score(_cycle(execution_effort=0))
    assert result == {"status": "DEFER_INVALID_EFFORT", "execution_effort": 0.0}


def test_positive_effectiveness_values():
    result = w84.score(_cycle(debug_spine={"x": 1}))
    assert result["status"] == "PASS_POSITIVE_EFFECTIVENESS"
    assert result["evidence_yield"] == 2.0
    assert result["dov_yield"] == 1.0
    assert result["recommendation_hit_rate"] == 0.75
    assert result["retry_efficiency"] == 0.5
    assert result["pressure_reduction"] == 6.0
    assert result["debug_spine"] == {"x": 1}
    assert result["adaptive_scheduler_credit"] is False


def test_zero_recs_and_retries_give_none_and_no_positive():
    result = w84.score(_cycle(recommendations_executed=0, retries=0, residual_after=10))
    assert result["status"] == "OBSERVED_NO_POSITIVE_EFFECTIVENESS"
    assert result["recommendation_hit_rate"] is None
    assert result["retry_efficiency"] is None
    assert result["debug_spine"] == {}


def test_main_writes_output_and_returns_zero(tmp_path, monkeypatch):
    src = tmp_path / "cycle.json"
    src.write_text(json.dumps(_cycle()), encoding="utf-8")
    out = tmp_path / "nested" / "receipt.json"
    monkeypatch.setattr(sys, "argv", ["w84", str(src), "--output", str(out)])
    assert w84.main() == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["status"] == "PASS_POSITIVE_EFFECTIVENESS"


def test_main_prints_and_returns_two(tmp_path, monkeypatch, capsys):
    src = tmp_path / "cycle.json"
    src.write_text(json.dumps({}), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["w84", str(src)])
    assert w84.main() == 2
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "DEFER_MISSING_OBSERVED_METRICS"
