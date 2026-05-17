"""QPLANT Advanced Monitoring — Predictive Analytics & Alerting.

Implements:
- Statistical Process Control (SPC) for metrics
- Anomaly detection using z-scores and moving averages
- Trend prediction using linear regression
- Multi-level alerting (INFO, WARNING, CRITICAL, PREDICTIVE)
- Alert aggregation and routing
- Performance monitoring (API latency, build times, resource usage)
- Time-series storage and historical analysis
"""

from __future__ import annotations

import json
import logging
import math
import os
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Alert System ─────────────────────────────────────────────────────────────

class AlertLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    PREDICTIVE = "PREDICTIVE"


@dataclass
class Alert:
    level: AlertLevel
    source: str
    message: str
    metric: str
    value: float
    threshold: float
    timestamp: str = ""
    acknowledged: bool = False
    routing: List[str] = field(default_factory=lambda: ["dashboard"])

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "source": self.source,
            "message": self.message,
            "metric": self.metric,
            "value": self.value,
            "threshold": self.threshold,
            "timestamp": self.timestamp,
            "acknowledged": self.acknowledged,
            "routing": self.routing,
        }


class AlertManager:
    """Manages alert lifecycle: creation, aggregation, routing, escalation."""

    def __init__(self, max_alerts: int = 1000, aggregation_window_s: int = 300):
        self.alerts: deque = deque(maxlen=max_alerts)
        self.aggregation_window = aggregation_window_s
        self._recent: Dict[str, datetime] = {}
        self.escalation_policies: Dict[str, List[str]] = {
            AlertLevel.INFO.value: ["dashboard"],
            AlertLevel.WARNING.value: ["dashboard", "log"],
            AlertLevel.CRITICAL.value: ["dashboard", "log", "email"],
            AlertLevel.PREDICTIVE.value: ["dashboard", "log"],
        }

    def fire(self, alert: Alert) -> bool:
        """Fire an alert. Returns False if suppressed by aggregation."""
        key = f"{alert.source}:{alert.metric}:{alert.level.value}"
        now = datetime.now(timezone.utc)

        if key in self._recent:
            elapsed = (now - self._recent[key]).total_seconds()
            if elapsed < self.aggregation_window:
                logger.debug(f"Alert suppressed (aggregation): {key}")
                return False

        alert.routing = self.escalation_policies.get(alert.level.value, ["dashboard"])
        self._recent[key] = now
        self.alerts.append(alert)
        logger.info(f"Alert fired: [{alert.level.value}] {alert.message}")
        return True

    def get_active(self, level: Optional[AlertLevel] = None) -> List[Dict[str, Any]]:
        """Get active (unacknowledged) alerts."""
        alerts = [a for a in self.alerts if not a.acknowledged]
        if level:
            alerts = [a for a in alerts if a.level == level]
        return [a.to_dict() for a in alerts]

    def acknowledge(self, index: int) -> bool:
        """Acknowledge an alert by index."""
        if 0 <= index < len(self.alerts):
            self.alerts[index].acknowledged = True
            return True
        return False

    def get_summary(self) -> Dict[str, int]:
        """Get alert count by level."""
        summary = defaultdict(int)
        for a in self.alerts:
            if not a.acknowledged:
                summary[a.level.value] += 1
        return dict(summary)


# ── Statistical Process Control ──────────────────────────────────────────────

