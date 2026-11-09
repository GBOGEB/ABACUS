"""Lane-B wave 9: everred_v3 metrics (provable KPIs, UNKNOWN stays null)."""

import copy

import pytest

from ._l2_loader import load

m = load("tools/everred_v3/src/metrics.py")

A, B, C = "a" * 40, "b" * 40, "c" * 40
REPO = "GBOGEB/ABACUS"


def _sec(sha, fingerprints, **overrides):
    evidence = {
        "scanner": "codeql",
        "scope": "repo",
        "config_digest": "d1",
        "scanner_version": "2.0",
        "rule_profile": "default",
        "normalization_version": "v1",
        "fingerprints": fingerprints,
    }
    evidence.update(overrides)
    return {"kind": "security_census", "sha": sha, "evidence": evidence}


def _cov(sha, covered, eligible, **overrides):
    evidence = {
        "scope": "repo",
        "unit": "line",
        "config_id": "cfg",
        "test_selection": "all",
        "exclusions": "none",
        "tool_version": "7.0",
        "covered": covered,
        "eligible": eligible,
    }
    evidence.update(overrides)
    return {"kind": "coverage", "sha": sha, "evidence": evidence}


def _consumer(cid="c1", repo=REPO, head=A):
    return {"consumer_id": cid, "repository": repo, "head_sha": head}


def _replay(root="R1", cid="c1", repo=REPO, sha=A, **overrides):
    evidence = {
        "consumer_id": cid,
        "source_binding": {
            "repository": repo,
            "source_sha": sha,
            "run_id": 10,
            "job_id": 20,
        },
        "proof_type": "NATIVE_EXACT_HEAD_CI",
        "status": "PASS",
        "job_status": "completed",
        "job_conclusion": "success",
    }
    evidence.update(overrides)
    return {
        "kind": "replay",
        "provenance": "observed",
        "root_id": root,
        "repo": repo,
        "sha": sha,
        "evidence": evidence,
    }


def _with(event, **top):
    out = copy.deepcopy(event)
    out.update(top)
    return out


def _bad_binding(**kw):
    ev = _replay()
    ev["evidence"]["source_binding"].update(kw)
    return ev


# --- rate -------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "n,d,expected",
    [
        (1, 3, 33.33),
        (0, 5, 0.0),
        (5, 5, 100.0),
        (1, 0, None),
        (6, 5, None),
        (-1, 5, None),
        (True, 5, None),
        (1, 2.0, None),
        (None, 2, None),
    ],
)
def test_rate(n, d, expected):
    assert m.rate(n, d) == expected


# --- comparable_security ----------------------------------------------------------------------


def test_comparable_security_happy_path():
    out = m.comparable_security(_sec(A, ["x", "y"]), _sec(B, ["y", "z", "w"]))
    assert out == {
        "scanner": "codeql",
        "config_digest": "d1",
        "before_sha": A,
        "after_sha": B,
        "before": 2,
        "after": 3,
        "opened": 2,
        "resolved": 1,
        "persisting": 1,
        "net_change": 1,
        "opened_ids": ["w", "z"],
        "resolved_ids": ["x"],
    }


def test_comparable_security_missing_evidence_is_none():
    assert m.comparable_security({"sha": A}, {"sha": B}) is None


@pytest.mark.parametrize(
    "before,after",
    [
        (_sec("", ["x"]), _sec(B, ["x"])),
        (_sec(A, ["x"]), _sec(None, ["x"])),
        (_sec(A, ["x"]), _sec(A, ["x"])),
        (_sec(A, ["x"], scanner=1), _sec(B, ["x"], scanner=1)),
        (_sec(A, ["x"], scope=""), _sec(B, ["x"], scope="")),
        (
            _sec(A, ["x"], rule_profile="UNKNOWN"),
            _sec(B, ["x"], rule_profile="UNKNOWN"),
        ),
        (_sec(A, ["x"]), _sec(B, ["x"], scanner_version="3.0")),
        (_sec(A, "x"), _sec(B, ["x"])),
        (_sec(A, ["x"]), _sec(B, None)),
        (_sec(A, ["x", ""]), _sec(B, ["x"])),
        (_sec(A, ["x", 3]), _sec(B, ["x"])),
        (_sec(A, ["x", "x"]), _sec(B, ["x"])),
        (_sec(A, ["x"]), _sec(B, ["y", "y"])),
    ],
)
def test_comparable_security_rejections(before, after):
    assert m.comparable_security(before, after) is None


