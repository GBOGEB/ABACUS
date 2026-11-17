"""Lane A wave 8: MIP/EVIDENCE_TO_ADMISSION_OBSERVATORY/elastic_wave_governor.py."""

import copy
import json

import pytest

from tests.coverage_waves.lane_a._load import load

eg = load("MIP/EVIDENCE_TO_ADMISSION_OBSERVATORY/elastic_wave_governor.py")

HEAD = "a" * 40
OTHER = "b" * 40
GE = eg.GovernorError


def _pulse(wave, covered, eligible=100, **over):
    pulse = {
        "wave": wave,
        "run_id": 1000 + wave,
        "source_sha": format(wave, "040x"),
        "artifact_sha256": format(wave, "064x"),
        "source_slice": "slice-%d" % wave,
        "covered": covered,
        "eligible": eligible,
        "terminal": True,
        "native_receipts_valid": True,
        "attempted_new_behavior": True,
        "failed_tests": 0,
        "cohort_id": "cohort",
        "configuration_id": "cfg",
    }
    pulse.update(over)
    return pulse


def _history(*covered):
    return [_pulse(i + 1, c) for i, c in enumerate(covered)]


def _family(fid="fam", paths=None, **over):
    fam = {
        "id": fid,
        "paths": paths or ["src/" + fid],
        "eligible": 100,
        "covered": 50,
        "target_percent": 90,
        "source_sha": HEAD,
        "first_reds": [],
        "native_observed": True,
        "history": [],
    }
    fam.update(over)
    return fam


def _capacity(**over):
    cap = {
        "previous_observation_lanes": 2,
        "maximum_observation_lanes": 8,
        "queue_soft_seconds": 100,
        "queue_hard_seconds": 200,
        "queue_p95_seconds": 50,
        "queue_population_complete": True,
        "evidence_yield": 1,
        "available_runner_slots": 4,
        "ready_disjoint_source_leases": 4,
        "source_owner_slots": 4,
        "outstanding_native_jobs": 0,
        "latest_terminal_run_id": 1003,
        "latest_terminal_source_sha": format(3, "040x"),
        "queue_population_run_id": 1003,
        "queue_population_source_sha": format(3, "040x"),
        "head_stable": True,
    }
    cap.update(over)
    return cap


def _acceptance(**over):
    end = {
        "accepted_roots_remaining": 0,
        "repositories": 2,
        "source_attested_repositories": 2,
        "required_artifacts": 3,
        "valid_artifacts": 3,
        "independent_stable_pulses": 8,
        "head_stable": True,
        "canonical_b0_exact_head": True,
        "no_special_cause_variation": True,
        "gates": {
            "branch_protection": True,
            "eligible_independent_review": True,
            "required_checks": True,
            "negative_red_canary": True,
            "security": True,
        },
    }
    end.update(over)
    return end


def _types(**over):
    row = {
        "kind": "report",
        "expected": 2,
        "native_verified": 2,
        "source_sha": HEAD,
        "consumer_attested": True,
    }
    row.update(over)
    return [row]


def _doc(families=None, **over):
    doc = {
        "schema": "codepurple.elastic_wave_input.v1",
        "repository": "GBOGEB/ABACUS",
        "snapshot_source_sha": HEAD,
        "families": families or [_family()],
        "capacity": _capacity(),
        "global_acceptance": _acceptance(),
        "artifact_types": _types(),
    }
    doc.update(over)
    return doc


# --- primitive validators -------------------------------------------------


def test_integer_sha_number():
    assert eg.integer(3, "x", 1) == 3
    for bad in (True, 1.0, -1, "1"):
        with pytest.raises(GE):
            eg.integer(bad, "x")
    assert eg.sha(HEAD, "s") == HEAD
    for bad in (None, "A" * 40, "a" * 39, "a" * 40 + "\n"):
        with pytest.raises(GE):
            eg.sha(bad, "s")
    assert eg.number(3, "n") == 3.0
    assert isinstance(eg.number(3, "n"), float)
    for bad in (True, "1", float("nan"), float("inf"), -0.5):
        with pytest.raises(GE):
            eg.number(bad, "n")
    with pytest.raises(GE, match="exceeds"):
        eg.number(5, "n", maximum=4)


