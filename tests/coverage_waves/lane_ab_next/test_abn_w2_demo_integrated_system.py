"""Behaviour tests for demo_integrated_system.py (time and clock are faked)."""

import json
import runpy

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

mod = load("demo_integrated_system.py", name="abn_demo_integrated_system")


class _FakeTime:
    """Replacement for the ``time`` module: no sleeping, 1 s per clock read."""

    def __init__(self):
        self.sleeps = []
        self.clock = 0.0

    def sleep(self, seconds):
        self.sleeps.append(seconds)

    def time(self):
        self.clock += 1.0
        return self.clock


class _FixedNow:
    def isoformat(self):
        return "2031-05-06T07:08:09"

    def strftime(self, fmt):
        return "20310506_070809"


class _FakeDatetime:
    @staticmethod
    def now():
        return _FixedNow()


def _system(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fake_time = _FakeTime()
    monkeypatch.setattr(mod, "time", fake_time)
    monkeypatch.setattr(mod, "datetime", _FakeDatetime)
    return mod.IntegratedDMAICDOW(), fake_time


def test_init_creates_default_and_custom_workspace(tmp_path, monkeypatch):
    system, _ = _system(tmp_path, monkeypatch)
    assert (tmp_path / "demo_workspace").is_dir()
    assert system.current_iteration == 0
    assert system.metrics == {
        "iterations": [],
        "total_files_processed": 0,
        "total_improvements": 0,
        "success_rate": 100.0,
    }

    other = mod.IntegratedDMAICDOW(workspace_dir="custom_ws")
    assert other.workspace.name == "custom_ws"
    assert (tmp_path / "custom_ws").is_dir()


def test_print_helpers_format_levels(tmp_path, monkeypatch, capsys):
    system, _ = _system(tmp_path, monkeypatch)
    system.print_header("Top", level=1)
    out = capsys.readouterr().out
    assert "Top".center(80) in out
    assert "=" * 80 in out

    system.print_header("Mid", level=2)
    out = capsys.readouterr().out
    assert "-" * 80 in out
    assert "Mid" in out

    system.print_header("Low", level=3)
    out = capsys.readouterr().out
    assert ">>> Low" in out
    assert "=" * 80 not in out

    system.print_success("ok")
    system.print_info("fyi")
    system.print_warning("careful")
    system.print_metric("Speed", 12, "rpm")
    out = capsys.readouterr().out
    assert "✓ ok" in out
    assert "ℹ fyi" in out
    assert "⚠ careful" in out
    assert "Speed:" in out
    assert "12" in out
    assert out.rstrip().endswith("rpm")


def test_simulate_delay_uses_sleep(tmp_path, monkeypatch):
    system, fake_time = _system(tmp_path, monkeypatch)
    system.simulate_delay()
    system.simulate_delay(0.01)
    assert fake_time.sleeps == [0.5, 0.01]


def test_dow_phases_scale_with_iteration(tmp_path, monkeypatch, capsys):
    system, _ = _system(tmp_path, monkeypatch)
    system.current_iteration = 3

    ingest = system.dow_ingest(2)
    assert ingest["files_discovered"] == 100
    assert ingest["total_size_mb"] == 5.0
    assert ingest["file_types"] == ["py", "md", "json", "yaml", "txt"]

    processed = system.dow_process(ingest)
    assert processed["files_processed"] == 100
    assert processed["lines_parsed"] == 15000
    assert processed["tokens_extracted"] == 200000

    analysed = system.dow_analyze(processed)
    assert analysed["quality_score"] == 92.5
    assert analysed["patterns_found"] == 15

    transformed = system.dow_transform(analysed, 4)
    assert transformed == {
        "phase": "transform",
        "improvements_applied": 9,
        "files_modified": 18,
        "lines_changed": 225,
        "quality_improvement": 4.5,
    }

    output = system.dow_output(transformed)
    assert output["git_ready"] is True
    assert output["commit_message"] == "DMAIC Iteration 3: Applied 9 improvements"

    out = capsys.readouterr().out
    assert "Discovered 100 files" in out
    assert "Applied 9 improvements" in out
    assert "Ready for commit" in out


def test_dmaic_phases(tmp_path, monkeypatch, capsys):
    system, _ = _system(tmp_path, monkeypatch)

    define = system.dmaic_define(2)
    assert define["iteration"] == 2
    assert len(define["goals"]) == 4
    assert define["scope"] == "Iteration 2 - Full workspace analysis"

    analysed = {"quality_score": 91.0, "complexity_score": 6.5, "patterns_found": 7}
    measure = system.dmaic_measure(analysed)
    assert measure["baseline_quality"] == 91.0
    assert measure["baseline_complexity"] == 6.5
    assert measure["baseline_patterns"] == 7
    assert measure["measurement_timestamp"] == "2031-05-06T07:08:09"

    analysis = system.dmaic_analyze(measure, 3)
    assert analysis["opportunities_identified"] == 11
    assert analysis["priority_actions"] == 5
    assert analysis["estimated_impact"] == "+6% quality improvement"

    transform = {
        "improvements_applied": 6,
        "files_modified": 12,
        "quality_improvement": 3.0,
    }
    improve = system.dmaic_improve(transform)
    assert improve["solutions_implemented"] == 6
    assert improve["files_improved"] == 12
    assert improve["quality_gain"] == 3.0
    assert improve["implementation_success"] is True

    control = system.dmaic_control(3, {})
    assert control["iteration"] == 3
    assert control["regression_detected"] is False
    assert control["control_metrics"]["quality_threshold"] == 90.0

    out = capsys.readouterr().out
    assert "Improve code quality" in out
    assert "Code duplication" in out
    assert "Quality Maintained" in out


def test_run_iteration_accumulates_metrics(tmp_path, monkeypatch, capsys):
    system, fake_time = _system(tmp_path, monkeypatch)

    summary = system.run_iteration(1)
    assert system.current_iteration == 1
    assert summary["iteration"] == 1
    assert summary["duration_seconds"] == 1.0
    assert summary["files_processed"] == 75
    assert summary["improvements_applied"] == 6
    assert summary["quality_improvement"] == 3.0
    assert summary["success"] is True
    assert summary["timestamp"] == "2031-05-06T07:08:09"
    assert set(summary["all_data"]) == {
        "dmaic_define",
        "dow_ingest",
        "dow_process",
        "dow_analyze",
        "dmaic_measure",
        "dmaic_analyze",
        "dow_transform",
        "dmaic_improve",
        "dow_output",
        "dmaic_control",
    }
    assert len(fake_time.sleeps) == 10

    system.run_iteration(2)
    assert system.metrics["total_files_processed"] == 75 + 100
    assert system.metrics["total_improvements"] == 6 + 7
    assert [i["iteration"] for i in system.metrics["iterations"]] == [1, 2]
    assert "Iteration 2 completed successfully!" in capsys.readouterr().out


def test_compare_iterations_needs_two(tmp_path, monkeypatch, capsys):
    system, _ = _system(tmp_path, monkeypatch)
    assert system.compare_iterations() is None
    out = capsys.readouterr().out
    assert "Need at least 2 iterations to compare" in out
    assert "TREND ANALYSIS" not in out


def test_compare_iterations_reports_trends(tmp_path, monkeypatch, capsys):
    system, _ = _system(tmp_path, monkeypatch)
    system.metrics["iterations"] = [
        dict(
            iteration=1,
            files_processed=100,
            improvements_applied=4,
            quality_improvement=1.5,
            duration_seconds=2.0,
        ),
        dict(
            iteration=2,
            files_processed=150,
            improvements_applied=6,
            quality_improvement=2.5,
            duration_seconds=3.0,
        ),
    ]
    system.compare_iterations()
    out = capsys.readouterr().out
    assert "TREND ANALYSIS" in out
    assert "+50.0%" in out
    assert "Cumulative Quality Gain" in out
    assert "+4.0%" in out
    assert "Avg Files/Iteration" in out
    assert "125" in out
    assert "2.50s" in out
    assert "50.0 files/sec" in out


def test_generate_final_report_writes_json(tmp_path, monkeypatch, capsys):
    system, _ = _system(tmp_path, monkeypatch)
    system.run_iteration(1)
    capsys.readouterr()

    system.generate_final_report()
    report = tmp_path / "demo_workspace" / "integration_report_20310506_070809.json"
    data = json.loads(report.read_bytes())
    assert data["total_files_processed"] == 75
    assert data["total_improvements"] == 6
    assert len(data["iterations"]) == 1

    out = capsys.readouterr().out
    assert "FINAL INTEGRATION REPORT" in out
    assert "Total Iterations" in out
    assert "Quality Gates: Passed" in out
    assert "Report saved to:" in out


def test_main_runs_five_iterations(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    fake_time = _FakeTime()
    monkeypatch.setattr(mod, "time", fake_time)
    monkeypatch.setattr(mod, "datetime", _FakeDatetime)

    assert mod.main() is None

    out = capsys.readouterr().out
    assert "INTEGRATED DEMONSTRATION" in out
    assert out.count("Preparing next iteration") == 4
    assert "ITERATION COMPARISON & ANALYSIS" in out
    assert "SUCCESS - DEMONSTRATION COMPLETE" in out
    assert fake_time.sleeps.count(1) == 5
    report = tmp_path / "demo_workspace" / "integration_report_20310506_070809.json"
    data = json.loads(report.read_bytes())
    assert [i["iteration"] for i in data["iterations"]] == [1, 2, 3, 4, 5]
    assert data["total_files_processed"] == sum(50 + 25 * i for i in range(1, 6))


def test_script_entry_point(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    fake_time = _FakeTime()
    monkeypatch.setattr("time.sleep", fake_time.sleep)
    monkeypatch.setattr("time.time", fake_time.time)

    runpy.run_path(str(REPO_ROOT / "demo_integrated_system.py"), run_name="__main__")

    assert "SUCCESS - DEMONSTRATION COMPLETE" in capsys.readouterr().out
    reports = list((tmp_path / "demo_workspace").glob("integration_report_*.json"))
    assert len(reports) == 1
