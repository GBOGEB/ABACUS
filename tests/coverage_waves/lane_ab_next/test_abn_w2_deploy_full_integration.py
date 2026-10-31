"""Behaviour tests for deploy_full_integration.py (subprocess and clock faked)."""

import json
import logging
import runpy

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

mod = load("deploy_full_integration.py", name="abn_deploy_full_integration")

STEP_KEYS = [
    "staging_deployed",
    "integration_tests_passed",
    "convergence_validated",
    "performance_benchmarked",
    "production_deployed",
    "monitoring_configured",
    "alerts_configured",
]


class _Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _FakeRun:
    """Returns queued results (or raises queued exceptions) and records calls."""

    def __init__(self, *answers, default=None):
        self.answers = list(answers)
        self.default = default or _Result(0, "ok", "")
        self.calls = []

    def __call__(self, cmd, **kwargs):
        self.calls.append((cmd, kwargs))
        answer = self.answers.pop(0) if self.answers else self.default
        if isinstance(answer, Exception):
            raise answer
        return answer


class _Clock:
    """Replacement ``time`` module whose clock advances by fixed steps."""

    def __init__(self, steps):
        self.steps = list(steps)
        self.now = 0.0

    def time(self):
        self.now += self.steps.pop(0) if self.steps else 0.0
        return self.now


def _deployer(tmp_path, monkeypatch, fake_run=None):
    monkeypatch.chdir(tmp_path)
    fake_run = fake_run or _FakeRun()
    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    return mod.FullIntegrationDeployer(), fake_run


def _messages(caplog):
    return "\n".join(r.getMessage() for r in caplog.records)


@pytest.fixture(autouse=True)
def _info_logs(caplog):
    caplog.set_level(logging.INFO, logger=mod.logger.name)


def test_init_state(tmp_path, monkeypatch):
    deployer, _ = _deployer(tmp_path, monkeypatch)
    assert deployer.workspace_root == tmp_path
    assert deployer.deployment_log == []
    assert list(deployer.metrics) == STEP_KEYS
    assert not any(deployer.metrics.values())


def test_run_command_success_records_log(tmp_path, monkeypatch, caplog):
    fake = _FakeRun(_Result(0, "out-", "err"))
    deployer, _ = _deployer(tmp_path, monkeypatch, fake)

    assert deployer.run_command("echo hi", "Say hi") == (True, "out-err")
    cmd, kwargs = fake.calls[0]
    assert cmd == "echo hi"
    assert kwargs["shell"] is True
    assert kwargs["timeout"] == 600
    assert kwargs["capture_output"] is True
    entry = deployer.deployment_log[0]
    assert entry["description"] == "Say hi"
    assert entry["success"] is True
    assert entry["output"] == "out-err"
    assert "Say hi - SUCCESS" in _messages(caplog)


def test_run_command_failure_truncates_output(tmp_path, monkeypatch, caplog):
    long_out = "".join(["x"] * 1500)
    fake = _FakeRun(_Result(2, long_out, ""))
    deployer, _ = _deployer(tmp_path, monkeypatch, fake)

    success, output = deployer.run_command("false", "Break")
    assert success is False
    assert output == long_out
    assert len(deployer.deployment_log[0]["output"]) == 1000
    assert deployer.deployment_log[0]["success"] is False
    assert "Break - FAILED" in _messages(caplog)


def test_run_command_exception_is_not_logged_as_action(tmp_path, monkeypatch, caplog):
    fake = _FakeRun(OSError("no shell"))
    deployer, _ = _deployer(tmp_path, monkeypatch, fake)

    assert deployer.run_command("boom", "Explode") == (False, "no shell")
    assert deployer.deployment_log == []
    assert "Explode - ERROR: no shell" in _messages(caplog)


