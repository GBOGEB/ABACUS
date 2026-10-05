import json

import pytest

from DMAIC_V3.convergence.stability_monitor import StabilityMonitor


@pytest.mark.unit
def test_stability_monitor_tracks_changes_regressions_metrics_and_report(tmp_path):
    monitor = StabilityMonitor(tmp_path, window_size=5)
    change_events = []
    alert_events = []
    monitor.register_change_hook(lambda kind, payload: change_events.append((kind, payload)))
    monitor.register_alert_hook(alert_events.append)

    target = tmp_path / "module.py"
    target.write_text("value = 1\n", encoding="utf-8")

    assert monitor.track_file(target) is False
    target.write_text("value = 2\n", encoding="utf-8")
    assert monitor.track_file(target) is True
    assert change_events[-1][0] == "file"
    assert monitor.alerts[-1].alert_type == "file_change"

    monitor.record_test_result("unit::example", "PASSED", 0.1)
    monitor.record_test_result("unit::example", "FAILED", 0.2)
    assert any(alert.alert_type == "test_regression" for alert in monitor.alerts)
    assert any(kind == "test" for kind, _ in change_events)

    for value in (10.0, 10.0, 10.0, 20.0):
        monitor.record_metric("latency", value)
    assert any(alert.alert_type == "metric_variance" for alert in monitor.alerts)
    assert any(kind == "metric" for kind, _ in change_events)

    assert monitor.calculate_file_stability() == 0.0
    assert monitor.calculate_test_stability() == 0.0
    assert monitor.calculate_metric_stability() == 0.0
    assert monitor.calculate_overall_stability() == 0.0

    recommendations = monitor.generate_recommendations()
    assert any("File stability low" in item for item in recommendations)
    assert any("Test stability low" in item for item in recommendations)
    assert any("Metric stability low" in item for item in recommendations)
    assert any("high-severity alerts" in item for item in recommendations)

    monitor.increment_iteration()
    assert monitor.iteration == 1

    output = tmp_path / "stability.json"
    assert monitor.save_report(output) == output
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["metadata"]["iteration"] == 1
    assert payload["stability"]["overall"] == 0.0
    assert len(payload["alerts"]) >= 3
    assert alert_events


@pytest.mark.unit
def test_stability_monitor_defaults_are_stable_and_missing_hash_is_empty(tmp_path, capsys):
    monitor = StabilityMonitor(tmp_path)

    assert monitor._calculate_file_hash(tmp_path / "missing.py") == ""
    assert monitor.calculate_file_stability() == 100.0
    assert monitor.calculate_test_stability() == 100.0
    assert monitor.calculate_metric_stability() == 100.0
    assert monitor.generate_recommendations() == ["System stable - continue current practices"]

    monitor.print_summary()
    output = capsys.readouterr().out
    assert "STABILITY MONITOR REPORT" in output
    assert "Overall Stability" in output
