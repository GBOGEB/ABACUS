"""Behaviour tests for local_mcp/agents/analysis_cryo_dm_v2.3_OPTIMIZED.py."""

import json

import pytest

from tests.coverage_waves.lane_a._load import load

cr = load("local_mcp/agents/analysis_cryo_dm_v2.3_OPTIMIZED.py")


@pytest.fixture
def agent(tmp_path):
    return cr.MemoryEfficientCryoAnalyzerV23({"output_dir": str(tmp_path / "out")})


def sample(i, hl=1.0, level="nominal"):
    return {"sample_id": i, "heat_load_w": hl, "cryo_level": level}


def write(tmp_path, name, text):
    p = tmp_path / name
    p.write_bytes(text.encode("utf-8"))
    return str(p)


def collect(agent, src, chunk_size=10):
    return list(agent.stream_cryo_data(src, chunk_size=chunk_size))


def test_init_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    agent = cr.MemoryEfficientCryoAnalyzerV23()
    assert agent.name == "cryo_analyzer"
    assert (tmp_path / "cryo_outputs_v2.3").is_dir()


def test_log_dmaic(agent, capsys):
    agent._log_dmaic("X", "y", "q" * 120)
    agent._log_dmaic("X", "z")
    assert len(agent.dmaic_log[0]["result"]) == 100
    assert agent.dmaic_log[1]["result"] == "Completed"
    assert "[X] y" in capsys.readouterr().out


def test_synthetic_data_deterministic(agent):
    a = agent._generate_synthetic_data(5)
    b = agent._generate_synthetic_data(5)
    assert len(a) == 5
    assert [s["heat_load_w"] for s in a] == [s["heat_load_w"] for s in b]
    for s in a:
        assert 0.1 <= s["heat_load_w"] <= 5.0
        assert 1.8 <= s["temperature_k"] <= 4.5
        assert s["cryo_level"] in {"nominal", "warning", "critical"}


def test_stream_synthetic_default(agent):
    chunks = collect(agent, None)
    assert [c["size"] for c in chunks] == [10] * 5
    assert [c["chunk_index"] for c in chunks] == [0, 1, 2, 3, 4]
    assert agent.performance_metrics["memory_chunks_processed"] == 5


def test_stream_json_array(agent, tmp_path):
    data = [sample(i) for i in range(5)]
    src = write(tmp_path, "a.json", "  \n" + json.dumps(data))
    chunks = collect(agent, src, chunk_size=2)
    assert [c["size"] for c in chunks] == [2, 2, 1]
    assert chunks[0]["samples"][0] == data[0]


def test_stream_json_array_empty(agent, tmp_path):
    src = write(tmp_path, "e.json", "[ ]")
    assert collect(agent, src) == []


def test_stream_json_array_large_whitespace_and_items(agent, tmp_path):
    pad = "".join(" " for _ in range(5000))
    big = {
        "sample_id": 1,
        "heat_load_w": 2.0,
        "note": "".join("n" for _ in range(9000)),
    }
    text = pad + "[" + pad + json.dumps(big) + "," + pad + json.dumps(sample(2)) + "]"
    chunks = collect(agent, write(tmp_path, "big.json", text))
    samples = chunks[0]["samples"]
    assert [s["sample_id"] for s in samples] == [1, 2]
    assert len(samples[0]["note"]) == 9000


def test_stream_json_array_unterminated(agent, tmp_path):
    src = write(tmp_path, "u.json", "[" + json.dumps(sample(1)) + ",")
    chunks = collect(agent, src)
    assert chunks == [{"error": "Unexpected EOF in JSON array"}]
    assert agent.performance_metrics["errors_handled"] == 1


def test_stream_json_array_truncated_item(agent, tmp_path):
    src = write(tmp_path, "t.json", '[{"sample_id": ')
    chunks = collect(agent, src)
    assert "error" in chunks[-1]


def test_stream_json_object_with_samples(agent, tmp_path):
    src = write(tmp_path, "o.json", json.dumps({"samples": [sample(1), sample(2)]}))
    chunks = collect(agent, src)
    assert chunks[0]["size"] == 2


def test_stream_json_object_without_samples(agent, tmp_path):
    src = write(tmp_path, "o2.json", json.dumps({"other": 1}))
    assert collect(agent, src) == []


