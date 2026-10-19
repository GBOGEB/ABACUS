"""P41-L2: test real local tracking-state behavior, denying GitHub/install side effects."""

import importlib.util
import sys
import types
from pathlib import Path


def isolated_source(monkeypatch):
    github = types.ModuleType("github")
    class DenyNetwork:
        def __init__(self, *args, **kwargs):
            raise AssertionError("remote authentication is forbidden")
    github.Github = DenyNetwork
    monkeypatch.setitem(sys.modules, "github", github)
    path = Path(__file__).resolve().parents[1] / "github_tracking_manager.py"
    spec = importlib.util.spec_from_file_location("p41_tracking_manager", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.GitHubTrackingManager


def test_empty_state_is_structurally_complete_and_disjoint(monkeypatch):
    cls = isolated_source(monkeypatch)
    one, two = object.__new__(cls), object.__new__(cls)
    one.repo_name = two.repo_name = "GBOGEB/ABACUS"
    left, right = one._create_empty_state(), two._create_empty_state()
    assert left["pull_requests"] == {}
    assert left["ci_cd_history"]["ci_runs"] == []
    assert left["action_items"] == []
    assert left["metadata"]["repository"] == "GBOGEB/ABACUS"
    left["action_items"].append({"id": "only-left"})
    assert right["action_items"] == []


def test_missing_local_state_loads_empty_not_network(monkeypatch, tmp_path):
    cls = isolated_source(monkeypatch)
    manager = object.__new__(cls)
    manager.repo_name = "GBOGEB/ABACUS"
    manager.json_file = tmp_path / "never-created.json"
    state = manager._load_state()
    assert state["pull_requests"] == {}
    assert state["ci_cd_history"]["missed_opportunities"] == []


def test_existing_local_state_loads_exact_json(monkeypatch, tmp_path):
    cls = isolated_source(monkeypatch)
    manager = object.__new__(cls)
    manager.repo_name = "GBOGEB/ABACUS"
    manager.json_file = tmp_path / "local.json"
    manager.json_file.write_text(
        '{"metadata":{"repository":"GBOGEB/ABACUS"},"action_items":[{"id":"x"}]}',
        encoding="utf-8",
    )
    assert manager._load_state()["action_items"] == [{"id": "x"}]
