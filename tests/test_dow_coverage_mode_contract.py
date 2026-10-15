"""DOW enhanced CI coverage-mode admission contract."""

from pathlib import Path

WORKFLOW = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "ci-enhanced.yml"
)


def test_dow_coverage_mode_is_explicit_and_branch_aware():
    """Stop regressions that produce mixed statement/branch parallel data."""
    source = WORKFLOW.read_text(encoding="utf-8")
    assert "pytest --benchmark-disable" in source
    assert "--cov-branch" in source
    assert "--cov-config=pyproject.toml" in source
    assert "python -m coverage erase" in source
    assert "--cov-report=xml" in source


def test_dow_does_not_hide_coverage_data_errors():
    """A coverage collection failure must remain an actual CI failure."""
    source = WORKFLOW.read_text(encoding="utf-8")
    for line in source.splitlines():
        if "pytest --benchmark-disable" in line:
            assert "|| true" not in line
            assert "|| echo" not in line
            assert "--no-cov" not in line