def test_step_1_without_integration_files(tmp_path, monkeypatch):
    deployer, _ = _deployer(tmp_path, monkeypatch)
    assert deployer.step_1_deploy_staging() is True
    for name in ["DOW", "DMAIC_V3", "INTEGRATED_OUTPUT", "logs", "config"]:
        assert (tmp_path / "staging" / name).is_dir()
    config = json.loads(
        (tmp_path / "staging" / "config" / "staging_config.json").read_bytes()
    )
    assert config["environment"] == "staging"
    assert config["iterations"] == 3
    assert not (tmp_path / "staging" / "UNIFIED_GLOB_CONFIG.yaml").exists()
    assert deployer.metrics["staging_deployed"] is True


def test_step_1_copies_present_integration_files(tmp_path, monkeypatch, caplog):
    (tmp_path / "UNIFIED_GLOB_CONFIG.yaml").write_bytes(b"a: 1\n")
    deployer, _ = _deployer(tmp_path, monkeypatch)
    deployer.step_1_deploy_staging()
    copied = tmp_path / "staging" / "UNIFIED_GLOB_CONFIG.yaml"
    assert copied.read_bytes() == b"a: 1\n"
    assert not (tmp_path / "staging" / "test_integration_bridge.py").exists()
    assert "Copied to staging: UNIFIED_GLOB_CONFIG.yaml" in _messages(caplog)


@pytest.mark.parametrize(
    "codes, expected",
    [([0, 0, 0, 0], True), ([0, 1, 0, 0], True), ([0, 1, 1, 0], False)],
)
def test_step_2_threshold(tmp_path, monkeypatch, caplog, codes, expected):
    fake = _FakeRun(*[_Result(c, "Status: completed", "") for c in codes])
    deployer, _ = _deployer(tmp_path, monkeypatch, fake)

    assert deployer.step_2_run_full_integration_tests() is expected
    assert deployer.metrics["integration_tests_passed"] is expected
    assert len(fake.calls) == 4
    assert all("IntegrationMode." in cmd for cmd, _ in fake.calls)
    passed = codes.count(0)
    assert f"Integration Tests: {passed}/4 PASSED" in _messages(caplog)


@pytest.mark.parametrize(
    "stdout, validated",
    [("Convergence Achieved: True", True), ("ImportError: nothing", False)],
)
def test_step_3_is_non_blocking(tmp_path, monkeypatch, stdout, validated):
    fake = _FakeRun(_Result(0, stdout, ""))
    deployer, _ = _deployer(tmp_path, monkeypatch, fake)

    assert deployer.step_3_validate_convergence() is True
    assert deployer.metrics["convergence_validated"] is validated
    assert fake.calls[0][0].startswith('python -c "')


def test_step_4_benchmarks_and_report(tmp_path, monkeypatch, caplog):
    deployer, fake = _deployer(tmp_path, monkeypatch)
    # Each benchmark reads the clock twice: (start, end) -> durations 4, 20, 22.
    monkeypatch.setattr(mod, "time", _Clock([0.0, 4.0, 1.0, 20.0, 1.0, 22.0]))

    assert deployer.step_4_performance_benchmark() is True
    report = json.loads((tmp_path / "PERFORMANCE_BENCHMARK_REPORT.json").read_bytes())
    durations = [b["duration"] for b in report["benchmarks"]]
    assert durations == [4.0, 20.0, 22.0]
    assert [b["passed"] for b in report["benchmarks"]] == [True, False, True]
    assert report["total"] == 3
    assert report["success_rate"] == pytest.approx(2 / 3)
    assert deployer.metrics["performance_benchmarked"] is True
    assert len(fake.calls) == 3
    assert "iterations=2" in fake.calls[1][0]
    assert "Target: 10.0s" in fake.calls[1][0]
    assert "Standard Execution Benchmark: 20.00s" in _messages(caplog)


def test_step_4_mostly_slow_is_not_benchmarked(tmp_path, monkeypatch):
    deployer, _ = _deployer(tmp_path, monkeypatch)
    monkeypatch.setattr(mod, "time", _Clock([0.0, 100.0, 0.0, 100.0, 0.0, 1.0]))

    assert deployer.step_4_performance_benchmark() is True
    assert deployer.metrics["performance_benchmarked"] is False


