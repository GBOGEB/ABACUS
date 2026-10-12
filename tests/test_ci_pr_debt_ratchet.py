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
MISSING = [tool for tool in TOOLS if importlib.util.find_spec(tool) is None]
# The lint tools are installed in the Code Quality job, which runs this file;
# the unit-test matrix does not install them.
needs_tools = pytest.mark.skipif(
    bool(MISSING),
    reason=f"TEST_BLOCKED_DEPENDENCY: {', '.join(MISSING)} unavailable",
)


@needs_tools
def test_new_debt_in_changed_files_fails(repo):
    base = commit(repo, {"pkg/a.py": CLEAN})
    commit(repo, {"pkg/a.py": BANDIT_HIT, "pkg/new.py": DIRTY_FORMAT})
    report = ratchet_mod.ratchet(base, TOOLS)
    added = {(row["path"], row["tool"]) for row in report["added_debt"]}
    assert ("pkg/a.py", "bandit") in added
    assert ("pkg/new.py", "black") in added
    assert report["status"] == "FAIL"


@needs_tools
def test_existing_debt_is_not_charged_to_the_pr(repo):
    base = commit(repo, {"pkg/legacy.py": DIRTY_FORMAT + BANDIT_HIT})
    commit(repo, {"pkg/legacy.py": DIRTY_FORMAT + BANDIT_HIT + "\n# touched\n"})
    report = ratchet_mod.ratchet(base, TOOLS)
    assert report["changed_python_files"] == ["pkg/legacy.py"]
    assert report["added_debt"] == []
    assert report["status"] == "PASS"


@needs_tools
def test_unchanged_files_are_out_of_scope(repo):
    base = commit(repo, {"pkg/legacy.py": BANDIT_HIT, "README.md": "x\n"})
    commit(repo, {"README.md": "y\n"})
    report = ratchet_mod.ratchet(base, TOOLS)
    assert report["changed_python_files"] == []
    assert report["status"] == "PASS"


@needs_tools
def test_rename_is_compared_against_its_original_path(repo):
    base = commit(repo, {"pkg/old.py": DIRTY_FORMAT + BANDIT_HIT})
    git(repo, "mv", "pkg/old.py", "pkg/new_name.py")
    git(repo, "commit", "-q", "-m", "rename")
    report = ratchet_mod.ratchet(base, TOOLS)
    assert report["changed_python_files"] == ["pkg/new_name.py"]
    assert report["renamed_from"] == {"pkg/new_name.py": "pkg/old.py"}
    assert report["added_debt"] == []


@needs_tools
def test_rename_that_adds_debt_still_fails(repo):
    base = commit(repo, {"pkg/old.py": CLEAN + "\n\nVALUE = 1\n"})
    git(repo, "mv", "pkg/old.py", "pkg/new_name.py")
    (repo / "pkg" / "new_name.py").write_text(
        CLEAN + "\n\nVALUE = 1\n\n\ndef run(cmd):\n    return eval(cmd)\n",
        encoding="utf-8",
    )
    commit(repo, {})
    report = ratchet_mod.ratchet(base, TOOLS)
    assert report["renamed_from"] == {"pkg/new_name.py": "pkg/old.py"}
    added = {(row["path"], row["tool"]) for row in report["added_debt"]}
    assert added == {("pkg/new_name.py", "bandit")}


@needs_tools
def test_asserts_in_tests_are_not_bandit_debt(repo):
    base = commit(repo, {"tests/test_x.py": "def test_a():\n    pass\n"})
    commit(repo, {"tests/test_x.py": "def test_a():\n    assert 1 + 1 == 2\n"})
    report = ratchet_mod.ratchet(base, ("bandit",))
    assert report["added_debt"] == []


def completed(returncode, stdout="", stderr=""):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


@pytest.mark.parametrize(
    ("tool", "result"),
    [
        ("flake8", completed(1, stderr="There was a critical error")),
        ("flake8", completed(2, stderr="bad config")),
        ("black", completed(2, stderr="No such option")),
        ("isort", completed(2, stderr="crash")),
        ("bandit", completed(2, stderr="bad profile")),
        ("bandit", completed(0, stdout="not json")),
    ],
)
def test_tool_that_cannot_run_fails_closed(monkeypatch, tool, result):
    monkeypatch.setattr(ratchet_mod, "run", lambda cmd, cwd: result)
    with pytest.raises(ratchet_mod.ToolError):
        ratchet_mod.debt(tool, Path("."), "pkg/a.py")


def test_missing_tool_fails_closed_before_scanning(monkeypatch):
    monkeypatch.setattr(ratchet_mod, "tool_origin", lambda tool: "")
    with pytest.raises(ratchet_mod.ToolError, match="not installed"):
        ratchet_mod.ratchet("HEAD", ("flake8",))
    assert ratchet_mod.main(["--base", "HEAD", "--tools", "flake8"]) == 2


