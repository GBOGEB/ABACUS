"""Lane-B wave 8: everred_v3 top21_rollout census."""

import copy

import pytest

from ._l2_loader import load

tr = load("tools/everred_v3/src/top21_rollout.py")

A, B = "a" * 40, "b" * 40
REPOS = ["GBOGEB/CODEX", "GBOGEB/ABACUS", "GBOGEB/gg_MATH"]


def _contract(**overrides):
    contract = {
        "schema_version": "1.0.0",
        "security_waiver": False,
        "authority": {
            "authority_transfer": False,
            "formal_credit_delta": 0,
            "engineering_credit_delta": 0,
        },
        "rollout": {
            "repository_candidates": list(REPOS),
            "top21_definition": "top roots by unblock",
        },
    }
    contract.update(overrides)
    return contract


def _url(repo="GBOGEB/ABACUS", run=5, job=6, tail=None):
    suffix = f"/job/{job}" if tail is None else tail
    return f"https://github.com/{repo}/actions/runs/{run}{suffix}"


def _coverage(**overrides):
    measurement = {
        "scope": "focused",
        "unit": "statements",
        "covered": 3,
        "eligible": 4,
        "config_digest": "c" * 64,
        "tool_version": "7.13.3",
        "test_selection": "lane_b",
    }
    measurement.update(overrides)
    return measurement


def _receipt(kind="CI", repo="GBOGEB/ABACUS", sha=A, run=5, job=6, **extra):
    receipt = {
        "repository": repo,
        "source_sha": sha,
        "run_id": run,
        "job_id": job,
        "evidence_url": _url(repo, run, job),
        "kind": kind,
    }
    if kind == "COVERAGE":
        receipt.update(measurement=_coverage(), artifact_sha256="d" * 64)
    receipt.update(extra)
    return receipt


def _receipts(*items):
    return {"schema": tr.RECEIPT_SCHEMA, "items": list(items)}


def _ranking(*items):
    return {"schema": tr.RANK_SCHEMA, "items": list(items)}


def _rank(rank, root, repo="GBOGEB/ABACUS"):
    return {"rank": rank, "root_candidate_id": root, "origin_repository": repo}


# --- primitives -------------------------------------------------------------------------------


def test_primitives():
    assert tr.stable_json({"b": 1, "a": "é"}) == '{"a":"é","b":1}'
    assert (
        tr.hash_payload({"a": 1}) == tr.hash_payload({"a": 1})
        and len(tr.hash_payload({})) == 64
    )
    assert tr.nonblank(" x ") and not tr.nonblank("  ") and not tr.nonblank(None)
    assert tr.valid_repo("o/r") and not tr.valid_repo("o/r/x")
    assert tr.valid_digest(A, tr.SHA) and not tr.valid_digest("A" * 40, tr.SHA)
    assert tr.positive(1) and not tr.positive(True) and not tr.positive(0)
    assert tr.percent(1, 3) == 33.33 and tr.percent(1, 0) is None
    with pytest.raises(tr.InvalidCensus, match="boom"):
        tr.need(False, "boom")


# --- contract / ranking -------------------------------------------------------------------


def test_validate_contract_sorts_case_insensitively():
    assert tr.validate_contract(_contract()) == [
        "GBOGEB/ABACUS",
        "GBOGEB/CODEX",
        "GBOGEB/gg_MATH",
    ]


def _rollout(**changes):
    rollout = {"repository_candidates": list(REPOS), "top21_definition": "x"}
    rollout.update(changes)
    return _contract(rollout=rollout)


@pytest.mark.parametrize(
    "contract,message",
    [
        ("x", "unsupported federation contract"),
        (_contract(schema_version="2"), "unsupported federation contract"),
        (_contract(security_waiver=True), "security waiver forbidden"),
        (_contract(authority={"authority_transfer": True}), "cannot be promoted"),
        (
            _contract(
                authority={
                    "authority_transfer": False,
                    "formal_credit_delta": 0,
                    "engineering_credit_delta": False,
                }
            ),
            "cannot be promoted",
        ),
        (_contract(rollout=None), "federation rollout missing"),
        (_rollout(repository_candidates="x"), "candidate repository inventory missing"),
        (_rollout(repository_candidates=["bad"]), "invalid repository candidate"),
        (
            _rollout(repository_candidates=["o/r", "O/R"]),
            "duplicate repository candidate",
        ),
        (_rollout(top21_definition=" "), "TOP21 definition missing"),
    ],
)
def test_validate_contract_rejections(contract, message):
    with pytest.raises(tr.InvalidCensus, match=message):
        tr.validate_contract(contract)


