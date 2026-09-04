from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "federation/qps/QPS_W43_DOW_BRIDGE_RECEIPT_v0.1.yaml"


def test_dow_receipt_is_child_bound_and_zero_credit():
    d = yaml.safe_load(DOC.read_text(encoding="utf-8"))
    assert d["child_anchor"]["pr"] == 383
    assert d["prior_parent_anchor"]["pr"] == 827
    assert d["acknowledged_child_state"]["buildings_utilities_candidate_mapping"] == "26/53"
    assert d["acknowledged_child_state"]["original_MSG_exact_attribution"] == "0/53"
    assert d["zero_credit_statement"]["formal_completion_delta"] == 0
    assert d["zero_credit_statement"]["PCA_engineering_evidence_delta"] == 0
    assert d["child_disposition_required"] is True
    assert d["supersedes_stale_lane"]["pr"] == 828
