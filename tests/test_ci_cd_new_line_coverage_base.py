"""PR new-line coverage must diff against the base tip the PR merges into."""

import os
import shutil
import subprocess  # nosec B404
from pathlib import Path

import pytest
import yaml

WORKFLOW = (
    Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci-cd-tests.yml"
)
BASH = shutil.which("bash")


def _coverage_job():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["coverage"]


def _step():
    (step,) = [
        s for s in _coverage_job()["steps"] if s.get("id") == "new_line_coverage"
    ]
    return step


def git(repo, *args):
    return subprocess.run(  # nosec B603 B607
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def commit(repo, name, message):
    (repo / name).write_text(f"{name}\n", encoding="utf-8")
    git(repo, "add", name)
    git(repo, "commit", "-qm", message)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "ci@example.invalid")
    git(repo, "config", "user.name", "ci")
    return repo


def run_step(repo, tmp_path, base_sha):
    # Stub the installer and diff-cover; record the base diff-cover gets.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "pip").write_bytes(b"#!/bin/sh\nexit 0\n")
    (bin_dir / "diff-cover").write_bytes(
        b'#!/bin/sh\nprintf "%s\\n" "$2" > compare.txt\n: > diff-coverage.md\n'
    )
    for stub in bin_dir.iterdir():
        stub.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "BASE_SHA": base_sha,
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary.md"),
    }
    return subprocess.run(  # nosec B603
        [BASH, "-c", _step()["run"]],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
    )


def test_coverage_checkout_keeps_the_merge_base_parent():
    checkout = _coverage_job()["steps"][0]
    assert checkout["uses"].startswith("actions/checkout@")
    assert checkout["with"]["fetch-depth"] == 2


def test_new_line_coverage_resolves_the_base_in_the_step():
    run = _step()["run"]
    assert run.startswith("set -euo pipefail\n")
    assert "git cat-file -e 'HEAD^2^{commit}'" in run
    assert "base=\"$(git rev-parse 'HEAD^1')\"" in run
    assert '--compare-branch="$base"' in run
    assert '--compare-branch="$BASE_SHA"' not in run
    assert "--diff-range-notation=.." in run


@pytest.mark.skipif(BASH is None, reason="needs bash")
def test_a_stale_base_sha_compares_against_the_merge_parent(repo, tmp_path):
    stale = commit(repo, "common.txt", "common")
    moved = commit(repo, "later-base.txt", "base moved on")
    git(repo, "checkout", "-qb", "feature", stale)
    commit(repo, "feature.txt", "feature")
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "-q", "--no-ff", "feature", "-m", "synthetic")

    result = run_step(repo, tmp_path, stale)

    assert result.returncode == 0, result.stderr
    assert (repo / "compare.txt").read_text().strip() == f"--compare-branch={moved}"


@pytest.mark.skipif(BASH is None, reason="needs bash")
def test_an_unfetchable_base_fails_closed(repo, tmp_path):
    commit(repo, "common.txt", "common")

    result = run_step(repo, tmp_path, "a" * 40)

    assert result.returncode != 0
    assert not (repo / "compare.txt").exists()
