"""Wave 13 lane A behaviour tests for DMAIC_V3/phases/phase7_action_tracking.py."""

import importlib
import json
import sys
from types import SimpleNamespace

import pytest


def _import_restoring_sys_path():
    saved = list(sys.path)
    try:
        return importlib.import_module("DMAIC_V3.phases.phase7_action_tracking")
    finally:
        sys.path[:] = saved


p7 = _import_restoring_sys_path()


@pytest.fixture
def cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _phase(root):
    return p7.Phase7ActionTracking(SimpleNamespace(workspace_root=str(root)), None)


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_register_action_updates_global_registry(cwd):
    tr = p7.ActionTracker(cwd)
    a = {"phase": "phase1", "agent": "X", "timestamp": "t1", "status": "done"}
    aid = tr.register_action(a)
    assert len(aid) == 12
    assert a["action_id"] == aid
    assert "registered_at" in a
    tr.register_action({"phase": "phase2", "agent": "Y", "type": "fix"})
    reg = json.loads(tr.global_registry_path.read_text(encoding="utf-8"))
    assert reg["total_actions"] == 2
    assert tr.local_actions[0] is a
    assert [x["agent"] for x in tr.get_actions_by_phase("phase1")] == ["X"]
    assert [x["phase"] for x in tr.get_actions_by_agent("Y")] == ["phase2"]
    stats = tr.get_action_statistics()
    assert stats["total_actions"] == 2
    assert stats["by_status"] == {"done": 1, "unknown": 1}
    assert stats["by_type"] == {"unknown": 1, "fix": 1}


def test_action_id_is_deterministic(cwd):
    tr = p7.ActionTracker(cwd)
    one = tr.register_action({"phase": "p", "agent": "a", "timestamp": "t"})
    two = tr.register_action({"phase": "p", "agent": "a", "timestamp": "t"})
    assert one == two


def test_empty_registry_statistics(cwd):
    stats = p7.ActionTracker(cwd).get_action_statistics()
    assert stats["total_actions"] == 0
    assert stats["by_phase"] == {}


def test_collect_phase_actions(cwd, capsys):
    it = cwd / "DMAIC_V3_OUTPUT" / "iteration_3"
    _write(
        it / "phase1_define" / "a.json",
        {"actions": [{"agent": "A", "description": "fix bug"}]},
    )
    _write(it / "phase2_measure" / "noactions.json", {"other": 1})
    (it / "phase3_analyze").mkdir(parents=True)
    (it / "phase3_analyze" / "bad.json").write_text("{nope", encoding="utf-8")
    _write(it / "phase5_control" / "typed.json", {"actions": ["not-a-dict"]})
    (it / "phase6_file.json").write_text("{}", encoding="utf-8")
    _write(
        it / "phase4_improvements.json",
        {
            "implementation_results": {
                "docstrings_added": [{"file": "x.py", "modifications": 2}, "loose"],
                "type_hints_added": [{}],
            }
        },
    )
    actions = _phase(cwd)._collect_phase_actions(3)
    assert actions[0]["phase"] == "phase1"
    assert actions[0]["source_file"].endswith("a.json")
    p4 = [a for a in actions if a["agent"] == "CodeImprover"]
    assert len(p4) == 2
    assert p4[0]["description"] == "Docstrings Added: x.py"
    assert p4[0]["modifications"] == 2
    assert p4[1]["file"] == "unknown"
    out = capsys.readouterr().out
    assert "Skipping invalid action file" in out


def test_collect_phase_actions_bad_phase4_file(cwd, capsys):
    it = cwd / "DMAIC_V3_OUTPUT" / "iteration_1"
    it.mkdir(parents=True)
    (it / "phase4_improvements.json").write_text("{bad", encoding="utf-8")
    assert _phase(cwd)._collect_phase_actions(1) == []
    assert "Could not extract Phase 4 actions" in capsys.readouterr().out


