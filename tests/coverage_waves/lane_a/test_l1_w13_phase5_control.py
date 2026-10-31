"""Wave 13 lane A behaviour tests for DMAIC_V3/phases/phase5_control.py."""

import importlib
import json
import sys
from types import SimpleNamespace

import pytest


def _import_restoring_sys_path():
    # phase5_control inserts the repo root at sys.path[0] on import.
    saved = list(sys.path)
    try:
        return importlib.import_module("DMAIC_V3.phases.phase5_control")
    finally:
        sys.path[:] = saved


p5 = _import_restoring_sys_path()


class FakeGBOGEB:
    instances = []

    def __init__(self, workspace):
        self.workspace = workspace
        self.metrics = []
        self.victory = []
        FakeGBOGEB.instances.append(self)

    def collect_metric(self, **kwargs):
        self.metrics.append(kwargs)

    def set_victory_criteria(self, name, target_value, current_value):
        self.victory.append((name, target_value, current_value))

    def generate_audit_trail(self):
        return "audit.json"


def _cfg(tmp_path):
    return SimpleNamespace(paths=SimpleNamespace(output_root=tmp_path / "out"))


def _phase(tmp_path, use_gbogeb=False):
    return p5.Phase5Control(_cfg(tmp_path), state_manager=None, use_gbogeb=use_gbogeb)


def _write_phase4(tmp_path, data, iteration=1):
    d = tmp_path / "out" / f"iteration_{iteration}" / "phase4_improve"
    d.mkdir(parents=True, exist_ok=True)
    (d / "phase4_improve.json").write_text(json.dumps(data), encoding="utf-8")


def test_init_without_gbogeb(tmp_path):
    ph = _phase(tmp_path, use_gbogeb=True)
    # GBOGEB is not importable in CI, so it is disabled regardless of the flag.
    assert ph.use_gbogeb is p5.GBOGEB_AVAILABLE
    if not p5.GBOGEB_AVAILABLE:
        assert ph.gbogeb is None
    assert ph.output_dir == tmp_path / "out"


def test_run_skips_when_phase4_missing(tmp_path):
    ok, res = _phase(tmp_path).run(1)
    assert ok is True
    assert res["skipped"] is True
    assert res["input_source"] == "N/A"
    assert res["reason"] == "Phase 4 results not found"


def test_skip_result_with_explicit_source(tmp_path):
    res = _phase(tmp_path)._create_skip_result(3, input_source="x.json")
    assert res["input_source"] == "x.json"
    assert res["iteration"] == 3


def test_run_all_gates_pass_writes_output(tmp_path):
    _write_phase4(
        tmp_path, {"statistics": {"total_modifications": 4, "docstrings_added": 2}}
    )
    ok, res = _phase(tmp_path).run(1)
    assert ok is True
    assert res["all_gates_passed"] is True
    assert res["quality_gates"]["code_quality"]["value"] == 4
    assert res["quality_gates"]["documentation"]["value"] == 2
    expected_controls = dict(
        total_gates=4,
        passed=4,
        failed=0,
        gates_details=res["quality_gates"],
    )
    assert res["controls"] == expected_controls
    assert len(res["validation_checkpoints"]) == 4
    assert res["validation_checkpoints"][0]["name"] == "code_quality_checkpoint"
    out = tmp_path / "out" / "iteration_1" / "phase5_control" / "phase5_control.json"
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["success"] is True
    assert saved["gbogeb_enabled"] is False


def test_run_failing_gate_when_no_improvements(tmp_path, capsys):
    _write_phase4(tmp_path, {})
    ok, res = _phase(tmp_path).run(1)
    assert ok is True
    assert res["all_gates_passed"] is False
    assert res["controls"]["failed"] == 1
    assert "SOME GATES FAILED" in capsys.readouterr().out


