"""Guard Enterprise CI against false-green pytest verdicts."""

from pathlib import Path

import yaml


WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/dmaic-enterprise-ci.yml"


def test_enterprise_pytest_is_required_on_all_supported_versions():
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    job = workflow["jobs"]["test"]
    assert job["strategy"]["matrix"]["python-version"] == [
        "3.10",
        "3.11",
        "3.12",
    ]
    assert set(job["strategy"]["matrix"]["os"]) == {
        "ubuntu-latest",
        "windows-latest",
        "macos-latest",
    }
    assert job.get("continue-on-error") is not True
    pytest_steps = [
        step
        for step in job["steps"]
        if "pytest --benchmark-disable" in step.get("run", "")
    ]
    assert len(pytest_steps) == 1
    pytest_step = pytest_steps[0]
    assert pytest_step.get("continue-on-error") in (None, False)
    assert "|| true" not in pytest_step["run"]
    assert "| tee" not in pytest_step["run"]


def test_enterprise_summary_requires_real_test_job_success():
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    summary = workflow["jobs"]["summary"]
    assert "test" in summary["needs"]
    final = next(
        step for step in summary["steps"] if step["name"] == "Set final status"
    )
    assert "needs.test.result" in final["run"]
    assert '== "success"' in final["run"]
    assert "exit 1" in final["run"]