def test_validate_ranking():
    known = {r.lower() for r in REPOS}
    assert tr.validate_ranking(None, known) == []
    ranked = tr.validate_ranking(
        _ranking(_rank(2, "root-b"), _rank(1, "root-a", "gbogeb/codex")), known
    )
    assert [x["rank"] for x in ranked] == [1, 2] and ranked[0][
        "causal_confirmation"
    ] == "UNKNOWN"


@pytest.mark.parametrize(
    "ranking,message",
    [
        ({"schema": "x"}, "unsupported ranking schema"),
        (_ranking(*[_rank(i, f"root-{i}") for i in range(1, 23)]), "capacity exceeded"),
        (_ranking({"rank": 1}), "missing/unrecognized keys"),
        (_ranking(_rank(22, "root-a")), "invalid or duplicate TOP21 rank"),
        (
            _ranking(_rank(1, "root-a"), _rank(1, "root-b")),
            "invalid or duplicate TOP21 rank",
        ),
        (_ranking(_rank(1, "x")), "invalid or duplicate root candidate"),
        (
            _ranking(_rank(1, "root-a"), _rank(2, "root-a")),
            "invalid or duplicate root candidate",
        ),
        (_ranking(_rank(1, "root-a", "GBOGEB/other")), "outside candidate inventory"),
    ],
)
def test_validate_ranking_rejections(ranking, message):
    with pytest.raises(tr.InvalidCensus, match=message):
        tr.validate_ranking(ranking, {r.lower() for r in REPOS})


# --- receipts -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        _url(tail=""),
        _url(tail="/"),
        _url(),
    ],
)
def test_check_run_url_accepts_bound_forms(url):
    tr._check_run_url(url, "GBOGEB/ABACUS", 5, 6)


@pytest.mark.parametrize(
    "url",
    [
        None,
        "http://github.com/GBOGEB/ABACUS/actions/runs/5",
        "https://evil.com/GBOGEB/ABACUS/actions/runs/5",
        _url(run=7),
        _url() + "?x=1",
        _url() + "#frag",
        "https://user@github.com/GBOGEB/ABACUS/actions/runs/5",
    ],
)
def test_check_run_url_rejections(url):
    with pytest.raises(tr.InvalidCensus):
        tr._check_run_url(url, "GBOGEB/ABACUS", 5, 6)


def test_validate_coverage():
    cov = tr._validate_coverage(_coverage())
    assert (
        cov["reported_pct"] == 75.0
        and cov["authenticity"] == "UNVERIFIED_OPERATOR_INPUT"
    )
    changed = tr._validate_coverage(
        _coverage(scope="changed_lines", covered=0, eligible=0)
    )
    assert changed["reported_pct"] is None


@pytest.mark.parametrize(
    "measurement,message",
    [
        ("x", "incomplete coverage measurement contract"),
        (dict(_coverage(), extra=1), "incomplete coverage measurement contract"),
        (_coverage(scope="global"), "invalid coverage scope/unit"),
        (_coverage(unit="arcs"), "invalid coverage scope/unit"),
        (_coverage(covered=5), "invalid coverage numerator/denominator"),
        (_coverage(covered=1.0), "invalid coverage numerator/denominator"),
        (_coverage(covered=0, eligible=0), "zero eligible lines only valid"),
        (_coverage(config_digest="x"), "unbound coverage tool/configuration"),
        (_coverage(tool_version=" "), "unbound coverage tool/configuration"),
    ],
)
def test_validate_coverage_rejections(measurement, message):
    with pytest.raises(tr.InvalidCensus, match=message):
        tr._validate_coverage(measurement)


