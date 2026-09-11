import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "governance" / "qps_triage" / "DOW_CONTRACT_v1.json"


def _load():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_dow_authority_ceiling_is_fail_closed():
    data = _load()
    authority = data["authority"]
    assert data["repo"] == "GBOGEB/ABACUS"
    assert authority["may_mutate_qps_engineering_truth"] is False
    assert authority["may_mutate_qps_compliance"] is False
    assert authority["may_mutate_qps_negotiation"] is False
    assert authority["final_qps_disposition"] is False


def test_dow_accept_requires_exact_producer_evidence():
    data = _load()
    gate = data["accept_gate"]
    assert gate["producer_exact_sha_match"] is True
    assert gate["producer_receipt_digest_required"] is True
    assert gate["producer_result_must_be_pass_for_accept"] is True
    assert gate["positive_execution_required_when_executable"] is True


def test_dow_disposition_and_reentry_are_explicit():
    data = _load()
    assert data["disposition_enum"] == ["ACCEPT", "REJECT", "DEFER"]
    required = set(data["required_output_fields"])
    assert {"consumer_pr", "consumer_head_sha", "producer_head_sha", "producer_receipt_sha256", "disposition", "child_reentry_target"} <= required
    assert data["predecessor"]["accepted_keb_receipt_pr"] == 1107


def test_repo_deep_files_exist():
    data = _load()
    for key in ("federation_activity", "repo_deep_handoff"):
        assert (ROOT / data["repo_surfaces"][key]).exists(), key
