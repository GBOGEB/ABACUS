"""Wave 12 lane A behaviour tests for DMAIC_V3/phases/phase3_analyze.py."""

import json
from types import SimpleNamespace

import pytest

from DMAIC_V3.phases import phase3_analyze as p3


@pytest.fixture
def phase(tmp_path):
    paths = SimpleNamespace(workspace_root=tmp_path, output_root=tmp_path / "out")
    return p3.Phase3Analyze(SimpleNamespace(paths=paths), state_manager=None)


def _fm(complexity=0, loc=0, functions=0, classes=0, comments=0, success=True):
    return {
        "success": success,
        "metrics": {
            "complexity_score": complexity,
            "lines_of_code": loc,
            "functions": functions,
            "classes": classes,
            "comment_lines": comments,
        },
    }


METRICS = {
    "low.py": _fm(complexity=10, loc=10),
    "med.py": _fm(complexity=150, loc=150),
    "high.py": _fm(complexity=400, loc=400),
    "crit.py": _fm(
        complexity=2000,
        loc=900,
        functions=[{"name": "f", "args": 7}, {"args": 9}, "g", {"args": 1}],
        classes=[{"name": "Big"}, {}, "Plain"],
        comments=500,
    ),
    "skip.py": _fm(complexity=5000, success=False),
}


def test_complexity_distribution(phase):
    assert phase.analyze_complexity_distribution(METRICS) == {
        "low": 1,
        "medium": 1,
        "high": 1,
        "critical": 1,
    }


def test_size_distribution(phase):
    assert phase.analyze_file_size_distribution(METRICS) == {
        "small": 1,
        "medium": 1,
        "large": 1,
        "very_large": 1,
    }


def test_high_complexity_files_sorted_and_list_lengths(phase):
    top = phase.identify_high_complexity_files(METRICS, top_n=2)
    assert [t["file"] for t in top] == ["crit.py", "high.py"]
    assert top[0]["functions"] == 4
    assert top[0]["classes"] == 3
    assert top[1]["functions"] == 0
    assert len(phase.identify_high_complexity_files(METRICS)) == 4


def test_detect_code_patterns(phase):
    pats = phase.detect_code_patterns(METRICS)
    assert [g["class"] for g in pats["god_classes"]] == ["Big", "Unknown", "Plain"]
    assert [m["function"] for m in pats["long_methods"]] == ["f", "Unknown"]
    assert pats["long_methods"][1]["args"] == 9
    low_doc = {d["file"] for d in pats["low_documentation"]}
    assert low_doc == {"med.py", "high.py"}
    assert pats["duplicate_imports"] == []


def test_detect_code_patterns_small_class_not_god(phase):
    pats = phase.detect_code_patterns({"a.py": _fm(loc=40, classes=["C"])})
    assert pats["god_classes"] == []
    assert pats["low_documentation"] == []


def test_generate_root_causes_all_and_none(phase):
    analysis = {
        "complexity_dist": {"critical": 2, "high": 11},
        "patterns": {"god_classes": [1], "low_documentation": [0] * 21},
    }
    rc = phase.generate_root_causes(analysis)
    assert [r["severity"] for r in rc] == ["critical", "high", "high", "medium"]
    assert rc[0]["count"] == 2
    quiet = {
        "complexity_dist": {"critical": 0, "high": 10},
        "patterns": {"god_classes": [], "low_documentation": [0] * 20},
    }
    assert phase.generate_root_causes(quiet) == []


def _write_phase2(tmp_path, data, iteration=1):
    d = tmp_path / "out" / f"iteration_{iteration}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "phase2_metrics.json").write_text(json.dumps(data), encoding="utf-8")


def test_run_missing_phase2(phase):
    ok, res = phase.run(3)
    assert ok is False
    assert "Phase 2 output not found" in res["error"]
    assert res["root_causes"] == []


def test_run_new_format_writes_output(phase, tmp_path):
    _write_phase2(tmp_path, {"file_metrics": METRICS})
    ok, res = phase.run(1)
    assert ok is True
    assert res["summary"]["total_files_analyzed"] == 5
    assert res["summary"]["critical_issues"] == 1
    assert res["summary"]["high_issues"] == 1
    out = tmp_path / "out" / "iteration_1" / "phase3_analysis.json"
    assert out.exists()
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["complexity_distribution"]["critical"] == 1
    assert res["output_file"] == str(out)


def test_run_old_measurements_format(phase, tmp_path):
    _write_phase2(
        tmp_path,
        {
            "measurements": [
                {"file_path": "a.py", "analysis": _fm(complexity=5, loc=5)},
                {"file_path": "b.py"},
                {"analysis": _fm()},
            ]
        },
    )
    ok, res = phase.run(1)
    assert ok is True
    assert res["summary"]["total_files_analyzed"] == 1
    assert res["complexity_distribution"]["low"] == 1


def test_run_empty_metrics(phase, tmp_path):
    _write_phase2(tmp_path, {"other": 1})
    ok, res = phase.run(1)
    assert ok is True
    assert res["summary"]["total_files_analyzed"] == 0


def test_execute_passes_through_run(phase, tmp_path):
    _write_phase2(tmp_path, {"file_metrics": {}})
    ok, res = phase.execute(1)
    assert ok is True
    assert res["phase"] == "ANALYZE"


@pytest.mark.parametrize(
    "run_result,expected_ok,key,value",
    [
        ((True, (True, {"x": 1})), True, "x", 1),
        ((1, {"y": 2}), True, "y", 2),
        ((True, "text"), False, "raw_payload_type", "str"),
        ((), False, "error", "Unexpected empty tuple returned from run()"),
        (("only",), False, "error", "Unexpected empty tuple returned from run()"),
        ({"success": False, "z": 3}, False, "z", 3),
        ({"error": "boom"}, False, "error", "boom"),
        ({"fine": 1}, True, "fine", 1),
        (42, False, "raw_result_type", "int"),
    ],
)
def test_execute_normalises_run_results(
    phase, monkeypatch, run_result, expected_ok, key, value
):
    monkeypatch.setattr(phase, "run", lambda iteration: run_result)
    ok, res = phase.execute(5)
    assert ok is expected_ok
    assert res[key] == value
