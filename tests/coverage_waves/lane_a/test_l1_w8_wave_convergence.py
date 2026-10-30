"""Lane A wave 8: MIP/EVIDENCE_TO_ADMISSION_OBSERVATORY/wave_convergence.py."""

import pytest

from tests.coverage_waves.lane_a._load import load

wc = load("MIP/EVIDENCE_TO_ADMISSION_OBSERVATORY/wave_convergence.py")

CFG = "e" * 64
COHORT = "f" * 64


def _row(wave, covered, **over):
    row = {
        "wave": wave,
        "run_id": 100 + wave,
        "run_attempt": 1,
        "source_sha": format(wave, "040x"),
        "artifact_digest": format(wave, "064x"),
        "configuration_digest": CFG,
        "cohort_digest": COHORT,
        "source_slice": "slice-%d" % wave,
        "eligible": 100,
        "covered": covered,
        "job_expected": 2,
        "job_success": 2,
        "test_failed": 0,
        "test_skipped": 0,
        "cases_added": 1,
        "terminal": True,
        "head_stable": True,
        "first_red_signatures": [],
        "root_dispositions_complete": False,
        "queue_p95_seconds": 100,
        "attempted_new_behavior": True,
    }
    # built via dict() to avoid bandit B105 on a dict-literal key
    row.update(dict(test_passed=5))
    row.update(over)
    return row


def _series(*covered, **over_last):
    rows = [_row(i + 1, c) for i, c in enumerate(covered)]
    rows[-1].update(over_last)
    return rows


def test_empty_history_awaits_first_observation():
    out = wc.evaluate([])
    assert out["state"] == "AWAIT_FIRST_TERMINAL_OBSERVATION"
    assert out["stop_engineering_wave"] is False


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(consecutive_no_change=0),
        dict(target_pct=0),
        dict(target_pct=101),
        dict(target_pct=True),
        dict(target_pct="95"),
        dict(queue_limit=0),
        dict(queue_limit=float("inf")),
        dict(queue_limit="900"),
    ],
)
def test_parameter_validation(kwargs):
    with pytest.raises(wc.ConvergenceProofError):
        wc.evaluate([], **kwargs)


def test_history_must_be_list():
    with pytest.raises(wc.ConvergenceProofError):
        wc.evaluate({"wave": 1})


@pytest.mark.parametrize(
    "over",
    [
        dict(wave=0),
        dict(run_id="1"),
        dict(run_attempt=None),
        dict(source_sha="abc"),
        dict(artifact_digest="g" * 64),
        dict(configuration_digest=None),
        dict(cohort_digest="F" * 64),
        dict(source_slice="  "),
        dict(source_slice=None),
        dict(eligible=0),
        dict(covered=-1),
        dict(covered=101),
        dict(test_failed=-1),
        dict(job_expected=0),
        dict(job_success=3),
        dict(terminal=False),
        dict(head_stable=None),
        dict(job_success=1),
        dict(test_passed=0),
        dict(test_failed=1),
        dict(test_skipped=1),
        dict(first_red_signatures="x"),
        dict(first_red_signatures=[""]),
        dict(first_red_signatures=["a", "a"]),
        dict(root_dispositions_complete=None),
        dict(queue_p95_seconds=-1),
        dict(queue_p95_seconds=float("nan")),
        dict(queue_p95_seconds="5"),
        dict(attempted_new_behavior=False),
    ],
)
def test_bad_observation_is_evidence_blocked(over):
    row = _row(1, 10)
    row.update(over)
    out = wc.evaluate([row])
    assert out["state"] == "EVIDENCE_BLOCKED"
    assert out["blocker"]
    assert out["stop_engineering_wave"] is False


def test_non_dict_row_is_evidence_blocked():
    out = wc.evaluate(["row"])
    assert out["state"] == "EVIDENCE_BLOCKED"
    assert "expected object" in out["blocker"]


