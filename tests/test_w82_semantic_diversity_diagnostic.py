from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
LEDGER = ROOT / "architecture/w82/W82_SEMANTIC_DIVERSITY_LEDGER_v0.1.json"
W79 = ROOT / "architecture/w79/W79_W78_INPUT.json"
CANONICAL = ROOT / "architecture/w82/W82_SEMANTIC_DIVERSITY_DIAGNOSTIC_v0.1.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


w82 = load_module(
    "w82_semantic_diversity_diagnostic",
    TOOLS / "w82_semantic_diversity_diagnostic.py",
)


def real_result() -> dict:
    source = json.loads(W79.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    return w82.evaluate(source, ledger)


def test_w82_canonical_receipt_recomputes_exactly() -> None:
    assert real_result() == json.loads(CANONICAL.read_text(encoding="utf-8"))


def test_w82_balanced_outcomes_have_no_semantic_discrimination() -> None:
    result = real_result()
    assert result["sample_geometry"]["measured_states"] == 6
    assert result["sample_geometry"]["docs_pass"] == 3
    assert result["sample_geometry"]["docs_fail"] == 3
    assert result["sample_geometry"]["semantic_unique_vector_count"] == 1
    assert result["frozen_w79_semantic_pc1"]["discrimination"] is False
    assert result["frozen_w79_semantic_pc1"]["out_of_support_count"] == 6


def test_w82_full_work_pc1_has_no_exact_outcome_evidence() -> None:
    result = real_result()
    full = result["frozen_w79_full_work_pc1"]
    assert full["out_of_support_count"] == 6
    assert full["docs_failure_auc"] == 0.444444444444
    assert full["exact_permutation_p"] == 1.0
    assert full["exact_permutation_count"] == 20


def test_w82_keeps_pca_bt_and_authority_fail_closed() -> None:
    result = real_result()
    assert result["pc1_predictive_validation"] is False
    assert result["pairwise_outcome_accumulation_permitted"] is False
    assert result["pairwise_events"] == []
    assert result["bt_status"] == "WITHHELD_NO_CONNECTED_OBSERVED_PAIRWISE_GRAPH"
    assert result["pca_refit_performed"] is False
    assert result["timing_pca_reopened"] is False
    assert result["global_allocation_authority"] is False
    assert result["engineering_compliance_release_authority"] is False
    assert result["formal_credit_delta"] == 0
    assert result["engineering_credit_delta"] == 0


def test_w82_probe_was_draft_and_closed_unmerged() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    probe = ledger["source_probe"]
    assert probe["pr"] == 1295
    assert probe["draft_merge_prevention"] is True
    assert probe["disposition"] == "CLOSED_UNMERGED_AFTER_RECEIPT_HARVEST"
