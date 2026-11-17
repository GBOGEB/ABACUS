"""Gap tests for src/qplant_presentation_engine/truth_score.py."""

import pytest

from src.qplant_presentation_engine import truth_score as mod


@pytest.mark.parametrize(
    "rule,evidence,expected",
    [
        ("chat_is_not_repo", {"repo_artifact_present": True}, True),
        (
            "chat_is_not_repo",
            {"repo_artifact_present": True, "chat_evidence_present": True},
            False,
        ),
        ("chat_is_not_repo", {}, False),
        ("architecture_is_not_runtime", {"runtime_executed": True}, True),
        (
            "architecture_is_not_runtime",
            {"runtime_executed": True, "architecture_only_evidence": True},
            False,
        ),
        ("claimed_is_not_validated", {}, True),
        ("claimed_is_not_validated", {"claimed_runtime_ready": True}, False),
        (
            "claimed_is_not_validated",
            {"claimed_runtime_ready": True, "validation_ready": True},
            True,
        ),
        ("exists_in_repo_is_not_ci_execution", {"ci_execution_observed": True}, True),
        ("exists_in_repo_is_not_ci_execution", {}, False),
        ("unknown_rule", {"ci_execution_observed": True}, False),
    ],
)
def test_evaluate_rule(rule, evidence, expected):
    row = mod._evaluate_rule(rule, evidence)
    assert row == {
        "principle": rule,
        "satisfied": expected,
        "score": 1.0 if expected else 0.0,
    }


def test_snapshot_partial_score():
    evidence = {
        "repo_artifact_present": True,
        "runtime_executed": True,
        "claimed_runtime_ready": True,
        "validation_ready": False,
    }
    snap = mod.build_truth_matrix_snapshot(evidence)
    # chat ok, architecture ok, claimed fails, ci fails -> 2/4
    assert snap["truth_score"] == 0.5
    assert [r["principle"] for r in snap["principles"]] == list(mod.TRUTH_RULES)
    assert snap["evidence"] == evidence
    assert snap["evidence"] is not evidence


def test_snapshot_full_score():
    evidence = {
        "repo_artifact_present": True,
        "runtime_executed": True,
        "ci_execution_observed": True,
    }
    assert mod.build_truth_matrix_snapshot(evidence)["truth_score"] == 1.0


def test_snapshot_with_no_rules(monkeypatch):
    monkeypatch.setattr(mod, "TRUTH_RULES", [])
    snap = mod.build_truth_matrix_snapshot({"x": True})
    assert snap == {"truth_score": 0.0, "principles": [], "evidence": {"x": True}}
