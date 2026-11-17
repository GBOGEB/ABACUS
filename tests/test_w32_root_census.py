"""W32 source-owned root/manifestation negative and reverse tests."""

from __future__ import annotations

import copy

import pytest

from tools.recovery import w32_root_census as census

HEAD = "a" * 40


def job(
    n,
    *,
    status="completed",
    conclusion="failure",
    root="MATPLOTLIB",
    family="python310",
    sha=HEAD,
):
    return {
        "run_id": 39100000000 + n,
        "attempt": 1,
        "job_id": 117000000000 + n,
        "status": status,
        "conclusion": conclusion,
        "root_id": root,
        "source_family": family,
        "head_sha": sha,
    }


def sample():
    return {
        "exact_head": HEAD,
        "jobs": [
            job(1),
            job(2, family="windows310"),
            job(3, root="SAFETY"),
            job(4, conclusion="success", root=None),
            job(5, status="queued", conclusion=None, root=None),
        ],
        "previous_root_ids": ["MATPLOTLIB", "SAFETY", "OLD_ROOT"],
    }


def test_two_shared_failures_are_one_root():
    value = census.summarize(sample())
    assert value["job_identities"] == 5
    assert value["failed_jobs"] == 3
    assert value["root_count"] == 2
    assert value["root_manifestations"] == 3
    assert value["root_amplification"] == 1.5
    assert value["roots"]["MATPLOTLIB"]["manifestations"] == 2
    assert len(value["roots"]["MATPLOTLIB"]["source_families"]) == 2
    assert value["formal_roots_closed"] is None
    assert value["merge_admission"] == "HOLD"


def test_nonobserved_prior_root_is_not_closed():
    receipt = census.summarize(sample())
    assert receipt["prior_roots_not_observed_here"] == ["OLD_ROOT"]
    assert receipt["formal_roots_closed"] is None


def test_nonterminal_is_not_failed_or_success():
    receipt = census.summarize(sample())
    assert receipt["nonterminal"] == 1
    assert receipt["successful_jobs"] == 1
    assert receipt["terminal"] == 4


def test_no_failed_jobs_not_automatically_formal_closure():
    receipt = census.summarize(
        {
            "exact_head": HEAD,
            "jobs": [
                job(1, conclusion="success", root=None),
            ],
            "previous_root_ids": ["SAFETY"],
        }
    )
    assert receipt["root_count"] == 0
    assert receipt["root_amplification"] is None
    assert receipt["formal_roots_closed"] is None


def test_unclassified_first_red_is_unknown_not_zero():
    data = sample()
    data["jobs"][0]["root_id"] = None
    receipt = census.summarize(data)
    assert receipt["unknown_first_red_count"] == 1
    assert receipt["failed_jobs"] == 3
    assert receipt["root_count"] == 2


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("head_sha", "b" * 40, "cross-head"),
        ("run_id", 0, "invalid run"),
        ("attempt", 0, "invalid run"),
        ("job_id", True, "invalid run"),
        ("source_family", "", "source family"),
        ("status", "mystery", "unknown job"),
        ("conclusion", None, "terminal job"),
        ("root_id", "", "malformed root"),
    ],
)
def test_bad_native_record_fails_closed(field, value, reason):
    data = sample()
    data["jobs"][0][field] = value
    with pytest.raises(ValueError, match=reason):
        census.summarize(data)


def test_duplicate_job_identity_rejected():
    data = sample()
    data["jobs"].append(copy.deepcopy(data["jobs"][0]))
    with pytest.raises(ValueError, match="duplicate run"):
        census.summarize(data)


def test_distinct_attempt_not_deduplicated_as_one_job():
    data = sample()
    copy_job = copy.deepcopy(data["jobs"][0])
    copy_job["attempt"] = 2
    data["jobs"].append(copy_job)
    receipt = census.summarize(data)
    assert receipt["job_identities"] == 6
    assert receipt["roots"]["MATPLOTLIB"]["manifestations"] == 3


def test_success_with_root_claim_rejected():
    data = sample()
    data["jobs"][3]["root_id"] = "FALSE_CLOSURE"
    with pytest.raises(ValueError, match="root claimed"):
        census.summarize(data)


def test_nonterminal_with_false_success_rejected():
    data = sample()
    data["jobs"][4]["conclusion"] = "success"
    with pytest.raises(ValueError, match="nonterminal conclusion"):
        census.summarize(data)


def test_unknown_prior_population_rejected():
    data = sample()
    data["previous_root_ids"] = None
    with pytest.raises(ValueError, match="prior"):
        census.summarize(data)


def test_duplicate_prior_roots_rejected():
    data = sample()
    data["previous_root_ids"].append("SAFETY")
    with pytest.raises(ValueError, match="duplicate prior"):
        census.summarize(data)


def test_invalid_sha_rejected():
    with pytest.raises(ValueError, match="invalid exact"):
        census.summarize({"exact_head": "a" * 39, "jobs": []})


def test_timed_out_job_is_a_failed_manifestation():
    j = job(1, conclusion="timed_out", root="TIMEOUT")
    out = census.summarize({"exact_head": HEAD, "jobs": [j]})
    assert out["failed_jobs"] == 1
    assert out["roots"]["TIMEOUT"]["manifestations"] == 1
