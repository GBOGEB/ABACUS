"""Positive, negative and identity/clock regression tests for native W11 scout."""

from copy import deepcopy

import pytest

from scripts import cbd_eoss_ci_triage as m

SHA = "a" * 40


def fixture():
    return {
        "schema": m.SCHEMA,
        "repository": "GBOGEB/ABACUS",
        "head_sha": SHA,
        "run_id": 10000,
        "run_attempt": 1,
        "readback_scope": "LATEST_ATTEMPT_FIRST_PAGE",
        "authority": {
            "admission": "HOLD",
            "security_waiver": False,
            "authority_transfer": False,
        },
        "jobs": [
            {
                "job_id": 1,
                "name": "Python 3.10",
                "head_sha": SHA,
                "run_attempt": 1,
                "conclusion": "failure",
                "first_failed_step": "Install tooling",
                "created_at": "2026-10-17T11:00:00Z",
                "started_at": "2026-10-17T11:00:05Z",
                "completed_at": "2026-10-17T11:00:18Z",
            },
            {
                "job_id": 2,
                "name": "Python proof completeness",
                "head_sha": SHA,
                "run_attempt": 1,
                "conclusion": "failure",
                "first_failed_step": "Audit executed and classified-skipped proof roles",
                "created_at": "2026-10-17T11:00:00Z",
                "started_at": "2026-10-17T11:00:02Z",
                "completed_at": "2026-10-17T11:00:10Z",
            },
            {
                "job_id": 3,
                "name": "optional canary",
                "head_sha": SHA,
                "run_attempt": 1,
                "conclusion": "skipped",
                "first_failed_step": None,
                "created_at": "2026-10-17T11:00:00Z",
                "started_at": "2026-10-17T11:00:00Z",
                "completed_at": "2026-10-17T10:59:59Z",
            },
        ],
    }


def test_native_issuer_identity_and_candidates():
    r = m.project(fixture())
    assert r["jobs_observed"] == 3 and r["failed_job_count"] == 2
    assert r["job_queue_seconds"] == [5.0, 2.0]
    assert r["job_execution_seconds"] == [13.0, 8.0]
    assert r["censored_or_partial_clock_observations"] == 1
    assert (
        r["failed_job_step_candidates"][0]["candidate_family"]
        == "DEPENDENCY_INSTALL_CANDIDATE"
    )
    assert (
        r["failed_job_step_candidates"][1]["candidate_family"]
        == "DOWNSTREAM_GATE_CANDIDATE"
    )
    assert r["accepted_causal_roots"] is None
    assert r["matched_main_coverage_delta"] is None
    assert r["github_speedup"] is None
    assert r["authority"]["admission"] == "HOLD"


@pytest.mark.parametrize(
    "bad",
    [
        lambda x: x.update(schema="wrong"),
        lambda x: x.update(repository="GBOGEB/CODEX"),
        lambda x: x.update(head_sha="not a SHA"),
        lambda x: x.update(run_id=True),
        lambda x: x.update(run_attempt=0),
        lambda x: x.update(jobs=[]),
        lambda x: x.update(readback_scope="ALL_ATTEMPTS"),
        lambda x: x["authority"].update(admission="PASS"),
        lambda x: x["authority"].update(security_waiver=True),
        lambda x: x["jobs"][1].update(job_id=1),
        lambda x: x["jobs"][0].update(run_attempt=2),
        lambda x: x["jobs"][0].update(head_sha="b" * 40),
        lambda x: x["jobs"][0].update(conclusion="unspecified"),
        lambda x: x["jobs"][2].update(first_failed_step="pretend step"),
        lambda x: x["jobs"][0].update(created_at="not-a-dateZ"),
        lambda x: x["jobs"][0].update(created_at="2026-10-17T11:00:00+01:00"),
        lambda x: x["jobs"][0].update(name=""),
        lambda x: x["jobs"][0].update(first_failed_step=""),
    ],
)
def test_bad_evidence_fails_closed(bad):
    d = fixture()
    bad(d)
    with pytest.raises(ValueError):
        m.project(d)


@pytest.mark.parametrize(
    "name,step,family",
    [
        ("Install", "Install canonical dependencies", "DEPENDENCY_INSTALL_CANDIDATE"),
        ("Pytest", "collect tests", "TEST_COLLECTION_CANDIDATE"),
        ("Code Coverage", "Run tests", "COVERAGE_CANDIDATE"),
        ("Bandit", "Scan", "SECURITY_CANDIDATE"),
        ("policy-and-inventory", "Fail closed", "GOVERNANCE_CANDIDATE"),
        ("Full Red Proof Summary", "Emit summary", "DOWNSTREAM_GATE_CANDIDATE"),
        ("mystery", "unknown", "UNCLASSIFIED_FIRST_STEP"),
    ],
)
def test_candidate_family_not_causes(name, step, family):
    assert m.classify(name, step) == family


def test_missing_clock_stays_censored_and_nullable():
    d = fixture()
    for j in d["jobs"][:2]:
        j["created_at"] = j["started_at"] = j["completed_at"] = None
    r = m.project(d)
    assert r["job_execution_samples"] == 0 and r["job_queue_samples"] == 0
    assert r["censored_or_partial_clock_observations"] >= 4


def test_nonterminal_job_is_not_falsely_completed():
    d = fixture()
    d["jobs"][0].update(conclusion=None, first_failed_step=None, completed_at=None)
    r = m.project(d)
    assert r["nonterminal_jobs"] == 1
    assert r["failed_job_count"] == 1


def test_first_red_missing_preserves_unknown_step():
    d = fixture()
    d["jobs"][0]["first_failed_step"] = None
    r = m.project(d)
    assert r["failed_job_count"] == 2 and r["first_failed_step_known"] == 1


def test_boolean_job_id_never_coerces_to_integer():
    d = fixture()
    d["jobs"][0]["job_id"] = True
    with pytest.raises(ValueError):
        m.project(d)
