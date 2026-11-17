"""Lane A wave 13: DMAIC_V3.core.twelve_cluster_orchestrator behaviour."""

import json
import math
import sys
import threading
import time
import types

import pytest

from DMAIC_V3.core import twelve_cluster_orchestrator as tco


@pytest.fixture
def orch():
    return tco.TwelveClusterOrchestrator(use_keb=False, use_gbogeb=False)


class _Backbone:
    instances = []

    def __init__(self, max_workers, max_memory_mb):
        self.max_workers = max_workers
        self.scheduled = []
        self.events = []
        self.tasks_executed = 0
        self.tasks_failed = 0
        self.task_queue = types.SimpleNamespace(empty=self._empty)
        self._polls = 0
        type(self).instances.append(self)

    def _empty(self):
        self._polls += 1
        return self._polls > 1

    def start(self):
        self.events.append("start")

    def stop(self):
        self.events.append("stop")

    def schedule_task(self, task_id, func, priority, args):
        self.scheduled.append((task_id, priority))
        func(*args)
        self.tasks_executed += 1


class _Gbogeb:
    def __init__(self, workspace):
        self.workspace = workspace
        self.metrics = []

    def collect_metric(self, **kw):
        self.metrics.append(kw)


def test_init_and_contract(capsys):
    orch = tco.TwelveClusterOrchestrator(use_keb=False, use_gbogeb=False)
    assert orch.use_execution_backbone is False
    assert orch.use_gbogeb is False
    contract = orch.get_cluster_contract()
    assert len(contract) == 12
    assert contract[0] == {
        "cluster_id": 1,
        "name": "Define-Scanner-1",
        "phase": "phase1",
        "priority": 10,
    }
    assert "initialized with 12 clusters" in capsys.readouterr().out


def test_use_keb_overrides_backbone_flag(monkeypatch):
    monkeypatch.setattr(tco, "EXECUTION_BACKBONE_AVAILABLE", True)
    monkeypatch.setattr(tco, "ExecutionBackbone", _Backbone, raising=False)
    monkeypatch.setattr(_Backbone, "instances", [])
    off = tco.TwelveClusterOrchestrator(use_keb=False, use_gbogeb=False)
    assert off.execution_backbone is None
    on = tco.TwelveClusterOrchestrator(
        max_workers=8, use_execution_backbone=True, use_gbogeb=False
    )
    assert on.execution_backbone.max_workers == 4


@pytest.mark.parametrize(
    "task,expected",
    [
        ({"file_path": "f.py", "task_id": "t"}, "f.py"),
        ({"task_id": 7}, "7"),
        ({"id": "x"}, "x"),
        ({"file_path": None}, "phase2:cluster3:task4"),
    ],
)
def test_task_key(task, expected):
    assert tco.TwelveClusterOrchestrator._task_key(task, "phase2", 3, 4) == expected


def test_execute_task_callable_and_passthrough(orch):
    cluster = orch.clusters[1]
    task = {"func": sorted, "args": ([1, 5],), "kwargs": {"reverse": True}}
    assert orch._execute_task(task, cluster) == [5, 1]
    plain = {"id": 1}
    assert orch._execute_task(plain, cluster) is plain


def test_execute_phase_unknown_and_empty(orch):
    with pytest.raises(ValueError, match="Unknown or unmapped phase"):
        orch.execute_phase_parallel("phase99", [{"id": 1}], 1)
    result = orch.execute_phase_parallel("phase3", [], 1)
    assert result["success"] is True
    assert result["tasks_executed"] == 0
    assert result["results_map"] == {}


def test_execute_phase_local_success_and_task_failure(orch, capsys):
    def bad():
        raise RuntimeError("nope")

    tasks = [{"task_id": f"t{i}", "func": abs, "args": (-i,)} for i in range(5)]
    tasks.append({"task_id": "bad", "func": bad})
    result = orch.execute_phase_parallel("phase1", tasks, 2)
    assert result["tasks_executed"] == 5
    assert result["tasks_failed"] == 1
    assert result["success"] is False
    assert result["clusters_used"] == 2
    assert result["results_map"] == {f"t{i}": i for i in range(5)}
    assert orch.clusters[1].tasks_executed + orch.clusters[2].tasks_executed == 5
    assert orch.clusters[1].status == "idle"
    assert "Task bad failed" in capsys.readouterr().out


def test_single_cluster_phase(orch):
    tasks = [{"id": i} for i in range(3)]
    result = orch.execute_phase_parallel("phase3", tasks, 1)
    assert result["clusters_used"] == 1
    assert sorted(result["results_map"]) == ["0", "1", "2"]
    assert result["success"] is True


def test_cluster_level_exception_counts_whole_chunk(orch, monkeypatch, capsys):
    def explode(cluster, chunk, phase):
        raise RuntimeError("cluster down")

    monkeypatch.setattr(orch, "_execute_cluster_tasks", explode)
    result = orch.execute_phase_parallel("phase2", [{"id": i} for i in range(4)], 1)
    assert result["tasks_failed"] == 4
    assert result["tasks_executed"] == 0
    assert result["success"] is False
    assert "failed: cluster down" in capsys.readouterr().out


