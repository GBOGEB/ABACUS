import copy
import json
from pathlib import Path

import pytest

from scripts import qps_triage_dow_consume_keb as dow


HEAD = "a" * 40
PRODUCER_HEAD = "b" * 40
PRODUCER_MERGE = "c" * 40
MANIFEST = "d" * 64


def keb_receipt(result="PASS", executed_steps=1):
    value = {
        "producer_repo": "GBOGEB/CODEX",
        "producer_pr": 715,
        "producer_head_sha": PRODUCER_HEAD,
        "producer_merge_sha": PRODUCER_MERGE,
        "source_object_ids": ["H4-W2", "H4-W3-P1"],
        "contract_version": "qps-triage-keb-contract/1.0.0",
        "workflow_or_validator": "strict bridge replay",
        "executed_steps": executed_steps,
        "result": result,
        "reason": "controlled fixture",
        "source_manifest_sha256": MANIFEST,
        "downstream_consumer": "GBOGEB/ABACUS",
        "child_reentry_target": "GBOGEB/cryoplant-project",
        "receipt_digest_basis": "canonical JSON of all envelope fields except receipt_sha256",
        "authority_transfer": False,
    }
    value["receipt_sha256"] = dow.canonical_digest(value)
    return value


def challenge(result="PASS", executed_steps=6):
    return {
        "challenge_or_execution": "independent component-analytics boundary challenge",
        "result": result,
        "executed_steps": executed_steps,
        "reason": "exact KEB identity and fail-closed system boundary independently confirmed",
        "private_evidence_copied": False,
        "authority_transfer": False,
        "component_analytics_only": True,
        "system_consequence_withheld": True,
        "table10_rate_per_year": 0.0,
        "first_red": "GHP03_N_MINUS_1_CAPACITY",
        "expected_producer_merge_sha": PRODUCER_MERGE,
        "expected_source_manifest_sha256": MANIFEST,
        "expected_source_object_ids": ["H4-W2", "H4-W3-P1"],
    }


def test_valid_pass_emits_complete_accept_receipt_and_digest():
    result = dow.finalize_dow_receipt(
        keb_receipt(), challenge(), consumer_pr=1200, consumer_head_sha=HEAD
    )
    assert result["consumer_repo"] == "GBOGEB/ABACUS"
    assert result["consumer_pr"] == 1200
    assert result["consumer_head_sha"] == HEAD
    assert result["producer_repo"] == "GBOGEB/CODEX"
    assert result["producer_pr"] == 715
    assert result["producer_head_sha"] == PRODUCER_HEAD
    assert result["disposition"] == "ACCEPT"
    assert result["authority_transfer"] is False
    assert result["scope"] == "COMPONENT_ANALYTICS_CONTRACT_ONLY"
    assert result["system_consequence_withheld"] is True
    assert result["table10_rate_per_year"] == 0.0
    assert result["first_red"] == "GHP03_N_MINUS_1_CAPACITY"
    digest_basis = {k: v for k, v in result.items() if k != "receipt_sha256"}
    assert result["receipt_sha256"] == dow.canonical_digest(digest_basis)


def test_missing_or_invalid_consumer_pr_fails_closed():
    for value in (0, -1, True, False, None, "12", 12.0):
        with pytest.raises(ValueError, match="consumer_pr"):
            dow.finalize_dow_receipt(
                keb_receipt(), challenge(), consumer_pr=value, consumer_head_sha=HEAD
            )


def test_tampered_keb_digest_fails_closed():
    receipt = keb_receipt()
    receipt["reason"] = "tampered after digest"
    with pytest.raises(ValueError, match="receipt_sha256_mismatch"):
        dow.finalize_dow_receipt(
            receipt, challenge(), consumer_pr=1200, consumer_head_sha=HEAD
        )


def test_pass_challenge_requires_positive_integer_execution_steps():
    for value in (0, -1, True, False, None, "1", 1.0):
        with pytest.raises(ValueError, match="executed_steps"):
            dow.finalize_dow_receipt(
                keb_receipt(),
                challenge(executed_steps=value),
                consumer_pr=1200,
                consumer_head_sha=HEAD,
            )


def test_expected_producer_identity_mismatch_fails_closed():
    candidate = challenge()
    candidate["expected_producer_merge_sha"] = "e" * 40
    with pytest.raises(ValueError, match="expected_producer_merge_sha"):
        dow.finalize_dow_receipt(
            keb_receipt(), candidate, consumer_pr=1200, consumer_head_sha=HEAD
        )


def test_upstream_defer_produces_dow_defer_not_accept():
    receipt = keb_receipt(result="DEFER", executed_steps=0)
    result = dow.finalize_dow_receipt(
        receipt, challenge(), consumer_pr=1200, consumer_head_sha=HEAD
    )
    assert result["disposition"] == "DEFER"
    assert result["authority_transfer"] is False


def test_pass_cannot_relax_system_boundary_or_authority():
    mutations = [
        ("authority_transfer", True),
        ("private_evidence_copied", True),
        ("component_analytics_only", False),
        ("system_consequence_withheld", False),
        ("table10_rate_per_year", 0.1),
        ("first_red", "CLOSED"),
    ]
    for field, value in mutations:
        candidate = copy.deepcopy(challenge())
        candidate[field] = value
        with pytest.raises(ValueError, match=field):
            dow.finalize_dow_receipt(
                keb_receipt(), candidate, consumer_pr=1200, consumer_head_sha=HEAD
            )


def test_real_w3_p2_offer11_receipt_replays_exactly():
    root = Path(__file__).resolve().parents[1]
    keb = json.loads(
        (root / "governance/qps_triage/inputs/H4_QPS_TRIAGE_W3_P2_KEB_OFFER11.json").read_text(
            encoding="utf-8"
        )
    )
    actual_challenge = json.loads(
        (root / "governance/qps_triage/challenges/H4_QPS_TRIAGE_W3_P2_DOW_OFFER11.json").read_text(
            encoding="utf-8"
        )
    )
    expected = json.loads(
        (root / "governance/qps_triage/receipts/H4_QPS_TRIAGE_W3_P2_DOW_OFFER11.json").read_text(
            encoding="utf-8"
        )
    )

    actual = dow.finalize_dow_receipt(
        keb,
        actual_challenge,
        consumer_pr=1219,
        consumer_head_sha="150deb3f61929944f8d3f0a7ed1453177cde1bce",
    )

    assert actual == expected
    assert actual["disposition"] == "ACCEPT"
    assert actual["receipt_sha256"] == "7e3d2efd498b89540392eef9da52cbf0a2dbd35d09b043200cb1e989e0262e44"
    assert actual["first_red"] == "GHP03_N_MINUS_1_CAPACITY"
    assert actual["system_consequence_withheld"] is True
    assert actual["table10_rate_per_year"] == 0.0
    assert actual["authority_transfer"] is False
