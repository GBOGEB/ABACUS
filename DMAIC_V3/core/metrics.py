"""
DMAIC V3.0 - Metrics Tracking and Aggregation
Comprehensive metrics collection, aggregation, and export functionality
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict
from dataclasses import asdict

from .models import Metric, PhaseMetrics, MetricType, PhaseStatus


class MetricsTracker:
    """
    Track metrics during phase execution
    
    Responsibilities:
    - Record individual metrics
    - Track phase timing
    - Maintain metric history
    - Support metric queries
    """
    
    def __init__(self, phase_name: str, iteration: int):
        self.phase_name = phase_name
        self.iteration = iteration
        self.phase_metrics = PhaseMetrics(
            phase_name=phase_name,
            iteration=iteration
        )
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
    
    def start(self):
        """Start tracking phase execution"""
        self.start_time = datetime.now()
        self.phase_metrics.start_time = self.start_time
        self.phase_metrics.status = PhaseStatus.IN_PROGRESS
    
    def end(self, status: PhaseStatus = PhaseStatus.COMPLETED):
        """End tracking phase execution"""
        self.end_time = datetime.now()
        self.phase_metrics.end_time = self.end_time
        self.phase_metrics.status = status
        
        if self.start_time:
            duration = (self.end_time - self.start_time).total_seconds()
            self.phase_metrics.duration_seconds = duration
            
            self.record_metric(
                name=f"{self.phase_name}_duration",
                value=duration,
                unit="seconds",
                metric_type=MetricType.DURATION
            )
    
    def record_metric(
        self,
        name: str,
        value: float,
        unit: str,
        metric_type: MetricType,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a single metric"""
        metric = Metric(
            name=name,
            value=value,
            unit=unit,
            metric_type=metric_type,
            metadata=metadata or {}
        )
        self.phase_metrics.add_metric(metric)
    
    def record_counter(self, name: str, value: float, metadata: Optional[Dict] = None):
        """Record a counter metric"""
        self.record_metric(name, value, "count", MetricType.COUNTER, metadata)
    
    def record_gauge(self, name: str, value: float, unit: str, metadata: Optional[Dict] = None):
        """Record a gauge metric"""
        self.record_metric(name, value, unit, MetricType.GAUGE, metadata)
    
    def record_histogram(self, name: str, value: float, unit: str, metadata: Optional[Dict] = None):
        """Record a histogram metric"""
        self.record_metric(name, value, unit, MetricType.HISTOGRAM, metadata)
    
    def get_metrics(self) -> PhaseMetrics:
        """Get all recorded metrics"""
        return self.phase_metrics
    
    def get_metric_by_name(self, name: str) -> Optional[Metric]:
        """Get a specific metric by name"""
        for metric in self.phase_metrics.metrics:
            if metric.name == name:
                return metric
        return None
    
    def get_metrics_by_type(self, metric_type: MetricType) -> List[Metric]:
        """Get all metrics of a specific type"""
        return [m for m in self.phase_metrics.metrics if m.metric_type == metric_type]


