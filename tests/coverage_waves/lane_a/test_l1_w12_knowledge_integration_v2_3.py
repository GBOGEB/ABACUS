"""Lane A wave 12: local_mcp/knowledge_integration_v2.3.py (backbone mocked)."""

import json
import sys
import threading

import pytest

from tests.coverage_waves.lane_a._load import load

mod = load("local_mcp/knowledge_integration_v2.3.py")


def _slow(flag=None):
    """Return a callable that blocks ~0.1 s, then records completion."""
    done = threading.Event()

    def run(*args, **kwargs):
        done.wait(0.1)
        if flag is not None:
            flag.append("finished")
        return True

    return run


class FakeBackbone:
    def __init__(self, max_workers, max_memory_mb):
        self.config = (max_workers, max_memory_mb)
        self.scheduled = []

    def schedule_task(self, **kwargs):
        self.scheduled.append(kwargs)


class FakeGbogeb:
    def __init__(self, workspace):
        self.workspace = workspace
        self.metrics = []
        self.checks = []

    def collect_metric(self, **kwargs):
        self.metrics.append(kwargs)

    def check_compliance(self, rule_name, check_func, severity):
        self.checks.append((rule_name, severity))
        return "from-gbogeb"


@pytest.fixture
def fallback(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mod, "EXECUTION_BACKBONE_AVAILABLE", False)
    return mod.KnowledgeIntegrationV23(workspace=str(tmp_path / "ws"))


@pytest.fixture
def enabled(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mod, "EXECUTION_BACKBONE_AVAILABLE", True)
    monkeypatch.setattr(mod, "ExecutionBackbone", FakeBackbone, raising=False)
    monkeypatch.setattr(mod, "GBOGEB", FakeGbogeb, raising=False)
    return mod.KnowledgeIntegrationV23(workspace=str(tmp_path / "ws"))


def test_import_fallback_when_backbone_missing(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "core.execution_backbone", None)
    other = load("local_mcp/knowledge_integration_v2.3.py", name="l1_w12_ki_nobb")
    sys.modules.pop("l1_w12_ki_nobb", None)
    assert other.EXECUTION_BACKBONE_AVAILABLE is False
    assert "using fallback mode" in capsys.readouterr().out


def test_run_with_timeout_returns_value():
    assert mod._run_with_timeout(lambda: 5, 1.0) == 5


def test_run_with_timeout_raises():
    with pytest.raises(mod.OperationTimeoutError, match="timed out after 0.01s"):
        mod._run_with_timeout(_slow(), 0.01)


def test_fallback_init_seeds_canonical_entries(fallback, tmp_path):
    assert fallback.execution_backbone is None
    assert fallback.gbogeb is None
    ids = [e.entry_id for e in fallback.knowledge_cache]
    assert ids == ["kb_001", "kb_002", "kb_003"]
    saved = tmp_path / "ws" / "knowledge_base" / "kb_002.json"
    data = json.loads(saved.read_text(encoding="utf-8"))
    assert data["source"] == "12_CLUSTER"
    assert data["tags"]["type"] == "architecture"


def test_add_entry_defaults_tags(fallback):
    fallback.add_knowledge_entry("e1", "src", "cat", {"a": 1})
    entry = fallback.knowledge_cache[-1]
    assert entry.tags == {}
    assert entry.confidence == 1.0


def test_query_knowledge_filters(fallback):
    assert len(fallback.query_knowledge()) == 3
    assert [e.entry_id for e in fallback.query_knowledge(category="domain")] == [
        "kb_003"
    ]
    assert fallback.query_knowledge(source="DMAIC_V3")[0].entry_id == "kb_001"
    assert fallback.query_knowledge(category="domain", source="DMAIC_V3") == []
    by_tag = fallback.query_knowledge(tags={"version": "v2.3"})
    assert [e.entry_id for e in by_tag] == ["kb_002"]
    both = fallback.query_knowledge(tags={"version": "v2.3", "type": "core"})
    assert both == []


def test_collect_metric_fallback(fallback, capsys):
    fallback.collect_agent_metric("ag", "m", 7)
    fallback.collect_agent_metric("ag", "n", 8, tags={"t": "1"})
    assert fallback.metrics_cache[0]["tags"] == {}
    assert fallback.metrics_cache[1]["tags"] == {"t": "1"}
    assert "[METRIC] ag.m = 7" in capsys.readouterr().out


def test_schedule_task_fallback_runs_inline(fallback, capsys):
    seen = []

    def task(x, y=0):
        seen.append(x + y)

    fallback.schedule_agent_task("t1", "ag", task, args=(1,), kwargs={"y": 2})
    fallback.schedule_agent_task("t2", "ag", task, args=(5,), timeout=1.0)
    assert seen == [3, 5]
    assert "[TASK] Scheduled: ag.t1 (priority: 5)" in capsys.readouterr().out


