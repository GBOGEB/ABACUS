"""Lane A wave 8: MIP/EVIDENCE_TO_ADMISSION_OBSERVATORY/wave_metrics.py."""

import json

import pytest

from tests.coverage_waves.lane_a._load import load

wm = load("MIP/EVIDENCE_TO_ADMISSION_OBSERVATORY/wave_metrics.py")

HEAD = "d" * 40
ART = "e" * 64
PE = wm.ProofError


def _jobs(run_id, n=2, conclusion="success"):
    return [
        {
            "job_id": i + 1,
            "run_id": run_id,
            "head_sha": HEAD,
            "conclusion": conclusion,
            "artifact_sha256": ART,
            "artifact_id": 10 + i,
        }
        for i in range(n)
    ]


def _obs(wave=1, covered=10, cases=5, run_id=None, **over):
    run_id = run_id or 500 + wave
    obs = {
        "head_sha": HEAD,
        "wave": wave,
        "run_id": run_id,
        "eligible_opportunities": 100,
        "covered_opportunities": covered,
        "cases_per_job": cases,
        "cohort_id": "W007",
        "configuration_id": "cfg",
        "expected_jobs": 2,
        "jobs": _jobs(run_id),
    }
    obs.update(over)
    return obs


# --- qualify_observation --------------------------------------------------


def test_qualify_fully_qualified():
    out = wm.qualify_observation(_obs(covered=25, cases=4))
    assert out["fully_qualified"] is True
    assert out["jobs_observed"] == 2
    assert out["jobs_success"] == 2
    assert out["execution_count"] == 8
    assert out["covered_percent"] == 25.0
    assert out["uncovered_opportunities"] == 75


def test_qualify_partial_success_not_qualified():
    obs = _obs()
    obs["jobs"][1]["conclusion"] = "failure"
    out = wm.qualify_observation(obs)
    assert out["fully_qualified"] is False
    assert out["execution_count"] is None
    assert out["covered_percent"] is None
    assert out["uncovered_opportunities"] is None


def test_qualify_fewer_jobs_than_expected():
    out = wm.qualify_observation(_obs(expected_jobs=3))
    assert out["fully_qualified"] is False


@pytest.mark.parametrize(
    "over,match",
    [
        (dict(head_sha="abc"), "SHA"),
        (dict(wave=-1), "wave"),
        (dict(run_id=0), "run_id"),
        (dict(eligible_opportunities=0), "eligible"),
        (dict(covered_opportunities=None), "covered"),
        (dict(covered_opportunities=101), "exceed"),
        (dict(cases_per_job=0), "cases_per_job"),
        (dict(cohort_id="  "), "cohort"),
        (dict(configuration_id=3), "configuration"),
        (dict(jobs=[]), "receipts"),
        (dict(jobs=None), "receipts"),
        (dict(jobs=["x"]), "Malformed"),
        (dict(expected_jobs=0), "expected_jobs"),
        (dict(expected_jobs=1), "More native jobs"),
    ],
)
def test_qualify_rejections(over, match):
    obs = _obs()
    obs.update(over)
    with pytest.raises(PE, match=match):
        wm.qualify_observation(obs)


def test_qualify_rejects_non_dict():
    with pytest.raises(PE):
        wm.qualify_observation([])


@pytest.mark.parametrize(
    "job_over,match",
    [
        (dict(job_id=0), "job_id"),
        (dict(run_id=999), "pinned"),
        (dict(head_sha="f" * 40), "pinned"),
        (dict(conclusion="weird"), "conclusion"),
        (dict(artifact_sha256="short"), "artifact SHA"),
        (dict(artifact_sha256=None), "artifact SHA"),
        (dict(artifact_id=0), "artifact_id"),
    ],
)
def test_job_receipt_rejections(job_over, match):
    obs = _obs()
    obs["jobs"][0].update(job_over)
    with pytest.raises(PE, match=match):
        wm.qualify_observation(obs)


