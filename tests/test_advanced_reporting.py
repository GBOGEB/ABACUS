#!/usr/bin/env python3
"""
# Version: 1.0.0
# Date: 2025-11-24
# Description: Auto-generated version header
"""

"""
Advanced Reporting Tests - Trend Analysis, Historical Metrics, Performance Regression Detection
"""

import pytest
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
import statistics


@dataclass
class PerformanceMetric:
    timestamp: str
    test_name: str
    execution_time_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    pass_rate: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TrendAnalyzer:
    def __init__(self, history_file: Path = None):
        self.history_file = history_file or Path("test_metrics/performance_history.json")
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.metrics: List[PerformanceMetric] = []
        self._load_history()
    
    def _load_history(self):
        if self.history_file.exists():
            with open(self.history_file, 'r') as f:
                data = json.load(f)
                self.metrics = [PerformanceMetric(**m) for m in data]
    
    def _save_history(self):
        with open(self.history_file, 'w') as f:
            json.dump([m.to_dict() for m in self.metrics], f, indent=2)
    
    def record_metric(self, metric: PerformanceMetric):
        self.metrics.append(metric)
        self._save_history()
    
    def get_trend(self, test_name: str, metric_name: str, window: int = 10) -> Dict[str, Any]:
        test_metrics = [m for m in self.metrics if m.test_name == test_name]
        
        if len(test_metrics) < 2:
            return {"trend": "insufficient_data", "direction": "stable", "change_percent": 0.0}
        
        recent = test_metrics[-window:]
        values = [getattr(m, metric_name) for m in recent]
        
        if len(values) < 2:
            return {"trend": "insufficient_data", "direction": "stable", "change_percent": 0.0}
        
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        avg_first = statistics.mean(first_half)
        avg_second = statistics.mean(second_half)
        
        change_percent = ((avg_second - avg_first) / avg_first * 100) if avg_first > 0 else 0.0
        
        if abs(change_percent) < 5:
            direction = "stable"
        elif change_percent > 0:
            direction = "increasing"
        else:
            direction = "decreasing"
        
        return {
            "trend": "analyzed",
            "direction": direction,
            "change_percent": round(change_percent, 2),
            "avg_first_half": round(avg_first, 2),
            "avg_second_half": round(avg_second, 2),
            "sample_size": len(values)
        }
    
    def detect_regression(self, test_name: str, threshold_percent: float = 20.0) -> Dict[str, Any]:
        test_metrics = [m for m in self.metrics if m.test_name == test_name]
        
        if len(test_metrics) < 2:
            return {"regression_detected": False, "reason": "insufficient_data"}
        
        baseline = test_metrics[-10:-1] if len(test_metrics) > 10 else test_metrics[:-1]
        current = test_metrics[-1]
        
        baseline_time = statistics.mean([m.execution_time_ms for m in baseline])
        current_time = current.execution_time_ms
        
        time_increase = ((current_time - baseline_time) / baseline_time * 100) if baseline_time > 0 else 0.0
        
        regression_detected = time_increase > threshold_percent
        
        return {
            "regression_detected": regression_detected,
            "baseline_avg_ms": round(baseline_time, 2),
            "current_ms": round(current_time, 2),
            "increase_percent": round(time_increase, 2),
            "threshold_percent": threshold_percent,
            "severity": "critical" if time_increase > 50 else "warning" if time_increase > 20 else "normal"
        }
    
    def get_historical_summary(self, test_name: str = None) -> Dict[str, Any]:
        if test_name:
            metrics = [m for m in self.metrics if m.test_name == test_name]
        else:
            metrics = self.metrics
        
        if not metrics:
            return {"error": "no_data"}
        
        execution_times = [m.execution_time_ms for m in metrics]
        memory_usage = [m.memory_usage_mb for m in metrics]
        pass_rates = [m.pass_rate for m in metrics]
        
        return {
            "total_runs": len(metrics),
            "date_range": {
                "first": metrics[0].timestamp,
                "last": metrics[-1].timestamp
            },
            "execution_time_ms": {
                "min": round(min(execution_times), 2),
                "max": round(max(execution_times), 2),
                "avg": round(statistics.mean(execution_times), 2),
                "median": round(statistics.median(execution_times), 2),
                "stdev": round(statistics.stdev(execution_times), 2) if len(execution_times) > 1 else 0.0
            },
            "memory_usage_mb": {
                "min": round(min(memory_usage), 2),
                "max": round(max(memory_usage), 2),
                "avg": round(statistics.mean(memory_usage), 2)
            },
            "pass_rate": {
                "min": round(min(pass_rates), 2),
                "max": round(max(pass_rates), 2),
                "avg": round(statistics.mean(pass_rates), 2)
            }
        }


