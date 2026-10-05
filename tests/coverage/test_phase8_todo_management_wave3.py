from __future__ import annotations

from types import SimpleNamespace

from DMAIC_V3.phases.phase8_todo_management import Phase8TODOManagement


def _phase(tmp_path):
    phase = object.__new__(Phase8TODOManagement)
    phase.config = SimpleNamespace(workspace_root=str(tmp_path))
    return phase


def test_parse_todo_files_reads_yaml_list_and_markdown(tmp_path):
    (tmp_path / "TODO_items.yaml").write_text(
        "- description: yaml task\n  priority: high\n",
        encoding="utf-8",
    )
    (tmp_path / "TODO_notes.md").write_text(
        "- [ ] pending markdown\n- [x] completed markdown\n",
        encoding="utf-8",
    )

    todos = _phase(tmp_path)._parse_todo_files()

    descriptions = {item["description"] for item in todos}
    assert {"yaml task", "pending markdown", "completed markdown"} <= descriptions
    completed = next(item for item in todos if item["description"] == "completed markdown")
    assert completed["status"] == "completed"
    assert completed["phase"] == "external"


def test_prioritize_todos_rewards_critical_pending_early_phase(tmp_path):
    phase = _phase(tmp_path)
    todos = [
        {"description": "ordinary task", "priority": "low", "phase": "phase9", "status": "completed"},
        {"description": "critical blocker must fix", "priority": "high", "phase": "phase1", "status": "pending"},
        {"description": "testing task", "priority": "medium", "phase": "phase4", "status": "in_progress"},
    ]

    ranked = phase._prioritize_todos(todos)

    assert ranked[0]["description"] == "critical blocker must fix"
    assert ranked[-1]["description"] == "ordinary task"


def test_create_links_and_classification_cover_all_routes(tmp_path):
    phase = _phase(tmp_path)
    todos = [{
        "todo_id": "T1",
        "agent": "agent-a",
        "phase": "phase2",
        "artifacts": ["a.json", "b.md"],
        "actions": ["review", "test"],
    }]

    links = phase._create_todo_links(todos)

    assert links["agent_to_todos"]["agent-a"] == ["T1"]
    assert links["phase_to_todos"]["phase2"] == ["T1"]
    assert links["artifact_to_todos"]["a.json"] == ["T1"]
    assert links["action_to_todos"]["test"] == ["T1"]

    assert phase._classify_todo({"description": "fix crash"}) == "code_fix"
    assert phase._classify_todo({"description": "update README documentation"}) == "documentation"
    assert phase._classify_todo({"description": "refactor and optimize"}) == "refactoring"
    assert phase._classify_todo({"description": "increase test coverage"}) == "testing"
    assert phase._classify_todo({"description": "coordinate follow-up"}) == "generic"
