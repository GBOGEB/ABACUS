#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE = ROOT / "runtime" / "federation" / "gg_math_temporal_pca_dow_consumer.py"
LIVE_FIXTURE = ROOT / "runtime" / "federation" / "fixtures" / "gg_math_temporal_pca_exact_live_binding.json"
spec = importlib.util.spec_from_file_location("gg_math_temporal_pca_dow_consumer", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


def base_binding():
    return {
        "semantic_owner": "CODEX/KEB",
        "status": "ACCEPT",
        "source_sha": "a" * 40,
        "source_artifact_digest": "sha256:" + "b" * 64,
        "provider_runtime_result": "PASS",
        "provider_challenges": sorted(mod.REQUIRED_CHALLENGES),
        "provider_diagnostics": sorted(mod.REQUIRED_DIAGNOSTICS),
        "authority_transfer": False,
        "hard_gate_compensation_allowed": False,
        "authority_cap": "A3_SYNTHETIC_ONLY",
    }


def test_accept_requires_all_exact_binding_guards():
    receipt = mod.consume(base_binding())
    assert receipt["status"] == "ACCEPT"
    assert receipt["emit_for_qps_bounded_consumption"] is True
    assert receipt["authority_guards"]["formal_engineering_credit_delta"] == 0
    assert receipt["authority_guards"]["qps_engineering_authority_transfer"] is False


def test_exact_live_gg_math_receipt_is_independently_consumable():
    binding = json.loads(LIVE_FIXTURE.read_text(encoding="utf-8"))
    assert binding["source_sha"] == "a99d7cacd03ed3a392c063a1b3f8dbffdba0d060"
    assert binding["source_artifact_digest"] == "sha256:876c55c759de33392985f693f1735cdc0d38dda7d7b7a6c80ee80aee33fd8405"
    assert binding["federation_followup"]["artifact_digest"] == "sha256:2c7cbcddffc6c3830ab02a212563ef390e7fe189ce24214f4313e6e5bccd2921"
    receipt = mod.consume(binding)
    assert receipt["status"] == "ACCEPT"
    assert receipt["emit_for_qps_bounded_consumption"] is True
    assert receipt["producer_exact_head_sha"] == binding["source_sha"]
    assert receipt["source_artifact_digest"] == binding["source_artifact_digest"]
    assert all(receipt["checks"].values())


def test_keb_defer_remains_dow_defer():
    binding = base_binding()
    binding["status"] = "DEFER"
    receipt = mod.consume(binding)
    assert receipt["status"] == "DEFER"
    assert receipt["emit_for_qps_bounded_consumption"] is False
    assert receipt["checks"]["keb_status_accept"] is False


def test_missing_challenge_fails_closed():
    binding = base_binding()
    binding["provider_challenges"].remove("C05_ATTENUATION_WITHOUT_REVERSAL")
    receipt = mod.consume(binding)
    assert receipt["status"] == "DEFER"
    assert receipt["checks"]["all_required_challenges_present"] is False


def test_invalid_sha_or_digest_fails_closed():
    binding = base_binding()
    binding["source_sha"] = "UNKNOWN"
    binding["source_artifact_digest"] = "TBD"
    receipt = mod.consume(binding)
    assert receipt["status"] == "DEFER"
    assert receipt["checks"]["provider_exact_sha_valid"] is False
    assert receipt["checks"]["provider_artifact_digest_valid"] is False


def test_authority_or_compensation_flip_fails_closed():
    binding = base_binding()
    binding["authority_transfer"] = True
    binding["hard_gate_compensation_allowed"] = True
    receipt = mod.consume(binding)
    assert receipt["status"] == "DEFER"
    assert receipt["checks"]["authority_transfer_false"] is False
    assert receipt["checks"]["hard_gate_compensation_false"] is False


def test_interpretation_guards_are_frozen_false():
    receipt = mod.consume(base_binding())
    guards = receipt["interpretation_guards"]
    assert guards["pca_loading_sign_is_policy_direction"] is False
    assert guards["attenuation_equals_direction_reversal"] is False
    assert guards["component_order_is_identity_without_assignment"] is False
    assert guards["event_step_equals_wall_time_step"] is False


if __name__ == "__main__":
    test_accept_requires_all_exact_binding_guards()
    test_exact_live_gg_math_receipt_is_independently_consumable()
    test_keb_defer_remains_dow_defer()
    test_missing_challenge_fails_closed()
    test_invalid_sha_or_digest_fails_closed()
    test_authority_or_compensation_flip_fails_closed()
    test_interpretation_guards_are_frozen_false()
    print("PASS_GG_MATH_TEMPORAL_PCA_DOW_CONSUMER")
