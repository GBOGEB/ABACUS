"""W76 source-bound breadth tests for historically zero-covered modules.

All I/O uses synthetic tmp_path fixtures, fake packages, and isolated mocks.
No GitHub dispatch, bidder data, deployment, approval, or authority transfer.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str, name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fake_package(name: str) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__path__ = []
    return module


def load_with_siblings(
    relative: str, package: str, siblings: dict[str, dict]
) -> types.ModuleType:
    modules = {package: fake_package(package)}
    for sibling, attributes in siblings.items():
        module = types.ModuleType(f"{package}.{sibling}")
        module.__dict__.update(attributes)
        modules[module.__name__] = module
    with mock.patch.dict(sys.modules, modules):
        return load(relative, f"{package}.{Path(relative).stem}")


def test_notebook_parser_native_cells_and_binary_sanitization(tmp_path):
    m = load("integration/codespace_jyperter/notebook_parser.py", "w76_notebook")
    notebook = tmp_path / "synthetic.ipynb"
    data = {
        "nbformat": 4,
        "metadata": {
            "kernelspec": {"display_name": "Synthetic", "language": "python"},
            "language_info": {"name": "python"},
        },
        "cells": [
            {
                "cell_type": "code",
                "source": ["print(", "'ok')"],
                "execution_count": 1,
                "metadata": {"tags": ["fixture"]},
                "outputs": [
                    {
                        "data": {
                            "text/plain": "ok",
                            "image/png": "redacted",
                            "application/octet-stream": "redacted",
                        }
                    },
                    "untrusted-output",
                ],
            },
            {"cell_type": "markdown", "source": "# Notes"},
            {"cell_type": "raw", "source": ["synthetic"]},
            {"cell_type": "unknown", "source": []},
        ],
    }
    notebook.write_text(json.dumps(data), encoding="utf-8")
    result = m.NotebookParser().parse(notebook)
    assert result["notebook_sha256"] == hashlib.sha256(notebook.read_bytes()).hexdigest()
    assert result["cell_count"] == 4
    assert (result["code_cell_count"], result["markdown_cell_count"]) == (1, 1)
    assert result["raw_cell_count"] == 1
    assert result["cells"][0]["source"] == "print('ok')"
    assert result["cells"][0]["outputs"][0]["data"] == {"text/plain": "ok"}
    parser = m.NotebookParser()
    saved = parser.save_extract(result, tmp_path / "out", iteration=0)
    assert saved.name == "notebook_cells_synthetic_iter0.json"
    assert json.loads(saved.read_text())["cell_count"] == 4
    assert parser.save_extract(result, tmp_path / "out").exists()
    knowledge = parser.build_knowledge_source(result)
    assert knowledge["source_id"].endswith(result["notebook_sha256"][:8])
    assert parser.build_knowledge_source(result, source_id="owner:test")["source_id"] == (
        "owner:test"
    )


def test_notebook_parser_negative_paths_and_unknown_defaults(tmp_path, capsys):
    m = load("integration/codespace_jyperter/notebook_parser.py", "w76_notebook_fail")
    parser = m.NotebookParser()
    with pytest.raises(FileNotFoundError):
        parser.parse(tmp_path / "absent.ipynb")
    wrong = tmp_path / "wrong.json"
    wrong.write_text("{}")
    with pytest.raises(ValueError, match="Expected"):
        parser.parse(wrong)
    notebook = tmp_path / "unsupported.ipynb"
    notebook.write_text(json.dumps({"nbformat": 3, "cells": []}))
    with pytest.raises(ValueError, match="Unsupported"):
        parser.parse(notebook)
    notebook.write_text(json.dumps({"nbformat": 4, "cells": []}))
    assert parser.parse(notebook)["kernel_name"] == "unknown"
    notebook.write_text("{not-json")
    with pytest.raises(json.JSONDecodeError):
        parser.parse(notebook)
    assert m._main([]) == 1
    assert m._main([str(tmp_path / "absent.ipynb")]) == 1
    assert "ERROR:" in capsys.readouterr().err
    notebook.write_text(json.dumps({"nbformat": 4, "cells": []}))
    assert m._main([str(notebook)]) == 0


def test_applicant_package_synthetic_and_unresolved_status(tmp_path):
    m = load("rextools/populate_package.py", "w76_package")
    data = {
        "verdict": "ISSUE_RFI",
        "n_open_gates": 1,
        "energy_model": "synthetic",
        "open_gates": [{"id": "TEST-01"}],
    }
    root = tmp_path / "owner"
    generated = root / "generated"
    generated.mkdir(parents=True)
    skeleton = root / "skeleton.md"
    skeleton.write_text("Synthetic skeleton")
    (generated / "t_available_grid.md").write_text("Synthetic grid")
    (generated / "applicant_rfi.md").write_text("Synthetic RFI")
    with (
        mock.patch.object(m, "SKELETON", skeleton),
        mock.patch.object(m, "GEN", generated),
    ):
        assembled = m.assemble(data)
        assert "DRAFT-GATED" in assembled
        assert "Synthetic RFI" in assembled
        assert "TEST-01" in assembled
        data["verdict"] = "PROCEED_MDA"
        data["n_open_gates"] = 0
        data["open_gates"] = []
        assert "READY FOR MDA" in m.assemble(data)
        (generated / "applicant_rfi.md").unlink()
        with pytest.raises(FileNotFoundError):
            m.assemble(data)


@pytest.mark.parametrize(
    "verdict,expected",
    [("PIPELINE_FAIL", 2), ("ISSUE_RFI", 1), ("PROCEED_MDA", 0)],
)
def test_applicant_package_native_exit_paths(tmp_path, verdict, expected):
    m = load("rextools/populate_package.py", f"w76_applicant_{expected}")
    root = tmp_path / "safe"
    root.mkdir()
    output = root / "safe-output.md"
    result = {
        "verdict": verdict,
        "n_open_gates": int(verdict == "ISSUE_RFI"),
        "energy_model": "synthetic",
        "open_gates": [],
    }
    package = fake_package("models")
    subpackage = fake_package("models.qps_line_s")
    runtime = types.ModuleType("models.qps_line_s.runtime")
    runtime.runtime = mock.Mock(return_value=result)
    subpackage.runtime = runtime
    modules = {
        "models": package,
        "models.qps_line_s": subpackage,
        "models.qps_line_s.runtime": runtime,
    }
    with (
        mock.patch.dict(sys.modules, modules),
        mock.patch.object(m, "ROOT", root),
        mock.patch.object(m, "GEN", root),
        mock.patch.object(m, "OUT", output),
        mock.patch.object(m, "assemble", return_value="synthetic output"),
    ):
        assert m.main() == expected
    runtime.runtime.assert_called_once_with(regenerate=True, enforce=False)
    assert output.exists() is (expected != 2)


def test_self_smoke_probes_and_deterministic_fail_closed_receipt(tmp_path):
    fake_config = type("FakeConfig", (), {})
    m = load_with_siblings(
        "DMAIC_V3/self_smoke.py",
        "w76_engine",
        {
            "config": {"DMAICConfig": fake_config, "VERSION": "3.3.0"},
            "product_version": {"ABACUS_VERSION": "6.0.0"},
        },
    )
    assert m._probe_import()["product_version"] == "6.0.0"
    assert m._probe_config()["config_type"] == "FakeConfig"
    sample = tmp_path / "bytes.txt"
    sample.write_bytes(b"source-bound")
    assert m._sha256(sample) == hashlib.sha256(b"source-bound").hexdigest()
    with mock.patch.object(m, "ROOT", tmp_path):
        with pytest.raises(FileNotFoundError):
            m._probe_ssot()
        manifest = tmp_path / "ssot" / "manifest.yaml"
        manifest.parent.mkdir()
        manifest.write_text("one_logical_fact_one_authority: true")
        with pytest.raises(RuntimeError, match="invariants"):
            m._probe_ssot()
        manifest.write_text(
            "one_logical_fact_one_authority: true\n"
            "reverse_mutation_from_binary_to_authority: false\n"
        )
        assert m._probe_ssot()["sha256"] == m._sha256(manifest)
        with pytest.raises(FileNotFoundError):
            m._probe_contract()
        for relative in (
            "qps_contract_canonicalization/src/schema.ts",
            "qps_slide_reviewer/lib/qps-contract-clarification-schema.ts",
        ):
            target = tmp_path / relative
            target.parent.mkdir(parents=True)
            target.write_text("synthetic")
        assert len(m._probe_contract()["surfaces"]) == 2
        with (
            mock.patch.object(m, "_git", side_effect=["a" * 40, "b" * 40] * 2),
            mock.patch.object(m, "_probe_orchestrator", return_value={"class": "Fake"}),
            mock.patch.object(m, "_probe_agent_manager", return_value={"class": "Fake"}),
            mock.patch.object(m, "_probe_handover", return_value={"module": "Fake"}),
        ):
            first = m.run_self_smoke()
            second = m.run_self_smoke()
    assert first["success"] is True
    assert first["passed"] == first["total"] == 7
    assert first["deterministic_sha256"] == second["deterministic_sha256"]


def test_self_smoke_preserves_failed_probe_and_captured_stdout(tmp_path):
    m = load_with_siblings(
        "DMAIC_V3/self_smoke.py",
        "w76_engine_failure",
        {
            "config": {"DMAICConfig": type("FakeConfig", (), {}), "VERSION": "3.3"},
            "product_version": {"ABACUS_VERSION": "6.0.0"},
        },
    )
    with (
        mock.patch.object(m, "_git", side_effect=["a" * 40, "b" * 40]),
        mock.patch.object(m, "_probe_config", side_effect=RuntimeError("synthetic red")),
        mock.patch.object(m, "_probe_ssot", return_value={"sha256": "safe"}),
        mock.patch.object(m, "_probe_contract", return_value={"surfaces": []}),
        mock.patch.object(m, "_probe_orchestrator", return_value={}),
        mock.patch.object(m, "_probe_agent_manager", return_value={}),
        mock.patch.object(m, "_probe_handover", return_value={}),
    ):
        receipt = m.run_self_smoke()
    assert receipt["success"] is False
    assert receipt["passed"] == 6
    assert receipt["stages"][1]["status"] == "FAIL"
    assert "synthetic red" in receipt["stages"][1]["error"]


def test_dmaic_entrypoint_version_json_and_self_smoke(capsys, monkeypatch):
    checker = mock.Mock(return_value={"success": True, "stages": []})
    m = load_with_siblings(
        "DMAIC_V3/__main__.py",
        "w76_cli",
        {
            "config": {"VERSION": "3.3.0"},
            "product_version": {"ABACUS_VERSION": "6.0.0"},
            "self_smoke": {"run_self_smoke": checker},
        },
    )
    monkeypatch.setattr(sys, "argv", ["abacus", "version", "--json"])
    assert m.main() == 0
    assert json.loads(capsys.readouterr().out)["product_version"] == "6.0.0"
    monkeypatch.setattr(sys, "argv", ["abacus"])
    assert m.main() == 0
    assert "ABACUS" in capsys.readouterr().out
    monkeypatch.setattr(sys, "argv", ["abacus", "self-smoke"])
    assert m.main() == 0
    checker.return_value = {"success": False, "stages": []}
    assert m.main() == 1


def test_compatibility_module_entrypoints_are_importable():
    main = types.ModuleType("src.qplant_presentation_engine.__main__")
    main.main = mock.Mock(return_value=0)
    modules = {
        "src": fake_package("src"),
        "src.qplant_presentation_engine": fake_package("src.qplant_presentation_engine"),
        "src.qplant_presentation_engine.__main__": main,
    }
    with mock.patch.dict(sys.modules, modules):
        qplant = load("qplant_presentation_engine/__main__.py", "w76_qplant_cli")
    assert qplant.main() == 0
    main.main.assert_called_once_with()
    phases = {"phase0_init": {"Phase0Init": type("Phase0Init", (), {})}}
    setup = load_with_siblings(
        "DMAIC_V3/phases/phase0_setup.py", "w76_phases", phases
    )
    assert setup.Phase0Setup.__bases__[0].__name__ == "Phase0Init"


def test_orchestrator_and_agent_api_exports_have_no_runtime_dispatch():
    orchestrator = type("FakeOrchestrator", (), {})
    creator = mock.Mock(return_value=orchestrator())
    shared = fake_package("w76_orchestrators")
    stub = types.ModuleType("w76_orchestrators.dmaic_postdeploy")
    stub.PostDeployOrchestrator = orchestrator
    stub.create_post_deploy_orchestrator = creator
    with mock.patch.dict(
        sys.modules,
        {"w76_orchestrators": shared, stub.__name__: stub},
    ):
        module = load(
            "DMAIC_V3/orchestrators/__init__.py", "w76_orchestrators.__init__"
        )
    assert module.PostDeployOrchestrator is orchestrator
    assert module.create_post_deploy_orchestrator is creator
    assert creator.call_count == 0

    exports = (
        ("framework", "FrameworkAgent"),
        ("style_extractor", "StyleExtractorAgent"),
        ("self_ranking", "SelfRankingAgent"),
        ("iteration_tracker", "IterationTrackerAgent"),
        ("context_manager", "ContextManagerAgent"),
        ("dependency_graph", "DependencyGraphAgent"),
        ("health_checker", "HealthCheckerAgent"),
        ("performance_tracker", "PerformanceTrackerAgent"),
    )
    stubs = {"w76_agents": fake_package("w76_agents")}
    for source, class_name in exports:
        module_name = f"w76_agents.{source}"
        stub = types.ModuleType(module_name)
        setattr(stub, class_name, type(class_name, (), {}))
        stubs[module_name] = stub
    with mock.patch.dict(sys.modules, stubs):
        module = load("DMAIC_V3/agents/__init__.py", "w76_agents.__init__")
    assert set(module.__all__) == {name for _, name in exports}
    for _, name in exports:
        assert getattr(module, name).__name__ == name
