import json
from pathlib import Path


CONTRACT = Path("federation/triage/qps_w43_dow_execution_contract.json")


def test_qps_w43_dow_contract_requires_real_execution_truth():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert data["role"] == "DOW_ANALYSIS_RUNTIME"
    assert data["execution"]["mode"] == "PARALLEL_WITH_KEB"
    assert len(data["execution"]["required_stages"]) == 6
    assert data["execution"]["required_stages"][-2:] == ["self_ranking", "validation"]
    assert data["formal_credit_delta"] == 0

    required = set(data["return_schema"]["required"])
    assert {"source_child_sha", "executed_stages", "actionable_findings", "blocked_findings", "return_hash"} <= required
    assert data["input_control"]["buildings_utilities_candidate_mapping"] == "26/53 = 49.06%"
    assert data["input_control"]["raw_msg_exact_attribution"] == "0/53 pending"
