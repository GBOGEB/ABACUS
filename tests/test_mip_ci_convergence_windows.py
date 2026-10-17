"""N-1/N/N+1 exact-source metric convergence negative and positive evidence.

Plateaus are *descriptive candidates*, never certified main coverage, root
closures, independence, inference or authorization.
"""
import math

import pytest

from tools.mip_ci_temporal_rollup import (
    INPUT_SCHEMA,
    OUTCOMES,
    coverage_convergence,
    rollup,
)

HASH = "d" * 64


def pair(lines, branches):
    return {
        "line_coverage_candidate_delta_pp": lines,
        "branch_coverage_candidate_delta_pp": branches,
    }


@pytest.mark.parametrize("series,length", [
    ([], 0),
    ([pair(0, 0)], 1),
    ([pair(0, 0), pair(0, 0)], 2),
])
def test_less_than_three_comparable_pulses_stays_unknown(series, length):
    result = coverage_convergence(series)
    assert result["state"] == "INSUFFICIENT_MATCHED_TRAILING_PAIRS"
    assert result["matched_trailing_pairs"] == length
    assert result["accepted_main_coverage_improvement"] is None


@pytest.mark.parametrize("series", [
    [pair(0, 0), pair(0, 0), pair(0, 0)],
    [pair(0.5, -0.5), pair(0.25, 0.1), pair(0, 0)],
])
def test_matched_trailing_three_pulses_descriptive_plateau_only(series):
    result = coverage_convergence(series)
    assert result["state"] == "DESCRIPTIVE_PLATEAU_CANDIDATE"
    assert result["required_consecutive_pairs"] == 3
    assert result["plateau_tolerance_pp"] == 0.5
    assert result["independent_trial_or_significance_certified"] is False
    assert result["merge_authorized"] is False


def test_significant_positive_change_is_not_mislabelled_stable():
    result = coverage_convergence([pair(2, 3), pair(2, 0), pair(1, 2)])
    assert result["state"] == "CHANGE_ABOVE_PLATEAU_TOLERANCE"
    assert result["line_deltas_pp"] == [2, 2, 1]


@pytest.mark.parametrize("index,dimension", [(0, "lines"), (1, "branches")])
def test_regression_in_either_dimension_blocks_plateau(index, dimension):
    series = [pair(0, 0) for _ in range(3)]
    series[index]["line_coverage_candidate_delta_pp" if dimension == "lines"
                  else "branch_coverage_candidate_delta_pp"] = -0.51
    result = coverage_convergence(series)
    assert result["state"] == "REGRESSION_OBSERVED"


def test_comparability_gap_resets_trailing_window():
    series = [pair(0, 0), pair(0, 0),
              pair(None, 0), pair(0, 0), pair(0, 0)]
    result = coverage_convergence(series)
    assert result["matched_trailing_pairs"] == 2
    assert result["state"] == "INSUFFICIENT_MATCHED_TRAILING_PAIRS"


def test_only_last_three_matched_pairs_define_current_state():
    series = [pair(-10, -10), pair(0, 0), pair(0, 0), pair(0, 0)]
    result = coverage_convergence(series)
    assert result["state"] == "DESCRIPTIVE_PLATEAU_CANDIDATE"
    assert result["matched_trailing_pairs"] == 3


@pytest.mark.parametrize("value", [True, "1", float("nan"), math.inf, -math.inf])
def test_nonfinite_or_forged_coverage_comparison_fails_closed(value):
    with pytest.raises(ValueError):
        coverage_convergence([pair(0, 0), pair(0, 0), pair(value, 0)])


def test_malformed_comparison_fails_closed():
    with pytest.raises(ValueError):
        coverage_convergence([pair(0, 0), "untrusted"])


def make_wave(n, *, lines=80, branches=30):
    sha = (chr(96 + n)) * 40
    outcomes = {name: 0 for name in OUTCOMES}
    outcomes["success"] = 20
    return {
        "wave": n,
        "source_sha": sha,
        "observed_at": f"2026-10-{n + 10:02d}T12:00:00Z",
        "run_attempts": [[n * 100 + i, 1] for i in range(20)],
        "telemetry": {
            "schema": "abacus.mip.ci-wave-telemetry.v2",
            "repository": "GBOGEB/ABACUS",
            "source_sha": sha,
            "workflow_records_observed": 20,
            "workflow_terminal_by_outcome": outcomes,
            "workflow_nonterminal": 0,
            "workflow_unclassified": 0,
            "jobs_observed": 0,
            "queue_samples": 0,
            "queue_seconds_p95": None,
            "queue_basis": "job.created_at -> job.started_at",
            "queue_source_counts": {
                "job_created_at": 0,
                "workflow_run_created_at_fallback": 0,
            },
            "merge_authorized": False,
            "independent_gates": {"admission": "HOLD"},
        },
        "coverage": {
            "source_sha": sha,
            "scope_sha256": HASH,
            "config_sha256": HASH,
            "artifact_sha256": HASH,
            "tool_version": "coverage.py pinned",
            "covered_lines": lines,
            "eligible_lines": 100,
            "covered_branches": branches,
            "eligible_branches": 40,
        },
    }


def test_temporal_rollup_emits_three_pair_plateau_without_promotion():
    payload = {
        "schema": INPUT_SCHEMA,
        "repository": "GBOGEB/ABACUS",
        "cohort": {
            "workflow_set_sha256": HASH,
            "test_selection_sha256": HASH,
            "runner_matrix_sha256": HASH,
        },
        "observations": [make_wave(n) for n in range(1, 5)],
        "forecasts": [],
    }
    result = rollup(payload)
    assert len(result["comparisons"]) == 3
    assert result["coverage_convergence"]["state"] == "DESCRIPTIVE_PLATEAU_CANDIDATE"
    assert result["admission"] == "HOLD"
    assert result["accepted_bd_root_closures"] is None
    assert all(c["accepted_main_coverage_delta_pp"] is None
               for c in result["comparisons"])


def test_temporal_rollup_rejects_scope_change_in_last_pair():
    payload = {
        "schema": INPUT_SCHEMA,
        "repository": "GBOGEB/ABACUS",
        "cohort": {
            "workflow_set_sha256": HASH,
            "test_selection_sha256": HASH,
            "runner_matrix_sha256": HASH,
        },
        "observations": [make_wave(n) for n in range(1, 5)],
        "forecasts": [],
    }
    payload["observations"][-1]["coverage"]["scope_sha256"] = "e" * 64
    result = rollup(payload)
    state = result["coverage_convergence"]
    assert state["state"] == "INSUFFICIENT_MATCHED_TRAILING_PAIRS"
    assert state["matched_trailing_pairs"] == 0
    assert result["comparisons"][-1]["line_coverage_candidate_delta_pp"] is None
