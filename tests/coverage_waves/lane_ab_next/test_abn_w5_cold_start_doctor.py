"""Behaviour tests for scripts/cold_start_doctor.py.

``subprocess.run`` and ``shutil.which`` are faked; the ``DMAIC_V3`` import is
steered through ``sys.modules`` and ``sys.path`` is restored after each test.
"""

import json
import sys
import types
from types import SimpleNamespace

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("scripts/cold_start_doctor.py", name="abn_cold_start_doctor")


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mod, "ROOT", tmp_path)


def _fake_run(rc, stdout="", stderr=""):
    calls = []

    def fake(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return SimpleNamespace(returncode=rc, stdout=stdout, stderr=stderr)

    return fake, calls


def test_run_captures_result_and_strips_output(monkeypatch):
    fake, calls = _fake_run(3, " out \n", " err\n")
    monkeypatch.setattr(mod.subprocess, "run", fake)
    result = mod.run("tool --flag")
    assert result == {"cmd": "tool --flag", "rc": 3, "stdout": "out", "stderr": "err"}
    assert calls[0][1]["capture_output"] is True
    assert calls[0][1]["text"] is True


def test_run_maps_exception_to_rc_127(monkeypatch):
    def boom(cmd, **kwargs):
        raise FileNotFoundError("no such tool")

    monkeypatch.setattr(mod.subprocess, "run", boom)
    result = mod.run("ghost")
    assert result["rc"] == 127
    assert result["stdout"] == ""
    assert "no such tool" in result["stderr"]


def test_main_healthy_returns_0(monkeypatch, tmp_path, capsys):
    (tmp_path / "DMAIC_V3").mkdir()
    (tmp_path / "DMAIC_V3" / "__init__.py").write_bytes(b"")
    (tmp_path / "knowledge_packages").mkdir()
    monkeypatch.setitem(sys.modules, "DMAIC_V3", types.ModuleType("DMAIC_V3"))
    fake, calls = _fake_run(0, "3.3.0\n")
    monkeypatch.setattr(mod.subprocess, "run", fake)
    monkeypatch.setattr(
        mod.shutil, "which", lambda t: "/bin/" + t if t == "gh" else None
    )
    assert mod.main() == 0
    report = json.loads(capsys.readouterr().out)
    checks = report["checks"]
    assert checks["root_exists"] is True
    assert checks["dmaic_dir_exists"] is True
    assert checks["dmaic_init_exists"] is True
    assert checks["import_DMAIC_V3"] is True
    assert checks["knowledge_dir"] is True
    assert checks["reports_dir"] is False
    assert report["tools"] == {"pandoc": "", "xelatex": "", "gh": "/bin/gh"}
    assert report["engine_version"]["stdout"] == "3.3.0"
    assert report["actions"] == []
    assert "DMAIC_V3.dmaic_v3_engine --version" in calls[0][0]
    assert sys.path[0] == str(tmp_path)


def test_main_broken_import_returns_2_with_actions(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "DMAIC_V3", None)
    fake, _ = _fake_run(0)
    monkeypatch.setattr(mod.subprocess, "run", fake)
    monkeypatch.setattr(mod.shutil, "which", lambda t: None)
    assert mod.main() == 2
    report = json.loads(capsys.readouterr().out)
    assert report["checks"]["import_DMAIC_V3"] is False
    assert report["checks"]["dmaic_dir_exists"] is False
    assert len(report["actions"]) == 3
    assert report["actions"][0].startswith("Create package marker")


def test_main_engine_failure_returns_2(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "DMAIC_V3", types.ModuleType("DMAIC_V3"))
    fake, _ = _fake_run(1, "", "boom")
    monkeypatch.setattr(mod.subprocess, "run", fake)
    monkeypatch.setattr(mod.shutil, "which", lambda t: None)
    assert mod.main() == 2
    report = json.loads(capsys.readouterr().out)
    assert report["checks"]["import_DMAIC_V3"] is True
    assert report["engine_version"]["rc"] == 1
    assert report["engine_version"]["stderr"] == "boom"
