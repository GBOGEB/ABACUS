"""Behaviour tests for local_mcp/agents/analysis_artifact_analyzer_v2.3_OPTIMIZED.py."""

import json

import pytest

from tests.coverage_waves.lane_a._load import load

aa = load("local_mcp/agents/analysis_artifact_analyzer_v2.3_OPTIMIZED.py")


@pytest.fixture
def agent(tmp_path):
    return aa.MemoryEfficientArtifactAnalyzerV23({"output_dir": str(tmp_path / "out")})


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "ws"
    (ws / "pkg").mkdir(parents=True)
    (ws / ".git").mkdir()
    (ws / "node_modules").mkdir()
    (ws / "pkg" / "a.py").write_bytes(b"x = 1\n")
    (ws / "pkg" / "b.PY").write_bytes(b"y = 2\n")
    (ws / "README.md").write_bytes(b"# hi\n")
    (ws / "c.yaml").write_bytes(b"a: 1\n")
    (ws / "d.yml").write_bytes(b"a: 1\n")
    (ws / "e.json").write_bytes(b"{}")
    (ws / "f.txt").write_bytes(b"t")
    (ws / "g.ipynb").write_bytes(b"{}")
    (ws / "h.bin").write_bytes(b"\x00")
    (ws / ".git" / "HEAD").write_bytes(b"ref")
    (ws / "node_modules" / "m.js").write_bytes(b"1")
    return ws


def test_init_defaults_create_output_dir_in_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    agent = aa.MemoryEfficientArtifactAnalyzerV23()
    assert agent.config == {}
    assert agent.name == "artifact_analyzer"
    assert agent.version == aa.__version__
    assert (tmp_path / "artifact_outputs_v2.3").is_dir()
    assert set(agent.artifact_index) == set(aa._CATEGORY_MAP)


def test_log_dmaic_records_result_and_truncates(agent, capsys):
    agent._log_dmaic("P", "act", "r" * 200)
    agent._log_dmaic("P", "act2")
    assert len(agent.dmaic_log[0]["result"]) == 100
    assert agent.dmaic_log[1]["result"] == "Completed"
    assert "[P] act" in capsys.readouterr().out


@pytest.mark.parametrize(
    "name,cat",
    [
        ("a.py", "python_source"),
        ("A.MD", "markdown"),
        ("x.yaml", "yaml_config"),
        ("x.yml", "yaml_config"),
        ("x.json", "json_data"),
        ("x.rst", "documentation"),
        ("x.html", "documentation"),
        ("x.ipynb", "notebook"),
        ("x.exe", "other"),
        ("noext", "other"),
    ],
)
def test_categorize(agent, name, cat):
    assert agent._categorize(aa.Path(name)) == cat


def test_stream_workspace_chunks_and_skips_dirs(agent, workspace):
    chunks = list(agent.stream_workspace(str(workspace), chunk_size=3))
    files = [f for c in chunks for f in c["files"]]
    assert len(files) == 9
    assert not any(".git" in f or "node_modules" in f for f in files)
    assert [len(c["files"]) for c in chunks] == [3, 3, 3]
    assert [c["chunk_index"] for c in chunks] == [1, 2, 3]
    assert agent.performance_metrics["memory_chunks_processed"] == 3
    assert agent.performance_metrics["directories_traversed"] == 2


def test_stream_workspace_remainder_chunk(agent, workspace):
    chunks = list(agent.stream_workspace(str(workspace), chunk_size=4))
    assert [len(c["files"]) for c in chunks] == [4, 4, 1]


def test_stream_workspace_defaults_to_cwd(agent, workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    chunks = list(agent.stream_workspace())
    assert sum(len(c["files"]) for c in chunks) == 9


def test_stream_workspace_empty_dir_yields_nothing(agent, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert list(agent.stream_workspace(str(empty))) == []


def test_stream_workspace_walk_error(agent, monkeypatch):
    def boom(_root):
        raise OSError("walk failed")

    monkeypatch.setattr(aa.os, "walk", boom)
    chunks = list(agent.stream_workspace("anything"))
    assert chunks == [{"error": "walk failed"}]
    assert agent.performance_metrics["errors_handled"] == 1
    assert agent.dmaic_log[-1]["phase"] == "STREAM"


def test_define_and_control(agent):
    d = agent.dmaic_define()
    assert d["categories"] == list(aa._CATEGORY_MAP)
    assert len(d["objectives"]) == 4
    c = agent.dmaic_control()
    assert c["max_uncategorised_files"] == 50
    assert agent.performance_metrics["dmaic_phases_completed"] == 2


def test_measure_counts_files(agent, workspace):
    m = agent.dmaic_measure(str(workspace))
    assert m["total_files"] == 9
    assert m["directories_traversed"] == 2
    assert agent.performance_metrics["files_scanned"] == 9


def test_measure_handles_error_chunk(agent, monkeypatch):
    def boom(_root):
        raise OSError("x")

    monkeypatch.setattr(aa.os, "walk", boom)
    assert agent.dmaic_measure("w")["total_files"] == 0


def test_analyze_counts_and_sample_limit(tmp_path, workspace):
    agent = aa.MemoryEfficientArtifactAnalyzerV23(
        {"output_dir": str(tmp_path / "o"), "sample_limit_per_category": 1}
    )
    a = agent.dmaic_analyze(str(workspace))
    counts = a["category_counts"]
    assert counts["python_source"] == 2
    assert counts["yaml_config"] == 2
    assert counts["markdown"] == 1
    assert counts["json_data"] == 1
    assert counts["documentation"] == 1
    assert counts["notebook"] == 1
    assert counts["other"] == 1
    assert len(a["category_samples"]["python_source"]) == 1
    assert a["total_categorized"] == 9
    assert agent.artifact_index["python_source"]["count"] == 2


def test_analyze_omits_empty_categories_from_samples(agent, tmp_path):
    ws = tmp_path / "only_md"
    ws.mkdir()
    (ws / "a.md").write_bytes(b"x")
    a = agent.dmaic_analyze(str(ws))
    assert list(a["category_samples"]) == ["markdown"]


def test_improve_recommendations(agent):
    r = agent.dmaic_improve({"category_counts": {"other": 51, "python_source": 0}})
    assert len(r["recommendations"]) == 2
    r = agent.dmaic_improve({"category_counts": {"other": 50, "python_source": 1}})
    assert r["recommendations"] == ["Artifact structure looks healthy"]
    r = agent.dmaic_improve({})
    assert len(r["recommendations"]) == 1
    assert "Python" in r["recommendations"][0]


def test_run_writes_output(agent, workspace):
    result = agent.run(str(workspace))
    out = aa.Path(result["output_file"])
    assert out.is_file()
    saved = json.loads(out.read_text())
    assert saved["agent"] == "artifact_analyzer"
    assert saved["dmaic"]["measure"]["total_files"] == 9
    assert result["performance_metrics"]["dmaic_phases_completed"] == 5
    assert "output_file" not in saved


def test_main_prints_json(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "x.py").write_bytes(b"1")
    aa.main()
    out = capsys.readouterr().out
    assert '"agent": "artifact_analyzer"' in out
    assert list((tmp_path / "artifact_outputs_v2.3").glob("artifact_analysis_*.json"))
