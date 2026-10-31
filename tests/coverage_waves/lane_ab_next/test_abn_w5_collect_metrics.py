"""Behaviour tests for qplant/monitoring_dashboard/collect_metrics.py.

PROJECT_ROOT and the hard-coded ``/home/ubuntu`` paths are redirected into
tmp_path, ``subprocess.run`` is faked and the bare ``src.config_loader``
import is stubbed through ``sys.modules``.
"""

import json
import locale
import sys
import types
from pathlib import Path

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

_SAVED_SYS_PATH = list(sys.path)
mod = load(
    "qplant/monitoring_dashboard/collect_metrics.py", name="abn_w5_collect_metrics"
)
# the module inserts a /home/ubuntu path into sys.path at import; undo it
sys.path[:] = _SAVED_SYS_PATH

HOME_PREFIX = "/home/ubuntu/"


class _Completed:
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.returncode = returncode


@pytest.fixture
def env(tmp_path, monkeypatch):
    root = tmp_path / "root"
    root.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(mod, "PROJECT_ROOT", root)

    def fake_path(*parts):
        text = str(parts[0])
        if text.startswith(HOME_PREFIX):
            return home.joinpath(text[len(HOME_PREFIX) :], *parts[1:])
        return Path(*parts)

    monkeypatch.setattr(mod, "Path", fake_path)
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return _Completed("abc1234\n", 0)

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    return types.SimpleNamespace(root=root, home=home, calls=calls)


def _set_run(monkeypatch, stdout="", returncode=0, error=None):
    def fake_run(cmd, **kwargs):
        if error is not None:
            raise error
        return _Completed(stdout, returncode)

    monkeypatch.setattr(mod.subprocess, "run", fake_run)


# --- collect_version_info -------------------------------------------------


def test_version_info_aligned(env):
    (env.root / "data").mkdir()
    (env.root / "data" / "config.yaml").write_bytes(b"version: '4.4.0'\n")
    (env.root / "VERSION.json").write_bytes(b'{"version": "4.4.0"}')
    info = mod.collect_version_info()
    assert info == {
        "config_yaml": "4.4.0",
        "version_json": "4.4.0",
        "git_commit": "abc1234",
        "aligned": True,
    }
    cmd, kwargs = env.calls[0]
    assert cmd == ["git", "rev-parse", "--short", "HEAD"]
    assert kwargs["cwd"] == str(env.root)


def test_version_info_missing_sources(env, monkeypatch):
    _set_run(monkeypatch, "", returncode=128)
    info = mod.collect_version_info()
    assert info["config_yaml"].startswith("ERROR: ")
    assert info["version_json"] == "missing"
    assert info["git_commit"] == "unknown"
    assert info["aligned"] is False


def test_version_info_defaults_and_git_exception(env, monkeypatch):
    (env.root / "data").mkdir()
    (env.root / "data" / "config.yaml").write_bytes(b"other: 1\n")
    (env.root / "VERSION.json").write_bytes(b"{}")
    _set_run(monkeypatch, error=OSError("git not installed"))
    info = mod.collect_version_info()
    assert info["config_yaml"] == "unknown"
    assert info["version_json"] == "unknown"
    assert info["git_commit"] == "unknown"
    assert info["aligned"] is True


# --- collect_test_results -------------------------------------------------


def test_test_results_passed_and_failed(env, monkeypatch):
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        seen["kwargs"] = kwargs
        return _Completed("tests/a.py ..F\n3 failed, 7 passed in 1.2s\n")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    res = mod.collect_test_results()
    assert res == dict(
        passed=7,
        failed=3,
        total=10,
        pass_rate=70.0,
        duration="3 failed, 7 passed in 1.2s",
        status="fail",
    )
    assert seen["cmd"][:3] == [sys.executable, "-m", "pytest"]
    assert seen["kwargs"]["timeout"] == 60


def test_test_results_all_passed(env, monkeypatch):
    _set_run(monkeypatch, "12 passed in 0.5s\n")
    res = mod.collect_test_results()
    assert res["passed"] == 12
    assert res["failed"] == 0
    assert res["pass_rate"] == 100.0
    assert res["status"] == "pass"


