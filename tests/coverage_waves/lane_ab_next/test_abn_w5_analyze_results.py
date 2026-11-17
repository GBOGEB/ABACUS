"""Behaviour tests for qplant/load_testing/analyze_results.py."""

import json
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("qplant/load_testing/analyze_results.py", name="abn_w5_analyze_results")

BASELINES = {
    "api_endpoints": {
        "/api/v1/health": {"p95_ms": 100, "p99_ms": 200, "error_rate_pct": "1%"},
        "/api/v1/config": {"p95_ms": 50, "p99_ms": 80, "error_rate_pct": 0.5},
    }
}

HEADER = "Type,Name,Request Count,Failure Count,50%,95%,99%\n"


def _row(name, p50, p95, p99, fails, reqs):
    return {
        "Name": name,
        "50%": str(p50),
        "95%": str(p95),
        "99%": str(p99),
        "Failure Count": str(fails),
        "Request Count": str(reqs),
    }


def test_load_baselines_reads_json(tmp_path):
    path = tmp_path / "b.json"
    path.write_text(json.dumps(BASELINES), encoding="utf-8")
    assert mod.load_baselines(str(path)) == BASELINES


def test_parse_locust_stats_rows_and_missing_file(tmp_path):
    path = tmp_path / "s_stats.csv"
    path.write_bytes((HEADER + "GET,/a,10,1,5,9,12\n").encode())
    rows = mod.parse_locust_stats(str(path))
    assert len(rows) == 1
    assert rows[0]["Name"] == "/a"
    assert rows[0]["95%"] == "9"
    assert mod.parse_locust_stats(str(tmp_path / "nope.csv")) == []


def test_grade_all_within_baseline_is_a():
    stats = [
        _row("/api/v1/health", 10, 50, 100, 0, 100),
        _row("Aggregated", 1, 1, 1, 0, 1),
        _row("", 1, 1, 1, 0, 1),
        _row("/unmatched", 999, 9999, 99999, 0, 5),
    ]
    result = mod.grade_performance(stats, BASELINES)
    assert result["grade"] == "A"
    assert result["score"] == 100.0
    assert [e["name"] for e in result["endpoints"]] == ["/api/v1/health", "/unmatched"]
    assert result["regressions"] == []
    assert result["recommendations"] == []
    first = result["endpoints"][0]
    assert first == {
        "name": "/api/v1/health",
        "p50_ms": 10.0,
        "p95_ms": 50.0,
        "p99_ms": 100.0,
        "error_rate_pct": 0.0,
        "requests": 100,
        "score": 100.0,
    }


def test_grade_regressions_penalise_and_recommend():
    stats = [_row("/api/v1/config", 10, 60, 90, 10, 100)]
    result = mod.grade_performance(stats, BASELINES)
    # -20 p95, -10 p99, -30 error rate
    assert result["endpoints"][0]["score"] == 40.0
    assert result["endpoints"][0]["error_rate_pct"] == 10.0
    assert result["grade"] == "F"
    assert result["regressions"] == [
        "/api/v1/config: p95=60.0ms exceeds baseline 50ms",
        "/api/v1/config: error_rate=10.00% exceeds baseline",
    ]
    assert result["recommendations"] == [
        "Investigate performance regressions listed above",
        "Consider scaling up resources or optimizing slow endpoints",
    ]


@pytest.mark.parametrize(
    "p95,p99,fails,grade,score",
    [
        (101, 100, 0, "C", 80.0),
        (50, 201, 0, "B", 90.0),
        (101, 201, 0, "C", 70.0),
        (50, 100, 50, "C", 70.0),
        (101, 100, 50, "D", 50.0),
    ],
)
def test_grade_bands(p95, p99, fails, grade, score):
    stats = [_row("/api/v1/health", 1, p95, p99, fails, 100)]
    result = mod.grade_performance(stats, BASELINES)
    assert result["score"] == score
    assert result["grade"] == grade


