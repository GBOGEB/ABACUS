"""P41-L1: run the real workflow analyzer with a fake PyGithub transport.

Never install a package on import, call the network, or dispatch a workflow.
"""

import importlib.util
import sys
import types
from pathlib import Path


def load_source(monkeypatch):
    github = types.ModuleType("github")
    class DenyNetwork:
        def __init__(self, *a, **kw):
            raise AssertionError("network authentication is prohibited in test")
    github.Github = DenyNetwork
    monkeypatch.setitem(sys.modules, "github", github)
    source = Path(__file__).resolve().parents[1] / "workflow_analyzer.py"
    spec = importlib.util.spec_from_file_location("p41_workflow_analyzer", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.WorkflowAnalyzer


def analyzer_without_network(cls):
    instance = object.__new__(cls)
    instance.repo_name = "GBOGEB/ABACUS"
    return instance


def test_failure_rate_counts_only_failed_runs(monkeypatch):
    cls = load_source(monkeypatch)
    analyzer = analyzer_without_network(cls)
    observations = [
        {"conclusion": "failure", "name": "B0", "head_branch": "main"},
        {"conclusion": "cancelled", "name": "Matrix", "head_branch": "old"},
        {"conclusion": "success", "name": "B0", "head_branch": "main"},
    ]
    result = analyzer.analyze_failure_patterns(observations)
    assert result["total_runs"] == 3
    assert result["total_failures"] == 1
    assert result["failures_by_workflow"] == {"B0": 1}
    assert result["failure_rate"] == 100 / 3


def test_empty_run_population_is_not_one_failed_run(monkeypatch):
    cls = load_source(monkeypatch)
    analyzer = analyzer_without_network(cls)
    result = analyzer.analyze_failure_patterns([])
    assert result["total_runs"] == 0
    assert result["total_failures"] == 0
    assert result["failure_rate"] == 0
    assert result["most_failing_workflow"] is None


def test_missing_test_and_cd_detection_uses_real_source(monkeypatch):
    cls = load_source(monkeypatch)
    analyzer = analyzer_without_network(cls)
    runs = [{
        "name": "Lint", "conclusion": "success",
        "status": "completed", "event": "push",
    }]
    result = analyzer.identify_missed_opportunities(runs)
    kinds = {row["type"] for row in result}
    assert "missing_tests" in kinds
    assert "missing_cd" in kinds
    assert "insufficient_pr_checks" in kinds
