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


def test_renaming_a_config_away_requires_the_full_scan(repo):
    base = commit(repo, {".editorconfig": "root = true\n", "pkg/a.py": CLEAN})
    git(repo, "mv", ".editorconfig", "editorconfig.old")
    commit(repo, {"pkg/a.py": CLEAN + "\n# touched\n"})
    assert ratchet_mod.changed_config_files(base) == [".editorconfig"]


@needs_tools
def test_a_nested_black_config_is_ignored_like_the_full_scan(repo):
    # black . from the root reads only the root config, so a line a nested
    # line-length = 200 would accept is still debt.
    long_line = "VALUE = " + " + ".join(["1"] * 30) + "\n"
    nested = "[tool.black]\nline-length = 200\n"
    base = commit(repo, {"pkg/pyproject.toml": nested, "pkg/a.py": "X = 1\n"})
    commit(repo, {"pkg/a.py": "X = 1\n" + long_line})
    report = ratchet_mod.ratchet(base, ("black",))
    [row] = report["added_debt"]
    assert row["base"] == 0 and row["head"] == 1


@needs_tools
def test_a_nested_isort_config_is_ignored_like_the_full_scan(repo):
    # isort . from the root reads only the root settings; a nested
    # force_single_line must not turn a root-clean file into debt.
    nested = "[settings]\nforce_single_line = true\n"
    base = commit(repo, {"pkg/.isort.cfg": nested, "pkg/a.py": "X = 1\n"})
    commit(repo, {"pkg/a.py": "from os import path, sep\n\nX = (path, sep)\n"})
    report = ratchet_mod.ratchet(base, ("isort",))
    assert report["added_debt"] == []


def test_a_gitignore_change_requires_the_full_scan(repo):
    base = commit(repo, {".gitignore": "build/\n", "pkg/a.py": CLEAN})
    commit(repo, {".gitignore": "build/\npkg/\n"})
    assert ratchet_mod.changed_config_files(base) == [".gitignore"]


@needs_tools
def test_a_symlink_replaced_by_a_file_is_new(repo):
    commit(repo, {"pkg/real.py": CLEAN})
    (repo / "pkg" / "mod.py").symlink_to("real.py")
    base = commit(repo, {})
    (repo / "pkg" / "mod.py").unlink()
    commit(repo, {"pkg/mod.py": BANDIT_HIT})
    report = ratchet_mod.ratchet(base, ("bandit",))
    assert "pkg/mod.py" in report["changed_python_files"]
    assert report["status"] == "FAIL"


def test_changing_the_lint_job_requirements_requires_the_full_scan(repo):
    base = commit(repo, {"requirements-test.txt": "pytest\n", "pkg/a.py": CLEAN})
    commit(repo, {"requirements-test.txt": "pytest\nflake8==3.0.0\n"})
    assert ratchet_mod.changed_config_files(base) == ["requirements-test.txt"]
    commit(repo, {"docs/requirements-test.txt": "x\n"})
    assert ratchet_mod.changed_config_files(base) == ["requirements-test.txt"]


@needs_tools
def test_base_imports_are_classified_against_the_base_tree(repo):
    # localpkg is first-party at the base; deleting it makes the head's
    # import a third-party one that isort . would re-sort.
    imports = "import os\n\nimport requests\n\nimport localpkg\n"
    base = commit(repo, {"localpkg/__init__.py": "", "pkg/a.py": imports})
    git(repo, "rm", "-q", "-r", "localpkg")
    commit(repo, {"pkg/a.py": imports + "\nX = (os, requests, localpkg)\n"})
    report = ratchet_mod.ratchet(base, ("isort",))
    [row] = report["added_debt"]
    assert row["base"] == 0 and row["head"] == 1


@needs_tools
def test_a_multiline_finding_is_keyed_by_its_whole_call(repo):
    def module(argument):
        return (
            CLEAN + f"\n\ndef run(cmd):\n    return eval(\n        {argument}\n    )\n"
        )

    base = commit(repo, {"pkg/a.py": module('"1 + 1"')})
    commit(repo, {"pkg/a.py": module("cmd")})
    report = ratchet_mod.ratchet(base, ("bandit",))
    [row] = report["added_debt"]
    assert row["base"] == row["head"] == 1
    assert any("cmd" in key for key in row["new_findings"])


