"""Reject missing/stale measurement evidence without weakening quality gates."""
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.test_dmaic_orchestration import DMAICTestOrchestrator


@pytest.mark.asyncio
@pytest.mark.parametrize("exit_code,emit,total", [(4, False, 0), (0, False, 0), (0, True, 0)])
async def test_measurement_rejects_invalid_evidence(tmp_path, monkeypatch, exit_code, emit, total):
    orchestrator = DMAICTestOrchestrator(tmp_path)
    (orchestrator.metrics_dir / "test_report.json").write_text(
        json.dumps({"summary": {"total": 99, "passed": 99}})
    )

    def run(cmd, **kwargs):
        assert kwargs["cwd"] == tmp_path
        assert "--cov" in cmd
        assert "--cov=." not in cmd
        if emit:
            report = Path(next(x.split("=", 1)[1] for x in cmd if x.startswith("--json-report-file=")))
            report.write_text(json.dumps({"summary": {"total": total}}))
            coverage = Path(next(x.split("json:", 1)[1] for x in cmd if x.startswith("--cov-report=")))
            coverage.write_text(json.dumps({"totals": {"percent_covered": 90}}))
        return SimpleNamespace(returncode=exit_code, stdout="output", stderr="diagnostic")

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(RuntimeError):
        await orchestrator.measure_test_performance("tests/example.py")
    assert len(list(orchestrator.metrics_dir.glob("*/stderr.log"))) == 1


@pytest.mark.asyncio
async def test_real_measurement_and_repeat(tmp_path):
    (tmp_path / "test_sample.py").write_text("def test_real():\n    assert 2 + 2 == 4\n")
    orchestrator = DMAICTestOrchestrator(tmp_path)
    for _ in range(2):
        metrics = await orchestrator.measure_test_performance("test_sample.py")
        assert metrics.total_tests == metrics.passed_tests == 1
    assert len(list(orchestrator.metrics_dir.glob("*/test_report.json"))) == 2


@pytest.mark.asyncio
async def test_real_measurement_ignores_parent_coverage_config(tmp_path, monkeypatch):
    """An outer CI config cannot silently omit the nested temporary SUT."""
    (tmp_path / "test_sample.py").write_text(
        "def test_real():\n    assert 2 + 2 == 4\n",
        encoding="utf-8",
    )
    parent_config = tmp_path / "parent-coverage.toml"
    parent_config.write_text(
        "[tool.coverage.run]\n"
        'source = ["."]\n'
        'omit = ["*/test_sample.py"]\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("COVERAGE_RCFILE", str(parent_config))
    metrics = await DMAICTestOrchestrator(tmp_path).measure_test_performance(
        "test_sample.py"
    )
    assert metrics.total_tests == metrics.passed_tests == 1
    assert metrics.coverage_score > 0.0


@pytest.mark.asyncio
async def test_measurement_scrubs_parent_pytest_cov_environment(tmp_path, monkeypatch):
    orchestrator = DMAICTestOrchestrator(tmp_path)
    monkeypatch.setenv("COV_CORE_SOURCE", "outer-source")
    monkeypatch.setenv("COV_CORE_CONFIG", "outer-config")
    monkeypatch.setenv("COV_CORE_DATAFILE", "outer-data")
    monkeypatch.setenv("COVERAGE_PROCESS_START", "outer-start")
    monkeypatch.setenv("COVERAGE_RCFILE", "outer-config.toml")

    def run(cmd, **kwargs):
        child_env = kwargs["env"]
        assert "COVERAGE_PROCESS_START" not in child_env
        assert "COVERAGE_RCFILE" not in child_env
        assert not any(key.startswith("COV_CORE_") for key in child_env)
        assert Path(child_env["COVERAGE_FILE"]).parent.parent == orchestrator.metrics_dir

        report = Path(next(x.split("=", 1)[1] for x in cmd if x.startswith("--json-report-file=")))
        report.write_text(json.dumps({"summary": {"total": 1, "passed": 1, "failed": 0, "skipped": 0}}))
        coverage = Path(next(x.split("json:", 1)[1] for x in cmd if x.startswith("--cov-report=")))
        coverage.write_text(json.dumps({"totals": {"num_statements": 10, "covered_lines": 9, "percent_covered": 90.0}}))
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", run)
    metrics = await orchestrator.measure_test_performance("test_sample.py")
    assert metrics.total_tests == 1
    assert metrics.passed_tests == 1
    assert metrics.coverage_score == 90.0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "suite, module_name",
    [
        ("tests/test_master_doc_manager.py", "master_doc_manager"),
        ("tests/test_user_library_rag.py", "user_library_rag"),
        ("tests/test_action_tracker.py", "action_tracker"),
    ],
)
async def test_component_measurement_uses_declared_source_scope(
    tmp_path, monkeypatch, suite, module_name
):
    """An individual component shall not be measured against the whole repo."""
    orchestrator = DMAICTestOrchestrator(tmp_path)

    def run(cmd, **kwargs):
        assert f"--cov={module_name}" in cmd
        assert "--cov=." not in cmd
        assert "--cov" not in cmd
        assert kwargs["cwd"] == tmp_path
        report = Path(next(x.split("=", 1)[1] for x in cmd
                           if x.startswith("--json-report-file=")))
        report.write_text(json.dumps({
            "summary": {"total": 2, "passed": 2, "failed": 0, "skipped": 0}
        }))
        coverage = Path(next(x.split("json:", 1)[1] for x in cmd
                             if x.startswith("--cov-report=")))
        coverage.write_text(json.dumps({
            "totals": {
                "num_statements": 100, "covered_lines": 83,
                "percent_covered": 76.5,
            }
        }))
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", run)
    metrics = await orchestrator.measure_test_performance(suite)
    assert metrics.total_tests == metrics.passed_tests == 2
    assert metrics.coverage_score == 83.0
    assert metrics.pass_rate() == 100.0


def test_undeclared_measurement_scope_stays_broad():
    """Unknown suite names must not mint optimistic component coverage."""
    assert DMAICTestOrchestrator._coverage_options_for_suite(
        "tests/not_registered.py"
    ) == ["--cov"]
    assert DMAICTestOrchestrator._coverage_options_for_suite(
        "tests/../test_master_doc_manager.py"
    ) == ["--cov"]


@pytest.mark.asyncio
async def test_week3_measurement_covers_all_three_production_modules(
    tmp_path, monkeypatch
):
    """The shared integration denominator uses the three exercised modules."""
    suite = "tests/test_week3_integration.py"
    orchestrator = DMAICTestOrchestrator(tmp_path)
    expected = {
        "--cov=master_doc_manager",
        "--cov=user_library_rag",
        "--cov=action_tracker",
    }

    def run(cmd, **kwargs):
        assert {arg for arg in cmd if arg.startswith("--cov=")} == expected
        assert "--cov=." not in cmd
        assert "--cov" not in cmd
        report = Path(next(x.split("=", 1)[1] for x in cmd
                           if x.startswith("--json-report-file=")))
        report.write_text(json.dumps({
            "summary": {"total": 8, "passed": 8, "failed": 0, "skipped": 0}
        }))
        coverage = Path(next(x.split("json:", 1)[1] for x in cmd
                             if x.startswith("--cov-report=")))
        coverage.write_text(json.dumps({
            "totals": {
                "num_statements": 400, "covered_lines": 300,
                "percent_covered": 72.0,
            }
        }))
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", run)
    metrics = await orchestrator.measure_test_performance(suite)
    assert metrics.total_tests == 8
    assert metrics.passed_tests == 8
    assert metrics.coverage_score == 75.0