@pytest.mark.parametrize(
    "value,ok",
    [
        ("src/pkg/mod.py", True),
        ("a", True),
        ("", False),
        (None, False),
        ("/abs/path", False),
        ("a\\b", False),
        ("C:/x", False),
        ("a/\tb", False),
        ("a/\x7fb", False),
        ("a//b", False),
        ("a/./b", False),
        ("a/../b", False),
        ("a/b.", False),
        ("a/b ", False),
    ],
)
def test_source_path_safe(value, ok):
    assert eg.source_path_safe(value) is ok


def test_source_path_overlap_is_segment_aware_and_casefolded():
    assert eg.source_path_overlap("src/a", "SRC/A")
    assert eg.source_path_overlap("src/a/b.py", "src/a")
    assert eg.source_path_overlap("src/a", "src/a/b.py")
    assert not eg.source_path_overlap("src/ab", "src/a")


# --- checked_history ------------------------------------------------------


def test_history_empty_and_type():
    out = eg.checked_history([])
    assert out["qualified"] is False
    assert out["reason"] == "NO_COMPLETED_SOURCE_CHANGING_PULSE"
    with pytest.raises(GE):
        eg.checked_history({})


@pytest.mark.parametrize(
    "over,match",
    [
        (dict(wave=0), "wave"),
        (dict(run_id=None), "run_id"),
        (dict(source_sha="x"), "source_sha"),
        (dict(artifact_sha256="short"), "artifact_sha256"),
        (dict(artifact_sha256=None), "artifact_sha256"),
        (dict(source_slice=""), "source_slice"),
        (dict(covered=-1), "covered"),
        (dict(eligible=0), "eligible"),
        (dict(covered=101), "exceeds"),
        (dict(cohort_id=""), "cohort_id"),
        (dict(configuration_id=None), "configuration_id"),
    ],
)
def test_history_pulse_validation(over, match):
    with pytest.raises(GE, match=match):
        pulse = _pulse(1, 10)
        pulse.update(over)
        eg.checked_history([pulse])


def test_history_non_dict_pulse():
    with pytest.raises(GE, match="object"):
        eg.checked_history(["p"])


@pytest.mark.parametrize(
    "over",
    [
        dict(terminal=False),
        dict(native_receipts_valid=None),
        dict(attempted_new_behavior=False),
        dict(failed_tests=1),
    ],
)
def test_history_incomplete_pulse(over):
    out = eg.checked_history([_pulse(1, 10, **over)])
    assert out == {
        "qualified": False,
        "reason": "INCOMPLETE_OR_FAILED_NATIVE_PULSE",
        "zero_gain_transitions": 0,
        "growth_transitions": 0,
    }


@pytest.mark.parametrize(
    "field", ["run_id", "source_sha", "source_slice", "artifact_sha256", "wave"]
)
def test_history_replay_rejected(field):
    hist = _history(10, 20)
    hist[1][field] = hist[0][field]
    with pytest.raises(GE, match="replayed"):
        eg.checked_history(hist)


def test_history_nonconsecutive_waves():
    hist = [_pulse(1, 10), _pulse(3, 20)]
    with pytest.raises(GE, match="consecutive"):
        eg.checked_history(hist)


@pytest.mark.parametrize(
    "over", [dict(cohort_id="c2"), dict(configuration_id="k2"), dict(eligible=200)]
)
def test_history_drift(over):
    hist = [_pulse(1, 10), _pulse(2, 20, **over)]
    out = eg.checked_history(hist)
    assert out["reason"] == "COHORT_OR_CONFIG_DRIFT"
    assert out["qualified"] is False


def test_history_counts_transitions():
    out = eg.checked_history(_history(10, 10, 10, 10))
    assert out["qualified"] is True
    assert out["zero_gain_transitions"] == 3
    assert out["growth_transitions"] == 0
    assert out["observations"] == 4
    assert out["last_run_id"] == 1004
    out = eg.checked_history(_history(10, 20, 30))
    assert out["growth_transitions"] == 2
    assert out["zero_gain_transitions"] == 0
    assert out["last_covered"] == 30
    assert out["last_eligible"] == 100
    # a regression resets both streaks
    out = eg.checked_history(_history(10, 20, 15))
    assert out["growth_transitions"] == 0
    assert out["zero_gain_transitions"] == 0


# --- family_result --------------------------------------------------------


