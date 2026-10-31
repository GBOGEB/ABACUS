"""Behaviour tests for staging/GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py.

The ``DOW`` package does not exist in the repo and the real DMAIC_V3
orchestrators run full pipelines, so both are replaced by in-memory stubs
supplied through the loader's ``deps`` (visible only during import). The
module is loaded twice: once with DMAIC stubs and once with the DMAIC import
failing, to exercise the limited (DOW-only) mode.
"""

import enum
import functools
import json
import logging
import runpy
import sys
import types

import pytest
import yaml

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

REL = "staging/GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py"


class FakeSUTMode(enum.Enum):
    FULL = "full"
    MINIMAL = "minimal"


class FakeSUTConfig:
    def __init__(self, mode):
        self.mode = mode


class FakeRunner:
    def __init__(self, sut_config, dmaic_phases, iterations, output_dir):
        self.sut_config = sut_config
        self.dmaic_phases = dmaic_phases
        self.iterations = iterations
        self.output_dir = output_dir
        self.iter_calls = []

    def run_pipeline(self):
        return {"pipeline": "dow", "iterations": self.iterations}

    def _run_iteration(self, iteration, history):
        self.iter_calls.append((iteration, list(history)))
        return {"dow_iteration": iteration}


class FakeController:
    pass


class FakeOrchestrator:
    def __init__(self, enable_idempotency_flag, enable_git_commits, verbose):
        self.kwargs = dict(
            enable_idempotency_flag=enable_idempotency_flag,
            enable_git_commits=enable_git_commits,
            verbose=verbose,
        )
        self.calls = []

    def execute_full_pipeline(self, iteration):
        self.calls.append(iteration)
        return iteration % 2 == 0


def _deps(dmaic):
    dow = types.ModuleType("DOW")
    dow.__path__ = []
    runner_mod = types.ModuleType("DOW.pipeline_runner")
    runner_mod.DOWPipelineRunner = FakeRunner
    sut_mod = types.ModuleType("DOW.sut_config")
    sut_mod.SUTConfig = FakeSUTConfig
    sut_mod.SUTMode = FakeSUTMode
    deps = {"DOW": dow, "DOW.pipeline_runner": runner_mod, "DOW.sut_config": sut_mod}
    if dmaic:
        pc = types.ModuleType("DMAIC_V3.pipeline_control")
        pc.PipelineController = FakeController
        fpo = types.ModuleType("DMAIC_V3.full_pipeline_orchestrator")
        fpo.FullPipelineOrchestrator = FakeOrchestrator
        deps["DMAIC_V3.pipeline_control"] = pc
        deps["DMAIC_V3.full_pipeline_orchestrator"] = fpo
    else:
        deps["DMAIC_V3.pipeline_control"] = None
    return deps


def _load(name, dmaic):
    saved_path = list(sys.path)
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    try:
        return load(REL, name=name, deps=_deps(dmaic))
    finally:
        sys.path[:] = saved_path
        root.handlers[:] = saved_handlers
        root.setLevel(saved_level)


mod = _load("abn_w4_gbogeb_bridge_full", dmaic=True)
lim = _load("abn_w4_gbogeb_bridge_limited", dmaic=False)


# The bridge opens its report with the locale encoding but writes U+2194; on a
# cp1252 locale (Windows CI) that crashes (see the production_defect test).
# Behaviour tests pin the module-level ``open`` to UTF-8 so they run on any OS.
_UTF8_OPEN = functools.partial(open, encoding="utf-8")


def _bridge(module, tmp_path, monkeypatch, **kwargs):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module, "open", _UTF8_OPEN, raising=False)
    kwargs.setdefault("output_dir", "out")
    kwargs.setdefault("sut_mode", FakeSUTMode.FULL)
    config = module.IntegrationConfig(**kwargs)
    return module.GBOGEBAbacusDOWBridge(config=config)


def _outputs(tmp_path, pattern):
    return sorted((tmp_path / "out").glob(pattern))


def test_import_modes_and_no_leaks():
    assert mod.DMAIC_AVAILABLE is True
    assert lim.DMAIC_AVAILABLE is False
    assert "DOW.pipeline_runner" not in sys.modules
    assert [m.value for m in mod.IntegrationMode] == [
        "dow_only",
        "dmaic_only",
        "unified",
        "parallel",
        "sequential",
    ]


