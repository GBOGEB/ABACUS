"""Lane-B wave 12: tools_v2.3 code index generator and task tracker."""

import json

import pytest
import yaml

from ._l2_loader import load

cig = load("tools_v2.3/code_index_generator_v2.3.py")
tt = load("tools_v2.3/task_tracker_v2.3_20251111.py")


# ---------------------------------------------------------------------------
# code_index_generator_v2.3
# ---------------------------------------------------------------------------

AGENT_SRC = (
    '__version__ = "1.2.3"\n'
    "obj.attr = 1\n"
    "class Alpha:\n"
    "    pass\n"
    "class Beta:\n"
    "    pass\n"
    "def helper():\n"
    "    return 1\n"
)


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _repo(tmp_path):
    agents = tmp_path / "local_mcp" / "agents"
    _write(agents / "alpha_agent_v2.3_OPTIMIZED.py", AGENT_SRC)
    _write(agents / "stub_agent_v2.3.py", "# STUB - Needs implementation\n")
    _write(agents / "plain_agent.py", "__version__ = VERSION\nX = 1\n")
    _write(agents / "_private.py", "x = 1\n")
    _write(agents / "notes.txt", "ignored")
    _write(
        tmp_path / "tools_v2.3" / "tool_v2.3_20251111.py", "VERSION = '0.0.0-stub'\n"
    )
    return agents


@pytest.mark.parametrize(
    "src, expected",
    [
        (AGENT_SRC, "1.2.3"),
        ("__version__ = VERSION\n", "unknown"),
        ("x, y = 1, 2\n", "unknown"),
        ("def broken(:\n", "unknown"),
        ("", "unknown"),
    ],
)
def test_extract_version(tmp_path, src, expected):
    assert cig._extract_version(_write(tmp_path / "m.py", src)) == expected


def test_extract_classes_and_stub(tmp_path):
    good = _write(tmp_path / "m.py", AGENT_SRC)
    assert cig._extract_classes(good) == ["Alpha", "Beta"]
    assert cig._is_stub(good) is False
    bad = _write(tmp_path / "bad.py", "class (:\n")
    assert cig._extract_classes(bad) == []
    assert cig._is_stub(_write(tmp_path / "s.py", "v = '0.0.0-stub'\n")) is True


def test_helpers_swallow_unreadable_path(tmp_path):
    folder = tmp_path / "folder.py"
    folder.mkdir()
    assert cig._extract_version(folder) == "unknown"
    assert cig._extract_classes(folder) == []
    assert cig._is_stub(folder) is False


def test_scan_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(cig, "_REPO_ROOT", tmp_path)
    agents = _repo(tmp_path)
    assert cig.scan_directory(tmp_path / "missing", "agent") == []
    found = cig.scan_directory(agents, "agent")
    assert [c["name"] for c in found] == ["alpha_agent", "plain_agent", "stub_agent"]
    alpha, plain, stub = found
    assert alpha["v2.3"] is True and alpha["version"] == "1.2.3"
    assert alpha["classes"] == ["Alpha", "Beta"]
    assert alpha["status"] == "active"
    assert alpha["file"].replace("\\", "/") == (
        "local_mcp/agents/alpha_agent_v2.3_OPTIMIZED.py"
    )
    assert plain["v2.3"] is False and plain["version"] == "unknown"
    assert stub["stub"] is True and stub["status"] == "stub"


def test_generate_index_without_orchestrator(tmp_path, monkeypatch):
    monkeypatch.setattr(cig, "_REPO_ROOT", tmp_path)
    _repo(tmp_path)
    index = cig.generate_index()
    assert index["summary"] == {
        "total_agents": 3,
        "v2.3_agents": 1,
        "stub_agents": 1,
        "total_tools": 1,
        "orchestrator_present": False,
    }
    assert index["orchestrator"] is None
    assert index["tools"][0]["name"] == "tool"
    assert index["tools"][0]["stub"] is True
    assert index["meta"]["version"] == cig.__version__


def test_generate_index_with_orchestrator(tmp_path, monkeypatch):
    monkeypatch.setattr(cig, "_REPO_ROOT", tmp_path)
    _write(tmp_path / "local_mcp" / "agent_orchestrator_v3.0.py", AGENT_SRC)
    index = cig.generate_index()
    orch = index["orchestrator"]
    assert orch["version"] == "1.2.3" and orch["v3.0"] is True
    assert orch["classes"] == ["Alpha", "Beta"] and orch["stub"] is False
    assert index["summary"]["orchestrator_present"] is True
    assert index["summary"]["total_agents"] == 0


def test_main_writes_json_and_yaml(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cig, "_REPO_ROOT", tmp_path)
    _repo(tmp_path)
    out_json = tmp_path / "out" / "index.json"
    out_yaml = tmp_path / "out" / "index.yaml"
    out_json.parent.mkdir()
    argv = ["--output-json", str(out_json), "--output-yaml", str(out_yaml)]
    assert cig.main(argv + ["--stdout"]) == 0
    printed = capsys.readouterr().out
    assert "Agents scanned  : 3 (1 v2.3, 1 stubs)" in printed
    assert "Orchestrator    : missing" in printed
    assert '"total_tools": 1' in printed
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["summary"]["total_agents"] == 3
    assert yaml.safe_load(out_yaml.read_text(encoding="utf-8"))["summary"] == (
        data["summary"]
    )


