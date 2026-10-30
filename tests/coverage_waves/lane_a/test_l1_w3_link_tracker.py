"""Lane A wave 3: DMAIC_V3.core.link_tracker."""

import json
import sys

import pytest

from DMAIC_V3.core import link_tracker as lt

DOC_V1 = """# Guide
Version: 1.2
See [the parent](old.md) for the recursive hook into history.

Some filler text so the next link is far from the first one, padding padding
padding padding padding padding padding padding padding padding padding.

Read [runner](tools/run.py) for the dmaic pipeline phase.

More filler words keep this context window clean of any release markers here.

Then [elsewhere](other.md) explains measure and control.
"""

DOC_V2 = """Version 2.0
Docs about the [v3.1 notes](notes.md) and the knowledge artifact.
"""

CODE = '''"""Module. Version: 1.10"""
def iteration():
    return "convergence checkpoint validation"
'''


@pytest.fixture
def project(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_bytes(DOC_V1.encode())
    (tmp_path / "release.md").write_bytes(DOC_V2.encode())
    (tmp_path / "mod.py").write_bytes(CODE.encode())
    (tmp_path / "noversion.py").write_bytes(b"x = 'state'\n")
    (tmp_path / "meta.json").write_bytes(
        json.dumps({"metadata": {"version": "1.2"}, "phase": "define"}).encode()
    )
    (tmp_path / "top.json").write_bytes(json.dumps({"version": "2.0"}).encode())
    (tmp_path / "list.json").write_bytes(b"[1, 2]")
    (tmp_path / "broken.md").write_bytes(b"\xff\xfe not utf8")
    (tmp_path / "broken.py").write_bytes(b"\xff\xfe not utf8")
    return tmp_path


def test_extract_version(tmp_path):
    tracker = lt.LinkTracker(tmp_path)
    assert tracker._extract_version("Version: 3.4.5 here") == "3.4.5"
    assert tracker._extract_version("version 2.0") == "2.0"
    assert tracker._extract_version("no marker") is None


@pytest.mark.parametrize(
    "text,target,context,expected",
    [
        ("x", "a.md", "the Recursive Hook", "recursive_hook"),
        ("x", "a.md", "parent version link", "recursive_hook"),
        ("x", "a.md", "see v2 docs", "recursive_hook"),
        ("x", "a.md", "the version notes", "version_link"),
        ("x", "a.md", "release v3.1", "version_link"),
        ("x", "run.py", "plain", "code_link"),
        ("x", "a.md", "plain", "cross_reference"),
    ],
)
def test_classify_link(tmp_path, text, target, context, expected):
    assert lt.LinkTracker(tmp_path)._classify_link(text, target, context) == expected


def test_analyze_term_frequency(tmp_path):
    tf = lt.LinkTracker(tmp_path)._analyze_term_frequency(
        "The phase and the Phase of DMAIC: measure x9 the", "f.md", "markdown", "1.0"
    )
    assert tf.total_words == 10
    assert tf.term_counts["the"] == 3
    assert tf.technical_terms == {"phase": 2, "dmaic": 1, "measure": 1}
    assert tf.top_terms[0] == ("phase", 2)
    assert all(term not in ("the", "of", "x9") for term, _ in tf.top_terms)
    assert tf.version == "1.0"


def test_scan_project_builds_graph(project, capsys):
    tracker = lt.LinkTracker(project)
    graph = tracker.scan_project()
    out = capsys.readouterr().out
    assert "Error scanning" in out
    assert out.count("Error scanning") == 3

    by_target = {link.target_file: link for link in graph.links}
    assert by_target["old.md"].link_type == "recursive_hook"
    assert by_target["old.md"].line_number == 3
    assert by_target["old.md"].version_source == "1.2"
    assert by_target["tools/run.py"].link_type == "code_link"
    assert by_target["other.md"].link_type == "cross_reference"
    assert by_target["notes.md"].link_type == "version_link"

    types = {tf.file_type for tf in graph.term_frequencies.values()}
    assert types == {"markdown", "python", "json"}
    assert graph.version_lineage == ["1.2", "1.10", "2.0"]
    assert graph.nodes["1.2"].parent_version is None
    assert graph.nodes["1.2"].child_versions == ["1.10"]
    assert graph.nodes["1.10"].parent_version == "1.2"
    assert graph.nodes["2.0"].child_versions == []
    assert sorted(graph.nodes["2.0"].files) == ["release.md", "top.json"]


def test_report_statistics_and_language(project, tmp_path):
    tracker = lt.LinkTracker(project)
    tracker.scan_project()
    out = tmp_path / "report.json"
    tracker.generate_link_report(out)
    report = json.loads(out.read_text(encoding="utf-8"))
    meta = report["metadata"]
    assert meta["total_links_found"] == 4
    assert meta["versions_detected"] == ["1.2", "1.10", "2.0"]
    stats = report["statistics"]
    assert stats["link_types"]["code_link"] == 1
    assert stats["file_types"]["json"] == 2
    assert stats["average_words_per_file"] > 0
    assert dict(stats["top_technical_terms"])["phase"] >= 2
    graph = report["link_graph"]
    assert graph["nodes"]["2.0"]["date"]
    assert {link["target_file"] for link in graph["links"]} >= {"old.md"}

    issues = tracker.validate_uniform_language()
    assert "convergence" in issues["missing_in_docs"]
    assert "knowledge" in issues["missing_in_code"]
    assert issues["inconsistent_usage"] == []


def test_statistics_empty_graph(tmp_path):
    stats = lt.LinkTracker(tmp_path)._generate_statistics()
    assert stats["average_words_per_file"] == 0
    assert stats["link_types"] == {}


def test_main_usage(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["link_tracker.py"])
    with pytest.raises(SystemExit) as exc:
        lt.main()
    assert exc.value.code == 1
    assert "Usage" in capsys.readouterr().out


def test_main_reports_inconsistency(project, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["link_tracker.py", str(project)])
    lt.main()
    out = capsys.readouterr().out
    assert "Found 4 links" in out
    assert "Terms in code but not docs" in out
    assert "Terms in docs but not code" in out
    assert (project / "link_tracker_report.json").exists()


def test_main_uniform_terms(tmp_path, monkeypatch, capsys):
    (tmp_path / "a.md").write_bytes(b"phase")
    (tmp_path / "a.py").write_bytes(b"phase = 1\n")
    monkeypatch.setattr(sys, "argv", ["link_tracker.py", str(tmp_path)])
    lt.main()
    assert (
        "[OK] Documentation and code use uniform terminology" in capsys.readouterr().out
    )


def test_main_only_docs_terms(tmp_path, monkeypatch, capsys):
    (tmp_path / "a.md").write_bytes(b"phase")
    monkeypatch.setattr(sys, "argv", ["link_tracker.py", str(tmp_path)])
    lt.main()
    out = capsys.readouterr().out
    assert "Terms in docs but not code: phase" in out
    assert "Terms in code but not docs" not in out
