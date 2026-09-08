from tools.generic_3pm_burndown import (
    build_plan,
    preservation_disposition,
    stable_item_id,
)


def test_stable_item_id_is_order_independent_and_deduplicated():
    a = {"scope": "GBOGEB/ABACUS", "type": "duplicate_family", "members": ["b.yml", "a.yml"]}
    b = {"scope": "GBOGEB/ABACUS", "type": "duplicate_family", "members": ["a.yml", "b.yml"]}
    assert stable_item_id(a) == stable_item_id(b)
    plan = build_plan({"items": [a, b]})
    assert plan["item_count"] == 1
    assert len(plan["items"][0]["subtasks"]) == 5


def test_runner_relationship_hints_link_code_to_docs_and_workflows():
    item = {
        "scope": "GBOGEB/ABACUS",
        "type": "duplicate_family",
        "members": ["tools/census.py", "docs/census.md", "config/census.yaml"],
    }
    hints = build_plan({"items": [item]})["items"][0]["relationship_hints"]
    edges = {hint["edge"] for hint in hints}
    assert "documents" in edges
    assert "implemented_by" in edges
    assert "workflow_invokes" in edges


def test_preservation_gate_quarantines_when_information_not_reintroduced():
    decision = preservation_disposition(
        {
            "duplicate_or_obsolete_role_proven": True,
            "unique_information_atoms": ["A", "B"],
            "reintroduction_targets": ["canonical:A"],
            "reintroduction_proof": "PASS",
            "canonical_target_lineaged": True,
            "post_reintroduction_tests_passed": True,
            "consumer_dependency_check": "PASS_NO_REQUIRED_CONSUMER",
        }
    )
    assert decision["disposition"] == "QUARANTINE"
    assert decision["remove_eligible"] is False


def test_preservation_gate_allows_remove_only_after_full_proof():
    decision = preservation_disposition(
        {
            "duplicate_or_obsolete_role_proven": True,
            "unique_information_atoms": ["A", "B"],
            "reintroduction_targets": ["canonical:A", "canonical:B"],
            "reintroduction_proof": "PASS",
            "canonical_target_lineaged": True,
            "post_reintroduction_tests_passed": True,
            "consumer_dependency_check": "PASS_NO_REQUIRED_CONSUMER",
        }
    )
    assert decision["disposition"] == "REMOVE_ELIGIBLE"
    assert decision["quarantine_required"] is False
