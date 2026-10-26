"""Tests for the delta1_bridge shared adapter.

Run from any repo that vendors delta1_bridge:
    pytest delta1_bridge/tests/test_delta1_bridge.py -q
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from delta1_bridge import (
    validate_metrics,
    load_and_validate_metrics,
    federation_status,
    detect_repo,
    assimilate,
    fit_bradley_terry,
    rank_pairwise,
    DMAIC_METRICS_REQUIRED_KEYS,
)


# --------------------------------------------------------------------------- #
# schema
# --------------------------------------------------------------------------- #
VALID_METRICS = {
    "timestamp": "2026-10-23T12:58:56Z",
    "sha": "e20797a79677",
    "quality_score": 100,
    "total_commits": 6432,
    "python_files": 853,
    "test_files": 262,
    "total_loc": 105822,
    "workflows": 164,
    "phase_scores": {
        "define": {"files": 142, "score": 100, "weight": 20},
        "measure": {"files": 241, "score": 100, "weight": 20},
    },
}


def test_valid_metrics_has_no_issues():
    assert validate_metrics(VALID_METRICS) == []


def test_missing_key_detected():
    broken = {k: v for k, v in VALID_METRICS.items() if k != "sha"}
    issues = validate_metrics(broken)
    assert any("sha" in i for i in issues)


def test_quality_score_out_of_range():
    bad = dict(VALID_METRICS, quality_score=150)
    assert any("quality_score" in i for i in validate_metrics(bad))


def test_non_numeric_detected():
    bad = dict(VALID_METRICS, total_loc="lots")
    assert any("total_loc" in i for i in validate_metrics(bad))


def test_required_keys_constant_covers_badges():
    for key in ("quality_score", "workflows", "phase_scores"):
        assert key in DMAIC_METRICS_REQUIRED_KEYS


def test_load_and_validate_roundtrip(tmp_path):
    p = tmp_path / "metrics.json"
    p.write_text(json.dumps(VALID_METRICS), encoding="utf-8")
    result = load_and_validate_metrics(p)
    assert result["found"] and result["valid"] and result["issues"] == []


def test_load_missing_file(tmp_path):
    result = load_and_validate_metrics(tmp_path / "nope.json")
    assert not result["found"] and not result["valid"]


# --------------------------------------------------------------------------- #
# adapter
# --------------------------------------------------------------------------- #
def _make_fake_codex(root: Path):
    (root / "src").mkdir(parents=True)
    (root / "src" / "bridge_adapter.py").write_text("# marker", encoding="utf-8")
    (root / "KEB" / "governance").mkdir(parents=True)
    (root / "KEB" / "governance" / "GLOSSARY.yml").write_text("x: 1", encoding="utf-8")
    (root / "docs" / "api").mkdir(parents=True)
    (root / "docs" / "api" / "metrics.json").write_text(
        json.dumps(VALID_METRICS), encoding="utf-8")
    (root / "federation").mkdir()
    (root / "federation" / "manifest.yaml").write_text("federation: DELTA_1", encoding="utf-8")


def test_detect_and_status_ok(tmp_path):
    _make_fake_codex(tmp_path)
    desc = detect_repo(tmp_path)
    assert desc is not None and desc.repo == "GBOGEB/CODEX"
    status = federation_status(tmp_path)
    assert status["status"] == "ok"
    assert status["plane"] == "governance"
    assert status["manifest_found"] is True
    assert status["metrics"]["valid"] is True


def test_status_degraded_when_metrics_missing(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "federation.py").write_text("# marker", encoding="utf-8")
    (tmp_path / "ocd-adr").mkdir()
    (tmp_path / "federation").mkdir()
    (tmp_path / "federation" / "manifest.yaml").write_text("x: 1", encoding="utf-8")
    status = federation_status(tmp_path)
    assert status["repo"] == "GBOGEB/cryoplant-project"
    assert status["status"] == "degraded"  # manifest present, metrics absent


def test_status_unknown_on_empty_dir(tmp_path):
    assert federation_status(tmp_path)["status"] == "unknown"


def test_assimilate_carries_context(tmp_path):
    _make_fake_codex(tmp_path)
    result = assimilate({"session": "s1"}, repo_root=tmp_path)
    assert result["context"] == {"session": "s1"}
    assert result["status"] == "ok"


# --------------------------------------------------------------------------- #
# ranking
# --------------------------------------------------------------------------- #
def test_bradley_terry_orders_dominant_first():
    ids = ["a", "b", "c"]
    comparisons = [
        {"a": "a", "b": "b", "a_score": 2, "b_score": 1},
        {"a": "a", "b": "c", "a_score": 3, "b_score": 1},
        {"a": "b", "b": "c", "a_score": 2, "b_score": 1},
    ]
    result = fit_bradley_terry(ids, comparisons)
    assert result["ranking"][0] == "a"
    assert result["ranking"][-1] == "c"
    assert set(result["strengths"]) == set(ids)


def test_rank_pairwise_returns_list():
    ids = ["x", "y"]
    comparisons = [{"a": "x", "b": "y", "a_score": 1, "b_score": 0}]
    assert rank_pairwise(ids, comparisons) == ["x", "y"]


def test_bradley_terry_rejects_bad_input():
    with pytest.raises(ValueError):
        fit_bradley_terry(["only_one"], [])
