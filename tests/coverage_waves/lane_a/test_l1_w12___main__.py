"""Lane A wave 12: delta1_bridge.__main__ CLI."""

import json

import pytest

from delta1_bridge import __main__ as cli
from delta1_bridge import ranking


def _metrics():
    return {
        "timestamp": "t",
        "sha": "s",
        "quality_score": 50,
        "total_commits": 1,
        "python_files": 1,
        "test_files": 1,
        "total_loc": 1,
        "workflows": 1,
        "phase_scores": {},
    }


def test_status_unknown_text_returns_one(tmp_path, capsys):
    assert cli.main(["status", "--repo-root", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "repo    : None" in out
    assert "status  : unknown" in out
    assert "  - could not identify" in out


def test_status_json_degraded_returns_zero(tmp_path, capsys):
    (tmp_path / "DMAIC_V3").mkdir()
    fed = tmp_path / "federation"
    fed.mkdir()
    (fed / "manifest.yaml").write_text("x", encoding="utf-8")
    assert cli.main(["status", "--repo-root", str(tmp_path), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "degraded"
    assert data["repo"] == "GBOGEB/ABACUS"


def test_validate_metrics_valid_and_invalid(tmp_path, capsys):
    good = tmp_path / "good.json"
    good.write_text(json.dumps(_metrics()), encoding="utf-8")
    assert cli.main(["validate-metrics", str(good)]) == 0
    assert json.loads(capsys.readouterr().out)["valid"] is True

    assert cli.main(["validate-metrics", str(tmp_path / "missing.json")]) == 1
    assert json.loads(capsys.readouterr().out)["found"] is False


def test_rank_demo(monkeypatch, capsys):
    monkeypatch.setattr(cli, "CANONICAL_BT_AVAILABLE", False)
    monkeypatch.setattr(ranking, "CANONICAL_BT_AVAILABLE", False)
    monkeypatch.setattr(ranking, "_canonical_fit", None)
    assert cli.main(["rank-demo"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ranking"] == ["artifact_a", "artifact_b", "artifact_c"]
    assert data["canonical_engine_available"] is False
    assert data["engine"] == "fallback"


def test_missing_command_exits(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main([])
    assert exc.value.code == 2
