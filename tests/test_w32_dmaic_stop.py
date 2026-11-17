"""W32 DMAIC adaptive N-1/N/N+1 stop rule, 3.4 DPMO bound and negatives."""

import copy
import math

import pytest

from tools.recovery import w32_dmaic_stop as d

SHA = "a" * 40
SOURCE = "b" * 64


def wave(n, **overrides):
    row = {
        "wave_id": "W" + str(n),
        "head_sha": ("%040x" % n),
        "source_sha256": SOURCE,
        "scope_id": "production.module.A",
        "covered": 80,
        "eligible": 100,
        "open_root_ids": [],
        "unknown_roots": 0,
        "terminal_jobs": 6,
        "successful_jobs": 6,
        "pending_jobs": 0,
        "receipt_verified": True,
        "queue_p95_seconds": 120,
        "quality_defects": None,
        "quality_opportunities": None,
        "cohort_id": None,
        "cohort_verified": False,
    }
    row.update(overrides)
    return row


def decision(rows):
    return d.decide({"waves": rows})


def test_initial_single_verified_wave_can_expand_bounded():
    out = decision([wave(1)])
    assert out["decision"] == "EXPAND_BOUNDED_DISJOINT_SLICE"
    assert out["max_next_native_cells"] == 6
    assert out["merge_admission"] == "HOLD"


def test_empty_ledger_is_unknown_not_stable():
    out = decision([])
    assert out["decision"] == "HOLD_NO_DATA"
    assert out["quality_bound"]["opportunities"] is None


def test_no_workflow_proof_is_hold_not_success():
    out = decision([wave(1, terminal_jobs=0, successful_jobs=0)])
    assert out["decision"] == "HOLD_NATIVE_PROOF_MISSING"


def test_new_queued_fanout_blocks_further_expansion():
    out = decision([wave(1), wave(2, pending_jobs=3)])
    assert out["decision"] == "HOLD_QUEUE_SATURATED"
    assert out["max_next_native_cells"] == 0


def test_unclassified_first_red_denies_stable_credit():
    out = decision([wave(1), wave(2, unknown_roots=1)])
    assert out["decision"] == "HOLD_UNCLASSIFIED_FIRST_RED"


def test_changed_source_denominator_is_not_fake_uplift():
    out = decision([wave(1), wave(2, eligible=115, covered=95)])
    assert out["decision"] == "RESET_UNMATCHED_COVERAGE_SCOPE"
    assert out["matched_coverage_delta"] is None


def test_changed_source_hash_denies_comparable_uplift():
    out = decision([wave(1), wave(2, source_sha256="c" * 64)])
    assert out["decision"] == "RESET_UNMATCHED_COVERAGE_SCOPE"


def test_real_same_scope_coverage_regression_stops_growth():
    out = decision([wave(1, covered=95), wave(2, covered=90)])
    assert out["decision"] == "STOP_COVERAGE_REGRESSION"
    assert out["matched_coverage_delta"] == -5


def test_unresolved_existing_root_must_be_repaired_not_multiplied():
    out = decision([wave(1, open_root_ids=["MATPLOTLIB"])])
    assert out["decision"] == "REPAIR_EXISTING_ROOTS_FIRST"
    assert out["max_next_native_cells"] == 0


def test_queue_pressure_is_capacity_hold():
    out = decision([wave(1, queue_p95_seconds=1600)])
    assert out["decision"] == "HOLD_QUEUE_PRESSURE"


def test_missing_duration_cannot_be_zero():
    out = decision([wave(1, queue_p95_seconds=None)])
    assert out["decision"] == "HOLD_LATENCY_UNKNOWN"


def test_three_equal_transitions_stops_local_branch_but_not_six_sigma():
    out = decision([wave(i) for i in range(1, 5)])
    assert out["consecutive_zero_value_transitions"] == 3
    assert out["decision"] == "STOP_LOCAL_PLATEAU"
    assert out["observed_local_plateau"] is True
    assert out["dmaic_stable_and_six_sigma_certified"] is False


