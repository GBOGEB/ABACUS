"""W52: exercise seven native DMAIC agents that were zero-covered in B0.

These are functional tests, not an import-only coverage inflation. All files
and external measurements are isolated under tmp_path or mocked.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

AGENTS = Path(__file__).resolve().parents[1] / "DMAIC_V3" / "agents"
_FAKE_PSUTIL = SimpleNamespace(
    cpu_percent=lambda interval: 12.5,
    virtual_memory=lambda: SimpleNamespace(percent=45.0),
    disk_usage=lambda path: SimpleNamespace(percent=60.0),
)


def _agent(name: str):
    spec = importlib.util.spec_from_file_location(
        f"w52_agent_{name}", AGENTS / f"{name}.py"
    )
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load source-owned agent: {name}")
    module = importlib.util.module_from_spec(spec)
    # The health-checker test does not depend on host sensors or psutil setup.
    with patch.dict(sys.modules, {"psutil": _FAKE_PSUTIL}):
        spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("name", "class_name"),
    [
        ("context_manager", "ContextManagerAgent"),
        ("health_checker", "HealthCheckerAgent"),
        ("iteration_tracker", "IterationTrackerAgent"),
        ("style_extractor", "StyleExtractorAgent"),
        ("dependency_graph", "DependencyGraphAgent"),
        ("framework", "FrameworkAgent"),
        ("performance_tracker", "PerformanceTrackerAgent"),
    ],
)
def test_agent_declared_identity_is_source_owned(tmp_path, name, class_name):
    agent = getattr(_agent(name), class_name)(tmp_path)
    assert agent.get_info() == {
        "name": name,
        "version": "3.3.0",
        "status": "active",
    }


def test_context_manager_missing_then_persistent_and_corrupted(tmp_path):
    module = _agent("context_manager")
    agent = module.ContextManagerAgent(tmp_path)
    assert agent.load_context() == {}
    assert agent.save_context({"lane": "test", "value": [1, 2]}) == {
        "success": True
    }
    assert agent.load_context() == {"lane": "test", "value": [1, 2]}
    agent.context_file.write_text("{corrupt", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        agent.load_context()


def test_iteration_tracker_preserves_two_real_records_and_denies_bad_json(tmp_path):
    module = _agent("iteration_tracker")
    agent = module.IterationTrackerAgent(tmp_path)
    assert agent.track_iteration(1, {"passed": 1})["iterations_tracked"] == 1
    assert agent.track_iteration(2, {"passed": 2})["iterations_tracked"] == 2
    rows = json.loads(agent.metrics_file.read_text(encoding="utf-8"))
    assert [row["iteration"] for row in rows] == [1, 2]
    assert [row["metrics"]["passed"] for row in rows] == [1, 2]
    assert all(row["timestamp"] for row in rows)
    agent.metrics_file.write_text("not-json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        agent.track_iteration(3, {"passed": 3})


def test_style_extractor_accepts_python_and_rejects_invalid_sources(tmp_path):
    module = _agent("style_extractor")
    agent = module.StyleExtractorAgent(tmp_path)
    valid = tmp_path / "good.py"
    valid.write_text(
        'def documented():\n    """documented function"""\n    return 42\n',
        encoding="utf-8",
    )
    style = agent.extract_style(valid)
    assert style["indentation"] == 4
    assert style["line_length"] == 100
    assert style["has_docstrings"] is True

    invalid = tmp_path / "bad.py"
    invalid.write_text("def broken(:\n", encoding="utf-8")
    assert agent.extract_style(invalid) == {}
    assert agent.extract_style(tmp_path / "missing.py") == {}


def test_dependency_graph_reads_imports_and_skips_unparseable_files(tmp_path):
    module = _agent("dependency_graph")
    agent = module.DependencyGraphAgent(tmp_path)
    source = tmp_path / "good.py"
    source.write_text(
        "import os, json\nfrom pathlib import Path\n", encoding="utf-8"
    )
    broken = tmp_path / "broken.py"
    broken.write_text("def invalid(:\n", encoding="utf-8")
    ignored = tmp_path / "notes.txt"
    ignored.write_text("import fake\n", encoding="utf-8")
    graph = agent.build_graph(
        [source, broken, ignored, tmp_path / "missing.py"]
    )
    assert set(graph[str(source)]) == {"os", "json", "pathlib"}
    assert set(graph) == {str(source)}


def test_framework_detector_positive_and_negative_file_matrix(tmp_path):
    module = _agent("framework")
    agent = module.FrameworkAgent(tmp_path)
    assert agent.detect_frameworks() == {
        "python": [],
        "javascript": [],
        "build_tools": [],
    }
    for name in ("requirements.txt", "setup.py", "pyproject.toml", "package.json"):
        (tmp_path / name).write_text("synthetic", encoding="utf-8")
    found = agent.detect_frameworks()
    assert found["python"] == ["pip", "setuptools", "poetry"]
    assert found["javascript"] == ["npm"]
    assert found["build_tools"] == []


def test_performance_tracker_unstarted_timed_and_bad_history(tmp_path):
    module = _agent("performance_tracker")
    agent = module.PerformanceTrackerAgent(tmp_path)
    assert agent.stop_tracking("never") == {"error": "Tracking not started"}
    with patch.object(module.time, "time", side_effect=[100.0, 101.25]):
        agent.start_tracking()
        result = agent.stop_tracking("measure")
    assert result["phase"] == "measure"
    assert result["duration_seconds"] == pytest.approx(1.25)
    assert agent.start_time is None
    rows = json.loads(agent.perf_file.read_text(encoding="utf-8"))
    assert len(rows) == 1 and rows[0]["phase"] == "measure"

    agent.perf_file.write_text("bad-json", encoding="utf-8")
    agent.start_tracking()
    with pytest.raises(json.JSONDecodeError):
        agent.stop_tracking("invalid-history")


def test_health_checker_uses_controlled_sensor_bytes_not_host_sensors(tmp_path):
    module = _agent("health_checker")
    agent = module.HealthCheckerAgent(tmp_path)
    values = agent.check_health()
    assert values["cpu_percent"] == 12.5
    assert values["memory_percent"] == 45.0
    assert values["disk_percent"] == 60.0
    assert values["status"] == "healthy"
    assert values["timestamp"]

    with patch.object(module.psutil, "cpu_percent", side_effect=RuntimeError("offline")):
        with pytest.raises(RuntimeError, match="offline"):
            agent.check_health()
