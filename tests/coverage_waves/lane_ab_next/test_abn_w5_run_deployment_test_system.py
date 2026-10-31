"""Behaviour tests for run_deployment_test_system.py.

The DMAIC_V3 collaborators are replaced with in-memory stubs during import and
with recording fakes per test, so no pytest suite or report write happens.
The ``sys.path`` insertion the script makes at import is undone right after.
"""

import sys
import types
from pathlib import Path

import pytest

from tests.coverage_waves.lane_b._l2_loader import load


def _stub_modules():
    names = (
        "DMAIC_V3",
        "DMAIC_V3.config",
        "DMAIC_V3.core",
        "DMAIC_V3.core.state",
        "DMAIC_V3.core.handover_bridge",
        "DMAIC_V3.core.test_system_bridge",
    )
    stubs = {name: types.ModuleType(name) for name in names}
    stubs["DMAIC_V3.config"].DMAICConfig = object
    stubs["DMAIC_V3.core.state"].StateManager = object
    stubs["DMAIC_V3.core.handover_bridge"].HandoverBridge = object
    stubs["DMAIC_V3.core.test_system_bridge"].TestSystemBridge = object
    return stubs


_saved_path = list(sys.path)
mod = load(
    "run_deployment_test_system.py",
    name="abn_run_deployment_test_system",
    deps=_stub_modules(),
)
sys.path[:] = _saved_path


class _Paths:
    def __init__(self):
        self.state_dir = Path("state")
        self.created = 0

    def create_directories(self):
        self.created += 1


class _Config:
    def __init__(self):
        self.paths = _Paths()


class _Metrics:
    def __init__(self, passed, total, errors, static_ok):
        self.version = "v9"
        self.tests_total = total
        self.tests_passed = passed
        self.tests_failed = total - passed
        self.execution_time_seconds = 1.234
        self.runtime_errors = errors
        self.static_analysis_passed = static_ok
        self.deployment_ready = static_ok and passed == total and not errors


class _Result:
    def __init__(self, success):
        self.success = success


def _bridge_cls(metrics, suite_ok=True, evidence=None):
    class _Bridge:
        instances = []

        def __init__(self, config, state_manager, handover_bridge):
            self.config = config
            self.state_manager = state_manager
            self.handover_bridge = handover_bridge
            self.versions = []
            self.suites = []
            self.saved = []
            self.deployment_metrics = None
            if evidence is not None:
                self.static_analysis_evidence = evidence
            _Bridge.instances.append(self)

        def update_version(self, version):
            self.versions.append(version)

        def run_pytest_suite(self, path, markers):
            self.suites.append((path, markers))
            return _Result(suite_ok)

        def generate_deployment_metrics(self):
            return metrics

        def save_deployment_report(self, path):
            self.saved.append(path)
            return path or Path("default_report.json")

    return _Bridge


def _wire(monkeypatch, argv, bridge):
    monkeypatch.setattr(mod, "DMAICConfig", _Config)
    monkeypatch.setattr(mod, "StateManager", lambda state_dir: ("state", state_dir))
    monkeypatch.setattr(mod, "HandoverBridge", lambda cfg, sm: ("handover", sm))
    monkeypatch.setattr(mod, "TestSystemBridge", bridge)
    monkeypatch.setattr(sys, "argv", ["run_deployment_test_system.py"] + argv)


def test_parse_args_defaults(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog"])
    args = mod.parse_args()
    assert args.test_suite == "all"
    assert args.skip_static is False
    assert args.version == "dev"
    assert args.output_dir is None


def test_parse_args_rejects_unknown_suite(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "--test-suite", "bogus"])
    with pytest.raises(SystemExit):
        mod.parse_args()


def test_main_all_suites_ready_returns_zero(monkeypatch, capsys):
    bridge = _bridge_cls(_Metrics(3, 3, [], True))
    _wire(monkeypatch, ["--version", "1.2"], bridge)
    assert mod.main() == 0
    inst = bridge.instances[0]
    assert inst.versions == ["1.2"]
    assert [m for _, m in inst.suites] == ["smoke", "unit", "integration"]
    assert inst.saved == [None]
    assert inst.handover_bridge == ("handover", ("state", Path("state")))
    assert inst.config.paths.created == 1
    out = capsys.readouterr().out
    assert "Smoke tests: PASSED" in out
    assert "Static Analysis: PASSED" in out
    assert "Execution Time: 1.23s" in out
    assert "completed successfully" in out


@pytest.mark.parametrize("suite", ["smoke", "unit", "integration"])
def test_main_single_suite_runs_only_that_marker(monkeypatch, capsys, suite):
    bridge = _bridge_cls(_Metrics(1, 1, [], True), suite_ok=False)
    _wire(monkeypatch, ["--test-suite", suite], bridge)
    assert mod.main() == 0
    assert [m for _, m in bridge.instances[0].suites] == [suite]
    assert "FAILED" in capsys.readouterr().out


def test_main_skip_static_recomputes_ready_and_output_dir(
    monkeypatch, capsys, tmp_path
):
    metrics = _Metrics(2, 2, [], False)
    bridge = _bridge_cls(metrics)
    _wire(
        monkeypatch,
        ["--skip-static", "--test-suite", "smoke", "--output-dir", str(tmp_path)],
        bridge,
    )
    assert mod.main() == 0
    inst = bridge.instances[0]
    assert metrics.static_analysis_passed is True
    assert metrics.deployment_ready is True
    assert inst.deployment_metrics is metrics
    assert inst.saved == [tmp_path / "deployment_report.json"]
    assert "SKIPPED (assumed PASSED)" in capsys.readouterr().out


def test_main_skip_static_still_not_ready_with_runtime_errors(monkeypatch, capsys):
    metrics = _Metrics(2, 2, ["boom"], False)
    bridge = _bridge_cls(metrics)
    _wire(monkeypatch, ["--skip-static", "--test-suite", "unit"], bridge)
    assert mod.main() == 1
    assert metrics.deployment_ready is False
    assert "not ready for deployment" in capsys.readouterr().out


def test_main_static_failure_prints_first_red_evidence(monkeypatch, capsys):
    findings = [
        dict(source_path="a.py", line=i, column=2, rule="F401", message="unused")
        for i in range(7)
    ]
    evidence = dict(status="RED", finding_count=7, findings=findings)
    bridge = _bridge_cls(_Metrics(1, 1, [], False), evidence=evidence)
    _wire(monkeypatch, ["--test-suite", "smoke"], bridge)
    assert mod.main() == 1
    out = capsys.readouterr().out
    assert "Static Analysis: FAILED" in out
    assert "Static first-red evidence: RED findings=7" in out
    assert "a.py:4:2: F401 unused" in out
    assert "a.py:5:2" not in out  # only the first five findings
    assert "Deployment Ready:" in out


def test_main_static_failure_without_evidence_dict(monkeypatch, capsys):
    bridge = _bridge_cls(_Metrics(1, 1, [], False), evidence="not-a-dict")
    _wire(monkeypatch, ["--test-suite", "integration"], bridge)
    assert mod.main() == 1
    assert "first-red evidence" not in capsys.readouterr().out


def test_main_static_failure_evidence_defaults(monkeypatch, capsys):
    bridge = _bridge_cls(_Metrics(1, 1, [], False), evidence={})
    _wire(monkeypatch, ["--test-suite", "integration"], bridge)
    assert mod.main() == 1
    assert "first-red evidence: UNKNOWN findings=None" in capsys.readouterr().out
