"""CODE PURPLE / MIP W53: lifecycle, evidence and CLI source penetration.

The five targets were unexecuted by the measured broad-coverage cohort.
External orchestration, subprocess effects and repository writes are mocked.
No mock result conveys merge admission or engineering authority.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _source(relative: str, *, modules=None):
    name = "w53_control_" + relative.replace("/", "_").replace(".", "_")
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    with patch.object(sys, "path", list(sys.path)):
        if modules:
            with patch.dict(sys.modules, modules):
                sys.modules[name] = module
                spec.loader.exec_module(module)
        else:
            sys.modules[name] = module
            spec.loader.exec_module(module)
    return module


def _verify():
    return _source("DMAIC_V3/verify_fixes.py")


def _cli():
    return importlib.import_module("DMAIC_V3.generators.__main__")


def _smoke():
    # The distributed package declares Python >=3.11. On optional 3.10 CI,
    # isolate only its 3.11-specific TOML product-version dependency; all
    # seven self-smoke functions still execute and retain failure semantics.
    if sys.version_info < (3, 11):
        fixture = types.ModuleType("DMAIC_V3.product_version")
        fixture.ABACUS_VERSION = "W53_TEST_FIXTURE_UNQUALIFIED"
        with patch.dict(sys.modules, {"DMAIC_V3.product_version": fixture}):
            return importlib.import_module("DMAIC_V3.self_smoke")
    return importlib.import_module("DMAIC_V3.self_smoke")


def _engine():
    return importlib.import_module("DMAIC_V3.dmaic_v3_engine")


def test_mip_fix_verifier_all_true_and_failing_error_is_not_green(
    monkeypatch, capsys
):
    mod = _verify()
    names = [f"test_fix_{i}_{suffix}" for i, suffix in enumerate(
        [
            "workspace_scope",
            "chunking",
            "improvements",
            "quality_gates",
            "knowledge_extraction",
            "action_collection",
            "todo_scanning",
        ],
        1,
    )]
    for name in names:
        monkeypatch.setattr(mod, name, lambda: True)
    assert mod.main() == 0
    assert "7/7" in capsys.readouterr().out

    def unavailable():
        raise RuntimeError("missing fixture")

    monkeypatch.setattr(mod, names[3], unavailable)
    assert mod.main() == 1
    output = capsys.readouterr().out
    assert "6/7" in output
    assert "missing fixture" in output


def test_generator_cli_missing_command_does_not_execute_source(
    monkeypatch, capsys
):
    mod = _cli()
    monkeypatch.setattr(sys, "argv", ["dmaic-generators"])
    assert mod.main() == 1
    assert "usage:" in capsys.readouterr().out.lower()


def test_generator_cli_dispatch_version_and_error(monkeypatch, capsys):
    mod = _cli()
    monkeypatch.setattr(sys, "argv", ["dmaic-generators", "version"])
    assert mod.main() == 0
    assert "VERSION INFORMATION" in capsys.readouterr().out

    monkeypatch.setattr(sys, "argv", ["dmaic-generators", "align-docs"])
    monkeypatch.setattr(
        mod, "cmd_align_docs", lambda args: (_ for _ in ()).throw(
            RuntimeError("offline alignment")
        ),
    )
    assert mod.main() == 1
    assert "offline alignment" in capsys.readouterr().out


def test_generator_full_run_requires_both_real_stage_contracts(monkeypatch):
    mod = _cli()
    args = SimpleNamespace()
    with (
        patch.object(mod, "cmd_execute", return_value=0),
        patch.object(mod, "cmd_align_docs", return_value=0),
    ):
        assert mod.cmd_full_run(args) == 0
    with (
        patch.object(mod, "cmd_execute", return_value=0),
        patch.object(mod, "cmd_align_docs", return_value=1),
    ):
        assert mod.cmd_full_run(args) == 1


def test_generator_document_alignment_missing_file_is_not_success(
    tmp_path, monkeypatch
):
    mod = _cli()
    args = SimpleNamespace(
        docs_dir=tmp_path, export_json=False, export_yaml=False
    )
    assert mod.cmd_align_docs(args) == 1


def test_smoke_native_sha_is_deterministic_and_probes_observed(tmp_path, monkeypatch):
    mod = _smoke()
    evidence = tmp_path / "sample.bin"
    evidence.write_bytes(b"fixture")
    assert len(mod._sha256(evidence)) == 64

    monkeypatch.setattr(mod, "_git", lambda *args: "a" * 40)
    names = [
        "_probe_import",
        "_probe_config",
        "_probe_ssot",
        "_probe_contract",
        "_probe_orchestrator",
        "_probe_agent_manager",
        "_probe_handover",
    ]
    for name in names:
        monkeypatch.setattr(mod, name, lambda: {"synthetic": True})
    first = mod.run_self_smoke()
    second = mod.run_self_smoke()
    assert first["success"] is True
    assert first["passed"] == first["total"] == 7
    assert first["deterministic_sha256"] == second["deterministic_sha256"]
    assert len(first["deterministic_sha256"]) == 64


def test_smoke_failing_stage_is_reported_with_captured_stdout(monkeypatch):
    mod = _smoke()
    monkeypatch.setattr(mod, "_git", lambda *args: "b" * 40)
    names = [
        "_probe_import",
        "_probe_config",
        "_probe_ssot",
        "_probe_contract",
        "_probe_orchestrator",
        "_probe_agent_manager",
        "_probe_handover",
    ]
    for name in names:
        monkeypatch.setattr(mod, name, lambda: {"positive": True})

    def fails():
        print("native diagnostic")
        raise RuntimeError("missing source")

    monkeypatch.setattr(mod, "_probe_ssot", fails)
    receipt = mod.run_self_smoke()
    assert receipt["passed"] == 6
    assert receipt["success"] is False
    row = next(x for x in receipt["stages"] if x["name"] == "ssot_authority")
    assert row["status"] == "FAIL"
    assert "missing source" in row["error"]
    assert row["captured_stdout"] == "native diagnostic"


def _runner(monkeypatch):
    fake = types.ModuleType("DMAIC_V3.full_pipeline_orchestrator")

    class Orchestrator:
        def __init__(self, *args, **kwargs):
            self.events = iter(())

        def execute_full_pipeline(self, *, iteration):
            return True

    fake.FullPipelineOrchestrator = Orchestrator
    mod = _source(
        "DMAIC_V3/run_3_iterations.py",
        modules={"DMAIC_V3.full_pipeline_orchestrator": fake},
    )
    monkeypatch.setattr(mod.time, "sleep", lambda seconds: None)
    return mod


def test_three_iteration_runner_positive_without_real_orchestration(monkeypatch):
    mod = _runner(monkeypatch)
    instance = SimpleNamespace(execute_full_pipeline=lambda **kwargs: True)
    monkeypatch.setattr(mod, "FullPipelineOrchestrator", lambda **kwargs: instance)
    assert mod.run_3_iterations() is True


def test_three_iteration_runner_mixed_failure_and_exception(monkeypatch, capsys):
    mod = _runner(monkeypatch)
    executed = []

    def run(*, iteration):
        executed.append(iteration)
        if iteration == 2:
            raise RuntimeError("synthetic runner crash")
        return iteration == 1

    monkeypatch.setattr(
        mod,
        "FullPipelineOrchestrator",
        lambda **kwargs: SimpleNamespace(execute_full_pipeline=run),
    )
    assert mod.run_3_iterations() is False
    assert executed == [1, 2, 3]
    assert "crashed" in capsys.readouterr().out


def _fake_engine_config(tmp_path, enabled):
    return SimpleNamespace(
        paths=SimpleNamespace(
            state_dir=tmp_path / "state",
            reports_dir=tmp_path / "reports",
        ),
        knowledge=SimpleNamespace(enabled=enabled),
    )


def test_engine_version_and_single_phase_tuple_success(
    tmp_path, monkeypatch
):
    mod = _engine()
    monkeypatch.setattr(sys, "argv", ["dmaic", "--version"])
    assert mod.main() == 0

    conf = _fake_engine_config(tmp_path, enabled=True)
    monkeypatch.setattr(mod, "DMAICConfig", lambda: conf)
    monkeypatch.setattr(mod, "StateManager", lambda path: object())
    monkeypatch.setattr(
        mod,
        "Phase6Knowledge",
        lambda *args: SimpleNamespace(
            execute=lambda **kwargs: (True, {"status": "synthetic"})
        ),
    )
    monkeypatch.setattr(
        sys, "argv", ["dmaic", "--mode", "single", "--phase", "phase6_knowledge"]
    )
    assert mod.main() == 0
    saved = list((tmp_path / "reports").glob("phase6_results_*.json"))
    assert len(saved) == 1
    assert json.loads(saved[0].read_text(encoding="utf-8"))["status"] == "synthetic"


def test_engine_negative_phase6_result_refuses_false_success(
    tmp_path, monkeypatch
):
    mod = _engine()
    conf = _fake_engine_config(tmp_path, enabled=True)
    monkeypatch.setattr(mod, "DMAICConfig", lambda: conf)
    monkeypatch.setattr(mod, "StateManager", lambda path: object())
    monkeypatch.setattr(
        mod,
        "Phase6Knowledge",
        lambda *args: SimpleNamespace(
            execute=lambda **kwargs: {"error": "synthetic E2E failure"}
        ),
    )
    monkeypatch.setattr(
        sys, "argv", ["dmaic", "--mode", "single", "--phase", "phase6_knowledge"]
    )
    assert mod.main() == 2


def test_engine_full_cycle_phase6_failure_remains_observable_not_crash(
    tmp_path, monkeypatch, capsys
):
    mod = _engine()
    conf = _fake_engine_config(tmp_path, enabled=True)
    monkeypatch.setattr(mod, "DMAICConfig", lambda: conf)
    monkeypatch.setattr(mod, "StateManager", lambda path: object())

    def raise_in_phase(*args):
        raise RuntimeError("synthetic phase 6 failure")

    monkeypatch.setattr(mod, "Phase6Knowledge", raise_in_phase)
    monkeypatch.setattr(sys, "argv", ["dmaic", "--mode", "full"])
    assert mod.main() is None
    assert "Phase 6 execution skipped/failed" in capsys.readouterr().out
