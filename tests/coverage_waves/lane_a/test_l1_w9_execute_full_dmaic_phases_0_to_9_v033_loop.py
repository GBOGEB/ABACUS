"""Behaviour tests for ABACUS-v032/execute_full_dmaic_phases_0_to_9_v033.py.

Part 2: phase 9 convergence maths, the iteration loop and main(). Convergence
inputs are stubbed so results never depend on wall-clock durations.
"""

import json
import sys
from pathlib import Path

import pytest

from tests.coverage_waves.lane_a._load import load

REL = "ABACUS-v032/execute_full_dmaic_phases_0_to_9_v033.py"


def _guarded_load():
    saved = sys.stdout
    try:
        return load(REL, name="l1_w9_v033_loop")
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


def _it(n, quality, duration=10.0, passed=True, **extra):
    d = dict(
        iteration=n,
        duration=duration,
        phases_completed=9,
        phases_failed=0,
        quality_score=quality,
        quality_passed=passed,
    )
    d.update(extra)
    return d


LOW_METRICS = {
    "convergence_score": 10.0,
    "quality_trend": "stable",
    "duration_trend": "stable",
    "stability_score": 50.0,
}


# ------------------------------------------------------------ convergence maths


def test_convergence_metrics_insufficient_data(orch):
    m = orch._calculate_convergence_metrics([_it(1, 50)])
    assert m["convergence_score"] == 0.0
    assert m["quality_trend"] == "insufficient_data"


def test_convergence_metrics_improving(orch):
    its = [_it(1, 60, 100.0), _it(2, 80, 50.0), _it(3, 100, 20.0)]
    m = orch._calculate_convergence_metrics(its)
    assert m["quality_trend"] == "improving"
    assert m["duration_trend"] == "improving"
    assert m["duration_improvement"] == pytest.approx(80.0)
    # variance of 60/80/100 is 266.67 -> stability clamps at 0
    assert m["stability_score"] == 0
    assert m["convergence_score"] == pytest.approx(100 * 0.5 + 0 + 80 * 0.2)


def test_convergence_metrics_stable_and_declining(orch):
    stable = orch._calculate_convergence_metrics([_it(1, 70, 0.0), _it(2, 70, 5.0)])
    assert stable["quality_trend"] == "stable"
    assert stable["duration_trend"] == "stable"
    assert stable["stability_score"] == 100
    down = orch._calculate_convergence_metrics([_it(1, 80, 10.0), _it(2, 70, 20.0)])
    assert down["quality_trend"] == "declining"
    assert down["duration_trend"] == "declining"
    assert down["stability_score"] == pytest.approx(75.0)


def test_improvement_deltas(orch):
    short = orch._analyze_improvement_deltas([_it(1, 1)])
    assert short["trend"] == "insufficient_data"
    up = orch._analyze_improvement_deltas([_it(1, 10), _it(2, 30), _it(3, 35)])
    assert up["deltas"] == [20, 5]
    assert up["average_improvement"] == 12.5
    assert up["max_improvement"] == 20 and up["min_improvement"] == 5
    assert up["trend"] == "improving"
    assert orch._analyze_improvement_deltas([_it(1, 5), _it(2, 5)])["trend"] == "stable"
    down = orch._analyze_improvement_deltas([_it(1, 5), _it(2, 1)])
    assert down["trend"] == "declining"


def test_track_knowledge_accumulation(orch):
    its = [_it(1, 1), _it(2, 2)]
    empty = orch._track_knowledge_accumulation(its)
    assert empty == {"total_items": 0, "items_by_iteration": [], "growth_rate": 0}
    kdir = orch.output_dir / "knowledge" / f"iteration_{orch.execution_id}"
    kdir.mkdir(parents=True)
    zero = orch._track_knowledge_accumulation(its)
    assert zero["items_by_iteration"] == [0, 0] and zero["growth_rate"] == 0
    (kdir / "knowledge_pack_1.json").write_text("{}")
    (kdir / "knowledge_pack_2.json").write_text("{}")
    full = orch._track_knowledge_accumulation(its)
    assert full["total_items"] == 4
    assert full["items_by_iteration"] == [2, 2]
    assert full["growth_rate"] == 0.0