def test_duplicate_job_identity():
    obs = _obs()
    obs["jobs"][1]["job_id"] = 1
    with pytest.raises(PE, match="Duplicate"):
        wm.qualify_observation(obs)


def test_non_success_jobs_need_no_artifact():
    obs = _obs()
    for job in obs["jobs"]:
        job["conclusion"] = None
        job.pop("artifact_sha256")
        job.pop("artifact_id")
    out = wm.qualify_observation(obs)
    assert out["jobs_success"] == 0
    assert out["fully_qualified"] is False


# --- matched_progress -------------------------------------------------------


def test_round_rejects_non_finite():
    assert wm._round(1.23456789) == 1.234568
    with pytest.raises(PE):
        wm._round(float("inf"))


def test_progress_requires_observations():
    with pytest.raises(PE):
        wm.matched_progress([])
    with pytest.raises(PE):
        wm.matched_progress(None)


def test_progress_single_observation():
    out = wm.matched_progress([_obs(covered=40)])
    assert out["gain_rate_trend"] == "INSUFFICIENT_MATCHED_PULSES"
    assert out["rate_change_pp_per_wave"] is None
    assert out["remaining_uncovered_opportunities"] == 60
    assert out["ceiling_reached"] is False
    assert (
        out["next_behavioral_focus"] == "TARGET_UNCOVERED_BRANCHES_AND_NEGATIVE_PATHS"
    )
    row = out["observations"][0]
    assert row["delta_covered"] is None
    assert row["url"].endswith("/runs/501")


def test_progress_decelerating_with_wave_span():
    obs = [
        _obs(wave=1, covered=10, cases=5),
        _obs(wave=3, covered=30, cases=7),
        _obs(wave=4, covered=35, cases=7),
    ]
    out = wm.matched_progress(obs)
    rows = out["observations"]
    assert rows[1]["wave_span"] == 2
    assert rows[1]["gain_pp_per_wave"] == 10.0
    assert rows[1]["new_covered_per_added_case"] == 10.0
    assert rows[2]["gain_pp_per_wave"] == 5.0
    # no added cases -> per-case yield is undefined, not infinite
    assert rows[2]["new_covered_per_added_case"] is None
    assert out["gain_rate_trend"] == "DECELERATING_GAIN"
    assert out["rate_change_pp_per_wave"] == -5.0
    assert out["causal_coverage_uplift"] is None


def test_progress_accelerating_and_stable():
    acc = wm.matched_progress(
        [_obs(1, 10), _obs(2, 12), _obs(3, 20)],
    )
    assert acc["gain_rate_trend"] == "ACCELERATING_GAIN"
    stable = wm.matched_progress(
        [_obs(1, 10), _obs(2, 20), _obs(3, 30)],
    )
    assert stable["gain_rate_trend"] == "STABLE_GAIN"
    assert stable["rate_change_pp_per_wave"] == 0.0


def test_progress_ceiling_reached():
    out = wm.matched_progress([_obs(1, 90), _obs(2, 100)])
    assert out["ceiling_reached"] is True
    assert out["next_behavioral_focus"] == ("EXPAND_TO_SEPARATE_UNCOVERED_SOURCE_SLICE")


def test_progress_rejects_wave_order():
    with pytest.raises(PE, match="strictly"):
        wm.matched_progress([_obs(2, 10), _obs(1, 20)])
    with pytest.raises(PE, match="strictly"):
        wm.matched_progress([_obs(1, 10), _obs(1, 20, run_id=900)])


@pytest.mark.parametrize(
    "over",
    [
        dict(cohort_id="other"),
        dict(configuration_id="other"),
        dict(eligible_opportunities=200),
    ],
)
def test_progress_rejects_cohort_drift(over):
    with pytest.raises(PE, match="Cohort"):
        wm.matched_progress([_obs(1, 10), _obs(2, 20, **over)])


