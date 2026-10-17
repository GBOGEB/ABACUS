"""Behavioral C3 coverage for stability telemetry and alert control."""

import json

from DMAIC_V3.convergence.stability_monitor import StabilityMonitor


def test_stability_monitor_tracks_regressions_variance_and_report(tmp_path):
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

    monitor.record_test_result("unit::example", "PASSED", 0.1)
    monitor.record_test_result("unit::example", "FAILED", 0.2)

    for value in (10.0, 10.0, 10.0, 20.0):
        monitor.record_metric("latency", value)

    assert any(alert.alert_type == "file_change" for alert in monitor.alerts)
    assert any(alert.alert_type == "test_regression" for alert in monitor.alerts)
    assert any(alert.alert_type == "metric_variance" for alert in monitor.alerts)
    assert {kind for kind, _ in change_events} == {"file", "test", "metric"}

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
    output = tmp_path / "stability.json"
    assert monitor.save_report(output) == output
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["metadata"]["iteration"] == 1
    assert payload["stability"]["overall"] == 0.0
    assert len(payload["alerts"]) >= 3
    assert alert_events


def test_stable_samples_missing_hash_and_hook_failure_are_fail_soft(tmp_path, capsys):
    monitor = StabilityMonitor(tmp_path, window_size=4)

    missing = tmp_path / "missing.py"
    assert monitor._calculate_file_hash(missing) == ""
    assert monitor.snapshot_file(missing).size == 0

    directory = tmp_path / "directory"
    directory.mkdir()
    assert monitor._calculate_file_hash(directory) == ""

    def broken_hook(*args, **kwargs):
        raise RuntimeError("observer unavailable")

    monitor.register_change_hook(broken_hook)
    target = tmp_path / "stable.py"
    target.write_text("stable = True\n", encoding="utf-8")
    assert monitor.track_file(target) is False
    assert monitor.track_file(target) is False

    monitor.record_test_result("stable-test", "PASSED", 0.1)
    monitor.record_test_result("stable-test", "PASSED", 0.1)
    for value in (100.0, 101.0, 99.0):
        monitor.record_metric("throughput", value)

    assert monitor.calculate_file_stability() == 100.0
    assert monitor.calculate_test_stability() == 100.0
    assert monitor.calculate_metric_stability() == 100.0
    assert monitor.calculate_overall_stability() == 100.0
    assert monitor.generate_recommendations() == [
        "System stable - continue current practices"
    ]
    assert "Hook execution failed" in capsys.readouterr().out


def test_scan_patterns_and_alert_summary_paths(tmp_path, capsys):
    monitor = StabilityMonitor(tmp_path)
    monitor.watch_patterns = ["*.py"]
    (tmp_path / "a.py").write_text("a = 1\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("b = 1\n", encoding="utf-8")

    assert monitor.scan_workspace() == 0
    (tmp_path / "a.py").write_text("a = 2\n", encoding="utf-8")
    assert monitor.scan_workspace() == 1

    for index in range(12):
        monitor._create_alert(
            "synthetic-control",
            "INFO" if index < 11 else "HIGH",
            f"alert-{index}",
            {"index": index},
        )

    monitor.print_summary()
    output = capsys.readouterr().out
    assert "STABILITY MONITOR REPORT" in output
    assert "... and" in output
    assert "Address 1 high-severity alerts" in output