@pytest.mark.parametrize(
    "over,match",
    [
        (dict(id=""), "family id"),
        (dict(paths=[]), "lease"),
        (dict(paths="src/x"), "lease"),
        (dict(paths=["/abs"]), "lease"),
        (dict(paths=["src/a", "SRC/A/b.py"]), "overlapping"),
        (dict(eligible=0), "eligible"),
        (dict(covered=101), "exceeds"),
        (dict(target_percent=0), "target_percent"),
        (dict(target_percent=101), "exceeds"),
        (dict(source_sha="bad"), "source_sha"),
        (dict(first_reds=None), "first_reds"),
        (dict(first_reds=[""]), "first_reds"),
    ],
)
def test_family_validation(over, match):
    fam = _family()
    fam.update(over)
    with pytest.raises(GE, match=match):
        eg.family_result(fam)


@pytest.mark.parametrize(
    "over,state,stop",
    [
        (dict(native_observed=False), "NATIVE_EVIDENCE_UNKNOWN", False),
        (dict(first_reds=["t::x"]), "FIRST_RED_REPAIR", False),
        (dict(covered=90), "LOCAL_COVERAGE_TARGET", True),
        (
            dict(history=_history(50, 50, 50, 50)),
            "LOCAL_PLATEAU_PIVOT",
            True,
        ),
        (
            dict(history=[_pulse(1, 10), _pulse(2, 20, cohort_id="z")]),
            "REBASELINE",
            False,
        ),
        (
            dict(history=[_pulse(1, 10, terminal=False)]),
            "REPAIR_NATIVE_RECEIPTS",
            False,
        ),
        (dict(), "EXPAND_BEHAVIORAL_TESTS", False),
    ],
)
def test_family_states(over, state, stop):
    out = eg.family_result(_family(**over))
    assert out["state"] == state
    assert out["stop_local_coverage"] is stop


def test_family_target_arithmetic():
    out = eg.family_result(_family(eligible=7, covered=3, target_percent=50))
    assert out["covered_percent"] == round(300 / 7, 6)
    assert out["uncovered"] == 4
    # ceil(3.5) - 3 = 1
    assert out["covered_opportunities_needed_for_target"] == 1
    out = eg.family_result(_family(eligible=7, covered=7, target_percent=50))
    assert out["covered_opportunities_needed_for_target"] == 0


# --- events ---------------------------------------------------------------


def _event(kind="CRITICAL_FIRST_RED", family="fam", **over):
    ev = {
        "kind": kind,
        "family": family,
        "source_sha": HEAD,
        "fingerprint": "fp",
        "terminal_exact_head_evidence": True,
    }
    ev.update(over)
    return ev


def test_events_container_validation():
    with pytest.raises(GE):
        eg._events({}, [], {"fam"})
    with pytest.raises(GE):
        eg._events([], "x", {"fam"})
    with pytest.raises(GE, match="seen_event_keys"):
        eg._events([], [1], {"fam"})
    with pytest.raises(GE, match="object"):
        eg._events(["e"], [], {"fam"})
    with pytest.raises(GE, match="event.source_sha"):
        eg._events([_event(source_sha="x")], [], {"fam"})


def test_events_classification():
    seen_key = "|".join(("fam", "CONTRACT_CHANGED", HEAD, "old"))
    events = [
        _event(kind="NOPE"),
        _event(family="ghost"),
        _event(fingerprint=""),
        _event(kind="CONTRACT_CHANGED", fingerprint="old"),
        _event(),
        _event(),
        _event(kind="NEW_ELIGIBLE_FRONTIER", verified_opportunity_delta=0),
        _event(kind="NEW_ELIGIBLE_FRONTIER", verified_opportunity_delta=True),
        _event(kind="COVERAGE_REGRESSION", verified_opportunity_delta=1),
        _event(
            kind="COVERAGE_REGRESSION",
            fingerprint="r",
            verified_opportunity_delta=-2,
        ),
        _event(
            kind="NEW_ELIGIBLE_FRONTIER",
            fingerprint="n",
            verified_opportunity_delta=3,
            terminal_exact_head_evidence=False,
        ),
        _event(kind="QUEUE_RECOVERED", fingerprint="q"),
    ]
    actionable, suppressed, withheld = eg._events(events, [seen_key], {"fam"})
    reasons = [w["reason"] for w in withheld]
    assert reasons == [
        "UNKNOWN_TRIGGER_KIND_OR_FAMILY",
        "UNKNOWN_TRIGGER_KIND_OR_FAMILY",
        "MISSING_CAUSAL_FINGERPRINT",
        "MISSING_SIGNED_MATCHED_EVIDENCE",
        "MISSING_SIGNED_MATCHED_EVIDENCE",
        "MISSING_SIGNED_MATCHED_EVIDENCE",
        "NOT_NATIVE_EXACT_HEAD_VERIFIED",
    ]
    assert [s["key"] for s in suppressed] == [
        seen_key,
        "|".join(("fam", "CRITICAL_FIRST_RED", HEAD, "fp")),
    ]
    kinds = [(a["kind"], a["reopens_local_coverage"]) for a in actionable]
    assert kinds == [
        ("CRITICAL_FIRST_RED", True),
        ("COVERAGE_REGRESSION", True),
        ("QUEUE_RECOVERED", False),
    ]


