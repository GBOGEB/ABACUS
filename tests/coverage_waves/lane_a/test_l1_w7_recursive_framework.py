"""Behaviour tests for local_mcp/agents/recursive_framework_v2.3_OPTIMIZED.py."""

import json

import pytest

from tests.coverage_waves.lane_a._load import load

MOD = load("local_mcp/agents/recursive_framework_v2.3_OPTIMIZED.py")
Agent = MOD.MemoryEfficientRecursiveFrameworkV23


@pytest.fixture
def agent(tmp_path):
    return Agent({"output_dir": str(tmp_path / "out"), "max_recursion": 2})


def test_init_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    a = Agent()
    assert a.max_recursion == 3
    assert a.recursion_depth == 0
    assert (tmp_path / "recursive_outputs_v2.3").is_dir()
    assert set(a.hooks) == {
        "pre_recursion",
        "post_recursion",
        "pre_dmaic_phase",
        "post_dmaic_phase",
        "error_handler",
    }
    assert a.dmaic_log[0]["phase"] == "INIT"
    assert a.get_results() == []


def test_register_hook_valid_and_invalid(agent):
    agent.register_hook("pre_recursion", lambda ctx: None)
    assert len(agent.hooks["pre_recursion"]) == 1
    with pytest.raises(ValueError, match="Invalid hook type: bogus"):
        agent.register_hook("bogus", lambda ctx: None)


def test_execute_hooks_counts_and_swallows_errors(agent):
    seen = []

    def ok(ctx):
        seen.append(ctx)

    def bad(ctx):
        raise RuntimeError("hook broke")

    agent.register_hook("error_handler", ok)
    agent.register_hook("error_handler", bad)
    agent._execute_hooks("error_handler")
    agent._execute_hooks("error_handler", {"k": 1})
    agent._execute_hooks("unknown_type", {"k": 2})
    assert seen == [{}, {"k": 1}]
    assert agent.performance_metrics["hooks_executed"] == 2
    assert "hook broke" in agent.dmaic_log[-1]["action"]


def test_log_dmaic_records_depth_and_truncates(agent, capsys):
    agent.recursion_depth = 2
    agent._log_dmaic("X", "act", "y" * 200)
    entry = agent.dmaic_log[-1]
    assert entry["recursion_depth"] == 2
    assert entry["result"] == "y" * 100
    assert "[X][D2] act" in capsys.readouterr().out


def test_measure_and_analyze_scale_with_depth(agent):
    agent.recursion_depth = 1
    m = agent.dmaic_measure({})
    assert m["frameworks_analyzed"] == 10
    assert m["patterns_found"] == 29
    assert m["memory_usage"] == "2.8M"
    a = agent.dmaic_analyze(m)
    assert a["recursion_efficiency"] == pytest.approx(0.82)
    assert agent.performance_metrics["frameworks_processed"] == 10


def test_define_and_control(agent):
    d = agent.dmaic_define({"task_id": "t"})
    assert d["scope"]["max_recursion_depth"] == 2
    c = agent.dmaic_control({})
    assert c["recursion_limits"]["depth_remaining"] == 2
    assert agent.performance_metrics["dmaic_phases_completed"] == 2


def test_improve_without_recursion(agent):
    analysis = agent.dmaic_analyze({})
    imp = agent.dmaic_improve(analysis, {"recursive": False})
    assert imp["optimizations_applied"] == 4
    assert imp["recursive_calls_made"] == 0
    assert imp["patterns_optimized"] == 3
    assert "sub_result" not in imp


def test_improve_recurses_to_max_depth_with_hooks(agent):
    events = []
    agent.register_hook("pre_recursion", lambda c: events.append(("pre", c["depth"])))
    agent.register_hook("post_recursion", lambda c: events.append(("post", c["depth"])))
    analysis = agent.dmaic_analyze({})
    imp = agent.dmaic_improve(analysis, {"task_id": "job", "recursive": True})
    assert imp["recursive_calls_made"] == 1
    sub = imp["sub_result"]
    assert sub["status"] == "success"
    assert sub["recursion_depth"] == 1
    inner = sub["dmaic_results"]["improve"]["sub_result"]
    assert inner["recursion_depth"] == 2
    assert "sub_result" not in inner["dmaic_results"]["improve"]
    assert events == [("pre", 0), ("pre", 1), ("post", 1), ("post", 0)]
    assert agent.recursion_depth == 0
    assert agent.performance_metrics["recursive_calls"] == 2


def test_recursive_task_id_default(agent):
    agent.max_recursion = 1
    captured = []
    agent.register_hook(
        "pre_dmaic_phase",
        lambda c: captured.append(c.get("task", {}).get("task_id")),
    )
    agent.dmaic_improve({}, {"recursive": True})
    assert "task_r1" in captured


def test_recursive_process_error_runs_error_hooks(agent, monkeypatch):
    errors = []
    agent.register_hook("error_handler", lambda c: errors.append(c))

    def boom(_m):
        raise RuntimeError("deep fail")

    monkeypatch.setattr(agent, "dmaic_analyze", boom)
    with pytest.raises(RuntimeError, match="deep fail"):
        agent._recursive_process({"task_id": "t"})
    assert errors == [{"error": "deep fail", "depth": 0}]


def test_run_default_task_success_saves_json(agent, tmp_path):
    result = agent.run()
    assert result["status"] == "success"
    assert result["dmaic_results"]["improve"]["recursive_calls_made"] == 0
    assert result["performance_metrics"]["dmaic_phases_completed"] == 5
    assert result["hooks_registered"]["pre_recursion"] == 0
    assert agent.get_results() == [result]
    files = list((tmp_path / "out").glob("recursive_results_*.json"))
    assert len(files) == 1
    saved = json.loads(files[0].read_text(encoding="utf-8"))
    assert saved["agent"] == "recursive_framework"


def test_run_error_path(agent, monkeypatch, capsys):
    errors = []
    agent.register_hook("error_handler", lambda c: errors.append(c))

    def boom(_m):
        raise RuntimeError("analyze broke")

    monkeypatch.setattr(agent, "dmaic_analyze", boom)
    result = agent.run({"task_id": "t", "recursive": False})
    assert result["status"] == "error"
    assert result["error"] == "analyze broke"
    assert result["performance_metrics"]["errors_handled"] == 1
    assert errors == [{"error": "analyze broke"}]
    assert "ERROR: analyze broke" in capsys.readouterr().out


def test_save_results_failure_warns(agent, tmp_path, capsys):
    agent.output_dir = tmp_path / "missing" / "deeper"
    agent._save_results({"a": 1})
    assert "Warning: Could not save results" in capsys.readouterr().out


def test_main_success(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert MOD.main() == 0
    out = capsys.readouterr().out
    assert "Recursive Calls: 2" in out
    assert list((tmp_path / "recursive_outputs_v2.3").glob("*.json"))


def test_main_error_returns_one(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def boom(self, task):
        raise RuntimeError("x")

    monkeypatch.setattr(Agent, "dmaic_define", boom)
    assert MOD.main() == 1
