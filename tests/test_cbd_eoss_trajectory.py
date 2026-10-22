"""W8: adversarial EOSS convergence, forecast and efficiency tests.

Synthetic four-wave fixtures assert method invariants; they are NOT native CI.
"""
from __future__ import annotations

import copy
import math
from datetime import datetime, timedelta, timezone

import pytest

from scripts import cbd_eoss_trajectory as t

D = "a" * 64
S = "b" * 64
C = "c" * 64
H = "d" * 64


def snapshot(*, coverage=None, clocks=True):
    baseline = {"covered_statements": 207, "covered_branches": 39}
    row = []
    for index, wave in enumerate(t.WAVES):
        coverage_values = (baseline if index == 0 else
                           {"covered_statements": 210, "covered_branches": 42})
        digest = coverage or D
        row.append({
            "wave": wave,
            "observed_at": f"2026-10-17T1{index}:00:00Z",
            "head_sha": (chr(97 + index) * 40),
            "evidence_tier": "LOCAL_REPRODUCIBILITY",
            "authority": {"admission": "HOLD", "security_waiver": False,
                          "authority_transfer": False},
            "tests": {"collected": [67, 73, 99, 99][index],
                      "passed": [67, 73, 99, 99][index], "failed": 0, "skipped": 0},
            "coverage": {"source_content_sha256": digest,
                         "scope_sha256": S, "config_sha256": C,
                         "tool_version": "coverage.py 7.13.3",
                         "eligible_statements": 210, "eligible_branches": 42,
                         **coverage_values},
            "clock": ({"basis": "LOCAL_MONOTONIC_WALL", "workload_sha256": H,
                       "host_sha256": H, "duration_ms": [150.0, 145.0, 149.0]}
                      if clocks else None),
            "historical_backlog": {"n0_total": 253, "observed_run_ids": 60,
                                   "formal_roots_closed": None},
        })
    return {"schema": t.SOURCE_SCHEMA, "repository": "GBOGEB/ABACUS",
            "observations": row, "forecasts": []}


def test_four_wave_n5_to_w9_is_approaching_plateau_only():
    result = t.run(snapshot())
    assert result["trajectory"]["state"] == "APPROACHING_PLATEAU_AFTER_GAIN"
    assert result["trajectory"]["matched_pairs"] == 3
    assert result["trajectory"]["branch_deltas_pp"] == [7.142857, 0.0, 0.0]
    assert result["trajectory"]["branch_second_difference_pp"] == [-7.142857, 0.0]
    assert result["growth_in_tests_passed"] == 32
    assert result["n0_runs_remaining"] == 193
    assert result["main_coverage_uplift_pp"] is None
    assert result["github_runner_speedup_seconds"] is None
    assert result["authority"]["admission"] == "HOLD"


def test_three_flat_matched_coverage_deltas_are_descriptive_not_certified():
    p = snapshot()
    p["observations"][0]["coverage"].update(covered_statements=210,
                                            covered_branches=42)
    d = t.run(p)["trajectory"]
    assert d["state"] == "DESCRIPTIVE_STABLE_PLATEAU"
    assert d["certified_convergence"] is False


def test_positive_acceleration_is_descriptive_not_approved():
    pairs = [{"qualified": True, "statement_delta_pp": 1,
              "branch_delta_pp": v} for v in (1, 2, 3)]
    assert t.classify(pairs)["state"] == "DESCRIPTIVE_ACCELERATING_BRANCH_GAINS"
    assert t.classify(pairs)["certified_convergence"] is False


def test_negative_branch_delta_preserved_not_clipped():
    p = snapshot()
    p["observations"][2]["coverage"]["covered_branches"] = 37
    d = t.run(p)
    assert d["trajectory"]["state"] == "REGRESSION_OBSERVED"
    assert d["coverage_pairs"][1]["branch_delta_pp"] < 0


@pytest.mark.parametrize("field,value", [
    ("eligible_statements", True), ("eligible_statements", 0),
    ("covered_statements", 211), ("covered_statements", -1),
    ("eligible_branches", 0), ("eligible_branches", "42"),
    ("covered_branches", 43), ("covered_branches", float("nan")),
])
def test_coverage_invalid_denominators_rejected(field, value):
    p = snapshot()
    p["observations"][1]["coverage"][field] = value
    with pytest.raises(ValueError):
        t.run(p)


@pytest.mark.parametrize("field,value", [
    ("source_content_sha256", "x" * 64),
    ("scope_sha256", None), ("config_sha256", "b" * 63),
    ("tool_version", " "),
])
def test_invalid_coverage_provenance_rejected(field, value):
    p = snapshot()
    p["observations"][2]["coverage"][field] = value
    with pytest.raises(ValueError):
        t.run(p)


@pytest.mark.parametrize("field,new", [
    ("scope_sha256", "f" * 64),
    ("config_sha256", "f" * 64),
    ("source_content_sha256", "f" * 64),
    ("tool_version", "coverage.py changed"),
    ("eligible_statements", 211),
    ("eligible_branches", 43),
])
def test_valid_but_unmatched_coverage_must_not_claim_stability(field, new):
    p = snapshot()
    p["observations"][2]["coverage"][field] = new
    d = t.run(p)
    assert d["trajectory"]["state"] == "INSUFFICIENT_MATCHED_COVERAGE_PAIRS"
    assert d["trajectory"]["certified_convergence"] is False
    assert d["trajectory"]["matched_pairs"] < 3


