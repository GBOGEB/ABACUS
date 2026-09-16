#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "runtime" / "federation" / "gg_math_temporal_pca_independent_challenge.py"
spec = importlib.util.spec_from_file_location("gg_math_temporal_pca_independent_challenge", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


def test_exact_codex_binding_and_authority_guards():
    receipt = mod.build_receipt()
    assert receipt["status"] == "ACCEPT"
    assert receipt["source"]["repo"] == "GBOGEB/CODEX"
    assert receipt["source"]["commit"] == mod.CODEX_COMMIT
    assert receipt["source"]["git_blob_sha1"] == mod.CODEX_BINDING_BLOB
    assert all(receipt["binding_checks"].values())
    assert receipt["authority_transfer"] is False
    assert receipt["formal_credit_delta"] == 0
    assert receipt["hard_gate_compensation_allowed"] is False


def test_independent_c01_c07_all_pass_without_gg_math_imports():
    receipt = mod.build_receipt()
    independent = receipt["independent_math"]
    assert independent["imports_gg_math_kernels"] is False
    assert independent["challenge_pass_ratio"] == 1.0
    assert set(independent["challenges"]) == set(mod.CHALLENGES)
    assert all(item["pass"] for item in independent["challenges"].values())


def test_governance_consumer_accepts_exact_keb_binding():
    receipt = mod.build_receipt()
    governance = receipt["governance_consumer"]
    assert governance["status"] == "ACCEPT"
    assert governance["emit_for_qps_bounded_consumption"] is True
    assert governance["authority_guards"]["qps_engineering_authority_transfer"] is False
    assert governance["authority_guards"]["formal_engineering_credit_delta"] == 0
    assert governance["interpretation_guards"]["pca_loading_sign_is_policy_direction"] is False
    assert governance["interpretation_guards"]["attenuation_equals_direction_reversal"] is False


def test_cycle2_kpis_close_at_control_without_credit():
    receipt = mod.build_receipt()
    kpis = receipt["kpis"]
    assert kpis["independent_consumer_count"] == 1
    assert kpis["independent_reproduction_pass_ratio"] == 1.0
    assert kpis["schema_parity"] == 1.0
    assert kpis["receipt_concordance"] == 1.0
    assert kpis["authority_inversion_count"] == 0
    assert kpis["formal_credit_delta"] == 0
    assert receipt["next_action"].startswith("PROMOTE_CODEX_KEB_SOURCE_RECEIPT_TO_KNOWLEDGE_ATOM")


def test_fixed_interpretation_guards_remain_separate():
    receipt = mod.build_receipt()
    interpretation = receipt["interpretation"]
    assert interpretation["pca_loading_sign_is_physical_reversal"] is False
    assert interpretation["attenuation_toward_parity_is_direction_reversal"] is False
    assert interpretation["component_identity_requires_assignment"] is True
    assert interpretation["event_wall_age_clocks_are_distinct"] is True


if __name__ == "__main__":
    test_exact_codex_binding_and_authority_guards()
    test_independent_c01_c07_all_pass_without_gg_math_imports()
    test_governance_consumer_accepts_exact_keb_binding()
    test_cycle2_kpis_close_at_control_without_credit()
    test_fixed_interpretation_guards_remain_separate()
    print("PASS_GG_MATH_TEMPORAL_PCA_INDEPENDENT_CHALLENGE_TESTS")
