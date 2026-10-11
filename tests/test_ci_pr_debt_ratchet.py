"""Tests for scripts/ci_pr_debt_ratchet.py (PR new-debt ratchet)."""

import importlib.util
import subprocess  # nosec B404
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ci_pr_debt_ratchet.py"
spec = importlib.util.spec_from_file_location("ci_pr_debt_ratchet", SCRIPT)
ratchet_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ratchet_mod)

CLEAN = 'import os\n\n\ndef home():\n    return os.environ.get("HOME")\n'
DIRTY_FORMAT = "import os\ndef home( ):\n    return os.environ.get('HOME')\n"
BANDIT_HIT = CLEAN + "\n\ndef run(cmd):\n    return eval(cmd)\n"


def git(repo, *args):
    return subprocess.run(  # nosec B603 B607
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "ci@example.invalid")
    git(tmp_path, "config", "user.name", "ci")
    monkeypatch.setattr(ratchet_mod, "ROOT", tmp_path)
    return tmp_path


def commit(repo, files):
    for name, text in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "c")
    return git(repo, "rev-parse", "HEAD")


TOOLS = ("black", "isort", "flake8", "bandit")


def test_new_debt_in_changed_files_fails(repo):
    base = commit(repo, {"pkg/a.py": CLEAN})
    commit(repo, {"pkg/a.py": BANDIT_HIT, "pkg/new.py": DIRTY_FORMAT})
    report = ratchet_mod.ratchet(base, TOOLS)
    added = {(row["path"], row["tool"]) for row in report["added_debt"]}
    assert ("pkg/a.py", "bandit") in added
    assert ("pkg/new.py", "black") in added
    assert report["status"] == "FAIL"


def test_existing_debt_is_not_charged_to_the_pr(repo):
    base = commit(repo, {"pkg/legacy.py": DIRTY_FORMAT + BANDIT_HIT})
    commit(repo, {"pkg/legacy.py": DIRTY_FORMAT + BANDIT_HIT + "\n# touched\n"})
    report = ratchet_mod.ratchet(base, TOOLS)
    assert report["changed_python_files"] == ["pkg/legacy.py"]
    assert report["added_debt"] == []
    assert report["status"] == "PASS"


def test_unchanged_files_are_out_of_scope(repo):
    base = commit(repo, {"pkg/legacy.py": BANDIT_HIT, "README.md": "x\n"})
    commit(repo, {"README.md": "y\n"})
    report = ratchet_mod.ratchet(base, TOOLS)
    assert report["changed_python_files"] == []
    assert report["status"] == "PASS"


def test_asserts_in_tests_are_not_bandit_debt(repo):
    base = commit(repo, {"tests/test_x.py": "def test_a():\n    pass\n"})
    commit(repo, {"tests/test_x.py": "def test_a():\n    assert 1 + 1 == 2\n"})
    report = ratchet_mod.ratchet(base, ("bandit",))
    assert report["added_debt"] == []