class MetricsAggregator:
    """
    Aggregate metrics across phases and iterations
    
    Responsibilities:
    - Combine metrics from multiple phases
    - Calculate aggregate statistics
    - Track trends across iterations
    - Generate summary reports
    """
    
    def __init__(self):
        self.phase_metrics: Dict[str, List[PhaseMetrics]] = defaultdict(list)
        self.iteration_metrics: Dict[int, List[PhaseMetrics]] = defaultdict(list)
    
    def add_phase_metrics(self, metrics: PhaseMetrics):
        """Add metrics from a phase execution"""
        self.phase_metrics[metrics.phase_name].append(metrics)
        self.iteration_metrics[metrics.iteration].append(metrics)
    
    def get_phase_history(self, phase_name: str) -> List[PhaseMetrics]:
        """Get all metrics for a specific phase"""
        return self.phase_metrics.get(phase_name, [])
    
    def get_iteration_metrics(self, iteration: int) -> List[PhaseMetrics]:
        """Get all metrics for a specific iteration"""
        return self.iteration_metrics.get(iteration, [])
    
    def calculate_phase_average_duration(self, phase_name: str) -> float:
        """Calculate average duration for a phase"""
        history = self.get_phase_history(phase_name)
        if not history:
            return 0.0
        
        durations = [pm.duration_seconds for pm in history if pm.duration_seconds > 0]
        return sum(durations) / len(durations) if durations else 0.0
    
    def calculate_iteration_total_duration(self, iteration: int) -> float:
        """Calculate total duration for an iteration"""
        metrics = self.get_iteration_metrics(iteration)
        return sum(pm.duration_seconds for pm in metrics)
    
    def get_metric_statistics(self, metric_name: str) -> Dict[str, float]:
        """Calculate statistics for a specific metric across all phases"""
        values = []
        
        for phase_list in self.phase_metrics.values():
            for phase_metrics in phase_list:
                for metric in phase_metrics.metrics:
                    if metric.name == metric_name:
                        values.append(metric.value)
        
        if not values:
            return {}
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "sum": sum(values)
        }
    
    def get_phase_success_rate(self, phase_name: str) -> float:
        """Calculate success rate for a phase"""
        history = self.get_phase_history(phase_name)
        if not history:
            return 0.0
        
        completed = sum(1 for pm in history if pm.status == PhaseStatus.COMPLETED)
        return (completed / len(history)) * 100
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate comprehensive metrics summary"""
        summary = {
            "total_phases": len(self.phase_metrics),
            "total_iterations": len(self.iteration_metrics),
            "phase_summaries": {},
            "iteration_summaries": {}
        }
        
        for phase_name, history in self.phase_metrics.items():
            summary["phase_summaries"][phase_name] = {
                "executions": len(history),
                "average_duration": self.calculate_phase_average_duration(phase_name),
                "success_rate": self.get_phase_success_rate(phase_name),
                "total_metrics": sum(len(pm.metrics) for pm in history)
            }
        
        for iteration, metrics in self.iteration_metrics.items():
            summary["iteration_summaries"][iteration] = {
                "phases_executed": len(metrics),
                "total_duration": self.calculate_iteration_total_duration(iteration),
                "total_metrics": sum(len(pm.metrics) for pm in metrics)
            }
        
        return summary


class MetricsExporter:
    """
    Export metrics to various formats
    
    Responsibilities:
    - Export to JSON
    - Export to CSV
    - Export to markdown reports
    - Generate visualizations data
    """
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_phase_metrics_json(self, metrics: PhaseMetrics, filename: Optional[str] = None):
        """Export phase metrics to JSON"""
        if filename is None:
            filename = f"{metrics.phase_name}_iter{metrics.iteration}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        output_file = self.output_dir / filename
        
        with open(output_file, 'w') as f:
            json.dump(metrics.to_dict(), f, indent=2)
        
        return output_file
    
    def export_aggregated_metrics_json(self, aggregator: MetricsAggregator, filename: str = "aggregated_metrics.json"):
        """Export aggregated metrics to JSON"""
        output_file = self.output_dir / filename
        
        data = {
            "summary": aggregator.generate_summary(),
            "phase_metrics": {
                phase: [pm.to_dict() for pm in history]
                for phase, history in aggregator.phase_metrics.items()
            },
            "exported_at": datetime.now().isoformat()
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        return output_file
    
    def export_metrics_csv(self, metrics: PhaseMetrics, filename: Optional[str] = None):
        """Export metrics to CSV format"""
        if filename is None:
            filename = f"{metrics.phase_name}_iter{metrics.iteration}.csv"
        
        output_file = self.output_dir / filename
        
        with open(output_file, 'w') as f:
            f.write("metric_name,value,unit,type,timestamp\n")
            
            for metric in metrics.metrics:
                f.write(f"{metric.name},{metric.value},{metric.unit},{metric.metric_type.value},{metric.timestamp.isoformat()}\n")
        
        return output_file
    
    def export_summary_markdown(self, aggregator: MetricsAggregator, filename: str = "metrics_summary.md"):
        """Export metrics summary as markdown"""
        output_file = self.output_dir / filename
        
        summary = aggregator.generate_summary()
        
        with open(output_file, 'w') as f:
            f.write("# DMAIC V3 Metrics Summary\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
            
            f.write("## Overview\n\n")
            f.write(f"- **Total Phases:** {summary['total_phases']}\n")
            f.write(f"- **Total Iterations:** {summary['total_iterations']}\n\n")
            
            f.write("## Phase Summaries\n\n")
            for phase_name, phase_summary in summary['phase_summaries'].items():
                f.write(f"### {phase_name}\n\n")
                f.write(f"- **Executions:** {phase_summary['executions']}\n")
                f.write(f"- **Average Duration:** {phase_summary['average_duration']:.2f}s\n")
                f.write(f"- **Success Rate:** {phase_summary['success_rate']:.1f}%\n")
                f.write(f"- **Total Metrics:** {phase_summary['total_metrics']}\n\n")
            
            f.write("## Iteration Summaries\n\n")
            for iteration, iter_summary in summary['iteration_summaries'].items():
                f.write(f"### Iteration {iteration}\n\n")
                f.write(f"- **Phases Executed:** {iter_summary['phases_executed']}\n")
                f.write(f"- **Total Duration:** {iter_summary['total_duration']:.2f}s\n")
                f.write(f"- **Total Metrics:** {iter_summary['total_metrics']}\n\n")
        
        return output_file
    
    def export_all(self, aggregator: MetricsAggregator, prefix: str = "dmaic_v3"):
        """Export all metrics in all formats"""
        results = {
            "json": self.export_aggregated_metrics_json(aggregator, f"{prefix}_metrics.json"),
            "markdown": self.export_summary_markdown(aggregator, f"{prefix}_summary.md")
        }
        
        return results