# --- artifact_type_census -------------------------------------------------


def test_artifact_census_unknown_and_validation():
    assert eg.artifact_type_census({})["status"] == "ARTIFACT_TYPE_POPULATION_UNKNOWN"
    base = {"snapshot_source_sha": HEAD}
    for rows, match in [
        ([], "nonempty"),
        ("x", "nonempty"),
        (["x"], "object"),
        (_types(kind=""), "distinct"),
        (_types() + _types(), "distinct"),
        (_types(expected=0), "expected"),
        (_types(native_verified=3), "exceeds"),
        (_types(source_sha=OTHER), "SHA mismatch"),
        (_types(consumer_attested="yes"), "boolean"),
    ]:
        with pytest.raises(GE, match=match):
            eg.artifact_type_census(dict(base, artifact_types=rows))


def test_artifact_census_statuses():
    base = {"snapshot_source_sha": HEAD}
    out = eg.artifact_type_census(dict(base, artifact_types=_types()))
    assert out["status"] == "NATIVE_COMPLETE_CONSUMER_ATTESTED"
    assert out["native_yield"] == 1.0
    assert out["consumer_attested_types"] == 1
    out = eg.artifact_type_census(
        dict(base, artifact_types=_types(consumer_attested=None))
    )
    assert out["status"] == "NATIVE_COMPLETE_CONSUMER_UNKNOWN"
    assert out["consumer_attestation_complete"] is False
    out = eg.artifact_type_census(
        dict(base, artifact_types=_types(native_verified=1, consumer_attested=False))
    )
    assert out["status"] == "NATIVE_INCOMPLETE"
    assert out["native_yield"] == 0.5
    assert out["global_federation_credit"] is None


# --- evaluate: input validation ------------------------------------------


@pytest.mark.parametrize(
    "mutate,match",
    [
        (lambda d: d.update(schema="v0"), "schema"),
        (lambda d: d.update(repository="x/y"), "repository"),
        (lambda d: d.update(snapshot_source_sha="x"), "snapshot_source_sha"),
        (lambda d: d.update(families=[]), "families"),
        (lambda d: d.update(families=[_family(), _family()]), "duplicate"),
        (
            lambda d: d.update(
                families=[_family("a", ["src/x"]), _family("b", ["SRC/x/y"])]
            ),
            "non-disjoint",
        ),
        (
            lambda d: d.update(families=[_family(source_sha=OTHER)]),
            "mixed source SHA",
        ),
        (lambda d: d.update(capacity=None), "capacity"),
        (lambda d: d.update(global_acceptance=[]), "global_acceptance"),
    ],
)
def test_evaluate_rejects(mutate, match):
    doc = _doc()
    mutate(doc)
    with pytest.raises(GE, match=match):
        eg.evaluate(doc)


def test_evaluate_rejects_non_dict():
    with pytest.raises(GE):
        eg.evaluate([])


@pytest.mark.parametrize(
    "over,match",
    [
        (dict(previous_observation_lanes=9), "exceed ceiling"),
        (dict(queue_hard_seconds=50), "queue_hard_seconds"),
        (dict(queue_p95_seconds=-1), "queue_p95_seconds"),
        (dict(evidence_yield=1.5), "exceeds"),
        (dict(available_runner_slots=-1), "available_runner_slots"),
        (dict(ready_disjoint_source_leases="1"), "ready_disjoint"),
        (dict(source_owner_slots=1.0), "source_owner_slots"),
        (dict(outstanding_native_jobs=-1), "outstanding"),
    ],
)
def test_capacity_validation(over, match):
    with pytest.raises(GE, match=match):
        eg.evaluate(_doc(capacity=_capacity(**over)))


