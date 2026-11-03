"""Lane A wave 14: DMAIC_V3.analyze_recent_files scanning, gap checks and report."""

import json
import os
import time

import pytest

from DMAIC_V3 import analyze_recent_files as arf


@pytest.fixture
def tree(tmp_path):
    docs = tmp_path / "docs"
    (docs / "sub").mkdir(parents=True)
    files = {
        "actions.yaml": "version: 1\nactions:\n  build:\n    command: make\n"
        "sprints:\n  s1:\n    tasks: []\n",
        "list.yml": "- a\n- b\n",
        "bad.yaml": "key: [unclosed\n",
        "phase_out.json": json.dumps({"phase": 1}),
        "iteration_7.json": json.dumps({"iteration": 7, "metadata": {}}),
        "plain.json": json.dumps([1, 2]),
        "broken.json": "{nope",
        "DMAIC_notes.md": "no title here | table\n```code```\n",
        "README.md": "# Title\n\nSome text\n",
        "good.md": "# Good\n## Usage\n",
        "skip.txt": "ignored",
    }
    for name, text in files.items():
        (docs / name).write_text(text, encoding="utf-8")
    (docs / "sub" / "deep.md").write_bytes(b"\xff\xfe bad utf8")
    old = docs / "old.json"
    old.write_text("{}", encoding="utf-8")
    past = time.time() - 30 * 86400
    os.utime(old, (past, past))
    return tmp_path


def _scan(root):
    an = arf.RecentFilesAnalyzer(root, days=7)
    an.scan_directories(["docs", "missing_dir"])
    return an


def _by_name(items):
    return {i["name"]: i for i in items}


def test_scan_classifies_files(tree):
    an = _scan(tree)
    yaml_files = _by_name(an.results["yaml_files"])
    assert set(yaml_files) == {"actions.yaml", "list.yml", "bad.yaml"}
    assert yaml_files["actions.yaml"]["has_version"] is True
    assert yaml_files["actions.yaml"]["keys"] == ["version", "actions", "sprints"]
    assert yaml_files["list.yml"]["keys"] == []
    assert "error" in yaml_files["bad.yaml"]
    json_files = _by_name(an.results["json_files"])
    assert "old.json" not in json_files
    assert json_files["plain.json"]["has_phase"] is False
    assert "error" in json_files["broken.json"]
    md = _by_name(an.results["markdown_files"])
    assert md["DMAIC_notes.md"]["has_tables"] is True
    assert md["DMAIC_notes.md"]["has_code_blocks"] is True
    assert md["good.md"]["has_headers"] is True
    assert "error" in md["deep.md"]


def test_gap_detection(tree):
    gaps = _scan(tree).results["gaps"]
    yaml_gaps = sorted(g["gap"] for g in gaps["yaml"])
    assert yaml_gaps == [
        "Action 'build' missing 'inputs'",
        "Action 'build' missing 'outputs'",
        "Sprint 's1' missing 'owner'",
    ]
    json_gaps = {(g["file"].replace("\\", "/"), g["gap"]) for g in gaps["json"]}
    assert ("docs/phase_out.json", "Missing 'metadata' section") in json_gaps
    assert ("docs/phase_out.json", "Missing 'version'") in json_gaps
    assert ("docs/iteration_7.json", "Missing 'convergence_metrics'") in json_gaps
    md_gaps = {g["gap"] for g in gaps["markdown"]}
    assert "Missing main title (# header)" in md_gaps
    assert "Missing 'recursive' concept" in md_gaps
    assert "Missing installation/setup section" in md_gaps
    assert "Missing usage section" in md_gaps


def test_gap_checks_ignore_non_dicts():
    an = arf.RecentFilesAnalyzer(".", days=1)
    an.check_yaml_gaps(["x"], {"path": "p"})
    an.check_json_gaps("x", {"path": "p", "name": "phase"})
    assert dict(an.results["gaps"]) == {}
    info = {"path": "p", "name": "DOW_README.md"}
    an.check_markdown_gaps(
        "# T\nrecursive iteration convergence\n## Setup\n## Usage\n", info
    )
    assert dict(an.results["gaps"]) == {}


def test_outer_exception_is_reported(tree, monkeypatch, capsys):
    an = arf.RecentFilesAnalyzer(tree, days=7)

    def boom(path, info):
        raise RuntimeError("analyzer broke")

    monkeypatch.setattr(an, "analyze_json", boom)
    an.scan_directories(["docs"])
    assert "analyzer broke" in capsys.readouterr().out
    assert an.results["json_files"] == []


def test_generate_report(tree):
    an = _scan(tree)
    out = tree / "report.md"
    an.generate_report(out)
    stats = an.results["statistics"]
    assert stats["yaml_count"] == 3
    assert stats["files_with_errors"] == 3
    assert stats["total_files"] == len(an.results["top_30_files"])
    text = out.read_text(encoding="utf-8")
    assert "## STATISTICS" in text
    assert "- **Error:**" in text
    assert "- **Keys:** version, actions, sprints" in text
    assert "### YAML Gaps" in text and "### JSON Gaps" in text
    assert "### Markdown Gaps" in text
    data = json.loads((tree / "report.json").read_text(encoding="utf-8"))
    assert data["statistics"]["json_gaps"] == stats["json_gaps"]


def test_generate_report_empty(tmp_path):
    an = arf.RecentFilesAnalyzer(tmp_path)
    an.generate_report(tmp_path / "r.md")
    text = (tmp_path / "r.md").read_text(encoding="utf-8")
    assert "Gaps" not in text.split("## IDENTIFIED GAPS")[1]
    assert an.results["statistics"]["total_files"] == 0