@pytest.mark.parametrize(
    "path", [".github/workflows/ci-cd-tests.yml", "scripts/ci_pr_debt_ratchet.py"]
)
def test_changing_how_the_tools_run_requires_the_full_scan(repo, path):
    base = commit(repo, {path: "a\n", "pkg/a.py": CLEAN})
    commit(repo, {path: "b\n"})
    for tool in TOOLS:
        assert ratchet_mod.changed_config_files(base, (tool,)) == [path]


def test_a_config_change_only_affects_the_tools_that_read_it(repo):
    base = commit(repo, {"pkg/a.py": CLEAN})
    commit(repo, {".bandit": "[bandit]\nskips = B101\n"})
    assert ratchet_mod.changed_config_files(base, ("bandit",)) == [".bandit"]
    assert ratchet_mod.changed_config_files(base, ("black", "isort", "flake8")) == []
    commit(repo, {".flake8": "[flake8]\nselect = E9\n"})
    assert ratchet_mod.changed_config_files(base, ("bandit",)) == [".bandit"]
    assert ratchet_mod.changed_config_files(base, ("flake8",)) == [".flake8"]
    assert ratchet_mod.changed_config_files(base, ("black", "isort")) == []


def test_the_lint_job_requirements_do_not_affect_bandit(repo):
    base = commit(repo, {"requirements-test.txt": "pytest\n"})
    commit(repo, {"requirements-test.txt": "pytest\nflake8==3.0.0\n"})
    assert ratchet_mod.changed_config_files(base, ("bandit",)) == []


@needs_tools
def test_a_bandit_config_change_keeps_the_formatting_ratchet(repo):
    base = commit(repo, {"pkg/a.py": CLEAN})
    commit(repo, {".bandit": "[bandit]\nskips = B101\n", "pkg/a.py": DIRTY_FORMAT})
    report = ratchet_mod.ratchet(base, ("black",))
    assert report["changed_config_files"] == []
    assert report["status"] == "FAIL"
    assert ratchet_mod.ratchet(base, ("bandit",))["status"] == "FULL_SCAN_REQUIRED"


@needs_tools
def test_stub_changes_are_charged_to_black_and_isort(repo):
    base = commit(repo, {"README.md": "before\n"})
    commit(
        repo,
        {
            "pkg/types.pyi": "import sys\nimport os\n\ndef  get()->str:...\n",
        },
    )
    report = ratchet_mod.ratchet(base, ("black", "isort"))
    assert report["changed_python_files"] == ["pkg/types.pyi"]
    assert {row["tool"] for row in report["added_debt"]} == {"black", "isort"}
    assert report["status"] == "FAIL"


@needs_tools
def test_stub_only_change_does_not_expand_bandit_flake8_scope(repo):
    base = commit(repo, {"pkg/types.pyi": "def get() -> str: ...\n"})
    commit(repo, {"pkg/types.pyi": "def  get()->str:...\n"})
    report = ratchet_mod.ratchet(base, ("flake8", "bandit"))
    assert report["changed_python_files"] == ["pkg/types.pyi"]
    assert report["rows"] == []
    assert report["added_debt"] == []
    assert report["status"] == "PASS"


@needs_tools
def test_type_stub_added_from_non_stub_extension_is_new(repo):
    base = commit(repo, {"api/interface.txt": "def  get()->str:...\n"})
    git(repo, "mv", "api/interface.txt", "api/interface.pyi")
    git(repo, "commit", "-q", "-m", "rename stub")
    report = ratchet_mod.ratchet(base, ("black",))
    assert report["renamed_from"] == {}
    assert report["status"] == "FAIL"


def test_quality_workflow_ratchets_each_tool_independently():
    workflow = (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "workflows"
        / "ci-cd-tests.yml"
    ).read_text(encoding="utf-8")
    assert workflow.count("- '**/*.pyi'") == 2
    assert "for tool in black isort flake8; do" in workflow
    for tool in ("black", "isort", "flake8"):
        assert f"{tool}_full_scan=required" not in workflow  # dynamically emitted
        assert f"steps.quality_ratchet.outputs.{tool}_full_scan" in workflow
    assert 'echo "${tool}_full_scan=required" >> "$GITHUB_OUTPUT"' in workflow
    assert 'flag_name="${tool}_FULL_SCAN"' in workflow
    assert 'fallback="${!flag_name}"' in workflow


def test_security_workflow_includes_governance_python_paths():
    workflow = (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "workflows"
        / "ci-cd-tests.yml"
    ).read_text(encoding="utf-8")
    assert workflow.count("- '**/*.py'") == 2
    assert "'!ci/governance/**'" not in workflow