def test_schedule_task_fallback_error_and_timeout(fallback, capsys):
    def bad():
        raise RuntimeError("nope")

    fallback.schedule_agent_task("t3", "ag", bad)
    fallback.schedule_agent_task("t4", "ag", _slow(), timeout=0.01)
    out = capsys.readouterr().out
    assert "[ERROR] Task t3 failed: nope" in out
    assert "[TIMEOUT] Task t4 timed out after 0.01s" in out
    record = fallback.metrics_cache[-1]
    assert record["metric_name"] == "task_timeout"
    assert record["tags"] == {"task_id": "t4", "mode": "fallback"}


def test_check_compliance_fallback_pass_fail(fallback, capsys):
    assert fallback.check_compliance("r1", lambda: True) is True
    assert fallback.check_compliance("r2", lambda: 0, timeout=1.0) == 0
    out = capsys.readouterr().out
    assert "[COMPLIANCE] r1: PASS" in out
    assert "[COMPLIANCE] r2: FAIL" in out


def test_check_compliance_fallback_exception(fallback, capsys):
    def bad():
        raise ValueError("x")

    assert fallback.check_compliance("r3", bad) is False
    assert "r3: ERROR - x" in capsys.readouterr().out


def test_check_compliance_timeout_exhausts_retries(fallback, capsys):
    result = fallback.check_compliance("r4", _slow(), timeout=0.01, max_retries=2)
    out = capsys.readouterr().out
    assert result is False
    assert "r4: timeout, retry 1/2" in out
    assert "r4: TIMEOUT after 2 attempts" in out


def test_check_compliance_retry_then_success(fallback, capsys):
    slow = _slow()
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) == 1:
            return slow()
        return True

    assert fallback.check_compliance("r5", flaky, timeout=0.01) is True
    assert "r5: PASS" in capsys.readouterr().out


def test_check_compliance_zero_retries(fallback):
    assert fallback.check_compliance("r6", lambda: True, max_retries=0) is False


def test_summary_and_export(fallback, tmp_path):
    fallback.collect_agent_metric("ag", "m", 1)
    summary = fallback.get_knowledge_summary()
    assert summary["total_entries"] == 3
    assert summary["categories"] == {
        "methodology": 1,
        "architecture": 1,
        "domain": 1,
    }
    assert summary["sources"]["CRYO_FRAMEWORK"] == 1
    assert summary["metrics_collected"] == 1
    assert summary["gbogeb_enabled"] is False
    path = fallback.export_knowledge_base("out.json")
    assert path == tmp_path / "ws" / "out.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["entries"]) == 3
    assert data["metrics"][0]["metric_name"] == "m"


def test_enabled_mode_delegates(enabled):
    assert enabled.execution_backbone.config == (2, 2048)
    assert enabled.gbogeb.workspace.endswith("gbogeb")
    assert len(enabled.gbogeb.metrics) == 3
    assert enabled.gbogeb.metrics[0]["tags"] == {
        "category": "methodology",
        "source": "DMAIC_V3",
    }
    enabled.collect_agent_metric("ag", "m", 2)
    assert enabled.gbogeb.metrics[-1]["agent"] == "ag"
    assert enabled.gbogeb.metrics[-1]["tags"] == {}
    assert enabled.metrics_cache == []

    enabled.schedule_agent_task("t", "ag", print, priority=1, args=(1,))
    task = enabled.execution_backbone.scheduled[0]
    assert task["task_id"] == "ag_t"
    assert task["priority"] == 1
    assert task["kwargs"] == {}

    assert enabled.check_compliance("r", bool, severity="warning") == "from-gbogeb"
    assert enabled.gbogeb.checks == [("r", "warning")]


def test_main_runs_in_fallback(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mod, "EXECUTION_BACKBONE_AVAILABLE", False)
    mod.main()
    out = capsys.readouterr().out
    assert "Found 1 methodology entries" in out
    assert "kb_001: DMAIC Cycle" in out
    assert "TEST COMPLETE" in out
    export = tmp_path / "knowledge_workspace_v2.3" / "knowledge_export.json"
    assert (
        json.loads(export.read_text(encoding="utf-8"))["summary"]["total_entries"] == 4
    )


def check_production_defect_timeout_waits_for_task():
    # Pins a production_defect: _run_with_timeout leaves its ThreadPoolExecutor
    # via the "with" block, whose shutdown(wait=True) blocks until the task
    # finishes, so the timeout never bounds wall-clock time. Fails once fixed.
    flag = []
    with pytest.raises(mod.OperationTimeoutError):
        mod._run_with_timeout(_slow(flag), 0.01)
    assert flag == ["finished"]
