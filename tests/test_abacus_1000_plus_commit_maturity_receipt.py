from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "governance" / "ABACUS_1000_PLUS_COMMIT_MATURITY_RECEIPT_v0.1.yaml"


def load_receipt():
    with RECEIPT.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def test_receipt_records_actual_1000_plus_commit_state():
    data = load_receipt()
    repo = data["repository"]

    assert repo["full_name"] == "GBOGEB/ABACUS"
    assert repo["default_branch"] == "main"
    assert repo["observed_main_commit_count"] == 2786
    assert repo["observed_main_commit_count"] > 1000
    assert repo["observed_main_head"] == "10c0ce67f7ba2eb67f474f061bc675be4139ce62"
    assert repo["initial_commit"] == "b549ad1d8696d019ceb4cc73c659660f91258e0c"


def test_receipt_is_not_a_vanity_commit_goal():
    data = load_receipt()
    controlled_meaning = " ".join(data["milestone_interpretation"]["controlled_meaning"].split())

    assert data["milestone_interpretation"]["observed_threshold_state"] == "EXCEEDED"
    assert data["controls"]["no_vanity_commit_goal"] is True
    assert "not to add more commits" in controlled_meaning


def test_parent_maturity_does_not_grant_child_credit():
    data = load_receipt()
    boundary = data["credit_boundary"]

    assert data["controls"]["no_child_credit_from_parent_maturity"] is True
    assert data["controls"]["no_qps_engineering_credit"] is True
    assert data["controls"]["no_qps_negotiation_credit"] is True
    assert data["controls"]["no_child_compliance_credit"] is True
    assert boundary["qps_engineering_closure_credit"] == 0
    assert boundary["qps_negotiation_credit"] == 0
    assert boundary["child_compliance_credit"] == 0


def test_release_readiness_remains_warn_until_measurements_exist():
    data = load_receipt()
    fields = data["receipt_fields"]

    assert fields["source_generated_split"]["status"] == "TODO_MEASURE"
    assert fields["ci_queue_health"]["status"] == "TODO_OBSERVE_CURRENT"
    assert fields["clean_clone_status"]["status"] == "BLOCKED_OR_PENDING_LOCAL_EVIDENCE"
    assert fields["legacy_binary_status"]["status"] == "TODO_CLASSIFY"
    assert fields["release_readiness"]["status"] == "WARN"


def test_linked_control_issues_are_preserved():
    data = load_receipt()
    linked = data["receipt_fields"]["open_control_issues"]["linked"]

    assert linked["queue_fanout_control"] == 776
    assert linked["clean_clone_reproducibility"] == 635
    assert linked["ci_semantic_reproducibility_legacy_audit"] == 638