def test_validate_receipts_sorted_and_typed():
    assert tr.validate_receipts(None, REPOS) == []
    out = tr.validate_receipts(
        _receipts(
            _receipt("SECURITY", run=9, job=1),
            _receipt("COVERAGE"),
            _receipt("CI", repo="GBOGEB/CODEX", sha=B),
        ),
        REPOS,
    )
    assert [(x["repository"], x["kind"]) for x in out] == [
        ("GBOGEB/ABACUS", "COVERAGE"),
        ("GBOGEB/ABACUS", "SECURITY"),
        ("GBOGEB/CODEX", "CI"),
    ]
    assert out[0]["measurement"]["covered"] == 3 and out[1]["measurement"] is None
    assert all(x["trust"] == "OPERATOR_SUPPLIED_NOT_AUTHENTICATED" for x in out)


def _without(receipt, key):
    receipt = copy.deepcopy(receipt)
    del receipt[key]
    return receipt


@pytest.mark.parametrize(
    "receipts,message",
    [
        ({"schema": "x"}, "unsupported receipts schema"),
        ({"schema": tr.RECEIPT_SCHEMA, "items": {}}, "receipts must be an array"),
        (_receipts("x"), "missing/unrecognized fields"),
        (_receipts(_without(_receipt(), "kind")), "missing/unrecognized fields"),
        (_receipts(_receipt(repo="GBOGEB/other")), "receipt for unknown repository"),
        (_receipts(_receipt(sha="short")), "receipt exact SHA missing"),
        (_receipts(_receipt(run=0)), "run/job must be positive"),
        (_receipts(_receipt(kind="PERF")), "unsupported receipt type"),
        (_receipts(_receipt(evidence_url=_url(run=99))), "not bound to the declared"),
        (_receipts(_receipt(), _receipt()), "duplicate source-bound receipt"),
        (
            _receipts(_receipt(), _receipt("SECURITY", sha=B)),
            "multiple repository heads",
        ),
        (
            _receipts(_receipt("COVERAGE", artifact_sha256="x")),
            "artifact digest invalid",
        ),
        (
            _receipts(
                _receipt("CI", measurement=_coverage(), artifact_sha256="d" * 64)
            ),
            "non-coverage receipt cannot claim coverage",
        ),
    ],
)
def test_validate_receipts_rejections(receipts, message):
    with pytest.raises(tr.InvalidCensus, match=message):
        tr.validate_receipts(receipts, REPOS)


def test_coverage_receipt_requires_measurement_keys():
    # Same six keys as a plain receipt, but kind COVERAGE without the extra fields.
    with pytest.raises(
        tr.InvalidCensus, match="coverage receipt lacks artifact and measurement"
    ):
        tr.validate_receipts(_receipts(dict(_receipt(), kind="COVERAGE")), REPOS)


# --- rollout_census ------------------------------------------------------------------------------


def test_rollout_census_end_to_end():
    receipts = _receipts(_receipt("COVERAGE"), _receipt("CI"))
    ranking = _ranking(_rank(1, "root-a"))
    census = tr.rollout_census(_contract(), receipts, ranking)
    assert census["schema"] == tr.OUTPUT_SCHEMA
    assert census["root_ranking"]["capacity_fill_pct"] == round(100 / 21, 2)
    rollout = census["repository_rollout"]
    assert (
        rollout["nominated_inventory"] == 3
        and rollout["source_bound_manifest_count"] == 2
    )
    assert rollout["repositories_with_declared_receipts"] == 1
    assert rollout["declared_receipt_presence_pct"] == 33.33
    by_repo = {row["repository"]: row for row in rollout["inventory"]}
    assert by_repo["GBOGEB/ABACUS"]["assessment"] == "SOURCE_BOUND_UNVERIFIED"
    assert by_repo["GBOGEB/ABACUS"]["source_sha"] == A
    assert len(by_repo["GBOGEB/ABACUS"]["coverage_by_scope"]) == 1
    assert by_repo["GBOGEB/CODEX"]["assessment"] == "NOT_ASSESSED"
    assert census["admission"] == "HOLD" and census["authority_transfer"] is False
    bare = tr.rollout_census(_contract())
    assert bare["root_ranking"]["operator_submitted_candidates"] == 0
    assert bare["source_contract_sha256"] == census["source_contract_sha256"]
    assert bare["input_sha256"] != census["input_sha256"]
