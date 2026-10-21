"""W77 lane B: codespace notebook parser and DMAIC master reconciliation.

All fixtures stay in temporary directories. No real project reconciliation.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _module(name, rel):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError("source missing")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def notebook_module():
    return _module(
        "w77_notebook_parser",
        "integration/codespace_jyperter/notebook_parser.py",
    )


@pytest.fixture
def master_module():
    return _module(
        "w77_master_reconciliation",
        "DMAIC_V3/generators/master_reconciliation.py",
    )


def _notebook(path, *, nbformat=4, cells=None, metadata=None):
    payload = {
        "nbformat": nbformat,
        "metadata": metadata if metadata is not None else {
            "kernelspec": {"display_name": "Python 3", "language": "python"},
            "language_info": {"name": "python"},
        },
        "cells": cells if cells is not None else [],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_notebook_empty_source_is_real_zero_cell_observation(notebook_module, tmp_path):
    path = _notebook(tmp_path / "empty.ipynb")
    result = notebook_module.NotebookParser().parse(path)
    assert result["notebook_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert result["nbformat"] == 4
    assert result["cell_count"] == 0
    assert result["code_cell_count"] == result["markdown_cell_count"] == 0
    assert result["cells"] == []
    assert result["kernel_name"] == "Python 3"


def test_notebook_mixed_cells_and_nonbinary_output(notebook_module, tmp_path):
    cells = [
        {"cell_type": "code", "source": ["print(", "'ok')"],
         "execution_count": 3, "metadata": {"trusted": True},
         "outputs": [
             {"output_type": "display_data",
              "data": {"text/plain": ["ok"], "image/png": "SECRET",
                       "application/octet-stream": "BINARY"}},
             {"output_type": "stream", "text": ["log"]},
             "invalid"
         ]},
        {"cell_type": "markdown", "source": "# Title", "metadata": {}},
        {"cell_type": "raw", "source": ["literal"], "metadata": {}},
    ]
    result = notebook_module.NotebookParser().parse(
        _notebook(tmp_path / "mixed.ipynb", cells=cells)
    )
    assert (result["cell_count"], result["code_cell_count"],
            result["markdown_cell_count"], result["raw_cell_count"]) == (3, 1, 1, 1)
    assert result["cells"][0]["source"] == "print('ok')"
    outputs = result["cells"][0]["outputs"]
    assert len(outputs) == 2
    assert outputs[0]["data"] == {"text/plain": ["ok"]}
    assert result["cells"][0]["execution_count"] == 3
    assert result["cells"][1]["source"] == "# Title"


def test_notebook_unknown_cell_type_does_not_fabricate_known_counts(
    notebook_module, tmp_path
):
    result = notebook_module.NotebookParser().parse(_notebook(
        tmp_path / "unknown.ipynb",
        cells=[{"cell_type": "future", "source": "x", "outputs": []}],
    ))
    assert result["cell_count"] == 1
    assert result["raw_cell_count"] == 0
    assert result["code_cell_count"] == 0


@pytest.mark.parametrize("nbformat", [0, 3, 5, "4", None, False])
def test_notebook_unsupported_format_rejected(notebook_module, tmp_path, nbformat):
    path = _notebook(tmp_path / "unsupported.ipynb", nbformat=nbformat)
    with pytest.raises(ValueError, match="Unsupported notebook format"):
        notebook_module.NotebookParser().parse(path)


def test_notebook_missing_wrong_suffix_corruption(notebook_module, tmp_path):
    parser = notebook_module.NotebookParser()
    with pytest.raises(FileNotFoundError):
        parser.parse(tmp_path / "missing.ipynb")
    text = tmp_path / "not-notebook.txt"
    text.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="Expected a .ipynb"):
        parser.parse(text)
    bad = tmp_path / "malformed.ipynb"
    bad.write_text("{broken", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        parser.parse(bad)


def test_notebook_missing_metadata_remains_unknown(notebook_module, tmp_path):
    result = notebook_module.NotebookParser().parse(
        _notebook(tmp_path / "nometa.ipynb", metadata={})
    )
    assert result["kernel_name"] == "unknown"
    assert result["language"] == "unknown"


def test_notebook_save_and_knowledge_source_are_scoped(notebook_module, tmp_path):
    parser = notebook_module.NotebookParser()
    extracted = parser.parse(_notebook(tmp_path / "t.ipynb"))
    output = parser.save_extract(extracted, tmp_path / "out", iteration=7)
    assert output.name == "notebook_cells_t_iter7.json"
    assert output.parent == tmp_path / "out"
    assert json.loads(output.read_text())["notebook_sha256"] == extracted["notebook_sha256"]
    k = parser.build_knowledge_source(extracted)
    assert k["source_id"].endswith(extracted["notebook_sha256"][:8])
    assert k["source_type"] == "notebook_extract"
    assert parser.build_knowledge_source(extracted, source_id="ID")["source_id"] == "ID"


def test_notebook_cli_refuses_empty_and_missing_paths(notebook_module, tmp_path, capsys):
    assert notebook_module._main([]) == 1
    assert "Usage" in capsys.readouterr().err
    assert notebook_module._main([str(tmp_path / "no.ipynb")]) == 1
    assert "ERROR" in capsys.readouterr().err


def test_notebook_cli_prints_only_parsed_local_content(notebook_module, tmp_path, capsys):
    path = _notebook(tmp_path / "ok.ipynb")
    assert notebook_module._main([str(path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["nbformat"] == 4
    assert result["notebook_path"] == str(path.resolve())


def test_master_constructor_no_implicit_project_mutation(master_module, tmp_path):
    manager = master_module.MasterReconciliationSystem(tmp_path)
    assert manager.root_dir == tmp_path
    assert manager.parent_name == "master_document_handler"
    assert manager.reconciliation_log == []
    assert not (tmp_path / "output").exists()


def test_master_unicode_rewrites_only_files_in_temp_root(master_module, tmp_path):
    source = tmp_path / "master_document_system"
    source.mkdir()
    p = source / "one.py"
    p.write_text("arrow = 'left ← right → two ↔ three'\n", encoding="utf-8")
    pristine = source / "pristine.py"
    pristine.write_text("x = 1\n", encoding="utf-8")
    mgr = master_module.MasterReconciliationSystem(tmp_path)
    assert mgr.fix_python_unicode_errors() == 1
    assert "<-" in p.read_text() and "<->" in p.read_text()
    assert pristine.read_text() == "x = 1\n"
    assert mgr.fix_python_unicode_errors() == 0


def test_master_invalid_unicode_source_is_error_not_success(master_module, tmp_path):
    root = tmp_path / "master_document_system"
    root.mkdir()
    (root / "bad.py").write_bytes(b"\xff\xff")
    mgr = master_module.MasterReconciliationSystem(tmp_path)
    assert mgr.fix_python_unicode_errors() == 0
    assert any("[ERROR]" in row for row in mgr.reconciliation_log)


def test_master_reconciles_existing_markdown_without_creating_missing(
    master_module, tmp_path
):
    folder = tmp_path / "master_document_system"
    folder.mkdir()
    p = folder / "README.md"
    p.write_text("# Original\n\nText.\n", encoding="utf-8")
    mgr = master_module.MasterReconciliationSystem(tmp_path)
    assert mgr.reconcile_markdown_files() == 1
    assert "Original" in p.read_text()
    assert p.read_text().count("DMAIC V3 RECONCILIATION") == 1
    assert mgr.reconcile_markdown_files() == 1
    assert p.read_text().count("DMAIC V3 RECONCILIATION") == 1
    assert not (folder / "INTEGRATION_PLAN.md").exists()


def test_master_metrics_are_initialized_not_operational(master_module, tmp_path):
    mgr = master_module.MasterReconciliationSystem(tmp_path)
    phases = mgr.generate_dmaic_metrics_per_phase()
    assert isinstance(phases, dict)
    assert len(phases) == 5
    assert all("metrics" in value for value in phases.values())
    files = list((tmp_path / "output").rglob("*.json"))
    assert len(files) == 6
    assert all(json.loads(p.read_text()) for p in files)
    assert not any("merge_authorized" in json.loads(p.read_text()) for p in files)


def test_master_final_report_and_logs_local_only(master_module, tmp_path):
    mgr = master_module.MasterReconciliationSystem(tmp_path)
    mgr.log("synthetic observation", "WARNING")
    report = mgr.generate_final_report()
    assert report["metadata"]["report_type"] == "MASTER_RECONCILIATION"
    assert any("synthetic observation" in row for row in report["reconciliation_log"])
    files = list((tmp_path / "output" / "reconciliation").glob("*.json"))
    assert len(files) == 1
    assert json.loads(files[0].read_text())["metadata"]["parent"] == mgr.parent_name
