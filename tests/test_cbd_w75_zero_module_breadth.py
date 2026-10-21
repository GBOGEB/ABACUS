"""CBD W75: real behavioural coverage for ten previously zero-covered sources.

Source cohort: ABACUS exact-main 7e9564f955dc00de23a7fba446d776e076758a8e.
Historical baseline from broad-coverage-ranking artifact 12316426500:
71/415 source files had zero covered statements. These tests propose a reduction;
only a fresh exact-head coverage artifact can establish any measured delta.

All fixtures run in tmp_path or memory. No deployment, network, provider,
bidder input, merge action, policy change, or security waiver is permitted.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
AGENTS = Path("DMAIC_V3/agents")


def source_module(relative: Path | str):
    path = ROOT / relative
    name = "w75_" + "_".join(path.relative_to(ROOT).with_suffix("").parts)
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def agent(name: str):
    return source_module(AGENTS / (name + ".py"))


def test_framework_detects_all_and_empty_project(tmp_path):
    m = agent("framework")
    a = m.FrameworkAgent(tmp_path)
    assert a.detect_frameworks() == {"python": [], "javascript": [], "build_tools": []}
    for name in ("requirements.txt", "setup.py", "pyproject.toml", "package.json"):
        (tmp_path / name).write_text("", encoding="utf-8")
    assert a.detect_frameworks() == {
        "python": ["pip", "setuptools", "poetry"],
        "javascript": ["npm"], "build_tools": [],
    }
    assert a.get_info()["status"] == "active"


def test_style_extractor_positive_missing_and_malformed(tmp_path):
    m = agent("style_extractor")
    a = m.StyleExtractorAgent(tmp_path)
    good = tmp_path / "source.py"
    good.write_text('class A:\n    """Documentation."""\n    def f(self):\n        return 1\n')
    assert a.extract_style(good)["has_docstrings"] is True
    good.write_text("def f():\n    return 1\n")
    assert a.extract_style(good)["has_docstrings"] is False
    good.write_text("def not valid ?\n")
    assert a.extract_style(good) == {}
    assert a.extract_style(tmp_path / "absent.py") == {}
    assert a.get_info()["name"] == "style_extractor"


def test_dependency_graph_imports_importfrom_nonpython_and_syntax(tmp_path):
    m = agent("dependency_graph")
    a = m.DependencyGraphAgent(tmp_path)
    good = tmp_path / "ok.py"
    good.write_text("import os, sys\nfrom pathlib import Path\nfrom . import local\n")
    malformed = tmp_path / "bad.py"
    malformed.write_text("this is python ???")
    missing = tmp_path / "missing.py"
    ignored = tmp_path / "file.txt"
    ignored.write_text("import pathlib")
    result = a.build_graph([good, malformed, missing, ignored])
    assert result == {str(good): ["os", "sys", "pathlib"]}
    assert a.build_graph([]) == {}
    assert a.get_info()["version"] == "3.3.0"


def test_context_manager_roundtrip_missing_and_corrupt_file(tmp_path):
    m = agent("context_manager")
    a = m.ContextManagerAgent(tmp_path)
    assert a.load_context() == {}
    assert a.save_context({"cycle": 2, "notes": ["local", "synthetic"]}) == {
        "success": True
    }
    assert a.load_context() == {"cycle": 2, "notes": ["local", "synthetic"]}
    a.context_file.write_text("{broken", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        a.load_context()
    assert a.get_info()["name"] == "context_manager"


def test_iteration_tracker_empty_append_history_and_corruption(tmp_path):
    m = agent("iteration_tracker")
    a = m.IterationTrackerAgent(tmp_path)
    assert a.track_iteration(1, {"yield": 0.3})["iterations_tracked"] == 1
    assert a.track_iteration(2, {"yield": 0.7})["iterations_tracked"] == 2
    history = json.loads(a.metrics_file.read_text(encoding="utf-8"))
    assert [r["iteration"] for r in history] == [1, 2]
    assert all("timestamp" in r for r in history)
    a.metrics_file.write_text("invalid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        a.track_iteration(3, {"yield": 0.8})
    assert a.get_info()["status"] == "active"


def test_performance_tracker_guard_two_runs_and_reset(tmp_path):
    m = agent("performance_tracker")
    a = m.PerformanceTrackerAgent(tmp_path)
    assert a.stop_tracking("none") == {"error": "Tracking not started"}
    with mock.patch.object(m.time, "time", side_effect=[100.0, 102.5, 120.0, 125.0]):
        a.start_tracking()
        first = a.stop_tracking("define")
        assert first["duration_seconds"] == 2.5
        assert a.start_time is None
        a.start_tracking()
        second = a.stop_tracking("measure")
    assert second["duration_seconds"] == 5.0
    assert [r["phase"] for r in json.loads(a.perf_file.read_text())] == [
        "define", "measure"
    ]
    assert a.get_info()["name"] == "performance_tracker"


def test_performance_tracker_rejects_invalid_existing_history(tmp_path):
    m = agent("performance_tracker")
    a = m.PerformanceTrackerAgent(tmp_path)
    a.perf_file.parent.mkdir(parents=True, exist_ok=True)
    a.perf_file.write_text("{not-json", encoding="utf-8")
    with mock.patch.object(m.time, "time", side_effect=[2.0, 3.0]):
        a.start_tracking()
        with pytest.raises(json.JSONDecodeError):
            a.stop_tracking("measure")


def test_health_agent_isolated_psutil_and_info(tmp_path):
    psutil = types.ModuleType("psutil")
    psutil.cpu_percent = mock.Mock(return_value=17.0)
    psutil.virtual_memory = mock.Mock(return_value=types.SimpleNamespace(percent=29.0))
    psutil.disk_usage = mock.Mock(return_value=types.SimpleNamespace(percent=38.0))
    with mock.patch.dict(sys.modules, {"psutil": psutil}):
        m = agent("health_checker")
    a = m.HealthCheckerAgent(tmp_path)
    health = a.check_health()
    assert health["status"] == "healthy"
    assert (health["cpu_percent"], health["memory_percent"], health["disk_percent"]) == (
        17.0, 29.0, 38.0
    )
    assert "T" in health["timestamp"]
    psutil.cpu_percent.assert_called_once_with(interval=1)
    assert a.get_info()["name"] == "health_checker"


@pytest.mark.parametrize(
    "filename,expected_repo",
    [
        ("integration/cryoplant_project/src/federation.py", "GBOGEB/cryoplant-project"),
        ("integration/codespace_jyperter/src/federation.py", "GBOGEB/codespace_jyperter"),
    ],
)
@pytest.mark.parametrize(
    "manifest_present,spec_present,status",
    [(True, True, "ok"), (True, False, "degraded"),
     (False, True, "degraded"), (False, False, "error")],
)
def test_auxiliary_federation_source_exists_contract(
    tmp_path, filename, expected_repo, manifest_present, spec_present, status
):
    m = source_module(filename)
    manifest = tmp_path / "manifest.yaml"
    spec = tmp_path / "source.yaml"
    if manifest_present:
        manifest.write_text("test: synthetic\n", encoding="utf-8")
    if spec_present:
        spec.write_text("test: synthetic\n", encoding="utf-8")
    with (
        mock.patch.object(m, "_INTEGRATION_MANIFEST", manifest),
        mock.patch.object(m, "_FEDERATION_SPEC", spec),
    ):
        receipt = m.assimilate({"pulse": "W75"})
        assert m.assimilate(None)["context"] == {}
    assert receipt["status"] == status
    assert receipt["repo"] == expected_repo
    assert receipt["manifest_found"] is manifest_present
    assert receipt["spec_found"] is spec_present
    assert receipt["plane"] == "auxiliary"
    assert receipt["context"]["pulse"] == "W75"
    assert len(receipt["details"]) == 2


def test_product_version_source_and_installed_fallback(tmp_path):
    pytest.importorskip("tomllib")  # 3.11+: native stdlib used by the SUT
    m = source_module("DMAIC_V3/product_version.py")
    assert m.get_product_version() == m.ABACUS_VERSION
    project_file = tmp_path / "pyproject.toml"
    project_file.write_text('[project]\nversion = "6.1.2"\n', encoding="utf-8")
    with mock.patch.object(m, "_root", return_value=tmp_path):
        assert m.get_product_version() == "6.1.2"
        project_file.write_text("[project]\n", encoding="utf-8")
        with pytest.raises(RuntimeError, match="missing"):
            m.get_product_version()
        project_file.unlink()
        with mock.patch.object(m, "package_version", return_value="7.2.1"):
            assert m.get_product_version() == "7.2.1"
        with mock.patch.object(m, "package_version", return_value=""):
            with pytest.raises(RuntimeError, match="empty"):
                m.get_product_version()
        with mock.patch.object(m, "package_version", side_effect=PackageNotFoundError):
            with pytest.raises(RuntimeError, match="unavailable"):
                m.get_product_version()
