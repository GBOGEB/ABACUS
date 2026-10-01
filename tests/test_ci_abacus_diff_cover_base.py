from pathlib import Path


WORKFLOW = Path(".github/workflows/ci-abacus.yml")


def test_diff_cover_fetches_main_remote_ref_before_comparison():
    text = WORKFLOW.read_text(encoding="utf-8")
    fetch = "git fetch --no-tags origin main:refs/remotes/origin/main"
    compare = "--compare-branch=origin/main"

    assert fetch in text
    assert compare in text
    assert text.index(fetch) < text.index(compare)


def test_abacus_proof_checkout_has_full_history_for_merge_base():
    text = WORKFLOW.read_text(encoding="utf-8")
    marker = "name: ABACUS - ${{ matrix.os }} - Python ${{ matrix.python-version }}"
    start = text.index(marker)
    proof_job = text[start:text.index("  compatibility-gate:", start)]

    assert "uses: actions/checkout@v7" in proof_job
    assert "fetch-depth: 0" in proof_job
