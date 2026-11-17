"""Measured convergence scoring, history, and runtime artifact regressions."""

import json

import pytest
import yaml

from DMAIC_V3.convergence.convergence_analyzer import ConvergenceAnalyzer


@pytest.fixture
def analyzer(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return ConvergenceAnalyzer(str(tmp_path / "missing-maturity.yaml"))


def test_default_thresholds_and_score_bounds(analyzer):
    assert analyzer.config["convergence_calculation"]["thresholds"]["converged"] == 95
    assert analyzer.calculate_convergence_score(100, 100, 100, 100, 0) == 100
    assert analyzer.calculate_convergence_score(100, 100, 100, 200, 0) == 100
    assert analyzer.calculate_convergence_score(100, 100, 100, 100, 1) == 90
    assert analyzer.calculate_convergence_score(0, 0, 0, 0, 1) == 0
    assert [analyzer.determine_maturity_level(value) for value in (10, 70, 85, 95)] == [
        0,
        1,
        2,
        3,
    ]


def test_custom_yaml_config_and_hashing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = {
        "convergence_calculation": {
            "weights": {
                "file_stability": 0.5,
                "test_stability": 0.5,
                "metric_stability": 0,
                "knowledge_growth": 0,
                "zero_regressions": 0,
            },
            "thresholds": {
                "converged": 90,
                "stable": 70,
                "developing": 50,
            },
        }
    }
    path = tmp_path / "maturity.yaml"
    path.write_text(yaml.safe_dump(config))
    current = ConvergenceAnalyzer(str(path))
    assert current.calculate_convergence_score(100, 0, 0, 0, 0) == 50
    assert current.determine_maturity_level(90) == 3
    payload = tmp_path / "payload.py"
    payload.write_bytes(b"print('a')\n")
    initial_hash = current.calculate_file_hash(payload)
    assert len(initial_hash) == 64
    payload.write_bytes(b"print('b')\n")
    assert current.calculate_file_hash(payload) != initial_hash
    assert current.calculate_file_hash(tmp_path / "missing.py").startswith("ERROR:")


def test_workspace_history_three_sample_stability_contract(analyzer, tmp_path):
    source = tmp_path / "app.py"
    source.write_text("VALUE = 1\n")
    (tmp_path / "__init__.py").write_text("# excluded\n")
    first = analyzer.scan_workspace_files()
    second = analyzer.scan_workspace_files()
    third = analyzer.scan_workspace_files()
    fourth = analyzer.scan_workspace_files()
    assert first == (1, 0)
    assert second == (1, 0)
    assert third == (1, 0)
    assert fourth == (1, 1)
    history_file = analyzer.output_dir / ".file_hashes.json"
    history = json.loads(history_file.read_text())
    assert len(history) == 4
    assert history[-1]["hashes"]["app.py"] == analyzer.calculate_file_hash(source)


def test_knowledge_growth_missing_and_present(analyzer, tmp_path):
    assert analyzer.check_knowledge_growth() == (0, 0)
    knowledge = tmp_path / "DMAIC_V3_OUTPUT/knowledge"
    knowledge.mkdir(parents=True)
    (knowledge / "one.json").write_text("{}")
    assert analyzer.check_knowledge_growth() == (1, 1)
    for i in range(2, 21):
        (knowledge / f"{i}.json").write_text("{}")
    assert analyzer.check_knowledge_growth() == (20, 2)


def test_analyze_writes_true_counts_scores_and_report(analyzer, monkeypatch):
    monkeypatch.setattr(analyzer, "scan_workspace_files", lambda: (2, 2))
    monkeypatch.setattr(analyzer, "check_test_stability", lambda: (10, 10))
    monkeypatch.setattr(analyzer, "check_metric_stability", lambda: (8, 6))
    monkeypatch.setattr(analyzer, "check_knowledge_growth", lambda: (2, 1))
    metrics = analyzer.analyze()
    assert metrics.iteration == 1
    assert metrics.file_stability_pct == 100
    assert metrics.metric_stability_pct == 75
    assert metrics.knowledge_growth_pct == 50
    assert metrics.convergence_score == 87.5
    assert metrics.maturity_level == 2
    assert metrics.converged is False
    report = analyzer.generate_report(metrics)
    assert report.is_file()
    content = report.read_text()
    assert "**Overall Score:** 87.5%" in content
    assert "**Stable Files:** 2/2" in content
    assert analyzer.get_trend() is None
    assert (
        json.loads((analyzer.output_dir / ".convergence_history.json").read_text())[0][
            "iteration"
        ]
        == 1
    )


def test_second_iteration_trend_and_degraded_scenario(analyzer, tmp_path):
    source = tmp_path / "changing.py"
    source.write_text("VALUE = 1\n")
    for _ in range(3):
        analyzer.scan_workspace_files()
    first = analyzer.analyze()
    source.write_text("VALUE = 2\n")
    second = analyzer.analyze()
    assert second.iteration == first.iteration + 1
    assert first.stable_files == 1
    assert second.stable_files == 0
    assert second.convergence_score < first.convergence_score
    assert analyzer.get_trend() == pytest.approx(
        second.convergence_score - first.convergence_score
    )
    report = analyzer.generate_report(second)
    assert "## Trend" in report.read_text()


def test_history_missing_does_not_fabricate_progress(analyzer):
    assert analyzer.get_trend() is None
    assert analyzer.check_test_stability() == (10, 10)
    assert analyzer.check_metric_stability() == (8, 6)
