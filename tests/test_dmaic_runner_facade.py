"""Argument parsing and dispatch of runners/dmaic_runner.py, with targets monkeypatched.

No heavy pipeline run: the loader is replaced by fakes that record what the
facade asked for.
"""

import csv
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from runners import dmaic_runner as runner


def _fake_pipeline(return_code, seen):
    def main():
        seen.append(list(sys.argv))
        return return_code

    return SimpleNamespace(main=main)


def _fake_inventory(rows, refs=None):
    refs = [] if refs is None else refs
    return SimpleNamespace(
        FIELDS=["path", "family"],
        inventory=lambda ref: refs.append(ref) or [dict(r) for r in rows],
        summary=lambda rs: f"root files: {len(rs)}",
    )


def test_action_is_required_and_restricted():
    with pytest.raises(SystemExit) as exc:
        runner.main([])
    assert exc.value.code == 2
    with pytest.raises(SystemExit) as exc:
        runner.main(["--action", "deploy"])
    assert exc.value.code == 2


def test_sprint_must_be_an_integer():
    with pytest.raises(SystemExit) as exc:
        runner.main(["--action", "run-sprint", "--sprint", "five"])
    assert exc.value.code == 2


def test_dispatch_table_targets_existing_code():
    assert set(runner.ACTIONS) == {"run-sprint", "inventory"}
    assert runner.RUN_ALL_PHASES.is_file()
    assert runner.INVENTORY_GENERATOR.is_file()


def test_run_sprint_dispatches_to_run_all_phases_without_git(monkeypatch):
    seen, loaded = [], []

    def loader(path, name):
        loaded.append(path)
        return _fake_pipeline(0, seen)

    monkeypatch.setattr(sys, "argv", ["sentinel"])
    args = runner.build_parser().parse_args(["--action", "run-sprint", "--sprint", "5"])
    assert runner.run_sprint(args, loader=loader) == 0
    assert loaded == [runner.RUN_ALL_PHASES]
    assert seen == [["run_all_phases.py", "--iteration", "5", "--no-git"]]
    assert sys.argv == ["sentinel"]


def test_run_sprint_forwards_verbose_and_git_and_propagates_failure():
    seen = []
    args = runner.build_parser().parse_args(
        ["--action", "run-sprint", "--sprint", "3", "--verbose", "--git"]
    )
    assert runner.run_sprint(args, loader=lambda p, n: _fake_pipeline(1, seen)) == 1
    assert seen == [["run_all_phases.py", "--iteration", "3", "--verbose"]]


@pytest.mark.parametrize("argv", [[], ["--sprint", "0"]])
def test_run_sprint_rejects_missing_or_nonpositive_sprint(argv):
    args = runner.build_parser().parse_args(["--action", "run-sprint", *argv])
    with pytest.raises(SystemExit) as exc:
        runner.run_sprint(args, loader=lambda p, n: pytest.fail("must not dispatch"))
    assert "--sprint" in str(exc.value.code)


def test_inventory_writes_rows_to_output_dir(tmp_path):
    rows = [{"path": "README.md", "family": "KEEP"}]
    loaded, refs = [], []

    def loader(path, name):
        loaded.append(path)
        return _fake_inventory(rows, refs)

    args = runner.build_parser().parse_args(
        ["--action", "inventory", "--ref", "abc123", "--output-dir", str(tmp_path)]
    )
    assert runner.run_inventory(args, loader=loader) == 0
    assert loaded == [runner.INVENTORY_GENERATOR]
    assert refs == ["abc123"]
    with (tmp_path / runner.INVENTORY_CSV).open(encoding="utf-8") as f:
        assert list(csv.DictReader(f)) == [{"path": "README.md", "family": "KEEP"}]
    assert (tmp_path / runner.INVENTORY_SUMMARY).read_text(
        encoding="utf-8"
    ) == "root files: 1\n"


def test_inventory_fails_on_unclassified_root_file(tmp_path, capsys):
    rows = [
        {"path": "README.md", "family": "KEEP"},
        {"path": ".odd", "family": "UNCLASSIFIED"},
    ]
    args = runner.build_parser().parse_args(
        ["--action", "inventory", "--output-dir", str(tmp_path)]
    )
    assert runner.run_inventory(args, loader=lambda p, n: _fake_inventory(rows)) == 1
    assert ".odd" in capsys.readouterr().out
    assert (tmp_path / runner.INVENTORY_CSV).is_file()


def test_main_routes_through_dispatch_table(monkeypatch):
    calls = []
    monkeypatch.setitem(
        runner.ACTIONS, "inventory", lambda args: calls.append(args.action) or 7
    )
    assert runner.main(["--action", "inventory"]) == 7
    assert calls == ["inventory"]


def test_missing_target_is_a_hard_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        runner._load_module(Path(tmp_path / "absent.py"), "absent")
