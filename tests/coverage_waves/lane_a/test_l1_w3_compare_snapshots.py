"""Lane A wave 3: MIP/G3CS_CONVERGENCE_V2/tools/compare_snapshots.py."""

import copy
import json

import pytest

from tests.coverage_waves.lane_a._load import load

cs = load("MIP/G3CS_CONVERGENCE_V2/tools/compare_snapshots.py")

SRC = "a" * 40
OTHER = "b" * 40
SEL = "c" * 64


def job(jid=1, **kw):
    j = {
        "job_id": jid,
        "source_sha": SRC,
        "status": "completed",
        "conclusion": "success",
        "created_at": "2026-01-01T00:00:00Z",
        "started_at": "2026-01-01T00:00:10Z",
        "completed_at": "2026-01-01T00:01:10Z",
    }
    j.update(kw)
    return j


def run(rid=1, attempt=1, jobs=None, **kw):
    r = {
        "run_id": rid,
        "attempt": attempt,
        "source_sha": SRC,
        "status": "completed",
        "conclusion": "success",
        "jobs": [job()] if jobs is None else jobs,
    }
    r.update(kw)
    return r


def snap(runs=None, observed="2026-01-01T01:00:00Z", **kw):
    s = {
        "schema": cs.SCHEMA,
        "repository": "GBOGEB/ABACUS",
        "source_sha": SRC,
        "selection_sha256": SEL,
        "source_clock": "EXACT_PR_HEAD",
        "observed_at_utc": observed,
        "admission": "HOLD",
        "authority_transfer": False,
        "runs": [run()] if runs is None else runs,
    }
    s.update(kw)
    return s


def test_date_parses_and_rejects():
    assert cs.date("2026-01-01T00:00:00Z").year == 2026
    with pytest.raises(ValueError, match="UTC Z"):
        cs.date("2026-01-01T00:00:00")
    with pytest.raises(ValueError, match="UTC Z"):
        cs.date(None)
    with pytest.raises(ValueError, match="invalid UTC time"):
        cs.date("notadateZ")


def test_validate_returns_keyed_runs():
    out = cs.validate(snap(runs=[run(1), run(2, 3)]))
    assert set(out) == {(1, 1), (2, 3)}


@pytest.mark.parametrize(
    "mutate,msg",
    [
        (lambda s: s.update(schema="x"), "invalid schema"),
        (lambda s: s.update(repository="x/y"), "repository identity"),
        (lambda s: s.update(source_sha="ABC"), "invalid source SHA"),
        (lambda s: s.update(selection_sha256="z"), "missing selection hash"),
        (lambda s: s.update(source_clock="NOW"), "missing source clock"),
        (lambda s: s.update(admission="ADMIT"), "unauthorized promotion"),
        (lambda s: s.update(authority_transfer=None), "unauthorized promotion"),
        (lambda s: s.update(runs=[]), "no native runs"),
        (lambda s: s.update(runs="x"), "no native runs"),
        (lambda s: s.update(runs=["x"]), "invalid native run entry"),
        (lambda s: s["runs"][0].update(run_id=0), "positive integers"),
        (lambda s: s["runs"][0].update(attempt="1"), "positive integers"),
        (lambda s: s["runs"].append(run()), "duplicate run/attempt"),
        (lambda s: s["runs"][0].update(source_sha=OTHER), "cross-SHA"),
        (lambda s: s["runs"][0].update(status="weird"), "bad run status"),
        (lambda s: s["runs"][0].update(conclusion="meh"), "terminal status"),
        (
            lambda s: s["runs"][0].update(status="queued"),
            "terminal status/conclusion mismatch",
        ),
        (lambda s: s["runs"][0].update(jobs={}), "jobs list required"),
        (lambda s: s["runs"][0]["jobs"][0].update(job_id=-1), "malformed job id"),
        (
            lambda s: s["runs"][0]["jobs"].append(job(1)),
            "duplicate/malformed job id",
        ),
        (
            lambda s: s["runs"][0]["jobs"][0].update(source_sha=OTHER),
            "wrong source SHA",
        ),
        (
            lambda s: s["runs"][0]["jobs"][0].update(status="waiting"),
            "malformed job status",
        ),
        (
            lambda s: s["runs"][0]["jobs"][0].update(conclusion="x"),
            "malformed job outcome",
        ),
        (
            lambda s: s["runs"][0]["jobs"][0].update(created_at="bad"),
            "UTC Z",
        ),
        (
            lambda s: s["runs"][0]["jobs"][0].update(
                status="in_progress", conclusion=None
            ),
            "nonterminal job completed",
        ),
        (
            lambda s: s["runs"][0]["jobs"][0].update(started_at="2025-12-31T00:00:00Z"),
            "negative queue clock",
        ),
        (
            lambda s: s["runs"][0]["jobs"][0].update(
                completed_at="2026-01-01T00:00:05Z"
            ),
            "negative runtime clock",
        ),
    ],
)
def test_validate_rejections(mutate, msg):
    s = snap()
    mutate(s)
    with pytest.raises(ValueError, match=msg):
        cs.validate(s)


def test_validate_accepts_nonterminal_and_sparse_job_timestamps():
    s = snap(
        runs=[
            run(
                status="in_progress",
                conclusion=None,
                jobs=[
                    job(
                        1,
                        status="queued",
                        conclusion=None,
                        started_at=None,
                        completed_at=None,
                    )
                ],
            ),
            run(2, jobs=[]),
        ],
        source_clock="CURRENT_MAIN",
    )
    assert len(cs.validate(s)) == 2


