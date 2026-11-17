"""Lane A wave 14: mission_control_lite.job_first_red validation and summary."""

import pytest

from mission_control_lite import job_first_red as jfr

SHA = "a" * 40
OTHER = "b" * 40


def _job(job_id=1, run_id=7, conclusion="success", steps=None, **extra):
    job = {
        "id": job_id,
        "run_id": run_id,
        "name": "build",
        "status": "completed",
        "conclusion": conclusion,
    }
    if steps is not None:
        job["steps"] = steps
    job.update(extra)
    return job


def _step(number, name="s", conclusion="success", status="completed"):
    return {"number": number, "name": name, "conclusion": conclusion, "status": status}


def test_sha_predicate():
    assert jfr._sha(SHA)
    assert not jfr._sha("A" * 40)
    assert not jfr._sha("a" * 39)
    assert not jfr._sha(None)


def test_summary_groups_first_failed_steps():
    jobs = [
        _job(
            3, 8, "failure", [_step(2, "lint", "failure"), _step(1, "unit", "failure")]
        ),
        _job(1, 7, "failure", [_step(1, "unit", "failure")]),
        _job(2, 7, "failure", [_step(1, "setup")]),
        _job(4, 8, "success"),
        dict(_job(5, 8, "failure", [_step(1, "x", "failure")]), name="deploy"),
    ]
    out = jfr.summarize(SHA, {7: SHA, 8: SHA}, jobs)
    assert out["runs_in_scope"] == 2
    assert out["terminal_jobs"] == 5
    assert out["failed_jobs"] == 4
    assert out["first_red_observed_jobs"] == 3
    assert out["first_red_unknown_jobs"] == 1
    assert out["first_red_observed_fraction"] == 0.75
    assert out["candidate_groups"][0] == {
        "job_name": "build",
        "step_name": "unit",
        "manifestations": 2,
    }
    assert out["candidate_groups"][1]["job_name"] == "deploy"
    assert [(r["run_id"], r["job_id"]) for r in out["records"]] == [
        (7, 1),
        (7, 2),
        (8, 3),
        (8, 4),
        (8, 5),
    ]
    assert out["records"][3]["first_failed_step"] is None
    assert out["root_cause_confirmed"] is False
    assert out["merge_admission"] == "HOLD"


def test_no_failures_fraction_none():
    out = jfr.summarize(SHA, {}, [])
    assert out["first_red_observed_fraction"] is None
    assert out["candidate_groups"] == [] and out["records"] == []


@pytest.mark.parametrize(
    "head,run_heads,jobs,msg",
    [
        ("bad", {}, [], "canonical"),
        (SHA, [], [], "mapping and job list"),
        (SHA, {}, {}, "mapping and job list"),
        (SHA, {"1": SHA}, [], "invalid run-head"),
        (SHA, {0: SHA}, [], "invalid run-head"),
        (SHA, {True: SHA}, [], "invalid run-head"),
        (SHA, {1: "zz"}, [], "invalid run-head"),
        (SHA, {1: OTHER}, [], "drift"),
    ],
)
def test_header_validation(head, run_heads, jobs, msg):
    with pytest.raises(ValueError, match=msg):
        jfr.summarize(head, run_heads, jobs)


@pytest.mark.parametrize(
    "jobs,msg",
    [
        (["x"], "record"),
        ([_job(job_id="1")], "invalid job ID"),
        ([_job(job_id=0)], "invalid job ID"),
        ([_job(run_id="7")], "invalid job ID"),
        ([_job(run_id=99)], "invalid job ID"),
        ([_job(1), _job(1)], "invalid job ID"),
        ([_job(name="")], "job name"),
        ([_job(name=5)], "job name"),
        ([_job(status="in_progress")], "nonterminal job"),
        ([_job(conclusion="weird")], "nonterminal job"),
        ([_job(steps="nope")], "invalid steps"),
        ([_job(steps=["x"])], "invalid step$"),
        ([_job(steps=[_step("1")])], "step identity"),
        ([_job(steps=[_step(0)])], "step identity"),
        ([_job(steps=[_step(1), _step(1)])], "step identity"),
        ([_job(steps=[_step(1, name="")])], "step identity"),
        ([_job(steps=[{"number": 1}])], "step identity"),
        (
            [_job(steps=[_step(1, conclusion="failure", status="queued")])],
            "failed step",
        ),
    ],
)
def test_job_validation(jobs, msg):
    with pytest.raises(ValueError, match=msg):
        jfr.summarize(SHA, {7: SHA}, jobs)
