"""Lane A wave 14: DMAIC_V3.core.agent_health_monitor status and strategy rules."""

import json
from datetime import datetime, timedelta

import pytest

from DMAIC_V3.core import agent_health_monitor as ahm


def _iso(seconds_ago, now=None):
    now = now or datetime.now()
    return (now - timedelta(seconds=seconds_ago)).isoformat()


def _agent(age_s, last_ago_s=10, total=10, exec_times=None):
    # One reference time for both stamps: separate now() calls differ by
    # microseconds on Linux/macOS, which turns age 0 into a huge frequency.
    now = datetime.now()
    data = {
        "first_execution": _iso(last_ago_s + age_s, now),
        "last_execution": _iso(last_ago_s, now),
        "total_executions": total,
        "iterations": [1, 2],
    }
    if exec_times is not None:
        data["execution_times"] = exec_times
    return data


AGENTS = {
    "healthy": _agent(1000, total=10),
    "new": _agent(100, total=3),
    "veteran": _agent(8 * 86400, total=500),
    "warning": _agent(100 * 3600, last_ago_s=13 * 3600, total=5),
    "stale": _agent(2000, last_ago_s=30 * 3600, total=10),
    "mature": _agent(2 * 3600, total=100),
}


@pytest.fixture
def monitor(tmp_path):
    path = tmp_path / "age.json"
    path.write_text(json.dumps(AGENTS), encoding="utf-8")
    return ahm.AgentHealthMonitor(path)


def test_load_missing_file_returns_empty(tmp_path):
    mon = ahm.AgentHealthMonitor(tmp_path / "nope.json")
    assert mon.load_agent_age_data() == {}
    assert mon.monitor_all_agents() == {}
    report = mon.generate_health_report()
    assert report["total_agents"] == 0
    assert report["summary"]["average_health_score"] == 0


@pytest.mark.parametrize(
    "age,level",
    [
        (10, ahm.MaturityLevel.INFANT),
        (1000, ahm.MaturityLevel.YOUNG),
        (5000, ahm.MaturityLevel.MATURE),
        (10**6, ahm.MaturityLevel.VETERAN),
    ],
)
def test_calculate_maturity(monitor, age, level):
    assert monitor.calculate_maturity(age) is level


def test_health_score_penalties(monitor):
    assert monitor.calculate_health_score(_agent(1000)) == 1.0
    assert monitor.calculate_health_score(_agent(0, total=1)) == pytest.approx(0.9)
    stale = _agent(1000, last_ago_s=30 * 3600)
    assert monitor.calculate_health_score(stale) == pytest.approx(0.5)
    half = _agent(1000, last_ago_s=13 * 3600)
    assert monitor.calculate_health_score(half) == pytest.approx(0.8)
    low_freq = _agent(100 * 3600, total=5)
    assert monitor.calculate_health_score(low_freq) == pytest.approx(0.8)


def test_stale_alert(monitor):
    assert monitor.check_stale_agents(_agent(10), "a") is None
    alert = monitor.check_stale_agents(_agent(10, last_ago_s=30 * 3600), "a")
    assert alert.severity == "warning"
    assert alert.threshold == 24
    assert alert.metric_value == pytest.approx(30, abs=0.1)


def test_performance_degradation(monitor):
    base = datetime(2025, 1, 1)
    times = [base + timedelta(seconds=s) for s in (0, 60, 120, 720)]
    slow = _agent(10, exec_times=[t.isoformat() for t in times])
    alert = monitor.check_performance_degradation(slow, "a")
    assert alert.metric_value == 600
    assert alert.threshold == 60
    assert "900.0%" in alert.message
    even = [base + timedelta(seconds=s) for s in (0, 60, 120, 180)]
    steady = _agent(10, exec_times=[t.isoformat() for t in even])
    assert monitor.check_performance_degradation(steady, "a") is None
    assert monitor.check_performance_degradation(_agent(10), "a") is None
    short = _agent(10, exec_times=[base.isoformat()] * 2)
    assert monitor.check_performance_degradation(short, "a") is None


