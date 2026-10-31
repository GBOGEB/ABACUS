"""Gap tests for scripts/qps_triage_dow_consume_keb.py (contract errors, main)."""

import json
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load(
    "scripts/qps_triage_dow_consume_keb.py",
    name="abn_w7_qps_triage_dow_consume_keb",
)

SHA40 = "a" * 40
CONSUMER_SHA = "b" * 40


def _seal(receipt):
    basis = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    receipt["receipt_sha256"] = mod.canonical_digest(basis)
    return receipt


def _keb(**overrides):
    receipt = {
        "producer_repo": mod.PRODUCER_REPO,
        "producer_pr": 12,
        "producer_head_sha": SHA40,
        "source_object_ids": ["obj-1", "obj-2"],
        "contract_version": mod.KEB_CONTRACT_VERSION,
        "workflow_or_validator": "keb.yml",
        "executed_steps": 3,
        "result": "PASS",
        "downstream_consumer": mod.CONSUMER_REPO,
        "child_reentry_target": mod.CHILD_REENTRY_TARGET,
        "authority_transfer": False,
        "producer_merge_sha": "c" * 40,
        "source_manifest_sha256": "d" * 64,
    }
    receipt.update(overrides)
    return _seal(receipt)


def _challenge(**overrides):
    challenge = {
        "challenge_or_execution": "replayed validator",
        "result": "PASS",
        "executed_steps": 2,
        "reason": "independent replay matched",
        "private_evidence_copied": False,
        "authority_transfer": False,
        "component_analytics_only": True,
        "system_consequence_withheld": True,
        "table10_rate_per_year": 0.0,
        "first_red": "GHP03_N_MINUS_1_CAPACITY",
    }
    challenge.update(overrides)
    return challenge


def test_keb_receipt_reports_every_field_error():
    bad = {
        "producer_repo": "x/y",
        "producer_pr": 0,
        "producer_head_sha": "zz",
        "source_object_ids": ["ok", "  "],
        "contract_version": "v0",
        "workflow_or_validator": "w",
        "executed_steps": 0,
        "result": "PASS",
        "receipt_sha256": "e" * 64,
        "downstream_consumer": "x/z",
        "child_reentry_target": "x/c",
        "authority_transfer": True,
    }
    errors = mod.validate_keb_receipt(bad)
    for field in (
        "producer_repo",
        "producer_pr",
        "producer_head_sha",
        "contract_version",
        "downstream_consumer",
        "child_reentry_target",
        "authority_transfer",
        "source_object_ids",
        "executed_steps",
        "receipt_sha256_mismatch",
    ):
        assert field in errors


def test_keb_receipt_invalid_result_and_digest():
    receipt = _keb(result="MAYBE")
    receipt["receipt_sha256"] = "short"
    errors = mod.validate_keb_receipt(receipt)
    assert "result" in errors
    assert "receipt_sha256" in errors


def test_challenge_reports_shape_and_pass_requirements():
    challenge = _challenge(
        challenge_or_execution="  ",
        executed_steps=0,
        reason=7,
        private_evidence_copied=True,
        authority_transfer=True,
        component_analytics_only=False,
        system_consequence_withheld=False,
        table10_rate_per_year=1.5,
        first_red="OTHER",
    )
    errors = mod.validate_challenge(challenge, _keb())
    assert errors == sorted(
        [
            "authority_transfer",
            "challenge_or_execution",
            "component_analytics_only",
            "executed_steps",
            "first_red",
            "private_evidence_copied",
            "reason",
            "system_consequence_withheld",
            "table10_rate_per_year",
        ]
    )


def test_challenge_invalid_result_skips_pass_checks():
    challenge = _challenge(result="BOGUS", component_analytics_only=False)
    assert mod.validate_challenge(challenge, _keb()) == ["result"]


def test_challenge_expected_bindings_mismatch():
    challenge = _challenge(
        expected_producer_merge_sha="f" * 40,
        expected_source_manifest_sha256="0" * 64,
        expected_source_object_ids=["obj-9"],
    )
    errors = mod.validate_challenge(challenge, _keb())
    assert errors == [
        "expected_producer_merge_sha",
        "expected_source_manifest_sha256",
        "expected_source_object_ids",
    ]


def test_challenge_expected_objects_must_be_list():
    challenge = _challenge(expected_source_object_ids="obj-1")
    assert mod.validate_challenge(challenge, _keb()) == ["expected_source_object_ids"]


def test_challenge_expected_bindings_match():
    challenge = _challenge(
        expected_producer_merge_sha="c" * 40,
        expected_source_manifest_sha256="d" * 64,
        expected_source_object_ids=["obj-2", "obj-1"],
    )
    assert mod.validate_challenge(challenge, _keb()) == []


def test_finalize_rejects_bad_consumer_sha():
    with pytest.raises(ValueError, match="consumer_head_sha"):
        mod.finalize_dow_receipt(
            _keb(), _challenge(), consumer_pr=5, consumer_head_sha="nothex"
        )


def test_finalize_rejects_invalid_challenge():
    with pytest.raises(ValueError, match="DOW_CHALLENGE_CONTRACT: reason"):
        mod.finalize_dow_receipt(
            _keb(), _challenge(reason=""), consumer_pr=5, consumer_head_sha=CONSUMER_SHA
        )


def test_finalize_fail_result_rejects():
    value = mod.finalize_dow_receipt(
        _keb(result="FAIL"),
        _challenge(result="DEFER"),
        consumer_pr=5,
        consumer_head_sha=CONSUMER_SHA,
    )
    assert value["disposition"] == "REJECT"


def test_load_json_rejects_non_object(tmp_path):
    path = tmp_path / "list.json"
    path.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ValueError, match="expected JSON object"):
        mod.load_json(path)


def _argv(tmp_path, keb, challenge, out):
    keb_path = tmp_path / "keb.json"
    challenge_path = tmp_path / "challenge.json"
    keb_path.write_text(json.dumps(keb), encoding="utf-8")
    challenge_path.write_text(json.dumps(challenge), encoding="utf-8")
    return [
        "dow",
        "--keb-receipt",
        str(keb_path),
        "--challenge",
        str(challenge_path),
        "--consumer-pr",
        "44",
        "--consumer-head-sha",
        CONSUMER_SHA,
        "--output",
        str(out),
    ]


def test_main_writes_accept_receipt(monkeypatch, tmp_path, capsys):
    out = tmp_path / "out" / "dow.json"
    monkeypatch.setattr(sys, "argv", _argv(tmp_path, _keb(), _challenge(), out))
    assert mod.main() == 0
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["disposition"] == "ACCEPT"
    assert written["consumer_pr"] == 44
    basis = {k: v for k, v in written.items() if k != "receipt_sha256"}
    assert written["receipt_sha256"] == mod.canonical_digest(basis)
    assert json.loads(capsys.readouterr().out) == written


def test_main_reports_failure(monkeypatch, tmp_path, capsys):
    out = tmp_path / "out" / "dow.json"
    keb = _keb(producer_repo="x/y")
    monkeypatch.setattr(sys, "argv", _argv(tmp_path, keb, _challenge(), out))
    assert mod.main() == 1
    assert "FAIL: KEB_RECEIPT_CONTRACT" in capsys.readouterr().out
    assert not out.exists()
