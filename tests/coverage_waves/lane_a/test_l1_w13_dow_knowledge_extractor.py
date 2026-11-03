"""Lane A wave 13: DOW knowledge extraction agent."""

import json
import sys

import pytest

from tests.coverage_waves.lane_a._load import load

_REL = "DMAIC_V3/local_mcp/agents/dow_knowledge_extractor.py"
_NAME = "l1_w13_dow_knowledge_extractor"


def _load_restoring():
    # The module inserts the repo root and src/ at sys.path[0] on import.
    saved = list(sys.path)
    try:
        return load(_REL, name=_NAME)
    finally:
        sys.path[:] = saved
        sys.modules.pop(_NAME, None)


mod = _load_restoring()


@pytest.fixture
def ext():
    return mod.DOWKnowledgeExtractor()


def _write(path, data):
    path.write_bytes(json.dumps(data).encode("utf-8"))
    return path


def test_extract_knowledge_rich_payload(tmp_path, ext):
    payload = {
        "metadata": {"phase": "phase4", "iteration": "2", "version": "3.4"},
        "recursive_hooks": {"consumed_from": ["a", "b"], "feeds_into": ["c"]},
        "convergence_metrics": {
            "quality_score": 0.9,
            "convergence_status": "improving",
            "improvement_from_previous": 0.25,
        },
    }
    path = _write(tmp_path / "p.json", payload)
    result = ext.extract_knowledge(path)
    assert result["status"] == "success"
    gain = result["knowledge"]
    assert "Metadata structure present" in gain["patterns_discovered"]
    assert "Recursive hooks implemented" in gain["patterns_discovered"]
    assert "High quality output achieved" in gain["insights_generated"]
    assert "DOW structure fully implemented" in gain["insights_generated"]
    assert "Positive improvement of 0.25 from previous iteration" in (
        gain["learnings_captured"]
    )
    assert "Data flow: consumes from 2 sources, feeds into 1 targets" in (
        gain["learnings_captured"]
    )
    telemetry = gain["finding_telemetry"]
    assert telemetry["closure_yield_state"] == "WITHHELD_CHILD_DISPOSITION"
    assert telemetry["unique_findings"] == len(gain["typed_findings"])
    for finding in gain["typed_findings"]:
        assert finding["target"] == "phase4"
        assert finding["finding_id"].startswith("DOW-")
        assert finding["authority_level"] == "DERIVED_ADVISORY"
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["knowledge_gain"]["child_disposition"] is None
    assert len(written["idempotency"]["output_hash"]) == 64


def test_extract_knowledge_bad_json_errors(tmp_path, ext):
    path = tmp_path / "bad.json"
    path.write_bytes(b"{")
    result = ext.extract_knowledge(path)
    assert result["status"] == "error"


def test_extract_batch_counts(tmp_path, ext):
    good = _write(tmp_path / "g.json", {"x": 1})
    result = ext.extract_batch([good, tmp_path / "missing.json"])
    assert (result["total"], result["success"], result["failed"]) == (2, 1, 1)


def test_discover_patterns_complex_deep_error_test(ext):
    data = {f"k{i}": i for i in range(21)}
    data["deep"] = {"a": {"b": {"c": {"d": 1}}}}
    data["note"] = "ERROR and Test"
    patterns = ext._discover_patterns(data)
    assert any(p.startswith("Complex data structure with 23 keys") for p in patterns)
    assert "Deep nesting detected (depth: 5)" in patterns
    assert "Error handling present" in patterns
    assert "Testing artifacts present" in patterns
    assert ext._discover_patterns({"a": 1}) == []


@pytest.mark.parametrize(
    "metrics,expected",
    [
        ({"quality_score": 0.3, "convergence_status": "degrading"}, 2),
        ({"quality_score": 0.6, "convergence_status": "stable"}, 0),
    ],
)
def test_generate_insights_quality_and_status(ext, metrics, expected):
    insights = ext._generate_insights({"convergence_metrics": metrics})
    assert len(insights) == expected
    if expected:
        assert "Quality improvement needed" in insights
        assert any("degrading" in i for i in insights)


def test_generate_insights_large_output(ext):
    insights = ext._generate_insights({"blob": "x" * 100001})
    assert insights == ["Large output generated - consider optimization"]


def test_capture_learnings_negative_and_zero(ext):
    neg = ext._capture_learnings(
        {"convergence_metrics": {"improvement_from_previous": -0.5}}
    )
    assert neg == ["Negative improvement of -0.50 - review needed"]
    assert ext._capture_learnings({"convergence_metrics": {}}) == []


def test_suggest_improvements(ext):
    assert ext._suggest_improvements({}) == [
        "Add metadata structure",
        "Add recursive hooks",
        "Add convergence metrics",
        "Add knowledge gain tracking",
    ]
    full = {
        "metadata": {},
        "recursive_hooks": {},
        "convergence_metrics": {"quality_score": 0.5},
        "knowledge_gain": {},
    }
    assert ext._suggest_improvements(full) == [
        "Add version to metadata",
        "Add timestamp to metadata",
        "Improve quality score (current: 0.50)",
    ]
    done = {
        "metadata": {"version": "1", "timestamp": "t"},
        "recursive_hooks": {},
        "convergence_metrics": {"quality_score": 0.9},
        "knowledge_gain": {},
    }
    assert ext._suggest_improvements(done) == []


def test_typed_findings_dedupe_and_determinism(ext):
    kwargs = dict(
        source_reference="s",
        target="t",
        input_hash="h",
        insights=["same", "same"],
        improvements=["fix"],
    )
    findings, telemetry = ext._build_typed_findings(**kwargs)
    again, _ = ext._build_typed_findings(**kwargs)
    assert findings == again
    assert telemetry["candidate_findings"] == 3
    assert telemetry["unique_findings"] == 2
    assert telemetry["duplicates_dropped"] == 1
    assert telemetry["remaining_semantic_debt"] == 1
    assert [f["finding_type"] for f in findings] == ["OBSERVATION", "IMPROVEMENT"]
    assert [f["confidence"] for f in findings] == [0.70, 0.80]


def test_nested_depth(ext):
    assert ext._calculate_nested_depth(5) == 0
    assert ext._calculate_nested_depth({}) == 0
    assert ext._calculate_nested_depth([]) == 0
    assert ext._calculate_nested_depth([[1], {"a": []}]) == 2
    assert ext._calculate_nested_depth({"a": [1, {"b": 2}]}) == 3


def _run_main(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["dow_knowledge_extractor.py", *args])
    return mod.main()


def test_main_missing_and_empty(tmp_path, monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, "--target", str(tmp_path / "none"))
    assert exc.value.code == 1
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, "--target", str(tmp_path), "--verbose")
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "Target directory not found" in out
    assert "No JSON files found" in out


def test_main_success_then_failure(tmp_path, monkeypatch, capsys):
    _write(tmp_path / "a.json", {"metadata": {"phase": "p"}})
    assert _run_main(monkeypatch, "--target", str(tmp_path)) is None
    assert "Success: 1" in capsys.readouterr().out
    (tmp_path / "b.json").write_bytes(b"[")
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, "--target", str(tmp_path))
    assert exc.value.code == 1
    assert "Failed: 1" in capsys.readouterr().out
