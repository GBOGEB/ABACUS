import subprocess
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_guard_fails_on_non_strict_xpass(tmp_path):
    test_file = tmp_path / "test_non_strict_xpass.py"
    test_file.write_text(
        "import pytest\n"
        "@pytest.mark.xfail(reason='regression', strict=False)\n"
        "def test_non_strict_xpass():\n"
        "    assert True\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(REPOSITORY_ROOT / "scripts/ci/family_collect_guard.py"),
            "--family",
            "xpass-regression",
            "--expected-min",
            "1",
            "--junit",
            str(tmp_path / "results.xml"),
            "--",
            str(test_file),
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "xfail/xpass present" in result.stdout
    assert "| 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |" in result.stdout