def test_config_defaults_and_to_dict():
    cfg = mod.IntegrationConfig()
    assert cfg.mode is mod.IntegrationMode.UNIFIED
    assert cfg.sut_mode is FakeSUTMode.FULL
    assert cfg.dmaic_phases == [0, 1, 2, 3, 4]
    assert cfg.to_dict() == {
        "mode": "unified",
        "sut_mode": "full",
        "dmaic_phases": [0, 1, 2, 3, 4],
        "iterations": 3,
        "enable_agents": True,
        "enable_convergence": True,
        "enable_git_commits": True,
        "enable_idempotency": True,
        "output_dir": "INTEGRATED_OUTPUT",
        "handover_dir": "gbogeg_handover",
    }


def test_config_to_dict_stringifies_plain_sut_mode():
    cfg = mod.IntegrationConfig(sut_mode="partial", dmaic_phases=[1])
    out = cfg.to_dict()
    assert out["sut_mode"] == "partial"
    assert out["dmaic_phases"] == [1]


def test_init_wires_dow_and_dmaic_components(tmp_path, monkeypatch):
    bridge = _bridge(mod, tmp_path, monkeypatch, iterations=2, enable_git_commits=False)
    assert (tmp_path / "out").is_dir()
    runner = bridge.dow_runner
    assert isinstance(runner, FakeRunner)
    assert runner.sut_config.mode is FakeSUTMode.FULL
    assert runner.iterations == 2
    assert runner.dmaic_phases == [0, 1, 2, 3, 4]
    assert runner.output_dir.replace("\\", "/") == "out/dow_outputs"
    assert isinstance(bridge.dmaic_controller, FakeController)
    assert bridge.dmaic_orchestrator.kwargs == dict(
        enable_idempotency_flag=True, enable_git_commits=False, verbose=True
    )
    assert bridge.metrics["total_executions"] == 0


def test_init_limited_mode_has_no_dmaic(tmp_path, monkeypatch):
    bridge = _bridge(lim, tmp_path, monkeypatch)
    assert isinstance(bridge.dow_runner, FakeRunner)
    assert bridge.dmaic_controller is None
    assert bridge.dmaic_orchestrator is None


def test_dow_only_completes_and_persists_results(tmp_path, monkeypatch):
    bridge = _bridge(
        mod, tmp_path, monkeypatch, mode=mod.IntegrationMode.DOW_ONLY, iterations=1
    )
    res = bridge.execute_integrated_pipeline()
    assert res["status"] == "completed"
    assert res["dow_results"] == {"pipeline": "dow", "iterations": 1}
    assert res["dmaic_results"] is None
    assert res["metrics"]["successful_executions"] == 1
    assert res["metrics"]["total_executions"] == 1
    assert res["duration_seconds"] >= 0
    saved = _outputs(tmp_path, "integration_results_*.json")
    assert len(saved) == 1
    on_disk = json.loads(saved[0].read_text(encoding="utf-8"))
    assert on_disk["integration_mode"] == "dow_only"
    assert on_disk["config"]["iterations"] == 1
    report = _outputs(tmp_path, "integration_report_*.md")[0].read_text(
        encoding="utf-8"
    )
    assert "**Integration Mode:** dow_only" in report
    assert "**Status:** COMPLETED" in report
    assert "| Total Iterations | 1 |" in report


def test_dmaic_only_counts_successful_iterations(tmp_path, monkeypatch):
    bridge = _bridge(
        mod, tmp_path, monkeypatch, mode=mod.IntegrationMode.DMAIC_ONLY, iterations=3
    )
    res = bridge.execute_integrated_pipeline()
    assert res["status"] == "completed"
    dm = res["dmaic_results"]
    assert dm["total_iterations"] == 3
    assert dm["successful_iterations"] == 2
    assert [r["success"] for r in dm["iterations"]] == [True, False, True]
    assert bridge.dmaic_orchestrator.calls == [0, 1, 2]


def test_dmaic_only_without_dmaic_fails(tmp_path, monkeypatch):
    bridge = _bridge(lim, tmp_path, monkeypatch, mode=lim.IntegrationMode.DMAIC_ONLY)
    res = bridge.execute_integrated_pipeline()
    assert res["status"] == "failed"
    assert res["error"] == "DMAIC components not available"
    assert bridge.metrics["failed_executions"] == 1
    assert bridge.metrics["successful_executions"] == 0
    report = _outputs(tmp_path, "integration_report_*.md")[0].read_text(
        encoding="utf-8"
    )
    assert "**Status:** FAILED" in report


