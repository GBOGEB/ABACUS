"""Behaviour tests for local_mcp/agents/analysis_document_consumer_v2.3_OPTIMIZED.py."""

import json

import pytest

from tests.coverage_waves.lane_a._load import load

dc = load("local_mcp/agents/analysis_document_consumer_v2.3_OPTIMIZED.py")


@pytest.fixture
def agent(tmp_path):
    return dc.MemoryEfficientDocumentConsumerV23({"output_dir": str(tmp_path / "out")})


def write_doc(tmp_path, lines):
    p = tmp_path / "doc.md"
    p.write_bytes("".join(line + "\n" for line in lines).encode("utf-8"))
    return p


def test_init_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    agent = dc.MemoryEfficientDocumentConsumerV23()
    assert agent.config == {}
    assert agent.name == "document_consumer"
    assert (tmp_path / "document_consumer_outputs_v2.3").is_dir()


def test_log_dmaic(agent, capsys):
    agent._log_dmaic("A", "b", "z" * 150)
    agent._log_dmaic("A", "c")
    assert len(agent.dmaic_log[0]["result"]) == 100
    assert agent.dmaic_log[1]["result"] == "Completed"
    assert "[A] b" in capsys.readouterr().out


def test_stream_synthetic_when_no_source(agent):
    chunks = list(agent.stream_document())
    assert chunks == [{"lines": agent._synthetic_lines(), "chunk_index": 0}]
    assert agent.performance_metrics["memory_chunks_processed"] == 1


def test_stream_synthetic_when_missing_file(agent, tmp_path):
    chunks = list(agent.stream_document(str(tmp_path / "nope.md")))
    assert chunks[0]["chunk_index"] == 0
    assert len(chunks) == 1


def test_stream_file_chunks_and_strips(agent, tmp_path):
    p = write_doc(tmp_path, ["l%d  " % i for i in range(5)])
    chunks = list(agent.stream_document(str(p), chunk_size=2))
    assert [c["lines"] for c in chunks] == [["l0", "l1"], ["l2", "l3"], ["l4"]]
    assert [c["chunk_index"] for c in chunks] == [1, 2, 3]


def test_stream_file_exact_multiple(agent, tmp_path):
    p = write_doc(tmp_path, ["a", "b"])
    chunks = list(agent.stream_document(str(p), chunk_size=2))
    assert len(chunks) == 1


def test_stream_empty_file(agent, tmp_path):
    p = tmp_path / "e.md"
    p.write_bytes(b"")
    assert list(agent.stream_document(str(p))) == []


def test_stream_invalid_utf8_replaced(agent, tmp_path):
    p = tmp_path / "bad.txt"
    p.write_bytes(b"ok \xff\xfe\n")
    chunks = list(agent.stream_document(str(p)))
    assert chunks[0]["lines"][0].startswith("ok ")


def test_stream_error_on_directory(agent, tmp_path):
    chunks = list(agent.stream_document(str(tmp_path)))
    assert len(chunks) == 1
    assert "error" in chunks[0]
    assert agent.performance_metrics["errors_handled"] == 1
    assert agent.dmaic_log[-1]["phase"] == "STREAM"


def test_extract_values_labels(agent):
    found = agent.extract_values(
        ["Version: v2.3.0", "Iteration: 7", "Phase: measure", "Status: complete"]
    )
    pairs = {(f["label"], f["value"]) for f in found}
    assert ("version", "v2.3.0") in pairs
    assert ("iteration", "7") in pairs
    assert ("phase", "measure") in pairs
    assert ("dmaic", "measure") in pairs
    assert ("status", "complete") in pairs
    assert found[0]["line"] == 1
    assert agent.performance_metrics["values_extracted"] == len(found)
    assert agent.performance_metrics["canonical_matches"] == len(found)


def test_extract_values_context_truncated(agent):
    found = agent.extract_values(["  DEFINE " + "".join("x" for _ in range(100))])
    assert found[0]["context"].startswith("DEFINE")
    assert len(found[0]["context"]) == 80


def test_extract_values_none(agent):
    assert agent.extract_values(["nothing here", ""]) == []


def test_extract_values_tuple_match_uses_first_group(agent, monkeypatch):
    monkeypatch.setattr(dc, "_CANONICAL_PATTERNS", {"pair": r"(\w+)=(\w+)"})
    found = agent.extract_values(["k=v"])
    assert found == [{"line": 1, "label": "pair", "value": "k", "context": "k=v"}]


def test_define_and_control(agent):
    assert ".md" in agent.dmaic_define()["supported_formats"]
    assert agent.dmaic_control()["required_labels"] == ["version", "phase", "status"]
    assert agent.performance_metrics["dmaic_phases_completed"] == 2


def test_measure_counts(agent, tmp_path):
    p = write_doc(tmp_path, ["a", "", "  ", "b"])
    m = agent.dmaic_measure(str(p))
    assert m == {"total_lines": 4, "non_empty_lines": 2}
    assert agent.performance_metrics["documents_processed"] == 1


def test_measure_error_chunk(agent, tmp_path):
    assert agent.dmaic_measure(str(tmp_path)) == {
        "total_lines": 0,
        "non_empty_lines": 0,
    }


def test_analyze_synthetic(agent):
    a = agent.dmaic_analyze()
    assert a["extracted_values"] == len(agent.extracted_values) > 0
    assert "v2.3.0" in a["by_label"]["version"]
    assert "3" in a["by_label"]["iteration"]


def test_improve(agent):
    r = agent.dmaic_improve({"extracted_values": 0})
    assert "canonical markers" in r["recommendations"][0]
    assert agent.dmaic_improve({})["recommendations"][0].startswith("Add")
    r = agent.dmaic_improve({"extracted_values": 3})
    assert r["recommendations"] == ["Document structure meets canonical standards"]


def test_run_with_file(agent, tmp_path):
    p = write_doc(tmp_path, ["plain text only"])
    result = agent.run(str(p))
    saved = json.loads(dc.Path(result["output_file"]).read_text())
    assert saved["dmaic"]["analyze"]["extracted_values"] == 0
    assert saved["dmaic"]["measure"]["total_lines"] == 1
    assert result["performance_metrics"]["dmaic_phases_completed"] == 5


def test_main(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    dc.main()
    assert '"agent": "document_consumer"' in capsys.readouterr().out
    out_dir = tmp_path / "document_consumer_outputs_v2.3"
    assert list(out_dir.glob("document_consumer_*.json"))