def test_progress_rejects_unqualified_cells():
    with pytest.raises(PE, match="nonterminal"):
        wm.matched_progress([_obs(1, 10), _obs(2, 20, expected_jobs=3)])


# --- rank_source_slices -----------------------------------------------------


def _cand(family, paths, uncovered=10, eligible=20, **over):
    cand = {
        "family": family,
        "paths": paths,
        "uncovered": uncovered,
        "eligible": eligible,
        "source_sha": HEAD,
    }
    cand.update(over)
    return cand


def test_rank_validation():
    with pytest.raises(PE):
        wm.rank_source_slices("x")
    with pytest.raises(PE):
        wm.rank_source_slices([], max_source_paths=0)
    with pytest.raises(PE, match="dictionary"):
        wm.rank_source_slices([1])
    with pytest.raises(PE, match="family"):
        wm.rank_source_slices([_cand("", ["a"])])


def test_rank_withholds_and_orders():
    cands = [
        _cand("wide", ["a", "b", "c"]),
        _cand("abs", ["/x"]),
        _cand("dots", ["x/../y"]),
        _cand("empty", []),
        _cand("blank", [""]),
        _cand("big", ["p1"], uncovered=12),
        _cand("overlap", ["p1"]),
        _cand("badnum", ["p2"], uncovered=30),
        _cand("badden", ["p3"], eligible=0),
        _cand("badsha", ["p4"], source_sha="x"),
        _cand("floatu", ["p5"], uncovered=1.0),
        _cand("done", ["p6"], uncovered=0),
        _cand("red", ["p7", "p8"], uncovered=4, first_red=True),
        _cand("alpha", ["p9"], uncovered=12),
    ]
    out = wm.rank_source_slices(cands)
    withheld = {w["family"]: w["reason"] for w in out["withheld"]}
    assert withheld == {
        "wide": "SOURCE_LEASE_TOO_WIDE_OR_INVALID",
        "abs": "SOURCE_LEASE_TOO_WIDE_OR_INVALID",
        "dots": "SOURCE_LEASE_TOO_WIDE_OR_INVALID",
        "empty": "SOURCE_LEASE_TOO_WIDE_OR_INVALID",
        "blank": "SOURCE_LEASE_TOO_WIDE_OR_INVALID",
        "overlap": "OVERLAPPING_SOURCE_LEASE",
        "badnum": "MISSING_COMPARABLE_SOURCE_METRIC",
        "badden": "MISSING_COMPARABLE_SOURCE_METRIC",
        "badsha": "MISSING_COMPARABLE_SOURCE_METRIC",
        "floatu": "MISSING_COMPARABLE_SOURCE_METRIC",
        "done": "MEASURED_COHORT_AT_CEILING",
    }
    ranked = [r["family"] for r in out["qualified_readonly_candidates"]]
    assert ranked == ["red", "alpha", "big"]
    assert (
        out["qualified_readonly_candidates"][0]["opportunities_per_changed_file"] == 2.0
    )
    assert out["max_disjoint_candidates"] == 3
    assert out["source_write_permitted"] is False


def test_rank_wider_lease_allowed_when_configured():
    out = wm.rank_source_slices([_cand("wide", ["a", "b", "c"])], max_source_paths=3)
    assert out["max_disjoint_candidates"] == 1
    assert out["withheld"] == []


# --- adaptive_slice_policy --------------------------------------------------


def _snapshot(**over):
    snap = {
        "main": {"head_stable": True, "sha": HEAD},
        "workflows": {
            "b0": {
                "sha": HEAD,
                "status": "completed",
                "conclusion": "success",
                "queue_p95_seconds": 300,
            }
        },
        "coverage": {"measured": {"sha": HEAD, "status": "MEASURED_ON_EXACT_MAIN_SHA"}},
        "governance": {
            "required_approvals": 1,
            "required_check_rules": 2,
            "negative_canary_rejected": True,
        },
        "census_errors": [],
        "issues": {"accepted_roots_closed": 4},
    }
    snap.update(over)
    return snap


