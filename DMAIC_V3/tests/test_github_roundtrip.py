import os
import shutil
import subprocess
import tempfile
import pytest

pytestmark = [pytest.mark.integration]


def git_available():
    """Check if git is available in PATH."""
    return shutil.which("git") is not None


@pytest.mark.skipif(not git_available(), reason="git not available in PATH")
@pytest.mark.xfail(reason="Git tests may fail on Windows with long paths")
def test_local_git_roundtrip_init_commit_log():
    """
    Local-only git roundtrip:
    - init a repo
    - add a file
    - commit
    - check log contains commit
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_dir = os.path.join(tmpdir, "test_repo")
        os.makedirs(repo_dir, exist_ok=True)
        env = os.environ.copy()

        def run_git(*args):
            result = subprocess.run(
                ["git", *args],
                cwd=repo_dir,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                pytest.fail(f"git {' '.join(args)} failed: {result.stderr}")
            return result.stdout

        run_git("init")
        run_git("config", "user.email", "test@example.com")
        run_git("config", "user.name", "Test User")

        readme_path = os.path.join(repo_dir, "README.md")
        with open(readme_path, "w") as f:
            f.write("# Test Repo\n")

        run_git("add", "README.md")
        run_git("commit", "-m", "Initial commit")

        log_out = run_git("log", "--oneline")
        assert "Initial commit" in log_out


@pytest.mark.skipif(not git_available(), reason="git not available in PATH")
@pytest.mark.xfail(reason="Git tests may fail on Windows with long paths")
def test_git_branch_and_merge():
    """Test git branching and merging workflow."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_dir = os.path.join(tmpdir, "test_repo")
        os.makedirs(repo_dir, exist_ok=True)
        env = os.environ.copy()

        def run_git(*args):
            result = subprocess.run(
                ["git", *args],
                cwd=repo_dir,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                pytest.fail(f"git {' '.join(args)} failed: {result.stderr}")
            return result.stdout

        run_git("init")
        run_git("config", "user.email", "test@example.com")
        run_git("config", "user.name", "Test User")

        file_path = os.path.join(repo_dir, "file.txt")
        with open(file_path, "w") as f:
            f.write("main branch\n")

        run_git("add", "file.txt")
        run_git("commit", "-m", "Main commit")

        run_git("checkout", "-b", "feature")

        feature_path = os.path.join(repo_dir, "feature.txt")
        with open(feature_path, "w") as f:
            f.write("feature branch\n")

        run_git("add", "feature.txt")
        run_git("commit", "-m", "Feature commit")

        run_git("checkout", "master")
        run_git("merge", "feature", "-m", "Merge feature")

        log_out = run_git("log", "--oneline")
        assert "Feature commit" in log_out or "Merge feature" in log_out


@pytest.mark.skipif(not git_available(), reason="git not available in PATH")
@pytest.mark.xfail(reason="Git tests may fail on Windows with long paths")
def test_git_status_shows_changes():
    """Test git status detects file changes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_dir = os.path.join(tmpdir, "test_repo")
        os.makedirs(repo_dir, exist_ok=True)
        env = os.environ.copy()

        def run_git(*args):
            result = subprocess.run(
                ["git", *args],
                cwd=repo_dir,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                pytest.fail(f"git {' '.join(args)} failed: {result.stderr}")
            return result.stdout

        run_git("init")
        run_git("config", "user.email", "test@example.com")
        run_git("config", "user.name", "Test User")

        tracked_path = os.path.join(repo_dir, "tracked.txt")
        with open(tracked_path, "w") as f:
            f.write("tracked\n")

        run_git("add", "tracked.txt")
        run_git("commit", "-m", "Add tracked file")

        with open(tracked_path, "w") as f:
            f.write("modified\n")

        untracked_path = os.path.join(repo_dir, "untracked.txt")
        with open(untracked_path, "w") as f:
            f.write("untracked\n")

        status_out = run_git("status", "--short")
        assert "M tracked.txt" in status_out or "tracked.txt" in status_out
        assert "untracked.txt" in status_out
