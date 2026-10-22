"""Lane 3: Phase 8 replay and registry-corruption coverage.

Every test is hermetic: the workspace (where the global registry lives) and the
current working directory (where ``execute`` writes its relative
``DMAIC_V3_OUTPUT/iteration_N`` tree) are both redirected under ``tmp_path``.
"""

from __future__ import annotations

import json
import os
from datetime import datetime as _real_datetime
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import DMAIC_V3.phases.phase8_todo_management as p8

# On case-insensitive globbing (Windows) both "TODO*.yaml" and "todo*.yaml"
# match the same file, so YAML TODO files are ingested once per pattern.
YAML_GLOB_MULTIPLICITY = 2 if os.name == "nt" else 1


class _FixedClock:
    """Deterministic stand-in for ``datetime`` inside the phase8 module."""

    moment = _real_datetime(2026, 10, 21, 12, 0, 0)

    @classmethod
    def now(cls):
        return cls.moment


class _TickingClock:
    """Each ``now()`` call advances one second (deterministic, no sleeps)."""

    current = _real_datetime(2026, 10, 21, 12, 0, 0)

    @classmethod
    def now(cls):
        cls.current = cls.current + timedelta(seconds=1)
        return cls.current


@pytest.fixture
def env(tmp_path, monkeypatch):
    workspace = tmp_path / "ws"
    run_dir = tmp_path / "run"
    workspace.mkdir()
    run_dir.mkdir()
    monkeypatch.chdir(run_dir)
    phase = p8.Phase8TODOManagement(
        SimpleNamespace(workspace_root=str(workspace)), SimpleNamespace()
    )
    return SimpleNamespace(
        phase=phase,
        ws=workspace,
        run=run_dir,
        registry=phase.tracker.global_registry_path,
    )