def test_timeout_fails_closed(capsys):
    orch = tco.TwelveClusterOrchestrator(
        use_keb=False, use_gbogeb=False, task_timeout_seconds=0.05
    )
    gate = threading.Event()
    tasks = [{"id": "slow", "func": gate.wait, "args": (2,)}]
    try:
        result = orch.execute_phase_parallel("phase5", tasks, 1)
    finally:
        gate.set()
    assert result["tasks_failed"] == 1
    assert result["success"] is False
    assert orch.clusters[7].status == "idle"
    assert "timed out" in capsys.readouterr().out


def test_backbone_and_gbogeb_path(monkeypatch):
    monkeypatch.setattr(tco, "EXECUTION_BACKBONE_AVAILABLE", True)
    monkeypatch.setattr(tco, "GBOGEB_AVAILABLE", True)
    monkeypatch.setattr(tco, "ExecutionBackbone", _Backbone, raising=False)
    monkeypatch.setattr(tco, "GBOGEB", _Gbogeb, raising=False)
    monkeypatch.setattr(_Backbone, "instances", [])
    fake_time = types.SimpleNamespace(time=time.time, sleep=lambda s: None)
    monkeypatch.setattr(tco, "time", fake_time)

    orch = tco.TwelveClusterOrchestrator(use_execution_backbone=True)
    assert orch.gbogeb.workspace.endswith("12cluster_workspace")
    tasks = [{"task_id": "a"}, {"task_id": "b"}, {}]
    result = orch.execute_phase_parallel("phase7", tasks, 3)
    backbone = _Backbone.instances[0]
    assert backbone.events == ["start", "stop"]
    assert [t[0] for t in backbone.scheduled] == ["a", "b", "phase7:cluster10:task0"]
    assert result["success"] is True
    assert result["tasks_executed"] == 3
    assert result["results_map"] == {}
    metric = orch.gbogeb.metrics[0]
    assert metric["metric_name"] == "phase7_execution"
    assert metric["tags"] == {"iteration": "3", "clusters": "2"}


def test_overflow_chunks_go_to_last_cluster(orch, monkeypatch):
    # Normal chunking never overflows; force chunk size 1 to reach that branch.
    monkeypatch.setattr(math, "ceil", lambda x: 1)
    tasks = [{"id": i} for i in range(5)]
    result = orch.execute_phase_parallel("phase1", tasks, 1)
    assert result["clusters_used"] == 5
    assert result["tasks_executed"] == 5


def test_run_phases_with_hooks_success(orch):
    def factory(phase):
        return [{"task_id": phase + "-t"}] if phase == "phase2" else None

    result = orch.run_phases_with_hooks(4, factory)
    assert result["success"] is True
    assert result["final_status"] == "completed"
    assert result["phases_run"] == orch.PHASE_SEQUENCE
    assert result["total_tasks_executed"] == 1
    events = result["temporal_events"]
    assert len(events) == 16
    assert events[0]["event"] == "phase_start"
    assert events[0]["clusters"] == [1, 2]
    assert events[3]["artifacts"] == ["phase2-t"]
    assert events[1]["artifacts"] == ["phase1:no-result-artifact"]


def test_run_phases_with_hooks_factory_error(orch):
    def factory(phase):
        if phase == "phase6":
            raise RuntimeError("factory broke")
        return []

    result = orch.run_phases_with_hooks(1, factory)
    assert result["success"] is False
    assert result["final_status"] == "failed"
    assert result["total_tasks_failed"] == 1
    phase6 = result["phase_results"]["phase6"]
    assert phase6["error"] == "factory broke"
    assert phase6["clusters_used"] == 1
    end = [e for e in result["temporal_events"] if e["phase"] == "phase6"][1]
    assert end["status"] == "failed"


def test_cluster_status_and_report(orch, tmp_path):
    orch.temporal_events = [{"event": "x"}]
    status = orch.get_cluster_status()
    assert status["total_clusters"] == 12
    assert status["clusters"][11]["name"] == "TODO-Manager-2"
    out = tmp_path / "nested" / "report.json"
    orch.generate_report(out)
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["temporal_events"] == [{"event": "x"}]
    assert report["execution_backbone_enabled"] is False
    assert report["status"]["total_clusters"] == 12


def test_main_test_mode(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    argv = ["tco", "--test", "--phase", "phase8", "--tasks", "4"]
    monkeypatch.setattr(sys, "argv", argv)
    assert tco.main() == 0
    out = capsys.readouterr().out
    assert "Test Results:" in out
    assert '"tasks_executed": 4' in out
    assert (tmp_path / "DMAIC_V3_OUTPUT" / "12cluster_test_report.json").exists()


def test_main_without_test_flag(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["tco"])
    assert tco.main() == 0
    assert not (tmp_path / "DMAIC_V3_OUTPUT").exists()
