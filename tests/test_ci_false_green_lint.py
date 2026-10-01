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
