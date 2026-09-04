import json
from pathlib import Path


RESULT = Path("federation/triage/qps_w44_dow_execution_result.json")


def test_qps_w44_dow_result_rebases_and_fails_closed():
    data = json.loads(RESULT.read_text(encoding="utf-8"))
    assert data["source_child"]["pr"] == 388
    assert data["source_child"]["merge_sha"] == "29c2fb587403c5ccab690392026a51ecd8fd92d8"
    assert data["supersedes_contract_child_anchor"]["pr"] == 383
    assert len(data["executed_stages"]) == 6
    assert data["formal_credit_delta"] == 0
    dispositions = {f["recommended_child_disposition"] for f in data["actionable_findings"] + data["blocked_findings"]}
    assert "DEFER_PENDING_SOURCE" in dispositions
    assert "DUPLICATE_EXISTING_WORK" in dispositions