def test_policy_fully_qualified_frontier():
    out = wm.adaptive_slice_policy(
        _snapshot(), {"remaining_uncovered_opportunities": 5}
    )
    assert out["measurement_frontier_qualified"] is True
    assert out["read_only_parallel_lanes_max"] == 3
    assert out["admission_blockers"] == []
    assert out["measurement_blockers"] == []
    assert out["accepted_causal_root_closed"] == 4
    assert out["next_slice"] == "SAME_COHORT_NEGATIVE_REVERSE_FAULT_INJECTION"
    assert "5 verified" in out["minimum_next_wave"]
    assert out["merge_admission"] == "HOLD"


def test_policy_empty_snapshot_lists_all_blockers():
    out = wm.adaptive_slice_policy({}, {"remaining_uncovered_opportunities": 0})
    assert out["read_only_parallel_lanes_max"] == 1
    assert out["admission_blockers"] == [
        "OWNER_GITHUB_RULES_NOT_ENFORCED",
        "NEGATIVE_RED_CANARY_NOT_PROVEN",
    ]
    assert out["measurement_blockers"] == [
        "A_B_A_MAIN_UNVERIFIED",
        "EXACT_MAIN_B0_NOT_TERMINAL_GREEN",
        "CURRENT_MAIN_COVERAGE_ARTIFACT_MISSING",
        "RUNNER_QUEUE_P95_UNKNOWN",
    ]
    assert out["accepted_causal_root_closed"] is None
    assert out["next_slice"] == "NEXT_DISTINCT_SOURCE_FAMILY_OR_DIFF_COHORT"


def test_policy_queue_above_limit_and_census_errors():
    snap = _snapshot(census_errors=["partial"])
    snap["workflows"]["b0"]["queue_p95_seconds"] = 901
    out = wm.adaptive_slice_policy(snap, {"remaining_uncovered_opportunities": 1})
    assert "RUNNER_QUEUE_P95_ABOVE_900_SECONDS" in out["measurement_blockers"]
    assert "CENSUS_PARTIAL_OR_FAILED" in out["measurement_blockers"]
    assert out["measurement_frontier_qualified"] is False


@pytest.mark.parametrize("queue", [float("nan"), -1, "5", None])
def test_policy_invalid_queue_is_unknown(queue):
    snap = _snapshot()
    snap["workflows"]["b0"]["queue_p95_seconds"] = queue
    out = wm.adaptive_slice_policy(snap, {"remaining_uncovered_opportunities": 1})
    assert "RUNNER_QUEUE_P95_UNKNOWN" in out["measurement_blockers"]


def test_policy_weak_governance():
    snap = _snapshot(governance={"required_approvals": 0, "required_check_rules": 1})
    out = wm.adaptive_slice_policy(snap, {"remaining_uncovered_opportunities": 1})
    assert out["admission_blockers"] == [
        "OWNER_GITHUB_RULES_NOT_ENFORCED",
        "NEGATIVE_RED_CANARY_NOT_PROVEN",
    ]
    # admission blockers do not block the measurement frontier
    assert out["measurement_frontier_qualified"] is True


def test_policy_requires_scope_numerator():
    with pytest.raises(PE, match="numerator"):
        wm.adaptive_slice_policy(_snapshot(), {})


# --- build_wave_receipt -----------------------------------------------------


def _history():
    return {"observations": [_obs(1, 10), _obs(2, 20)]}


def _write(path, payload):
    path.write_bytes(json.dumps(payload).encode("utf-8"))


def test_receipt_with_all_inputs_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(wm, "ROOT", tmp_path)
    out = wm.build_wave_receipt(_snapshot(), _history())
    assert out["schema"] == "codepurple.adaptive_wave_receipt.v1"
    assert out["source_frontier"]["status"] == "CANDIDATE_PROOF_UNAVAILABLE"
    assert out["engineering_convergence"]["state"] == "CONVERGENCE_PROOF_UNAVAILABLE"
    assert out["elastic_controller"]["state"] == "W33_CONTROLLER_INPUT_UNQUALIFIED"
    assert out["main_sha"] == HEAD
    assert out["current_main_coverage_sha"] == HEAD
    assert out["historical_focus"]["remaining_uncovered_opportunities"] == 80
    assert out["scale_policy"]["read_only_parallel_lanes_max"] == 3


