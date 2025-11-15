#!/usr/bin/env python3
"""
DMAIC V3 - Stability Monitor
Version: 3.2.0
Created: 2025-11-11T22:45:00Z
Updated: 2025-11-11T22:45:00Z

Real-time stability monitoring with recursive hooks.
Tracks file changes, test execution, metric variance, and generates alerts.
"""

import json
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, asdict, field
from collections import defaultdict, deque


VERSION = "3.2.0"


@dataclass
class FileSnapshot:
    path: str
    hash: str
    size: int
    modified: float
    timestamp: str


@dataclass
class TestResult:
    test_id: str
    status: str
    duration: float
    timestamp: str
    iteration: int


@dataclass
class MetricSnapshot:
    metric_name: str
    value: float
    timestamp: str
    iteration: int


@dataclass
class StabilityAlert:
    alert_type: str
    severity: str
    message: str
    timestamp: str
    details: Dict[str, Any]


@dataclass
class StabilityReport:
    version: str
    timestamp: str
    iteration: int
    monitoring_duration: float
    file_stability: float
    test_stability: float
    metric_stability: float
    overall_stability: float
    changes_detected: int
    alerts: List[StabilityAlert]
    recommendations: List[str]


class StabilityMonitor:
    def __init__(self, workspace_path: Optional[Path] = None, window_size: int = 10):
        self.version = VERSION
        self.workspace_path = workspace_path or Path.cwd()
        self.window_size = window_size
        
        self.file_snapshots: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self.test_results: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self.metric_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        
        self.alerts: List[StabilityAlert] = []
        self.start_time = time.time()
        self.iteration = 0
        
        self.change_hooks: List[Callable] = []
        self.alert_hooks: List[Callable] = []
        
        self.watch_patterns = [
            "DMAIC_V3/**/*.py",
            "config/**/*.yaml",
            "scripts/**/*.py"
        ]
    
    def register_change_hook(self, hook: Callable) -> None:
        self.change_hooks.append(hook)
    
    def register_alert_hook(self, hook: Callable) -> None:
        self.alert_hooks.append(hook)
    
    def _trigger_hooks(self, hook_list: List[Callable], *args, **kwargs) -> None:
        for hook in hook_list:
            try:
                hook(*args, **kwargs)
            except Exception as e:
                print(f"[WARN]️  Hook execution failed: {e}")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        if not file_path.exists():
            return ""
        
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return ""
    
    def snapshot_file(self, file_path: Path) -> FileSnapshot:
        timestamp = datetime.now().isoformat()
        
        if file_path.exists():
            hash_value = self._calculate_file_hash(file_path)
            size = file_path.stat().st_size
            modified = file_path.stat().st_mtime
        else:
            hash_value = ""
            size = 0
            modified = 0
        
        return FileSnapshot(
            path=str(file_path),
            hash=hash_value,
            size=size,
            modified=modified,
            timestamp=timestamp
        )
    
    def track_file(self, file_path: Path) -> bool:
        snapshot = self.snapshot_file(file_path)
        path_str = str(file_path)
        
        previous_snapshots = self.file_snapshots[path_str]
        changed = False
        
        if previous_snapshots:
            last_snapshot = previous_snapshots[-1]
            if last_snapshot.hash != snapshot.hash:
                changed = True
                self._create_alert(
                    alert_type="file_change",
                    severity="INFO",
                    message=f"File changed: {file_path.name}",
                    details={"path": path_str, "old_hash": last_snapshot.hash[:8], "new_hash": snapshot.hash[:8]}
                )
                self._trigger_hooks(self.change_hooks, "file", snapshot)
        
        self.file_snapshots[path_str].append(snapshot)
        return changed
    
    def track_files(self, file_paths: List[Path]) -> int:
        changes = sum(1 for path in file_paths if self.track_file(path))
        return changes
    
    def scan_workspace(self) -> int:
        files_to_track = []
        
        for pattern in self.watch_patterns:
            files_to_track.extend(self.workspace_path.glob(pattern))
        
        return self.track_files(files_to_track)
    
    def record_test_result(self, test_id: str, status: str, duration: float) -> None:
        result = TestResult(
            test_id=test_id,
            status=status,
            duration=duration,
            timestamp=datetime.now().isoformat(),
            iteration=self.iteration
        )
        
        previous_results = self.test_results[test_id]
        
        if previous_results:
            last_result = previous_results[-1]
            if last_result.status == "PASSED" and status == "FAILED":
                self._create_alert(
                    alert_type="test_regression",
                    severity="HIGH",
                    message=f"Test regression detected: {test_id}",
                    details={"test_id": test_id, "previous": "PASSED", "current": "FAILED"}
                )
        
        self.test_results[test_id].append(result)
        self._trigger_hooks(self.change_hooks, "test", result)
    
    def record_metric(self, metric_name: str, value: float) -> None:
        snapshot = MetricSnapshot(
            metric_name=metric_name,
            value=value,
            timestamp=datetime.now().isoformat(),
            iteration=self.iteration
        )
        
        previous_metrics = self.metric_history[metric_name]
        
        if len(previous_metrics) >= 3:
            recent_values = [m.value for m in list(previous_metrics)[-3:]]
            avg_value = sum(recent_values) / len(recent_values)
            
            variance = abs(value - avg_value) / avg_value if avg_value != 0 else 0
            
            if variance > 0.2:
                self._create_alert(
                    alert_type="metric_variance",
                    severity="MEDIUM",
                    message=f"High variance in {metric_name}: {variance*100:.1f}%",
                    details={"metric": metric_name, "current": value, "average": avg_value, "variance": variance}
                )
        
        self.metric_history[metric_name].append(snapshot)
        self._trigger_hooks(self.change_hooks, "metric", snapshot)
    
    def _create_alert(self, alert_type: str, severity: str, message: str, details: Dict[str, Any]) -> None:
        alert = StabilityAlert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            timestamp=datetime.now().isoformat(),
            details=details
        )
        
        self.alerts.append(alert)
        self._trigger_hooks(self.alert_hooks, alert)
    
    def calculate_file_stability(self) -> float:
        if not self.file_snapshots:
            return 100.0
        
        stable_count = 0
        total_count = 0
        
        for path, snapshots in self.file_snapshots.items():
            if len(snapshots) >= 2:
                total_count += 1
                hashes = [s.hash for s in snapshots]
                if len(set(hashes)) == 1:
                    stable_count += 1
        
        return (stable_count / total_count * 100) if total_count > 0 else 100.0
    
    def calculate_test_stability(self) -> float:
        if not self.test_results:
            return 100.0
        
        stable_count = 0
        total_count = 0
        
        for test_id, results in self.test_results.items():
            if len(results) >= 2:
                total_count += 1
                statuses = [r.status for r in results]
                if all(s == "PASSED" for s in statuses):
                    stable_count += 1
        
        return (stable_count / total_count * 100) if total_count > 0 else 100.0
    
    def calculate_metric_stability(self) -> float:
        if not self.metric_history:
            return 100.0
        
        stable_count = 0
        total_count = 0
        
        for metric_name, snapshots in self.metric_history.items():
            if len(snapshots) >= 3:
                total_count += 1
                values = [s.value for s in snapshots]
                avg_value = sum(values) / len(values)
                
                if avg_value != 0:
                    variances = [abs(v - avg_value) / avg_value for v in values]
                    max_variance = max(variances)
                    
                    if max_variance < 0.1:
                        stable_count += 1
        
        return (stable_count / total_count * 100) if total_count > 0 else 100.0
    
    def calculate_overall_stability(self) -> float:
        file_stab = self.calculate_file_stability()
        test_stab = self.calculate_test_stability()
        metric_stab = self.calculate_metric_stability()
        
        return (file_stab * 0.4) + (test_stab * 0.4) + (metric_stab * 0.2)
    
    def generate_recommendations(self) -> List[str]:
        recommendations = []
        
        file_stab = self.calculate_file_stability()
        test_stab = self.calculate_test_stability()
        metric_stab = self.calculate_metric_stability()
        
        if file_stab < 80:
            recommendations.append(f"File stability low ({file_stab:.1f}%) - reduce code churn")
        
        if test_stab < 80:
            recommendations.append(f"Test stability low ({test_stab:.1f}%) - fix flaky tests")
        
        if metric_stab < 80:
            recommendations.append(f"Metric stability low ({metric_stab:.1f}%) - stabilize performance")
        
        high_alerts = [a for a in self.alerts if a.severity == "HIGH"]
        if high_alerts:
            recommendations.append(f"Address {len(high_alerts)} high-severity alerts")
        
        if not recommendations:
            recommendations.append("System stable - continue current practices")
        
        return recommendations
    
    def generate_report(self) -> StabilityReport:
        duration = time.time() - self.start_time
        changes = sum(len(snapshots) for snapshots in self.file_snapshots.values())
        
        return StabilityReport(
            version=self.version,
            timestamp=datetime.now().isoformat(),
            iteration=self.iteration,
            monitoring_duration=duration,
            file_stability=self.calculate_file_stability(),
            test_stability=self.calculate_test_stability(),
            metric_stability=self.calculate_metric_stability(),
            overall_stability=self.calculate_overall_stability(),
            changes_detected=changes,
            alerts=self.alerts,
            recommendations=self.generate_recommendations()
        )
    
    def save_report(self, output_path: Optional[Path] = None) -> Path:
        report = self.generate_report()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if output_path is None:
            output_path = self.workspace_path / f"stability_report_{timestamp}.json"
        
        report_dict = {
            'metadata': {
                'version': report.version,
                'timestamp': report.timestamp,
                'iteration': report.iteration,
                'generator': 'StabilityMonitor'
            },
            'stability': {
                'overall': report.overall_stability,
                'file': report.file_stability,
                'test': report.test_stability,
                'metric': report.metric_stability,
                'monitoring_duration': report.monitoring_duration,
                'changes_detected': report.changes_detected
            },
            'alerts': [asdict(alert) for alert in report.alerts],
            'recommendations': report.recommendations
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        
        print(f"[OK] Stability report saved: {output_path}")
        return output_path
    
    def print_summary(self) -> None:
        report = self.generate_report()
        
        print("=" * 78)
        print("DMAIC V3 - STABILITY MONITOR REPORT")
        print("=" * 78)
        print(f"Version: {report.version}")
        print(f"Timestamp: {report.timestamp}")
        print(f"Iteration: {report.iteration}")
        print(f"Monitoring Duration: {report.monitoring_duration:.1f}s")
        print()
        
        print("STABILITY METRICS")
        print("-" * 78)
        print(f"Overall Stability:  {report.overall_stability:6.1f}%")
        print(f"File Stability:     {report.file_stability:6.1f}%")
        print(f"Test Stability:     {report.test_stability:6.1f}%")
        print(f"Metric Stability:   {report.metric_stability:6.1f}%")
        print(f"Changes Detected:   {report.changes_detected}")
        print()
        
        if report.alerts:
            print("ALERTS")
            print("-" * 78)
            for alert in report.alerts[-10:]:
                icon = "🔴" if alert.severity == "HIGH" else "🟡" if alert.severity == "MEDIUM" else "🔵"
                print(f"{icon} [{alert.severity}] {alert.message}")
            if len(report.alerts) > 10:
                print(f"... and {len(report.alerts) - 10} more alerts")
            print()
        
        print("RECOMMENDATIONS")
        print("-" * 78)
        for i, rec in enumerate(report.recommendations, 1):
            print(f"{i}. {rec}")
        print("=" * 78)
    
    def increment_iteration(self) -> None:
        self.iteration += 1


def main():
    import sys
    
    monitor = StabilityMonitor()
    
    print("Scanning workspace for stability analysis...")
    changes = monitor.scan_workspace()
    print(f"Tracked {changes} file changes")
    
    if len(sys.argv) > 1 and sys.argv[1] == '--json':
        output_path = monitor.save_report()
        print(f"Report saved to: {output_path}")
    else:
        monitor.print_summary()
        
        if '--save' in sys.argv:
            monitor.save_report()


if __name__ == '__main__':
    main()
