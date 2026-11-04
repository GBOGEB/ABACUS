"""Wave 13 lane A behaviour tests for DMAIC_V3/phases/phase2_measure.py."""

import importlib
import json
import sys
from types import SimpleNamespace

import pytest


def _import_restoring_sys_path():
    saved = list(sys.path)
    try:
        return importlib.import_module("DMAIC_V3.phases.phase2_measure")
    finally:
        sys.path[:] = saved


p2 = _import_restoring_sys_path()

SAMPLE = (
    "# header comment\n"
    "import os\n"
    "import sys, json\n"
    "from pathlib import Path\n"
    "from . import sibling\n"
    "\n"
    "class A:\n"
    "    def m(self, x):\n"
    "        return x\n"
    "\n"
    "def f(a, b, c):\n"
    "    return a\n"
)


class FakeCluster:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls = []
        self.response = {}

    def execute_phase_parallel(self, phase, tasks, iteration):
        self.calls.append((phase, tasks, iteration))
        return self.response


class FakeQueue:
    def __init__(self, sizes):
        self.sizes = list(sizes)

    def empty(self):
        return self.sizes.pop(0) if self.sizes else True


class FakeBackbone:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.scheduled = []
        self.started = False
        self.stopped = False
        self.task_queue = FakeQueue([False, True])
        self.tasks_executed = 2
        self.tasks_failed = 0

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def schedule_task(self, task_id, func, priority, args):
        self.scheduled.append((task_id, priority, args))


@pytest.fixture
def no_parallel(monkeypatch):
    monkeypatch.setattr(p2, "CLUSTER_AVAILABLE", False)
    monkeypatch.setattr(p2, "EXECUTION_BACKBONE_AVAILABLE", False)


def _cfg(tmp_path):
    return SimpleNamespace(
        paths=SimpleNamespace(workspace_root=tmp_path, output_root=tmp_path / "out")
    )


def _write_phase1(tmp_path, files, iteration=1):
    d = tmp_path / "out" / f"iteration_{iteration}" / "phase1_define"
    d.mkdir(parents=True, exist_ok=True)
    (d / "phase1_define.json").write_text(json.dumps({"files": files}), "utf-8")


def _py(tmp_path, name, body):
    p = tmp_path / name
    p.write_bytes(body.encode("utf-8"))
    return str(p)


def test_analyze_python_file_metrics(tmp_path, no_parallel):
    ph = p2.Phase2Measure(_cfg(tmp_path), None)
    res = ph.analyze_python_file(_py(tmp_path, "s.py", SAMPLE))
    assert res["success"] is True
    m = res["metrics"]
    assert m["comment_lines"] == 1
    assert m["functions"] == 2
    assert m["classes"] == 1
    assert m["imports"] == 5
    assert m["lines_of_code"] == 9
    assert m["complexity_score"] == 9 + 2 * 2 + 3 + 5
    assert "" in res["details"]["imports"]
    assert res["details"]["functions"][0]["args"] in (2, 3)


def test_analyze_python_file_syntax_error_and_missing(tmp_path, no_parallel):
    ph = p2.Phase2Measure(_cfg(tmp_path), None)
    bad = ph.analyze_python_file(_py(tmp_path, "bad.py", "def (:\n"))
    assert bad["success"] is False
    assert bad["error"].startswith("Syntax error")
    assert bad["metrics"]["total_lines"] == 2
    missing = ph.analyze_python_file(str(tmp_path / "nope.py"))
    assert missing["success"] is False
    assert "metrics" not in missing


def test_init_flags_disabled(tmp_path, no_parallel):
    ph = p2.Phase2Measure(_cfg(tmp_path), None, use_keb=True, use_12cluster=True)
    assert ph.use_execution_backbone is False
    assert ph.use_12cluster is False
    assert ph.cluster_orchestrator is None
    assert ph.execution_backbone is None


def test_run_missing_phase1_returns_failure(tmp_path, no_parallel):
    ok, res = p2.Phase2Measure(_cfg(tmp_path), None).run(1)
    assert ok is False
    assert "Phase 1 results not found" in res["error"]
    assert res["measurements"] == []


