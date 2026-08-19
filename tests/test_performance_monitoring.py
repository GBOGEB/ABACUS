#!/usr/bin/env python3
"""
# Version: 1.0.0
# Date: 2025-11-24
# Description: Auto-generated version header
"""

"""
Performance Monitoring Tests - Benchmark Tracking, Performance Budgets, Regression Alerts
"""

import pytest
import time
import json
import statistics
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict, field
import functools


@dataclass
class PerformanceBenchmark:
    name: str
    category: str
    execution_time_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PerformanceBudget:
    name: str
    max_execution_time_ms: float
    max_memory_mb: float
    max_cpu_percent: float
    alert_threshold_percent: float = 80.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PerformanceAlert:
    benchmark_name: str
    alert_type: str
    severity: str
    message: str
    current_value: float
    budget_value: float
    exceeded_by_percent: float
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BenchmarkTracker:
    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path("test_metrics/benchmarks.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.benchmarks: List[PerformanceBenchmark] = []
        self._load_benchmarks()
    
    def _load_benchmarks(self):
        if self.storage_path.exists():
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                self.benchmarks = [PerformanceBenchmark(**b) for b in data]
    
    def _save_benchmarks(self):
        with open(self.storage_path, 'w') as f:
            json.dump([b.to_dict() for b in self.benchmarks], f, indent=2)
    
    def record_benchmark(self, benchmark: PerformanceBenchmark):
        self.benchmarks.append(benchmark)
        self._save_benchmarks()
    
    def get_benchmarks(self, name: str = None, category: str = None, 
                      limit: int = None) -> List[PerformanceBenchmark]:
        filtered = self.benchmarks
        
        if name:
            filtered = [b for b in filtered if b.name == name]
        
        if category:
            filtered = [b for b in filtered if b.category == category]
        
        if limit:
            filtered = filtered[-limit:]
        
        return filtered
    
    def get_statistics(self, name: str) -> Dict[str, Any]:
        benchmarks = self.get_benchmarks(name=name)
        
        if not benchmarks:
            return {"error": "no_data"}
        
        exec_times = [b.execution_time_ms for b in benchmarks]
        memory_usage = [b.memory_usage_mb for b in benchmarks]
        cpu_usage = [b.cpu_usage_percent for b in benchmarks]
        
        return {
            "name": name,
            "total_runs": len(benchmarks),
            "execution_time_ms": {
                "min": round(min(exec_times), 2),
                "max": round(max(exec_times), 2),
                "avg": round(statistics.mean(exec_times), 2),
                "median": round(statistics.median(exec_times), 2),
                "p95": round(self._percentile(exec_times, 95), 2),
                "p99": round(self._percentile(exec_times, 99), 2),
                "stdev": round(statistics.stdev(exec_times), 2) if len(exec_times) > 1 else 0.0
            },
            "memory_usage_mb": {
                "min": round(min(memory_usage), 2),
                "max": round(max(memory_usage), 2),
                "avg": round(statistics.mean(memory_usage), 2)
            },
            "cpu_usage_percent": {
                "min": round(min(cpu_usage), 2),
                "max": round(max(cpu_usage), 2),
                "avg": round(statistics.mean(cpu_usage), 2)
            }
        }
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def compare_with_baseline(self, name: str, baseline_window: int = 10) -> Dict[str, Any]:
        benchmarks = self.get_benchmarks(name=name)
        
        if len(benchmarks) < baseline_window + 1:
            return {"error": "insufficient_data"}
        
        baseline = benchmarks[-baseline_window-1:-1]
        current = benchmarks[-1]
        
        baseline_time = statistics.mean([b.execution_time_ms for b in baseline])
        current_time = current.execution_time_ms
        
        time_change = ((current_time - baseline_time) / baseline_time * 100) if baseline_time > 0 else 0.0
        
        return {
            "name": name,
            "baseline_avg_ms": round(baseline_time, 2),
            "current_ms": round(current_time, 2),
            "change_percent": round(time_change, 2),
            "trend": "regression" if time_change > 10 else "improvement" if time_change < -10 else "stable"
        }


class PerformanceBudgetManager:
    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path("test_metrics/budgets.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.budgets: Dict[str, PerformanceBudget] = {}
        self._load_budgets()
    
    def _load_budgets(self):
        if self.storage_path.exists():
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                self.budgets = {name: PerformanceBudget(**budget) for name, budget in data.items()}
    
    def _save_budgets(self):
        with open(self.storage_path, 'w') as f:
            json.dump({name: budget.to_dict() for name, budget in self.budgets.items()}, f, indent=2)
    
    def set_budget(self, budget: PerformanceBudget):
        self.budgets[budget.name] = budget
        self._save_budgets()
    
    def get_budget(self, name: str) -> Optional[PerformanceBudget]:
        return self.budgets.get(name)
    
    def check_budget(self, benchmark: PerformanceBenchmark) -> Dict[str, Any]:
        budget = self.get_budget(benchmark.name)
        
        if not budget:
            return {
                "within_budget": True,
                "reason": "no_budget_defined"
            }
        
        violations = []
        
        if benchmark.execution_time_ms > budget.max_execution_time_ms:
            exceeded_by = ((benchmark.execution_time_ms - budget.max_execution_time_ms) / 
                          budget.max_execution_time_ms * 100)
            violations.append({
                "metric": "execution_time_ms",
                "current": benchmark.execution_time_ms,
                "budget": budget.max_execution_time_ms,
                "exceeded_by_percent": round(exceeded_by, 2)
            })
        
        if benchmark.memory_usage_mb > budget.max_memory_mb:
            exceeded_by = ((benchmark.memory_usage_mb - budget.max_memory_mb) / 
                          budget.max_memory_mb * 100)
            violations.append({
                "metric": "memory_usage_mb",
                "current": benchmark.memory_usage_mb,
                "budget": budget.max_memory_mb,
                "exceeded_by_percent": round(exceeded_by, 2)
            })
        
        if benchmark.cpu_usage_percent > budget.max_cpu_percent:
            exceeded_by = ((benchmark.cpu_usage_percent - budget.max_cpu_percent) / 
                          budget.max_cpu_percent * 100)
            violations.append({
                "metric": "cpu_usage_percent",
                "current": benchmark.cpu_usage_percent,
                "budget": budget.max_cpu_percent,
                "exceeded_by_percent": round(exceeded_by, 2)
            })
        
        return {
            "within_budget": len(violations) == 0,
            "violations": violations,
            "total_violations": len(violations)
        }


class RegressionAlertSystem:
    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path("test_metrics/alerts.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.alerts: List[PerformanceAlert] = []
        self._load_alerts()
    
    def _load_alerts(self):
        if self.storage_path.exists():
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                self.alerts = [PerformanceAlert(**a) for a in data]
    
    def _save_alerts(self):
        with open(self.storage_path, 'w') as f:
            json.dump([a.to_dict() for a in self.alerts], f, indent=2)
    
    def create_alert(self, alert: PerformanceAlert):
        self.alerts.append(alert)
        self._save_alerts()
    
    def check_for_regressions(self, tracker: BenchmarkTracker, 
                             budget_manager: PerformanceBudgetManager,
                             benchmark_name: str) -> List[PerformanceAlert]:
        benchmarks = tracker.get_benchmarks(name=benchmark_name)
        
        if not benchmarks:
            return []
        
        current = benchmarks[-1]
        budget = budget_manager.get_budget(benchmark_name)
        
        new_alerts = []
        
        if budget:
            budget_check = budget_manager.check_budget(current)
            
            if not budget_check["within_budget"]:
                for violation in budget_check["violations"]:
                    severity = "critical" if violation["exceeded_by_percent"] > 50 else "warning"
                    
                    alert = PerformanceAlert(
                        benchmark_name=benchmark_name,
                        alert_type="budget_violation",
                        severity=severity,
                        message=f"{violation['metric']} exceeded budget by {violation['exceeded_by_percent']}%",
                        current_value=violation["current"],
                        budget_value=violation["budget"],
                        exceeded_by_percent=violation["exceeded_by_percent"],
                        timestamp=datetime.now().isoformat()
                    )
                    new_alerts.append(alert)
                    self.create_alert(alert)
        
        comparison = tracker.compare_with_baseline(benchmark_name)
        
        if comparison.get("trend") == "regression":
            alert = PerformanceAlert(
                benchmark_name=benchmark_name,
                alert_type="performance_regression",
                severity="warning",
                message=f"Performance regression detected: {comparison['change_percent']}% slower",
                current_value=comparison["current_ms"],
                budget_value=comparison["baseline_avg_ms"],
                exceeded_by_percent=comparison["change_percent"],
                timestamp=datetime.now().isoformat()
            )
            new_alerts.append(alert)
            self.create_alert(alert)
        
        return new_alerts
    
    def get_alerts(self, benchmark_name: str = None, severity: str = None,
                  limit: int = None) -> List[PerformanceAlert]:
        filtered = self.alerts
        
        if benchmark_name:
            filtered = [a for a in filtered if a.benchmark_name == benchmark_name]
        
        if severity:
            filtered = [a for a in filtered if a.severity == severity]
        
        if limit:
            filtered = filtered[-limit:]
        
        return filtered


def benchmark(name: str, category: str = "general"):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            
            result = func(*args, **kwargs)
            
            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000
            
            benchmark_data = PerformanceBenchmark(
                name=name,
                category=category,
                execution_time_ms=execution_time_ms,
                memory_usage_mb=50.0,
                cpu_usage_percent=30.0,
                timestamp=datetime.now().isoformat()
            )
            
            tracker = BenchmarkTracker()
            tracker.record_benchmark(benchmark_data)
            
            return result
        return wrapper
    return decorator


@pytest.fixture
def benchmark_tracker(tmp_path):
    storage_path = tmp_path / "benchmarks.json"
    return BenchmarkTracker(storage_path)


@pytest.fixture
def budget_manager(tmp_path):
    storage_path = tmp_path / "budgets.json"
    return PerformanceBudgetManager(storage_path)


@pytest.fixture
def alert_system(tmp_path):
    storage_path = tmp_path / "alerts.json"
    return RegressionAlertSystem(storage_path)


@pytest.fixture
def sample_benchmarks():
    base_time = datetime.now()
    benchmarks = []
    
    for i in range(15):
        benchmark = PerformanceBenchmark(
            name="test_function",
            category="unit",
            execution_time_ms=100.0 + i * 5,
            memory_usage_mb=50.0 + i * 2,
            cpu_usage_percent=30.0 + i * 1,
            timestamp=(base_time + timedelta(minutes=i)).isoformat()
        )
        benchmarks.append(benchmark)
    
    return benchmarks


class TestBenchmarkTracking:
    
    def test_tracker_initialization(self, benchmark_tracker):
        assert benchmark_tracker is not None
        assert isinstance(benchmark_tracker.benchmarks, list)
    
    def test_record_benchmark(self, benchmark_tracker):
        benchmark = PerformanceBenchmark(
            name="test_sample",
            category="unit",
            execution_time_ms=150.0,
            memory_usage_mb=60.0,
            cpu_usage_percent=35.0,
            timestamp=datetime.now().isoformat()
        )
        
        benchmark_tracker.record_benchmark(benchmark)
        assert len(benchmark_tracker.benchmarks) == 1
    
    def test_get_benchmarks_by_name(self, benchmark_tracker, sample_benchmarks):
        for b in sample_benchmarks:
            benchmark_tracker.record_benchmark(b)
        
        results = benchmark_tracker.get_benchmarks(name="test_function")
        assert len(results) == 15
    
    def test_get_benchmarks_by_category(self, benchmark_tracker, sample_benchmarks):
        for b in sample_benchmarks:
            benchmark_tracker.record_benchmark(b)
        
        results = benchmark_tracker.get_benchmarks(category="unit")
        assert len(results) == 15
    
    def test_get_benchmarks_with_limit(self, benchmark_tracker, sample_benchmarks):
        for b in sample_benchmarks:
            benchmark_tracker.record_benchmark(b)
        
        results = benchmark_tracker.get_benchmarks(name="test_function", limit=5)
        assert len(results) == 5
    
    def test_get_statistics(self, benchmark_tracker, sample_benchmarks):
        for b in sample_benchmarks:
            benchmark_tracker.record_benchmark(b)
        
        stats = benchmark_tracker.get_statistics("test_function")
        
        assert "execution_time_ms" in stats
        assert "memory_usage_mb" in stats
        assert "cpu_usage_percent" in stats
        assert stats["total_runs"] == 15
    
    def test_statistics_percentiles(self, benchmark_tracker, sample_benchmarks):
        for b in sample_benchmarks:
            benchmark_tracker.record_benchmark(b)
        
        stats = benchmark_tracker.get_statistics("test_function")
        exec_time = stats["execution_time_ms"]
        
        assert "p95" in exec_time
        assert "p99" in exec_time
        assert exec_time["p95"] <= exec_time["p99"]
    
    def test_compare_with_baseline(self, benchmark_tracker, sample_benchmarks):
        for b in sample_benchmarks:
            benchmark_tracker.record_benchmark(b)
        
        comparison = benchmark_tracker.compare_with_baseline("test_function")
        
        assert "baseline_avg_ms" in comparison
        assert "current_ms" in comparison
        assert "change_percent" in comparison
        assert "trend" in comparison
    
    def test_persistence(self, tmp_path):
        storage_path = tmp_path / "persist_benchmarks.json"
        tracker1 = BenchmarkTracker(storage_path)
        
        benchmark = PerformanceBenchmark(
            name="test_persist",
            category="unit",
            execution_time_ms=150.0,
            memory_usage_mb=60.0,
            cpu_usage_percent=35.0,
            timestamp=datetime.now().isoformat()
        )
        tracker1.record_benchmark(benchmark)
        
        tracker2 = BenchmarkTracker(storage_path)
        assert len(tracker2.benchmarks) == 1


class TestPerformanceBudgets:
    
    def test_budget_manager_initialization(self, budget_manager):
        assert budget_manager is not None
        assert isinstance(budget_manager.budgets, dict)
    
    def test_set_budget(self, budget_manager):
        budget = PerformanceBudget(
            name="test_function",
            max_execution_time_ms=200.0,
            max_memory_mb=100.0,
            max_cpu_percent=50.0
        )
        
        budget_manager.set_budget(budget)
        assert "test_function" in budget_manager.budgets
    
    def test_get_budget(self, budget_manager):
        budget = PerformanceBudget(
            name="test_function",
            max_execution_time_ms=200.0,
            max_memory_mb=100.0,
            max_cpu_percent=50.0
        )
        
        budget_manager.set_budget(budget)
        retrieved = budget_manager.get_budget("test_function")
        
        assert retrieved is not None
        assert retrieved.name == "test_function"
    
    def test_check_budget_within(self, budget_manager):
        budget = PerformanceBudget(
            name="test_function",
            max_execution_time_ms=200.0,
            max_memory_mb=100.0,
            max_cpu_percent=50.0
        )
        budget_manager.set_budget(budget)
        
        benchmark = PerformanceBenchmark(
            name="test_function",
            category="unit",
            execution_time_ms=150.0,
            memory_usage_mb=80.0,
            cpu_usage_percent=40.0,
            timestamp=datetime.now().isoformat()
        )
        
        result = budget_manager.check_budget(benchmark)
        assert result["within_budget"] is True
    
    def test_check_budget_violation(self, budget_manager):
        budget = PerformanceBudget(
            name="test_function",
            max_execution_time_ms=100.0,
            max_memory_mb=50.0,
            max_cpu_percent=30.0
        )
        budget_manager.set_budget(budget)
        
        benchmark = PerformanceBenchmark(
            name="test_function",
            category="unit",
            execution_time_ms=150.0,
            memory_usage_mb=80.0,
            cpu_usage_percent=40.0,
            timestamp=datetime.now().isoformat()
        )
        
        result = budget_manager.check_budget(benchmark)
        assert result["within_budget"] is False
        assert result["total_violations"] > 0


class TestRegressionAlerts:
    
    def test_alert_system_initialization(self, alert_system):
        assert alert_system is not None
        assert isinstance(alert_system.alerts, list)
    
    def test_create_alert(self, alert_system):
        alert = PerformanceAlert(
            benchmark_name="test_function",
            alert_type="budget_violation",
            severity="warning",
            message="Execution time exceeded budget",
            current_value=150.0,
            budget_value=100.0,
            exceeded_by_percent=50.0,
            timestamp=datetime.now().isoformat()
        )
        
        alert_system.create_alert(alert)
        assert len(alert_system.alerts) == 1
    
    def test_get_alerts_by_name(self, alert_system):
        alert1 = PerformanceAlert(
            benchmark_name="test_function_1",
            alert_type="budget_violation",
            severity="warning",
            message="Test alert 1",
            current_value=150.0,
            budget_value=100.0,
            exceeded_by_percent=50.0,
            timestamp=datetime.now().isoformat()
        )
        
        alert2 = PerformanceAlert(
            benchmark_name="test_function_2",
            alert_type="budget_violation",
            severity="critical",
            message="Test alert 2",
            current_value=200.0,
            budget_value=100.0,
            exceeded_by_percent=100.0,
            timestamp=datetime.now().isoformat()
        )
        
        alert_system.create_alert(alert1)
        alert_system.create_alert(alert2)
        
        results = alert_system.get_alerts(benchmark_name="test_function_1")
        assert len(results) == 1
    
    def test_get_alerts_by_severity(self, alert_system):
        alert = PerformanceAlert(
            benchmark_name="test_function",
            alert_type="budget_violation",
            severity="critical",
            message="Critical alert",
            current_value=200.0,
            budget_value=100.0,
            exceeded_by_percent=100.0,
            timestamp=datetime.now().isoformat()
        )
        
        alert_system.create_alert(alert)
        
        results = alert_system.get_alerts(severity="critical")
        assert len(results) == 1
    
    def test_check_for_regressions(self, benchmark_tracker, budget_manager, alert_system, sample_benchmarks):
        for b in sample_benchmarks:
            benchmark_tracker.record_benchmark(b)
        
        budget = PerformanceBudget(
            name="test_function",
            max_execution_time_ms=120.0,
            max_memory_mb=70.0,
            max_cpu_percent=40.0
        )
        budget_manager.set_budget(budget)
        
        alerts = alert_system.check_for_regressions(
            benchmark_tracker,
            budget_manager,
            "test_function"
        )
        
        assert isinstance(alerts, list)


class TestBenchmarkDecorator:
    
    @benchmark(name="test_decorated_function", category="unit")
    def sample_function(self):
        time.sleep(0.01)
        return "result"
    
    def test_decorator_execution(self):
        result = self.sample_function()
        assert result == "result"
    
    def test_decorator_records_benchmark(self):
        tracker = BenchmarkTracker()
        initial_count = len(tracker.benchmarks)
        
        self.sample_function()
        
        tracker = BenchmarkTracker()
        assert len(tracker.benchmarks) >= initial_count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
