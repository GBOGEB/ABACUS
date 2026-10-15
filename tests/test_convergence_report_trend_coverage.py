"""Focused real-output branch tests for convergence report generation.

This isolates report paths from workspace scanning and does not change production
behavior. Expected results are read back from actual files.
"""

import json
from dataclasses import replace

import pytest

from DMAIC_V3.convergence.convergence_analyzer import ConvergenceAnalyzer, ConvergenceMetrics


@pytest.fixture
def analyzer(tmp_path):
    instance = ConvergenceAnalyzer.__new__(ConvergenceAnalyzer)
    instance.output_dir = tmp_path
    return instance


@pytest.fixture
def metrics():
    return ConvergenceMetrics(
        iteration=2,
        timestamp="2026-10-13T00:00:00",
        total_files=10,
        stable_files=8,
        file_stability_pct=80.0,
        total_tests=10,
        passing_tests=8,
        test_stability_pct=80.0,
        tracked_metrics=10,
        stable_metrics=8,
        metric_stability_pct=80.0,
        knowledge_packs_total=5,
        knowledge_packs_new=1,
        knowledge_growth_pct=20.0,
        regressions_detected=2,
        convergence_score=80.0,
        converged=False,
        maturity_level=1,
    )


@pytest.mark.parametrize(
    ("previous", "current", "expected"),
    [
        (75.0, 80.0, "+5.0%"),
        (85.0, 80.0, "-5.0%"),
        (80.0, 80.0, "+0.0%"),
    ],
)
def test_report_includes_signed_measured_trend(analyzer, metrics, previous, current, expected):
    (analyzer.output_dir / ".convergence_history.json").write_text(
        json.dumps(
            [
                {"convergence_score": previous},
                {"convergence_score": current},
            ]
        ),
        encoding="utf-8",
    )
    path = analyzer.generate_report(replace(metrics, convergence_score=current))
    report = path.read_text(encoding="utf-8")
    assert "## Trend" in report
    assert expected in report
    assert "Fix 2 failing tests" in report
    assert "Fix 2 regressions" in report
    assert path.name == "convergence_report_iteration_2.md"


def test_report_with_no_history_omits_trend_but_retains_actions(analyzer, metrics):
    path = analyzer.generate_report(metrics)
    body = path.read_text(encoding="utf-8")
    assert "## Trend" not in body
    assert "Stabilize 2 more files" in body
    assert "Stabilize 2 more metrics" in body
    assert "## Next Steps to Achieve Convergence" in body


def test_converged_report_has_no_unnecessary_actions(analyzer, metrics):
    complete = replace(
        metrics,
        convergence_score=100.0,
        converged=True,
        maturity_level=3,
        file_stability_pct=100.0,
        stable_files=10,
        test_stability_pct=100.0,
        passing_tests=10,
        metric_stability_pct=100.0,
        stable_metrics=10,
        regressions_detected=0,
    )
    analyzer._save_metrics(complete)
    path = analyzer.generate_report(complete)
    body = path.read_text(encoding="utf-8")
    assert "[OK] CONVERGED" in body
    assert "Stable Files:** 10/10" in body
    assert "Passing Tests:** 10/10" in body
    assert "Stable Metrics:** 10/10" in body
    assert "3 - Production" in body
    assert "## Next Steps to Achieve Convergence" not in body
    history = json.loads(
        (analyzer.output_dir / ".convergence_history.json").read_text(
            encoding="utf-8"
        )
    )
    assert history[0]["converged"] is True


def test_single_history_entry_does_not_invent_a_trend(analyzer, metrics):
    (analyzer.output_dir / ".convergence_history.json").write_text(
        json.dumps([{"convergence_score": 80.0}]), encoding="utf-8"
    )
    report = analyzer.generate_report(metrics).read_text(encoding="utf-8")
    assert "## Trend" not in report
    assert "## Next Steps to Achieve Convergence" in report


def test_exact_thresholds_have_no_false_stabilization_actions(analyzer, metrics):
    edge = replace(
        metrics,
        total_files=20,
        stable_files=19,
        file_stability_pct=95.0,
        total_tests=10,
        passing_tests=10,
        test_stability_pct=100.0,
        tracked_metrics=20,
        stable_metrics=19,
        metric_stability_pct=95.0,
        regressions_detected=0,
        converged=False,
    )
    report = analyzer.generate_report(edge).read_text(encoding="utf-8")
    assert "🔄 DEVELOPING" in report
    assert "## Next Steps to Achieve Convergence" in report
    assert "- Stabilize " not in report
    assert "- Fix " not in report


def test_short_history_trend_ignores_older_entries(analyzer, metrics):
    (analyzer.output_dir / ".convergence_history.json").write_text(
        json.dumps(
            [
                {"convergence_score": 10.0},
                {"convergence_score": 79.0},
                {"convergence_score": 80.0},
            ]
        ),
        encoding="utf-8",
    )
    report = analyzer.generate_report(metrics).read_text(encoding="utf-8")
    assert "## Trend" in report
    assert "+1.0% from previous iteration" in report
    assert "+70.0% from previous iteration" not in report