def test_test_results_no_summary(env, monkeypatch):
    _set_run(monkeypatch, "")
    res = mod.collect_test_results()
    assert res["total"] == 0
    assert res["pass_rate"] == 0.0
    assert res["duration"] == ""


def test_test_results_passed_word_without_count(env, monkeypatch):
    _set_run(monkeypatch, "nothing passed\n")
    res = mod.collect_test_results()
    assert res["passed"] == 0
    assert res["failed"] == 0


def test_test_results_subprocess_error(env, monkeypatch):
    _set_run(monkeypatch, error=RuntimeError("timeout"))
    res = mod.collect_test_results()
    assert res["total"] == 0
    assert res["status"] == "error: timeout"


def test_production_defect_all_failed_run_reported_as_pass(env, monkeypatch):
    """production_defect: an all-failing pytest summary is parsed as 0 failed and status pass; this test fails once fixed"""
    _set_run(monkeypatch, "4 failed in 0.3s\n")
    res = mod.collect_test_results()
    assert res["failed"] == 0
    assert res["status"] == "pass"


# --- collect_compliance ---------------------------------------------------


def test_compliance_present_invalid_and_missing(env):
    assert mod.collect_compliance() == {"compliance_score": 0, "status": "unknown"}
    path = env.root / "TRIAGE_COMPLIANCE_REPORT.json"
    path.write_bytes(b"{not json")
    assert mod.collect_compliance() == {"compliance_score": 0, "status": "unknown"}
    path.write_bytes(b'{"compliance_score": 91, "status": "ok"}')
    assert mod.collect_compliance() == {"compliance_score": 91, "status": "ok"}


# --- collect_config_drift -------------------------------------------------


def _stub_loader(monkeypatch, values):
    class ConfigLoader:
        def get(self, path):
            return values.get(path)

    pkg = types.ModuleType("src")
    sub = types.ModuleType("src.config_loader")
    sub.ConfigLoader = ConfigLoader
    pkg.config_loader = sub
    monkeypatch.setitem(sys.modules, "src", pkg)
    monkeypatch.setitem(sys.modules, "src.config_loader", sub)


def test_config_drift_compares_expected_values(monkeypatch):
    values = {
        "compressor_specifications.hp_compressors.count": 3,
        "compressor_specifications.fsd575.motor_power_kW": 300,
        "financial.compressor_capex.total_3_units_eur": 600000,
    }
    _stub_loader(monkeypatch, values)
    rows = mod.collect_config_drift()
    assert len(rows) == 6
    assert rows[0] == {
        "parameter": "compressor_specifications.hp_compressors.count",
        "expected": 3,
        "actual": 3,
        "aligned": True,
    }
    assert rows[1]["aligned"] is False
    assert rows[1]["actual"] == 300
    assert rows[3]["actual"] is None
    assert [r["aligned"] for r in rows] == [True, False, True, False, False, False]


def test_config_drift_import_failure_returns_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "src", None)
    monkeypatch.delitem(sys.modules, "src.config_loader", raising=False)
    rows = mod.collect_config_drift()
    assert len(rows) == 1
    assert "error" in rows[0]


# --- collect_file_stats / collect_todo_status ------------------------------


def test_file_stats_counts(env):
    root = env.root
    (root / "src").mkdir()
    (root / "src" / "a.py").write_bytes(b"")
    (root / "src" / "b.py").write_bytes(b"")
    (root / "src" / "c.txt").write_bytes(b"")
    (root / "tests").mkdir()
    (root / "tests" / "test_a.py").write_bytes(b"")
    viz = root / "docs" / "visualizations"
    viz.mkdir(parents=True)
    (viz / "c1.html").write_bytes(b"")
    (viz / "c2.html").write_bytes(b"")
    (root / "docs" / "plots").mkdir()
    (root / "docs" / "plots" / "p.html").write_bytes(b"")
    (root / "docs" / "index.html").write_bytes(b"")
    stats = mod.collect_file_stats()
    assert stats == {
        "python_files": 2,
        "html_docs": 4,
        "test_files": 1,
        "total_charts": 3,
    }