def test_unified_converges_and_collects_artifacts(tmp_path, monkeypatch):
    bridge = _bridge(mod, tmp_path, monkeypatch, iterations=4)
    (tmp_path / "out" / "a_iteration_0.txt").write_bytes(b"12345")
    (tmp_path / "out" / "dir_iteration_1").mkdir()
    res = bridge.execute_integrated_pipeline()
    assert res["status"] == "completed"
    uni = res["unified_results"]
    assert [it["iteration"] for it in uni["iterations"]] == [0, 1, 2, 3]
    assert [c["converged"] for c in uni["convergence_history"]] == [
        False,
        False,
        False,
        True,
    ]
    assert uni["convergence_history"][-1]["reason"] == "convergence_threshold_met"
    assert uni["iterations"][1]["dmaic_phase"]["success"] is False
    assert uni["iterations"][0]["dow_phase"] == {"dow_iteration": 0}
    assert [a["iteration"] for a in uni["artifacts_generated"]] == [0]
    art = uni["artifacts_generated"][0]
    assert art["path"].replace("\\", "/") == "out/a_iteration_0.txt"
    assert art["size"] == 5
    assert bridge.metrics["convergence_achieved"] is True
    assert bridge.metrics["total_artifacts_processed"] == 1
    assert [c[0] for c in bridge.dow_runner.iter_calls] == [0, 1, 2, 3]


def test_unified_limited_without_convergence(tmp_path, monkeypatch):
    bridge = _bridge(lim, tmp_path, monkeypatch, iterations=2, enable_convergence=False)
    res = bridge.execute_integrated_pipeline()
    uni = res["unified_results"]
    assert len(uni["iterations"]) == 2
    assert all(it["dmaic_phase"] is None for it in uni["iterations"])
    assert all(it["convergence"] is None for it in uni["iterations"])
    assert uni["convergence_history"] == []
    assert bridge.metrics["convergence_achieved"] is False


@pytest.mark.parametrize("module_name", ["mod", "lim"])
def test_parallel_mode(tmp_path, monkeypatch, module_name):
    module = mod if module_name == "mod" else lim
    bridge = _bridge(
        module,
        tmp_path,
        monkeypatch,
        mode=module.IntegrationMode.PARALLEL,
        iterations=1,
    )
    res = bridge.execute_integrated_pipeline()
    assert res["status"] == "completed"
    assert res["execution_mode"] == "parallel"
    assert res["dow_results"] == {"pipeline": "dow", "iterations": 1}
    if module_name == "mod":
        assert res["dmaic_results"]["total_iterations"] == 1
    else:
        assert res["dmaic_results"] is None


@pytest.mark.parametrize("module_name", ["mod", "lim"])
def test_sequential_mode(tmp_path, monkeypatch, module_name):
    module = mod if module_name == "mod" else lim
    bridge = _bridge(
        module,
        tmp_path,
        monkeypatch,
        mode=module.IntegrationMode.SEQUENTIAL,
        iterations=2,
    )
    res = bridge.execute_integrated_pipeline()
    assert res["execution_mode"] == "sequential"
    if module_name == "mod":
        assert res["dmaic_results"]["successful_iterations"] == 1
    else:
        assert res["dmaic_results"] is None


def test_unrecognised_mode_runs_nothing_but_completes(tmp_path, monkeypatch):
    bridge = _bridge(mod, tmp_path, monkeypatch)
    bridge.config.mode = types.SimpleNamespace(value="custom")
    res = bridge.execute_integrated_pipeline()
    assert res["status"] == "completed"
    assert res["integration_mode"] == "custom"
    assert res["dow_results"] is None
    assert res["unified_results"] is None


def test_runner_exception_marks_failure(tmp_path, monkeypatch):
    bridge = _bridge(mod, tmp_path, monkeypatch, mode=mod.IntegrationMode.DOW_ONLY)

    def boom():
        raise RuntimeError("runner exploded")

    monkeypatch.setattr(bridge.dow_runner, "run_pipeline", boom)
    res = bridge.execute_integrated_pipeline()
    assert res["status"] == "failed"
    assert res["error"] == "runner exploded"
    assert res["metrics"]["failed_executions"] == 1
    assert res["metrics"]["total_executions"] == 1


def test_check_convergence_thresholds(tmp_path, monkeypatch):
    bridge = _bridge(mod, tmp_path, monkeypatch, iterations=3)
    assert bridge._check_convergence([{}]) == {
        "converged": False,
        "confidence": 0.0,
        "reason": "insufficient_data",
    }
    two = bridge._check_convergence([{}, {}])
    assert two["converged"] is False
    assert two["reason"] == "still_improving"
    assert two["confidence"] == pytest.approx(2 / 3)
    five = bridge._check_convergence([{}] * 5)
    assert five["converged"] is True
    assert five["iterations_analyzed"] == 3
    assert five["total_iterations"] == 5
    assert five["confidence"] == 1.0