@pytest.fixture
def trend_analyzer(tmp_path):
    history_file = tmp_path / "test_history.json"
    return TrendAnalyzer(history_file)


@pytest.fixture
def sample_metrics():
    base_time = datetime.now()
    metrics = []
    
    for i in range(20):
        metric = PerformanceMetric(
            timestamp=(base_time + timedelta(hours=i)).isoformat(),
            test_name="test_example",
            execution_time_ms=100.0 + i * 2,
            memory_usage_mb=50.0 + i * 0.5,
            cpu_usage_percent=30.0 + i * 0.3,
            pass_rate=95.0 + (i % 5)
        )
        metrics.append(metric)
    
    return metrics


class TestTrendAnalysis:
    
    def test_trend_analyzer_initialization(self, trend_analyzer):
        assert trend_analyzer is not None
        assert isinstance(trend_analyzer.metrics, list)
    
    def test_record_metric(self, trend_analyzer):
        metric = PerformanceMetric(
            timestamp=datetime.now().isoformat(),
            test_name="test_sample",
            execution_time_ms=150.0,
            memory_usage_mb=60.0,
            cpu_usage_percent=35.0,
            pass_rate=98.5
        )
        
        trend_analyzer.record_metric(metric)
        assert len(trend_analyzer.metrics) == 1
        assert trend_analyzer.metrics[0].test_name == "test_sample"
    
    def test_get_trend_insufficient_data(self, trend_analyzer):
        metric = PerformanceMetric(
            timestamp=datetime.now().isoformat(),
            test_name="test_single",
            execution_time_ms=100.0,
            memory_usage_mb=50.0,
            cpu_usage_percent=30.0,
            pass_rate=95.0
        )
        trend_analyzer.record_metric(metric)
        
        trend = trend_analyzer.get_trend("test_single", "execution_time_ms")
        assert trend["trend"] == "insufficient_data"
    
    def test_get_trend_increasing(self, trend_analyzer, sample_metrics):
        for metric in sample_metrics:
            trend_analyzer.record_metric(metric)
        
        trend = trend_analyzer.get_trend("test_example", "execution_time_ms")
        assert trend["trend"] == "analyzed"
        assert trend["direction"] == "increasing"
        assert trend["change_percent"] > 0
    
    def test_get_trend_stable(self, trend_analyzer):
        base_time = datetime.now()
        for i in range(10):
            metric = PerformanceMetric(
                timestamp=(base_time + timedelta(hours=i)).isoformat(),
                test_name="test_stable",
                execution_time_ms=100.0 + (i % 2),
                memory_usage_mb=50.0,
                cpu_usage_percent=30.0,
                pass_rate=95.0
            )
            trend_analyzer.record_metric(metric)
        
        trend = trend_analyzer.get_trend("test_stable", "execution_time_ms")
        assert trend["trend"] == "analyzed"
        assert trend["direction"] == "stable"
    
    def test_detect_regression_no_regression(self, trend_analyzer):
        base_time = datetime.now()
        for i in range(10):
            metric = PerformanceMetric(
                timestamp=(base_time + timedelta(hours=i)).isoformat(),
                test_name="test_normal",
                execution_time_ms=100.0 + i * 0.5,
                memory_usage_mb=50.0,
                cpu_usage_percent=30.0,
                pass_rate=95.0
            )
            trend_analyzer.record_metric(metric)
        
        regression = trend_analyzer.detect_regression("test_normal")
        assert regression["regression_detected"] is False
    
    def test_detect_regression_with_regression(self, trend_analyzer):
        base_time = datetime.now()
        for i in range(10):
            metric = PerformanceMetric(
                timestamp=(base_time + timedelta(hours=i)).isoformat(),
                test_name="test_regressed",
                execution_time_ms=100.0 if i < 9 else 200.0,
                memory_usage_mb=50.0,
                cpu_usage_percent=30.0,
                pass_rate=95.0
            )
            trend_analyzer.record_metric(metric)
        
        regression = trend_analyzer.detect_regression("test_regressed", threshold_percent=20.0)
        assert regression["regression_detected"] is True
        assert regression["severity"] in ["warning", "critical"]
    
    def test_historical_summary(self, trend_analyzer, sample_metrics):
        for metric in sample_metrics:
            trend_analyzer.record_metric(metric)
        
        summary = trend_analyzer.get_historical_summary("test_example")
        assert summary["total_runs"] == 20
        assert "execution_time_ms" in summary
        assert "memory_usage_mb" in summary
        assert "pass_rate" in summary
        assert summary["execution_time_ms"]["min"] < summary["execution_time_ms"]["max"]
    
    def test_historical_summary_all_tests(self, trend_analyzer, sample_metrics):
        for metric in sample_metrics:
            trend_analyzer.record_metric(metric)
        
        metric2 = PerformanceMetric(
            timestamp=datetime.now().isoformat(),
            test_name="test_other",
            execution_time_ms=200.0,
            memory_usage_mb=80.0,
            cpu_usage_percent=40.0,
            pass_rate=90.0
        )
        trend_analyzer.record_metric(metric2)
        
        summary = trend_analyzer.get_historical_summary()
        assert summary["total_runs"] == 21
    
    def test_persistence(self, tmp_path):
        history_file = tmp_path / "persist_test.json"
        analyzer1 = TrendAnalyzer(history_file)
        
        metric = PerformanceMetric(
            timestamp=datetime.now().isoformat(),
            test_name="test_persist",
            execution_time_ms=150.0,
            memory_usage_mb=60.0,
            cpu_usage_percent=35.0,
            pass_rate=98.5
        )
        analyzer1.record_metric(metric)
        
        analyzer2 = TrendAnalyzer(history_file)
        assert len(analyzer2.metrics) == 1
        assert analyzer2.metrics[0].test_name == "test_persist"