def test_detect_convergence(orch):
    ok = orch._detect_convergence(
        {"convergence_score": 96, "stability_score": 95}, {"average_improvement": -0.5}
    )
    assert ok["converged"] is True
    assert ok["reasons"] == ["All convergence criteria met"]
    assert ok["recommendation"] == "System has converged"
    bad = orch._detect_convergence({}, {})
    assert bad["converged"] is False
    assert bad["improvement_delta"] == 100
    assert len(bad["reasons"]) == 3
    assert bad["recommendation"] == "Continue iterating"


def test_convergence_recommendations(orch):
    yes = orch._generate_convergence_recommendations({"converged": True}, {})
    assert len(yes) == 3 and "converged" in yes[0]
    status = {"converged": False, "convergence_score": 50, "stability_score": 50}
    no = orch._generate_convergence_recommendations(status, {"average_improvement": -2})
    assert len(no) == 5
    status = {"converged": False, "convergence_score": 99, "stability_score": 99}
    minimal = orch._generate_convergence_recommendations(status, {})
    assert len(minimal) == 2


def test_iteration_comparison(orch):
    one = orch._generate_iteration_comparison([_it(1, 50.0, passed=False)])
    text = one.read_text(encoding="utf-8")
    assert "| 1 | 10.00s | 9/9 | 50.0 |" in text
    assert "Quality Change" not in text
    two = orch._generate_iteration_comparison([_it(1, 50.0), _it(2, 70.0)])
    text = two.read_text(encoding="utf-8")
    assert "**Quality Change:** +20.0 points" in text
    assert "**Total Iterations:** 2" in text


def test_update_convergence_tracking_appends(orch):
    f = orch._update_convergence_tracking(1, {"a": 1}, {"converged": False})
    assert len(json.loads(f.read_text())) == 1
    orch._update_convergence_tracking(2, {"a": 2}, {"converged": True})
    data = json.loads(f.read_text())
    assert [d["iteration"] for d in data] == [1, 2]
    f.write_text(json.dumps({"iteration": 0}))
    orch._update_convergence_tracking(3, {}, {})
    data = json.loads(f.read_text())
    assert [d["iteration"] for d in data] == [0, 3]


def test_phase_9_report_content(orch):
    status = {
        "converged": True,
        "convergence_score": 97.0,
        "stability_score": 99.0,
        "improvement_delta": 0.1,
        "reasons": ["All convergence criteria met"],
        "recommendation": "System has converged",
    }
    path = orch._generate_phase_9_report(3, {}, {}, {}, status, ["do it"])
    text = path.read_text(encoding="utf-8")
    assert "**Iteration:** 3" in text
    assert "- do it" in text
    assert "- All convergence criteria met" in text
    assert "**Next Action:** System has converged" in text
    assert "**Quality Trend:** N/A" in text


# ------------------------------------------------------------ phase 9


def test_phase_9_single_iteration(orch):
    p = orch.execute_phase_9_recursive_loop(1, [_it(1, 100)])
    assert p.status == "completed"
    assert p.metrics == {
        "convergence_score": 0.0,
        "converged": False,
        "improvement_delta": 0.0,
        "knowledge_items": 0,
    }
    assert len(p.output_files) == 3
    assert orch.phase_executions[-1] is p
    assert (orch.output_dir / "convergence_tracking.json").exists()


def test_phase_9_converged(orch, monkeypatch):
    monkeypatch.setattr(
        orch,
        "_calculate_convergence_metrics",
        lambda its: {"convergence_score": 99.0, "stability_score": 100.0},
    )
    p = orch.execute_phase_9_recursive_loop(2, [_it(1, 100), _it(2, 100)])
    assert p.metrics["converged"] is True
    report = Path(p.output_files[0]).read_text(encoding="utf-8")
    assert "CONVERGED" in report


def test_phase_9_failure_reraises(orch, monkeypatch):
    def boom(its):
        raise ValueError("nope")

    monkeypatch.setattr(orch, "_calculate_convergence_metrics", boom)
    with pytest.raises(ValueError, match="nope"):
        orch.execute_phase_9_recursive_loop(1, [])
    assert orch.phase_executions[-1].status == "failed"
    assert orch.phase_executions[-1].end_time is not None


# ------------------------------------------------------------ iteration helpers


def test_run_single_iteration(orch):
    summary = orch._run_single_iteration(1)
    assert summary["iteration"] == 1
    assert summary["phases_completed"] == 9
    assert summary["phases_failed"] == 0
    assert [p.phase_number for p in orch.phase_executions] == list(range(9))


