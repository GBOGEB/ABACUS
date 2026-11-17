"""Gap tests for src/qplant_presentation_engine/metrics.py."""

import pytest

from src.qplant_presentation_engine import metrics as mod


def test_default_evidence_outside_ci(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    ev = mod._default_evidence()
    assert ev["ci_execution_observed"] is False
    assert ev["repo_artifact_present"] is True
    assert ev["chat_evidence_present"] is False


def test_default_evidence_in_ci(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "TRUE")
    assert mod._default_evidence()["ci_execution_observed"] is True


def test_load_metrics_defaults_outside_ci(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    out = mod.load_metrics()
    assert out["forward_pca"] == 1.0
    assert out["backward_pca"] == pytest.approx(0.6667)
    assert out["truth_score"] == 0.75
    assert out["geti"] == round((1.0 + 0.6667 + 0.75) / 3.0, 4)
    assert out["runtime_ready"] is True
    snap = out["truth_matrix_snapshot"]
    assert len(snap["principles"]) == 4


def test_load_metrics_evidence_override_coerces_to_bool(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    out = mod.load_metrics(
        {
            "repo_artifact_present": 0,
            "runtime_executed": "",
            "validation_ready": None,
            "claimed_runtime_ready": 1,
            "ci_execution_observed": 0,
        }
    )
    assert out["forward_pca"] == 0.0
    assert out["backward_pca"] == 0.0
    assert out["truth_score"] == 0.0
    assert out["runtime_ready"] is False
    ev = out["truth_matrix_snapshot"]["evidence"]
    assert ev["claimed_runtime_ready"] is True
    assert ev["runtime_executed"] is False


def test_load_metrics_empty_mapping_uses_defaults(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    out = mod.load_metrics({})
    assert out["truth_score"] == 1.0
    assert out["geti"] == 1.0