# --- evaluate: capacity modes ---------------------------------------------


def _growth_doc(**cap):
    fam = _family(covered=30, history=_history(10, 20, 30))
    return _doc(families=[fam], capacity=_capacity(**cap))


def test_geometric_scale_on_two_positive_transitions():
    out = eg.evaluate(_growth_doc())
    cap = out["capacity"]
    assert cap["state"] == "GEOMETRIC_SCALE"
    assert cap["recommended_read_only_observation_lanes"] == 4
    assert cap["proposed_native_runner_lanes"] == 1
    assert cap["proposed_source_owner_write_lanes"] == 1
    assert cap["automatic_dispatch_permitted"] is False
    assert out["next_pilot"] == "fam"
    assert out["governed_merge_admission"] == "HOLD"


def test_geometric_scale_respects_ceiling():
    out = eg.evaluate(
        _growth_doc(previous_observation_lanes=5, maximum_observation_lanes=6)
    )
    assert out["capacity"]["recommended_read_only_observation_lanes"] == 6


def test_already_scaled_identity_holds():
    out = eg.evaluate(
        _growth_doc(last_scaled_run_id=1003, last_scaled_source_sha=format(3, "040x"))
    )
    assert out["capacity"]["state"] == "HOLD_CAPACITY"
    assert out["capacity"]["reason"] == "NO_NEW_QUALIFIED_TWO_TRANSITION_GROWTH"


@pytest.mark.parametrize(
    "cap,state,reason,lanes",
    [
        (dict(head_stable=False), "OBSERVE_ONLY", "A_B_A_SOURCE_HEAD_UNVERIFIED", 1),
        (
            dict(queue_population_complete=False),
            "OBSERVE_ONLY",
            "QUEUE_POPULATION_UNKNOWN",
            1,
        ),
        (dict(queue_p95_seconds=None), "OBSERVE_ONLY", "QUEUE_POPULATION_UNKNOWN", 1),
        (
            dict(queue_population_run_id=1),
            "OBSERVE_ONLY",
            "QUEUE_POPULATION_UNKNOWN",
            1,
        ),
        (
            dict(queue_p95_seconds=300, previous_observation_lanes=6),
            "THROTTLE",
            "QUEUE_ABOVE_HARD_LIMIT",
            3,
        ),
        (
            dict(evidence_yield=0.5),
            "THROTTLE",
            "REQUIRED_EVIDENCE_YIELD_BELOW_100_PERCENT",
            1,
        ),
        (
            dict(evidence_yield=None),
            "THROTTLE",
            "REQUIRED_EVIDENCE_YIELD_BELOW_100_PERCENT",
            1,
        ),
        (dict(queue_p95_seconds=150), "HOLD_CAPACITY", "QUEUE_ABOVE_SOFT_LIMIT", 2),
    ],
)
def test_capacity_modes(cap, state, reason, lanes):
    out = eg.evaluate(_growth_doc(**cap))
    assert out["capacity"]["state"] == state
    assert out["capacity"]["reason"] == reason
    assert out["capacity"]["recommended_read_only_observation_lanes"] == lanes


@pytest.mark.parametrize(
    "cap",
    [
        dict(available_runner_slots=None),
        dict(ready_disjoint_source_leases=None),
        dict(source_owner_slots=None),
        dict(outstanding_native_jobs=None),
        dict(outstanding_native_jobs=2),
        dict(head_stable=False),
    ],
)
def test_unknown_capacity_means_no_runner_lanes(cap):
    out = eg.evaluate(_growth_doc(**cap))
    assert out["capacity"]["proposed_native_runner_lanes"] == 0
    assert out["capacity"]["proposed_source_owner_write_lanes"] == 0


def test_queue_recovered_event_caps_runner_lanes():
    fams = [
        _family("a", ["src/a"], first_reds=["x"]),
        _family("b", ["src/b"]),
        _family("c", ["src/c"]),
    ]
    events = [_event(kind="QUEUE_RECOVERED", family="b")]
    out = eg.evaluate(_doc(families=fams))
    assert out["capacity"]["proposed_native_runner_lanes"] == 2
    out = eg.evaluate(_doc(families=fams, events=events))
    assert out["capacity"]["proposed_native_runner_lanes"] == 1
    # first-red family ranks first
    assert out["ranked_next_source_families"][0] == "a"


