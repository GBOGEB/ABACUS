from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "architecture/w83/W83_OUTCOME_LEDGER_v0.1.json"
EXPECTED = ROOT / "architecture/w83/W83_OUTCOME_DISCRIMINATION_v0.1.json"
TOOL = ROOT / "tools/w83_outcome_discrimination.py"


def load_module():
    spec = importlib.util.spec_from_file_location("w83_outcome_discrimination", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


w83 = load_module()


def test_real_w83_typed_basis_is_non_discriminating() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    result = w83.evaluate(ledger)
    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    for key, value in expected.items():
        assert result[key] == value
    assert result["exact_inference"]["odds_ratio"] == 1.0
    assert result["exact_inference"]["fisher_exact_two_sided_p"] == 1.0
    assert result["exact_inference"]["mutual_information_bits"] == 0.0
    assert result["outcome_discrimination_supported"] is False
    assert result["pca_fit_performed"] is False
    assert result["pairwise_outcome_accumulation_permitted"] is False
    assert result["pairwise_events"] == []


def test_w83_forged_outcome_fails_closed() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    forged = copy.deepcopy(ledger)
    forged["rows"][0]["outcome"]["failure_label"] = 1
    try:
        w83.evaluate(forged)
    except ValueError as exc:
        assert "outcome mismatch" in str(exc)
    else:
        raise AssertionError("forged W83 outcome must fail closed")


def test_w83_variable_feature_drift_fails_closed() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    forged = copy.deepcopy(ledger)
    forged["variable_features"].append("semantic_composition.gap_open")
    try:
        w83.evaluate(forged)
    except ValueError as exc:
        assert "variable feature set drift" in str(exc)
    else:
        raise AssertionError("W83 feature drift must fail closed")
