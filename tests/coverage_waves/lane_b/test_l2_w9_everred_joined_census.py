"""Lane-B wave 9: everred_v3 joined_census exact-source native join."""

import types

import pytest

from ._l2_loader import load

fake_fcntl = types.SimpleNamespace(LOCK_EX=2, LOCK_UN=8, flock=lambda fd, op: None)
mt = load("tools/everred_v3/src/metrics.py")
ev = load("tools/everred_v3/src/everred.py", deps={"fcntl": fake_fcntl, "metrics": mt})
jc = load("tools/everred_v3/src/joined_census.py", deps={"everred": ev})

A, B = "a" * 40, "b" * 40
REPO = "GBOGEB/ABACUS"


def _bound(kind, eid, repo=REPO, sha=A, run=10, job=None, provenance="observed", **ev_):
    binding = {"repository": repo, "source_sha": sha, "run_id": run}
    if job is not None:
        binding["job_id"] = job
    evidence = {"source_binding": binding}
    evidence.update(ev_)
    return {
        "kind": kind,
        "id": eid,
        "repo": repo,
        "sha": sha,
        "provenance": provenance,
        "evidence": evidence,
    }


def test_join_empty_and_skipped_events():
    out = jc.join(
        [
            {"kind": "repair", "evidence": {"source_binding": {}}},
            {"kind": "note"},
            {"kind": "note", "evidence": {"source_binding": "x"}},
        ]
    )
    assert out == {
        "schema": "abacus.everred.joined.native.v1",
        "run_groups": [],
        "run_group_count": 0,
        "source_bound_events": 0,
        "global_merge_admission": "HOLD",
        "evidence_integrity": "EXACT_SCOPE_JOIN_ONLY",
        "security_waiver": False,
        "authority_transfer": False,
        "note": "Raw native events cannot certify root causality, live worker count or merge admission.",
    }


def test_join_groups_every_producer():
    events = [
        _bound(
            "verification",
            "v-2",
            job=7,
            status="completed",
            conclusion="failure",
            name="tests",
        ),
        _bound("verification", "v-1", job=3),
        _bound("occurrence", "o-2", job=7),
        _bound("occurrence", "o-1", provenance="manual"),
        _bound(
            "security_census",
            "s-1",
            scanner="Bandit",
            raw_findings=4,
            unique_findings=3,
            config_digest="d",
            fingerprints=["f1", "f2"],
        ),
        _bound("security_census", "s-0", scanner="Bandit"),
        _bound("security_census", "s-x", scanner="Semgrep"),
        _bound(
            "coverage",
            "c-1",
            scope="broad",
            unit="lines",
            covered=1,
            eligible=2,
            config_id="cfg",
        ),
        _bound(
            "runtime",
            "r-1",
            backend="rhel",
            reported_complete=True,
            runtime_trust="LOW",
        ),
        _bound(
            "note",
            "n-1",
            provenance="historical_source",
            producer_schema="bd.ldab.joined.census.v1",
            producer_sha256="ps",
            bandit_fingerprint_observations=9,
            join_groups=["g"],
        ),
        _bound("note", "n-2", producer_schema="other"),
        _bound("note", "n-other-run", run=11),
        _bound("note", "n-other-sha", sha=B),
    ]
    out = jc.join(events)
    assert out["run_group_count"] == 3
    assert out["source_bound_events"] == 13
    keys = [(g["repo"], g["sha"], g["run_id"]) for g in out["run_groups"]]
    assert keys == [(REPO, A, 10), (REPO, A, 11), (REPO, B, 10)]
    g = out["run_groups"][0]
    assert g["job_ids"] == [3, 7]
    assert g["job_count"] == 2
    assert g["events"] == sorted(g["events"]) and len(g["events"]) == 11
    assert g["first_red"] == ["o-1", "o-2"]
    assert g["first_red_count"] == 2
    assert g["unverified_entries"] == 2
    assert g["bandit"] == [
        {
            "event_id": "s-0",
            "raw_findings": None,
            "unique_findings": None,
            "config_digest": None,
            "fingerprint_count": None,
        },
        {
            "event_id": "s-1",
            "raw_findings": 4,
            "unique_findings": 3,
            "config_digest": "d",
            "fingerprint_count": 2,
        },
    ]
    assert g["bd_ldab"] == [
        {
            "event_id": "n-1",
            "source_digest": "ps",
            "fingerprint_observations": 9,
            "join_groups": ["g"],
            "root_causality": "UNCONFIRMED",
            "trust": "MANUAL_UNVERIFIED",
        }
    ]
    assert g["coverage"] == [
        {
            "event_id": "c-1",
            "scope": "broad",
            "unit": "lines",
            "covered": 1,
            "eligible": 2,
            "config_id": "cfg",
        }
    ]
    assert g["runtime"] == [
        {
            "event_id": "r-1",
            "backend": "rhel",
            "reported_complete": True,
            "trust": "LOW",
        }
    ]
    assert g["verification"] == [
        {"event_id": "v-1", "status": None, "conclusion": None, "job_name": None},
        {
            "event_id": "v-2",
            "status": "completed",
            "conclusion": "failure",
            "job_name": "tests",
        },
    ]
    assert g["confirmed_unique_roots"] is None
    assert g["worker_sessions_verified"] is None
    assert g["security_burndown"] is None
    other = out["run_groups"][1]
    assert other["job_ids"] == [] and other["job_count"] == 0
    assert other["unverified_entries"] == 0


def _with_binding(**binding):
    e = _bound("note", "n-1")
    e["evidence"]["source_binding"].update(binding)
    return e


@pytest.mark.parametrize(
    "event,message",
    [
        (_with_binding(repository=5), "invalid native join identity"),
        (_with_binding(source_sha="A" * 40), "invalid native join identity"),
        (_with_binding(run_id="10"), "invalid native join identity"),
        (_with_binding(run_id=True), "invalid native join identity"),
        (_with_binding(run_id=0), "invalid native join identity"),
        (_with_binding(job_id="3"), "invalid native join identity"),
        (_with_binding(job_id=0), "invalid native join identity"),
        (_with_binding(job_id=-1), "invalid native join identity"),
        (_with_binding(repository="GBOGEB/OTHER"), "native source/census mismatch"),
        (_with_binding(source_sha=B), "native source/census mismatch"),
    ],
)
def test_join_rejections(event, message):
    with pytest.raises(ev.InvalidEvidence, match=message):
        jc.join([event])


def test_join_rejects_duplicate_identity():
    with pytest.raises(ev.InvalidEvidence, match="duplicate joined event identity"):
        jc.join([_bound("note", "n-1"), _bound("coverage", "n-1")])


def test_join_reuses_everred_symbols():
    assert jc.InvalidEvidence is ev.InvalidEvidence
    assert jc.valid_sha is ev.valid_sha