def test_execution_frequency(monitor):
    assert monitor.check_execution_frequency(_agent(30), "a") is None
    assert monitor.check_execution_frequency(_agent(1000), "a") is None
    alert = monitor.check_execution_frequency(_agent(100 * 3600, total=5), "a")
    assert alert.severity == "info"
    assert alert.metric_value == pytest.approx(0.05)
    few = _agent(100 * 3600, total=2)
    assert monitor.check_execution_frequency(few, "a") is None


def test_analyze_statuses(monitor):
    expected = {
        "healthy": ahm.HealthStatus.HEALTHY,
        "new": ahm.HealthStatus.NEW,
        "veteran": ahm.HealthStatus.MATURE,
        "warning": ahm.HealthStatus.WARNING,
        "stale": ahm.HealthStatus.STALE,
        "mature": ahm.HealthStatus.HEALTHY,
    }
    for name, status in expected.items():
        health = monitor.analyze_agent_health(name, AGENTS[name])
        assert health.status is status, name
    warn = monitor.analyze_agent_health("warning", AGENTS["warning"])
    assert warn.metrics["iterations"] == [1, 2]
    assert [a.severity for a in warn.alerts] == ["info"]
    assert warn.recommendations == [warn.alerts[0].recommendation]
    zero = monitor.analyze_agent_health("z", _agent(0))
    assert zero.metrics["execution_frequency"] == 0


def test_analyze_critical_and_perf_alert(monitor, monkeypatch):
    monkeypatch.setattr(monitor, "calculate_health_score", lambda d: 0.2)
    base = datetime(2025, 1, 1)
    times = [base + timedelta(seconds=s) for s in (0, 60, 120, 720)]
    data = _agent(1000, exec_times=[t.isoformat() for t in times])
    health = monitor.analyze_agent_health("c", data)
    assert health.status is ahm.HealthStatus.CRITICAL
    assert len(health.alerts) == 1


def test_monitor_all_and_report(monitor):
    report = monitor.generate_health_report()
    assert report["total_agents"] == len(AGENTS)
    summary = report["summary"]
    assert summary["stale"] == 1
    assert summary["warning"] == 1
    assert summary["healthy"] == 2
    assert summary["critical"] == 0
    assert report["maturity_distribution"]["veteran"] == 2
    assert {a["agent"] for a in report["warning_alerts"]} == {"stale"}
    assert report["critical_alerts"] == []
    assert report["agents"]["new"]["status"] == "new"
    monitor.alerts.append(ahm.HealthAlert("x", "critical", "m", "t", 1.0, 0.5, "r"))
    assert [a.agent_name for a in monitor.get_critical_alerts()] == ["x"]


def test_should_trigger_iteration(monitor, monkeypatch):
    assert monitor.should_trigger_iteration("ghost") == (
        True,
        "New agent - should execute",
    )
    trig, reason = monitor.should_trigger_iteration("stale")
    assert trig and reason.startswith("Agent is stale")
    assert monitor.should_trigger_iteration("new") == (
        True,
        "Infant agent needs more executions to mature",
    )
    assert monitor.should_trigger_iteration("healthy")[0] is False
    monkeypatch.setattr(monitor, "calculate_health_score", lambda d: 0.1)
    trig, reason = monitor.should_trigger_iteration("healthy")
    assert trig and "critical (score: 0.10)" in reason


@pytest.mark.parametrize(
    "name,strategy,interval",
    [
        ("ghost", "aggressive", 5),
        ("new", "aggressive", 5),
        ("healthy", "moderate", 15),
        ("mature", "conservative", 60),
        ("veteran", "maintenance", 240),
    ],
)
def test_adaptive_strategy(monitor, name, strategy, interval):
    res = monitor.get_adaptive_strategy(name)
    assert res["strategy"] == strategy
    assert res["recommended_interval_minutes"] == interval
