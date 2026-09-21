from __future__ import annotations
import importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/"architecture/w83/W83_NG1_NON_GOVERNANCE_OUTCOME_LEDGER_v0.1.json"
CANONICAL=ROOT/"architecture/w83/W83_NG1_NON_GOVERNANCE_OUTCOME_DIAGNOSTIC_v0.1.json"

def load_module():
    path=ROOT/"tools/w83_ng1_nongovernance_outcome.py"
    spec=importlib.util.spec_from_file_location("w83_ng1",path)
    assert spec and spec.loader
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def test_canonical_exact_inference_matches():
    m=load_module()
    ledger=json.loads(LEDGER.read_text(encoding="utf-8"))
    expected=json.loads(CANONICAL.read_text(encoding="utf-8"))
    assert m.evaluate(ledger)==expected

def test_negative_small_sample_boundary():
    d=json.loads(CANONICAL.read_text(encoding="utf-8"))
    assert d["status"]=="CONTROLLED_NEGATIVE_NON_GOVERNANCE_OUTCOME_DIAGNOSTIC"
    assert d["sample_geometry"]=={
        "state_count":11,
        "docs_failure_count":8,
        "docs_pass_count":3,
        "unique_semantic_vectors":2,
        "unique_consumer_graph_vectors":6,
        "variable_non_governance_feature_count":16,
        "exact_label_permutation_count":165,
    }
    assert d["inference"]["significant_feature_count"]==0
    assert d["inference"]["signal_supported"] is False
    assert d["interpretation"]["strongest_raw_feature"]=="consumer_graph_distribution.consumer_entities_exactly_one_file"
    assert d["interpretation"]["strongest_raw_auc"]==0.770833
    assert d["interpretation"]["strongest_raw_exact_p"]==0.151515
    assert d["interpretation"]["strongest_holm_p"]==1
    assert d["pca_fit_performed"] is False
    assert d["pairwise_outcome_accumulation_permitted"] is False
    assert d["bt_status"].startswith("WITHHELD_")
    assert d["global_allocation_authority"] is False

def test_governance_features_are_excluded():
    ledger=json.loads(LEDGER.read_text(encoding="utf-8"))
    assert ledger["feature_policy"]["excluded_blocks"]==["workflow_governance_composition"]
    d=json.loads(CANONICAL.read_text(encoding="utf-8"))
    assert all(not row["feature"].startswith("workflow_governance") for row in d["inference"]["feature_results"])
