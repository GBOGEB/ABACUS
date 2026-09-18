from __future__ import annotations

import copy
import functools
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
W79_INPUT = ROOT / "architecture/w79/W79_W78_INPUT.json"
W80_LEDGER = ROOT / "architecture/w80/W80_OBSERVED_VALIDATION_LEDGER.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


w80 = load_module(
    "w80_observed_outcome_validation",
    TOOLS / "w80_observed_outcome_validation.py",
)
w79 = load_module(
    "w79_deterministic_work_pca_for_w80_test",
    TOOLS / "w79_deterministic_work_pca.py",
)


def load_inputs() -> tuple[dict, dict]:
    return (
        json.loads(W79_INPUT.read_text(encoding="utf-8")),
        json.loads(W80_LEDGER.read_text(encoding="utf-8")),
    )


@functools.lru_cache(maxsize=1)
def real_result() -> dict:
    w79_source, ledger = load_inputs()
    return w80.evaluate(w79_source, ledger)


def test_real_w80_is_negative_observed_outcome_validation() -> None:
    result = real_result()
    assert result["status"] == "OUTCOME_VALIDATION_NOT_SUPPORTED"
    assert result["semantic_pc1"]["eigenvalue"] == 6.341341
    assert result["semantic_pc1"]["explained_variance_ratio"] == 0.905906

    coverage = result["outcome_coverage"]
    assert coverage["observed_states"] == 11
    assert coverage["missing_states"] == 4
    assert coverage["coverage_fraction"] == 0.733333
    assert coverage["pc1_full_min"] == -6.074314
    assert coverage["pc1_full_max"] == 1.904192
    assert coverage["pc1_observed_min"] == -0.300676
    assert coverage["pc1_observed_max"] == 1.904192
    assert coverage["pc1_range_coverage_fraction"] == 0.276351
    assert coverage["range_restriction_warning"] is True

    primary = result["primary_outcome"]
    assert primary["spearman_rho"] == 0.01978
    assert primary["exact_permutation_p"] == 0.974459
    assert primary["exact_permutation_count"] == 9240
    assert primary["loocv_linear_r2"] == -0.724876

    secondary = result["secondary_outcome"]
    assert secondary["positive_count"] == 8
    assert secondary["negative_count"] == 3
    assert secondary["auc"] == 0.604167
    assert secondary["exact_permutation_p"] == 0.642424
    assert secondary["exact_permutation_count"] == 165

    gate = result["predeclared_gate"]
    assert gate["minimum_pc1_range_coverage_fraction"] == 0.70
    assert gate["pc1_range_gate_pass"] is False
    assert gate["primary_gate_pass"] is False

    assert result["pc1_predictive_validation"] is False
    assert result["pairwise_outcome_accumulation_permitted"] is False
    assert result["pairwise_events"] == []
    assert result["bt_status"] == (
        "WITHHELD_PC1_NOT_VALIDATED_AGAINST_OBSERVED_OUTCOMES"
    )
    assert result["timing_pca_reopened"] is False
    assert result["global_allocation_authority"] is False


def test_cancelled_validation_is_missing_not_failure() -> None:
    result = real_result()
    s10 = next(row for row in result["outcome_rows"] if row["label"] == "s10")
    assert s10["executed_core_validators"] == 6
    assert s10["cancelled_core_validators"] == 1
    assert s10["core_success_count"] == 5
    assert s10["core_failure_count"] == 1
    assert round(s10["core_pass_fraction"], 6) == 0.833333


def test_missing_states_are_not_zero_imputed() -> None:
    result = real_result()
    missing = {row["label"] for row in result["outcome_coverage"]["missing_rows"]}
    observed = {row["label"] for row in result["outcome_rows"]}
    assert missing == {"s01", "s02", "s03", "s04"}
    assert missing.isdisjoint(observed)


def test_forged_observed_outcome_payload_fails_closed() -> None:
    w79_source, ledger = load_inputs()
    forged = copy.deepcopy(ledger)
    observed = next(state for state in forged["states"] if state["status"] == "OBSERVED")
    observed["runs"][0]["conclusion"] = "failure"
    try:
        w80.evaluate(w79_source, forged)
    except ValueError as exc:
        assert "governed outcome ledger payload mismatch" in str(exc)
    else:
        raise AssertionError("forged W80 outcome ledger must fail closed")


def test_tampered_w79_source_fails_closed_before_outcome_credit() -> None:
    w79_source, ledger = load_inputs()
    forged = copy.deepcopy(w79_source)
    forged["rows"][0]["values"][-1] += 1
    try:
        w80.evaluate(forged, ledger)
    except ValueError as exc:
        assert "hash mismatch" in str(exc) or "payload mismatch" in str(exc)
    else:
        raise AssertionError("tampered W79 source must fail closed")


def test_range_restriction_blocks_promotion_even_with_observed_count_gate_met() -> None:
    result = real_result()
    coverage = result["outcome_coverage"]
    assert coverage["observed_states"] >= result["predeclared_gate"]["minimum_observed_states"]
    assert coverage["coverage_fraction"] >= result["predeclared_gate"]["minimum_coverage_fraction"]
    assert coverage["pc1_range_coverage_fraction"] < result["predeclared_gate"]["minimum_pc1_range_coverage_fraction"]
    assert result["predeclared_gate"]["pc1_range_gate_pass"] is False
    assert result["pc1_predictive_validation"] is False
    assert result["pairwise_events"] == []


def test_authoritative_actions_receipt_binds_every_counted_run() -> None:
    w79_source, ledger = load_inputs()
    receipt = w80.load_governed_run_receipt()
    assert receipt["repository_id"] == 1054507184
    assert receipt["repository_full_name"] == "GBOGEB/ABACUS"
    assert receipt["run_count"] == 77
    rows = w80.validate_ledger(ledger, w79_source, w79, receipt)
    assert len(rows) == 15

    forged = copy.deepcopy(receipt)
    forged["runs"][0]["source_sha"] = "0" * 40
    try:
        w80.validate_ledger(ledger, w79_source, w79, forged)
    except ValueError as exc:
        assert "authoritative run binding mismatch" in str(exc)
    else:
        raise AssertionError("cross-SHA Actions outcome must fail closed")