def test_create_action_links(cwd):
    links = _phase(cwd)._create_action_links(
        [
            {"action_id": "1", "agent": "A", "phase": "p1", "artifacts": ["f", "g"]},
            {"action_id": "2", "agent": "A", "phase": "p2", "artifacts": ["f"]},
            {},
        ]
    )
    assert links["agent_to_actions"] == {"A": ["1", "2"], "unknown": ["unknown"]}
    assert links["phase_to_actions"]["p1"] == ["1"]
    assert links["artifact_to_actions"] == {"f": ["1", "2"], "g": ["1"]}


@pytest.mark.parametrize(
    "action, expected",
    [
        ({"description": "Security hole"}, "high"),
        ({"type": "Bug_Fix"}, "high"),
        ({"description": "optimize loop"}, "medium"),
        ({}, "low"),
    ],
)
def test_calculate_action_priority(cwd, action, expected):
    assert _phase(cwd)._calculate_action_priority(action) == expected


def test_feedback_categories_and_recommendations(cwd):
    actions = [
        {"action_id": str(i), "description": "urgent", "status": "pending"}
        for i in range(11)
    ]
    actions += [
        {"action_id": "c", "description": "done", "status": "completed"},
        {"action_id": "f", "status": "failed", "failure_reason": "boom"},
        {"action_id": "g", "status": "failed"},
        {"action_id": "s", "status": "skipped"},
        {"action_id": "p", "status": "in_progress"},
    ]
    fb = _phase(cwd)._create_feedback_for_next_iteration(actions, 4)
    assert fb["source_iteration"] == 4
    assert fb["target_iteration"] == 5
    assert len(fb["pending_actions"]) == 12
    assert fb["completed_actions"] == [{"action_id": "c", "description": "done"}]
    assert [f["reason"] for f in fb["failed_actions"]] == ["boom", "Unknown"]
    assert [r["type"] for r in fb["recommendations"]] == [
        "workload",
        "quality",
        "priority",
    ]


def test_feedback_no_recommendations(cwd):
    fb = _phase(cwd)._create_feedback_for_next_iteration([{"status": "completed"}], 1)
    assert fb["recommendations"] == []


def test_execute_end_to_end(cwd):
    it = cwd / "DMAIC_V3_OUTPUT" / "iteration_2"
    _write(
        it / "phase1_define" / "a.json",
        {
            "actions": [
                {"agent": "A", "description": "refactor", "artifacts": ["x.py"]},
                {"agent": "B", "description": "crash", "status": "failed"},
            ]
        },
    )
    ok, res = _phase(cwd).execute(2)
    assert ok is True
    assert len(res["local_actions"]) == 2
    assert res["global_statistics"]["total_actions"] == 2
    assert res["action_links"]["artifact_to_actions"]["x.py"] == [
        res["local_actions"][0]["action_id"]
    ]
    out_dir = it / "phase7_action_tracking"
    saved = json.loads((out_dir / "phase7_action_tracking.json").read_text("utf-8"))
    assert saved["phase"] == "phase7_action_tracking"
    report = (out_dir / "action_report.md").read_text(encoding="utf-8")
    assert "**Iteration:** 2" in report
    assert "- phase1: 2" in report
    assert "- Artifact Links: 1" in report
    fb = json.loads((out_dir / "feedback_for_next_iteration.json").read_text("utf-8"))
    assert len(fb["pending_actions"]) == 1
    assert len(fb["failed_actions"]) == 1


def test_execute_feedback_typeerror_fallback(cwd, monkeypatch):
    ph = _phase(cwd)
    calls = []

    def fake(actions, iteration):
        calls.append(iteration)
        if len(calls) == 1:
            raise TypeError("first call fails")
        return None

    monkeypatch.setattr(ph, "_create_feedback_for_next_iteration", fake)
    ok, res = ph.execute(1)
    assert ok is True
    assert calls == [1, 1]
    assert res["feedback"] == {}


def test_execute_failure_sets_error(cwd, monkeypatch):
    ph = _phase(cwd)

    def boom(iteration):
        raise RuntimeError("disk gone")

    monkeypatch.setattr(ph, "_collect_phase_actions", boom)
    ok, res = ph.execute(1)
    assert ok is False
    assert res["error"] == "disk gone"
