"""Lane-B wave 9: everred_v3 ldab_adapter canonical BD/LDAB census consumption."""

import copy
import hashlib
import json

import pytest

from ._l2_loader import load

fp = load("tools/everred_v3/src/four_planes.py")
la = load("tools/everred_v3/src/ldab_adapter.py", deps={"four_planes": fp})

A, B = "a" * 40, "b" * 40
REPO = "GBOGEB/ABACUS"
FPRINT = "0123456789abcdef" * 4


def _src(**overrides):
    values = {"repository": REPO, "source_sha": A, "run_id": 5, "job_id": 6}
    values.update(overrides)
    return fp.Source(**values)


def _obs(**overrides):
    values = {"repository": REPO, "source_sha": A, "run_id": 5, "job_id": 6}
    values.update(overrides)
    return values


def _report():
    return {
        "schema": "bd.ldab.joined.census.v1",
        "merge_admission": "HOLD",
        "authority_transfer": False,
        "security_waiver": False,
        "scope": {"repository": REPO, "head_sha": A, "run_id": 5, "job_id": 6},
        "roots": [
            {
                "root_id": "root-bandit-1",
                "category": "BANDIT",
                "fingerprint": FPRINT,
                "owner_lane": "L2",
                "observations": [
                    _obs(),
                    # cross-repo observation is skipped, even with bad ids
                    _obs(repository="OTHER/repo", run_id="x"),
                    # same repo but other head is skipped too
                    _obs(source_sha=B, job_id=None),
                ],
            },
            {"root_id": "root-ci-2", "category": "CI", "observations": [_obs()]},
            {"root_id": "root-ci-1", "category": "CI", "observations": []},
        ],
        "unlinked_debug_receipts": [{"x": 1}, {"x": 2}],
        "metrics": {"full_bandit_unique": 1},
    }


def test_consume_happy_path():
    report = _report()
    out = la.consume_bd_ldab(report, expected_source=_src())
    assert out["schema"] == "abacus.everred.ldab.canonical.bridge.v1"
    assert out["source_binding"] == _src().binding()
    expected_digest = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert out["canonical_sha256"] == expected_digest
    assert out["ci_candidate_ids"] == ["root-ci-1", "root-ci-2"]
    assert out["unlinked_debug_count"] == 2
    assert out["causal_roots_confirmed"] is None
    assert out["merge_admission"] == "HOLD"
    assert out["authority_transfer"] is False
    assert out["security_disposition"] == "PENDING_INDEPENDENT_REVIEW"
    (cand,) = out["bandit_candidates"]
    assert cand["plane"] == "diagnostic"
    assert cand["domain"] == "ldab"
    assert cand["data"]["root_id"] == "root-bandit-1"
    assert cand["data"]["finding_fingerprint"] == FPRINT
    assert cand["data"]["owner"] == "L2"
    assert cand["data"]["disposition"] == "HYPOTHESIS"
    assert cand["data"]["scope"] == "canonical-observation-only"


def test_consume_empty_roots():
    report = _report()
    report["roots"] = []
    report["unlinked_debug_receipts"] = []
    report["metrics"] = {"full_bandit_unique": 0}
    out = la.consume_bd_ldab(report, expected_source=_src())
    assert out["bandit_candidates"] == []
    assert out["ci_candidate_ids"] == []
    assert out["unlinked_debug_count"] == 0


def _set(path, value):
    def mutate(report):
        target = report
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    return mutate


def _drop(key):
    def mutate(report):
        del report[key]

    return mutate


@pytest.mark.parametrize(
    "mutate,message",
    [
        (_set(("schema",), "other"), "canonical BD/LDAB schema required"),
        (_set(("merge_admission",), "ALLOW"), "canonical admission boundary"),
        (_set(("authority_transfer",), True), "canonical admission boundary"),
        (_set(("security_waiver",), None), "canonical admission boundary"),
        (_set(("scope",), []), "missing canonical scope"),
        (_drop("scope"), "missing canonical scope"),
        (_set(("scope", "repository"), "OTHER/repo"), "scope does not match"),
        (_set(("scope", "head_sha"), B), "scope does not match"),
        (_set(("scope", "run_id"), 7), "scope does not match"),
        (_set(("scope", "job_id"), None), "scope does not match"),
        (_set(("roots",), {}), "invalid root/debug arrays"),
        (_drop("unlinked_debug_receipts"), "invalid root/debug arrays"),
        (_set(("roots", 0), "row"), "root identity invalid"),
        (_set(("roots", 0, "root_id"), 7), "root identity invalid"),
        (_set(("roots", 2, "root_id"), "root-ci-2"), "duplicate canonical root"),
        (_set(("roots", 0, "category"), "LINT"), "root category unknown"),
        (_set(("roots", 1, "observations"), None), "root observations missing"),
        (_set(("roots", 1, "observations", 0), "obs"), "malformed root observation"),
        (
            _set(("roots", 1, "observations", 0, "run_id"), "5"),
            "root run/job identity invalid",
        ),
        (
            _set(("roots", 1, "observations", 0, "job_id"), True),
            "root run/job identity invalid",
        ),
        (_set(("roots", 0, "fingerprint"), None), "invalid Bandit fingerprint"),
        (_set(("roots", 0, "fingerprint"), "ab"), "invalid Bandit fingerprint"),
        (_set(("roots", 0, "fingerprint"), "A" * 64), "invalid Bandit fingerprint"),
        (_set(("metrics",), None), "Bandit denominator mismatches"),
        (_set(("metrics", "full_bandit_unique"), 2), "Bandit denominator mismatches"),
    ],
)
def test_consume_rejections(mutate, message):
    report = copy.deepcopy(_report())
    mutate(report)
    with pytest.raises(fp.EvidenceError, match=message):
        la.consume_bd_ldab(report, expected_source=_src())


def test_consume_rejects_non_mapping_report():
    with pytest.raises(fp.EvidenceError, match="canonical BD/LDAB schema required"):
        la.consume_bd_ldab(["not", "a", "dict"], expected_source=_src())


def test_consume_bandit_root_id_must_satisfy_ldab_receipt():
    report = _report()
    report["roots"][0]["root_id"] = "!!"
    with pytest.raises(fp.EvidenceError, match="stable root ID required"):
        la.consume_bd_ldab(report, expected_source=_src())