# --- evaluate: retrigger, ranking and programme stop ----------------------


def test_reopen_event_retriggers_local_stop():
    fams = [
        _family("done", ["src/done"], covered=95),
        _family("open", ["src/open"], covered=10),
    ]
    events = [_event(kind="CONTRACT_CHANGED", family="done")]
    out = eg.evaluate(_doc(families=fams, events=events))
    states = {f["id"]: f["state"] for f in out["families"]}
    assert states["done"] == "LOCAL_RETRIGGER_PILOT"
    assert out["ranked_next_source_families"] == ["done", "open"]
    assert out["retrigger"]["consume_only_after_actual_execution"] == [
        "|".join(("done", "CONTRACT_CHANGED", HEAD, "fp"))
    ]


def test_ranking_by_need_then_id():
    fams = [
        _family("b", ["src/b"], covered=10),
        _family("a", ["src/a"], covered=10),
        _family("c", ["src/c"], covered=50),
        _family("z", ["src/z"], covered=100),
    ]
    out = eg.evaluate(_doc(families=fams))
    assert out["ranked_next_source_families"] == ["a", "b", "c"]
    assert out["next_pilot"] == "a"
    assert out["programme"]["state"] == "CONTINUE_OR_HOLD"
    assert out["explicit_stop_scope"] == "LOCAL_ONLY_OR_NONE"


def test_global_stop_when_everything_proven():
    out = eg.evaluate(_doc(families=[_family(covered=95)]))
    prog = out["programme"]
    assert prog["state"] == "GLOBAL_CONTROL_ELIGIBLE"
    assert prog["stop_entire_program"] is True
    assert prog["required_artifact_yield"] == 1.0
    assert out["explicit_stop_scope"] == "GLOBAL"
    assert out["next_pilot"] is None
    assert out["capacity"]["proposed_native_runner_lanes"] == 0
    assert out["capacity"]["proposed_source_owner_write_lanes"] == 0


@pytest.mark.parametrize(
    "over",
    [
        dict(accepted_roots_remaining=1),
        dict(source_attested_repositories=1),
        dict(valid_artifacts=2),
        dict(independent_stable_pulses=7),
        dict(head_stable=False),
        dict(gates={"branch_protection": True}),
        dict(gates=None),
        dict(no_special_cause_variation=False),
    ],
)
def test_global_stop_blocked(over):
    doc = _doc(families=[_family(covered=95)], global_acceptance=_acceptance(**over))
    assert eg.evaluate(doc)["programme"]["stop_entire_program"] is False


def test_global_stop_needs_consumer_evidence():
    doc = _doc(families=[_family(covered=95)], artifact_types=None)
    prog = eg.evaluate(doc)["programme"]
    assert prog["stop_entire_program"] is False
    assert prog["artifact_consumer_evidence_complete"] is False


def test_programme_untyped_numbers_reported_as_none():
    end = _acceptance(
        accepted_roots_remaining="0",
        valid_artifacts=None,
        independent_stable_pulses=None,
    )
    prog = eg.evaluate(_doc(global_acceptance=end))["programme"]
    assert prog["accepted_roots_remaining"] is None
    assert prog["required_artifact_yield"] is None
    assert prog["repeatability_observations"] is None
    assert prog["governance_qualified"] is True


# --- CLI --------------------------------------------------------------------


def test_main_writes_decision(tmp_path, capsys):
    src = tmp_path / "in.json"
    src.write_text(json.dumps(_growth_doc()), encoding="utf-8")
    out = tmp_path / "nested" / "out.json"
    assert eg.main(["--input", str(src), "--out", str(out)]) == 0
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["schema"] == "codepurple.elastic_wave_decision.v1"
    printed = json.loads(capsys.readouterr().out)
    assert printed == {
        "decision": "GEOMETRIC_SCALE",
        "global_stop": False,
        "next_pilot": "fam",
        "runner_lanes": 1,
    }


def test_evaluate_does_not_mutate_input():
    doc = _growth_doc()
    before = copy.deepcopy(doc)
    eg.evaluate(doc)
    assert doc == before