@pytest.mark.parametrize("mutation", [
    lambda p: p["observations"].pop(),
    lambda p: p["observations"][1].update(wave="W9"),
    lambda p: p["observations"][1].update(head_sha="x" * 40),
    lambda p: p["observations"][1].update(observed_at="2026-02-30T12:00:00Z"),
    lambda p: p["observations"][1].update(observed_at="2026-10-17T09:00:00Z"),
    lambda p: p["observations"][2]["authority"].update(admission="PASS"),
    lambda p: p["observations"][1]["tests"].update(passed=500),
    lambda p: p["observations"][0]["historical_backlog"].update(formal_roots_closed=3),
])
def test_identity_governance_and_test_totals_fail_closed(mutation):
    p = snapshot()
    mutation(p)
    with pytest.raises(ValueError):
        t.run(p)


@pytest.mark.parametrize("field,value", [
    ("basis", "RUN_CREATED_TO_START"),
    ("host_sha256", "x" * 64),
    ("workload_sha256", "a" * 63),
    ("duration_ms", [1.0, 2.0]),
    ("duration_ms", [1.0, 2.0, math.inf]),
    ("duration_ms", [True, 1.0, 2.0]),
])
def test_clock_proof_rejects_false_native_queue_or_bad_samples(field, value):
    p = snapshot()
    p["observations"][2]["clock"][field] = value
    with pytest.raises(ValueError):
        t.run(p)


def test_clock_workload_change_prevents_claim_of_acceleration():
    p = snapshot()
    p["observations"][2]["clock"]["workload_sha256"] = "f" * 64
    result = t.run(p)
    assert not result["clock_pairs"][1]["qualified"]
    assert result["clock_pairs"][1]["median_wall_delta_ms"] is None
    assert result["github_runner_speedup_seconds"] is None


def test_missing_clock_is_unknown_not_zero():
    p = snapshot()
    p["observations"][0]["clock"] = None
    result = t.run(p)
    assert result["clock_pairs"][0]["median_wall_delta_ms"] is None
    assert result["observations"][0]["local_clock_p50_ms"] is None


def test_prior_issued_score_requires_matching_source_and_native_free():
    p = snapshot()
    p["forecasts"] = [{"issued_wave": "N5", "target_wave": "W7",
                       "issued_at": "2026-10-17T10:01:00Z",
                       "issued_head_sha": "a" * 40,
                       "predicted_branch_pct": 99.0}]
    result = t.run(p)
    assert result["forecasts"][0]["actual"] == 100.0
    assert result["forecast_mae_pp"] == 1.0
    assert not result["forecasts"][0]["admissible_as_independent_forecast"]


@pytest.mark.parametrize("change", [
    lambda f: f.update(issued_head_sha="0" * 40),
    lambda f: f.update(issued_at="2026-10-17T09:59:00Z"),
    lambda f: f.update(issued_at="2026-10-17T11:00:00Z"),
    lambda f: f.update(predicted_branch_pct=102),
    lambda f: f.update(predicted_branch_pct=True),
])
def test_forecast_rejects_leakage_and_forged_projection(change):
    p = snapshot()
    f = {"issued_wave": "N5", "target_wave": "W7",
         "issued_at": "2026-10-17T10:01:00Z",
         "issued_head_sha": "a" * 40, "predicted_branch_pct": 99.0}
    change(f)
    p["forecasts"] = [f]
    with pytest.raises(ValueError):
        t.run(p)


def test_unobserved_next_wave_forecast_has_no_scored_actual():
    p = snapshot()
    p["forecasts"] = [{"issued_wave": "W9", "target_wave": "W10",
                       "issued_at": "2026-10-17T13:00:01Z",
                       "issued_head_sha": "d" * 40,
                       "predicted_branch_pct": 100.0}]
    result = t.run(p)
    assert result["forecasts"][0]["actual"] is None
    assert result["forecast_mae_pp"] is None


def test_forecast_on_unequal_source_sha_must_not_get_scored_actual():
    p = snapshot()
    p["observations"][1]["coverage"]["source_content_sha256"] = "f" * 64
    p["forecasts"] = [{"issued_wave": "N5", "target_wave": "W7",
                       "issued_at": "2026-10-17T10:01:00Z",
                       "issued_head_sha": "a" * 40,
                       "predicted_branch_pct": 99.0}]
    result = t.run(p)
    assert result["forecast_mae_pp"] is None


def test_duplicate_forecasts_not_independent_trials():
    p = snapshot()
    f = {"issued_wave": "N5", "target_wave": "W7",
         "issued_at": "2026-10-17T10:01:00Z",
         "issued_head_sha": "a" * 40, "predicted_branch_pct": 99.0}
    p["forecasts"] = [f, copy.deepcopy(f)]
    with pytest.raises(ValueError, match="duplicate immutable forecast"):
        t.run(p)


def test_timestamp_preserves_date_calendar_and_utc():
    stamp = t.timestamp("2026-10-17T10:11:12Z")
    assert stamp == datetime(2026, 10, 17, 10, 11, 12, tzinfo=timezone.utc)


def test_hash_rejected_if_not_exact_lowercase():
    with pytest.raises(ValueError):
        t.hex_digest("A" * 64, t.HEX64, "digest")


def test_mixed_non_plateau_deltas_are_classified_changing_not_converged():
    pairs = [{"qualified": True, "statement_delta_pp": 0.1,
              "branch_delta_pp": step} for step in (0.8, 0.1, 0.7)]
    result = t.classify(pairs)
    assert result["state"] == "CHANGING_OR_UNQUALIFIED_STABILITY"
    assert result["branch_second_difference_pp"] == [-0.7, 0.6]
    assert result["certified_convergence"] is False
