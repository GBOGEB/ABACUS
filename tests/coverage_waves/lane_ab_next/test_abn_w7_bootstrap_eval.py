"""Gap tests for bootstrap_eval.py: folder parsing, analyse_group, run_analysis."""

import math

import numpy as np
import pandas as pd

from tests.coverage_waves.lane_b._l2_loader import load

be = load("bootstrap_eval.py", name="abn_w7_bootstrap_eval")


def test_load_from_folders_skips_non_numeric(tmp_path):
    group = tmp_path / "alpha"
    group.mkdir()
    (group / "a.txt").write_text("1.5", encoding="utf-8")
    (group / "b.txt").write_text("not-a-number", encoding="utf-8")
    (tmp_path / "loose.txt").write_text("9", encoding="utf-8")
    frame = be.load_from_folders(tmp_path)
    assert frame.to_dict("records") == [{"group": "alpha", "score": 1.5}]


def test_analyse_group_writes_placeholder_and_stats(tmp_path):
    out_dir = tmp_path / "out"
    result = be.analyse_group("grp/1", [1.0, 2.0, 3.0, float("nan")], out_dir)
    assert result["name"] == "grp/1"
    assert result["n"] == 3
    assert result["mean"] == 2.0
    assert result["std"] == 1.0
    assert result["ci_norm_low"] < 2.0 < result["ci_norm_high"]
    assert 1.0 <= result["ci_boot_low"] <= result["ci_boot_high"] <= 3.0
    plot = out_dir / "grp_1.txt"
    assert result["plot_path"] == str(plot)
    assert plot.read_text(encoding="utf-8") == "plot placeholder\n"


def test_analyse_group_empty_and_single_values(tmp_path):
    empty = be.analyse_group("e", [], tmp_path)
    assert empty["n"] == 0
    assert math.isnan(empty["mean"]) and math.isnan(empty["std"])
    single = be.analyse_group("s", np.array([4.0]), tmp_path)
    assert single["mean"] == 4.0
    assert math.isnan(single["std"])


def test_run_analysis_writes_report(tmp_path):
    frame = pd.DataFrame(
        {
            "group": ["a", "a", "a", "b", "b", "b"],
            "score": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        }
    )
    out_dir = tmp_path / "report_dir"
    be.run_analysis(frame, out_dir=str(out_dir))
    report = (out_dir / "report.md").read_text(encoding="utf-8")
    assert report.startswith("# Bootstrap Evaluation Report")
    assert "Rows: 6" in report
    assert "- a: n=3 mean=2.000" in report
    assert "- b: n=3 mean=5.000" in report
    assert "- a vs b: diff=3.000 ci=[" in report
    assert (out_dir / "a.txt").exists() and (out_dir / "b.txt").exists()
