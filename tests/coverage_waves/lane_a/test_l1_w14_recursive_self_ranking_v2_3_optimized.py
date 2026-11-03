"""Lane A wave 14: DOW Stage 5 self-ranking adapter (loaded by path)."""

import json
import sys
from pathlib import Path

import pytest

from tests.coverage_waves.lane_a._load import load

REL = "DMAIC_V3/local_mcp/agents/recursive_self_ranking_v2.3_OPTIMIZED.py"


def _import():
    saved_path = list(sys.path)
    saved_mods = set(sys.modules)
    try:
        return load(REL, name="l1_w14_recursive_self_ranking")
    finally:
        sys.path[:] = saved_path
        for key in set(sys.modules) - saved_mods:
            del sys.modules[key]


rk = _import()


def _artifacts(target):
    target.mkdir()
    (target / "b.json").write_text(
        json.dumps({"validation_results": [1], "x": 2}), encoding="utf-8"
    )
    (target / "a.json").write_text(json.dumps({"x": 1}), encoding="utf-8")
    (target / "notes.txt").write_text("ignored", encoding="utf-8")


def test_module_binds_parent_agent():
    assert rk.__version__ == "3.3.0"
    assert rk.SelfRankingAgent.__name__ == "SelfRankingAgent"
    assert rk.PARENT_RANKING_PATH.name == "self_ranking.py"


def test_load_descriptor(tmp_path):
    p = tmp_path / "d.json"
    p.write_text(json.dumps({"validation_results": []}), encoding="utf-8")
    d = rk._load_descriptor(p)
    assert d == {
        "path": str(p),
        "type": "data",
        "complexity": len('{"validation_results":[]}'),
        "has_tests": False,
    }


def test_loader_raises_when_spec_missing(monkeypatch):
    monkeypatch.setattr(rk, "PARENT_RANKING_PATH", Path("not_a_python_module.txt"))
    with pytest.raises(ImportError, match="Cannot load parent ranking module"):
        rk._load_parent_self_ranking()


def test_run_ranks_json_only(tmp_path):
    target = tmp_path / "t"
    _artifacts(target)
    out = tmp_path / "rank.json"
    payload = rk.run(target, out)
    assert payload["stage"] == 5
    assert payload["total_artifacts"] == 2
    assert payload["engine_version"] == "3.3.0"
    paths = sorted(Path(a["path"]).name for a in payload["ranked_artifacts"])
    assert paths == ["a.json", "b.json"]
    assert json.loads(out.read_text(encoding="utf-8")) == payload


def test_run_errors(tmp_path):
    with pytest.raises(FileNotFoundError):
        rk.run(tmp_path / "missing", tmp_path / "o.json")
    (tmp_path / "empty").mkdir()
    with pytest.raises(ValueError, match="No JSON artifacts"):
        rk.run(tmp_path / "empty", tmp_path / "o.json")


def test_main_ok_and_failures(tmp_path, monkeypatch, capsys):
    target = tmp_path / "t"
    _artifacts(target)
    out = tmp_path / "r.json"
    monkeypatch.setattr(
        sys, "argv", ["rk", "--target", str(target), "--output", str(out)]
    )
    assert rk.main() == 0
    assert "[OK] DOW Stage 5 ranked 2 JSON artifact(s)" in capsys.readouterr().out

    (target / "c.json").write_text("{broken", encoding="utf-8")
    assert rk.main() == 1
    monkeypatch.setattr(sys, "argv", ["rk", "--target", str(tmp_path / "nope")])
    assert rk.main() == 1
    assert capsys.readouterr().out.count("[X] DOW Stage 5 ranking failed") == 2