def test_stream_json_lines(agent, tmp_path):
    # Lines whose first record is not an object reach the JSON-lines reader.
    text = '"first"\n\n' + json.dumps(sample(2)) + "\n"
    chunks = collect(agent, write(tmp_path, "d.jsonl", text))
    assert chunks[0]["samples"] == ["first", sample(2)]


def check_production_defect_jsonl_objects_routed_to_json_load(agent, tmp_path):
    # Reproduction of a production_defect (see WAVE_LEDGER.jsonl). Named check_*
    # so the governed suite does not collect it: a pinned defect must never block
    # the fix. Run on demand: pytest -o python_functions=check_* <this file>
    text = json.dumps(sample(1)) + "\n" + json.dumps(sample(2)) + "\n"
    chunks = collect(agent, write(tmp_path, "objs.jsonl", text))
    assert len(chunks) == 1
    assert "Extra data" in chunks[0]["error"]


def test_stream_json_lines_bad_line(agent, tmp_path):
    chunks = collect(agent, write(tmp_path, "bad.jsonl", "not json\n"))
    assert len(chunks) == 1
    assert "error" in chunks[0]
    assert agent.dmaic_log[-1]["phase"] == "STREAM"


def test_stream_empty_file(agent, tmp_path):
    empty = write(tmp_path, "empty.json", "   ")
    assert collect(agent, empty) == []


def test_stream_missing_file_falls_back_to_synthetic(agent, tmp_path):
    chunks = collect(agent, str(tmp_path / "missing.json"))
    assert sum(c["size"] for c in chunks) == 50


def test_define(agent):
    d = agent.dmaic_define()
    assert d["constraints"]["memory_limit_mb"] == 4
    assert agent.performance_metrics["dmaic_phases_completed"] == 1


def test_measure(agent, tmp_path):
    data = [sample(i) for i in range(4)]
    m = agent.dmaic_measure(write(tmp_path, "m.json", json.dumps(data)))
    assert m["total_samples"] == 4
    assert m["sample_preview"] == data[:3]
    assert agent.performance_metrics["samples_processed"] == 4


def test_analyze_empty(agent):
    assert agent.dmaic_analyze([]) == {"error": "No samples to analyze"}
    assert agent.performance_metrics["dmaic_phases_completed"] == 0


def test_analyze_stats(agent):
    samples = [sample(0, 1.0), sample(1, 3.0, "critical"), {"cryo_level": "warning"}]
    a = agent.dmaic_analyze(samples)
    assert a["mean_heat_load_w"] == 2.0
    assert a["std_dev_w"] == 1.0
    assert a["anomaly_count"] == 1
    assert a["anomaly_rate_pct"] == 33.33
    assert agent.performance_metrics["anomalies_detected"] == 1


def test_analyze_no_heat_loads(agent):
    a = agent.dmaic_analyze([{"cryo_level": "nominal"}])
    assert a["mean_heat_load_w"] == 0
    assert a["std_dev_w"] == 0


def test_improve(agent):
    r = agent.dmaic_improve({"anomaly_rate_pct": 11, "std_dev_w": 1.5})
    assert len(r["recommendations"]) == 2
    r = agent.dmaic_improve({"anomaly_rate_pct": 10, "std_dev_w": 1.0})
    assert r["recommendations"] == ["System within normal parameters"]
    assert agent.dmaic_improve({})["recommendations"] == [
        "System within normal parameters"
    ]


def test_control(agent):
    c = agent.dmaic_control({"recommendations": ["a"]})
    assert c["applied_recommendations"] == ["a"]
    assert agent.dmaic_control({})["applied_recommendations"] == []


def test_run_with_file(agent, tmp_path):
    data = [sample(0, 1.0), sample(1, 1.0)]
    result = agent.run(write(tmp_path, "r.json", json.dumps(data)))
    saved = json.loads(cr.Path(result["output_file"]).read_text())
    assert saved["dmaic"]["analyze"]["mean_heat_load_w"] == 1.0
    assert saved["dmaic"]["improve"]["recommendations"] == [
        "System within normal parameters"
    ]
    assert result["performance_metrics"]["dmaic_phases_completed"] == 5


def test_main(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    cr.main()
    assert '"agent": "cryo_analyzer"' in capsys.readouterr().out
    assert list((tmp_path / "cryo_outputs_v2.3").glob("cryo_analysis_*.json"))