class TestPerformanceRegression:
    
    def test_regression_threshold_critical(self, trend_analyzer):
        base_time = datetime.now()
        for i in range(10):
            metric = PerformanceMetric(
                timestamp=(base_time + timedelta(hours=i)).isoformat(),
                test_name="test_critical",
                execution_time_ms=100.0 if i < 9 else 300.0,
                memory_usage_mb=50.0,
                cpu_usage_percent=30.0,
                pass_rate=95.0
            )
            trend_analyzer.record_metric(metric)
        
        regression = trend_analyzer.detect_regression("test_critical")
        assert regression["regression_detected"] is True
        assert regression["severity"] == "critical"
    
    def test_regression_threshold_warning(self, trend_analyzer):
        base_time = datetime.now()
        for i in range(10):
            metric = PerformanceMetric(
                timestamp=(base_time + timedelta(hours=i)).isoformat(),
                test_name="test_warning",
                execution_time_ms=100.0 if i < 9 else 130.0,
                memory_usage_mb=50.0,
                cpu_usage_percent=30.0,
                pass_rate=95.0
            )
            trend_analyzer.record_metric(metric)
        
        regression = trend_analyzer.detect_regression("test_warning")
        assert regression["regression_detected"] is True
        assert regression["severity"] == "warning"
    
    def test_custom_threshold(self, trend_analyzer):
        base_time = datetime.now()
        for i in range(10):
            metric = PerformanceMetric(
                timestamp=(base_time + timedelta(hours=i)).isoformat(),
                test_name="test_custom",
                execution_time_ms=100.0 if i < 9 else 115.0,
                memory_usage_mb=50.0,
                cpu_usage_percent=30.0,
                pass_rate=95.0
            )
            trend_analyzer.record_metric(metric)
        
        regression = trend_analyzer.detect_regression("test_custom", threshold_percent=10.0)
        assert regression["regression_detected"] is True


class TestHistoricalMetrics:
    
    def test_date_range_tracking(self, trend_analyzer, sample_metrics):
        for metric in sample_metrics:
            trend_analyzer.record_metric(metric)
        
        summary = trend_analyzer.get_historical_summary("test_example")
        assert "date_range" in summary
        assert summary["date_range"]["first"] != summary["date_range"]["last"]
    
    def test_statistical_metrics(self, trend_analyzer, sample_metrics):
        for metric in sample_metrics:
            trend_analyzer.record_metric(metric)
        
        summary = trend_analyzer.get_historical_summary("test_example")
        exec_time = summary["execution_time_ms"]
        
        assert "min" in exec_time
        assert "max" in exec_time
        assert "avg" in exec_time
        assert "median" in exec_time
        assert "stdev" in exec_time
        assert exec_time["min"] <= exec_time["median"] <= exec_time["max"]
    
    def test_empty_history(self, trend_analyzer):
        summary = trend_analyzer.get_historical_summary("nonexistent_test")
        assert "error" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
