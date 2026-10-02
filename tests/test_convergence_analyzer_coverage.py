from __future__ import annotations

from DMAIC_V3.convergence.convergence_analyzer import (
    ConvergenceAnalyzer,
    ConvergenceMetrics,
)


def test_analyze_executes_convergence_status_lines(tmp_path, capsys, monkeypatch):
    analyzer = ConvergenceAnalyzer(config_path=str(tmp_path / "missing.yaml"))
    analyzer.output_dir = tmp_path

    monkeypatch.setattr(analyzer, "scan_workspace_files", lambda: (10, 9))
    monkeypatch.setattr(analyzer, "check_test_stability", lambda: (10, 10))
    monkeypatch.setattr(analyzer, "check_metric_stability", lambda: (8, 8))
    monkeypatch.setattr(analyzer, "check_knowledge_growth", lambda: (10, 1))

    metrics = analyzer.analyze()

    output = capsys.readouterr().out
    assert "[1/5] Scanning workspace files..." in output
    assert "[2/5] Checking test stability..." in output
    assert "[3/5] Checking metric stability..." in output
    assert "[4/5] Checking knowledge growth..." in output
    assert "[5/5] Checking for regressions..." in output
    assert metrics.total_files == 10
    assert metrics.stable_files == 9


def test_generate_report_executes_literal_target_lines(tmp_path, monkeypatch):
    analyzer = ConvergenceAnalyzer(config_path=str(tmp_path / "missing.yaml"))
    analyzer.output_dir = tmp_path
    monkeypatch.setattr(analyzer, "get_trend", lambda: None)

    metrics = ConvergenceMetrics(
        iteration=1,
        timestamp="2026-10-02T00:00:00",
        total_files=10,
        stable_files=9,
        file_stability_pct=90.0,
        total_tests=10,
        passing_tests=10,
        test_stability_pct=100.0,
        tracked_metrics=8,
        stable_metrics=8,
        metric_stability_pct=100.0,
        knowledge_packs_total=10,
        knowledge_packs_new=1,
        knowledge_growth_pct=10.0,
        regressions_detected=0,
        convergence_score=92.5,
        converged=False,
        maturity_level=2,
    )

    report = analyzer.generate_report(metrics)
    text = report.read_text(encoding="utf-8")

    assert "- **Target:** ≥95%" in text
    assert "- **Target:** 100%" in text
    assert "- **Target:** >0%" in text
    assert "- **Target:** 0" in text
    assert "## Detailed Metrics" in text