def test_run_sequential_mode(tmp_path, no_parallel):
    good = _py(tmp_path, "good.py", SAMPLE)
    bad = _py(tmp_path, "bad.py", "def (:\n")
    _write_phase1(tmp_path, [good, bad, "readme.md"])
    ph = p2.Phase2Measure(_cfg(tmp_path), None)
    ok, res = ph.execute(1)
    assert ok is True
    st = res["statistics"]
    assert st["total_files"] == 2
    assert st["analyzed_successfully"] == 1
    assert st["analysis_errors"] == 1
    assert st["total_functions"] == 2
    assert st["total_classes"] == 1
    assert set(res["file_metrics"]) == {good, bad}
    it = tmp_path / "out" / "iteration_1"
    assert (it / "phase2_measure" / "phase2_measure.json").exists()
    assert json.loads((it / "phase2_metrics.json").read_text("utf-8"))["phase"] == (
        "MEASURE"
    )


def test_run_sequential_progress_message(tmp_path, no_parallel, capsys):
    paths = [_py(tmp_path, f"m{i}.py", "x = 1\n") for i in range(101)]
    _write_phase1(tmp_path, paths)
    ok, res = p2.Phase2Measure(_cfg(tmp_path), None).run(1)
    assert ok is True
    assert res["statistics"]["analyzed_successfully"] == 101
    assert "Analyzed 100/101 files in chunk" in capsys.readouterr().out


def test_run_cluster_mode_prefers_cluster_results(tmp_path, monkeypatch):
    monkeypatch.setattr(p2, "CLUSTER_AVAILABLE", True)
    monkeypatch.setattr(p2, "TwelveClusterOrchestrator", FakeCluster)
    a = _py(tmp_path, "a.py", SAMPLE)
    b = _py(tmp_path, "b.py", "y = 2\n")
    c = _py(tmp_path, "c.py", "z = 3\n")
    _write_phase1(tmp_path, [a, b, c], iteration=4)
    ph = p2.Phase2Measure(_cfg(tmp_path), None)
    assert isinstance(ph.cluster_orchestrator, FakeCluster)
    assert ph.cluster_orchestrator.kwargs["use_gbogeb"] is True
    ph.cluster_orchestrator.response = {
        "tasks_executed": 1,
        "results_map": {a: {"success": False, "error": "remote"}},
    }

    real = ph.analyze_python_file

    def flaky(path):
        if path == c:
            raise RuntimeError("worker died")
        return real(path)

    monkeypatch.setattr(ph, "analyze_python_file", flaky)
    ok, res = ph.run(4)
    assert ok is True
    phase, tasks, iteration = ph.cluster_orchestrator.calls[0]
    assert (phase, iteration, len(tasks)) == ("phase2", 4, 3)
    assert res["file_metrics"][a]["error"] == "remote"
    assert res["file_metrics"][b]["success"] is True
    assert res["file_metrics"][c] == {"success": False, "error": "worker died"}
    assert res["statistics"]["analyzed_successfully"] == 1
    assert res["statistics"]["analysis_errors"] == 2


def test_run_execution_backbone_mode(tmp_path, monkeypatch):
    monkeypatch.setattr(p2, "CLUSTER_AVAILABLE", False)
    monkeypatch.setattr(p2, "EXECUTION_BACKBONE_AVAILABLE", True)
    monkeypatch.setattr(p2, "ExecutionBackbone", FakeBackbone, raising=False)
    sleeps = []
    monkeypatch.setattr("time.sleep", sleeps.append)
    a = _py(tmp_path, "a.py", SAMPLE)
    bad = _py(tmp_path, "bad.py", "def (:\n")
    _write_phase1(tmp_path, [a, bad])
    ph = p2.Phase2Measure(_cfg(tmp_path), None, use_keb=True)
    bb = ph.execution_backbone
    assert bb.kwargs == {"max_workers": 2, "max_memory_mb": 2048}
    ok, res = ph.run(1)
    assert ok is True
    assert bb.started and bb.stopped
    assert len(bb.scheduled) == 2
    assert all(t[0].startswith("analyze_0_") for t in bb.scheduled)
    assert sleeps == [0.5, 2]
    assert res["statistics"]["analyzed_successfully"] == 1
    assert res["statistics"]["analysis_errors"] == 1


def test_execute_unwraps_nested_tuple(tmp_path, no_parallel, monkeypatch):
    ph = p2.Phase2Measure(_cfg(tmp_path), None)
    monkeypatch.setattr(ph, "run", lambda iteration: (True, (False, {"x": 1})))
    assert ph.execute(1) == (False, {"x": 1})
    monkeypatch.setattr(ph, "run", lambda iteration: (True, {"y": 2}))
    assert ph.execute(1) == (True, {"y": 2})