def test_production_defect_benchmark_command_breaks_shell_quoting(
    tmp_path, monkeypatch
):
    """production_defect: step_4 benchmark command embeds double quotes inside a shell double-quoted python -c string; this test fails once fixed"""
    deployer, fake = _deployer(tmp_path, monkeypatch)
    monkeypatch.setattr(mod, "time", _Clock([]))
    deployer.step_4_performance_benchmark()

    cmd = fake.calls[0][0]
    assert cmd.startswith('python -c "')
    body = cmd[len('python -c "') : -1]
    # An unescaped '"' inside the body terminates the shell string early, so
    # the shell passes results[status] (a NameError) instead of results["status"].
    assert 'results["status"]' in body


def test_step_5_skips_when_prerequisites_missing(tmp_path, monkeypatch, caplog):
    deployer, _ = _deployer(tmp_path, monkeypatch)
    deployer.metrics["staging_deployed"] = True

    assert deployer.step_5_deploy_production() is False
    assert not (tmp_path / "production").exists()
    assert deployer.metrics["production_deployed"] is False
    assert "NOT ALL PREREQUISITES MET" in _messages(caplog)


def test_step_5_deploys_when_ready(tmp_path, monkeypatch, caplog):
    (tmp_path / "INTEGRATION_GUIDE.md").write_bytes(b"# guide\n")
    deployer, _ = _deployer(tmp_path, monkeypatch)
    for key in STEP_KEYS[:4]:
        deployer.metrics[key] = True

    assert deployer.step_5_deploy_production() is True
    prod = tmp_path / "production"
    for name in ["DOW", "DMAIC_V3", "INTEGRATED_OUTPUT", "logs", "config"]:
        assert (prod / name).is_dir()
    assert (prod / "monitoring").is_dir()
    assert (prod / "INTEGRATION_GUIDE.md").read_bytes() == b"# guide\n"
    assert not (prod / "UNIFIED_GLOB_CONFIG.yaml").exists()
    config = json.loads((prod / "config" / "production_config.json").read_bytes())
    assert config["environment"] == "production"
    assert config["enable_idempotency"] is True
    assert deployer.metrics["production_deployed"] is True
    assert "Deployed to production: INTEGRATION_GUIDE.md" in _messages(caplog)


def test_step_6_writes_monitoring_files(tmp_path, monkeypatch):
    deployer, _ = _deployer(tmp_path, monkeypatch)
    assert deployer.step_6_setup_monitoring() is True
    monitoring = tmp_path / "production" / "monitoring"
    config = json.loads((monitoring / "monitoring_config.json").read_bytes())
    assert config["check_interval_seconds"] == 300
    assert config["thresholds"]["min_success_rate"] == 0.80
    script = (monitoring / "monitor.py").read_text()
    assert "def check_metrics():" in script
    assert "time.sleep(300)" in script
    assert deployer.metrics["monitoring_configured"] is True


@pytest.mark.parametrize("code, configured", [(0, True), (1, False)])
def test_step_7_alerts_follow_handler_result(tmp_path, monkeypatch, code, configured):
    fake = _FakeRun(_Result(code, "", ""))
    deployer, _ = _deployer(tmp_path, monkeypatch, fake)

    assert deployer.step_7_configure_alerts() is True
    monitoring = tmp_path / "production" / "monitoring"
    config = json.loads((monitoring / "alerts_config.json").read_bytes())
    assert [r["name"] for r in config["alert_rules"]] == [
        "High Error Rate",
        "Low Success Rate",
        "Slow Execution",
        "Convergence Failure",
    ]
    assert "def trigger_alert(" in (monitoring / "alert_handler.py").read_text()
    assert fake.calls[0][0] == "python production/monitoring/alert_handler.py"
    assert deployer.metrics["alerts_configured"] is configured


def test_report_complete_lists_last_twenty_actions(tmp_path, monkeypatch):
    deployer, _ = _deployer(tmp_path, monkeypatch)
    for key in STEP_KEYS:
        deployer.metrics[key] = True
    deployer.deployment_log = [
        dict(timestamp="t", description="action-" + str(i), success=i % 2 == 0)
        for i in range(25)
    ]

    report = deployer.generate_deployment_report()
    assert (tmp_path / "FULL_DEPLOYMENT_REPORT.md").read_bytes().decode(
        "utf-8"
    ).replace("\r\n", "\n") == report
    assert "**Status:** ✅ COMPLETE" in report
    assert "Overall Status:** ✅ SUCCESS" in report
    assert "Total Actions: 25" in report
    assert "action-4 " not in report
    assert "1. ✗ action-5 (t)" in report
    assert "20. ✓ action-24 (t)" in report
    assert "**Monitoring:** Enabled" in report


