"""Regression tests for the G-family result guard."""

import pytest

from scripts.ci.family_collect_guard import main, run_pytest, tally


@pytest.mark.unit
@pytest.mark.parametrize(
    ("source", "category", "exit_code"),
    [
        ("def test_result(): pass", "passed", 0),
        ("def test_result(): assert False", "failed", 1),
        ('@pytest.mark.skip(reason="skip")\ndef test_result(): pass', "skipped", 0),
        (
            '@pytest.mark.xfail(reason="expected")\ndef test_result(): assert False',
            "xfailed",
            0,
        ),
        (
            "@pytest.mark.xfail(strict=True)\ndef test_result(): pass",
            "xpassed",
            1,
        ),
        (
            "@pytest.mark.xfail(strict=False)\ndef test_result(): pass",
            "xpassed",
            0,
        ),
    ],
)
def test_tally_pytest_results(tmp_path, monkeypatch, source, category, exit_code):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    test_file = tmp_path / "test_result.py"
    test_file.write_text("import pytest\n\n" + source + "\n", encoding="utf-8")
    junit = tmp_path / "results.xml"

    assert run_pytest([str(test_file)], junit) == exit_code
    counts = tally(junit)
    assert counts["collected"] == 1
    assert counts[category] == 1
    assert sum(value for key, value in counts.items() if key != "collected") == 1


@pytest.mark.unit
def test_guard_rejects_non_strict_xpass(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    summary = tmp_path / "summary.txt"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    test_file = tmp_path / "test_xpass.py"
    test_file.write_text(
        "import pytest\n\n"
        "@pytest.mark.xfail(strict=False)\n"
        "def test_unexpected_pass():\n"
        "    assert True\n",
        encoding="utf-8",
    )

    assert (
        main(["--family", "regression", "--expected-min", "1", "--", str(test_file)])
        == 1
    )
    report = capsys.readouterr().out
    assert "G family `regression`: FAIL" in report
    assert "xfail/xpass present" in report
    assert "pytest exit code" not in report
    assert "| 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1 |" in report
    assert summary.read_text(encoding="utf-8") in report
