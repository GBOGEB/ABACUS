import subprocess
import sys
from pathlib import Path


def test_non_strict_xpass_is_counted_and_rejected(tmp_path):
    repository = Path(__file__).resolve().parents[2]
    tests = tmp_path / "test_xpass.py"
    tests.write_text(
        "import pytest\n"
        "@pytest.mark.xfail(reason='unexpected pass', strict=False)\n"
        "def test_unexpected_pass():\n"
        "    pass\n"
        "@pytest.mark.xfail(reason='expected failure', strict=False)\n"
        "def test_expected_failure():\n"
        "    assert False\n",
        encoding="utf-8",
    )
    junit = tmp_path / "junit.xml"

    result = subprocess.run(
        [
            sys.executable,
            str(repository / "scripts/ci/family_collect_guard.py"),
            "--family",
            "xpass-regression",
            "--expected-min",
            "2",
            "--junit",
            str(junit),
            "--",
            str(tests),
        ],
        cwd=repository,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "G family `xpass-regression`: FAIL" in result.stdout
    assert "| 2 | 2 | 0 | 0 | 0 | 0 | 1 | 1 |" in result.stdout
    assert "xfail/xpass present" in result.stdout
