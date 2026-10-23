"""Lane 4 coverage: SelfImprovementAgent quality-root preservation.

The agent reads JSON artefacts under ``config.paths.output_root`` (phase
outputs, ``agent_registry.json``, ``*RANKING*.json``), derives improvement
opportunities and writes ``self_improvement_iteration_<n>.json``.  These tests
run fully hermetically: every test chdirs into ``tmp_path`` before the real
``DMAICConfig`` is built, so the relative default ``DMAIC_V3_OUTPUT`` tree is
created inside the temporary directory, never inside the repository.

The module never shells out (no subprocess / pylint / bandit calls), so no
process mocking is needed; the "red root" signals here are missing, small,
malformed or under-populated artefacts.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "DMAIC_V3"
    / "agents"
    / "self_improvement_agent.py"
)
_MODULE_CACHE = {}


def _load_module():
    """Load the agent module once, restoring sys.path afterwards."""
    if "mod" not in _MODULE_CACHE:
        saved_path = list(sys.path)
        try:
            spec = importlib.util.spec_from_file_location(
                "lane4_self_improvement_agent", MODULE_PATH
            )
            assert spec is not None and spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        finally:
            sys.path[:] = saved_path
        _MODULE_CACHE["mod"] = module
    return _MODULE_CACHE["mod"]


@pytest.fixture
def mod(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return _load_module()


@pytest.fixture
def agent(mod, tmp_path):
    """A real agent built through the real __init__, rooted in tmp_path."""
    instance = mod.SelfImprovementAgent()
    out = Path(instance.config.paths.output_root).resolve()
    assert tmp_path.resolve() in out.parents  # hermetic: never the repo tree
    return instance


def _out(agent):
    return Path(agent.config.paths.output_root)


def _write_json(path: Path, payload) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _big_payload():
    # Comfortably above the 1000-byte "small output" threshold.
    return {"rows": [{"k": i, "v": "x" * 20} for i in range(60)]}


# --------------------------------------------------------------------------
# __init__
# --------------------------------------------------------------------------


def test_init_builds_empty_state_and_creates_dirs_under_tmp(agent, tmp_path):
    assert agent.improvement_history == []
    assert agent.knowledge_base == {
        "patterns": [],
        "anti_patterns": [],
        "best_practices": [],
        "metrics": {},
    }
    assert _out(agent).is_dir()
    assert Path(agent.config.paths.state_dir).is_dir()
    assert Path(agent.state_mgr.state_dir) == Path(agent.config.paths.state_dir)


# --------------------------------------------------------------------------
# DEVOUR
# --------------------------------------------------------------------------


def test_devour_empty_output_root_yields_zero_insights(agent):
    devoured = agent._devour_knowledge(1)
    assert devoured == {
        "total_insights": 0,
        "phase_outputs": [],
        "agent_data": [],
        "rankings": [],
        "knowledge_books": [],
    }


def test_devour_collects_phase_outputs_registry_and_rankings(agent):
    out = _out(agent)
    p1 = _write_json(out / "iteration_1" / "phase1_define" / "a.json", {"x": 1})
    _write_json(out / "iteration_1" / "phase2_measure" / "b.json", _big_payload())
    # Non-json and non-phase files are ignored by the phase scan.
    (out / "iteration_1" / "phase1_define" / "notes.txt").write_text("ignored")
    _write_json(out / "iteration_1" / "misc" / "c.json", {"ignored": True})
    _write_json(out / "agent_registry.json", {"agents": {"a": {}, "b": {}, "c": {}}})
    _write_json(out / "reports" / "GLOBAL_RANKING.json", {"rank": 1})

    devoured = agent._devour_knowledge(1)

    files = sorted(Path(o["file"]).name for o in devoured["phase_outputs"])
    assert files == ["a.json", "b.json"]
    small = next(o for o in devoured["phase_outputs"] if Path(o["file"]) == p1)
    assert small["data"] == {"x": 1}
    assert small["size"] == p1.stat().st_size
    assert devoured["agent_data"] == {"agents": {"a": {}, "b": {}, "c": {}}}
    assert devoured["rankings"] == [{"rank": 1}]
    # 2 phase files + 3 agents + 1 ranking
    assert devoured["total_insights"] == 6


def test_devour_skips_malformed_phase_and_ranking_json(agent):
    out = _out(agent)
    (out / "iteration_1" / "phase3_analyze").mkdir(parents=True)
    (out / "iteration_1" / "phase3_analyze" / "broken.json").write_text(
        "{not json", encoding="utf-8"
    )
    (out / "BROKEN_RANKING.json").write_text("[1, 2", encoding="utf-8")
    _write_json(out / "iteration_1" / "phase3_analyze" / "ok.json", {"ok": True})

    devoured = agent._devour_knowledge(1)

    assert [Path(o["file"]).name for o in devoured["phase_outputs"]] == ["ok.json"]
    assert devoured["rankings"] == []
    assert devoured["total_insights"] == 1


def test_devour_malformed_agent_registry_raises_not_silently_passes(agent):
    """Quality root: a corrupt registry is a loud failure, not an empty pass."""
    (_out(agent) / "agent_registry.json").write_text('{"agents": ', encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        agent._devour_knowledge(1)


def test_devour_registry_with_unexpected_top_level_type_raises(agent):
    _write_json(_out(agent) / "agent_registry.json", ["agent-a", "agent-b"])
    with pytest.raises(AttributeError):
        agent._devour_knowledge(1)


def test_devour_ranking_inside_phase_dir_is_counted_twice(agent):
    """Current behaviour: a *RANKING*.json under a phase dir is both a phase
    output and a ranking, so it contributes two insights (double count)."""
    _write_json(
        _out(agent) / "iteration_1" / "phase7_rank" / "PHASE_RANKING.json", {"r": 1}
    )
    devoured = agent._devour_knowledge(1)
    assert len(devoured["phase_outputs"]) == 1
    assert devoured["rankings"] == [{"r": 1}]
    assert devoured["total_insights"] == 2


def test_devour_missing_output_root_returns_empty(agent):
    out = _out(agent)
    # Remove the whole output tree (missing artefact root).
    for p in sorted(out.rglob("*"), reverse=True):
        p.rmdir() if p.is_dir() else p.unlink()
    out.rmdir()
    assert not out.exists()
    devoured = agent._devour_knowledge(1)
    assert devoured["total_insights"] == 0
    assert devoured["phase_outputs"] == []


# --------------------------------------------------------------------------
# DEFINE
# --------------------------------------------------------------------------


def _devoured(phase_outputs=None, agent_data=None):
    return {
        "total_insights": 0,
        "phase_outputs": phase_outputs or [],
        "agent_data": agent_data if agent_data is not None else [],
        "rankings": [],
        "knowledge_books": [],
    }


def test_define_flags_every_phase_missing_when_nothing_devoured(agent):
    opps = agent._define_opportunities(_devoured())
    assert [o["phase"] for o in opps] == list(range(9))
    assert all(o["type"] == "missing_output" and o["priority"] == "HIGH" for o in opps)


def test_define_small_output_flagged_large_not(agent):
    outputs = [
        {
            "file": str(Path("iteration_1") / "phase1_define" / "tiny.json"),
            "size": 10,
            "data": {},
        },
        {
            "file": str(Path("iteration_1") / "phase1_define" / "edge.json"),
            "size": 999,
            "data": {},
        },
        {
            "file": str(Path("iteration_1") / "phase1_define" / "ok.json"),
            "size": 1000,
            "data": {},
        },
    ]
    opps = agent._define_opportunities(_devoured(outputs))
    small = [o for o in opps if o["type"] == "small_output"]
    assert [Path(o["file"]).name for o in small] == ["tiny.json", "edge.json"]
    assert [o["size"] for o in small] == [10, 999]
    assert all(o["priority"] == "MEDIUM" for o in small)
    assert "tiny.json" in small[0]["description"]


def test_define_agent_underutilization_preserved_and_full_registry_clean(agent):
    under = agent._define_opportunities(_devoured(agent_data={"agents": {"a": {}}}))
    util = [o for o in under if o["type"] == "agent_underutilization"]
    assert len(util) == 1
    assert util[0]["current_agents"] == 1
    assert util[0]["expected_agents"] == 12

    full = {"agents": {f"a{i}": {} for i in range(12)}}
    clean = agent._define_opportunities(_devoured(agent_data=full))
    assert not [o for o in clean if o["type"] == "agent_underutilization"]


def test_define_registry_without_agents_key_counts_as_zero(agent):
    opps = agent._define_opportunities(_devoured(agent_data={"other": 1}))
    util = [o for o in opps if o["type"] == "agent_underutilization"]
    assert util and util[0]["current_agents"] == 0


def test_define_current_behaviour_phase_with_output_still_flagged(agent):
    """F9 (current behaviour, pinned; the canonical lane forbids xfail):
    _define_opportunities keys phase_counts by the real directory name (e.g.
    'phase1_define') but looks up the literal glob string 'phase1_*', so a
    phase that DID produce output is still reported as missing_output. When
    fixed, phase 1 must drop out of this list."""
    outputs = [
        {
            "file": str(Path("iteration_1") / "phase1_define" / "x.json"),
            "size": 5000,
            "data": {},
        }
    ]
    opps = agent._define_opportunities(_devoured(outputs))
    assert [o["phase"] for o in opps if o["type"] == "missing_output"] == list(range(9))


def test_define_empty_registry_drops_underutilization_current_behaviour(agent):
    """F11 (current behaviour, pinned; the canonical lane forbids xfail): an
    existing-but-empty agent_registry.json ({}) is falsy, so the
    agent_underutilization root (0/12 agents) is silently dropped. When fixed,
    flip to ``any(...)``."""
    opps = agent._define_opportunities(_devoured(agent_data={}))
    assert not any(o["type"] == "agent_underutilization" for o in opps)


# --------------------------------------------------------------------------
# MEASURE
# --------------------------------------------------------------------------


def test_measure_baseline_counts_iterations_files_phases_and_agents(agent):
    out = _out(agent)
    _write_json(out / "iteration_1" / "phase0_init" / "a.json", {"a": 1})
    _write_json(out / "iteration_1" / "phase4_improve" / "b.json", {"b": 1})
    _write_json(out / "iteration_2" / "phase0_init" / "c.json", {"c": 1})
    (out / "iteration_2" / "phase0_init" / "raw.bin").write_bytes(b"\0" * 2048)
    _write_json(out / "agent_registry.json", {"agents": {"x": {}, "y": {}}})

    metrics = agent._measure_baseline()

    assert metrics["total_iterations"] == 2
    assert metrics["total_files"] == 4  # 3 phase json + registry
    assert metrics["phases_with_output"] == {"phase0": 2, "phase4": 1}
    assert metrics["agent_count"] == 2
    expected_bytes = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    assert metrics["total_size_mb"] == pytest.approx(expected_bytes / (1024 * 1024))


def test_measure_baseline_keeps_malformed_artifact_visible(agent):
    """A malformed phase file is skipped by DEVOUR but still counted in the
    MEASURE baseline, so the red artefact is not erased from the record."""
    bad = _out(agent) / "iteration_1" / "phase5_control" / "bad.json"
    bad.parent.mkdir(parents=True)
    bad.write_text("<<<garbage>>>", encoding="utf-8")

    assert agent._devour_knowledge(1)["total_insights"] == 0
    metrics = agent._measure_baseline()
    assert metrics["total_files"] == 1
    assert metrics["phases_with_output"] == {"phase5": 1}


def test_measure_baseline_without_registry_reports_zero_agents(agent):
    metrics = agent._measure_baseline()
    assert metrics["agent_count"] == 0
    assert metrics["total_iterations"] == 0
    assert metrics["phases_with_output"] == {}


def test_measure_baseline_malformed_registry_raises(agent):
    (_out(agent) / "agent_registry.json").write_text("not-json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        agent._measure_baseline()


# --------------------------------------------------------------------------
# ANALYZE / IMPROVE / CONTROL edge branches
# --------------------------------------------------------------------------


def test_unknown_opportunity_type_is_dropped_by_analyze(agent):
    """Current behaviour: an unrecognised opportunity type produces no root
    cause (silently dropped), while known ones are preserved in order."""
    opps = [
        {"type": "lint_regression", "priority": "HIGH"},
        {"type": "missing_output", "phase": 2, "priority": "HIGH"},
    ]
    roots = agent._analyze_root_causes(opps, {})
    assert len(roots) == 1
    assert roots[0]["opportunity"]["phase"] == 2
    assert roots[0]["evidence"] == "Phase 2 has no output files"


def test_unknown_root_cause_type_is_dropped_by_generate(agent):
    roots = [
        {"opportunity": {"type": "bandit_finding"}},
        {"opportunity": {"type": "small_output", "file": "f.json", "size": 3}},
    ]
    imps = agent._generate_improvements(roots)
    assert [i["id"] for i in imps] == ["IMP-001"]
    assert imps[0]["target"] == "f.json"


def test_control_rejects_improvement_missing_required_field(agent):
    imp = {
        "id": "IMP-9",
        "type": "t",
        "priority": "LOW",
        "effort": "LOW",
        "action": "a",
    }
    assert agent._control_improvements([imp]) == []
    assert imp["validated"] is False
    assert imp["validation_notes"] == [
        "Missing field: target",
        "Missing field: expected_outcome",
    ]


def test_control_rejects_invalid_effort_only(agent):
    imp = {
        "id": "IMP-7",
        "type": "t",
        "target": "x",
        "action": "a",
        "expected_outcome": "o",
        "priority": "HIGH",
        "effort": "EPIC",
    }
    assert agent._control_improvements([imp]) == []
    assert imp["validated"] is False
    assert imp["validation_notes"] == ["Invalid effort level"]


def test_define_only_literal_glob_dirname_suppresses_missing_flag(agent):
    """Adversarial: the lookup key is the literal 'phaseN_*' string, so only a
    parent directory named exactly 'phase3_*' clears phase 3 (bug evidence)."""
    outputs = [
        {
            "file": str(Path("iteration_1") / "phase3_*" / "x.json"),
            "size": 5000,
            "data": {},
        }
    ]
    opps = agent._define_opportunities(_devoured(outputs))
    missing = [o["phase"] for o in opps if o["type"] == "missing_output"]
    assert missing == [0, 1, 2, 4, 5, 6, 7, 8]


def test_control_missing_priority_raises_keyerror(agent):
    with pytest.raises(KeyError):
        agent._control_improvements([{"id": "x", "effort": "LOW"}])


def test_rejected_improvement_does_not_lower_success_rate(agent):
    """Documents that success_rate is computed only over survivors: a red
    (rejected) improvement leaves success_rate at 100%.  The drop remains
    visible only through validated count vs generated count."""
    good = {
        "id": "1",
        "type": "t",
        "target": "x",
        "action": "a",
        "expected_outcome": "o",
        "priority": "LOW",
        "effort": "LOW",
    }
    bad = dict(good, id="2", priority="BOGUS")
    generated = [good, bad]
    validated = agent._control_improvements(generated)
    optimized = agent._optimize_improvements(validated)
    metrics = agent._measure_success({}, optimized)
    assert len(generated) == 2 and len(validated) == 1
    assert bad["validated"] is False
    assert metrics["success_rate"] == 100.0


def test_measure_success_with_no_improvements_is_zero(agent):
    metrics = agent._measure_success({"k": 1}, [])
    assert metrics["success_rate"] == 0.0
    assert metrics["improvements_count"] == 0
    assert metrics["estimated_total_effort"] == "0.0 hours"


def test_total_effort_hours_branch_below_one_day(agent):
    assert (
        agent._calculate_total_effort([{"effort": "LOW"}, {"effort": "LOW"}])
        == "3.0 hours"
    )
    assert (
        agent._calculate_total_effort([{"effort": "MEDIUM"}, {"effort": "LOW"}])
        == "7.5 hours"
    )
    assert (
        agent._calculate_total_effort([{"effort": "MEDIUM"}, {"effort": "MEDIUM"}])
        == "1.5 days"
    )
    assert agent._calculate_total_effort([{"effort": "WEIRD"}]) == "0.0 hours"


# --------------------------------------------------------------------------
# Full cycle, persistence, idempotency
# --------------------------------------------------------------------------


def _seed_red_tree(out: Path):
    _write_json(out / "iteration_1" / "phase1_define" / "tiny.json", {"t": 1})
    _write_json(out / "iteration_1" / "phase2_measure" / "big.json", _big_payload())
    _write_json(out / "agent_registry.json", {"agents": {"a": {}, "b": {}}})
    _write_json(out / "SUITE_RANKING.json", {"score": 0.4})


def test_full_cycle_preserves_red_roots_and_round_trips_to_disk(agent, capsys):
    out = _out(agent)
    _seed_red_tree(out)

    result = agent.execute_improvement_cycle(iteration=3)

    # 2 phase outputs + 2 agents + 1 ranking
    assert result["devoured_insights"] == 5
    # 9 missing_output (see bug) + 1 small_output + 1 agent_underutilization
    assert result["opportunities_found"] == 11
    assert result["improvements_generated"] == 11
    assert result["improvements_validated"] == 11
    assert result["improvements_optimized"] == 11
    types = [i["type"] for i in result["improvements"]]
    assert types.count("enhance_data_processing") == 1
    assert types.count("fix_agent_initialization") == 1
    assert [i["id"] for i in result["improvements"]] == [
        f"IMP-{n:03d}" for n in range(1, 12)
    ]
    small = next(
        i for i in result["improvements"] if i["type"] == "enhance_data_processing"
    )
    assert Path(small["target"]).name == "tiny.json"
    assert result["baseline_metrics"]["agent_count"] == 2
    assert result["success_rate"] == 100.0
    assert agent.improvement_history == [result]

    saved = out / "self_improvement_iteration_3.json"
    assert saved.is_file()
    assert json.loads(saved.read_text(encoding="utf-8")) == result

    printed = capsys.readouterr().out
    assert "SELF-IMPROVEMENT CYCLE - ITERATION 3" in printed
    assert "Self-improvement cycle saved" in printed


def test_repeat_cycle_same_iteration_overwrites_not_duplicates(agent):
    out = _out(agent)
    _seed_red_tree(out)

    first = agent.execute_improvement_cycle(iteration=1)
    second = agent.execute_improvement_cycle(iteration=1)

    saved = sorted(p.name for p in out.glob("self_improvement_iteration_*.json"))
    assert saved == ["self_improvement_iteration_1.json"]
    on_disk = json.loads((out / saved[0]).read_text(encoding="utf-8"))
    assert on_disk == second
    # Same red roots are re-derived, not accumulated across runs.
    assert second["opportunities_found"] == first["opportunities_found"]
    assert [i["id"] for i in second["improvements"]] == [
        i["id"] for i in first["improvements"]
    ]
    assert len({i["id"] for i in second["improvements"]}) == len(second["improvements"])
    # The saved report is not itself devoured as a phase output/ranking...
    assert second["devoured_insights"] == first["devoured_insights"]
    # ...but the MEASURE baseline does see it as one extra json file (stale input).
    assert (
        second["baseline_metrics"]["total_files"]
        == first["baseline_metrics"]["total_files"] + 1
    )
    # In-memory history records both runs.
    assert len(agent.improvement_history) == 2


def test_stale_report_is_replaced_by_new_cycle(agent):
    out = _out(agent)
    stale = _write_json(
        out / "self_improvement_iteration_2.json",
        {"iteration": 2, "success_rate": 0.0, "stale": True},
    )
    _seed_red_tree(out)

    result = agent.execute_improvement_cycle(iteration=2)

    loaded = json.loads(stale.read_text(encoding="utf-8"))
    assert "stale" not in loaded
    assert loaded == result


def test_cycle_on_empty_tree_still_reports_missing_roots(agent):
    result = agent.execute_improvement_cycle(iteration=1)
    assert result["devoured_insights"] == 0
    assert result["opportunities_found"] == 9
    assert all(i["type"] == "fix_phase_execution" for i in result["improvements"])
    assert result["final_metrics"]["high_priority_count"] == 9
    assert result["final_metrics"]["estimated_total_effort"] == "6.8 days"


def test_cycle_fails_loudly_when_output_root_vanishes(agent):
    out = _out(agent)
    for p in sorted(out.rglob("*"), reverse=True):
        p.rmdir() if p.is_dir() else p.unlink()
    out.rmdir()
    with pytest.raises(FileNotFoundError):
        agent.execute_improvement_cycle(iteration=1)
    # History is appended before the save attempt (current behaviour).
    assert len(agent.improvement_history) == 1


def test_cycle_with_corrupt_registry_aborts_without_writing_report(agent):
    out = _out(agent)
    (out / "agent_registry.json").write_text("{bad", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        agent.execute_improvement_cycle(iteration=4)
    assert not (out / "self_improvement_iteration_4.json").exists()
    assert agent.improvement_history == []


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def test_main_runs_multiple_cycles_and_writes_each_report(
    mod, tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr(
        sys, "argv", ["self_improvement_agent", "--iteration", "5", "--cycles", "2"]
    )
    assert mod.main() == 0
    out = tmp_path / "DMAIC_V3_OUTPUT"
    names = sorted(p.name for p in out.glob("self_improvement_iteration_*.json"))
    assert names == [
        "self_improvement_iteration_5.json",
        "self_improvement_iteration_6.json",
    ]
    printed = capsys.readouterr().out
    assert "Total Cycles: 2" in printed
    assert "Total Improvements: 18" in printed
    assert "Average Success Rate: 100.0%" in printed


def test_main_rejects_non_integer_argument(mod, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["self_improvement_agent", "--cycles", "two"])
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 2


def test_main_zero_cycles_divides_by_zero(mod, monkeypatch):
    """Current behaviour: --cycles 0 crashes computing the average success
    rate (ZeroDivisionError) instead of reporting an empty run."""
    monkeypatch.setattr(sys, "argv", ["self_improvement_agent", "--cycles", "0"])
    with pytest.raises(ZeroDivisionError):
        mod.main()
