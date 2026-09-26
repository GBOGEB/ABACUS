from datetime import datetime, timedelta
import json

from DMAIC_V3.core.models import (
    ExecutionState,
    IterationResult,
    KnowledgePack,
    Metric,
    MetricType,
    PhaseMetrics,
    PhaseStatus,
)
from DMAIC_V3.core.metrics import MetricsAggregator, MetricsExporter, MetricsTracker


def test_models_serialize_complete_execution_state():
    metric = Metric("throughput", 12.5, "items/s", MetricType.GAUGE, metadata={"source": "test"})
    phase = PhaseMetrics("measure", 2)
    phase.add_metric(metric)
    phase.start_time = datetime(2026, 1, 1, 12, 0, 0)
    phase.end_time = datetime(2026, 1, 1, 12, 0, 5)
    phase.duration_seconds = 5.0
    phase.status = PhaseStatus.COMPLETED

    pack = KnowledgePack(
        iteration=2,
        phase_name="measure",
        artifacts=["metrics.json"],
        insights=["stable"],
        decisions=[{"id": "D1"}],
        references=["REQ-1"],
    )
    iteration = IterationResult(
        iteration=2,
        phases_completed=["measure"],
        total_duration_seconds=5.0,
        metrics={"measure": phase},
        knowledge_packs=[pack],
        start_time=phase.start_time,
        end_time=phase.end_time,
        success=True,
    )
    state = ExecutionState(
        current_iteration=2,
        current_phase="measure",
        iterations={2: iteration},
        global_metrics=[metric],
        execution_start=phase.start_time,
        execution_end=phase.end_time,
        total_iterations_completed=2,
    )

    payload = state.to_dict()
    assert payload["current_iteration"] == 2
    assert payload["iterations"][2]["success"] is True
    assert payload["iterations"][2]["metrics"]["measure"]["status"] == "completed"
    assert payload["global_metrics"][0]["metric_type"] == "gauge"
    assert payload["iterations"][2]["knowledge_packs"][0]["references"] == ["REQ-1"]


def test_metrics_tracker_records_queries_and_duration():
    tracker = MetricsTracker("analyze", 3)
    tracker.start()
    tracker.record_counter("files", 4)
    tracker.record_gauge("coverage", 42.0, "%", {"scope": "core"})
    tracker.record_histogram("latency", 1.5, "s")
    tracker.end()

    assert tracker.get_metric_by_name("files").value == 4
    assert tracker.get_metric_by_name("missing") is None
    gauges = tracker.get_metrics_by_type(MetricType.GAUGE)
    assert [m.name for m in gauges] == ["coverage"]
    assert tracker.get_metrics().status == PhaseStatus.COMPLETED
    assert tracker.get_metrics().duration_seconds >= 0
    assert tracker.get_metric_by_name("analyze_duration") is not None


def test_metrics_aggregator_statistics_and_summary():
    p1 = PhaseMetrics("define", 1, duration_seconds=2.0, status=PhaseStatus.COMPLETED)
    p1.add_metric(Metric("score", 10.0, "pts", MetricType.GAUGE))
    p2 = PhaseMetrics("define", 2, duration_seconds=4.0, status=PhaseStatus.FAILED)
    p2.add_metric(Metric("score", 20.0, "pts", MetricType.GAUGE))

    agg = MetricsAggregator()
    agg.add_phase_metrics(p1)
    agg.add_phase_metrics(p2)

    assert agg.get_phase_history("define") == [p1, p2]
    assert agg.get_iteration_metrics(1) == [p1]
    assert agg.get_phase_history("missing") == []
    assert agg.calculate_phase_average_duration("define") == 3.0
    assert agg.calculate_phase_average_duration("missing") == 0.0
    assert agg.calculate_iteration_total_duration(2) == 4.0
    assert agg.get_metric_statistics("score") == {
        "count": 2,
        "min": 10.0,
        "max": 20.0,
        "mean": 15.0,
        "sum": 30.0,
    }
    assert agg.get_metric_statistics("missing") == {}
    assert agg.get_phase_success_rate("define") == 50.0
    assert agg.get_phase_success_rate("missing") == 0.0

    summary = agg.generate_summary()
    assert summary["total_phases"] == 1
    assert summary["total_iterations"] == 2
    assert summary["phase_summaries"]["define"]["executions"] == 2


def test_metrics_exporter_writes_all_formats(tmp_path):
    phase = PhaseMetrics("control", 4, duration_seconds=1.25, status=PhaseStatus.COMPLETED)
    phase.add_metric(Metric("quality", 99.0, "%", MetricType.GAUGE))
    agg = MetricsAggregator()
    agg.add_phase_metrics(phase)

    exporter = MetricsExporter(tmp_path)
    phase_json = exporter.export_phase_metrics_json(phase, "phase.json")
    aggregate_json = exporter.export_aggregated_metrics_json(agg, "aggregate.json")
    csv_path = exporter.export_metrics_csv(phase, "phase.csv")
    md_path = exporter.export_summary_markdown(agg, "summary.md")
    all_paths = exporter.export_all(agg, "bundle")

    assert json.loads(phase_json.read_text())["phase_name"] == "control"
    assert json.loads(aggregate_json.read_text())["summary"]["total_phases"] == 1
    assert "metric_name,value,unit,type,timestamp" in csv_path.read_text()
    assert "# DMAIC V3 Metrics Summary" in md_path.read_text()
    assert all_paths["json"].exists()
    assert all_paths["markdown"].exists()
