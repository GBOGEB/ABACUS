import importlib.util
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
GUARD_PATH = ROOT / "scripts" / "ci" / "family_collect_guard.py"
spec = importlib.util.spec_from_file_location("family_collect_guard", GUARD_PATH)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def test_guard_rejects_non_strict_xpass(tmp_path, capsys, monkeypatch):
    junit = tmp_path / "junit.xml"

    def run_pytest(_pytest_args, output):
        output.write_text(
            '<testsuites><testsuite><testcase name="test_non_strict_xpass">'
            '<properties><property name="xfail" value="true"/></properties>'
            "</testcase></testsuite></testsuites>",
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr(guard, "run_pytest", run_pytest)
    result = guard.main(
        [
            "--family",
            "non-strict-xpass",
            "--expected-min",
            "1",
            "--junit",
            str(junit),
            "--",
            "test_non_strict_xpass.py",
        ]
    )

    assert result == 1
    assert "| 1 | 0 | 0 | 0 | 0 | 0 | 1 |" in capsys.readouterr().out


def test_run_pytest_loads_test_state_plugin(tmp_path):
    with patch.object(guard.subprocess, "call", return_value=0) as call:
        guard.run_pytest(["test_sample.py"], tmp_path / "junit.xml")

    assert call.call_args.args[0][3:5] == [
        "-p",
        "scripts.pytest_test_state_plugin",
    ]
