"""Lane A wave 7: local_mcp/agent_orchestrator_v3.0.py."""

import json
import types

import pytest

from tests.coverage_waves.lane_a._load import load

orch_mod = load("local_mcp/agent_orchestrator_v3.0.py")
Orchestrator = orch_mod.AgentOrchestratorV3


class _GoodAgent:
    def __init__(self, config=None):
        self.config = config
        self.cleaned = False

    def run(self):
        return {"ok": True, "phase": (self.config or {}).get("phase")}

    def cleanup(self):
        self.cleaned = True


class _EmptyAgent:
    def __init__(self, config=None):
        self.config = config

    def run(self):
        return None


class _BoomAgent:
    def __init__(self, config=None):
        self.config = config

    def run(self):
        raise RuntimeError("kaboom")

    def cleanup(self):
        raise OSError("cleanup failed")


def _fake_module(**classes):
    mod = types.ModuleType("fake_agents")
    for name, cls in classes.items():
        setattr(mod, name, cls)
    return mod


@pytest.fixture
def orch(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return Orchestrator({"output_dir": str(tmp_path / "out")})


def _install_import(monkeypatch, mapping):
    """Stub importlib.import_module; mapping: path fragment -> module or exc."""
    calls = []

    def fake_import(path):
        calls.append(path)
        for key, value in mapping.items():
            if key in path:
                if isinstance(value, Exception):
                    raise value
                return value
        raise ImportError("no module " + path)

    monkeypatch.setattr(orch_mod.importlib, "import_module", fake_import)
    return calls


def _loaded(cls, instance=None):
    return {
        "class": cls,
        "instance": instance,
        "status": "loaded",
        "version": "v2.3.0",
    }


def test_init_defaults_create_output_dir_in_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    o = Orchestrator()
    assert o.config == {}
    assert o.name == "agent_orchestrator"
    assert o.version == "v3.0.0"
    assert (tmp_path / "orchestrator_outputs_v3.0").is_dir()
    assert o.initialized is False
    assert o.performance_metrics["agents_initialized"] == 0


def test_log_dmaic_truncates_result_and_defaults(orch, capsys):
    orch._log_dmaic("P", "act")
    orch._log_dmaic("P", "act2", "x" * 300)
    assert orch.dmaic_log[0]["result"] == "Completed"
    assert len(orch.dmaic_log[1]["result"]) == 100
    assert "[P] act" in capsys.readouterr().out


def test_initialize_agents_mixed_success_and_failure(orch, monkeypatch):
    calls = _install_import(
        monkeypatch,
        {
            "cryo_dm": _fake_module(MemoryEfficientCryoAnalyzerV23=_GoodAgent),
            "document_consumer": ImportError("missing dep"),
            "artifact_analyzer": _fake_module(),
            "smoke_test": _fake_module(MemoryEfficientSmokeTestV23=_EmptyAgent),
        },
    )
    result = orch.initialize_agents()
    assert len(calls) == 4
    assert result["status"] == "initialized"
    assert result["agents_loaded"] == 2
    assert orch.initialized is True
    assert orch.agents["cryo_analyzer"]["status"] == "loaded"
    assert orch.agents["cryo_analyzer"]["class"] is _GoodAgent
    assert orch.agents["document_consumer"] == {
        "status": "failed",
        "error": "missing dep",
    }
    # Module imports but lacks the class -> AttributeError -> failed.
    assert orch.agents["artifact_analyzer"]["status"] == "failed"
    assert orch.performance_metrics["errors_handled"] == 2


def test_production_defect_dotted_module_names_never_import(
    orch, tmp_path, monkeypatch
):
    # Pins a production_defect: the configured module paths contain "v2.3", which
    # import_module reads as sub-package "..._v2" plus module "3_OPTIMIZED", so no
    # agent can ever load even when its file exists. Fails once that is fixed.
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    (pkg_dir / "analysis_smoke_test_v2.3_OPTIMIZED.py").write_bytes(
        b"class MemoryEfficientSmokeTestV23:\n    pass\n"
    )
    root = types.ModuleType("local_mcp")
    root.__path__ = [str(tmp_path)]
    agents = types.ModuleType("local_mcp.agents")
    agents.__path__ = [str(pkg_dir)]
    monkeypatch.setitem(orch_mod.sys.modules, "local_mcp", root)
    monkeypatch.setitem(orch_mod.sys.modules, "local_mcp.agents", agents)
    result = orch.initialize_agents()
    assert result["agents_loaded"] == 0
    assert orch.agents["smoke_test"]["status"] == "failed"
    assert "analysis_smoke_test_v2" in orch.agents["smoke_test"]["error"]


def test_execute_agent_requires_initialization(orch):
    with pytest.raises(RuntimeError, match="not initialized"):
        orch.execute_agent("cryo_analyzer")


def test_execute_agent_unknown_name(orch):
    orch.initialized = True
    with pytest.raises(ValueError, match="not found"):
        orch.execute_agent("ghost")


def test_execute_agent_not_loaded_returns_error(orch):
    orch.initialized = True
    orch.agents["bad"] = {"status": "failed", "error": "x"}
    res = orch.execute_agent("bad")
    assert res == {"status": "error", "agent": "bad", "error": "Agent status: failed"}


def test_execute_agent_success_records_history(orch):
    orch.initialized = True
    orch.agents["good"] = _loaded(_GoodAgent)
    res = orch.execute_agent("good", {"phase": "MEASURE"})
    assert res["status"] == "success"
    assert res["result"] == {"ok": True, "phase": "MEASURE"}
    assert orch.performance_metrics["tasks_executed"] == 1
    assert isinstance(orch.agents["good"]["instance"], _GoodAgent)
    assert orch.execution_history[-1]["status"] == "success"
    assert "ok" in orch.execution_history[-1]["result_summary"]


def test_execute_agent_none_result_and_default_config(orch):
    orch.initialized = True
    orch.agents["empty"] = _loaded(_EmptyAgent)
    res = orch.execute_agent("empty")
    assert res["status"] == "success"
    assert orch.agents["empty"]["instance"].config == {}
    assert orch.execution_history[-1]["result_summary"] == "No result"


def test_execute_agent_exception_is_captured(orch):
    orch.initialized = True
    orch.agents["boom"] = _loaded(_BoomAgent)
    res = orch.execute_agent("boom")
    assert res["status"] == "error"
    assert res["error"] == "kaboom"
    assert "RuntimeError" in res["traceback"]
    assert orch.performance_metrics["errors_handled"] == 1
    assert orch.execution_history[-1]["status"] == "error"


def test_execute_dmaic_cycle_runs_loaded_agents_each_phase(orch):
    orch.initialized = True
    orch.agents["good"] = _loaded(_GoodAgent)
    orch.agents["bad"] = {"status": "failed", "error": "x"}
    res = orch.execute_dmaic_cycle("src.csv")
    assert res["overall_status"] == "completed"
    phases = ["DEFINE", "MEASURE", "ANALYZE", "IMPROVE", "CONTROL"]
    assert list(res["phases"]) == phases
    for phase, data in res["phases"].items():
        assert data["agents_executed"] == 1
        assert data["results"][0]["result"]["phase"] == phase
    assert orch.performance_metrics["dmaic_phases_completed"] == 5
    assert orch.performance_metrics["tasks_executed"] == 5
    assert "total_execution_time" in res


def test_execute_dmaic_cycle_handles_raising_execute(orch, monkeypatch):
    orch.initialized = True
    orch.agents["good"] = _loaded(_GoodAgent)

    def raising(name, cfg=None):
        raise ValueError("bad exec")

    monkeypatch.setattr(orch, "execute_agent", raising)
    res = orch.execute_dmaic_cycle()
    first = res["phases"]["DEFINE"]["results"][0]
    assert first == {"agent": "good", "status": "error", "error": "bad exec"}


def test_get_agent_status_variants(orch):
    orch.agents["good"] = _loaded(_GoodAgent)
    assert orch.get_agent_status("ghost") == {"error": "Agent ghost not found"}
    one = orch.get_agent_status("good")
    assert one["agent"] == "good"
    assert one["info"]["status"] == "loaded"
    assert orch.get_agent_status() == {
        "total_agents": 1,
        "agents": {"good": "loaded"},
        "initialized": False,
    }


def test_get_performance_metrics_is_copy(orch):
    m = orch.get_performance_metrics()
    m["metrics"]["tasks_executed"] = 99
    assert orch.performance_metrics["tasks_executed"] == 0
    assert m["execution_history_count"] == 0
    assert m["uptime_seconds"] >= 0


def test_save_results_default_and_custom_name(orch, tmp_path):
    orch.agents["good"] = _loaded(_GoodAgent)
    orch.agents["bad"] = {"status": "failed", "error": "x"}
    for i in range(60):
        orch._log_dmaic("X", "a" + str(i))
    path = orch.save_results()
    expected = tmp_path / "out" / ("orchestrator_results_" + orch.timestamp + ".json")
    assert path == str(expected)
    data = json.loads(expected.read_text(encoding="utf-8"))
    assert data["orchestrator"]["version"] == "v3.0.0"
    assert data["agents"]["good"] == {"status": "loaded", "version": "v2.3.0"}
    assert data["agents"]["bad"] == {"status": "failed", "version": "unknown"}
    assert len(data["dmaic_log"]) == 50
    custom = orch.save_results("custom.json")
    assert custom == str(tmp_path / "out" / "custom.json")
    assert (tmp_path / "out" / "custom.json").exists()


def test_shutdown_cleans_up_instances_and_saves(orch, tmp_path):
    good = _GoodAgent()
    orch.agents["good"] = _loaded(_GoodAgent, good)
    orch.agents["boom"] = _loaded(_BoomAgent, _BoomAgent())
    orch.agents["plain"] = _loaded(_EmptyAgent, _EmptyAgent())
    orch.agents["none"] = _loaded(_GoodAgent)
    orch.shutdown()
    assert good.cleaned is True
    actions = [e["action"] for e in orch.dmaic_log]
    assert any("Error cleaning up boom" in a for a in actions)
    assert actions[-1] == "Shutdown complete"
    assert list((tmp_path / "out").glob("orchestrator_results_*.json"))


def test_main_success(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _install_import(
        monkeypatch,
        {"smoke_test": _fake_module(MemoryEfficientSmokeTestV23=_EmptyAgent)},
    )
    o = orch_mod.main()
    assert isinstance(o, Orchestrator)
    assert o.performance_metrics["agents_initialized"] == 1
    assert "Orchestrator ready" in capsys.readouterr().out
    assert (tmp_path / "orchestrator_outputs_v3.0").is_dir()


def test_main_returns_none_on_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    def broken(self):
        raise RuntimeError("init broke")

    monkeypatch.setattr(Orchestrator, "initialize_agents", broken)
    assert orch_mod.main() is None
    assert "ERROR: init broke" in capsys.readouterr().out
