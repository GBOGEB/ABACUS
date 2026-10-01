from pathlib import Path


WORKFLOW = Path(".github/workflows/ci-abacus.yml")


def test_diff_cover_fetches_main_remote_ref_before_comparison():
    text = WORKFLOW.read_text(encoding="utf-8")
    fetch = "git fetch --no-tags origin main:refs/remotes/origin/main"
    compare = "--compare-branch=origin/main"

    assert fetch in text
    assert compare in text
    assert text.index(fetch) < text.index(compare)