def test_code_quality_falls_back_to_improvement_list_and_total(tmp_path):
    ph = _phase(tmp_path)
    assert ph._check_code_quality({"improvements": [1, 2, 3]})["value"] == 3
    assert ph._check_code_quality({"total_improvements": 7})["value"] == 7
    res = ph._check_code_quality({"improvements": [], "total_improvements": 0})
    assert res["passed"] is False
    assert res["message"] == "0 improvements made"


def test_documentation_and_placeholder_gates(tmp_path):
    ph = _phase(tmp_path)
    assert ph._check_documentation({})["passed"] is True
    assert ph._check_test_coverage({})["value"] == 100
    assert ph._check_performance({})["passed"] is True


def test_validation_checkpoint_defaults(tmp_path):
    cps = _phase(tmp_path)._create_validation_checkpoints({"g": dict(passed=False)}, 1)
    assert cps == [
        dict(
            name="g_checkpoint",
            description="Validation checkpoint for g",
            passed=False,
            value=0,
            message="",
        )
    ]


def test_run_with_gbogeb_collects_metrics(tmp_path, monkeypatch):
    monkeypatch.setattr(p5, "GBOGEB_AVAILABLE", True)
    monkeypatch.setattr(p5, "GBOGEB", FakeGBOGEB, raising=False)
    ph = _phase(tmp_path, use_gbogeb=True)
    assert isinstance(ph.gbogeb, FakeGBOGEB)
    assert ph.gbogeb.workspace.endswith("gbogeb_workspace")
    _write_phase4(tmp_path, {"total_improvements": 1})
    ok, res = ph.run(1)
    assert ok is True
    assert res["gbogeb_enabled"] is True
    names = [m["metric_name"] for m in ph.gbogeb.metrics]
    assert "quality_gate_code_quality" in names
    assert "quality_gates_passed" in names
    assert ph.gbogeb.victory == [("all_quality_gates_passed", 4, 4)]


def test_run_handles_corrupt_json(tmp_path):
    d = tmp_path / "out" / "iteration_2" / "phase4_improve"
    d.mkdir(parents=True)
    (d / "phase4_improve.json").write_text("{bad", encoding="utf-8")
    ok, res = _phase(tmp_path).run(2)
    assert ok is False
    assert res["quality_gates"] == {}
    assert res["all_gates_passed"] is False
    assert "error" in res


@pytest.mark.parametrize(
    "returned, ok, key",
    [
        ((True, {"a": 1}), True, "a"),
        ((1, "text"), True, "raw_payload_type"),
        ((), False, "error"),
        ({"success": False}, False, "success"),
        ({"error": "x"}, False, "error"),
        ({"phase": "CONTROL"}, True, "phase"),
        (42, False, "raw_result_type"),
    ],
)
def test_execute_normalises_run_results(tmp_path, monkeypatch, returned, ok, key):
    ph = _phase(tmp_path)
    monkeypatch.setattr(ph, "run", lambda iteration: returned)
    success, payload = ph.execute(5)
    assert success is ok
    assert key in payload


def test_execute_reports_payload_type(tmp_path, monkeypatch):
    ph = _phase(tmp_path)
    monkeypatch.setattr(ph, "run", lambda iteration: (True, ["x"]))
    success, payload = ph.execute(1)
    assert success is True
    assert payload["raw_payload_type"] == "list"
    assert payload["iteration"] == 1


def test_main_usage_without_argument(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["phase5_control.py"])
    assert p5.main() == 1
    assert "Usage" in capsys.readouterr().out


def test_main_runs_phase(tmp_path, monkeypatch):
    from DMAIC_V3 import config as cfg_mod
    from DMAIC_V3.core import state as state_mod

    class FakeConfig:
        def __init__(self):
            self.paths = SimpleNamespace(output_root=tmp_path / "out")

    monkeypatch.setattr(cfg_mod, "DMAICConfig", FakeConfig)
    monkeypatch.setattr(state_mod, "StateManager", lambda path: SimpleNamespace())
    monkeypatch.setattr(sys, "argv", ["phase5_control.py", "1"])
    # Phase 4 output missing -> skip result, which has no error -> exit code 0.
    assert p5.main() == 0