@pytest.mark.parametrize(
    "job, step_id",
    [("lint-and-format", "quality_ratchet"), ("security-scan", "bandit_ratchet")],
)
def test_workflow_ratchets_against_the_merge_base_tip(job, step_id):
    # base.sha goes stale when the base branch moves, and a depth-2 checkout
    # does not hold it; the merge commit's first parent is the live base tip.
    import yaml

    workflow = yaml.safe_load(
        (
            Path(__file__).resolve().parents[1]
            / ".github"
            / "workflows"
            / "ci-cd-tests.yml"
        ).read_text(encoding="utf-8")
    )
    steps = workflow["jobs"][job]["steps"]
    (step,) = [s for s in steps if s.get("id") == step_id]
    run = step["run"]
    assert "base=\"$(git rev-parse 'HEAD^1')\"" in run
    assert "git cat-file -e 'HEAD^2^{commit}'" in run
    # The policy still comes from the base, never from the PR head.
    assert '"$base:scripts/ci_pr_debt_ratchet.py"' in run
    assert 'python -I "$ratchet"' in run
    assert '--base "$base"' in run
    assert '--base "$BASE_SHA"' not in run
    assert '"$BASE_SHA:' not in run

    if step_id == "quality_ratchet":
        assert step["env"]["FORCED"] == "${{ github.event.forced }}"
        assert (
            'if [[ "$FORCED" == "true" || "$BEFORE_SHA" =~ ^0+$ ]]; then'
            in run
        )
        assert 'if [[ -z "$BEFORE_SHA" ]]; then' in run
        assert (
            'if ! git cat-file -e "$base^{commit}" 2>/dev/null; then'
            in run
        )
        assert (
            'git fetch --no-tags --depth=1 origin "$BEFORE_SHA"'
            in run
        )
        assert (
            'git fetch --no-tags --depth=1 origin "$BEFORE_SHA"; then'
            not in run
        )


def test_security_push_baseline_fails_closed_for_unavailable_previous_tip():
    workflow = (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "workflows"
        / "ci-cd-tests.yml"
    ).read_text(encoding="utf-8")
    assert "FORCED_PUSH: ${{ github.event.forced }}" in workflow
    assert "Could not fetch previous push tip" in workflow
    assert '[[ "$FORCED_PUSH" != "true" && -n "$BEFORE_SHA" &&' in workflow


def test_bandit_full_scan_is_pinned_and_report_errors_fail_closed():
    workflow = (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "workflows"
        / "ci-cd-tests.yml"
    ).read_text(encoding="utf-8")
    assert '"bandit==1.8.6"' in workflow
    assert 'report.get("results"), list' in workflow
    assert 'report.get("metrics"), dict' in workflow
    assert "steps.bandit.outputs.scan_error" in workflow


def test_per_tool_config_map_is_not_global_override(repo):
    base = commit(repo, {"pkg/a.py": CLEAN})
    commit(repo, {".flake8": "[flake8]\nselect=E9\n"})
    assert ratchet_mod.changed_config_files(base, ("flake8",)) == [".flake8"]
    assert ratchet_mod.changed_config_files(base, ("black",)) == []
    assert ratchet_mod.changed_config_files(base, ("isort",)) == []


@needs_tools
def test_a_bandit_config_cannot_silence_its_own_new_finding(repo):
    base = commit(repo, {"pkg/a.py": CLEAN})
    commit(repo, {".bandit": "[bandit]\nskips = B307\n", "pkg/a.py": BANDIT_HIT})
    report = ratchet_mod.ratchet(base, ("bandit",))
    assert report["base_policy_red"] == ["bandit"]
    assert report["status"] == "BASE_POLICY_RED"
    assert ratchet_mod.main(["--base", base, "--tools", "bandit"]) == 1


@needs_tools
def test_a_flake8_config_cannot_silence_its_own_new_finding(repo):
    base = commit(repo, {"pkg/a.py": CLEAN})
    commit(
        repo,
        {
            ".flake8": "[flake8]\nextend-ignore = F821\n",
            "pkg/a.py": CLEAN + "\n\ndef broken():\n    return missing_name\n",
        },
    )
    assert ratchet_mod.ratchet(base, ("flake8",))["status"] == "BASE_POLICY_RED"


