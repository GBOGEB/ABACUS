"""Regression tests for the G-family pytest guard."""

import subprocess
import sys
from pathlib import Path

import pytest

from scripts.ci.family_collect_guard import tally

GUARD = Path(__file__).resolve().parents[2] / "scripts/ci/family_collect_guard.py"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("marker", "assertion", "expected_rc", "outcome"),
    [
        ("", "True", 0, "passed"),
        ("", "False", 1, "failed"),
        ("@pytest.mark.skip(reason='regression fixture')", "True", 0, "skipped"),
        ("@pytest.mark.xfail(reason='regression fixture')", "False", 1, "xfailed"),
        ("@pytest.mark.xfail(reason='regression fixture')", "True", 1, "xpassed"),
        (
            "@pytest.mark.xfail(reason='regression fixture', strict=False)",
            "True",
            1,
            "xpassed",
        ),
        (
            "@pytest.mark.xfail(reason='regression fixture', strict=True)",
            "True",
            1,
            "xpassed",
        ),
    ],
)
def test_family_guard_outcomes(
    tmp_path: Path, marker: str, assertion: str, expected_rc: int, outcome: str
) -> None:
    test_file = tmp_path / "test_fixture.py"
    test_file.write_text(
        f"import pytest\n{marker}\ndef test_fixture():\n    assert {assertion}\n",
        encoding="utf-8",
    )
    config = tmp_path / "pytest.ini"
    config.write_text("[pytest]\n", encoding="utf-8")
    junit = tmp_path / "junit.xml"

    result = subprocess.run(
        [
            sys.executable,
            str(GUARD),
            "--family",
            "regression",
            "--expected-min",
            "1",
            "--junit",
            str(junit),
            "--",
            str(test_file),
            "-c",
            str(config),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert result.returncode == expected_rc, result.stdout + result.stderr
    counts = tally(junit)
    assert counts["collected"] == 1
    assert counts[outcome] == 1
    assert sum(counts.values()) == 2
    verdict = "PASS" if expected_rc == 0 else "FAIL"
    assert f"G family `regression`: {verdict}" in result.stdout