def test_two_equal_transitions_not_enough_for_stability():
    out = decision([wave(i) for i in range(1, 4)])
    assert out["consecutive_zero_value_transitions"] == 2
    assert out["decision"] != "STOP_LOCAL_PLATEAU"


def test_shifted_p95_breaks_stability_streak():
    waves = [wave(i) for i in range(1, 5)]
    waves[-1]["queue_p95_seconds"] = 150
    out = decision(waves)
    assert out["consecutive_zero_value_transitions"] == 0
    assert out["observed_local_plateau"] is False


def test_pending_historical_wave_breaks_plateau_window():
    waves = [wave(i) for i in range(1, 5)]
    waves[1]["pending_jobs"] = 2
    assert decision(waves)["consecutive_zero_value_transitions"] == 1


def test_no_independent_defect_population_is_unknown():
    out = decision([wave(1)])
    assert out["quality_bound"]["opportunities"] is None
    assert out["quality_bound"]["formal_six_sigma_certification"] is False


def test_zero_defects_100_trials_not_six_sigma():
    out = decision(
        [
            wave(
                1,
                quality_defects=0,
                quality_opportunities=100,
                cohort_id="unique-1",
                cohort_verified=True,
            )
        ]
    )
    assert out["quality_bound"]["one_sided_95_upper_dpmo_zero_only"] > 10000
    assert out["quality_bound"]["reported_cohort_3_4_dpmo_target_met"] is False


def test_exact_binomial_required_denominator_conservative():
    n = d.min_zero_defect_trials()
    assert d.zero_defect_upper_dpmo(n) <= 3.4
    assert d.zero_defect_upper_dpmo(n - 1) > 3.4


def test_multiple_disjoint_large_cohorts_only_yield_candidate_not_certification():
    waves = [
        wave(
            i,
            quality_defects=0,
            quality_opportunities=220300,
            cohort_id="cohort-" + str(i),
            cohort_verified=True,
        )
        for i in range(1, 6)
    ]
    quality = decision(waves)["quality_bound"]
    assert quality["reported_cohort_3_4_dpmo_target_met"] is True
    assert quality["formal_six_sigma_certification"] is False
    assert quality["independent_sampling_externally_attested"] is None


def test_repeated_cohort_not_double_counted():
    waves = [
        wave(
            1,
            cohort_id="C",
            cohort_verified=True,
            quality_defects=0,
            quality_opportunities=100,
        ),
        wave(
            2,
            cohort_id="C",
            cohort_verified=True,
            quality_defects=0,
            quality_opportunities=100,
        ),
    ]
    with pytest.raises(ValueError, match="duplicate quality cohort"):
        decision(waves)


def test_any_defect_blocks_zero_defect_bound_qualification():
    data = [
        wave(
            i,
            quality_defects=0,
            quality_opportunities=200000,
            cohort_id=str(i),
            cohort_verified=True,
        )
        for i in range(1, 6)
    ]
    data[3]["quality_defects"] = 1
    quality = decision(data)["quality_bound"]
    assert quality["one_sided_95_upper_dpmo_zero_only"] is None
    assert quality["reported_cohort_3_4_dpmo_target_met"] is False


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("covered", 101, "coverage denominator"),
        ("eligible", 0, "coverage denominator"),
        ("unknown_roots", -1, "invalid unknown"),
        ("terminal_jobs", True, "invalid terminal"),
        ("successful_jobs", 7, "native successes"),
        ("head_sha", "bad", "invalid head"),
        ("source_sha256", "bad", "invalid source"),
        ("scope_id", "", "invalid scope"),
        ("open_root_ids", None, "root inventory"),
        ("receipt_verified", None, "receipt status"),
        ("quality_defects", 3, "quality opportunities"),
        ("queue_p95_seconds", math.inf, "queue p95"),
    ],
)
def test_bad_input_fails_closed(field, value, reason):
    with pytest.raises(ValueError, match=reason):
        decision([wave(1, **{field: value})])


def test_wave_identity_not_replayable():
    duplicate = copy.deepcopy(wave(1))
    with pytest.raises(ValueError, match="wave identity reused"):
        decision([wave(1), duplicate])
