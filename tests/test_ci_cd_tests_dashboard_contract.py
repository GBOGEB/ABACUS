from pathlib import Path


WORKFLOW = Path(".github/workflows/ci-cd-tests.yml")


def _comprehensive_block() -> str:
    text = WORKFLOW.read_text(encoding="utf-8")
    start = text.index("  comprehensive-test-suite:")
    end = text.index("  security-scan:", start)
    return text[start:end]


def test_comprehensive_suite_uses_live_repo_test_surface():
    block = _comprehensive_block()

    assert "scripts/run_comprehensive_tests.py" not in block
    assert "python -m pytest tests/ --benchmark-disable -q" in block
    assert "2>&1 | tee test_output.log" in block
    assert "continue-on-error: true" not in block


def test_dashboard_artifacts_are_strict_and_evidence_is_preserved():
    block = _comprehensive_block()

    assert "mkdir -p dashboard" in block
    assert "name: comprehensive-test-output" in block
    assert "name: test-dashboard" in block
    assert block.count("if-no-files-found: error") == 2
    assert "if: always()" in block