def test_pctile():
    assert cs.pctile([], 0.5) is None
    assert cs.pctile([5], 0.95) == 5
    assert cs.pctile([1, 2, 3, 4], 0.5) == 2.5
    assert cs.pctile([10, 0], 0.95) == 9.5


def test_stats_counts_and_percentiles():
    runs = [
        run(1, jobs=[job(1), job(2, conclusion="failure")]),
        run(2, conclusion="failure", jobs=[]),
        run(
            3,
            status="queued",
            conclusion=None,
            jobs=[
                job(
                    3,
                    status="queued",
                    conclusion=None,
                    started_at=None,
                    completed_at=None,
                )
            ],
        ),
    ]
    st = cs.stats(snap(runs=runs))
    assert st["observed"] == 3
    assert st["terminal"] == 2
    assert st["success"] == 1
    assert st["failed"] == 1
    assert st["nonterminal"] == 1
    assert st["success_observed_pct"] == round(100 / 3, 4)
    assert st["terminal_success_pct"] == 50.0
    assert st["jobs_observed"] == 3
    assert st["failed_jobs"] == 1
    assert st["queue_p50_seconds"] == 10.0
    assert st["queue_sample_n"] == 2
    assert st["runtime_p95_seconds"] == 60.0
    assert st["runtime_sample_n"] == 2
    assert st["statistical_control"] is None


def test_stats_no_terminal_runs():
    st = cs.stats(snap(runs=[run(status="pending", conclusion=None, jobs=[])]))
    assert st["terminal_success_pct"] is None
    assert st["queue_p50_seconds"] is None


def test_production_defect_stats_keyerror_on_job_without_conclusion():
    """validate() accepts a queued job with no 'conclusion'; stats() indexes it."""
    # production_defect (see WAVE_LEDGER.jsonl): this test pins the current
    # broken behaviour, so it fails once the defect is fixed. The repo's
    # test-evidence ratchet allows no xfails, hence no xfail marker.
    j = job(1, status="queued", started_at=None, completed_at=None)
    del j["conclusion"]
    s = snap(runs=[run(status="queued", conclusion=None, jobs=[j])])
    cs.validate(s)
    with pytest.raises(KeyError, match="conclusion"):
        cs.stats(s)


def test_compare_comparable_delta():
    before = snap(
        runs=[
            run(1, status="in_progress", conclusion=None, jobs=[]),
            run(2, jobs=[job(5)]),
            run(3, status="queued", conclusion=None, jobs=[]),
        ]
    )
    after = copy.deepcopy(before)
    after["observed_at_utc"] = "2026-01-01T02:00:00Z"
    after["runs"][0].update(status="completed", conclusion="success")
    after["runs"][2].update(status="completed", conclusion="failure")
    res = cs.compare(before, after)
    assert res["comparable"] is True
    assert res["reasons"] == []
    assert res["successful_run_delta"] == 1
    assert res["blocked_to_success_run_ids"] == [1]
    assert res["regressed_success_run_ids"] == []
    assert res["job_first_red_cleared"] == []
    assert res["job_first_red_qualification"].startswith("NOT_A_CROSS")
    assert res["authority_transfer"] is False


def test_compare_noncomparable_reasons():
    before = snap(runs=[run(1, jobs=[job(1)]), run(2)])
    after = snap(
        runs=[
            run(1, conclusion="failure", jobs=[job(1, conclusion="failure")]),
            run(4),
        ],
        observed="2026-01-01T00:00:00Z",
        source_clock="CURRENT_MAIN",
    )
    res = cs.compare(before, after)
    assert res["comparable"] is False
    assert res["reasons"] == [
        "DIFFERENT_SOURCE_OR_SELECTION_CONTEXT",
        "IMMUTABLE_JOB_TERMINAL_CHANGED",
        "IMMUTABLE_RUN_TERMINAL_CHANGED",
        "NONMONOTONE_OBSERVATION_TIME",
        "RUN_ATTEMPT_POPULATION_CHANGED",
    ]
    assert res["successful_run_delta"] is None
    assert "job_first_red_qualification" not in res


def test_compare_job_timestamp_change_is_immutable_violation():
    before = snap()
    after = snap(
        runs=[run(jobs=[job(completed_at="2026-01-01T00:02:00Z")])],
        observed="2026-01-01T03:00:00Z",
    )
    res = cs.compare(before, after)
    assert res["reasons"] == ["IMMUTABLE_JOB_TERMINAL_CHANGED"]


def test_compare_run_back_to_nonterminal():
    before = snap(runs=[run(jobs=[])])
    after = snap(
        runs=[run(status="in_progress", conclusion=None, jobs=[])],
        observed="2026-01-01T03:00:00Z",
    )
    assert cs.compare(before, after)["reasons"] == ["IMMUTABLE_RUN_TERMINAL_CHANGED"]


def test_main_writes_output(tmp_path, capsys):
    b = tmp_path / "b.json"
    a = tmp_path / "a.json"
    out = tmp_path / "out.json"
    b.write_text(json.dumps(snap()), encoding="utf-8")
    a.write_text(json.dumps(snap(observed="2026-01-01T05:00:00Z")), encoding="utf-8")
    cs.main(["--before", str(b), "--after", str(a), "--out", str(out)])
    printed = json.loads(capsys.readouterr().out)
    assert printed == {"comparable": True, "reasons": [], "delta": 0}
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["schema"] == "codepurple.g3cs.native-run-delta.v1"
