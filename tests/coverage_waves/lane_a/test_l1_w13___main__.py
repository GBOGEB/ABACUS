"""Lane A wave 13: DMAIC_V3.generators.__main__ CLI with stubbed workers."""

import argparse
import importlib
import sys
import types

import pytest


def _import_restoring_sys_path():
    # The CLI inserts the repo root at sys.path[0] on import.
    saved = list(sys.path)
    try:
        return importlib.import_module("DMAIC_V3.generators.__main__")
    finally:
        sys.path[:] = saved


cli = _import_restoring_sys_path()


class _Tracker:
    instances = []
    victory = {"a": True}

    def __init__(self, output_dir, timeout):
        self.output_dir = output_dir
        self.timeout = timeout
        self.calls = []
        self.statistics = types.SimpleNamespace(
            victory_conditions_met=dict(type(self).victory)
        )
        type(self).instances.append(self)

    def scan_and_execute(self, root, patterns):
        self.calls.append(("scan", root, tuple(patterns)))

    def print_summary(self):
        self.calls.append("summary")

    def export_json(self):
        self.calls.append("json")

    def export_yaml(self):
        self.calls.append("yaml")

    def export_markdown(self):
        self.calls.append("md")


class _Aligner:
    instances = []
    results = {"a.md": (True, "ok")}

    def __init__(self, docs_dir):
        self.docs_dir = docs_dir
        self.calls = []
        type(self).instances.append(self)

    def align_all(self):
        return dict(type(self).results)

    def export_version_info_json(self):
        self.calls.append("json")

    def export_version_info_yaml(self):
        self.calls.append("yaml")


@pytest.fixture
def stubs(monkeypatch):
    monkeypatch.setattr(_Tracker, "instances", [])
    monkeypatch.setattr(_Tracker, "victory", {"a": True})
    monkeypatch.setattr(_Aligner, "instances", [])
    monkeypatch.setattr(_Aligner, "results", {"a.md": (True, "ok")})
    monkeypatch.setattr(cli, "ExecutionTracker", _Tracker)
    monkeypatch.setattr(cli, "DocumentationAligner", _Aligner)
    return _Tracker, _Aligner


def _main(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["generators", *args])
    return cli.main()


def test_execute_success_default_patterns(monkeypatch, tmp_path, stubs, capsys):
    rc = _main(monkeypatch, "execute", "--root", str(tmp_path), "--timeout", "5")
    assert rc == 0
    tracker = stubs[0].instances[0]
    assert tracker.timeout == 5
    assert tracker.calls == [
        ("scan", tmp_path, ("**/*.py", "**/*.bas")),
        "summary",
        "json",
        "yaml",
        "md",
    ]
    assert "ALL VICTORY CONDITIONS MET" in capsys.readouterr().out


def test_execute_failure_custom_patterns(monkeypatch, tmp_path, stubs, capsys):
    monkeypatch.setattr(_Tracker, "victory", {"a": True, "b": False})
    rc = _main(monkeypatch, "execute", "--root", str(tmp_path), "--patterns", "*.x")
    assert rc == 1
    assert stubs[0].instances[0].calls[0] == ("scan", tmp_path, ("*.x",))
    assert "Some victory conditions not met" in capsys.readouterr().out


def test_cmd_execute_without_exports(stubs):
    args = argparse.Namespace(
        output_dir="o",
        timeout=1,
        patterns=None,
        root="r",
        export_json=False,
        export_yaml=False,
        export_markdown=False,
    )
    assert cli.cmd_execute(args) == 0
    assert stubs[0].instances[0].calls == [
        ("scan", "r", ("**/*.py", "**/*.bas")),
        "summary",
    ]


def test_align_docs_success_and_failure(monkeypatch, tmp_path, stubs, capsys):
    assert _main(monkeypatch, "align-docs", "--docs-dir", str(tmp_path)) == 0
    assert stubs[1].instances[0].calls == ["json", "yaml"]
    assert stubs[1].instances[0].docs_dir == tmp_path
    assert "All documentation aligned" in capsys.readouterr().out

    monkeypatch.setattr(_Aligner, "results", {"a": (True, ""), "b": (False, "x")})
    assert _main(monkeypatch, "align-docs") == 1
    assert "failed to align" in capsys.readouterr().out


def test_cmd_align_docs_without_exports(stubs):
    args = argparse.Namespace(docs_dir="d", export_json=False, export_yaml=False)
    assert cli.cmd_align_docs(args) == 0
    assert stubs[1].instances[0].calls == []


@pytest.mark.parametrize(
    "victory,results,rc,marker",
    [
        ({"a": True}, {"x": (True, "")}, 0, "FULL RUN SUCCESSFUL"),
        ({"a": False}, {"x": (True, "")}, 1, "Execution: [FAIL] FAILED"),
        ({"a": True}, {"x": (False, "")}, 1, "Documentation: [FAIL] FAILED"),
    ],
)
def test_full_run(monkeypatch, tmp_path, stubs, capsys, victory, results, rc, marker):
    monkeypatch.setattr(_Tracker, "victory", victory)
    monkeypatch.setattr(_Aligner, "results", results)
    args = ["full-run", "--root", str(tmp_path), "--docs-dir", str(tmp_path)]
    assert _main(monkeypatch, *args) == rc
    out = capsys.readouterr().out
    assert marker in out
    assert "FULL RUN MODE" in out
    assert "Version: " in out


def test_version_command(monkeypatch, capsys):
    assert _main(monkeypatch, "version") == 0
    out = capsys.readouterr().out
    assert "VERSION INFORMATION" in out
    assert "Victory Conditions:" in out
    assert "Changelog:" in out


def test_version_flag_exits(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        _main(monkeypatch, "--version")
    assert exc.value.code == 0
    assert "DMAIC V3 Generators" in capsys.readouterr().out


def test_no_command_prints_help(monkeypatch, capsys):
    assert _main(monkeypatch) == 1
    assert "usage:" in capsys.readouterr().out


def test_keyboard_interrupt_and_exception(monkeypatch, stubs, capsys):
    def interrupt(self, root, patterns):
        raise KeyboardInterrupt

    monkeypatch.setattr(_Tracker, "scan_and_execute", interrupt)
    assert _main(monkeypatch, "execute") == 130
    assert "Interrupted by user" in capsys.readouterr().out

    def boom(self, root, patterns):
        raise RuntimeError("kaput")

    monkeypatch.setattr(_Tracker, "scan_and_execute", boom)
    assert _main(monkeypatch, "execute") == 1
    captured = capsys.readouterr()
    assert "[X] Error: kaput" in captured.out
    assert "RuntimeError" in captured.err
