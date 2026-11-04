#!/usr/bin/env python3
"""PR admission ratchet for repository-wide static-analysis debt.

The full-red jobs in ``ci-cd-tests.yml`` scan the whole repository, so on a
pull request they report debt the PR did not create. This script compares
the PR's changed Python files at the PR base and at the checked-out head and
fails only if the PR adds debt:

* ``black`` / ``isort``: a file that was clean at the base must stay clean,
  and a new file must be clean. Files that were already unformatted at the
  base may stay unformatted.
* ``flake8``: for each code in the critical selection (E9, F63, F7, F82),
  the per-file count must not increase.
* ``bandit``: for each test id and severity, the per-file count must not
  increase, so removing one finding cannot pay for a different new one. In
  test files B101 (``assert`` use) is not counted, since that is how pytest
  tests assert.

A PR that changes lint configuration (``CONFIG_TOOLS``) or the files that
install and invoke the tools (``TOOL_ENVIRONMENT_FILES``) can change results
for every file, which a per-file comparison cannot attribute, so the ratchet
does not admit it for the tools that file affects: it exits 3 and the
full-repository result applies.

The full-repository scans still run on every event. For Black, isort and
Flake8 they are census on main pushes, schedules and manual runs too: there
the ratchet compares with the previous main tip. Bandit's full scan is still
enforced on those events; see docs/ci/DAB_FULL_RED_GATES_AND_PROOF_GROWTH.md.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess  # nosec B404
import sys
import tempfile
from collections import Counter
from pathlib import Path

# subprocess runs only git and the lint tools, with fixed arguments.
ROOT = Path(__file__).resolve().parents[1]
FLAKE8_SELECT = "E9,F63,F7,F82"
TOOLS = ("black", "isort", "flake8", "bandit")
# Lint config, mapped to the tools that read it. Copied into the base
# snapshot so both sides run under the head's config; a change sends only
# the tools that read the file to the full scan, so tightening .bandit is
# not judged by the repository-wide Black result.
CONFIG_TOOLS = {
    # Black reads only pyproject.toml; Flake8 does not read it. Bandit
    # reads .bandit only (no -c is passed).
    "pyproject.toml": ("black", "isort"),
    "setup.cfg": ("isort", "flake8"),
    "tox.ini": ("isort", "flake8"),
    ".flake8": ("flake8",),
    ".isort.cfg": ("isort",),
    ".bandit": ("bandit",),
    # isort reads indent and line_length from .editorconfig.
    ".editorconfig": ("isort",),
    # Black's, isort's and Bandit's recursive discovery in the full scan
    # skip ignored paths, so .gitignore changes what the full scan covers.
    ".gitignore": ("black", "isort", "bandit"),
}
CONFIG_FILES = tuple(CONFIG_TOOLS)
# Repo-root paths that install or invoke the tools. Not copied to the base
# snapshot; a change to one always needs the full scan for its tools.
TOOL_ENVIRONMENT_FILES = {
    # Installed by the Code Quality job after the lint tools, so a pin
    # there can replace Black, isort, Flake8 or add a Flake8 plugin. The
    # Security job installs Bandit on its own.
    "requirements-test.txt": ("black", "isort", "flake8"),
    # Installs every tool and sets the full-scan commands and flags.
    ".github/workflows/ci-cd-tests.yml": TOOLS,
    # The ratchet runs from the head, so it would admit its own weakening.
    "scripts/ci_pr_debt_ratchet.py": TOOLS,
}


def git(*args: str) -> str:
    return subprocess.run(  # nosec B603 B607
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout


def config_tools(path: str) -> tuple[str, ...]:
    """Tools whose full-scan result a change to ``path`` can alter."""
    if path in TOOL_ENVIRONMENT_FILES:
        return TOOL_ENVIRONMENT_FILES[path]
    return CONFIG_TOOLS.get(Path(path).name, ())


def changed_config_files(base: str, tools: tuple[str, ...] = TOOLS) -> list[str]:
    """Lint config and tool-environment paths the PR adds, edits, deletes
    or renames that ``tools`` read.

    Both sides of a rename count, so renaming ``.editorconfig`` away is a
    config change too.
    """
    output = git("diff", "--name-status", "-z", "-M", base, "HEAD", "--")
    fields = output.split("\0")
    paths = set()
    index = 0
    while index < len(fields) and fields[index]:
        width = 3 if fields[index][0] in "RC" else 2
        paths.update(fields[index + 1 : index + width])
        index += width
    return sorted(path for path in paths if set(config_tools(path)) & set(tools))


def tracked_config_files() -> list[str]:
    output = git("ls-files", "-z")
    return [p for p in output.split("\0") if p and Path(p).name in CONFIG_FILES]


def changed_python_files(base: str) -> dict[str, str | None]:
    """Map each changed head path to the path it had at the base.

    A renamed file maps to its original path, so it is compared with its own
    base content rather than treated as new. A file with no base counterpart
    maps to None: all of its debt is the PR's.
    """
    output = git(
        "diff", "--name-status", "-z", "-M", "--diff-filter=ACMRT", base, "HEAD", "--"
    )
    fields = output.split("\0")
    changed = {}
    index = 0
    while index < len(fields) and fields[index]:
        status = fields[index]
        if status[0] in "RC":
            old, new = fields[index + 1], fields[index + 2]
            if status[0] == "C" or not old.endswith((".py", ".pyi")):
                # A copy, or a non-Python file renamed to .py, is a new
                # Python file: its debt is the PR's.
                old = None
            index += 3
        else:
            new = fields[index + 1]
            # An added path has no base. A type change (symlink or submodule
            # to a regular file) has no comparable base content either.
            old = None if status[0] in "AT" else new
            index += 2
        if new.endswith((".py", ".pyi")):
            changed[new] = old
    return dict(sorted(changed.items()))


def base_snapshot(base: str, paths: dict[str, str | None], target: Path) -> list[str]:
    """Export the whole base tree into target; list the head paths it covers.

    The full tree, not only the changed files, so isort classifies imports
    against the base's own packages: a package the PR deletes is still
    first-party on the base side. A renamed file keeps its original path, so
    it keeps its original test-file status.
    """
    export_tree(base, target)
    existing = []
    for path, base_path in paths.items():
        if base_path is None:
            continue
        source = target / base_path
        if source.is_file() and not source.is_symlink():
            existing.append(path)
    return existing


def export_tree(rev: str, target: Path) -> None:
    """Write the tree of ``rev`` into target (no .git, no untracked files)."""
    archive = subprocess.Popen(  # nosec B603 B607
        ["git", "archive", "--format=tar", rev], cwd=ROOT, stdout=subprocess.PIPE
    )
    extract = subprocess.run(  # nosec B603 B607
        ["tar", "-x", "-f", "-", "-C", str(target)],
        stdin=archive.stdout,
        capture_output=True,
        check=False,
    )
    archive.stdout.close()
    if archive.wait() != 0 or extract.returncode != 0:
        raise ToolError(f"could not export {rev}: {extract.stderr!r}")


class ToolError(RuntimeError):
    """A lint tool could not produce a result; the ratchet fails closed."""


# Every scan runs in an isolated interpreter (-I): the checkout is not on
# sys.path, so a PR that adds bandit.py or black.py cannot stand in for the
# installed tool.
PYTHON = (sys.executable, "-I")
FIND_ORIGIN = (
    "import importlib.util, sys; "
    "spec = importlib.util.find_spec(sys.argv[1]); "
    "print(spec.origin if spec and spec.origin else '')"
)


def tool_origin(tool: str) -> str:
    """Where an isolated interpreter in the checkout imports ``tool`` from."""
    return run([*PYTHON, "-c", FIND_ORIGIN, tool], ROOT).stdout.strip()


def require_tools(tools: tuple[str, ...]) -> None:
    missing, shadowed = [], []
    root, prefix = ROOT.resolve(), Path(sys.prefix).resolve()
    for tool in tools:
        origin = tool_origin(tool)
        if not origin:
            missing.append(tool)
            continue
        path = Path(origin).resolve()
        if path.is_relative_to(root) and not path.is_relative_to(prefix):
            shadowed.append(f"{tool} ({origin})")
    if missing:
        raise ToolError(f"not installed: {', '.join(missing)}")
    if shadowed:
        raise ToolError(f"resolved inside the checkout: {', '.join(shadowed)}")


def tool_error(tool: str, path: str, result: subprocess.CompletedProcess) -> ToolError:
    detail = (result.stderr or result.stdout or "").strip().splitlines()
    tail = detail[-1] if detail else "no output"
    return ToolError(f"{tool} exited {result.returncode} on {path}: {tail}")


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    # Lint tools run through sys.executable with fixed arguments.
    return subprocess.run(  # nosec B603
        cmd, cwd=cwd, capture_output=True, text=True, check=False
    )


def formatting_debt(tool: str, root: Path, path: str) -> Counter:
    """One "unformatted" finding if the formatter would change the file."""
    # The full scan runs ``black .`` and ``isort .`` from the root, which
    # read only the root's configuration. Given a single file, both would
    # look upward from that file's directory and could pick a nested
    # config instead, so pin them to the root like the full scan.
    if tool == "black":
        config = root / "pyproject.toml"
        cmd = [
            *PYTHON,
            "-m",
            "black",
            "--check",
            "--quiet",
            "--config",
            str(config) if config.is_file() else os.devnull,
            path,
        ]
    else:
        # --src is the tree being scanned (the checkout, or the exported
        # base), so each side classifies imports against its own packages.
        cmd = [
            *PYTHON,
            "-m",
            "isort",
            "--check-only",
            "--quiet",
            "--settings-path",
            str(root),
            "--src",
            str(root),
            path,
        ]
    result = run(cmd, root)
    if tool == "black" and result.returncode == 123:
        # Black could not parse the file: a syntax error is debt, not clean.
        return Counter({"unparseable": 1})
    if result.returncode not in (0, 1):
        raise tool_error(tool, path, result)
    return Counter({"unformatted": 1}) if result.returncode else Counter()


def import_roots(rev: str) -> tuple[list[str], list[str]]:
    """The top-level names and top-level ``__init__.py`` files at ``rev``.

    isort run with ``--src`` at the root classifies ``import x`` as
    first-party when ``x`` is a top-level module or package there, so these
    decide every import's section across the whole tree.
    """
    files = git("ls-tree", "-r", "-z", "--name-only", rev).split("\0")
    roots = sorted({path.split("/", 1)[0] for path in files if path})
    inits = sorted(
        path for path in files if path.count("/") == 1 and path.endswith("/__init__.py")
    )
    return roots, inits


ISORT_ERROR = re.compile(r"^ERROR: (.+?) Imports are incorrectly sorted")


def unsorted_files(root: Path) -> set[str]:
    """Paths ``isort --check-only .`` rejects in the tree at root."""
    result = run(
        [
            *PYTHON,
            "-m",
            "isort",
            "--check-only",
            "--quiet",
            "--settings-path",
            str(root),
            "--src",
            str(root),
            ".",
        ],
        root,
    )
    found = set()
    for line in (result.stdout + result.stderr).splitlines():
        match = ISORT_ERROR.match(line)
        if match:
            path = Path(match.group(1)).resolve()
            found.add(path.relative_to(root.resolve()).as_posix())
    if result.returncode not in (0, 1) or (result.returncode == 1 and not found):
        raise tool_error("isort", ".", result)
    return found


def flake8_debt(root: Path, path: str, isolated: bool = False) -> Counter:
    cmd = [
        *PYTHON,
        "-m",
        "flake8",
        # Likewise an inline ``# noqa`` cannot hide a new critical error.
        "--disable-noqa",
        f"--select={FLAKE8_SELECT}",
        "--format=%(code)s",
    ]
    if isolated:
        # The PR changed Flake8 config: read none, so its ignores and
        # per-file-ignores cannot hide a new error on either side.
        cmd.append("--isolated")
    result = run([*cmd, path], root)
    findings = [line for line in result.stdout.splitlines() if line.strip()]
    # Flake8 exits 1 with findings; any other non-zero exit, or 1 with no
    # findings printed, means it did not run (bad config, crash).
    if result.returncode not in (0, 1) or (result.returncode == 1 and not findings):
        raise tool_error("flake8", path, result)
    return Counter(line.strip() for line in findings)


def is_test_file(path: str) -> bool:
    # Only files under a tests/ directory: a test_-named module elsewhere
    # can be production code (e.g. DMAIC_V3/core/test_system_bridge.py).
    return "/tests/" in f"/{path}"


def bandit_debt(root: Path, path: str) -> Counter:
    # --ignore-nosec: a PR cannot silence its own new finding with an inline
    # ``# nosec``; suppressed findings count on both sides alike.
    cmd = [*PYTHON, "-m", "bandit", "-q", "--ignore-nosec", "-f", "json"]
    if is_test_file(path):
        # B101 (assert_used) is how pytest tests assert; it is not a finding
        # in test code.
        cmd += ["--skip", "B101"]
    result = run([*cmd, path], root)
    if result.returncode not in (0, 1):
        raise tool_error("bandit", path, result)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise tool_error("bandit", path, result) from exc
    # A finding is its rule, severity and the flagged source line, so a PR
    # cannot remove one eval() and add a different one under the same rule.
    lines = (root / path).read_text(encoding="utf-8", errors="replace").splitlines()
    findings = Counter()
    for item in payload.get("results", []):
        # The whole reported range: a multi-line call is flagged on its
        # first line, and its arguments are on the lines that follow.
        numbers = item.get("line_range") or [item.get("line_number") or 0]
        source = " ".join(
            lines[number - 1].strip() for number in numbers if 0 < number <= len(lines)
        )
        findings[f"{item.get('test_id')}:{item.get('issue_severity')}:{source}"] += 1
    if payload.get("errors"):
        # Bandit could not scan the file (usually a syntax error): debt.
        findings["scan_error"] += 1
    return findings


def debt(tool: str, root: Path, path: str, isolated: bool = False) -> Counter:
    if tool in ("black", "isort"):
        return formatting_debt(tool, root, path)
    if tool == "flake8":
        return flake8_debt(root, path, isolated)
    return bandit_debt(root, path)


# Tools whose configuration can only suppress findings (skips, excludes,
# ignores). When a PR changes such a config, the full scan that decides runs
# under the PR's own config, so the PR could silence its new findings. The
# head's code must therefore also be clean under the base's config. Black and
# isort configs define the expected output instead, so a change to them
# legitimately changes the full-scan result and is judged by it alone.
POLICY_SCANS = {
    "flake8": ["-m", "flake8", ".", f"--select={FLAKE8_SELECT}", "-q"],
    "bandit": ["-m", "bandit", "-r", ".", "-q", "-f", "json", "-o", os.devnull],
}


def base_policy_scan(base: str, tool: str, configs: list[str]) -> bool:
    """Whether the head's tree passes ``tool``'s full scan under the base's
    version of the changed config files.

    A config file the PR added is removed and one it changed or deleted is
    restored, so a PR cannot relax the policy that judges it.
    """
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        export_tree("HEAD", root)
        for path in configs:
            target = root / path
            if target.is_file() or target.is_symlink():
                target.unlink()
            shown = subprocess.run(  # nosec B603 B607
                ["git", "show", f"{base}:{path}"], cwd=ROOT, capture_output=True
            )
            if shown.returncode == 0:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(shown.stdout)
        result = run([*PYTHON, *POLICY_SCANS[tool]], root)
    if result.returncode not in (0, 1):
        raise tool_error(tool, ".", result)
    return result.returncode == 0


def ratchet(base: str, tools: tuple[str, ...]) -> dict:
    require_tools(tools)
    configs = changed_config_files(base, tools)
    paths = changed_python_files(base)
    report = {
        "schema": "abacus-pr-debt-ratchet/1.9.0",
        "base": base,
        "tools": list(tools),
        "changed_config_files": configs,
        "changed_python_files": list(paths),
        "renamed_from": {new: old for new, old in paths.items() if old and new != old},
    }
    if configs:
        policy = [path for path in configs if path not in TOOL_ENVIRONMENT_FILES]
        red = [
            tool
            for tool in tools
            if tool in POLICY_SCANS
            and any(tool in config_tools(path) for path in policy)
            and not base_policy_scan(
                base, tool, [p for p in policy if tool in config_tools(p)]
            )
        ]
        # Bandit given a file (not -r) reads no .bandit, and Flake8 runs
        # --isolated here, so their per-file comparisons still hold when the
        # config changed, and still catch a new finding, even one under an
        # inline nosec or noqa, that the full scans would not report.
        compared = tuple(tool for tool in ("flake8", "bandit") if tool in tools)
        rows = compare_files(base, paths, compared, report, isolated=True)
        added = [row for row in rows if row["added"]]
        if red:
            status = "BASE_POLICY_RED"
        else:
            status = "FAIL" if added else "FULL_SCAN_REQUIRED"
        return {
            **report,
            "rows": rows,
            "added_debt": added,
            "base_policy_red": red,
            "status": status,
        }
    rows = compare_files(base, paths, tools, report)
    added = [row for row in rows if row["added"]]
    return {
        **report,
        "rows": rows,
        "added_debt": added,
        "status": "FAIL" if added else "PASS",
    }


def compare_files(
    base: str,
    paths: dict[str, str | None],
    tools: tuple[str, ...],
    report: dict,
    isolated: bool = False,
) -> list[dict]:
    """Per-file debt rows for ``tools`` over the changed paths.

    ``isolated`` makes Flake8 read no config, for when the PR changed it.
    """
    rows = []
    with tempfile.TemporaryDirectory() as scratch:
        base_root = Path(scratch)
        at_base = set(base_snapshot(base, paths, base_root))
        # Copy every tracked config file (the head's) to its own directory:
        # tools find nested configs (e.g. pkg/pyproject.toml) the same way on
        # both sides. Only Bandit and isolated Flake8 run here when it changed.
        for name in tracked_config_files():
            if (ROOT / name).is_file():
                destination = base_root / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((ROOT / name).read_bytes())
        for path in paths:
            for tool in tools:
                # Black and isort scan type stubs in broad recursive mode.
                # Flake8-critical and Bandit full-repo jobs target .py files;
                # do not invent .pyi security findings outside their scope.
                if path.endswith(".pyi") and tool not in ("black", "isort"):
                    continue
                head = debt(tool, ROOT, path, isolated)
                # The base side is scanned at its own path, so a rename keeps
                # its original directory's config and test-file status: a
                # test moved into production code loses its B101 exemption.
                at_base_debt = (
                    debt(tool, base_root, paths[path], isolated)
                    if path in at_base
                    else Counter()
                )
                new = head - at_base_debt
                rows.append(
                    {
                        "path": path,
                        "tool": tool,
                        "base": sum(at_base_debt.values()),
                        "head": sum(head.values()),
                        "added": sum(new.values()),
                        "new_findings": dict(sorted(new.items())),
                    }
                )
        # A PR that adds, removes or renames a top-level package changes how
        # isort classifies that import in files the PR did not touch, so
        # compare the whole tree on both sides, as the full scan would.
        if "isort" in tools and import_roots(base) != import_roots("HEAD"):
            report["import_roots_changed"] = True
            base_unsorted = unsorted_files(base_root)
            for path in sorted(unsorted_files(ROOT) - base_unsorted - set(paths)):
                rows.append(
                    {
                        "path": path,
                        "tool": "isort",
                        "base": 0,
                        "head": 1,
                        "added": 1,
                        "new_findings": {"unformatted": 1},
                    }
                )
    return rows


def summary(report: dict) -> str:
    lines = [
        "### PR new-debt ratchet",
        "",
        f"- tools: {', '.join(report['tools'])}",
        f"- changed Python files: **{len(report['changed_python_files'])}**",
        f"- files/tools with added debt: **{len(report['added_debt'])}**",
        f"- status: **{report['status']}**",
    ]
    for tool in report.get("base_policy_red", []):
        lines.append(
            f"- {tool}: the PR's code is not clean under the base's {tool}"
            " configuration, so the config change cannot admit it"
        )
    if report["changed_config_files"]:
        lines.append(
            "- lint configuration changed ("
            + ", ".join(f"`{path}`" for path in report["changed_config_files"])
            + "): per-file comparison does not apply; the full-repository"
            " scan decides"
        )
    for row in report["added_debt"]:
        found = ", ".join(
            f"{key} x{count}" for key, count in row["new_findings"].items()
        )
        lines.append(
            f"  - `{row['path']}` {row['tool']}: "
            f"{row['base']} at base -> {row['head']} at head; new: {found}"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="PR base commit SHA")
    parser.add_argument("--tools", nargs="+", choices=TOOLS, required=True)
    # CI runs the base revision's copy of this script, so a PR cannot weaken
    # the check that admits it; --root points that copy at the checkout.
    parser.add_argument("--root", type=Path, help="checkout to check")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args(argv)
    global ROOT
    if args.root:
        ROOT = args.root.resolve()

    try:
        report = ratchet(args.base, tuple(args.tools))
    except ToolError as exc:
        print(f"::error::PR new-debt ratchet could not run: {exc}")
        return 2
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as handle:
            handle.write(summary(report))
    print(summary(report), end="")
    if report["status"] in ("BASE_POLICY_RED", "FAIL"):
        return 1
    return 3 if report["changed_config_files"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