def test_flake8_findings_are_counted(monkeypatch):
    findings = completed(1, stdout="F821\nF821\nE999\n")
    monkeypatch.setattr(ratchet_mod, "run", lambda cmd, cwd: findings)
    assert ratchet_mod.debt("flake8", Path("."), "pkg/a.py") == {"F821": 2, "E999": 1}


@needs_tools
def test_swapping_one_bandit_finding_for_another_still_fails(repo):
    subprocess_call = "import subprocess\n\n\ndef run(cmd):\n"
    base = commit(
        repo,
        {"pkg/a.py": subprocess_call + "    return subprocess.call(cmd, shell=True)\n"},
    )
    commit(repo, {"pkg/a.py": subprocess_call + "    return eval(cmd)\n"})
    report = ratchet_mod.ratchet(base, ("bandit",))
    [row] = report["added_debt"]
    assert row["base"] >= row["head"]
    assert any(key.startswith("B307:") for key in row["new_findings"])
    assert report["status"] == "FAIL"


@needs_tools
def test_lint_config_change_requires_the_full_scan(repo):
    base = commit(repo, {"pkg/a.py": CLEAN})
    commit(repo, {"setup.cfg": "[flake8]\nselect = E9\n"})
    report = ratchet_mod.ratchet(base, TOOLS)
    assert report["changed_config_files"] == ["setup.cfg"]
    assert report["status"] == "FULL_SCAN_REQUIRED"
    assert ratchet_mod.main(["--base", base, "--tools", "flake8"]) == 3


@needs_tools
def test_replacing_a_finding_under_the_same_rule_still_fails(repo):
    base = commit(
        repo, {"pkg/a.py": CLEAN + "\n\ndef run(cmd):\n    return eval(cmd)\n"}
    )
    commit(
        repo,
        {"pkg/a.py": CLEAN + "\n\ndef run(cmd, env):\n    return eval(env[cmd])\n"},
    )
    report = ratchet_mod.ratchet(base, ("bandit",))
    [row] = report["added_debt"]
    assert row["base"] == row["head"] == 1
    assert any("eval(env[cmd])" in key for key in row["new_findings"])
    assert report["status"] == "FAIL"


@needs_tools
def test_a_pr_module_cannot_stand_in_for_a_tool(repo):
    fake = 'print(\'{"results": [], "errors": []}\')\n'
    base = commit(repo, {"pkg/a.py": CLEAN})
    commit(repo, {"pkg/a.py": BANDIT_HIT, "bandit.py": fake})
    report = ratchet_mod.ratchet(base, ("bandit",))
    rows = {row["path"]: row for row in report["added_debt"]}
    assert "pkg/a.py" in rows
    assert report["status"] == "FAIL"


def test_a_tool_resolved_inside_the_checkout_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setattr(ratchet_mod, "ROOT", tmp_path)
    monkeypatch.setattr(
        ratchet_mod, "tool_origin", lambda tool: str(tmp_path / f"{tool}.py")
    )
    with pytest.raises(ratchet_mod.ToolError, match="inside the checkout"):
        ratchet_mod.require_tools(("bandit",))


@pytest.mark.parametrize(
    ("path", "is_test"),
    [
        ("tests/test_x.py", True),
        ("integration/cryoplant_project/tests/test_smoke.py", True),
        ("tests/conftest.py", True),
        ("DMAIC_V3/core/test_system_bridge.py", False),
        ("pkg/thing_test.py", False),
    ],
)
def test_only_files_under_tests_skip_assert_findings(path, is_test):
    assert ratchet_mod.is_test_file(path) is is_test


@needs_tools
def test_a_text_file_renamed_to_python_is_a_new_file(repo):
    base = commit(repo, {"payload.txt": BANDIT_HIT})
    git(repo, "mv", "payload.txt", "payload.py")
    git(repo, "commit", "-q", "-m", "rename")
    report = ratchet_mod.ratchet(base, ("bandit",))
    assert report["renamed_from"] == {}
    assert report["status"] == "FAIL"


@needs_tools
def test_moving_a_test_into_production_charges_its_asserts(repo):
    body = "def check(x):\n    assert x\n    return x\n"
    base = commit(repo, {"tests/test_x.py": body})
    (repo / "pkg").mkdir()
    git(repo, "mv", "tests/test_x.py", "pkg/x.py")
    git(repo, "commit", "-q", "-m", "move")
    report = ratchet_mod.ratchet(base, ("bandit",))
    assert report["renamed_from"] == {"pkg/x.py": "tests/test_x.py"}
    [row] = report["added_debt"]
    assert any(key.startswith("B101:") for key in row["new_findings"])
