"""W76: source-blob-pinned recovery of seven previously zero-covered DMAIC agents.

These tests use local temporary directories and no deployment, network access,
GitHub mutation, or real CPU sampling. They intentionally exercise normal,
boundary, negative and reverse paths.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import tempfile
import types
import unittest
from datetime import datetime
import unittest.mock as mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
AGENTS = ROOT / "DMAIC_V3" / "agents"


def load(name):
    spec = importlib.util.spec_from_file_location(
        "w76_agent_" + name, AGENTS / (name + ".py"))
    if spec is None or spec.loader is None:
        raise AssertionError("missing source module " + name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class W76DMAICAgentCoverage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="w76-dmaic-")
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)

    def test_health_check_is_deterministic_under_mocked_resources(self):
        calls = []
        fake_psutil = types.ModuleType("psutil")
        fake_psutil.cpu_percent = lambda interval: (calls.append(interval), 24.5)[1]
        fake_psutil.virtual_memory = lambda: types.SimpleNamespace(percent=45.0)
        fake_psutil.disk_usage = lambda path: (
            calls.append(path), types.SimpleNamespace(percent=67.0))[1]
        with mock.patch.dict(sys.modules, {"psutil": fake_psutil}):
            m = load("health_checker")
        agent = m.HealthCheckerAgent(self.root)
        data = agent.check_health()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual((data["cpu_percent"], data["memory_percent"],
                          data["disk_percent"]), (24.5, 45.0, 67.0))
        self.assertEqual(calls, [1, "/"])
        datetime.fromisoformat(data["timestamp"])
        self.assertEqual(agent.get_info(),
                         {"name": "health_checker", "version": "3.3.0", "status": "active"})

    def test_health_percentages_are_observations_not_acceptance(self):
        fake = types.ModuleType("psutil")
        fake.cpu_percent = lambda interval: 100.0
        fake.virtual_memory = lambda: types.SimpleNamespace(percent=99.9)
        fake.disk_usage = lambda path: types.SimpleNamespace(percent=100.0)
        with mock.patch.dict(sys.modules, {"psutil": fake}):
            m = load("health_checker")
        data = m.HealthCheckerAgent(self.root).check_health()
        self.assertEqual(data["status"], "healthy")  # existing implementation; not a safety pass
        self.assertNotIn("merge_authorized", data)
        self.assertNotIn("security_waiver", data)

    def test_style_extractor_has_docstrings_and_valid_parse(self):
        m = load("style_extractor")
        p = self.root / "valid.py"
        p.write_text('class Engine:\n    """API contract."""\n    def run(self):\n        """Execute."""\n        return 1\n',
                     encoding="utf-8")
        agent = m.StyleExtractorAgent(self.root)
        got = agent.extract_style(p)
        self.assertEqual((got["indentation"], got["quotes"], got["line_length"]),
                         (4, "double", 100))
        self.assertTrue(got["has_docstrings"])
        self.assertEqual(agent.get_info()["name"], "style_extractor")

    def test_style_extractor_docstring_absent_negative(self):
        m = load("style_extractor")
        p = self.root / "no_doc.py"
        p.write_text("def f():\n    return 2\n", encoding="utf-8")
        self.assertFalse(m.StyleExtractorAgent(self.root).extract_style(p)["has_docstrings"])

    def test_style_extractor_rejects_syntax_missing_and_binary_input(self):
        agent = load("style_extractor").StyleExtractorAgent(self.root)
        bad = self.root / "invalid.py"
        bad.write_text("def broken(:\n", encoding="utf-8")
        binary = self.root / "invalid_utf8.py"
        binary.write_bytes(b"\xff\xfe")
        for path in (bad, binary, self.root / "absent.py"):
            with self.subTest(path=path.name):
                self.assertEqual(agent.extract_style(path), {})

    def test_framework_empty_and_all_detected_without_build_execution(self):
        m = load("framework")
        agent = m.FrameworkAgent(self.root)
        self.assertEqual(agent.detect_frameworks(),
                         {"python": [], "javascript": [], "build_tools": []})
        for name in ("requirements.txt", "setup.py", "pyproject.toml", "package.json"):
            (self.root / name).write_text("", encoding="utf-8")
        found = agent.detect_frameworks()
        self.assertEqual(found["python"], ["pip", "setuptools", "poetry"])
        self.assertEqual(found["javascript"], ["npm"])
        self.assertEqual(found["build_tools"], [])
        self.assertEqual(agent.get_info()["version"], "3.3.0")

    def test_framework_partial_presence_is_not_inferred(self):
        agent = load("framework").FrameworkAgent(self.root)
        (self.root / "setup.py").write_text("# intentionally empty\n")
        self.assertEqual(agent.detect_frameworks()["python"], ["setuptools"])
        self.assertEqual(agent.detect_frameworks()["javascript"], [])

    def test_context_manager_missing_then_roundtrip_and_overwrite(self):
        m = load("context_manager")
        agent = m.ContextManagerAgent(self.root)
        self.assertEqual(agent.load_context(), {})
        self.assertEqual(agent.save_context({"pulse": 1, "data": ["a", "b"]}),
                         {"success": True})
        self.assertEqual(agent.load_context(), {"pulse": 1, "data": ["a", "b"]})
        agent.save_context({"pulse": 2})
        self.assertEqual(agent.load_context(), {"pulse": 2})
        self.assertEqual(agent.get_info()["name"], "context_manager")
        self.assertTrue(agent.context_file.is_relative_to(self.root.resolve()))

    def test_context_manager_corrupt_json_fails_closed(self):
        agent = load("context_manager").ContextManagerAgent(self.root)
        agent.context_file.parent.mkdir(parents=True)
        agent.context_file.write_text("{invalid", encoding="utf-8")
        with self.assertRaises(json.JSONDecodeError):
            agent.load_context()
        self.assertEqual(agent.context_file.read_text(), "{invalid")

    def test_iteration_tracker_one_then_many_in_same_workspace(self):
        m = load("iteration_tracker")
        agent = m.IterationTrackerAgent(self.root)
        self.assertEqual(agent.track_iteration(1, {"yield": 0.5})["iterations_tracked"], 1)
        self.assertEqual(agent.track_iteration(2, {"yield": 0.9})["iterations_tracked"], 2)
        series = json.loads(agent.metrics_file.read_text(encoding="utf-8"))
        self.assertEqual([row["iteration"] for row in series], [1, 2])
        self.assertEqual([row["metrics"]["yield"] for row in series], [0.5, 0.9])
        for row in series:
            datetime.fromisoformat(row["timestamp"])
        self.assertEqual(agent.get_info()["name"], "iteration_tracker")

    def test_iteration_tracker_invalid_history_must_not_be_overwritten(self):
        agent = load("iteration_tracker").IterationTrackerAgent(self.root)
        agent.metrics_file.parent.mkdir(parents=True)
        agent.metrics_file.write_text("INVALID JSON", encoding="utf-8")
        with self.assertRaises(json.JSONDecodeError):
            agent.track_iteration(2, {"a": 1})
        self.assertEqual(agent.metrics_file.read_text(), "INVALID JSON")

    def test_dependency_graph_imports_from_nested_ast(self):
        m = load("dependency_graph")
        agent = m.DependencyGraphAgent(self.root)
        source = self.root / "good.py"
        source.write_text("import os, sys\nfrom pathlib import Path\n"
                          "def inner():\n    from collections import deque\n"
                          "    import json\n    return deque()\n", encoding="utf-8")
        graph = agent.build_graph([source])
        self.assertEqual(graph[str(source)], ["os", "sys", "pathlib", "collections", "json"])
        self.assertEqual(agent.get_info()["name"], "dependency_graph")

    def test_dependency_graph_filters_nonpython_and_parse_errors(self):
        agent = load("dependency_graph").DependencyGraphAgent(self.root)
        skipped = self.root / "ignored.txt"
        skipped.write_text("import os")
        bad = self.root / "invalid.py"
        bad.write_text("def x(:", encoding="utf-8")
        missing = self.root / "missing.py"
        invalid_utf8 = self.root / "invalid_utf8.py"
        invalid_utf8.write_bytes(b"\xff")
        good = self.root / "blank.py"
        good.write_text("x = 1\n", encoding="utf-8")
        with self.assertLogs(level="WARNING") as logged:
            graph = agent.build_graph([skipped, bad, missing, invalid_utf8, good])
        self.assertEqual(graph, {str(good): []})
        self.assertEqual(len(logged.records), 3)
        self.assertTrue(all("Skipping dependency parsing" in e.getMessage()
                            for e in logged.records))

    def test_dependency_graph_relative_from_and_ignored_path(self):
        agent = load("dependency_graph").DependencyGraphAgent(self.root)
        source = self.root / "relative.py"
        source.write_text("from . import local\nfrom .helpers import tool\n")
        graph = agent.build_graph([source])
        self.assertEqual(graph[str(source)], ["helpers"])
        self.assertEqual(agent.build_graph([]), {})

    def test_performance_tracker_stop_without_start_is_explicit_error(self):
        m = load("performance_tracker")
        agent = m.PerformanceTrackerAgent(self.root)
        self.assertEqual(agent.stop_tracking("phase"), {"error": "Tracking not started"})
        self.assertFalse(agent.perf_file.exists())
        self.assertEqual(agent.get_info()["name"], "performance_tracker")

    def test_performance_tracker_measured_duration_and_reentrant_stop(self):
        m = load("performance_tracker")
        timer = types.SimpleNamespace(time=mock.Mock(side_effect=[10.0, 13.25]))
        with mock.patch.object(m, "time", timer):
            agent = m.PerformanceTrackerAgent(self.root)
            agent.start_tracking()
            result = agent.stop_tracking("DMAIC:CONTROL")
        self.assertEqual(result["duration_seconds"], 3.25)
        self.assertEqual(result["phase"], "DMAIC:CONTROL")
        self.assertEqual(agent.stop_tracking("again"), {"error": "Tracking not started"})
        history = json.loads(agent.perf_file.read_text(encoding="utf-8"))
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["duration_seconds"], 3.25)
        datetime.fromisoformat(history[0]["timestamp"])

    def test_performance_tracker_append_history_and_invalid_json(self):
        m = load("performance_tracker")
        agent = m.PerformanceTrackerAgent(self.root)
        with mock.patch.object(m, "time", types.SimpleNamespace(
                time=mock.Mock(side_effect=[1.0, 2.0, 3.0, 5.0]))):
            agent.start_tracking()
            agent.stop_tracking("P1")
            agent.start_tracking()
            agent.stop_tracking("P2")
        self.assertEqual(len(json.loads(agent.perf_file.read_text())), 2)
        agent.perf_file.write_text("not json")
        agent.start_tracking()
        with self.assertRaises(json.JSONDecodeError):
            agent.stop_tracking("P3")
        self.assertEqual(agent.perf_file.read_text(), "not json")


if __name__ == "__main__":
    unittest.main()
