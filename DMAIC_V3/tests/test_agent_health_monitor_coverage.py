import json
from datetime import datetime, timedelta

import pytest

from DMAIC_V3.core.agent_health_monitor import (
    AgentHealthMonitor,
    HealthStatus,
    MaturityLevel,
)


def _iso(delta):
    return (datetime.now() + delta).isoformat()


@pytest.mark.parametrize(
    ("age_seconds", "expected"),
    [
        (10, MaturityLevel.INFANT),
        (600, MaturityLevel.YOUNG),
        (7200, MaturityLevel.MATURE),
        (172800, MaturityLevel.VETERAN),
    ],
)
def test_maturity_boundaries(tmp_path, age_seconds, expected):
    monitor = AgentHealthMonitor(tmp_path / "agents.json")
    assert monitor.calculate_maturity(age_seconds) == expected


def test_health_alerts_and_status_classification(tmp_path):
    monitor = AgentHealthMonitor(tmp_path / "agents.json")

    healthy = {
        "first_execution": _iso(timedelta(hours=-2)),
        "last_execution": _iso(timedelta(minutes=-5)),
        "total_executions": 12,
        "execution_times": [
            _iso(timedelta(minutes=-35)),
            _iso(timedelta(minutes=-25)),
            _iso(timedelta(minutes=-15)),
            _iso(timedelta(minutes=-5)),
        ],
        "iterations": [1, 2, 3],
    }
    healthy_result = monitor.analyze_agent_health("healthy", healthy)
    assert healthy_result.status in {HealthStatus.HEALTHY, HealthStatus.MATURE}
    assert healthy_result.health_score > 0.7
    assert healthy_result.metrics["total_executions"] == 12

    stale = {
        "first_execution": _iso(timedelta(days=-5)),
        "last_execution": _iso(timedelta(hours=-30)),
        "total_executions": 4,
        "execution_times": [
            _iso(timedelta(hours=-80)),
            _iso(timedelta(hours=-70)),
            _iso(timedelta(hours=-30)),
        ],
        "iterations": [1],
    }
    stale_result = monitor.analyze_agent_health("stale", stale)
    assert stale_result.status == HealthStatus.STALE
    assert monitor.check_stale_agents(stale, "stale") is not None
    assert monitor.check_execution_frequency(stale, "stale") is not None


def test_performance_degradation_and_frequency_edges(tmp_path):
    monitor = AgentHealthMonitor(tmp_path / "agents.json")

    degraded = {
        "first_execution": _iso(timedelta(hours=-5)),
        "last_execution": _iso(timedelta(minutes=-10)),
        "total_executions": 4,
        "execution_times": [
            _iso(timedelta(hours=-4)),
            _iso(timedelta(hours=-3)),
            _iso(timedelta(hours=-1)),
        ],
    }
    alert = monitor.check_performance_degradation(degraded, "worker")
    assert alert is not None
    assert alert.severity == "warning"

    insufficient = dict(degraded)
    insufficient["execution_times"] = insufficient["execution_times"][:2]
    assert monitor.check_performance_degradation(insufficient, "worker") is None

    very_new = {
        "first_execution": _iso(timedelta(seconds=-30)),
        "last_execution": _iso(timedelta(seconds=-5)),
        "total_executions": 1,
    }
    assert monitor.check_execution_frequency(very_new, "new") is None


def test_monitor_report_trigger_and_adaptive_strategy(tmp_path):
    path = tmp_path / "agents.json"
    payload = {
        "fresh": {
            "first_execution": _iso(timedelta(minutes=-20)),
            "last_execution": _iso(timedelta(minutes=-2)),
            "total_executions": 3,
            "execution_times": [
                _iso(timedelta(minutes=-20)),
                _iso(timedelta(minutes=-10)),
                _iso(timedelta(minutes=-2)),
            ],
            "iterations": [1, 2, 3],
        },
        "stale": {
            "first_execution": _iso(timedelta(days=-3)),
            "last_execution": _iso(timedelta(hours=-30)),
            "total_executions": 3,
            "execution_times": [
                _iso(timedelta(days=-3)),
                _iso(timedelta(days=-2)),
                _iso(timedelta(hours=-30)),
            ],
            "iterations": [1],
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    monitor = AgentHealthMonitor(path)

    report = monitor.generate_health_report()
    assert report["total_agents"] == 2
    assert report["summary"]["stale"] == 1
    assert report["maturity_distribution"]

    should_run, reason = monitor.should_trigger_iteration("missing")
    assert should_run is True
    assert "New agent" in reason

    should_run, reason = monitor.should_trigger_iteration("stale")
    assert should_run is True
    assert "stale" in reason.lower()

    assert monitor.get_adaptive_strategy("missing")["strategy"] == "aggressive"
    assert monitor.get_adaptive_strategy("fresh")["strategy"] in {"aggressive", "moderate"}

    missing_monitor = AgentHealthMonitor(tmp_path / "does-not-exist.json")
    assert missing_monitor.load_agent_age_data() == {}