class SPCMonitor:
    """Statistical Process Control for metric monitoring.

    Implements:
    - Control limits (UCL/LCL) based on ±3σ
    - Z-score anomaly detection
    - Moving average with configurable window
    - Trend detection via linear regression
    """

    def __init__(self, window_size: int = 30, z_threshold: float = 3.0):
        self.window_size = window_size
        self.z_threshold = z_threshold
        self.series: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size * 10))
        self.timestamps: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size * 10))

    def add_observation(self, metric: str, value: float, ts: Optional[str] = None) -> Dict[str, Any]:
        """Add an observation and return analysis."""
        self.series[metric].append(value)
        self.timestamps[metric].append(ts or datetime.now(timezone.utc).isoformat())

        data = list(self.series[metric])
        result = {
            "metric": metric,
            "value": value,
            "count": len(data),
            "anomaly": False,
            "trend": "stable",
        }

        if len(data) < 3:
            return result

        mean = statistics.mean(data)
        stdev = statistics.stdev(data) if len(data) > 1 else 0.0

        result["mean"] = round(mean, 4)
        result["stdev"] = round(stdev, 4)

        # Control limits
        if stdev > 0:
            result["ucl"] = round(mean + 3 * stdev, 4)
            result["lcl"] = round(mean - 3 * stdev, 4)

            # Z-score anomaly detection
            z_score = (value - mean) / stdev
            result["z_score"] = round(z_score, 4)
            result["anomaly"] = abs(z_score) > self.z_threshold

        # Moving average
        window = data[-self.window_size:]
        result["moving_avg"] = round(statistics.mean(window), 4)

        # Trend detection (linear regression on recent window)
        if len(window) >= 5:
            trend = self._linear_trend(window)
            result["trend_slope"] = round(trend, 6)
            if abs(trend) < 0.001:
                result["trend"] = "stable"
            elif trend > 0:
                result["trend"] = "increasing"
            else:
                result["trend"] = "decreasing"

        return result

    def get_control_chart(self, metric: str) -> Dict[str, Any]:
        """Get control chart data for a metric."""
        data = list(self.series[metric])
        ts = list(self.timestamps[metric])
        if not data:
            return {"metric": metric, "data": [], "timestamps": []}

        mean = statistics.mean(data)
        stdev = statistics.stdev(data) if len(data) > 1 else 0.0

        return {
            "metric": metric,
            "data": data,
            "timestamps": ts,
            "mean": round(mean, 4),
            "stdev": round(stdev, 4),
            "ucl": round(mean + 3 * stdev, 4),
            "lcl": round(mean - 3 * stdev, 4),
            "count": len(data),
        }

    def predict(self, metric: str, steps: int = 5) -> List[Dict[str, Any]]:
        """Predict future values using linear regression."""
        data = list(self.series[metric])
        if len(data) < 5:
            return []

        slope = self._linear_trend(data[-self.window_size:])
        last_value = data[-1]
        predictions = []

        for i in range(1, steps + 1):
            predicted = last_value + slope * i
            confidence = max(0.5, 1.0 - (i * 0.1))  # Confidence decreases with distance
            predictions.append({
                "step": i,
                "predicted_value": round(predicted, 4),
                "confidence": round(confidence, 4),
            })

        return predictions

    def _linear_trend(self, data: List[float]) -> float:
        """Compute slope of linear regression."""
        n = len(data)
        if n < 2:
            return 0.0
        x_mean = (n - 1) / 2
        y_mean = sum(data) / n
        numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(data))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        return numerator / denominator if denominator != 0 else 0.0


# ── Performance Monitor ─────────────────────────────────────────────────────