def test_check_iteration_quality(orch):
    good = orch._check_iteration_quality(
        {"phases_failed": 0, "phases_completed": 9, "duration": 1.0}
    )
    assert good == {
        "quality_score": 100,
        "passed": True,
        "issues": [],
        "recommendations": [],
    }
    bad = orch._check_iteration_quality(
        {"phases_failed": 2, "phases_completed": 7, "duration": 400.0}
    )
    assert bad["quality_score"] == 0 and bad["passed"] is False
    assert bad["recommendations"] == [
        "Review failed phases and fix errors",
        "Ensure all phases are properly executed",
        "Optimize phase execution time",
    ]


def test_apply_tweaks(orch):
    check = {
        "recommendations": [
            "Review failed phases and fix errors",
            "Ensure all phases are properly executed",
            "Optimize phase execution time",
        ]
    }
    orch._apply_tweaks(check, 4)
    data = json.loads((orch.output_dir / "tweaks_iteration_4.json").read_text())
    assert data["tweaks"] == [
        "error_handling_improved",
        "dependencies_reconfigured",  # "failed phases" also mentions phases
        "dependencies_reconfigured",
        "execution_optimized",
    ]
    orch._apply_tweaks({}, 5)
    data = json.loads((orch.output_dir / "tweaks_iteration_5.json").read_text())
    assert data["tweaks"] == []


def test_next_steps(orch):
    early = orch._generate_next_steps(1, {"phases_failed": 2})
    assert early[0] == "Fix 2 failed phases"
    assert "Prepare for iteration 2" in early
    late = orch._generate_next_steps(3, {})
    assert late[0] == "Finalize all outputs and reports"
    assert len(late) == 4


def test_update_canonical_input_and_changelog(orch):
    orch.phase_executions = [
        mod.PhaseExecution(0, "Init", "completed", "t", artifacts_processed=4)
    ]
    summary = {"duration": 2.0, "phases_completed": 9, "phases_failed": 0}
    f = orch._update_canonical_input(1, summary)
    data = json.loads(f.read_text())
    assert data["version"] == "v032.1"
    assert data["metrics"]["success_rate"] == 100.0
    assert data["artifacts"]["by_phase"] == {"Init": 4}
    orch._update_canonical_input(2, summary)
    log = (orch.canonical_dir / "CHANGELOG.md").read_text()
    assert log.count("# ABACUS v033 - Changelog") == 1
    assert "## Version v032.1" in log and "## Version v032.2" in log
    assert "- Phase 0 (Init): completed" in log


def test_global_task_tracker(orch):
    its = [_it(1, 70), _it(2, 100)]
    del its[0]["quality_score"]
    f = orch._create_global_task_tracker(its)
    text = f.read_text()
    assert "Quality Score: N/A" in text
    assert "Total Phases Executed: 18" in text
    assert "Average Success Rate: 100.0%" in text


def test_final_report(orch):
    phases = [
        dict(phase_number=0, status="completed", duration_seconds=1.0, metrics={}),
        dict(
            phase_number=1,
            status="failed",
            duration_seconds=0.5,
            metrics={"a": 1, "b": 2, "c": 3},
        ),
    ]
    its = [_it(1, 40, passed=False), _it(2, 100, phases=phases, code_quality=88)]
    f = orch._generate_final_report(its)
    text = f.read_text(encoding="utf-8")
    assert "**Success Rate:** 50.0%" in text
    assert "| Phase 1 | " in text and "a: 1, b: 2 |" in text
    assert "c: 3" not in text
    assert "**Code Quality:** 88" in text
    assert "**Test Coverage:** N/A" in text


# ------------------------------------------------------------ main loop


def test_execute_all_phases_real_run_without_convergence(orch, monkeypatch, capsys):
    monkeypatch.setattr(orch, "_calculate_convergence_metrics", lambda its: LOW_METRICS)
    results = orch.execute_all_phases()
    assert [r["iteration"] for r in results] == [1, 2, 3, 4, 5]
    assert all(r["quality_passed"] for r in results)
    assert len(results[0]["phases"]) == 9
    out = capsys.readouterr().out
    assert "[CONVERGENCE PENDING]" in out
    assert list(orch.reports_dir.glob("FINAL_REPORT_*.md"))


