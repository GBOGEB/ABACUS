from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class PhaseStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    DURATION = "duration"


@dataclass
class Metric:
    name: str
    value: float
    unit: str
    metric_type: MetricType
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "metric_type": self.metric_type.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class PhaseMetrics:
    phase_name: str
    iteration: int
    metrics: List[Metric] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    status: PhaseStatus = PhaseStatus.PENDING
    
    def add_metric(self, metric: Metric):
        self.metrics.append(metric)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase_name": self.phase_name,
            "iteration": self.iteration,
            "metrics": [m.to_dict() for m in self.metrics],
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "status": self.status.value
        }


@dataclass
class KnowledgePack:
    iteration: int
    phase_name: str
    artifacts: List[str] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "iteration": self.iteration,
            "phase_name": self.phase_name,
            "artifacts": self.artifacts,
            "insights": self.insights,
            "decisions": self.decisions,
            "references": self.references,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class IterationResult:
    iteration: int
    phases_completed: List[str] = field(default_factory=list)
    phases_failed: List[str] = field(default_factory=list)
    phases_skipped: List[str] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    metrics: Dict[str, PhaseMetrics] = field(default_factory=dict)
    knowledge_packs: List[KnowledgePack] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    success: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "iteration": self.iteration,
            "phases_completed": self.phases_completed,
            "phases_failed": self.phases_failed,
            "phases_skipped": self.phases_skipped,
            "total_duration_seconds": self.total_duration_seconds,
            "metrics": {k: v.to_dict() for k, v in self.metrics.items()},
            "knowledge_packs": [kp.to_dict() for kp in self.knowledge_packs],
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "success": self.success
        }


@dataclass
class ExecutionState:
    current_iteration: int = 0
    current_phase: Optional[str] = None
    iterations: Dict[int, IterationResult] = field(default_factory=dict)
    global_metrics: List[Metric] = field(default_factory=list)
    execution_start: Optional[datetime] = None
    execution_end: Optional[datetime] = None
    total_iterations_completed: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_iteration": self.current_iteration,
            "current_phase": self.current_phase,
            "iterations": {k: v.to_dict() for k, v in self.iterations.items()},
            "global_metrics": [m.to_dict() for m in self.global_metrics],
            "execution_start": self.execution_start.isoformat() if self.execution_start else None,
            "execution_end": self.execution_end.isoformat() if self.execution_end else None,
            "total_iterations_completed": self.total_iterations_completed
        }