# --- comparable_coverage ----------------------------------------------------------------------


def test_comparable_coverage_happy_path():
    out = m.comparable_coverage(_cov(A, 50, 100), _cov(B, 2, 3))
    assert out == {
        "scope": "repo",
        "unit": "line",
        "before_sha": A,
        "after_sha": B,
        "before_rate": 50.0,
        "after_rate": 66.67,
        "delta_percentage_points": 16.67,
        "before": {"covered": 50, "eligible": 100},
        "after": {"covered": 2, "eligible": 3},
    }


def test_comparable_coverage_missing_evidence_is_none():
    assert m.comparable_coverage({"sha": A}, {"sha": B}) is None


@pytest.mark.parametrize(
    "before,after",
    [
        (_cov(A, 1, 2, unit=None), _cov(B, 1, 2, unit=None)),
        (_cov(A, 1, 2, scope=""), _cov(B, 1, 2, scope="")),
        (
            _cov(A, 1, 2, tool_version="UNKNOWN"),
            _cov(B, 1, 2, tool_version="UNKNOWN"),
        ),
        (_cov(A, 1, 2), _cov(B, 1, 2, exclusions="other")),
        (_cov(A, 1, 2), _cov(A, 1, 2)),
        (_cov("", 1, 2), _cov(B, 1, 2)),
        (_cov(A, 1, 2), _cov(None, 1, 2)),
        (_cov(A, 3, 2), _cov(B, 1, 2)),
        (_cov(A, 1, 2), _cov(B, 1, 0)),
    ],
)
def test_comparable_coverage_rejections(before, after):
    assert m.comparable_coverage(before, after) is None


# --- compute_metrics --------------------------------------------------------------------------


def test_compute_metrics_empty_is_all_unknown():
    out = m.compute_metrics([], {})
    assert out["occurrence_amplification"] is None
    assert out["consumer_replay_coverage_pct"] is None
    assert out["recurrence_rate_pct"] is None
    assert out["queue_wait_mean_seconds"] is None
    assert out["security_comparable_pairs"] == []
    assert out["coverage_comparable_pairs"] == []
    assert out["known_consumer_denominator"] is None
    assert out["queue_wait_samples"] == 0
    assert "null" in out["method"]


def test_compute_metrics_pairs_only_comparable_ones():
    events = [
        _sec(A, ["x"]),
        _sec(B, ["x", "y"]),
        _sec(C, ["x"], scanner="other"),
        _cov(A, 1, 2),
        _cov(B, 2, 2),
        _cov(C, 1, 0),
    ]
    out = m.compute_metrics(events, {})
    sec = [(p["before_sha"], p["after_sha"]) for p in out["security_comparable_pairs"]]
    cov = [(p["before_sha"], p["after_sha"]) for p in out["coverage_comparable_pairs"]]
    assert sec == [(A, B)]
    assert cov == [(A, B)]


def test_compute_metrics_full_replay_and_amplification():
    roots = {
        "R1": {"state": "CONFIRMED", "applicable_consumers": [_consumer("c1")]},
        "R2": {
            "state": "CONFIRMED",
            "applicable_consumers": [_consumer("c2", head=B)],
        },
        "R3": {"state": "CANDIDATE"},
    }
    events = [
        {"kind": "occurrence", "root_id": "R1"},
        {"kind": "occurrence", "root_id": "R1"},
        {"kind": "occurrence", "root_id": "R2"},
        {"kind": "occurrence", "root_id": "R3"},
        {"kind": "occurrence"},
        _replay("R1", "c1"),
        _replay("R2", "c2", sha=B, status="FAIL"),
    ]
    out = m.compute_metrics(events, roots)
    assert out["occurrence_amplification"] == 1.5
    assert out["known_consumer_denominator"] == 2
    assert out["consumer_replay_coverage_pct"] == 50.0


