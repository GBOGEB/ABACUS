"""Gap tests for scripts/runners/phase0_runner.py (main CLI, git fallback)."""

import json
import sys
from pathlib import Path

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

REL = "scripts/runners/phase0_runner.py"
mod = load(REL, name="abn_w7_phase0_runner")


def _receipt(status, scratch=None):
    return dict(status=status, scratch_root=str(scratch), steps=[])


def test_head_sha_withheld_when_git_missing(monkeypatch, tmp_path):
    def boom(*args, **kwargs):
        raise OSError("git not installed")

    monkeypatch.setattr(mod.subprocess, "check_output", boom)
    assert mod._head_sha(tmp_path) == "WITHHELD"


def test_head_sha_withheld_on_called_process_error(monkeypatch, tmp_path):
    def fail(*args, **kwargs):
        raise mod.subprocess.CalledProcessError(128, args[0])

    monkeypatch.setattr(mod.subprocess, "check_output", fail)
    assert mod._head_sha(tmp_path) == "WITHHELD"


def test_main_without_scratch_uses_tempdir_and_returns_zero(monkeypatch, capsys):
    seen = {}

    def fake_run(workspace, scratch):
        seen["workspace"] = workspace
        seen["scratch"] = scratch
        seen["existed"] = scratch.is_dir()
        return _receipt("PASS", scratch)

    monkeypatch.setattr(mod, "run_smoke", fake_run)
    assert mod.main(["--smoke"]) == 0
    assert seen["existed"] is True
    assert seen["scratch"].name.startswith("abacus-phase0-smoke-")
    assert seen["workspace"] == mod.ROOT
    printed = json.loads(capsys.readouterr().out)
    assert printed["status"] == "PASS"


def test_main_with_scratch_and_receipt_writes_file_and_fails(
    monkeypatch, tmp_path, capsys
):
    scratch = tmp_path / "deep" / "scratch"
    receipt = tmp_path / "out" / "nested" / "receipt.json"

    def fake_run(workspace, scratch_dir):
        assert scratch_dir == scratch
        assert scratch_dir.is_dir()
        return _receipt("FAIL", scratch_dir)

    monkeypatch.setattr(mod, "run_smoke", fake_run)
    rc = mod.main(
        [
            "--smoke",
            "--workspace",
            str(tmp_path),
            "--scratch",
            str(scratch),
            "--receipt",
            str(receipt),
        ]
    )
    assert rc == 1
    written = json.loads(receipt.read_text(encoding="utf-8"))
    assert written["status"] == "FAIL"
    assert written["scratch_root"] == str(scratch)
    assert json.loads(capsys.readouterr().out) == written


def test_module_inserts_root_on_sys_path_when_absent(monkeypatch):
    root = Path(REPO_ROOT).resolve()
    filtered = [p for p in sys.path if not p or Path(p).resolve() != root]
    monkeypatch.setattr(sys, "path", filtered)
    monkeypatch.delitem(sys.modules, "abn_w7_phase0_runner_reload", raising=False)
    fresh = load(REL, name="abn_w7_phase0_runner_reload")
    assert sys.path[0] == str(fresh.ROOT)
    assert fresh.ROOT == root