def _write_phase_output(
    run_dir: Path, iteration: int, phase_dir: str, name: str, payload
) -> Path:
    target = run_dir / "DMAIC_V3_OUTPUT" / f"iteration_{iteration}" / phase_dir
    target.mkdir(parents=True, exist_ok=True)
    path = target / name
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _read_registry(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


FIVE_ROUTES = [
    {"description": "fix crash in loader", "priority": "high", "status": "pending"},
    {"description": "document the readme", "priority": "high", "status": "pending"},
    {"description": "refactor scheduler", "priority": "high", "status": "pending"},
    {"description": "add unittest suite", "priority": "high", "status": "pending"},
    {"description": "coordinate follow-up", "priority": "high", "status": "pending"},
]


# --------------------------------------------------------------------------- execute


def test_execute_routes_each_high_priority_todo_and_persists_status(env, monkeypatch):
    monkeypatch.setattr(p8, "datetime", _FixedClock)
    _write_phase_output(
        env.run,
        1,
        "phase2_build",
        "out.json",
        {"todos": [dict(t) for t in FIVE_ROUTES]},
    )

    ok, results = env.phase.execute(iteration=1)

    assert ok is True
    executions = {r["description"]: r for r in results["todo_executions"]}
    assert len(executions) == 5
    assert all(r["success"] for r in executions.values())
    assert executions["fix crash in loader"]["message"] == "Logged for code review"
    assert (
        executions["document the readme"]["message"]
        == "Logged for documentation update"
    )
    assert (
        executions["refactor scheduler"]["message"] == "Logged for refactoring review"
    )
    assert (
        executions["add unittest suite"]["message"] == "Logged for test implementation"
    )
    assert executions["coordinate follow-up"]["message"] == "Logged for manual review"
    assert executions["coordinate follow-up"]["actions_taken"] == [
        "Added to general review queue"
    ]

    registry = _read_registry(env.registry)
    status_by_desc = {t["description"]: t["status"] for t in registry["todos"]}
    assert status_by_desc == {
        "fix crash in loader": "in_review",
        "document the readme": "in_progress",
        "refactor scheduler": "in_review",
        "add unittest suite": "in_progress",
        "coordinate follow-up": "pending_review",
    }
    assert registry["statistics"]["by_status"] == {
        "in_review": 2,
        "in_progress": 2,
        "pending_review": 1,
    }
    assert all(t["phase"] == "phase2" for t in registry["todos"])

    out_dir = env.run / "DMAIC_V3_OUTPUT" / "iteration_1" / "phase8_todo_management"
    saved = json.loads(
        (out_dir / "phase8_todo_management.json").read_text(encoding="utf-8")
    )
    assert len(saved["local_todos"]) == 5
    exported = yaml.safe_load(
        (out_dir / "prioritized_todos.yaml").read_text(encoding="utf-8")
    )
    assert exported["total_todos"] == 5
    assert "Action Links: 0" in (out_dir / "todo_report.md").read_text(encoding="utf-8")


def test_execute_caps_execution_at_five_and_skips_non_pending(env, monkeypatch):
    monkeypatch.setattr(p8, "datetime", _FixedClock)
    todos = [
        {"description": f"generic item {i}", "priority": "high", "status": "pending"}
        for i in range(7)
    ]
    todos.append(
        {"description": "already done", "priority": "high", "status": "completed"}
    )
    _write_phase_output(env.run, 3, "phase1_x", "a.json", {"todos": todos})

    ok, results = env.phase.execute(iteration=3)

    assert ok is True
    executed = [r["description"] for r in results["todo_executions"]]
    assert len(executed) == 5
    assert "already done" not in executed


def test_execute_fails_closed_on_truncated_registry_without_clobbering_it(env, capsys):
    env.registry.parent.mkdir(parents=True)
    truncated = '{"todos": [{"todo_id": "abc", "status": "pen'
    env.registry.write_text(truncated, encoding="utf-8")
    _write_phase_output(
        env.run, 1, "phase0_init", "o.json", {"todos": [{"description": "anything"}]}
    )

    ok, results = env.phase.execute(iteration=1)

    assert ok is False
    assert "Unterminated string" in results["error"] or "Expecting" in results["error"]
    assert env.registry.read_text(encoding="utf-8") == truncated
    assert not (
        env.run / "DMAIC_V3_OUTPUT" / "iteration_1" / "phase8_todo_management"
    ).exists()
    assert "[ERROR] Phase 8 failed" in capsys.readouterr().out


def test_execute_fails_closed_on_registry_missing_todos_key(env):
    env.registry.parent.mkdir(parents=True)
    env.registry.write_text(
        json.dumps({"total_todos": 3, "statistics": {}}), encoding="utf-8"
    )

    # With nothing to register the schema-broken registry is never indexed and
    # the phase passes, reporting the registry's own (empty) statistics.
    ok_empty, empty = env.phase.execute(iteration=1)
    assert ok_empty is True
    assert empty["global_statistics"] == {}

    _write_phase_output(
        env.run,
        2,
        "phase7_last",
        "o.json",
        {"todos": [{"description": "needs registry"}]},
    )
    ok, results = env.phase.execute(iteration=2)

    assert ok is False
    assert results["error"] == "'todos'"
    assert "todo_executions" not in results
    assert _read_registry(env.registry) == {"total_todos": 3, "statistics": {}}


def test_execute_with_no_inputs_succeeds_with_empty_registry(env):
    ok, results = env.phase.execute(iteration=9)

    assert ok is True
    assert results["local_todos"] == []
    assert results["todo_executions"] == []
    assert results["global_statistics"] == {}
    assert not env.registry.exists()


# --------------------------------------------------------------------------- replay


def _seed_replay_inputs(env):
    _write_phase_output(
        env.run,
        1,
        "phase2_build",
        "out.json",
        {"todos": [dict(t) for t in FIVE_ROUTES[:2]]},
    )
    (env.ws / "TODO_notes.md").write_text(
        "- [ ] markdown pending\n- [x] markdown done\n", encoding="utf-8"
    )
    (env.ws / "mod.py").write_text("x = 1  # TODO: scan me\n", encoding="utf-8")


def test_replay_with_identical_clock_is_idempotent(env, monkeypatch):
    monkeypatch.setattr(p8, "datetime", _FixedClock)
    _seed_replay_inputs(env)

    ok1, first = env.phase.execute(iteration=1)
    registry_after_first = _read_registry(env.registry)
    ok2, second = env.phase.execute(iteration=1)
    registry_after_second = _read_registry(env.registry)

    assert ok1 and ok2
    assert registry_after_first == registry_after_second
    assert registry_after_second["total_todos"] == 5
    first_ids = sorted(t["todo_id"] for t in first["local_todos"])
    assert first_ids == sorted(t["todo_id"] for t in second["local_todos"])


def test_replay_reissues_code_scan_ids_and_grows_registry_current_behaviour(
    env, monkeypatch
):
    """Documents a replay defect: code-scan TODOs hash ``datetime.now()`` into
    their ID, so replaying the same workspace registers the same inline TODO
    again under a fresh ID instead of updating it in place."""
    monkeypatch.setattr(p8, "datetime", _TickingClock)
    (env.ws / "mod.py").write_text("x = 1  # TODO: scan me\n", encoding="utf-8")

    env.phase.execute(iteration=1)
    first = _read_registry(env.registry)
    env.phase.execute(iteration=1)
    second = _read_registry(env.registry)

    assert first["total_todos"] == 1
    assert second["total_todos"] == 2
    descriptions = [t["description"] for t in second["todos"]]
    assert descriptions == ["scan me", "scan me"]
    assert len({t["todo_id"] for t in second["todos"]}) == 2


def test_duplicate_todo_ids_collapse_in_registry_but_not_in_local_list(
    env, monkeypatch
):
    monkeypatch.setattr(p8, "datetime", _FixedClock)
    dup = {"description": "same task", "priority": "low", "status": "completed"}
    _write_phase_output(env.run, 1, "phase4_a", "x.json", {"todos": [dict(dup)]})
    _write_phase_output(env.run, 1, "phase4_b", "y.json", {"todos": [dict(dup)]})

    ok, results = env.phase.execute(iteration=1)

    assert ok is True
    assert len(results["local_todos"]) == 2
    ids = {t["todo_id"] for t in results["local_todos"]}
    assert len(ids) == 1
    only_id = next(iter(ids))
    registry = _read_registry(env.registry)
    assert registry["total_todos"] == 1
    # The registry keeps only the last writer's source file.
    assert registry["todos"][0]["source_file"].endswith("y.json")
    assert results["todo_links"]["phase_to_todos"]["phase4"] == [only_id] * 2


# --------------------------------------------------------------------------- collection


def test_collect_phase_todos_skips_corrupt_and_non_directory_inputs(env, capsys):
    _write_phase_output(
        env.run, 2, "phase1_ok", "good.json", {"todos": [{"description": "kept"}]}
    )
    _write_phase_output(env.run, 2, "phase1_ok", "corrupt.json", '{"todos": [')
    _write_phase_output(env.run, 2, "phase3_nolist", "meta.json", {"other": 1})
    _write_phase_output(
        env.run,
        2,
        "phase8_self",
        "loop.json",
        {"todos": [{"description": "own output"}]},
    )
    # A plain file whose name matches the phase glob must not be treated as a phase dir.
    (env.run / "DMAIC_V3_OUTPUT" / "iteration_2" / "phase5_stray.json").write_text(
        json.dumps({"todos": [{"description": "stray"}]}), encoding="utf-8"
    )
    # A directory named like a Python file cannot be opened and must be skipped.
    (env.ws / "pkg.py").mkdir()
    (env.ws / "real.py").write_text("# todo: lower case marker\n", encoding="utf-8")

    todos = env.phase._collect_phase_todos(2)

    descriptions = sorted(t["description"] for t in todos)
    assert descriptions == ["kept", "lower case marker"]
    kept = next(t for t in todos if t["description"] == "kept")
    assert kept["phase"] == "phase1"
    assert kept["source_file"].endswith("good.json")
    code = next(t for t in todos if t.get("type") == "code_todo")
    assert code["line"] == 1
    assert "Found 1 TODO comments" in capsys.readouterr().out


def test_collect_phase_todos_tolerates_unusable_workspace_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    phase = object.__new__(p8.Phase8TODOManagement)
    phase.config = SimpleNamespace(workspace_root=None)
    _write_phase_output(
        tmp_path, 1, "phase6_z", "z.json", {"todos": [{"description": "only phase"}]}
    )

    todos = phase._collect_phase_todos(1)

    assert [t["description"] for t in todos] == ["only phase"]


# --------------------------------------------------------------------------- file parsing


def test_parse_todo_files_ignores_unusable_yaml_shapes(env, capsys):
    (env.ws / "TODO_scalar.yaml").write_text("just a string\n", encoding="utf-8")
    (env.ws / "TODO_nokey.yml").write_text(
        "items:\n  - description: hidden\n", encoding="utf-8"
    )
    (env.ws / "TODO_mixed.yaml").write_text(
        "- description: real entry\n- bare string entry\n- 42\n", encoding="utf-8"
    )
    (env.ws / "TODO_broken.yaml").write_text("todos: [unclosed\n", encoding="utf-8")

    todos = env.phase._parse_todo_files()

    assert [t["description"] for t in todos] == ["real entry"] * YAML_GLOB_MULTIPLICITY
    assert todos[0]["source_file"].endswith("TODO_mixed.yaml")
    assert "Warning: Failed to parse" in capsys.readouterr().out


def test_parse_todo_files_dict_form_and_uppercase_suffix(env):
    (env.ws / "TODO_dict.yaml").write_text(
        "todos:\n  - description: from dict\n", encoding="utf-8"
    )
    # Only matched by the lowercase patterns on case-insensitive globbing; its
    # ".YAML" suffix is not in the accepted list, so it is never parsed.
    (env.ws / "TODO_upper.YAML").write_text(
        "todos:\n  - description: never parsed\n", encoding="utf-8"
    )

    todos = env.phase._parse_todo_files()

    descriptions = [t["description"] for t in todos]
    assert "never parsed" not in descriptions
    assert descriptions == ["from dict"] * YAML_GLOB_MULTIPLICITY


def test_yaml_todo_file_double_ingestion_is_platform_dependent(env, monkeypatch):
    """Documents a defect: on Windows the overlapping case-variant patterns
    ingest the same YAML file twice; registration then collapses the copies
    to one registry ID (no timestamp in the identity)."""
    monkeypatch.setattr(p8, "datetime", _FixedClock)
    (env.ws / "TODO_one.yaml").write_text(
        "- description: single entry\n  priority: low\n", encoding="utf-8"
    )

    ok, results = env.phase.execute(iteration=1)

    assert ok is True
    assert len(results["local_todos"]) == YAML_GLOB_MULTIPLICITY
    assert _read_registry(env.registry)["total_todos"] == 1


# --------------------------------------------------------------------------- prioritisation / links


def test_prioritize_unknown_priority_and_malformed_phase_contribute_nothing(env):
    todos = [
        {
            "description": "a",
            "priority": "urgentish",
            "phase": "phase_alpha",
            "status": "completed",
        },
        {
            "description": "b",
            "priority": "low",
            "phase": "external",
            "status": "completed",
        },
        {
            "description": "c",
            "priority": "low",
            "phase": "phase9",
            "status": "completed",
        },
    ]

    ranked = [t["description"] for t in env.phase._prioritize_todos(todos)]

    # c: 1 + (10-9) = 2; b: 1; a: unknown priority (0) + malformed phase (0) = 0
    assert ranked == ["c", "b", "a"]


def test_prioritize_null_phase_raises_current_behaviour(env):
    """Documents a defect: an explicit ``phase: null`` escapes the guarded
    phase parse (the ``'phase' in phase`` test runs outside the try)."""
    with pytest.raises(TypeError):
        env.phase._prioritize_todos([{"description": "x", "phase": None}])


def test_links_accumulate_shared_actions_and_artifacts(env):
    todos = [
        {
            "todo_id": "T1",
            "agent": "a",
            "phase": "phase1",
            "artifacts": ["r.json"],
            "actions": ["review"],
        },
        {
            "todo_id": "T2",
            "agent": "a",
            "phase": "phase1",
            "artifacts": ["r.json"],
            "actions": ["review"],
        },
        {"phase": "phase2"},
    ]

    links = env.phase._create_todo_links(todos)

    assert links["action_to_todos"] == {"review": ["T1", "T2"]}
    assert links["artifact_to_todos"] == {"r.json": ["T1", "T2"]}
    assert links["agent_to_todos"] == {"a": ["T1", "T2"], "unknown": ["unknown"]}


# --------------------------------------------------------------------------- execution failure paths


def test_execute_todos_records_failure_when_registry_corrupt_and_continues(env, capsys):
    env.registry.parent.mkdir(parents=True)
    env.registry.write_text("[not json", encoding="utf-8")
    todos = [
        {"todo_id": "id1", "description": "fix bug"},
        {"description": "explain things"},
    ]

    results = env.phase._execute_todos(todos, iteration=1)

    assert [r["success"] for r in results] == [False, False]
    assert results[0]["message"].startswith("Execution failed: ")
    assert results[1]["todo_id"] == "unknown"
    assert all("completed_at" in r for r in results)
    # Current behaviour: the queue action is recorded before the registry write
    # fails, so a failed execution still lists an action it never completed.
    assert results[0]["actions_taken"] == ["Added to code review queue"]
    assert results[1]["actions_taken"] == ["Added to documentation queue"]
    assert "Failed:" in capsys.readouterr().out
    assert env.registry.read_text(encoding="utf-8") == "[not json"


def test_execute_todos_unknown_id_leaves_registry_entries_untouched(env, monkeypatch):
    monkeypatch.setattr(p8, "datetime", _FixedClock)
    tracker = env.phase.tracker
    known = tracker.register_todo({"description": "existing", "phase": "phase1"})

    results = env.phase._execute_todos(
        [{"todo_id": "ghost", "description": "verify output"}], iteration=1
    )

    assert results[0]["success"] is True
    assert results[0]["message"] == "Logged for test implementation"
    registry = _read_registry(env.registry)
    assert [(t["todo_id"], t["status"]) for t in registry["todos"]] == [
        (known, "pending")
    ]


def test_tracker_register_on_corrupt_registry_raises(tmp_path):
    tracker = p8.TODOTracker(tmp_path)
    tracker.global_registry_path.parent.mkdir(parents=True)
    tracker.global_registry_path.write_text("", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        tracker.register_todo({"description": "x"})
    # The in-memory local list was appended before the registry write failed.
    assert len(tracker.local_todos) == 1
    assert tracker.global_registry_path.read_text(encoding="utf-8") == ""
