"""Lane A wave 4: dmaic-sprint-system/code/compare_iterations.py."""

import json
import sys
from pathlib import Path

import pytest

from tests.coverage_waves.lane_a._load import load

ci = load("dmaic-sprint-system/code/compare_iterations.py")

PHASE_PATHS = {
    "phase0_setup": "phase0_setup.json",
    "phase1_define": "phase1_define/phase1_define.json",
    "phase2_measure": "phase2_measure/phase2_measure.json",
    "phase3_analyze": "phase3_analysis.json",
    "phase4_improve": "phase4_improvements.json",
    "phase5_control": "phase5_control/phase5_control.json",
}


def _iteration(root, n, phases):
    base = root / ("iteration_" + str(n))
    base.mkdir(parents=True)
    for name, payload in phases.items():
        path = base / PHASE_PATHS[name]
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(payload, bytes):
            path.write_bytes(payload)
        else:
            path.write_bytes(json.dumps(payload).encode())
    return base


def _full(files, issues, duration):
    return {
        "phase0_setup": {"ok": True},
        "phase1_define": {
            "total_files": files,
            "documentation_files": 2,
            "code_files": files - 2,
            "duration": duration,
        },
        "phase2_measure": {"total_metrics": 0, "duration": 1},
        "phase3_analyze": {"summary": {"critical_issues": issues, "high_issues": 1}},
        "phase4_improve": {"total_improvements": 3, "improvements_applied": 1},
        "phase5_control": {"quality_gates_count": 4, "validation_checkpoints": 2},
    }


@pytest.fixture
def comp(tmp_path):
    return ci.IterationComparator(tmp_path)


def test_default_output_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    expected = tmp_path / "DMAIC_V3_OUTPUT" / "sprints"
    assert ci.IterationComparator().output_dir == expected


def test_load_iteration_data_missing_corrupt_and_partial(comp, tmp_path, capsys):
    assert comp.load_iteration_data(7) is None
    _iteration(
        tmp_path, 1, {"phase1_define": {"total_files": 3}, "phase3_analyze": b"{"}
    )
    data = comp.load_iteration_data(1)
    assert data["iteration"] == 1
    assert data["phases"]["phase1_define"] == {"total_files": 3}
    assert data["phases"]["phase3_analyze"] is None
    assert data["phases"]["phase0_setup"] is None
    assert "Error loading" in capsys.readouterr().out


def test_extract_key_metrics(comp, tmp_path):
    assert comp.extract_key_metrics(None) == {}
    _iteration(tmp_path, 1, _full(10, 2, 5))
    metrics = comp.extract_key_metrics(comp.load_iteration_data(1))
    assert metrics["phases_completed"] == 6
    assert metrics["files_scanned"] == 10
    assert metrics["code_files"] == 8
    assert metrics["total_issues"] == 3
    assert metrics["medium_issues"] == 0
    assert metrics["improvements_applied"] == 1
    assert metrics["quality_gates"] == 4

    sparse = {"iteration": 2, "phases": {"phase0_setup": {"a": 1}}}
    assert comp.extract_key_metrics(sparse) == {"iteration": 2, "phases_completed": 1}


def test_compare_iterations_missing_sides(comp, tmp_path, capsys):
    assert comp.compare_iterations(1, 2) is None
    assert "Iteration 1 data not found" in capsys.readouterr().out
    _iteration(tmp_path, 1, _full(10, 2, 5))
    assert comp.compare_iterations(1, 2) is None
    assert "Iteration 2 data not found" in capsys.readouterr().out


def test_compare_iterations_computes_changes(comp, tmp_path):
    _iteration(tmp_path, 1, _full(10, 2, 5))
    _iteration(tmp_path, 2, _full(15, 1, 4))
    result = comp.compare_iterations(1, 2)
    imp = result["improvements"]
    assert "iteration" not in imp
    assert imp["files_scanned"] == {
        "iteration_1": 10,
        "iteration_2": 15,
        "change": 5,
        "percent_change": 50.0,
    }
    assert imp["critical_issues"]["change"] == -1
    assert imp["metrics_collected"]["percent_change"] == 0
    assert imp["medium_issues"]["percent_change"] == 0


