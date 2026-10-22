"""F3 regression: the report-only census must never read a stale JUnit file.

Before the fix, ``main`` reused ``<junit-dir>/NNN-<stem>.xml`` without deleting
it. When the pytest run wrote no JUnit (exit 0/5, crash before reporting), a
passing file left by an earlier census was classified ``TEST_GREEN``.

Hermetic: ``ROOT`` points at ``tmp_path``; the module's ``subprocess`` is a
scripted fake (no child pytest/coverage runs); the script is loaded by path
because a site-packages ``scripts`` package can shadow the repo directory.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "test_admission_census.py"
)
MODULE_NAME = "_f3_admission_census"


def _load():
    if MODULE_NAME in sys.modules:
        return sys.modules[MODULE_NAME]
    spec = importlib.util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


census = _load()

STALE_PASS = '<testsuite><testcase name="old_pass"/></testsuite>'
FRESH_FAIL = '<testsuite><testcase name="new"><failure/></testcase></testsuite>'


class FakeProcs:
    """Scripted ``subprocess`` for the census: ``junit`` None writes nothing."""

    PIPE = subprocess.PIPE
    STDOUT = subprocess.STDOUT

    def __init__(self, *, run_rc, junit=None):
        self.run_rc = run_rc
        self.junit = junit
        self.junit_existed_at_run: list[bool] = []

    def run(self, args, **kwargs):
        if args[1:3] == ["-m", "coverage"]:
            if args[3] != "erase":
                out = Path(args[args.index("-o") + 1])
                out.write_text(json.dumps({"files": {}}), encoding="utf-8")
            return subprocess.CompletedProcess(args, 0, stdout="")
        if "--collect-only" in args:
            return subprocess.CompletedProcess(args, 0, stdout="collected")
        junit = Path(
            next(a for a in args if a.startswith("--junitxml=")).split("=", 1)[1]
        )
        self.junit_existed_at_run.append(junit.exists())
        if self.junit is not None:
            junit.write_text(self.junit, encoding="utf-8")
        return subprocess.CompletedProcess(args, self.run_rc, stdout="")


@pytest.fixture
def tree(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    tests_dir = root / "DMAIC_V3" / "tests"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_a.py").write_text("def test_a():\n    pass\n", encoding="utf-8")
    monkeypatch.setattr(census, "ROOT", root)
    monkeypatch.setattr(census, "DEFAULT_ROOTS", (tests_dir, root / "integration"))
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    out = tmp_path / "out"
    junit_dir = out / "junit"
    junit_dir.mkdir(parents=True)
    return {"out": out, "junit_dir": junit_dir, "stale": junit_dir / "000-test_a.xml"}


def _run(monkeypatch, tree, fake) -> dict:
    monkeypatch.setattr(census, "subprocess", fake)
    census.main(
        [
            "--out",
            str(tree["out"] / "census.json"),
            "--coverage-out",
            str(tree["out"] / "coverage.json"),
            "--junit-dir",
            str(tree["junit_dir"]),
        ]
    )
    report = json.loads((tree["out"] / "census.json").read_text(encoding="utf-8"))
    assert len(report["rows"]) == 1
    return report["rows"][0]


@pytest.mark.parametrize("run_rc", [0, 5], ids=["exit0", "exit5-no-tests"])
def test_stale_passing_junit_is_not_trusted_when_run_writes_none(
    monkeypatch, tree, run_rc
):
    tree["stale"].write_text(STALE_PASS, encoding="utf-8")
    fake = FakeProcs(run_rc=run_rc, junit=None)

    row = _run(monkeypatch, tree, fake)

    # The stale file was removed before pytest ran and nothing replaced it.
    assert fake.junit_existed_at_run == [False]
    assert not tree["stale"].exists()
    assert row["outcomes"] == {"pass": 0, "fail": 0, "error": 0, "skip": 0}
    assert row["test_state"] != "TEST_GREEN"
    assert row["test_state"] == "TEST_EXISTS_UNCOLLECTED"


def test_stale_passing_junit_cannot_mask_a_crashed_run(monkeypatch, tree):
    tree["stale"].write_text(STALE_PASS, encoding="utf-8")

    row = _run(monkeypatch, tree, FakeProcs(run_rc=1, junit=None))

    assert row["outcomes"]["pass"] == 0
    assert row["test_state"] != "TEST_GREEN"


def test_fresh_junit_from_this_run_replaces_stale_evidence(monkeypatch, tree):
    tree["stale"].write_text(STALE_PASS, encoding="utf-8")
    fake = FakeProcs(run_rc=1, junit=FRESH_FAIL)

    row = _run(monkeypatch, tree, fake)

    assert fake.junit_existed_at_run == [False]
    assert row["outcomes"] == {"pass": 0, "fail": 1, "error": 0, "skip": 0}
    assert row["test_state"] == "TEST_FAILING"


def test_missing_junit_dir_entry_is_tolerated(monkeypatch, tree):
    # No stale file at all: unlink(missing_ok=True) must not raise.
    row = _run(monkeypatch, tree, FakeProcs(run_rc=0, junit=STALE_PASS))

    assert row["outcomes"]["pass"] == 1
    assert row["test_state"] == "TEST_GREEN"
