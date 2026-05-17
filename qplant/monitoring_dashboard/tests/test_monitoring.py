"""Tests for QPLANT Advanced Monitoring System."""

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from monitoring_dashboard.predictive import (
    AdvancedMonitor,
    Alert,
    AlertLevel,
    AlertManager,
    PerformanceMonitor,
    SPCMonitor,
    TimeSeriesStore,
)


# ── SPC Tests ────────────────────────────────────────────────────────────────

class TestSPC:
    def test_add_observation(self):
        spc = SPCMonitor()
        result = spc.add_observation("test_metric", 10.0)
        assert result["metric"] == "test_metric"
        assert result["value"] == 10.0

    def test_control_limits(self):
        spc = SPCMonitor()
        for v in [10, 11, 9, 10, 12, 8, 10, 11, 9, 10]:
            result = spc.add_observation("test", v)
        assert "ucl" in result
        assert "lcl" in result
        assert result["ucl"] > result["mean"]
        assert result["lcl"] < result["mean"]

    def test_anomaly_detection(self):
        spc = SPCMonitor(z_threshold=2.0)
        for v in [10] * 20:
            spc.add_observation("test", v)
        # Add an extreme outlier
        result = spc.add_observation("test", 1000)
        assert result["anomaly"] is True

    def test_trend_detection(self):
        spc = SPCMonitor()
        for i in range(20):
            result = spc.add_observation("test", float(i))
        assert result["trend"] == "increasing"

    def test_predict(self):
        spc = SPCMonitor()
        for i in range(20):
            spc.add_observation("test", float(i))
        predictions = spc.predict("test", steps=3)
        assert len(predictions) == 3
        assert predictions[0]["predicted_value"] > 19

    def test_control_chart(self):
        spc = SPCMonitor()
        for i in range(10):
            spc.add_observation("test", float(i))
        chart = spc.get_control_chart("test")
        assert len(chart["data"]) == 10
        assert "ucl" in chart


# ── Alert Tests ──────────────────────────────────────────────────────────────

class TestAlerts:
    def test_fire_alert(self):
        mgr = AlertManager()
        alert = Alert(
            level=AlertLevel.WARNING,
            source="test",
            message="Test warning",
            metric="test_metric",
            value=100,
            threshold=90,
        )
        assert mgr.fire(alert) is True

    def test_alert_aggregation(self):
        mgr = AlertManager(aggregation_window_s=300)
        alert = Alert(
            level=AlertLevel.WARNING, source="test",
            message="Test", metric="m", value=100, threshold=90
        )
        assert mgr.fire(alert) is True
        assert mgr.fire(alert) is False  # Suppressed

    def test_get_active(self):
        mgr = AlertManager()
        mgr.fire(Alert(level=AlertLevel.INFO, source="t", message="i", metric="m", value=1, threshold=0))
        mgr.fire(Alert(level=AlertLevel.CRITICAL, source="t", message="c", metric="m2", value=2, threshold=1))
        active = mgr.get_active()
        assert len(active) == 2

    def test_acknowledge(self):
        mgr = AlertManager()
        mgr.fire(Alert(level=AlertLevel.INFO, source="t", message="i", metric="m", value=1, threshold=0))
        assert mgr.acknowledge(0) is True
        assert len(mgr.get_active()) == 0

    def test_summary(self):
        mgr = AlertManager()
        mgr.fire(Alert(level=AlertLevel.INFO, source="t", message="1", metric="m1", value=1, threshold=0))
        mgr.fire(Alert(level=AlertLevel.WARNING, source="t", message="2", metric="m2", value=2, threshold=1))
        summary = mgr.get_summary()
        assert summary["INFO"] == 1
        assert summary["WARNING"] == 1


# ── Performance Tests ────────────────────────────────────────────────────────

class TestPerformance:
    def test_record_latency(self):
        perf = PerformanceMonitor()
        perf.record_latency("/api/v1/health", 45.2)
        perf.record_latency("/api/v1/health", 50.1)
        stats = perf.get_latency_stats("/api/v1/health")
        assert "/api/v1/health" in stats
        assert stats["/api/v1/health"]["count"] == 2

    def test_build_stats(self):
        perf = PerformanceMonitor()
        perf.record_build_time(22.5, 11, 11)
        stats = perf.get_build_stats()
        assert stats["count"] == 1
        assert stats["avg_duration_s"] == 22.5


# ── Time Series Tests ────────────────────────────────────────────────────────

class TestTimeSeries:
    def test_append_and_query(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ts = TimeSeriesStore(tmpdir)
            ts.append("cpu", 45.2)
            ts.append("cpu", 50.1)
            data = ts.query("cpu", hours=1)
            assert len(data) == 2

    def test_correlation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ts = TimeSeriesStore(tmpdir)
            for i in range(10):
                ts.append("a", float(i))
                ts.append("b", float(i * 2))
            corr = ts.get_correlation("a", "b", hours=1)
            assert corr is not None
            assert corr > 0.99  # Perfect positive correlation

    def test_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ts = TimeSeriesStore(tmpdir)
            for i in range(5):
                ts.append("metric1", float(i))
            report = ts.generate_report(["metric1"], hours=1)
            assert "metric1" in report["metrics"]
            assert report["metrics"]["metric1"]["count"] == 5


# ── Integrated Monitor Tests ────────────────────────────────────────────────

class TestAdvancedMonitor:
    def test_observe(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = AdvancedMonitor(tmpdir)
            result = monitor.observe("api_latency_ms", 50)
            assert result["metric"] == "api_latency_ms"

    def test_threshold_alert(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = AdvancedMonitor(tmpdir)
            monitor.observe("api_latency_ms", 600, source="test")
            alerts = monitor.alerts.get_active()
            critical = [a for a in alerts if a["level"] == "CRITICAL"]
            assert len(critical) >= 1

    def test_dashboard_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = AdvancedMonitor(tmpdir)
            data = monitor.get_dashboard_data()
            assert "alerts" in data
            assert "performance" in data

    def test_set_threshold(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = AdvancedMonitor(tmpdir)
            monitor.set_threshold("custom_metric", 50, 100)
            assert monitor.thresholds["custom_metric"]["warning"] == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