def test_compare_iterations_zero_baseline_is_infinite(comp, tmp_path):
    first = _full(10, 0, 5)
    second = _full(10, 3, 5)
    _iteration(tmp_path, 1, first)
    _iteration(tmp_path, 2, second)
    result = comp.compare_iterations(1, 2)
    assert result["improvements"]["critical_issues"]["percent_change"] == float("inf")


def test_print_comparison_formats_rows(comp, capsys):
    comp.print_comparison(None)
    assert capsys.readouterr().out == ""
    comparison = {
        "iteration_1": 1,
        "iteration_2": 2,
        "comparison_date": "D",
        "improvements": {
            "files_scanned": _row(10, 15, 50.0),
            "code_files": _row(8, 6, -25.0),
            "critical_issues": _row(2, 1, -50.0),
            "total_issues": _row(0, 3, float("inf")),
            "high_issues": _row(1, 1, 0.0),
            "scan_duration": _row(5.0, 4.5, -10.0),
        },
    }
    comp.print_comparison(comparison)
    lines = capsys.readouterr().out.splitlines()
    row = {line.split()[0]: line.split() for line in lines if line[:1].islower()}
    assert row["files_scanned"][1:] == ["10", "15", "+5", "+50.0%", "↑"]
    assert row["code_files"][-1] == "↓"
    assert row["critical_issues"][-1] == "↓"
    assert row["total_issues"][4] == "N/A"
    assert row["high_issues"][-1] == "="
    assert row["scan_duration"][1:4] == ["5.00", "4.50", "-0.50"]


def _row(a, b, pct):
    return {"iteration_1": a, "iteration_2": b, "change": b - a, "percent_change": pct}


def check_production_defect_print_comparison_int_to_float_metric(comp):
    """change is formatted with :+d when iteration 1 is an int, so 5 -> 5.5 fails."""
    # Reproduction of a production_defect (see WAVE_LEDGER.jsonl). Named check_*
    # so the governed suite does not collect it: a pinned defect must never block
    # the fix. Run on demand: pytest -o python_functions=check_* <this file>
    comparison = {
        "iteration_1": 1,
        "iteration_2": 2,
        "comparison_date": "D",
        "improvements": {"scan_duration": _row(5, 5.5, 10.0)},
    }
    with pytest.raises(ValueError, match="Unknown format code 'd'"):
        comp.print_comparison(comparison)


def test_save_comparison_paths(comp, tmp_path, capsys):
    explicit = tmp_path / "out.json"
    assert comp.save_comparison({"a": 1}, explicit) == explicit
    assert json.loads(explicit.read_text(encoding="utf-8")) == {"a": 1}
    default = comp.save_comparison({"b": 2})
    assert default.parent == tmp_path
    assert default.name.startswith("iteration_comparison_")
    assert "Comparison report saved" in capsys.readouterr().out


def test_main_success_and_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    sprints = tmp_path / "DMAIC_V3_OUTPUT" / "sprints"
    monkeypatch.setattr(sys, "argv", ["compare_iterations.py"])
    assert ci.main() == 1
    assert "Comparison failed" in capsys.readouterr().out

    _iteration(sprints, 1, _full(10, 2, 5))
    _iteration(sprints, 3, _full(12, 2, 5))
    out = tmp_path / "cmp.json"
    monkeypatch.setattr(
        sys, "argv", ["c", "--iter1", "1", "--iter2", "3", "--output", str(out)]
    )
    assert ci.main() == 0
    assert json.loads(out.read_text(encoding="utf-8"))["iteration_2"] == 3
    assert Path(out).exists()
