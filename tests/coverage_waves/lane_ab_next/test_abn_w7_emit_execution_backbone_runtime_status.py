"""Gap tests for scripts/emit_execution_backbone_runtime_status.py."""

import json
import sys
from pathlib import Path

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

REL = "scripts/emit_execution_backbone_runtime_status.py"
mod = load(REL, name="abn_w7_emit_execution_backbone_runtime_status")


class _Backbone:
    def __init__(self, metrics):
        self.metrics = metrics
        self.calls = 0

    def get_metrics(self):
        self.calls += 1
        return self.metrics


def test_wait_for_completion_times_out_without_polling():
    backbone = _Backbone(dict(tasks_executed=0, tasks_failed=0, queue_size=1))
    assert mod._wait_for_completion(backbone, 2, timeout_seconds=0) == "timeout"
    assert backbone.calls == 0


def test_wait_for_completion_times_out_when_queue_never_drains(monkeypatch):
    clock = iter([0.0, 0.0, 10.0])
    monkeypatch.setattr(mod.time, "time", lambda: next(clock))
    monkeypatch.setattr(mod.time, "sleep", lambda seconds: None)
    backbone = _Backbone(dict(tasks_executed=2, tasks_failed=0, queue_size=3))
    assert mod._wait_for_completion(backbone, 2, timeout_seconds=1.0) == "timeout"
    assert backbone.calls == 1


def _write_main(monkeypatch, tmp_path, status):
    seen = {}

    def fake_build(timeout_seconds):
        seen["timeout"] = timeout_seconds
        return dict(status=status, schema_version="0.1.0")

    monkeypatch.setattr(mod, "build_execution_backbone_runtime_status", fake_build)
    out = tmp_path / "reports" / "nested" / "status.json"
    return seen, out


def test_main_writes_report_and_returns_zero_when_ok(monkeypatch, tmp_path, capsys):
    seen, out = _write_main(monkeypatch, tmp_path, "ok")
    rc = mod.main(["--output", str(out), "--timeout-seconds", "0.5"])
    assert rc == 0
    assert seen["timeout"] == 0.5
    assert json.loads(out.read_text(encoding="utf-8"))["status"] == "ok"
    assert json.loads(capsys.readouterr().out)["schema_version"] == "0.1.0"


def test_main_returns_one_on_attention(monkeypatch, tmp_path, capsys):
    seen, out = _write_main(monkeypatch, tmp_path, "attention")
    assert mod.main(["--output", str(out)]) == 1
    assert seen["timeout"] == 5.0
    assert '"attention"' in capsys.readouterr().out


def test_module_inserts_root_on_sys_path_when_absent(monkeypatch):
    root = Path(REPO_ROOT).resolve()
    filtered = [p for p in sys.path if not p or Path(p).resolve() != root]
    monkeypatch.setattr(sys, "path", filtered)
    fresh = load(REL, name="abn_w7_emit_execution_backbone_reload")
    assert sys.path[0] == str(fresh.ROOT)
    assert fresh.DEFAULT_OUTPUT.name == "execution_backbone_runtime_status.json"