@pytest.mark.parametrize(
    "event",
    [
        {"kind": "occurrence", "root_id": "R1"},
        _with(_replay(), provenance="imported"),
        _with(_replay(), evidence="not-a-dict"),
        _replay(cid="unknown"),
        _replay(root="R9"),
        _replay(source_binding="flat"),
        _with(_replay(), repo="other/repo"),
        _with(_replay(), sha=B),
        _bad_binding(repository="other/repo"),
        _bad_binding(source_sha=B),
        _bad_binding(run_id=True),
        _bad_binding(run_id=0),
        _bad_binding(job_id="20"),
        _bad_binding(job_id=-1),
        _replay(proof_type="MERGE_TREE_PREVIEW"),
        _replay(status="UNKNOWN"),
        _replay(job_status="in_progress"),
        _replay(job_conclusion="failure"),
    ],
)
def test_compute_metrics_replay_without_credit(event):
    roots = {"R1": {"state": "CONFIRMED", "applicable_consumers": [_consumer()]}}
    out = m.compute_metrics([event], roots)
    assert out["known_consumer_denominator"] == 1
    assert out["consumer_replay_coverage_pct"] == 0.0


def test_compute_metrics_replay_without_evidence_key_uses_default():
    roots = {"R1": {"state": "CONFIRMED", "applicable_consumers": [_consumer()]}}
    event = _replay()
    del event["evidence"]
    assert m.compute_metrics([event], roots)["consumer_replay_coverage_pct"] == 0.0


@pytest.mark.parametrize(
    "consumers",
    [
        None,
        "c1",
        [_consumer(), "not-a-dict"],
        [_consumer(), _consumer("")],
        [_consumer(), {"consumer_id": 7, "repository": REPO, "head_sha": A}],
        [_consumer(), _consumer("c2", repo="")],
        [_consumer(), {"consumer_id": "c2", "repository": 1, "head_sha": A}],
        [_consumer(), {"consumer_id": "c2", "repository": REPO}],
        [_consumer(), _consumer("c2", head="A" * 40)],
        [_consumer(), _consumer("c2", head="a" * 39)],
        [_consumer(), _consumer()],
    ],
)
def test_compute_metrics_incomplete_registry_stays_null(consumers):
    root = {"state": "CONFIRMED"}
    if consumers is not None:
        root["applicable_consumers"] = copy.deepcopy(consumers)
    out = m.compute_metrics([_replay()], {"R1": root})
    assert out["consumer_replay_coverage_pct"] is None
    assert out["known_consumer_denominator"] is None
    assert out["occurrence_amplification"] == 0.0


def test_compute_metrics_confirmed_root_with_no_consumers_is_null():
    roots = {"R1": {"state": "CONFIRMED", "applicable_consumers": []}}
    out = m.compute_metrics([], roots)
    assert out["consumer_replay_coverage_pct"] is None
    assert out["known_consumer_denominator"] is None


def test_compute_metrics_recurrence_rate():
    events = [
        {"kind": "closure", "root_id": "R1", "evidence": {"state": "CLOSED"}},
        {"kind": "closure", "root_id": "R2", "evidence": {"state": "CLOSED"}},
        {"kind": "closure", "root_id": "R3", "evidence": {"state": "OPEN"}},
        {"kind": "closure", "root_id": "", "evidence": {"state": "CLOSED"}},
        {"kind": "closure", "root_id": "R4"},
        {"kind": "recurrence", "root_id": "R1"},
        {"kind": "recurrence", "root_id": "R3"},
    ]
    assert m.compute_metrics(events, {})["recurrence_rate_pct"] == 50.0


def _rt(**evidence):
    return {"kind": "runtime", "evidence": evidence}


def test_compute_metrics_queue_wait():
    t0, t10 = "2026-01-01T00:00:00", "2026-01-01T00:00:10"
    events = [
        _rt(dispatched_at=t0 + "Z", started_at=t10 + "Z"),
        _rt(dispatched_at=t0 + "+00:00", started_at="2026-01-01T00:00:05+00:00"),
        _rt(dispatched_at=t10 + "Z", started_at=t0 + "Z"),
        _rt(dispatched_at="not-a-time", started_at=t0 + "Z"),
        _rt(dispatched_at=t0, started_at=t10 + "Z"),
        _rt(dispatched_at=1, started_at=t0 + "Z"),
        _rt(dispatched_at=t0 + "Z"),
        {"kind": "occurrence"},
    ]
    out = m.compute_metrics(events, {})
    assert out["queue_wait_samples"] == 2
    assert out["queue_wait_mean_seconds"] == 7.5


def test_compute_metrics_requires_kind_key():
    with pytest.raises(KeyError):
        m.compute_metrics([{"sha": A}], {})
