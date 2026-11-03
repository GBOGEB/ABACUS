"""Behaviour tests for ABACUS-v032/execute_full_dmaic_phases_0_to_9_v033.py.

Part 1: module import guard, PhaseExecution, orchestrator setup and phases 0-8.
Everything is sandboxed under tmp_path; the module rewraps sys.stdout at import,
so each load restores the original stream and detaches the wrapper.
"""

import io
import json
import os
import sys
from pathlib import Path

import pytest

from tests.coverage_waves.lane_a._load import load

REL = "ABACUS-v032/execute_full_dmaic_phases_0_to_9_v033.py"


def _guarded_load(name=None):
    saved = sys.stdout
    try:
        return load(REL, name=name)
    finally:
        wrapper = sys.stdout
        sys.stdout = saved
        if wrapper is not saved and hasattr(wrapper, "detach"):
            wrapper.detach()


mod = _guarded_load()


@pytest.fixture
def orch(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ws = tmp_path / "ws"
    ws.mkdir()
    return mod.FullDMAICOrchestrator(ws, tmp_path / "out")


# --------------------------------------------------------------- import guard


def test_import_wraps_stdout_without_buffer_uses_dunder_stdout(monkeypatch):
    monkeypatch.setattr(sys, "path", list(sys.path))
    fake_real = io.TextIOWrapper(io.BytesIO(), encoding="ascii")
    monkeypatch.setattr(sys, "__stdout__", fake_real)
    monkeypatch.setattr(sys, "stdout", io.StringIO())
    saved = sys.stdout
    load(REL, name="l1_w9_v033_nobuffer")
    wrapper = sys.stdout
    assert wrapper is not saved
    assert wrapper.encoding == "utf-8"
    assert wrapper.buffer is fake_real.buffer
    wrapper.detach()


def test_import_falls_back_to_env_when_no_buffer_anywhere(monkeypatch):
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setenv("PYTHONIOENCODING", "x")
    monkeypatch.delenv("PYTHONIOENCODING")
    monkeypatch.setattr(sys, "__stdout__", io.StringIO())
    plain = io.StringIO()
    monkeypatch.setattr(sys, "stdout", plain)
    load(REL, name="l1_w9_v033_noenc")
    assert sys.stdout is plain
    assert os.environ["PYTHONIOENCODING"] == "utf-8"


# ------------------------------------------------------------ PhaseExecution


def test_phase_execution_defaults_and_explicit_values():
    p = mod.PhaseExecution(1, "Define", "running", "t0")
    assert p.agents_involved == []
    assert p.metrics == {}
    assert p.output_files == []
    assert p.end_time is None and p.duration_seconds == 0.0
    q = mod.PhaseExecution(
        2, "M", "done", "t", agents_involved=["a"], metrics={"k": 1}, output_files=["f"]
    )
    assert q.agents_involved == ["a"] and q.metrics == {"k": 1}
    assert q.output_files == ["f"]


# ------------------------------------------------------------ orchestrator


def test_init_creates_directories(orch, tmp_path, capsys):
    out = tmp_path / "out"
    for sub in ("logs", "reports", "canonical_books"):
        assert (out / sub).is_dir()
    assert (tmp_path / "ws" / ".dmaic").is_dir()
    assert orch.phase_executions == []
    assert len(orch.execution_id) == 15


def test_discover_agents(orch, tmp_path):
    assert orch._discover_agents() == []
    a = tmp_path / "ws" / "DMAIC_V3" / "agents"
    b = tmp_path / "ws" / "local_mcp" / "agents"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    (a / "alpha.py").write_text("x")
    (a / "__init__.py").write_text("")
    (a / "notes.txt").write_text("")
    (b / "beta.py").write_text("x")
    assert sorted(orch._discover_agents()) == ["alpha", "beta"]


def test_initialize_temporal_engine(orch, tmp_path):
    assert orch._initialize_temporal_engine() is True
    blocker = tmp_path / "blocker.txt"
    blocker.write_text("x")
    orch.temporal_db_path = blocker / "sub" / "db"
    assert orch._initialize_temporal_engine() is False


def test_load_configuration_and_orchestrators(orch):
    cfg = orch._load_configuration()
    assert cfg["version"] == "v032"
    assert cfg["execution_id"] == orch.execution_id
    assert len(orch._initialize_orchestrators()) == 3
    orch._setup_output_directories()
    for sub in ("knowledge", "metrics", "artifacts"):
        assert (orch.output_dir / sub).is_dir()


def test_scan_artifacts_filters_extensions_git_and_venv(orch, tmp_path):
    ws = tmp_path / "ws"
    (ws / "a.py").write_text("print(1)")
    (ws / "b.md").write_text("# b")
    (ws / "c.yml").write_text("k: v")
    (ws / "d.txt").write_text("ignored")
    (ws / ".git").mkdir()
    (ws / ".git" / "e.json").write_text("{}")
    (ws / "venv").mkdir()
    (ws / "venv" / "f.py").write_text("")
    arts = orch._scan_artifacts()
    by_path = {a["path"]: a for a in arts}
    assert set(by_path) == {"a.py", "b.md", "c.yml"}
    assert by_path["a.py"]["type"] == "py"
    assert by_path["c.yml"]["type"] == "yml"
    assert by_path["a.py"]["size"] == len("print(1)")


def test_canonical_index_and_temporal_metadata(orch):
    arts = [{"path": "x.py"}]
    idx = orch._create_canonical_index(arts)
    data = json.loads(idx.read_text())
    assert data["total_artifacts"] == 1 and data["artifacts"] == arts
    orch._update_temporal_metadata(arts, "phaseX")
    meta = json.loads((orch.output_dir / "temporal_metadata_phaseX.json").read_text())
    assert meta["phase"] == "phaseX" and meta["artifacts_count"] == 1


# ------------------------------------------------------------ phases 0-8


def test_phase_0_success(orch, tmp_path):
    (tmp_path / "ws" / "DMAIC_V3" / "agents").mkdir(parents=True)
    (tmp_path / "ws" / "DMAIC_V3" / "agents" / "ag.py").write_text("")
    p = orch.execute_phase_0_initialization()
    assert p.status == "completed"
    assert p.agents_involved == ["ag"]
    assert p.metrics == {"config_loaded": 4, "orchestrators": 3}
    assert orch.phase_executions == [p]
    assert p.end_time is not None


def test_phase_1_success(orch, tmp_path):
    (tmp_path / "ws" / "m.py").write_text("")
    p = orch.execute_phase_1_define()
    assert p.status == "completed"
    assert p.artifacts_processed == 1
    assert p.output_files[0].endswith("canonical.index.json")
    assert (orch.output_dir / "temporal_metadata_phase1.json").exists()


def test_phase_2_success(orch):
    p = orch.execute_phase_2_measure()
    assert p.status == "completed"
    assert p.metrics == {"complexity_score": 3.5, "quality_score": 85.0, "baselines": 3}
    text = (orch.reports_dir / f"phase_2_measure_{orch.execution_id}.md").read_text()
    assert "quality_score" in text


def test_phase_3_success(orch):
    p = orch.execute_phase_3_analyze()
    assert p.status == "completed"
    assert p.metrics == {
        "patterns_found": 3,
        "dependencies": 2,
        "bottlenecks": 2,
        "root_causes": 2,
    }
    assert "Analyze Report" in Path(p.output_files[0]).read_text()


def test_phase_4_success_and_prioritisation(orch):
    p = orch.execute_phase_4_improve()
    assert p.status == "completed"
    assert p.metrics["proposals"] == 3
    assert p.metrics["high_priority"] == 2
    assert p.metrics["plans"] == 3
    assert p.metrics["expected_improvement"] == 35.0
    ranked = orch._prioritize_improvements(
        [{"id": 1, "impact": "low"}, {"id": 2, "impact": "high"}]
    )
    assert {r["id"]: r["priority"] for r in ranked} == {1: "medium", 2: "high"}
    assert "Improve Report" in Path(p.output_files[0]).read_text()


def test_phase_5_success(orch):
    p = orch.execute_phase_5_control()
    assert p.status == "completed"
    assert p.metrics == {
        "controls": 3,
        "monitors": 3,
        "validation_rules": 3,
        "feedback_loops": 2,
    }
    assert "Control Report" in Path(p.output_files[0]).read_text()


def test_phase_6_success_preserves_knowledge(orch):
    orch.execute_phase_2_measure()
    orch.execute_phase_3_analyze()
    p = orch.execute_phase_6_knowledge_devour()
    assert p.status == "completed"
    assert p.metrics["knowledge_items"] == 2
    assert p.metrics["knowledge_packs"] == 2
    assert p.metrics["recall_keys"] == 2
    assert p.metrics["recall_accuracy"] == 95.0
    pres = orch.output_dir / "knowledge" / f"iteration_{orch.execution_id}"
    packs = json.loads((pres / "knowledge_packs.json").read_text())
    assert [x["pack_id"] for x in packs] == ["pack_000", "pack_001"]
    assert packs[0]["phase"] == "Measure"
    index = json.loads((pres / "knowledge_index.json").read_text())
    assert index["total_packs"] == 2
    # the report is written before the status flips to completed
    assert "## Status: RUNNING" in Path(p.output_files[1]).read_text()


def test_knowledge_helpers(orch):
    packs = orch._create_knowledge_packs([{"phase": "P", "metrics": {"a": 1}}])
    assert packs[0]["name"] == "Knowledge Pack 1"
    assert orch._establish_recall_mechanisms(packs) == ["recall_pack_000"]
    assert orch._build_knowledge_index(packs)["total_packs"] == 1
    assert orch._test_recall_system([]) == 95.0


def test_phase_7_success(orch):
    p = orch.execute_phase_7_integration()
    assert p.status == "completed"
    assert p.metrics["integrations"] == 2
    assert p.metrics["tests_passed"] == 45 and p.metrics["tests_failed"] == 2
    assert p.metrics["coherence_score"] == 92.5
    assert p.metrics["dependencies_resolved"] == 18
    imap = json.loads(Path(p.output_files[0]).read_text())
    assert len(imap["phases"]) == 9
    assert "Integration Report" in Path(p.output_files[1]).read_text()


def test_phase_8_success_writes_reports(orch, tmp_path):
    ws = tmp_path / "ws"
    for i in range(12):
        (ws / f"m{i:02d}.py").write_text("")
    orch.execute_phase_0_initialization()
    orch.phase_executions[0].agents_involved = ["ag1", "ag2"]
    orch.phase_executions.append(
        mod.PhaseExecution(1, "Define", "failed", "t", agents_involved=["ag1"])
    )
    p = orch.execute_phase_8_results_reports()
    assert p.status == "completed"
    books = list(orch.canonical_dir.glob("*_governance.md"))
    assert len(books) == 10
    involvement = json.loads(
        (orch.reports_dir / f"agent_involvement_{orch.execution_id}.json").read_text()
    )
    assert involvement["ag1"] == {
        "phases": ["Initialization", "Define"],
        "total_invocations": 2,
    }
    changelog = (orch.output_dir / f"CHANGELOG_{orch.execution_id}.md").read_text()
    assert "Phase 1: Define" in changelog and "Status: failed" in changelog
    maturity = json.loads(
        (orch.output_dir / f"artifact_maturity_{orch.execution_id}.json").read_text()
    )
    assert maturity["maturity_levels"]["level_3"] == 50
    final = (orch.reports_dir / f"EXECUTION_REPORT_{orch.execution_id}.md").read_text()
    assert "**Total Phases:** 2" in final
    assert "**Failed:** 1" in final
    assert "**Agents:** 2" in final


def test_governance_books_skip_git_and_venv(orch, tmp_path):
    ws = tmp_path / "ws"
    (ws / "venv").mkdir()
    (ws / "venv" / "skip.py").write_text("")
    (ws / "keep.py").write_text("")
    books = orch._generate_canonical_governance_books()
    assert [b.name for b in books] == ["keep_governance.md"]
    assert "keep.py" in books[0].read_text()


def test_execution_summary_counts(orch):
    orch.phase_executions = [
        mod.PhaseExecution(0, "a", "completed", "t", duration_seconds=1.5),
        mod.PhaseExecution(1, "b", "failed", "t", duration_seconds=0.5),
    ]
    s = orch._generate_execution_summary()
    assert s["total_phases"] == 2
    assert s["completed_phases"] == 1 and s["failed_phases"] == 1
    assert s["total_duration"] == 2.0


@pytest.mark.parametrize(
    "runner, helper",
    [
        ("execute_phase_0_initialization", "_discover_agents"),
        ("execute_phase_1_define", "_scan_artifacts"),
        ("execute_phase_2_measure", "_analyze_artifact_complexity"),
        ("execute_phase_3_analyze", "_detect_patterns"),
        ("execute_phase_4_improve", "_generate_improvement_proposals"),
        ("execute_phase_5_control", "_establish_control_mechanisms"),
        ("execute_phase_6_knowledge_devour", "_extract_learning"),
        ("execute_phase_7_integration", "_integrate_improvements"),
        ("execute_phase_8_results_reports", "_generate_execution_summary"),
    ],
)
def test_phase_failure_is_recorded(orch, monkeypatch, capsys, runner, helper):
    def boom(*args, **kwargs):
        raise RuntimeError("kaput")

    monkeypatch.setattr(orch, helper, boom)
    p = getattr(orch, runner)()
    assert p.status == "failed"
    assert p.metrics["error"] == "kaput"
    assert p.end_time is None
    assert orch.phase_executions[-1] is p
    assert "failed: kaput" in capsys.readouterr().out


# Reproduction of a production_defect (see WAVE_LEDGER.jsonl). Named check_*
# so the governed suite does not collect it: a pinned defect must never block the fix.
# Run on demand: pytest -o python_functions=check_* <this file>
def check_production_defect_agent_report_returns_none(orch):
    # Pins production_defect: _create_agent_involvement_report (line 772) has no
    # return, so phase 8 records the string "None" as an output file. Fails once fixed.
    assert orch._create_agent_involvement_report() is None
    p = orch.execute_phase_8_results_reports()
    assert p.output_files[0] == "None"


# Reproduction of a production_defect (see WAVE_LEDGER.jsonl). Named check_*
# so the governed suite does not collect it: a pinned defect must never block the fix.
# Run on demand: pytest -o python_functions=check_* <this file>
def check_production_defect_prioritize_sorts_medium_first(orch):
    # Pins production_defect: _prioritize_improvements (line 853) sorts the priority
    # strings in reverse alphabetical order, so "medium" ranks above "high".
    ranked = orch._prioritize_improvements(
        [{"id": 1, "impact": "high"}, {"id": 2, "impact": "low"}]
    )
    assert [r["id"] for r in ranked] == [2, 1]
