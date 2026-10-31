"""Gap tests for src/dmaic/metrics.py (global collector state is restored)."""

import pytest

from src.dmaic import metrics as mod


@pytest.fixture
def fresh(monkeypatch):
    monkeypatch.setattr(mod, "_global_metrics", mod.MetricsCollector())
    return mod


def test_collector_record_appends_with_timestamp():
    c = mod.MetricsCollector()
    c.record("k", 1)
    c.record("k", 2)
    values = c.get("k")
    assert [v["value"] for v in values] == [1, 2]
    assert all("T" in v["timestamp"] for v in values)
    assert c.get("missing") == []
    assert c.aggregate() == {"k": values}


def test_global_record_get_and_reset(fresh):
    fresh.record_metric("a", 3.5)
    fresh.record_metric("b", "x")
    got = fresh.get_metrics()
    assert set(got) == {"a", "b"}
    assert got["a"][0]["value"] == 3.5
    fresh.reset_metrics()
    assert fresh.get_metrics() == {}
