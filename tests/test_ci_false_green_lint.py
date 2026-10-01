from pathlib import Path

from scripts import ci_false_green_lint as lint


def test_false_green_lint_distinguishes_governed_allow(tmp_path: Path):
    workflow = tmp_path / "ci.yml"
    workflow.write_text(
        """jobs:
  test:
    steps:
      - run: pytest || true
      # rex-allow: advisory formatter does not gate correctness
      - run: pre-commit run --all-files || echo "advisory"
""",
        encoding="utf-8",
    )

    rows = lint.scan_file(workflow)

    assert len(rows) == 2
    assert rows[0]["allowed"] is False
    assert rows[0]["patterns"] == ["shell_or_true"]
    assert rows[1]["allowed"] is True
    assert rows[1]["patterns"] == ["shell_or_echo"]


def test_false_green_report_builds_pressure_queue_and_ratchet(tmp_path: Path, capsys):
    first = tmp_path / "a.yml"
    second = tmp_path / "b.yml"
    first.write_text(
        """jobs:
  test:
    steps:
      - run: pytest || true
      - run: mypy . || echo "advisory"
""",
        encoding="utf-8",
    )
    second.write_text(
        """jobs:
  test:
    continue-on-error: true
    steps:
      - run: pytest
""",
        encoding="utf-8",
    )

    exit_code = lint.main(
        [
            "--paths",
            str(first),
            str(second),
            "--mode",
            "census",
            "--max-unguarded",
            "3",
        ]
    )

    assert exit_code == 0
    report = __import__("json").loads(capsys.readouterr().out)
    assert report["schema"] == "abacus-ci-false-green-census/1.1.0"
    assert report["unguarded_count"] == 3
    assert report["allowed_count"] == 0
    assert report["ratchet_status"] == "PASS"
    assert report["pressure_queue"][0]["path"] in {
        first.as_posix(),
        second.as_posix(),
    }

    exit_code = lint.main(
        [
            "--paths",
            str(first),
            str(second),
            "--mode",
            "census",
            "--max-unguarded",
            "2",
        ]
    )
    assert exit_code == 1
