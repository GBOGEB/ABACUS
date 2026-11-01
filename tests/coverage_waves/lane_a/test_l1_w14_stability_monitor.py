"""Lane A wave 14: DMAIC_V3.convergence.stability_monitor tracking and reports."""

import json
import sys

import pytest

from DMAIC_V3.convergence import stability_monitor as sm


@pytest.fixture
def mon(tmp_path):
    return sm.StabilityMonitor(workspace_path=tmp_path, window_size=5)


def test_file_tracking_and_hooks(mon, tmp_path, capsys):
    seen = []
    alerts = []
    mon.register_change_hook(lambda kind, snap: seen.append(kind))
    mon.register_alert_hook(alerts.append)

    def broken(*args):
        raise RuntimeError("hook bug")

    mon.register_change_hook(broken)
    f = tmp_path / "a.py"
    f.write_bytes(b"one")
    assert mon.track_file(f) is False
    assert mon.track_file(f) is False
    f.write_bytes(b"two")
    assert mon.track_file(f) is True
    assert seen == ["file"]
    assert alerts[0].alert_type == "file_change"
    assert "Hook execution failed: hook bug" in capsys.readouterr().out
    assert mon.calculate_file_stability() == 0.0


def test_snapshot_missing_file_and_hash_errors(mon, tmp_path, monkeypatch):
    snap = mon.snapshot_file(tmp_path / "ghost.py")
    assert (snap.hash, snap.size, snap.modified) == ("", 0, 0)
    assert mon._calculate_file_hash(tmp_path / "ghost.py") == ""
    d = tmp_path / "adir"
    d.mkdir()
    assert mon._calculate_file_hash(d) == ""


def test_scan_workspace(mon, tmp_path):
    pkg = tmp_path / "DMAIC_V3" / "x"
    pkg.mkdir(parents=True)
    f = pkg / "m.py"
    f.write_bytes(b"a")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "c.yaml").write_bytes(b"k: 1")
    assert mon.scan_workspace() == 0
    f.write_bytes(b"b")
    assert mon.scan_workspace() == 1
    assert mon.track_files([]) == 0


def test_test_results_regression_and_stability(mon):
    mon.record_test_result("t1", "PASSED", 0.1)
    mon.record_test_result("t1", "FAILED", 0.2)
    mon.record_test_result("t2", "PASSED", 0.1)
    mon.record_test_result("t2", "PASSED", 0.1)
    mon.record_test_result("t3", "FAILED", 0.1)
    mon.record_test_result("t3", "FAILED", 0.1)
    reg = [a for a in mon.alerts if a.alert_type == "test_regression"]
    assert len(reg) == 1
    assert reg[0].severity == "HIGH"
    assert mon.calculate_test_stability() == pytest.approx(100 / 3)


def test_metric_variance_and_stability(mon):
    for v in (10, 10, 10):
        mon.record_metric("m", v)
    mon.record_metric("m", 20)
    var = [a for a in mon.alerts if a.alert_type == "metric_variance"]
    assert len(var) == 1
    assert var[0].details["variance"] == pytest.approx(1.0)
    for v in (0, 0, 0, 0):
        mon.record_metric("zero", v)
    for v in (5, 5, 5):
        mon.record_metric("flat", v)
    mon.record_metric("short", 1)
    assert mon.calculate_metric_stability() == pytest.approx(100 / 3)


def test_empty_stability_defaults(mon):
    assert mon.calculate_file_stability() == 100.0
    assert mon.calculate_test_stability() == 100.0
    assert mon.calculate_metric_stability() == 100.0
    mon.record_test_result("t", "PASSED", 0.0)
    mon.record_metric("m", 1.0)
    mon.track_file(mon.workspace_path / "nothing")
    assert mon.calculate_test_stability() == 100.0
    assert mon.calculate_metric_stability() == 100.0
    assert mon.calculate_file_stability() == 100.0
    assert mon.calculate_overall_stability() == 100.0
    assert mon.generate_recommendations() == [
        "System stable - continue current practices"
    ]


def test_recommendations_when_unstable(mon, tmp_path):
    f = tmp_path / "x.py"
    f.write_bytes(b"1")
    mon.track_file(f)
    f.write_bytes(b"2")
    mon.track_file(f)
    mon.record_test_result("t", "PASSED", 0.0)
    mon.record_test_result("t", "FAILED", 0.0)
    for v in (1, 1, 1, 9):
        mon.record_metric("m", v)
    recs = mon.generate_recommendations()
    assert len(recs) == 4
    assert recs[-1] == "Address 1 high-severity alerts"


def test_report_save_and_summary(mon, tmp_path, capsys):
    mon.increment_iteration()
    for i in range(12):
        mon._create_alert("x", ["HIGH", "MEDIUM", "LOW"][i % 3], f"msg{i}", {})
    report = mon.generate_report()
    assert report.iteration == 1
    assert report.version == sm.VERSION
    out = tmp_path / "rep.json"
    assert mon.save_report(out) == out
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["metadata"]["generator"] == "StabilityMonitor"
    assert len(data["alerts"]) == 12
    default = mon.save_report()
    assert default.parent == tmp_path
    assert default.name.startswith("stability_report_")
    mon.print_summary()
    text = capsys.readouterr().out
    assert "... and 2 more alerts" in text
    assert "msg11" in text and "msg1\n" not in text


def test_summary_without_alerts(mon, capsys):
    mon.print_summary()
    text = capsys.readouterr().out
    assert "ALERTS" not in text
    assert "1. System stable" in text


@pytest.mark.parametrize(
    "argv,expect_files",
    [(["--json"], 1), (["--save"], 1), ([], 0)],
)
def test_main(tmp_path, monkeypatch, capsys, argv, expect_files):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["stability_monitor.py", *argv])
    sm.main()
    assert len(list(tmp_path.glob("stability_report_*.json"))) == expect_files
    assert "Tracked 0 file changes" in capsys.readouterr().out
