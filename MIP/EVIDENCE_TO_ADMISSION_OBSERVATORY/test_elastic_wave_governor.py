"""W33 elastic governor: bounded scale, local stop, idempotent re-entry.

Synthetic test pulses are controller oracles, NOT GitHub-native evidence.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import elastic_wave_governor as g  # noqa: E402

HEAD = "a" * 40


def pulse(n, covered, *, family="W82", eligible=215):
    return {
        "wave": n, "run_id": 800000 + n + (1 if family == "W81" else 0),
        "source_sha": f"{1000+n+(1 if family == 'W81' else 0):040x}",
        "artifact_sha256": f"{90000+n+(1 if family == 'W81' else 0):064x}",
        "source_slice": f"{family}-independent-attack-{n}",
        "covered": covered, "eligible": eligible,
        "cohort_id": f"{family}-stable-fixed-source-opportunities",
        "configuration_id": f"{family}-matched-branch-coverage-config",
        "terminal": True, "native_receipts_valid": True,
        "attempted_new_behavior": True, "failed_tests": 0,
    }


def specimen():
    families = [
        ("W75", "tools/w75_stability_diagnostic.py", 221, 219),
        ("W64", "tools/w64_census_reverse_pressure_v2.py", 125, 123),
        ("W81", "tools/w81_repair_outcome_block.py", 162, 154),
        ("W82", "tools/w82_semantic_diversity_diagnostic.py", 215, 164),
    ]
    return {
        "schema": "codepurple.elastic_wave_input.v1",
        "repository": "GBOGEB/ABACUS", "snapshot_source_sha": HEAD,
        "families": [
            {"id": f, "paths": [p], "eligible": e, "covered": c,
             "target_percent": 95.0, "first_reds": [],
             "source_sha": HEAD, "native_observed": True, "history": []}
            for f, p, e, c in families
        ],
        "capacity": {
            "queue_population_complete": True, "queue_p95_seconds": 150.0,
            "head_stable": True,
            "queue_population_run_id": 90000,
            "queue_population_source_sha": HEAD,
            "queue_soft_seconds": 600, "queue_hard_seconds": 900,
            "evidence_yield": 1.0, "previous_observation_lanes": 1,
            "maximum_observation_lanes": 8, "available_runner_slots": 8,
            "ready_disjoint_source_leases": 4, "source_owner_slots": 2,
            "outstanding_native_jobs": 0, "latest_terminal_run_id": 90000,
            "latest_terminal_source_sha": HEAD,
            "last_scaled_run_id": None, "last_scaled_source_sha": None,
        },
        "events": [], "seen_event_keys": [],
        "global_acceptance": {
            "head_stable": None, "canonical_b0_exact_head": False,
            "accepted_roots_remaining": None, "repositories": 3,
            "source_attested_repositories": None, "required_artifacts": 12,
            "valid_artifacts": None, "independent_stable_pulses": None,
            "no_special_cause_variation": False,
            "gates": {
                "branch_protection": False, "eligible_independent_review": False,
                "required_checks": False, "negative_red_canary": False,
                "security": False,
            },
        },
    }


def family(doc, family_id="W82"):
    return next(f for f in doc["families"] if f["id"] == family_id)


def test_actual_four_module_source_frontier_is_arithmetic_not_main_credit():
    r = g.evaluate(specimen())
    assert {f["id"]: (f["covered"], f["eligible"]) for f in r["families"]} == {
        "W75": (219, 221), "W64": (123, 125),
        "W81": (154, 162), "W82": (164, 215),
    }
    assert sum(f["covered"] for f in r["families"]) == 660
    assert sum(f["eligible"] for f in r["families"]) == 723
    assert r["next_pilot"] == "W82"
    assert family_result(r, "W82")["covered_opportunities_needed_for_target"] == 41
    assert family_result(r, "W82")["covered_percent"] == pytest.approx(76.27907, abs=1e-5)
    assert r["governed_merge_admission"] == "HOLD"
    assert r["formal_acceptance_claim"] is False


def family_result(result, ident):
    return next(f for f in result["families"] if f["id"] == ident)


@pytest.mark.parametrize("id", ["W75", "W64", "W81"])
def test_stop_achieved_local_target_without_stopping_global(id):
    r = g.evaluate(specimen())
    assert family_result(r, id)["state"] == "LOCAL_COVERAGE_TARGET"
    assert family_result(r, id)["stop_local_coverage"] is True
    assert r["programme"]["stop_entire_program"] is False


def test_incomplete_queue_downscales_to_one_read_only_and_zero_runners():
    doc = specimen()
    doc["capacity"]["queue_population_complete"] = False
    doc["capacity"]["queue_p95_seconds"] = None
    r = g.evaluate(doc)
    assert r["capacity"]["state"] == "OBSERVE_ONLY"
    assert r["capacity"]["recommended_read_only_observation_lanes"] == 1
    assert r["capacity"]["proposed_native_runner_lanes"] == 0


@pytest.mark.parametrize("q,previous,expected,mode", [
    (905, 8, 4, "THROTTLE"), (1200, 4, 2, "THROTTLE"),
    (800, 4, 4, "HOLD_CAPACITY"), (601, 2, 2, "HOLD_CAPACITY"),
])
def test_queue_pressure_decelerates_without_claiming_stability(q, previous, expected, mode):
    doc = specimen()
    doc["capacity"]["queue_p95_seconds"] = q
    doc["capacity"]["previous_observation_lanes"] = previous
    r = g.evaluate(doc)
    assert r["capacity"]["state"] == mode
    assert r["capacity"]["recommended_read_only_observation_lanes"] == expected


def test_artifact_yield_less_than_one_forces_halving():
    doc = specimen()
    doc["capacity"]["evidence_yield"] = .99
    doc["capacity"]["previous_observation_lanes"] = 8
    r = g.evaluate(doc)
    assert r["capacity"]["state"] == "THROTTLE"
    assert r["capacity"]["recommended_read_only_observation_lanes"] == 4


def test_missing_capacity_never_invents_runner_slots():
    for key in ("available_runner_slots", "ready_disjoint_source_leases", "source_owner_slots"):
        doc = specimen()
        doc["capacity"][key] = None
        assert g.evaluate(doc)["capacity"]["proposed_native_runner_lanes"] == 0


def test_existing_jobs_block_additional_automatic_fanout():
    doc = specimen()
    doc["capacity"]["outstanding_native_jobs"] = 23
    assert g.evaluate(doc)["capacity"]["proposed_native_runner_lanes"] == 0


def test_three_independent_pulses_with_two_positive_deltas_double_lanes_once():
    doc = specimen()
    family(doc)["history"] = [pulse(1, 164), pulse(2, 170), pulse(3, 173)]
    doc["capacity"]["latest_terminal_run_id"] = 800003
    doc["capacity"]["latest_terminal_source_sha"] = family(doc)["history"][-1]["source_sha"]
    doc["capacity"]["queue_population_run_id"] = 800003
    doc["capacity"]["queue_population_source_sha"] = family(doc)["history"][-1]["source_sha"]
    r = g.evaluate(doc)
    assert r["capacity"]["state"] == "GEOMETRIC_SCALE"
    assert r["capacity"]["recommended_read_only_observation_lanes"] == 2
    assert r["capacity"]["proposed_native_runner_lanes"] == 1  # W82 only below target
    assert r["capacity"]["automatic_dispatch_permitted"] is False


def test_geometric_ramp_is_bounded_one_two_four_eight():
    observed = []
    for previous, expected in ((1, 2), (2, 4), (4, 8), (8, 8)):
        doc = specimen()
        family(doc)["history"] = [pulse(1, 164), pulse(2, 170), pulse(3, 173)]
        doc["capacity"]["previous_observation_lanes"] = previous
        doc["capacity"]["latest_terminal_run_id"] = 800003
        doc["capacity"]["latest_terminal_source_sha"] = family(doc)["history"][-1]["source_sha"]
        doc["capacity"]["queue_population_run_id"] = 800003
        doc["capacity"]["queue_population_source_sha"] = family(doc)["history"][-1]["source_sha"]
        observed.append(g.evaluate(doc)["capacity"]["recommended_read_only_observation_lanes"])
    assert observed == [2, 4, 8, 8]


def test_repeated_observation_cannot_double_capacity_again():
    doc = specimen()
    family(doc)["history"] = [pulse(1, 164), pulse(2, 170), pulse(3, 173)]
    doc["capacity"]["latest_terminal_run_id"] = 800003
    doc["capacity"]["latest_terminal_source_sha"] = family(doc)["history"][-1]["source_sha"]
    doc["capacity"]["queue_population_run_id"] = 800003
    doc["capacity"]["queue_population_source_sha"] = family(doc)["history"][-1]["source_sha"]
    doc["capacity"]["last_scaled_run_id"] = doc["capacity"]["latest_terminal_run_id"]
    doc["capacity"]["last_scaled_source_sha"] = doc["capacity"]["latest_terminal_source_sha"]
    r = g.evaluate(doc)
    assert r["capacity"]["state"] == "HOLD_CAPACITY"
    assert r["capacity"]["recommended_read_only_observation_lanes"] == 1


def test_source_owner_and_runner_capacity_remain_separate():
    doc = specimen()
    doc["capacity"]["available_runner_slots"] = 1
    doc["capacity"]["ready_disjoint_source_leases"] = 3
    doc["capacity"]["source_owner_slots"] = 2
    r = g.evaluate(doc)
    assert r["capacity"]["proposed_native_runner_lanes"] == 1
    assert r["capacity"]["proposed_source_owner_write_lanes"] == 1


def test_three_zero_delta_transitions_require_four_fresh_pulses():
    doc = specimen()
    for n in (1, 2, 3):
        family(doc)["history"] = [pulse(i, 164) for i in range(1, n+1)]
        result = g.evaluate(doc)
        assert family_result(result, "W82")["state"] != "LOCAL_PLATEAU_PIVOT"
    family(doc)["history"].append(pulse(4, 164))
    r = g.evaluate(doc)
    assert family_result(r, "W82")["state"] == "LOCAL_PLATEAU_PIVOT"
    assert family_result(r, "W82")["stop_local_coverage"]
    assert r["programme"]["stop_entire_program"] is False


def test_one_real_gain_resets_plateau_streak():
    doc = specimen()
    family(doc)["history"] = [pulse(1, 164), pulse(2, 164), pulse(3, 170), pulse(4, 170)]
    r = g.evaluate(doc)
    assert family_result(r, "W82")["pulse_evidence"]["zero_gain_transitions"] == 1
    assert family_result(r, "W82")["state"] == "EXPAND_BEHAVIORAL_TESTS"


@pytest.mark.parametrize("kind,value", [
    ("replay_source", None), ("replay_run", None), ("replay_artifact", None),
    ("replay_slice", None), ("gap_wave", None), ("mutated_cohort", None),
    ("mutated_config", None), ("mutated_denominator", None),
])
def test_forbid_false_plateau_from_replays_or_unmatched_cohorts(kind, value):
    doc = specimen()
    history = [pulse(1, 164), pulse(2, 164), pulse(3, 164), pulse(4, 164)]
    if kind == "replay_source": history[2]["source_sha"] = history[1]["source_sha"]
    elif kind == "replay_run": history[2]["run_id"] = history[1]["run_id"]
    elif kind == "replay_artifact": history[2]["artifact_sha256"] = history[1]["artifact_sha256"]
    elif kind == "replay_slice": history[2]["source_slice"] = history[1]["source_slice"]
    elif kind == "gap_wave": history[2]["wave"] = 5
    elif kind == "mutated_cohort": history[2]["cohort_id"] = "other"
    elif kind == "mutated_config": history[2]["configuration_id"] = "other"
    else: history[2]["eligible"] = 216
    family(doc)["history"] = history
    if kind.startswith("mutated"):
        r = g.evaluate(doc)
        assert family_result(r, "W82")["state"] == "REBASELINE"
    else:
        with pytest.raises(g.GovernorError):
            g.evaluate(doc)


@pytest.mark.parametrize("key,value", [
    ("terminal", False), ("native_receipts_valid", None),
    ("attempted_new_behavior", False), ("failed_tests", 1),
])
def test_nonterminal_or_failed_pulse_is_not_silent_zero_change(key, value):
    doc = specimen()
    p = pulse(1, 164)
    p[key] = value
    family(doc)["history"] = [p]
    r = g.evaluate(doc)
    assert family_result(r, "W82")["state"] == "REPAIR_NATIVE_RECEIPTS"


def event(kind, *, identity=HEAD, fingerprint="root-evidence-v1", delta=None):
    return {"kind": kind, "family": "W75", "source_sha": identity,
            "fingerprint": fingerprint, "terminal_exact_head_evidence": True,
            "verified_opportunity_delta": delta}


def test_critical_first_red_reopens_local_control_with_small_pilot_only():
    doc = specimen()
    doc["events"] = [event("CRITICAL_FIRST_RED")]
    r = g.evaluate(doc)
    assert family_result(r, "W75")["state"] == "LOCAL_RETRIGGER_PILOT"
    assert not family_result(r, "W75")["stop_local_coverage"]
    assert r["retrigger"]["actionable"][0]["reopens_local_coverage"] is True
    assert r["capacity"]["automatic_dispatch_permitted"] is False


def test_replayed_trigger_key_or_duplicate_in_one_batch_never_restarts_work():
    doc = specimen()
    doc["events"] = [event("CRITICAL_FIRST_RED"), event("CRITICAL_FIRST_RED")]
    r = g.evaluate(doc)
    assert len(r["retrigger"]["actionable"]) == 1
    assert len(r["retrigger"]["duplicate_suppressed"]) == 1
    doc["seen_event_keys"] = [r["retrigger"]["actionable"][0]["key"]]
    r2 = g.evaluate(doc)
    assert len(r2["retrigger"]["actionable"]) == 0
    assert len(r2["retrigger"]["duplicate_suppressed"]) == 2
    assert family_result(r2, "W75")["state"] == "LOCAL_COVERAGE_TARGET"


@pytest.mark.parametrize("kind,delta", [
    ("NEW_ELIGIBLE_FRONTIER", None), ("NEW_ELIGIBLE_FRONTIER", 0),
    ("COVERAGE_REGRESSION", 1),
])
def test_new_scope_or_regression_needs_signed_measured_delta(kind, delta):
    doc = specimen()
    doc["events"] = [event(kind, delta=delta)]
    r = g.evaluate(doc)
    assert r["retrigger"]["actionable"] == []
    assert r["retrigger"]["withheld"][0]["reason"] == "MISSING_SIGNED_MATCHED_EVIDENCE"


def test_new_eligible_source_reopens_but_capacity_is_not_unbounded():
    doc = specimen()
    doc["events"] = [event("NEW_ELIGIBLE_FRONTIER", delta=5)]
    r = g.evaluate(doc)
    assert family_result(r, "W75")["state"] == "LOCAL_RETRIGGER_PILOT"
    assert r["capacity"]["proposed_native_runner_lanes"] <= 2


def test_queue_recovery_is_one_pilot_not_full_geometric_restart():
    doc = specimen()
    doc["events"] = [event("QUEUE_RECOVERED")]
    r = g.evaluate(doc)
    assert r["capacity"]["proposed_native_runner_lanes"] <= 1
    assert family_result(r, "W75")["stop_local_coverage"]


def test_stale_nonterminal_event_cannot_reopen_closed_family():
    doc = specimen()
    e = event("CRITICAL_FIRST_RED")
    e["terminal_exact_head_evidence"] = False
    doc["events"] = [e]
    r = g.evaluate(doc)
    assert family_result(r, "W75")["state"] == "LOCAL_COVERAGE_TARGET"
    assert len(r["retrigger"]["withheld"]) == 1


def test_existing_first_red_overrides_fresh_coverage_target():
    doc = specimen()
    family(doc, "W81")["first_reds"] = ["provenance.unsafe"]
    r = g.evaluate(doc)
    assert family_result(r, "W81")["state"] == "FIRST_RED_REPAIR"


def make_global_ready(doc):
    for f in doc["families"]:
        f["covered"] = f["eligible"]
    e = doc["global_acceptance"]
    e.update({"accepted_roots_remaining": 0, "source_attested_repositories": 3,
              "valid_artifacts": 12, "independent_stable_pulses": 8,
              "no_special_cause_variation": True,
              "head_stable": True, "canonical_b0_exact_head": True})
    e["gates"] = dict.fromkeys(e["gates"], True)


def test_only_all_families_and_independent_governance_allow_global_control():
    doc = specimen()
    make_global_ready(doc)
    r = g.evaluate(doc)
    assert r["programme"]["state"] == "GLOBAL_CONTROL_ELIGIBLE"
    assert r["programme"]["stop_entire_program"] is True
    assert r["capacity"]["proposed_native_runner_lanes"] == 0
    assert r["programme"]["is_six_sigma_capability_proof"] is False
    assert r["governed_merge_admission"] == "HOLD"


@pytest.mark.parametrize("corruption", [
    "family", "root", "repo", "artifact", "stability", "branch_protection",
    "eligible_independent_review", "required_checks", "negative_red_canary", "security",
    "canonical_b0_exact_head", "head_stable",
])
def test_no_global_stop_on_partial_target_or_missing_proof(corruption):
    doc = specimen()
    make_global_ready(doc)
    e = doc["global_acceptance"]
    if corruption == "family":
        family(doc)["covered"] = 164
    elif corruption == "root":
        e["accepted_roots_remaining"] = None
    elif corruption == "repo":
        e["source_attested_repositories"] = 2
    elif corruption == "artifact":
        e["valid_artifacts"] = 11
    elif corruption == "stability":
        e["independent_stable_pulses"] = 7
    elif corruption in {"canonical_b0_exact_head", "head_stable"}:
        e[corruption] = False
    else:
        e["gates"][corruption] = False
    assert g.evaluate(doc)["programme"]["stop_entire_program"] is False


@pytest.mark.parametrize("defect", [
    "overlapping_paths", "duplicate_families", "mixed_sha", "negative_covered",
    "covered_above_eligible", "zero_eligible", "target_zero", "target_above_100",
    "bad_queue_p95", "bad_evidence_yield", "head_short", "bad_capacity",
])
def test_invalid_input_rejects_instead_of_silently_scaling(defect):
    doc = specimen()
    if defect == "overlapping_paths":
        family(doc, "W81")["paths"] = family(doc, "W82")["paths"]
    elif defect == "duplicate_families":
        family(doc, "W81")["id"] = "W82"
    elif defect == "mixed_sha":
        family(doc, "W82")["source_sha"] = "b" * 40
    elif defect == "negative_covered":
        family(doc, "W82")["covered"] = -1
    elif defect == "covered_above_eligible":
        family(doc, "W82")["covered"] = 216
    elif defect == "zero_eligible":
        family(doc, "W82")["eligible"] = 0
    elif defect == "target_zero":
        family(doc, "W82")["target_percent"] = 0
    elif defect == "target_above_100":
        family(doc, "W82")["target_percent"] = 101
    elif defect == "bad_queue_p95":
        doc["capacity"]["queue_p95_seconds"] = float("nan")
    elif defect == "bad_evidence_yield":
        doc["capacity"]["evidence_yield"] = 1.1
    elif defect == "head_short":
        doc["snapshot_source_sha"] = "short"
    else:
        doc["capacity"]["previous_observation_lanes"] = 9
    with pytest.raises(g.GovernorError):
        g.evaluate(doc)


def test_governed_execution_remains_manual_even_when_pilot_recommended():
    r = g.evaluate(specimen())
    assert r["capacity"]["automatic_dispatch_permitted"] is False
    assert r["capacity"]["automated_merge_permitted"] is False
    assert r["programme"]["no_automatic_authority_transfer"] is True
    assert r["explicit_stop_scope"] == "LOCAL_ONLY_OR_NONE"
    assert r["control_method"] == "AIMD_WITH_HYSTERESIS_AND_IDEMPOTENT_RETRIGGERS"


def test_stale_queue_run_identity_blocks_scaling_even_with_green_history():
    doc = specimen()
    family(doc)["history"] = [pulse(1, 164), pulse(2, 168), pulse(3, 172)]
    doc["capacity"]["latest_terminal_run_id"] = 800003
    doc["capacity"]["latest_terminal_source_sha"] = family(doc)["history"][-1]["source_sha"]
    # The queue sample remains for a different run/SHA: no scaling credit.
    result = g.evaluate(doc)
    assert result["capacity"]["state"] == "OBSERVE_ONLY"
    assert result["capacity"]["proposed_native_runner_lanes"] == 0
    assert result["capacity"]["queue_bound_to_latest_terminal_head"] is False


def test_unstable_head_cannot_scale_even_with_low_p95_and_complete_receipts():
    doc = specimen()
    doc["capacity"]["head_stable"] = False
    result = g.evaluate(doc)
    assert result["capacity"]["state"] == "OBSERVE_ONLY"
    assert result["capacity"]["proposed_native_runner_lanes"] == 0
    assert result["capacity"]["source_head_stable"] is False


def test_unrelated_terminal_run_does_not_double_source_specific_wave_budget():
    doc = specimen()
    family(doc)["history"] = [pulse(1, 164), pulse(2, 168), pulse(3, 172)]
    # Queue is exact for current run, but this was NOT the pulse with 2 gains.
    result = g.evaluate(doc)
    assert result["capacity"]["state"] == "HOLD_CAPACITY"
    assert result["capacity"]["recommended_read_only_observation_lanes"] == 1


def test_existing_observatory_consumer_exposes_pinned_policy_without_main_credit():
    import wave_metrics
    here = Path(__file__).resolve().parent
    snapshot = json.loads((here / "evidence.json").read_text(encoding="utf-8"))
    history = json.loads((here / "wave_history.json").read_text(encoding="utf-8"))
    receipt = wave_metrics.build_wave_receipt(snapshot, history)
    elastic = receipt["elastic_controller"]
    assert elastic["measurement_freshness"] == (
        "HISTORICAL_FOCUSED_SOURCE_HEAD_NOT_EXACT_CURRENT_MAIN"
    )
    assert elastic["source_head_equals_current_main"] is False
    assert elastic["capacity"]["state"] == "OBSERVE_ONLY"
    assert elastic["capacity"]["recommended_read_only_observation_lanes"] == 1
    assert elastic["capacity"]["proposed_native_runner_lanes"] == 0
    assert elastic["next_pilot"] == "W82"
    assert elastic["programme"]["stop_entire_program"] is False
    assert receipt["scale_policy"]["merge_admission"] == "HOLD"
