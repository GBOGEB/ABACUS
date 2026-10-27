"""Behaviour tests for local_mcp/agents/documentation_framework_v2.3_OPTIMIZED.py."""

import json

import pytest

from tests.coverage_waves.lane_a._load import load

MOD = load("local_mcp/agents/documentation_framework_v2.3_OPTIMIZED.py")
Agent = MOD.MemoryEfficientDocumentationFrameworkV23


@pytest.fixture
def agent(tmp_path):
    return Agent({"output_dir": str(tmp_path / "out")})


def test_init_defaults_create_output_dir_in_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    a = Agent()
    assert a.config == {}
    assert a.name == "documentation_framework"
    assert a.version == "v2.3.0"
    assert (tmp_path / "documentation_outputs_v2.3").is_dir()
    assert a.get_results() == []
    assert all(v == 0 for v in a.performance_metrics.values())


def test_log_dmaic_truncates_result_and_defaults(agent, capsys):
    agent._log_dmaic("P", "act", "x" * 150)
    agent._log_dmaic("P", "act2")
    assert agent.dmaic_log[0]["result"] == "x" * 100
    assert agent.dmaic_log[1]["result"] == "Completed"
    assert "[P] act" in capsys.readouterr().out


def test_stream_real_file_chunks(agent, tmp_path):
    src = tmp_path / "doc.md"
    src.write_bytes("".join("line %d \n" % i for i in range(5)).encode())
    chunks = list(agent.stream_documentation(str(src), chunk_size=2))
    assert [c["size"] for c in chunks] == [2, 2, 1]
    assert chunks[0]["lines"] == ["line 0", "line 1"]
    assert agent.performance_metrics["memory_chunks_processed"] == 3


def test_stream_exact_multiple_has_no_trailing_chunk(agent, tmp_path):
    src = tmp_path / "doc.md"
    src.write_bytes(b"a\nb\n")
    chunks = list(agent.stream_documentation(str(src), chunk_size=2))
    assert len(chunks) == 1


def test_stream_missing_file_yields_synthetic(agent, tmp_path):
    chunks = list(agent.stream_documentation(str(tmp_path / "nope.md")))
    assert [c["doc"]["section"] for c in chunks] == [
        "Introduction",
        "Architecture",
        "API Reference",
        "Examples",
        "Troubleshooting",
    ]
    assert agent.performance_metrics["memory_chunks_processed"] == 5


def test_stream_error_yields_error_chunk(agent, tmp_path):
    # A directory exists but cannot be opened as a file.
    chunks = list(agent.stream_documentation(str(tmp_path)))
    assert len(chunks) == 1
    assert "error" in chunks[0]
    assert agent.performance_metrics["errors_handled"] == 1
    assert agent.dmaic_log[-1]["phase"] == "STREAM"


def test_define(agent):
    d = agent.dmaic_define()
    assert d["constraints"]["memory_limit"] == "4M"
    assert "markdown" in d["scope"]["output_formats"]
    assert agent.performance_metrics["dmaic_phases_completed"] == 1


def test_measure_without_source_returns_baseline(agent):
    m = agent.dmaic_measure()
    assert m == {
        "total_documents": 12,
        "total_sections": 48,
        "total_words": 8500,
        "diagrams": 6,
        "code_examples": 24,
    }


def test_measure_synthetic_source(agent, tmp_path):
    m = agent.dmaic_measure(str(tmp_path / "missing.md"))
    assert m["total_documents"] == 5
    assert m["total_sections"] == 15
    assert m["total_words"] == 2500


def test_production_defect_measure_real_file_counts_nothing(agent, tmp_path):
    # Pins a production_defect: chunks streamed from a real file carry "lines",
    # not "doc", so dmaic_measure counts zero documents. Fails once fixed.
    src = tmp_path / "doc.md"
    src.write_bytes(b"# Title\nsome text\n")
    m = agent.dmaic_measure(str(src))
    assert m["total_documents"] == 0
    assert m["total_words"] == 0


def test_analyze(agent):
    a = agent.dmaic_analyze({})
    assert a["quality_score"] == 0.85
    assert len(a["recommendations"]) == 4


def test_improve_branches(agent):
    analysis = {
        "recommendations": [
            "Add more code examples",
            "Update diagrams",
            "Expand troubleshooting section",
            "Something else",
        ]
    }
    imp = agent.dmaic_improve(analysis)
    assert imp == {
        "documents_generated": 4,
        "sections_added": 3,
        "diagrams_created": 2,
        "examples_added": 5,
    }
    pm = agent.performance_metrics
    assert pm["documents_generated"] == 4
    assert pm["sections_written"] == 3
    assert pm["diagrams_created"] == 2


def test_improve_empty(agent):
    imp = agent.dmaic_improve({})
    assert imp["documents_generated"] == 0


def test_control_reflects_metrics(agent):
    agent.dmaic_improve({"recommendations": ["diagrams"]})
    c = agent.dmaic_control({})
    assert c["metrics_tracking"]["diagrams_created"] == 2
    assert c["monitoring"]["review_frequency"] == "weekly"


def test_run_success_saves_json(agent, tmp_path):
    result = agent.run()
    assert result["status"] == "success"
    assert result["performance_metrics"]["dmaic_phases_completed"] == 5
    assert result["dmaic_results"]["improve"]["documents_generated"] == 4
    assert agent.get_results() == [result]
    files = list((tmp_path / "out").glob("documentation_results_*.json"))
    assert len(files) == 1
    saved = json.loads(files[0].read_text(encoding="utf-8"))
    assert saved["agent"] == "documentation_framework"


def test_run_error_path(agent, monkeypatch, capsys):
    def boom(_m):
        raise RuntimeError("analysis failed")

    monkeypatch.setattr(agent, "dmaic_analyze", boom)
    result = agent.run()
    assert result["status"] == "error"
    assert result["error"] == "analysis failed"
    assert "RuntimeError" in result["traceback"]
    assert result["performance_metrics"]["errors_handled"] == 1
    assert "ERROR: analysis failed" in capsys.readouterr().out


def test_save_results_failure_warns(agent, tmp_path, capsys):
    agent.output_dir = tmp_path / "missing" / "deeper"
    agent._save_results({"a": 1})
    assert "Warning: Could not save results" in capsys.readouterr().out


def test_main_success(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert MOD.main() == 0
    out = capsys.readouterr().out
    assert "Status: success" in out
    assert list((tmp_path / "documentation_outputs_v2.3").glob("*.json"))


def test_main_error_returns_one(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def boom(self):
        raise RuntimeError("x")

    monkeypatch.setattr(Agent, "dmaic_define", boom)
    assert MOD.main() == 1
