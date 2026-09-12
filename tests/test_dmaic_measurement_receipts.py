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