def test_report_partial(tmp_path, monkeypatch):
    deployer, _ = _deployer(tmp_path, monkeypatch)
    deployer.metrics["staging_deployed"] = True

    report = deployer.generate_deployment_report()
    assert "PARTIAL SUCCESS" in report
    assert "| 1 | ✅ | Deploy to Staging Environment |" in report
    assert "| 5 | ❌ | Deploy to Production |" in report
    assert "**Alerts:** Disabled" in report
    assert "Total Actions: 0" in report


def _patch_steps(deployer, monkeypatch, outcomes):
    names = [
        "step_1_deploy_staging",
        "step_2_run_full_integration_tests",
        "step_3_validate_convergence",
        "step_4_performance_benchmark",
        "step_5_deploy_production",
        "step_6_setup_monitoring",
        "step_7_configure_alerts",
    ]
    calls = []

    def make(name, key, outcome):
        def step():
            calls.append(name)
            if isinstance(outcome, Exception):
                raise outcome
            deployer.metrics[key] = bool(outcome)
            return outcome

        return step

    for name, key, outcome in zip(names, STEP_KEYS, outcomes):
        monkeypatch.setattr(deployer, name, make(name, key, outcome))
    return calls


def test_run_full_deployment_all_success(tmp_path, monkeypatch, caplog):
    deployer, _ = _deployer(tmp_path, monkeypatch)
    calls = _patch_steps(deployer, monkeypatch, [True] * 7)

    assert deployer.run_full_deployment() is True
    assert len(calls) == 7
    assert (tmp_path / "FULL_DEPLOYMENT_REPORT.md").exists()
    assert "Steps Completed: 7/7" in _messages(caplog)


def test_run_full_deployment_handles_warnings_and_errors(tmp_path, monkeypatch, caplog):
    deployer, _ = _deployer(tmp_path, monkeypatch)
    outcomes = [True, False, RuntimeError("kaput"), True, False, True, True]
    calls = _patch_steps(deployer, monkeypatch, outcomes)

    assert deployer.run_full_deployment() is False
    assert len(calls) == 7
    text = _messages(caplog)
    assert "Run Full Integration Tests completed with warnings" in text
    assert "Validate Convergence failed: kaput" in text
    assert "Deploy to Production skipped due to unmet prerequisites" in text
    assert "Steps Completed: 4/7" in text


@pytest.mark.parametrize("success, code", [(True, 0), (False, 1)])
def test_main_exit_code(monkeypatch, success, code):
    monkeypatch.setattr(
        mod.FullIntegrationDeployer, "run_full_deployment", lambda self: success
    )
    assert mod.main() == code


def test_full_pipeline_with_fake_shell(tmp_path, monkeypatch):
    output = "Status: completed\nConvergence Achieved: True\n"
    deployer, fake = _deployer(
        tmp_path, monkeypatch, _FakeRun(default=_Result(0, output))
    )
    monkeypatch.setattr(mod, "time", _Clock([]))

    assert deployer.run_full_deployment() is True
    # 4 integration tests + 1 convergence + 3 benchmarks + 1 alert test
    assert len(fake.calls) == 9
    assert (tmp_path / "production" / "config" / "production_config.json").exists()


def test_script_entry_point_exits_with_status(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fake = _FakeRun(default=_Result(1, "", "no bridge"))
    monkeypatch.setattr("subprocess.run", fake)

    with pytest.raises(SystemExit) as exc:
        runpy.run_path(
            str(REPO_ROOT / "deploy_full_integration.py"), run_name="__main__"
        )
    assert exc.value.code == 1
    assert (tmp_path / "FULL_DEPLOYMENT_REPORT.md").exists()