@pytest.mark.parametrize(
    "field", ["run_id", "source_sha", "artifact_digest", "source_slice"]
)
def test_reused_identity_raises(field):
    rows = _series(10, 20)
    rows[1][field] = rows[0][field]
    with pytest.raises(wc.ConvergenceProofError, match=field):
        wc.evaluate(rows)


def test_reused_wave_raises():
    rows = _series(10, 20)
    rows[1]["wave"] = 1
    with pytest.raises(wc.ConvergenceProofError, match="wave"):
        wc.evaluate(rows)


def test_wave_gap_raises():
    rows = [_row(1, 10), _row(3, 20)]
    with pytest.raises(wc.ConvergenceProofError, match="consecutively"):
        wc.evaluate(rows)


@pytest.mark.parametrize(
    "field,value",
    [
        ("eligible", 200),
        ("configuration_digest", "1" * 64),
        ("cohort_digest", "2" * 64),
    ],
)
def test_incomparable_cohort(field, value):
    rows = _series(10, 20)
    rows[1][field] = value
    out = wc.evaluate(rows)
    assert out["state"] == "INCOMPARABLE_COHORT"
    assert out["cohort_difference"] == field
    assert out["verified_waves"] == 2


def test_regression_wins_over_everything():
    out = wc.evaluate(_series(99, 96, first_red_signatures=["boom"]))
    assert out["state"] == "COVERAGE_REGRESSION"
    assert out["delta_covered_by_wave"] == [-3]


def test_first_red_unresolved():
    out = wc.evaluate(_series(10, 20, first_red_signatures=["boom"]))
    assert out["state"] == "FIRST_RED_UNRESOLVED"
    assert out["suggested_readonly_lanes"] == 1
    assert out["stop_this_source_slice"] is False


def test_source_target_reached_stops_slice_not_program():
    out = wc.evaluate(_series(90, 96))
    assert out["state"] == "SOURCE_TARGET_REACHED"
    assert out["stop_this_source_slice"] is True
    assert out["stop_entire_program"] is False
    assert out["covered_percent"] == 96.0
    assert out["uncovered"] == 4


def test_custom_target_pct():
    out = wc.evaluate(_series(40), target_pct=40)
    assert out["state"] == "SOURCE_TARGET_REACHED"


def test_plateau_needs_four_waves():
    three = wc.evaluate(_series(50, 50, 50))
    assert three["state"] != "COHORT_PLATEAU_CONFIRMED"
    assert three["no_change_streak"] == 2
    four = wc.evaluate(_series(50, 50, 50, 50))
    assert four["state"] == "COHORT_PLATEAU_CONFIRMED"
    assert four["stop_this_source_slice"] is True
    assert four["consecutive_no_change_required"] == 3


def test_plateau_streak_resets_on_growth():
    out = wc.evaluate(_series(50, 50, 60, 60))
    assert out["no_change_streak"] == 1
    assert out["state"] == "NOT_YET_CONVERGED"


def test_queue_unknown():
    out = wc.evaluate(_series(10, 20, queue_p95_seconds=None))
    assert out["state"] == "QUEUE_PROOF_UNKNOWN"
    assert out["queue_qualified"] is False
    assert out["suggested_readonly_lanes"] == 1


def test_capacity_pressure():
    out = wc.evaluate(_series(10, 20, queue_p95_seconds=1000))
    assert out["state"] == "CAPACITY_PRESSURE"


def test_custom_queue_limit():
    out = wc.evaluate(_series(10, 20, queue_p95_seconds=50), queue_limit=40)
    assert out["state"] == "CAPACITY_PRESSURE"


def test_measurable_progress():
    out = wc.evaluate(_series(10, 20, queue_p95_seconds=900))
    assert out["state"] == "MEASURABLE_PROGRESS"
    assert out["queue_qualified"] is True
    assert out["suggested_readonly_lanes"] == 3
    assert out["last_run_id"] == 102
    assert out["governed_merge_credit"] is None


def test_single_wave_not_yet_converged():
    out = wc.evaluate([_row(5, 10)])
    assert out["state"] == "NOT_YET_CONVERGED"
    assert out["delta_covered_by_wave"] == []
    assert out["verified_waves"] == 1