def test_main_orchestrator_present_no_stdout(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cig, "_REPO_ROOT", tmp_path)
    _write(tmp_path / "local_mcp" / "agent_orchestrator_v3.0.py", AGENT_SRC)
    argv = ["--output-json", str(tmp_path / "i.json")]
    assert cig.main(argv + ["--output-yaml", str(tmp_path / "i.yaml")]) == 0
    printed = capsys.readouterr().out
    assert "Orchestrator    : present" in printed
    assert '"agents"' not in printed


def test_write_yaml_without_pyyaml(tmp_path, capsys):
    no_yaml = load(
        "tools_v2.3/code_index_generator_v2.3.py",
        name="l2_w12_cig_no_yaml",
        deps={"yaml": None},
    )
    assert no_yaml._HAS_YAML is False
    out = tmp_path / "x.yaml"
    no_yaml.write_yaml({"a": 1}, out)
    assert not out.exists()
    assert "pyyaml not installed" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# task_tracker_v2.3_20251111
# ---------------------------------------------------------------------------


def test_tracker_default_db_and_empty(tmp_path):
    assert tt.TaskTrackerV23().db_path == tt._DEFAULT_DB
    tracker = tt.TaskTrackerV23(tmp_path / "db" / "tasks.json")
    assert tracker.list_tasks() == []
    assert tracker.get_summary() == {
        "total": 0,
        "completed": 0,
        "progress_pct": 0.0,
        "by_status": {s: 0 for s in tt._STATUSES},
        "version": tt.__version__,
    }


def test_tracker_add_update_and_summary(tmp_path):
    db = tmp_path / "db" / "tasks.json"
    tracker = tt.TaskTrackerV23(str(db))
    task = tracker.add_task("T-1", "One", "Define", priority=1, description="d")
    assert task["status"] == "pending" and task["completed_at"] is None
    tracker.add_task("T-2", "Two", "Measure")
    with pytest.raises(ValueError, match="already exists"):
        tracker.add_task("T-1", "Dup", "Define")
    done = tracker.update_status("T-1", "completed")
    assert done["completed_at"] is not None
    assert [t["id"] for t in tracker.list_tasks("completed")] == ["T-1"]
    reopened = tracker.update_status("T-1", "blocked")
    assert reopened["completed_at"] is None
    tracker.update_status("T-2", "completed")
    stored = json.loads(db.read_text(encoding="utf-8"))
    assert stored["last_updated"] is not None
    stored["tasks"].append({"id": "T-3", "status": "legacy"})
    stored["tasks"].append({"id": "T-4"})
    db.write_text(json.dumps(stored), encoding="utf-8")
    summary = tracker.get_summary()
    assert summary["total"] == 4 and summary["completed"] == 1
    assert summary["progress_pct"] == 25.0
    assert summary["by_status"]["legacy"] == 1
    assert summary["by_status"]["pending"] == 1
    assert summary["by_status"]["blocked"] == 1


def test_tracker_update_rejections(tmp_path):
    tracker = tt.TaskTrackerV23(tmp_path / "t.json")
    with pytest.raises(ValueError, match="Invalid status 'done'"):
        tracker.update_status("T-1", "done")
    with pytest.raises(KeyError, match="T-9"):
        tracker.update_status("T-9", "completed")


def test_find_task():
    tasks = [{"id": "a"}, {"id": "b"}]
    assert tt._find_task(tasks, "b") == {"id": "b"}
    assert tt._find_task(tasks, "z") is None


def test_cli_flow(tmp_path, capsys):
    db = ["--db", str(tmp_path / "tasks.json")]
    assert tt.main(db) == 0
    assert "No tasks found." in capsys.readouterr().out
    assert tt.main(db + ["add", "T-1", "Title", "Improve", "--priority", "2"]) == 0
    assert "Added task: T-1" in capsys.readouterr().out
    assert tt.main(db + ["list"]) == 0
    assert "[PENDING   ] T-1 | P2 | Title" in capsys.readouterr().out
    assert tt.main(db + ["update", "T-1", "completed"]) == 0
    assert "Updated T-1" in capsys.readouterr().out
    assert tt.main(db + ["summary"]) == 0
    out = capsys.readouterr().out
    assert "Total tasks : 1" in out and "Progress    : 100.0%" in out
    assert "  completed   : 1" in out


def test_cli_unknown_command_prints_help(tmp_path, monkeypatch, capsys):
    original = tt._build_parser

    def build():
        parser = original()
        for action in parser._actions:
            if isinstance(action, tt.argparse._SubParsersAction):
                action.add_parser("noop")
        return parser

    monkeypatch.setattr(tt, "_build_parser", build)
    assert tt.main(["--db", str(tmp_path / "t.json"), "noop"]) == 1
    assert "Task Tracker V2.3" in capsys.readouterr().out
