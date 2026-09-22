from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "federation/qps/W329_R1_HIST_BD_034_DOW_REVIEW.yaml"


def load_review():
    return yaml.safe_load(REVIEW.read_text(encoding="utf-8"))


def test_w329_dow_binds_exact_candidate_heads():
    data = load_review()
    assert data["child"]["repair_pr"] == 1650
    assert data["child"]["exact_head"] == "9ac6748a806ac7e260b37e1c9d95401670eed9d2"
    assert data["keb"]["review_pr"] == 824
    assert data["keb"]["exact_head"] == "0f5c097a74758a8e0dba9e90e4e0077010ab483a"


def test_w329_dow_quantification_is_non_compensating():
    data = load_review()
    metrics = data["quantified_challenge"]
    assert metrics["physical_conversion_denominator"] == 5
    assert metrics["physical_conversion_delta_from_code_only_repair"] == 0
    assert metrics["strict_numerical_delta"] == 0
    assert metrics["runtime_gold_delta"] == 0
    assert metrics["reviewed_guard_findings"] == 4
    assert metrics["candidate_guard_repairs"] == 4


def test_w329_dow_perpetuate_waits_for_final_binding():
    data = load_review()
    assert data["mip"]["perpetuate"]["state"] == "HOLD_FINAL_BINDING"
    assert data["authority_transfer"] is False
    assert data["formal_credit_delta"] == 0
    assert data["semantic_checks"]["BT0"]["protected_or_signed_owner_attestation_required"] is True
    assert data["semantic_checks"]["BT2"]["decimal_residual_semantics_exact"] is True