def test_assimilate_missing_handover(tmp_path, monkeypatch):
    bridge = _bridge(mod, tmp_path, monkeypatch, handover_dir="nope")
    assert bridge.assimilate_handover_package() == {
        "status": "not_found",
        "path": "nope",
    }


def test_assimilate_full_handover(tmp_path, monkeypatch):
    bridge = _bridge(mod, tmp_path, monkeypatch, handover_dir="ho")
    ho = tmp_path / "ho"
    ho.mkdir()
    for name in ["Chapter_1.md", "Chapter_2.md", "notes.md", "glob.yaml", "README.md"]:
        (ho / name).write_bytes(b"x")
    res = bridge.assimilate_handover_package()
    assert res["status"] == "completed"
    assert res["files_processed"] == 2
    assert sorted(res["chapters_integrated"]) == ["Chapter_1.md", "Chapter_2.md"]
    assert res["glob_config_merged"] is True
    assert res["documentation_updated"] is True


def test_assimilate_empty_handover(tmp_path, monkeypatch):
    bridge = _bridge(mod, tmp_path, monkeypatch, handover_dir="ho")
    (tmp_path / "ho").mkdir()
    res = bridge.assimilate_handover_package()
    assert res["status"] == "completed"
    assert res["files_processed"] == 0
    assert res["glob_config_merged"] is False
    assert res["documentation_updated"] is False


def test_create_unified_glob_config_writes_yaml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = mod.create_unified_glob_config()
    on_disk = yaml.safe_load(
        (tmp_path / "UNIFIED_GLOB_CONFIG.yaml").read_text(encoding="utf-8")
    )
    assert on_disk["project"]["name"] == "DOW-GBOGEB-ABACUS-UNIFIED"
    assert on_disk["integration"]["modes"] == [m.value for m in mod.IntegrationMode]
    assert on_disk["directories"] == cfg["directories"]
    assert cfg["workflows"]["dow_pipeline"] == "DOW/pipeline_runner.py"


def test_main_cli_assimilate_glob_and_run(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mod, "open", _UTF8_OPEN, raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "bridge",
            "--mode",
            "dow_only",
            "--iterations",
            "1",
            "--output-dir",
            "cli_out",
            "--assimilate",
            "--create-glob",
        ],
    )
    res = mod.main()
    assert res["status"] == "completed"
    assert res["config"]["output_dir"] == "cli_out"
    assert (tmp_path / "UNIFIED_GLOB_CONFIG.yaml").is_file()
    assert list((tmp_path / "cli_out").glob("integration_results_*.json"))
    out = capsys.readouterr().out
    assert "Assimilation Results" in out
    assert '"status": "not_found"' in out
    assert "Unified Glob Config" in out
    assert "INTEGRATION COMPLETE" in out
    assert "Status: COMPLETED" in out
    assert "Artifacts: 0" in out


def test_main_cli_rejects_unknown_mode(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["bridge", "--mode", "bogus"])
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 2


def test_dunder_main_runs_default_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    for key, value in _deps(dmaic=False).items():
        monkeypatch.setitem(sys.modules, key, value)
    monkeypatch.setattr(sys, "path", list(sys.path))
    root = logging.getLogger()
    monkeypatch.setattr(root, "handlers", list(root.handlers))
    monkeypatch.setattr(sys, "argv", ["bridge", "--iterations", "1"])
    runpy.run_path(
        str(REPO_ROOT / REL), init_globals={"open": _UTF8_OPEN}, run_name="__main__"
    )
    assert "Status: COMPLETED" in capsys.readouterr().out
    assert list((tmp_path / "INTEGRATED_OUTPUT").glob("integration_report_*.md"))


def test_production_defect_report_crashes_on_non_utf8_locale(tmp_path, monkeypatch):
    """production_defect: integration report is written with the locale encoding but contains U+2194, so it crashes on cp1252 (Windows); this test fails once fixed"""
    bridge = _bridge(mod, tmp_path, monkeypatch)

    def cp1252_locale_open(*args, **kwargs):
        # Model a cp1252 locale: only an explicit encoding= argument overrides it.
        kwargs.setdefault("encoding", "cp1252")
        return open(*args, **kwargs)

    monkeypatch.setattr(mod, "open", cp1252_locale_open, raising=False)
    results = {
        "integration_mode": "unified",
        "status": "completed",
        "config": bridge.config.to_dict(),
    }
    with pytest.raises(UnicodeEncodeError):
        bridge._generate_integration_report(results)