@needs_tools
def test_a_config_change_on_clean_code_goes_to_the_full_scan(repo):
    base = commit(repo, {"pkg/a.py": CLEAN})
    commit(repo, {".bandit": "[bandit]\nskips = B101\n"})
    report = ratchet_mod.ratchet(base, ("bandit",))
    assert report["base_policy_red"] == []
    assert ratchet_mod.main(["--base", base, "--tools", "bandit"]) == 3


@needs_tools
def test_deleting_a_package_rechecks_its_untouched_importers(repo):
    imports = "import os\n\nimport requests\n\nimport localpkg\n\nX = (os, requests, localpkg)\n"
    base = commit(repo, {"localpkg/__init__.py": "", "pkg/a.py": imports})
    git(repo, "rm", "-q", "-r", "localpkg")
    git(repo, "commit", "-q", "-m", "drop localpkg")
    report = ratchet_mod.ratchet(base, ("isort",))
    assert report["changed_python_files"] == []
    assert report["import_roots_changed"] is True
    assert [(row["path"], row["tool"]) for row in report["added_debt"]] == [
        ("pkg/a.py", "isort")
    ]
    assert report["status"] == "FAIL"


@needs_tools
def test_a_new_nested_module_does_not_recheck_the_tree(repo):
    base = commit(repo, {"pkg/__init__.py": "", "pkg/a.py": CLEAN})
    commit(repo, {"pkg/b.py": CLEAN})
    report = ratchet_mod.ratchet(base, ("isort",))
    assert "import_roots_changed" not in report
    assert report["status"] == "PASS"


@needs_tools
def test_an_inline_nosec_cannot_hide_a_new_finding(repo):
    base = commit(repo, {"pkg/a.py": CLEAN})
    commit(repo, {"pkg/a.py": BANDIT_HIT.replace("eval(cmd)", "eval(cmd)  # nosec")})
    assert ratchet_mod.ratchet(base, ("bandit",))["status"] == "FAIL"


@needs_tools
def test_an_inline_noqa_cannot_hide_a_new_critical_error(repo):
    base = commit(repo, {"pkg/a.py": CLEAN})
    commit(repo, {"pkg/a.py": CLEAN + "\n\ndef f():\n    return nope  # noqa\n"})
    assert ratchet_mod.ratchet(base, ("flake8",))["status"] == "FAIL"


@needs_tools
@pytest.mark.parametrize(
    "config",
    [
        "[flake8]\nmax-line-length = 100\n",
        "[flake8]\nper-file-ignores = pkg/a.py:F821\n",
    ],
)
def test_a_flake8_config_change_still_compares_changed_files(repo, config):
    base = commit(repo, {"pkg/a.py": CLEAN})
    commit(
        repo,
        {
            ".flake8": config,
            "pkg/a.py": CLEAN + "\n\ndef f():\n    return nope  # noqa\n",
        },
    )
    report = ratchet_mod.ratchet(base, ("flake8",))
    assert [row["path"] for row in report["added_debt"]] == ["pkg/a.py"]
    assert report["added_debt"][0]["new_findings"] == {"F821": 1}
    assert ratchet_mod.main(["--base", base, "--tools", "flake8"]) == 1


@needs_tools
def test_a_bandit_config_change_still_compares_changed_files(repo):
    base = commit(repo, {"pkg/a.py": CLEAN, "pkg/b.py": CLEAN})
    commit(
        repo,
        {
            ".bandit": "[bandit]\nexclude_dirs = pkg\n",
            "pkg/a.py": BANDIT_HIT.replace("eval(cmd)", "eval(cmd)  # nosec"),
        },
    )
    report = ratchet_mod.ratchet(base, ("bandit",))
    assert report["status"] in ("FAIL", "BASE_POLICY_RED")
    assert [row["path"] for row in report["added_debt"]] == ["pkg/a.py"]
    assert ratchet_mod.main(["--base", base, "--tools", "bandit"]) == 1


@needs_tools
def test_root_points_a_copied_ratchet_at_the_checkout(repo, monkeypatch):
    base = commit(repo, {"pkg/a.py": CLEAN})
    commit(repo, {"pkg/a.py": BANDIT_HIT})
    monkeypatch.setattr(ratchet_mod, "ROOT", repo / "elsewhere")
    assert (
        ratchet_mod.main(["--root", str(repo), "--base", base, "--tools", "bandit"])
        == 1
    )
    assert ratchet_mod.ROOT == repo.resolve()
