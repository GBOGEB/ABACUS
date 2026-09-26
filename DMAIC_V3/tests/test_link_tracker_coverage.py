import json
import sys
from datetime import datetime
from pathlib import Path

from DMAIC_V3.core.link_tracker import (
    DocumentLink,
    LinkGraph,
    LinkTracker,
    TermFrequency,
    VersionNode,
    main,
)


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / "README.md").write_text(
        "# Demo\nVersion: 1.2.0\n"
        "See [code](worker.py) for the recursive hook and "
        "[guide](guide.md) for control validation.\n",
        encoding="utf-8",
    )
    (tmp_path / "guide.md").write_text(
        "# Guide\nVersion: 1.3.0\n"
        "DMAIC measure analyze improve control pipeline artifact validation.\n"
        "See [older](README.md) for version history.\n",
        encoding="utf-8",
    )
    (tmp_path / "worker.py").write_text(
        '"""Version: 1.4.0 DMAIC recursive orchestrator validation."""\n'
        "def execute():\n"
        "    return 'ok'\n",
        encoding="utf-8",
    )
    (tmp_path / "metadata.json").write_text(
        json.dumps(
            {
                "version": "1.5.0",
                "metadata": {"kind": "artifact"},
                "text": "dmaic metric checkpoint convergence",
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_link_graph_to_dict_serializes_all_components():
    graph = LinkGraph(
        nodes={
            "1.0.0": VersionNode(
                version="1.0.0",
                date=datetime(2026, 1, 1),
                files=["README.md"],
                child_versions=["1.1.0"],
                changes={"README.md": "added"},
            )
        },
        links=[
            DocumentLink(
                source_file="README.md",
                target_file="worker.py",
                link_type="code_link",
                line_number=2,
                context="worker",
                version_source="1.0.0",
                version_target="1.1.0",
            )
        ],
        term_frequencies={
            "README.md": TermFrequency(
                file_path="README.md",
                file_type="markdown",
                total_words=3,
                unique_words=3,
                term_counts={"dmaic": 1, "control": 1, "artifact": 1},
                top_terms=[("dmaic", 1)],
                technical_terms={"dmaic": 1, "control": 1, "artifact": 1},
                version="1.0.0",
            )
        },
        version_lineage=["1.0.0", "1.1.0"],
    )

    payload = graph.to_dict()
    assert payload["nodes"]["1.0.0"]["date"] == "2026-01-01T00:00:00"
    assert payload["links"][0]["link_type"] == "code_link"
    assert payload["term_frequencies"]["README.md"]["technical_terms"]["dmaic"] == 1
    assert payload["version_lineage"] == ["1.0.0", "1.1.0"]


def test_link_classification_version_and_term_analysis(tmp_path):
    tracker = LinkTracker(tmp_path)

    assert tracker._extract_version("Version: 2.4.1") == "2.4.1"
    assert tracker._extract_version("no release here") is None

    assert (
        tracker._classify_link("child", "next.md", "recursive hook to child")
        == "recursive_hook"
    )
    assert (
        tracker._classify_link("history", "old.md", "Version 1.2.0 history")
        == "version_link"
    )
    assert tracker._classify_link("code", "worker.py", "plain code") == "code_link"
    assert (
        tracker._classify_link("docs", "guide.md", "plain documentation")
        == "cross_reference"
    )

    tf = tracker._analyze_term_frequency(
        "DMAIC dmaic control artifact artifact validation and the pipeline",
        "README.md",
        "markdown",
        "3.0.0",
    )
    assert tf.total_words > 0
    assert tf.term_counts["dmaic"] == 2
    assert tf.technical_terms["artifact"] == 2
    assert ("artifact", 2) in tf.top_terms
    assert tf.version == "3.0.0"


def test_scan_project_builds_links_terms_and_version_lineage(tmp_path):
    root = _workspace(tmp_path)
    tracker = LinkTracker(root)

    graph = tracker.scan_project()

    assert {"README.md", "guide.md", "worker.py", "metadata.json"} <= set(
        graph.term_frequencies
    )
    assert graph.version_lineage == ["1.2.0", "1.3.0", "1.4.0", "1.5.0"]
    assert graph.nodes["1.2.0"].parent_version is None
    assert graph.nodes["1.2.0"].child_versions == ["1.3.0"]
    assert graph.nodes["1.5.0"].parent_version == "1.4.0"
    assert any(link.target_file == "worker.py" for link in graph.links)
    assert any(link.target_file == "guide.md" for link in graph.links)

    stats = tracker._generate_statistics()
    assert stats["file_types"]["markdown"] == 2
    assert stats["file_types"]["python"] == 1
    assert stats["file_types"]["json"] == 1
    assert stats["average_words_per_file"] > 0
    assert stats["top_technical_terms"]


def test_generate_report_and_uniform_language_validation(tmp_path):
    root = _workspace(tmp_path)
    tracker = LinkTracker(root)
    tracker.scan_project()

    report_path = root / "reports" / "links.json"
    report_path.parent.mkdir()
    tracker.generate_link_report(report_path)

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["metadata"]["root_directory"] == str(root)
    assert payload["metadata"]["total_files_scanned"] >= 4
    assert payload["metadata"]["total_links_found"] >= 2
    assert payload["statistics"]["file_types"]["markdown"] == 2

    issues = tracker.validate_uniform_language()
    assert set(issues) == {
        "missing_in_docs",
        "missing_in_code",
        "inconsistent_usage",
    }
    assert isinstance(issues["missing_in_docs"], list)
    assert isinstance(issues["missing_in_code"], list)


def test_invalid_json_is_fail_soft_and_main_writes_report(tmp_path, monkeypatch, capsys):
    root = _workspace(tmp_path)
    broken = root / "broken.json"
    broken.write_text("{not-json", encoding="utf-8")

    tracker = LinkTracker(root)
    tracker._scan_json_file(broken)
    captured = capsys.readouterr()
    assert "Error scanning" in captured.out

    monkeypatch.setattr(sys, "argv", ["link_tracker.py", str(root)])
    main()

    report = root / "link_tracker_report.json"
    assert report.exists()
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["metadata"]["total_files_scanned"] >= 4


def test_main_without_root_exits_with_usage(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["link_tracker.py"])
    try:
        main()
    except SystemExit as exc:
        assert exc.code == 1
    else:
        raise AssertionError("main() must exit when root argument is missing")

    assert "Usage: python link_tracker.py <project_root>" in capsys.readouterr().out
