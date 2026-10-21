"""W77 lane A: formerly zero-covered DMAIC document producers.

All filesystem work is isolated in temporary directories; no deployment.
"""
from __future__ import annotations

import importlib.util
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: str):
    file_path = ROOT / path
    spec = importlib.util.spec_from_file_location(name, file_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"missing source module: {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def recent(tmp_path):
    module = _load("w77_recent", "DMAIC_V3/analyze_recent_files.py")
    return module.RecentFilesAnalyzer(tmp_path, days=7)


@pytest.fixture
def aligner(tmp_path):
    module = _load(
        "w77_doc_aligner",
        "DMAIC_V3/generators/documentation_aligner.py",
    )
    return module.DocumentationAligner(tmp_path)


def _file(root, name, text):
    dest = root / "recent" / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return dest


def test_scan_missing_directories_is_empty(recent):
    recent.scan_directories(["absent"])
    recent.calculate_statistics()
    assert recent.results["statistics"]["total_files"] == 0
    assert all(not recent.results[key] for key in (
        "yaml_files", "json_files", "markdown_files", "top_30_files"
    ))


def test_scan_mixed_files_and_rank_by_size(recent, tmp_path):
    _file(tmp_path, "action.yaml", "version: 3\nactions:\n  build: {}\n")
    _file(tmp_path, "iteration_state.json", '{"iteration": 1}')
    _file(tmp_path, "README.md", "No title and no install or usage section.\n")
    _file(tmp_path, "ignore.txt", "not a source")
    recent.scan_directories(["recent"])
    recent.calculate_statistics()
    m = recent.results["statistics"]
    assert (m["total_files"], m["yaml_count"], m["json_count"],
            m["markdown_count"]) == (3, 1, 1, 1)
    assert m["total_size"] > 0
    assert recent.results["yaml_files"][0]["has_actions"] is True
    assert len(recent.results["gaps"]["yaml"]) == 3
    assert len(recent.results["gaps"]["json"]) == 2
    assert len(recent.results["gaps"]["markdown"]) >= 3
    sizes = [f["size"] for f in recent.results["top_30_files"]]
    assert sizes == sorted(sizes, reverse=True)


def test_scan_ignores_old_content(recent, tmp_path):
    p = _file(tmp_path, "outdated.json", '{"version": 1}')
    old = (datetime.now() - timedelta(days=50)).timestamp()
    os.utime(p, (old, old))
    recent.scan_directories(["recent"])
    assert recent.results["json_files"] == []


def test_scan_nested_phase_reports(recent, tmp_path):
    _file(tmp_path, "nested/sub/phase_report.json", "{}")
    recent.scan_directories(["recent"])
    assert recent.results["json_files"][0]["path"].endswith(
        "recent/nested/sub/phase_report.json"
    )
    assert len(recent.results["gaps"]["json"]) == 3


def test_yaml_full_contract_and_nonmapping_are_gap_free(recent, tmp_path):
    _file(tmp_path, "complete.yml", (
        "actions:\n  build:\n    inputs: {}\n    outputs: {}\n"
        "    command: echo\nsprints:\n  current:\n    tasks: []\n"
        "    owner: nobody\n"
    ))
    _file(tmp_path, "list.yml", "- hello\n- world\n")
    recent.scan_directories(["recent"])
    assert len(recent.results["yaml_files"]) == 2
    assert recent.results["gaps"]["yaml"] == []
    assert recent.results["yaml_files"][1]["keys"] == []


def test_yaml_malformed_is_recorded_not_discarded(recent, tmp_path):
    _file(tmp_path, "malformed.yml", "entries: [unterminated\n")
    recent.scan_directories(["recent"])
    assert "error" in recent.results["yaml_files"][0]
    recent.calculate_statistics()
    assert recent.results["statistics"]["files_with_errors"] == 1


def test_json_invalid_and_array_are_distinct(recent, tmp_path):
    _file(tmp_path, "bad.json", "{bad")
    _file(tmp_path, "list.json", '[1, "two"]')
    recent.scan_directories(["recent"])
    rows = {x["name"]: x for x in recent.results["json_files"]}
    assert "error" in rows["bad.json"]
    assert rows["list.json"]["keys"] == []
    assert "error" not in rows["list.json"]


def test_markdown_valid_headings_and_fence(recent, tmp_path):
    fence = chr(96) * 3
    _file(tmp_path, "DMAIC_README.md", (
        "# DMAIC\n## Installation\n## Usage\n"
        "recursive iteration convergence\n"
        + fence + "python\npass\n" + fence + "\n| A | B |\n"
    ))
    recent.scan_directories(["recent"])
    md = recent.results["markdown_files"][0]
    assert md["has_headers"] and md["has_code_blocks"] and md["has_tables"]
    assert not recent.results["gaps"]["markdown"]


def test_markdown_missing_title_and_terms_are_detected(recent):
    info = {"path": "docs/DMAIC.md", "name": "DMAIC.md"}
    recent.check_markdown_gaps("Plain text without a header", info)
    descriptions = [g["gap"] for g in recent.results["gaps"]["markdown"]]
    assert len(descriptions) == 4
    assert "Missing main title (# header)" in descriptions


def test_generate_markdown_and_json_reports(recent, tmp_path):
    _file(tmp_path, "phase_3.json", "{}")
    _file(tmp_path, "README.md", "No title")
    recent.scan_directories(["recent"])
    output = tmp_path / "analysis.md"
    recent.generate_report(output)
    payload = json.loads(output.with_suffix(".json").read_text())
    assert payload["statistics"]["total_files"] == 2
    assert payload["statistics"]["json_gaps"] == 3
    assert "IDENTIFIED GAPS" in output.read_text()
    assert payload["top_30_files"]


def test_aligner_missing_is_not_created(aligner, tmp_path):
    success, message = aligner.align_file("README.md")
    assert success is False and "File not found" in message
    assert not (tmp_path / "README.md").exists()


def test_aligner_plain_text_gets_version_and_links(aligner, tmp_path):
    p = tmp_path / "README.md"
    p.write_text("A plain first line.\nBody content.\n", encoding="utf-8")
    ok, message = aligner.align_file("README.md")
    assert ok and "Aligned" in message
    content = p.read_text()
    assert content.startswith("# Readme\n")
    assert "**Version**: 3.1.0" in content
    assert "## Changelog" in content
    assert "Body content." in content
    assert "Integration Architecture" in content


def test_aligner_preserves_controlled_header(aligner, tmp_path):
    p = tmp_path / "INTEGRATION_PLAN.md"
    p.write_text("# Controlled Title\n\nNarrative.\n", encoding="utf-8")
    assert aligner.align_file(p.name)[0]
    assert p.read_text().startswith("# Controlled Title\n")
    assert "Narrative." in p.read_text()


def test_aligner_invalid_utf8_cannot_succeed(aligner, tmp_path):
    p = tmp_path / "README.md"
    p.write_bytes(b"\xff\xfe")
    ok, message = aligner.align_file(p.name)
    assert ok is False and "Error aligning" in message
    assert p.read_bytes() == b"\xff\xfe"


def test_aligner_full_set_reports_missing(aligner, tmp_path):
    (tmp_path / "README.md").write_text("# One\n", encoding="utf-8")
    results = aligner.align_all()
    assert len(results) == len(aligner.MARKDOWN_FILES)
    assert sum(status for status, _ in results.values()) == 1
    assert results["README.md"][0] is True


def test_aligner_json_yaml_roundtrip(aligner, tmp_path):
    json_path = aligner.export_version_info_json()
    yaml_path = aligner.export_version_info_yaml()
    assert json_path.parent == yaml_path.parent == tmp_path
    j = json.loads(json_path.read_text())
    y = yaml.safe_load(yaml_path.read_text())
    assert j["version_info"]["version"] == y["version_info"]["version"]
    assert j["changelog"] == y["changelog"]
    assert aligner._create_changelog_section().count("### Version") == 2


def test_aligner_io_is_bound_to_temp_workspace(aligner, tmp_path):
    assert aligner.docs_dir == tmp_path
    assert not (tmp_path / "master_document_system").exists()
    assert "DMAIC_V3" in aligner.version_info["code_links"]["metrics"]
