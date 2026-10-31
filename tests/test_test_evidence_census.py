import subprocess
import sys
from pathlib import Path

from scripts import test_evidence_census as census


def test_junit_census_records_every_outcome_and_governed_skip(tmp_path: Path):
    junit = tmp_path / "junit.xml"
    junit.write_text(
        """<testsuite tests="4">
  <testcase classname="tests.test_a" name="test_green"/>
  <testcase classname="tests.test_a" name="test_fail">
    <failure message="boom">boom</failure>
  </testcase>
  <testcase classname="tests.test_a" name="test_error">
    <error message="setup">setup</error>
  </testcase>
  <testcase classname="tests.test_a" name="test_config">
    <skipped message="TEST_BLOCKED_CONFIG: fixture unavailable"/>
  </testcase>
</testsuite>
""",
        encoding="utf-8",
    )

    result = census.build_census(junit)

    assert result["outcomes"] == {
        "error": 1,
        "fail": 1,
        "pass": 1,
        "skip": 1,
    }
    assert result["states"]["TEST_GREEN"] == 1
    assert result["states"]["TEST_FAILING"] == 2
    assert result["states"]["TEST_BLOCKED_CONFIG"] == 1
    assert result["uncategorized_skips"] == []
    assert result["formal_credit_delta"] == 0
    assert result["engineering_credit_delta"] == 0


def test_uncategorized_skip_is_visible_not_silently_accepted(tmp_path: Path):
    junit = tmp_path / "junit.xml"
    junit.write_text(
        """<testsuite tests="1">
  <testcase classname="tests.test_a" name="test_skip">
    <skipped message="old free-text skip"/>
  </testcase>
</testsuite>
""",
        encoding="utf-8",
    )

    result = census.build_census(junit)

    assert result["uncategorized_skips"] == ["tests.test_a::test_skip"]
    assert result["states"]["UNCLASSIFIED_SKIP"] == 1


def test_explicit_exact_checkout_sha_overrides_synthetic_merge_sha(
    tmp_path: Path, monkeypatch
):
    junit = tmp_path / "junit.xml"
    junit.write_text('<testsuite><testcase name="passes"/></testsuite>')
    fake_merge = "1" * 40
    checked_out_head = "2" * 40
    monkeypatch.setenv("GITHUB_SHA", fake_merge)

    outcome = census.build_census(junit, exact_sha=checked_out_head)
    assert outcome["exact_sha"] == checked_out_head
    assert outcome["exact_sha"] != fake_merge


def test_cli_rejects_invalid_sha_instead_of_publishing_green(tmp_path: Path):
    junit = tmp_path / "junit.xml"
    result_file = tmp_path / "result.json"
    junit.write_text('<testsuite><testcase name="passes"/></testsuite>')
    result = subprocess.run(
        [
            sys.executable,
            "scripts/test_evidence_census.py",
            "--junit",
            str(junit),
            "--out",
            str(result_file),
            "--exact-sha",
            "synthetic-head",
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert not result_file.exists()


def test_cli_stamps_explicit_pr_head_despite_synthetic_github_sha(
    tmp_path: Path, monkeypatch
):
    junit = tmp_path / "junit.xml"
    result_file = tmp_path / "result.json"
    junit.write_text('<testsuite><testcase name="passes"/></testsuite>')
    monkeypatch.setenv("GITHUB_SHA", "3" * 40)
    result = subprocess.run(
        [
            sys.executable,
            "scripts/test_evidence_census.py",
            "--junit",
            str(junit),
            "--out",
            str(result_file),
            "--exact-sha",
            "4" * 40,
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    import json

    receipt = json.loads(result_file.read_text())
    assert receipt["exact_sha"] == "4" * 40
    assert receipt["ratchet_status"] == "PASS"


def test_direct_script_execution_resolves_sibling_plugin(tmp_path: Path):
    junit = tmp_path / "junit.xml"
    out = tmp_path / "evidence.json"
    junit.write_text(
        """<testsuite tests="1">
  <testcase classname="tests.test_a" name="test_green"/>
</testsuite>
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/test_evidence_census.py",
            "--junit",
            str(junit),
            "--out",
            str(out),
            "--max-skips",
            "0",
            "--max-xfails",
            "0",
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert out.is_file()
    assert '"ratchet_status": "PASS"' in out.read_text(encoding="utf-8")


def test_explicit_sha_overrides_synthetic_merge_sha(tmp_path: Path, monkeypatch):
    import json

    junit = tmp_path / "junit.xml"
    out = tmp_path / "evidence.json"
    sha = "a" * 40
    junit.write_text(
        '<testsuite><testcase classname="x" name="ok"/></testsuite>',
        encoding="utf-8",
    )
    monkeypatch.setenv("GITHUB_SHA", "b" * 40)

    assert (
        census.main(["--junit", str(junit), "--out", str(out), "--exact-sha", sha]) == 0
    )
    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert receipt["exact_sha"] == sha
    assert receipt["ratchet_status"] == "PASS"


def test_exact_sha_cli_rejects_invalid_identity(tmp_path: Path, capsys):
    import pytest

    junit = tmp_path / "junit.xml"
    out = tmp_path / "evidence.json"
    junit.write_text(
        '<testsuite><testcase classname="x" name="ok"/></testsuite>',
        encoding="utf-8",
    )
    with pytest.raises(SystemExit) as exc:
        census.main(
            ["--junit", str(junit), "--out", str(out), "--exact-sha", "not-a-sha"]
        )
    assert exc.value.code == 2
    assert "40-character Git SHA" in capsys.readouterr().err
    assert not out.exists()


def test_explicit_sha_preserves_fail_closed_uncategorized_skip(
    tmp_path: Path, monkeypatch
):
    import json

    junit = tmp_path / "junit.xml"
    out = tmp_path / "evidence.json"
    sha = "c" * 40
    junit.write_text(
        '<testsuite><testcase classname="x" name="skipped"><skipped message="unknown"/></testcase></testsuite>',
        encoding="utf-8",
    )
    monkeypatch.setenv("GITHUB_SHA", "d" * 40)

    assert (
        census.main(["--junit", str(junit), "--out", str(out), "--exact-sha", sha]) == 1
    )
    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert receipt["exact_sha"] == sha
    assert receipt["ratchet_status"] == "FAIL"
    assert receipt["uncategorized_skips"] == ["x::skipped"]