def test_grade_name_substring_matching_and_defaults():
    # baseline key contained in the stat name
    stats = [_row("GET /api/v1/health?x=1", 1, 500, 1, 0, 10)]
    result = mod.grade_performance(stats, BASELINES)
    assert result["endpoints"][0]["score"] == 80.0
    # baseline missing p95/p99/error keys falls back to permissive defaults
    loose = {"api_endpoints": {"/x": {}}}
    result = mod.grade_performance([_row("/x", 1, 5000, 5000, 0, 10)], loose)
    assert result["endpoints"][0]["score"] == 100.0
    # zero requests never divide by zero
    result = mod.grade_performance([_row("/y", 1, 1, 1, 0, 0)], {})
    assert result["endpoints"][0]["error_rate_pct"] == 0.0


def test_grade_empty_stats():
    result = mod.grade_performance([], BASELINES)
    assert result["score"] == 0.0
    assert result["grade"] == "F"
    assert result["endpoints"] == []
    assert result["recommendations"] == [
        "Consider scaling up resources or optimizing slow endpoints"
    ]


def _write_inputs(tmp_path, body):
    (tmp_path / "base.json").write_text(json.dumps(BASELINES), encoding="utf-8")
    (tmp_path / "run_stats.csv").write_bytes((HEADER + body).encode())


def test_main_with_prefix_and_output(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_inputs(
        tmp_path,
        "GET,/api/v1/health,100,0,5,50,100\n"
        "GET,/api/v1/config,100,0,5,60,70\n"
        "GET,/api/v1/other,100,50,5,60,70\n",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "analyze_results.py",
            "--csv-prefix",
            "run",
            "--baselines",
            "base.json",
            "--output",
            "out.json",
        ],
    )
    mod.main()
    out = capsys.readouterr().out
    assert "Performance Grade: B (93.3/100)" in out
    assert "/api/v1/health" in out
    assert "p50=5.0ms  p95=60.0ms  err=0.0%" in out
    assert "Regressions:" in out
    assert "exceeds baseline 50ms" in out
    assert "Recommendations:" in out
    assert "Report saved to out.json" in out
    saved = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert saved["grade"] == "B"
    assert len(saved["endpoints"]) == 3


def test_main_status_icons_for_low_scores(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_inputs(
        tmp_path,
        "GET,/api/v1/health,100,0,5,500,500\n" "GET,/api/v1/config,100,90,5,500,500\n",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["a", "--csv-prefix", "run", "--baselines", "base.json"],
    )
    mod.main()
    out = capsys.readouterr().out
    # health: 70 -> warning icon; config: 40 -> fail icon
    assert "⚠️ /api/v1/health" in out
    assert "❌ /api/v1/config" in out
    assert "Report saved" not in out


def test_main_clean_run_has_no_regression_section(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_inputs(tmp_path, "GET,/api/v1/health,100,0,5,50,100\n")
    monkeypatch.setattr(
        sys, "argv", ["a", "--csv-prefix", "run", "--baselines", "base.json"]
    )
    mod.main()
    out = capsys.readouterr().out
    assert "Performance Grade: A (100.0/100)" in out
    assert "✅ /api/v1/health" in out
    assert "Regressions" not in out
    assert "Recommendations" not in out


def test_main_autodiscovers_latest_report(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "performance_baselines.json").write_text(
        json.dumps(BASELINES), encoding="utf-8"
    )
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "a_20260101_stats.csv").write_bytes(
        (HEADER + "GET,/old,1,0,1,1,1\n").encode()
    )
    (reports / "b_20260202_stats.csv").write_bytes(
        (HEADER + "GET,/newest,1,0,1,1,1\n").encode()
    )
    monkeypatch.setattr(sys, "argv", ["a"])
    mod.main()
    out = capsys.readouterr().out
    assert "Using most recent:" in out
    assert "b_20260202_stats.csv" in out
    assert "/newest" in out
    assert "/old" not in out


def test_main_no_reports_exits_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["a"])
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 1
    assert "No load test results found" in capsys.readouterr().out


def test_main_empty_stats_exits_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "base.json").write_text(json.dumps(BASELINES), encoding="utf-8")
    monkeypatch.setattr(
        sys, "argv", ["a", "--csv-prefix", "missing", "--baselines", "base.json"]
    )
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 1
    assert "No stats found in missing_stats.csv" in capsys.readouterr().out