class PerformanceMonitor:
    """Track performance metrics: API latency, build times, resource usage."""

    def __init__(self, max_entries: int = 10000):
        self.latencies: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_entries))
        self.build_times: deque = deque(maxlen=1000)

    def record_latency(self, endpoint: str, duration_ms: float) -> None:
        """Record an API call latency."""
        self.latencies[endpoint].append({
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def record_build_time(self, duration_s: float, steps: int, passed: int) -> None:
        """Record a build pipeline execution."""
        self.build_times.append({
            "duration_s": duration_s,
            "steps": steps,
            "passed": passed,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_latency_stats(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """Get latency statistics (p50, p95, p99)."""
        result = {}
        endpoints = [endpoint] if endpoint else list(self.latencies.keys())

        for ep in endpoints:
            durations = [e["duration_ms"] for e in self.latencies[ep]]
            if not durations:
                continue
            durations.sort()
            n = len(durations)
            result[ep] = {
                "count": n,
                "p50": round(durations[int(n * 0.50)] if n > 0 else 0, 2),
                "p95": round(durations[int(n * 0.95)] if n > 0 else 0, 2),
                "p99": round(durations[int(n * 0.99)] if n > 0 else 0, 2),
                "mean": round(statistics.mean(durations), 2),
                "min": round(min(durations), 2),
                "max": round(max(durations), 2),
            }

        return result

    def get_build_stats(self) -> Dict[str, Any]:
        """Get build performance statistics."""
        if not self.build_times:
            return {"count": 0}

        durations = [b["duration_s"] for b in self.build_times]
        return {
            "count": len(durations),
            "last_build": self.build_times[-1],
            "avg_duration_s": round(statistics.mean(durations), 2),
            "min_duration_s": round(min(durations), 2),
            "max_duration_s": round(max(durations), 2),
            "trend": "stable" if len(durations) < 3 else (
                "degrading" if durations[-1] > statistics.mean(durations) * 1.2 else "healthy"
            ),
        }

    def get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage (best effort)."""
        try:
            import psutil
            return {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage("/").percent,
            }
        except ImportError:
            # Fallback: parse /proc on Linux
            try:
                with open("/proc/loadavg") as f:
                    load = f.read().split()
                return {
                    "load_1m": float(load[0]),
                    "load_5m": float(load[1]),
                    "load_15m": float(load[2]),
                }
            except Exception:
                return {"status": "unavailable"}


# ── Time Series Store ────────────────────────────────────────────────────────

class TimeSeriesStore:
    """Simple file-based time-series storage for historical analysis."""

    def __init__(self, storage_path: str = "monitoring_data"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def append(self, metric: str, value: float, metadata: Optional[Dict] = None) -> None:
        """Append a data point to the time series."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "value": value,
            "metadata": metadata or {},
        }
        file_path = self.storage_path / f"{metric}.jsonl"
        with open(file_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def query(self, metric: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Query time series data for the last N hours."""
        file_path = self.storage_path / f"{metric}.jsonl"
        if not file_path.exists():
            return []

        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        results = []
        with open(file_path) as f:
            for line in f:
                entry = json.loads(line.strip())
                if entry["timestamp"] >= cutoff:
                    results.append(entry)
        return results

    def get_correlation(self, metric1: str, metric2: str, hours: int = 24) -> Optional[float]:
        """Calculate Pearson correlation between two metrics."""
        data1 = self.query(metric1, hours)
        data2 = self.query(metric2, hours)
        if len(data1) < 3 or len(data2) < 3:
            return None

        vals1 = [d["value"] for d in data1[:min(len(data1), len(data2))]]
        vals2 = [d["value"] for d in data2[:min(len(data1), len(data2))]]
        n = min(len(vals1), len(vals2))
        vals1 = vals1[:n]
        vals2 = vals2[:n]

        mean1 = sum(vals1) / n
        mean2 = sum(vals2) / n
        numerator = sum((a - mean1) * (b - mean2) for a, b in zip(vals1, vals2))
        denom1 = math.sqrt(sum((a - mean1) ** 2 for a in vals1))
        denom2 = math.sqrt(sum((b - mean2) ** 2 for b in vals2))

        if denom1 == 0 or denom2 == 0:
            return 0.0
        return round(numerator / (denom1 * denom2), 4)

    def generate_report(self, metrics: List[str], hours: int = 24) -> Dict[str, Any]:
        """Generate an automated performance report."""
        report = {
            "generated": datetime.now(timezone.utc).isoformat(),
            "period_hours": hours,
            "metrics": {},
        }
        for metric in metrics:
            data = self.query(metric, hours)
            if not data:
                report["metrics"][metric] = {"status": "no_data"}
                continue
            values = [d["value"] for d in data]
            report["metrics"][metric] = {
                "count": len(values),
                "mean": round(statistics.mean(values), 4),
                "min": round(min(values), 4),
                "max": round(max(values), 4),
                "stdev": round(statistics.stdev(values), 4) if len(values) > 1 else 0,
                "latest": values[-1],
            }
        return report


# ── Integrated Monitor ───────────────────────────────────────────────────────

class AdvancedMonitor:
    """Integrated monitoring system combining SPC, alerts, performance, and storage."""

    def __init__(self, storage_path: str = "monitoring_data"):
        self.spc = SPCMonitor()
        self.alerts = AlertManager()
        self.performance = PerformanceMonitor()
        self.timeseries = TimeSeriesStore(storage_path)
        self.thresholds: Dict[str, Dict[str, float]] = {
            "api_latency_ms": {"warning": 300, "critical": 500},
            "build_duration_s": {"warning": 30, "critical": 60},
            "config_drift_count": {"warning": 1, "critical": 3},
            "test_failures": {"warning": 1, "critical": 5},
            "compliance_score": {"warning": 9.0, "critical": 8.0},
        }

    def observe(self, metric: str, value: float, source: str = "system") -> Dict[str, Any]:
        """Record an observation and check thresholds."""
        # SPC analysis
        analysis = self.spc.add_observation(metric, value)

        # Store in time series
        self.timeseries.append(metric, value, {"source": source})

        # Check thresholds
        if metric in self.thresholds:
            th = self.thresholds[metric]
            is_inverse = metric in ("compliance_score",)  # Lower is worse

            if is_inverse:
                if value < th.get("critical", float("-inf")):
                    self.alerts.fire(Alert(
                        level=AlertLevel.CRITICAL, source=source, metric=metric,
                        value=value, threshold=th["critical"],
                        message=f"{metric} dropped to {value} (critical: {th['critical']})"
                    ))
                elif value < th.get("warning", float("-inf")):
                    self.alerts.fire(Alert(
                        level=AlertLevel.WARNING, source=source, metric=metric,
                        value=value, threshold=th["warning"],
                        message=f"{metric} dropped to {value} (warning: {th['warning']})"
                    ))
            else:
                if value > th.get("critical", float("inf")):
                    self.alerts.fire(Alert(
                        level=AlertLevel.CRITICAL, source=source, metric=metric,
                        value=value, threshold=th["critical"],
                        message=f"{metric} exceeded {th['critical']} (current: {value})"
                    ))
                elif value > th.get("warning", float("inf")):
                    self.alerts.fire(Alert(
                        level=AlertLevel.WARNING, source=source, metric=metric,
                        value=value, threshold=th["warning"],
                        message=f"{metric} exceeded {th['warning']} (current: {value})"
                    ))

        # Anomaly alert
        if analysis.get("anomaly"):
            self.alerts.fire(Alert(
                level=AlertLevel.WARNING, source=source, metric=metric,
                value=value, threshold=self.spc.z_threshold,
                message=f"Anomaly detected: {metric}={value} (z={analysis.get('z_score', 0)})"
            ))

        # Predictive alert
        predictions = self.spc.predict(metric, steps=3)
        if predictions:
            for pred in predictions:
                predicted = pred["predicted_value"]
                if metric in self.thresholds:
                    th = self.thresholds[metric]
                    if predicted > th.get("critical", float("inf")):
                        self.alerts.fire(Alert(
                            level=AlertLevel.PREDICTIVE, source=source, metric=metric,
                            value=predicted, threshold=th["critical"],
                            message=f"PREDICTION: {metric} may reach {predicted:.2f} in {pred['step']} steps"
                        ))
                        break

        analysis["alerts"] = self.alerts.get_summary()
        return analysis

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get all data needed for the monitoring dashboard."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "alerts": {
                "active": self.alerts.get_active(),
                "summary": self.alerts.get_summary(),
            },
            "performance": {
                "api_latency": self.performance.get_latency_stats(),
                "build": self.performance.get_build_stats(),
                "resources": self.performance.get_resource_usage(),
            },
            "thresholds": self.thresholds,
        }

    def set_threshold(self, metric: str, warning: float, critical: float) -> None:
        """Update alert thresholds for a metric."""
        self.thresholds[metric] = {"warning": warning, "critical": critical}


# ── Convenience Functions ────────────────────────────────────────────────────

_monitor: Optional[AdvancedMonitor] = None


def get_monitor(storage_path: str = "monitoring_data") -> AdvancedMonitor:
    """Get or create the singleton monitoring instance."""
    global _monitor
    if _monitor is None:
        _monitor = AdvancedMonitor(storage_path)
    return _monitor


if __name__ == "__main__":
    # Demo
    monitor = AdvancedMonitor("/tmp/qplant_monitoring")

    # Simulate observations
    import random
    for i in range(50):
        lat = 50 + random.gauss(0, 20)
        result = monitor.observe("api_latency_ms", lat, source="demo")
        if i % 10 == 0:
            print(f"Step {i}: {result}")

    # Force a critical value
    result = monitor.observe("api_latency_ms", 600, source="demo")
    print(f"\nCritical: {result}")

    # Dashboard data
    dashboard = monitor.get_dashboard_data()
    print(f"\nAlerts: {dashboard['alerts']['summary']}")
    print(f"Performance: {json.dumps(dashboard['performance'], indent=2)}")
