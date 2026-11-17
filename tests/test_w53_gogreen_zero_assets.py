"""W53 GoGREEN: behavior-test three never-covered, source-owned modules.

No network calls or writes outside pytest temporary directories. This is a
source rehabilitation test, not a release or external federation acceptance.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def _source(relative: str):
    path = ROOT / relative
    name = "w53_green_" + relative.replace("/", "_").replace(".", "_")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _recent():
    return _source("DMAIC_V3/analyze_recent_files.py").RecentFilesAnalyzer


def _notebook():
    return _source("integration/codespace_jyperter/notebook_parser.py")


def _aligner():
    return _source("DMAIC_V3/generators/documentation_aligner.py").DocumentationAligner


def test_recent_files_real_yaml_json_markdown_gap_detection(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "actions.yaml").write_text(
        "actions:\n  pulse:\n    inputs: []\nsprints:\n  W53: {}\n",
        encoding="utf-8",
    )
    (docs / "phase_state.json").write_text("{}", encoding="utf-8")
    (docs / "iteration_state.json").write_text("{}", encoding="utf-8")
    (docs / "README.md").write_text("No heading or usage", encoding="utf-8")
    (docs / "skip.bin").write_bytes(b"not a tracked format")
    agent = _recent()(tmp_path)
    agent.scan_directories(["docs", "absent"])
    agent.calculate_statistics()
    metrics = agent.results["statistics"]
    assert metrics["total_files"] == 4
    assert (
        metrics["yaml_count"],
        metrics["json_count"],
        metrics["markdown_count"],
    ) == (
        1,
        2,
        1,
    )
    assert metrics["yaml_gaps"] >= 3
    assert metrics["json_gaps"] >= 5
    assert metrics["markdown_gaps"] >= 3
    assert metrics["files_with_errors"] == 0


def test_recent_files_corrupt_and_nonmapping_inputs_remain_observable(tmp_path):
    folder = tmp_path / "inbox"
    folder.mkdir()
    (folder / "broken.yaml").write_text("broken: [", encoding="utf-8")
    (folder / "bad.json").write_text("{", encoding="utf-8")
    (folder / "list.yml").write_text("- item\n", encoding="utf-8")
    (folder / "array.json").write_text("[1, 2]\n", encoding="utf-8")
    agent = _recent()(tmp_path)
    agent.scan_directories(["inbox"])
    agent.calculate_statistics()
    assert agent.results["statistics"]["total_files"] == 4
    assert agent.results["statistics"]["files_with_errors"] == 2
    assert agent.results["statistics"]["yaml_gaps"] == 0
    assert agent.results["statistics"]["json_gaps"] == 0
    assert any("error" in entry for entry in agent.results["yaml_files"])


def test_recent_files_old_mtime_and_unknown_directory_are_excluded(tmp_path):
    folder = tmp_path / "docs"
    folder.mkdir()
    stale = folder / "old.json"
    stale.write_text("{}", encoding="utf-8")
    old_time = time.time() - 60 * 60 * 24 * 20
    os.utime(stale, (old_time, old_time))
    agent = _recent()(tmp_path, days=1)
    agent.scan_directories(["docs", "missing"])
    assert agent.results["json_files"] == []


def test_recent_file_report_is_consistent_with_json_receipt(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "README.md").write_text("# Title\n\n## Usage\n", encoding="utf-8")
    agent = _recent()(tmp_path)
    agent.scan_directories(["docs"])
    report = tmp_path / "analysis.md"
    agent.generate_report(report)
    payload = json.loads((tmp_path / "analysis.json").read_text(encoding="utf-8"))
    assert payload["statistics"]["total_files"] == 1
    assert payload["statistics"]["markdown_count"] == 1
    assert "## STATISTICS" in report.read_text(encoding="utf-8")
    assert payload["top_30_files"][0]["name"] == "README.md"


def _notebook_fixture():
    return {
        "nbformat": 4,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python"},
            "language_info": {"name": "python"},
        },
        "cells": [
            {
                "cell_type": "code",
                "source": ["x = 1\n", "print(x)\n"],
                "outputs": [
                    {
                        "output_type": "display_data",
                        "data": {
                            "image/png": "large-bytes",
                            "text/plain": "1",
                        },
                    }
                ],
                "execution_count": 1,
                "metadata": {},
            },
            {"cell_type": "markdown", "source": "# Result", "metadata": {}},
            {"cell_type": "raw", "source": ["owner context"], "metadata": {}},
        ],
    }


def test_notebook_hash_counts_binary_filter_and_knowledge_receipt(tmp_path):
    module = _notebook()
    notebook = tmp_path / "lesson.ipynb"
    notebook.write_text(json.dumps(_notebook_fixture()), encoding="utf-8")
    extracted = module.NotebookParser().parse(notebook)
    assert (
        extracted["notebook_sha256"]
        == hashlib.sha256(notebook.read_bytes()).hexdigest()
    )
    assert extracted["cell_count"] == 3
    assert extracted["code_cell_count"] == 1
    assert extracted["markdown_cell_count"] == 1
    assert extracted["raw_cell_count"] == 1
    assert extracted["cells"][0]["source"] == "x = 1\nprint(x)\n"
    data = extracted["cells"][0]["outputs"][0]["data"]
    assert data == {"text/plain": "1"}
    parser = module.NotebookParser()
    saved = parser.save_extract(extracted, tmp_path / "extracts", iteration=2)
    assert saved.name == "notebook_cells_lesson_iter2.json"
    assert json.loads(saved.read_text(encoding="utf-8"))["cell_count"] == 3
    descriptor = parser.build_knowledge_source(extracted)
    assert descriptor["source_type"] == "notebook_extract"
    assert descriptor["source_id"].endswith(extracted["notebook_sha256"][:8])
    assert descriptor["repo"] == "GBOGEB/codespace_jyperter"


@pytest.mark.parametrize(
    "kind",
    ["missing", "wrong-extension", "unsupported-format"],
)
def test_notebook_bad_source_refused_without_fabricating_receipt(tmp_path, kind):
    module = _notebook()
    filename = tmp_path / "case.ipynb"
    if kind == "missing":
        with pytest.raises(FileNotFoundError):
            module.NotebookParser().parse(filename)
        return
    if kind == "wrong-extension":
        filename = tmp_path / "case.txt"
    payload = _notebook_fixture()
    if kind == "unsupported-format":
        payload["nbformat"] = 3
    filename.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError):
        module.NotebookParser().parse(filename)


def test_notebook_cli_good_and_bad_inputs(tmp_path, capsys):
    module = _notebook()
    assert module._main([]) == 1
    assert "Usage:" in capsys.readouterr().err
    path = tmp_path / "nb.ipynb"
    path.write_text(json.dumps(_notebook_fixture()), encoding="utf-8")
    assert module._main([str(path)]) == 0
    assert '"cell_count": 3' in capsys.readouterr().out
    assert module._main([str(tmp_path / "absent.ipynb")]) == 1
    assert "ERROR:" in capsys.readouterr().err


def test_notebook_nonmapping_binary_outputs_are_dropped():
    module = _notebook()
    result = module._sanitize_outputs(
        [None, 42, {"data": {"application/octet-stream": "x", "text/plain": "ok"}}]
    )
    assert result == [{"data": {"text/plain": "ok"}}]


def test_notebook_non_object_json_root_is_refused_by_parser_and_cli(tmp_path, capsys):
    module = _notebook()
    path = tmp_path / "array.ipynb"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON root must be an object"):
        module.NotebookParser().parse(path)
    assert module._main([str(path)]) == 1
    assert "ERROR: Notebook JSON root must be an object" in capsys.readouterr().err


def test_document_aligner_missing_then_local_alignment(tmp_path):
    Aligner = _aligner()
    agent = Aligner(tmp_path)
    assert agent.align_file("missing.md")[0] is False
    path = tmp_path / "README.md"
    path.write_text("# Header\n\nContent\n", encoding="utf-8")
    ok, info = agent.align_file("README.md")
    assert ok and "Aligned" in info
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# Header")
    assert "**Version**: 3.1.0" in text
    assert "## Changelog" in text
    assert "Integration Architecture" in text


def test_document_aligner_uses_filename_title_and_exports_json_yaml(tmp_path):
    Aligner = _aligner()
    agent = Aligner(tmp_path)
    path = tmp_path / "INTEGRATION_PLAN.md"
    path.write_text("Unheaded body\n", encoding="utf-8")
    ok, _ = agent.align_file(path.name)
    assert ok
    assert path.read_text(encoding="utf-8").startswith("# Integration Plan")
    json_path = agent.export_version_info_json()
    yaml_path = agent.export_version_info_yaml()
    assert json.loads(json_path.read_text(encoding="utf-8"))["changelog"]
    assert (
        yaml.safe_load(yaml_path.read_text(encoding="utf-8"))["version_info"][
            "integration_mode"
        ]
        == "BIDIRECTIONAL"
    )


def test_document_aligner_all_four_missing_files_are_reported(tmp_path):
    Aligner = _aligner()
    agent = Aligner(tmp_path)
    results = agent.align_all()
    assert set(results) == set(agent.MARKDOWN_FILES)
    assert all(not ok for ok, _ in results.values())