def test_file_stats_empty_project(env):
    assert mod.collect_file_stats() == {
        "python_files": 0,
        "html_docs": 0,
        "test_files": 0,
        "total_charts": 0,
    }


def test_todo_status_missing(env):
    assert mod.collect_todo_status() == {"total": 0, "done": 0, "remaining": 0}


def test_todo_status_parses_items(env):
    content = "\n".join(
        [
            "| C-1 | crit | ✅ DONE |",
            "| H-12 | high | open |",
            "| M-3 | med | ✅ DONE |",
            "| L-4 | low | open |",
            "| X-5 | ignored | open |",
        ]
    )
    raw = content.encode("utf-8")
    (env.home / "phase1_consolidated_todos.md").write_bytes(raw)
    res = mod.collect_todo_status()
    # the module reads with the locale encoding: UTF-8 hosts see both DONE
    # markers, a cp1252 Windows host decodes the emoji to mojibake and sees none
    done = raw.decode(locale.getpreferredencoding(False)).count("✅ DONE")
    assert done in (0, 2)
    assert res == {
        "total": 4,
        "done": done,
        "remaining": 4 - done,
        "completion_pct": round(done / 4 * 100, 1),
    }


# --- collect_all_metrics / main -------------------------------------------


def test_collect_all_metrics_shape(env, monkeypatch):
    _stub_loader(monkeypatch, {})
    _set_run(monkeypatch, "5 passed in 0.1s\n")
    metrics = mod.collect_all_metrics()
    assert metrics["project"] == "MYRRHA QPLANT Cryogenic Dashboard"
    assert metrics["status"] == "healthy"
    assert metrics["tests"]["passed"] == 5
    assert set(metrics) == {
        "timestamp",
        "project",
        "versions",
        "tests",
        "compliance",
        "config_drift",
        "file_stats",
        "todos",
        "status",
    }
    assert "T" in metrics["timestamp"]


def _fake_metrics(aligned=True, failed=0, drift=()):
    return {
        "versions": {"aligned": aligned},
        "tests": {"failed": failed},
        "config_drift": list(drift),
    }


def test_main_check_healthy(env, monkeypatch, capsys):
    monkeypatch.setattr(mod, "collect_all_metrics", lambda: _fake_metrics())
    monkeypatch.setattr(sys, "argv", ["collect_metrics.py", "--check"])
    assert mod.main() == 0
    assert "QPLANT Health Check: ✅ HEALTHY" in capsys.readouterr().out


def test_main_check_degraded_lists_issues(env, monkeypatch, capsys):
    drift = [
        {"aligned": False},
        {"aligned": True},
        {"error": "boom"},
        "not-a-dict",
    ]
    monkeypatch.setattr(
        mod,
        "collect_all_metrics",
        lambda: _fake_metrics(aligned=False, failed=2, drift=drift),
    )
    monkeypatch.setattr(sys, "argv", ["collect_metrics.py", "--check"])
    assert mod.main() == 1
    out = capsys.readouterr().out
    assert "DEGRADED: Version mismatch, 2 tests failing, 1 config drift(s)" in out


def test_main_json_writes_snapshot(env, monkeypatch, capsys):
    (env.home / "monitoring_dashboard").mkdir()
    monkeypatch.setattr(mod, "collect_all_metrics", lambda: _fake_metrics(failed=1))
    monkeypatch.setattr(sys, "argv", ["collect_metrics.py"])
    assert mod.main() == 0
    written = json.loads(
        (env.home / "monitoring_dashboard" / "monitoring_data.json").read_text(
            encoding="utf-8"
        )
    )
    assert written["status"] == "degraded"
    assert written["issues"] == ["1 tests failing"]
    printed = json.loads(capsys.readouterr().out)
    assert printed == written


def test_main_rejects_unknown_output_choice(env, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["collect_metrics.py", "--output", "pdf"])
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 2