def test_receipt_with_all_inputs_present(tmp_path, monkeypatch):
    monkeypatch.setattr(wm, "ROOT", tmp_path)
    _write(
        tmp_path / "source_frontier.json",
        {
            "coverage_observed_main_sha": HEAD,
            "coverage_total_opportunities": 52200,
            "candidates": [_cand("fam", ["src/a.py"])],
        },
    )
    _write(
        tmp_path / "engineering_wave_history.json",
        {"observations": [], "target_coverage_percent": 90},
    )
    _write(tmp_path / "w33_verified_focused_input.json", {"snapshot_source_sha": HEAD})
    calls = []

    def fake_elastic(doc):
        calls.append(doc)
        return {"capacity": {"state": "HOLD_CAPACITY"}}

    monkeypatch.setattr(wm, "evaluate_elastic_wave", fake_elastic)
    out = wm.build_wave_receipt(_snapshot(), _history())
    frontier = out["source_frontier"]
    assert frontier["coverage_total_opportunities"] == 52200
    assert [
        c["family"] for c in frontier["ranked"]["qualified_readonly_candidates"]
    ] == ["fam"]
    assert out["engineering_convergence"]["state"] == (
        "AWAIT_FIRST_TERMINAL_OBSERVATION"
    )
    elastic = out["elastic_controller"]
    assert elastic["source_head_equals_current_main"] is True
    assert elastic["measurement_freshness"].startswith("HISTORICAL")
    assert calls == [{"snapshot_source_sha": HEAD}]


def test_receipt_bad_frontier_and_elastic_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(wm, "ROOT", tmp_path)
    _write(tmp_path / "source_frontier.json", {"candidates": "notalist"})
    (tmp_path / "engineering_wave_history.json").write_bytes(b"{not json")
    _write(tmp_path / "w33_verified_focused_input.json", {"schema": "wrong"})
    out = wm.build_wave_receipt(_snapshot(), _history())
    assert out["source_frontier"]["status"] == "CANDIDATE_PROOF_UNAVAILABLE"
    assert "Candidates" in out["source_frontier"]["error"]
    assert out["engineering_convergence"]["stop_entire_program"] is False
    # the real governor rejects the schema with a ValueError subclass
    assert out["elastic_controller"]["state"] == "W33_CONTROLLER_INPUT_UNQUALIFIED"
    assert "schema" in out["elastic_controller"]["error"]


def test_production_defect_receipt_crashes_on_null_main(tmp_path, monkeypatch):
    # Pins a production_defect: adaptive_slice_policy tolerates main=None
    # (``snapshot.get("main") or {}``) but build_wave_receipt then calls
    # ``snapshot.get("main", {}).get("sha")`` on None. This test will fail
    # once the receipt builder handles a null main section.
    monkeypatch.setattr(wm, "ROOT", tmp_path)
    with pytest.raises(AttributeError):
        wm.build_wave_receipt(_snapshot(main=None), _history())


# --- CLI --------------------------------------------------------------------


def test_main_writes_receipt(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(wm, "ROOT", tmp_path)
    snap = tmp_path / "evidence.json"
    hist = tmp_path / "wave_history.json"
    out = tmp_path / "wave.json"
    _write(snap, _snapshot())
    _write(hist, _history())
    rc = wm.main(["--snapshot", str(snap), "--history", str(hist), "--out", str(out)])
    assert rc == 0
    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert receipt["main_sha"] == HEAD
    printed = capsys.readouterr().out
    assert "readonly_lanes=3" in printed
    assert "covered=20/100" in printed
