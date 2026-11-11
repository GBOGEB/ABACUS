"""MIP2 deterministic seeded method-qualification fixtures."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from validate_method_contracts import validate


def test_contracts_are_structurally_valid():
    receipt = validate()
    assert receipt["status"] == "STRUCTURAL_PASS"
    assert receipt["methods"] >= 11
    assert receipt["cases"] >= 8


def test_formatter_idempotence_and_semantics():
    black = pytest.importorskip("black")
    isort = pytest.importorskip("isort")
    original = "import sys\nimport os\n\ndef add( x,y ):\n return x+y\n"

    def format_once(text):
        return black.format_str(isort.code(text), mode=black.Mode())

    first = format_once(original)
    assert format_once(first) == first
    before = {}
    after = {}
    exec(compile(original, "<before>", "exec"), before)
    exec(compile(first, "<after>", "exec"), after)
    assert before["add"](2, 3) == after["add"](2, 3) == 5


def test_bandit_positive_and_negative(tmp_path):
    pytest.importorskip("bandit")
    bad = tmp_path / "bad.py"
    good = tmp_path / "good.py"
    bad.write_text(
        "import subprocess\nsubprocess.run('echo test', shell=True)\n", encoding="utf-8"
    )
    good.write_text(
        "import subprocess\nsubprocess.run(['echo', 'test'], shell=False)\n",
        encoding="utf-8",
    )

    def scan(path):
        out = tmp_path / (path.stem + ".json")
        result = subprocess.run(
            [sys.executable, "-m", "bandit", "-f", "json", "-o", str(out), str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode in (0, 1), "Bandit scan did not finish normally"
        assert out.is_file(), "Bandit JSON artifact missing"
        return json.loads(out.read_text(encoding="utf-8"))["results"]

    assert any(x["test_id"] == "B602" for x in scan(bad))
    assert not any(x["test_id"] == "B602" for x in scan(good))


def test_coverage_detects_missing_branch(tmp_path):
    pytest.importorskip("coverage")
    src = tmp_path / "fixture.py"
    src.write_text(
        "def choose(flag):\n    if flag:\n        return 1\n    return 0\n",
        encoding="utf-8",
    )
    runner = tmp_path / "run.py"
    runner.write_text(
        "from fixture import choose\nassert choose(True) == 1\n", encoding="utf-8"
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "--branch",
            "--source",
            str(tmp_path),
            str(runner),
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "json",
            "-o",
            str(tmp_path / "coverage.json"),
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    report = json.loads((tmp_path / "coverage.json").read_text(encoding="utf-8"))
    details = next(v for k, v in report["files"].items() if k.endswith("fixture.py"))
    assert details["summary"]["missing_branches"] >= 1