def _stub_iteration(failed):
    def run(iteration_num, all_iterations=None):
        return {
            "iteration": iteration_num,
            "duration": 1.0,
            "phases_completed": 9 - failed,
            "phases_failed": failed,
            "timestamp": "t",
        }

    return run


def test_execute_all_phases_converges_early(orch, monkeypatch, capsys):
    monkeypatch.setattr(orch, "_run_single_iteration", _stub_iteration(0))

    def phase9(iteration, its):
        return mod.PhaseExecution(
            9, "Recursive Loop", "completed", "t", metrics={"converged": iteration == 2}
        )

    monkeypatch.setattr(orch, "execute_phase_9_recursive_loop", phase9)
    results = orch.execute_all_phases()
    assert len(results) == 2
    out = capsys.readouterr().out
    assert "System converged in iteration 2" in out
    assert "[CONVERGENCE ACHIEVED]" in out


def test_execute_all_phases_quality_never_passes(orch, monkeypatch, capsys):
    monkeypatch.setattr(orch, "_run_single_iteration", _stub_iteration(3))
    monkeypatch.setattr(orch, "_calculate_convergence_metrics", lambda its: LOW_METRICS)
    results = orch.execute_all_phases()
    assert len(results) == 5
    assert not any(r["quality_passed"] for r in results)
    out = capsys.readouterr().out
    assert "Continuing to iteration 6" in out


def test_main_real_run_in_sandbox(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mod, "__file__", str(tmp_path / "fake_script.py"))
    monkeypatch.setattr(
        mod.FullDMAICOrchestrator,
        "_calculate_convergence_metrics",
        lambda self, its: LOW_METRICS,
    )
    assert mod.main() == 0
    assert (tmp_path / "STATS" / "DMAIC_FULL" / "reports").is_dir()
    out = capsys.readouterr().out
    assert "Total iterations: 5" in out
    assert "Final quality score: 100.00" in out
    assert "Convergence status" not in out


def test_main_reports_phase_9_when_present(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(mod, "__file__", str(tmp_path / "fake_script.py"))
    canned = [
        dict(
            quality_score=90.0,
            quality_passed=True,
            phases=[
                dict(phase_number=8, metrics={}),
                dict(
                    phase_number=9,
                    metrics={"converged": True, "convergence_score": 97.5},
                ),
            ],
        )
    ]
    monkeypatch.setattr(
        mod.FullDMAICOrchestrator, "execute_all_phases", lambda self: canned
    )
    assert mod.main() == 0
    out = capsys.readouterr().out
    assert "Convergence score: 97.5%" in out


def test_main_returns_1_on_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(mod, "__file__", str(tmp_path / "fake_script.py"))

    def boom(self):
        raise RuntimeError("broken")

    monkeypatch.setattr(mod.FullDMAICOrchestrator, "execute_all_phases", boom)
    assert mod.main() == 1
    assert "Execution failed: broken" in capsys.readouterr().out


# Reproduction of a production_defect (see WAVE_LEDGER.jsonl). Named check_*
# so the governed suite does not collect it: a pinned defect must never block the fix.
# Run on demand: pytest -o python_functions=check_* <this file>
def check_production_defect_knowledge_glob_never_matches(orch):
    # Pins production_defect: _track_knowledge_accumulation (line 1196) globs
    # "knowledge_pack_*.json" but _preserve_knowledge writes "knowledge_packs.json",
    # so real phase 6 output is never counted. Fails once fixed.
    orch.execute_phase_2_measure()
    orch.execute_phase_6_knowledge_devour()
    growth = orch._track_knowledge_accumulation([_it(1, 1)])
    assert growth["total_items"] == 0


# Reproduction of a production_defect (see WAVE_LEDGER.jsonl). Named check_*
# so the governed suite does not collect it: a pinned defect must never block the fix.
# Run on demand: pytest -o python_functions=check_* <this file>
def check_production_defect_phase_9_missing_from_results(orch, monkeypatch):
    # Pins production_defect: execute_all_phases (line 1699) snapshots phases before
    # phase 9 runs, so main() can never report convergence. Fails once fixed.
    monkeypatch.setattr(orch, "_calculate_convergence_metrics", lambda its: LOW_METRICS)
    results = orch.execute_all_phases()
    numbers = [p["phase_number"] for p in results[-1]["phases"]]
    assert 9 not in numbers
