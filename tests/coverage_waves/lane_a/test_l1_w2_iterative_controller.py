"""Lane A wave 2: DMAIC_V3.convergence.iterative_controller."""

import json

import pytest

from DMAIC_V3.convergence import iterative_controller as ic

ALL_PHASES = [
    "phase0_init",
    "phase1_define",
    "phase2_measure",
    "phase3_analyze",
    "phase4_improve",
    "phase5_control",
]


@pytest.fixture
def ctl(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    return ic.IterativeController(ws, tmp_path / "out", max_iterations=4)


def _metrics(i, files, changes, maturity="initial"):
    return ic.IterationMetrics(
        iteration=i,
        files_processed=files,
        changes_detected=changes,
        maturity_level=maturity,
    )


def test_init_layout(ctl, tmp_path):
    assert ctl.state_dir == tmp_path / "out" / "convergence_state"
    assert ctl.state_dir.is_dir()
    assert ctl.change_detector.state_dir == ctl.state_dir


def test_should_continue_max_and_first(ctl):
    assert ctl.should_continue_iteration(4) == (False, "Maximum iterations (4) reached")
    assert ctl.should_continue_iteration(1) == (True, "Initial iteration")


def test_should_continue_change_and_convergence(ctl):
    # No changes file yet: first run counts as changed, not converged.
    ok, reason = ctl.should_continue_iteration(2)
    assert ok and "continuing iteration 2" in reason

    ctl.change_detector.changes_file.write_text(
        json.dumps({"total_changes": 0}), encoding="utf-8"
    )
    assert ctl.should_continue_iteration(2) == (
        False,
        "No changes detected since last iteration",
    )

    ctl.change_detector.changes_file.write_text(
        json.dumps({"total_changes": 3}), encoding="utf-8"
    )
    ctl.iteration_history = [_metrics(1, 10, 5), _metrics(2, 10, 5, "mature")]
    assert ctl.should_continue_iteration(3) == (False, "System has converged")


def test_is_converged_rules(ctl):
    assert ctl._is_converged() is False
    ctl.iteration_history = [_metrics(1, 10, 9), _metrics(2, 10, 9, "converged")]
    assert ctl._is_converged() is True
    ctl.iteration_history = [_metrics(1, 10, 9), _metrics(2, 100, 4)]
    assert ctl._is_converged() is True
    ctl.iteration_history = [_metrics(1, 10, 9), _metrics(2, 100, 50)]
    assert ctl._is_converged() is False
    ctl.iteration_history = [_metrics(1, 10, 9), _metrics(2, 0, 0)]
    assert ctl._is_converged() is False


def test_convergence_score_first_iterations(ctl):
    assert ctl.calculate_convergence_score(0, 0, ALL_PHASES) == pytest.approx(0.85)
    assert ctl.calculate_convergence_score(10, 10, []) == pytest.approx(0.15)
    assert ctl.calculate_convergence_score(10, 1, ALL_PHASES[:3]) == pytest.approx(
        0.8 * 0.4 + 0.15 + 0.15
    )


def test_convergence_score_uses_history(ctl):
    ctl.iteration_history = [_metrics(1, 10, 5), _metrics(2, 10, 5)]
    falling = ctl.calculate_convergence_score(10, 1, ALL_PHASES)
    assert falling == pytest.approx(0.8 * 0.4 + 0.3 + 0.3)
    rising = ctl.calculate_convergence_score(10, 9, [])
    assert rising == pytest.approx(0.15)
    zero_files = ctl.calculate_convergence_score(0, 0, [])
    assert zero_files == pytest.approx(0.4 + 0.3)
    ctl.iteration_history[-1] = _metrics(2, 0, 0)
    assert ctl.calculate_convergence_score(10, 10, []) == pytest.approx(0.0)


@pytest.mark.parametrize(
    "score,level",
    [
        (0.95, "converged"),
        (0.9, "converged"),
        (0.7, "mature"),
        (0.4, "developing"),
        (0.1, "initial"),
    ],
)
def test_determine_maturity_level(ctl, score, level):
    assert ctl.determine_maturity_level(score, 1) == level


def test_record_iteration_persists_and_reports(ctl, capsys):
    assert ctl.generate_convergence_report() == "No iterations completed yet."
    ctl.record_iteration(1, 10, 1, ALL_PHASES, 1.5)
    ctl.record_iteration(2, 10, 0, ALL_PHASES, 2.0)
    out = capsys.readouterr().out
    assert "[Iteration 2] Metrics:" in out

    metrics = json.loads(ctl.metrics_file.read_text(encoding="utf-8"))
    assert metrics["total_iterations"] == 2 and metrics["max_iterations"] == 4
    status = ctl.get_convergence_status()
    assert status["current_iteration"] == 2
    assert status["is_converged"] is True
    assert status["total_files_processed"] == 20
    assert status["total_execution_time"] == pytest.approx(3.5)

    report = ctl.generate_convergence_report()
    assert "Status: CONVERGED" in report
    assert "Iterations Completed: 2/4" in report
    assert "Iteration 1:" in report and "Time: 2.00s" in report

    fresh = ic.IterativeController(ctl.workspace_root, ctl.output_root)
    fresh.load_history()
    assert [m.iteration for m in fresh.iteration_history] == [1, 2]
    assert fresh.iteration_history[0].phases_executed == ALL_PHASES


def test_report_in_progress(ctl):
    ctl.record_iteration(1, 10, 9, [], 0.1)
    assert "Status: IN PROGRESS" in ctl.generate_convergence_report()


def test_status_and_history_defaults_and_errors(ctl, capsys):
    default = {"is_converged": False, "maturity_level": "initial"}
    assert ctl.get_convergence_status() == default
    ctl.load_history()
    assert ctl.iteration_history == []
    ctl._update_convergence_status()
    assert not ctl.convergence_file.exists()

    ctl.convergence_file.write_text("{bad", encoding="utf-8")
    assert ctl.get_convergence_status() == default
    ctl.metrics_file.write_text("{bad", encoding="utf-8")
    ctl.load_history()
    assert "Error loading history" in capsys.readouterr().out


def test_save_errors_are_reported(ctl, capsys):
    ctl.metrics_file.mkdir()
    ctl.convergence_file.mkdir()
    ctl.record_iteration(1, 1, 1, [], 0.0)
    out = capsys.readouterr().out
    assert "Error saving metrics" in out
    assert "Error updating convergence status" in out
