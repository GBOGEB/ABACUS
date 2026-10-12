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

A PR that changes lint configuration (any of ``CONFIG_FILES``) can change
results for every file, which a per-file comparison cannot attribute, so the
ratchet does not admit it: it exits 3 and the full-repository result applies.

The full-repository scans still run and are still enforced on main pushes,
schedules and manual runs; see docs/ci/DAB_FULL_RED_GATES_AND_PROOF_GROWTH.md.
"""

from __future__ import annotations

import argparse
import json
import subprocess  # nosec B404
import sys
import tempfile
from collections import Counter
from pathlib import Path

# subprocess runs only git and the lint tools, with fixed arguments.
ROOT = Path(__file__).resolve().parents[1]
FLAKE8_SELECT = "E9,F63,F7,F82"
TOOLS = ("black", "isort", "flake8", "bandit")
# Copied into the base snapshot so both sides run under the head's config.
CONFIG_FILES = (
    "pyproject.toml",
    "setup.cfg",
    "tox.ini",
    ".flake8",
    ".isort.cfg",
    ".bandit",
    # isort reads indent and line_length from .editorconfig.
    ".editorconfig",
)
# Installed by the Code Quality job after the lint tools (repo-root path), so
# a pin there can replace Black, isort, Flake8 or add a Flake8 plugin. Not
# copied to the base snapshot; a change to it always needs the full scan.
TOOL_ENVIRONMENT_FILES = ("requirements-test.txt",)


def git(*args: str) -> str:
    return subprocess.run(  # nosec B603 B607
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout


def changed_config_files(base: str) -> list[str]:
    """Lint config and tool-environment paths the PR adds, edits, deletes
    or renames.

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
    return sorted(
        path
        for path in paths
        if Path(path).name in CONFIG_FILES or path in TOOL_ENVIRONMENT_FILES
    )


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
            if status[0] == "C" or not old.endswith(".py"):
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
        if new.endswith(".py"):
            changed[new] = old
    return dict(sorted(changed.items()))


def base_snapshot(base: str, paths: dict[str, str | None], target: Path) -> list[str]:
    """Write each path's base content into target at its base path.

    A renamed file keeps its original path, so tools apply the configuration
    that governed it at the base and classify it by its original directory.
    """
    existing = []
    for path, base_path in paths.items():
        if base_path is None:
            continue
        result = subprocess.run(  # nosec B603 B607
            ["git", "show", f"{base}:{base_path}"],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            continue
        destination = target / base_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(result.stdout)
        existing.append(path)
    return existing


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
    if tool == "black":
        cmd = [*PYTHON, "-m", "black", "--check", "--quiet", path]
    else:
        # --src keeps first-party import detection tied to the repository,
        # so the base snapshot sorts imports the same way the head does.
        cmd = [
            *PYTHON,
            "-m",
            "isort",
            "--check-only",
            "--quiet",
            "--src",
            str(ROOT),
            path,
        ]
    result = run(cmd, root)
    if tool == "black" and result.returncode == 123:
        # Black could not parse the file: a syntax error is debt, not clean.
        return Counter({"unparseable": 1})
    if result.returncode not in (0, 1):
        raise tool_error(tool, path, result)
    return Counter({"unformatted": 1}) if result.returncode else Counter()


def flake8_debt(root: Path, path: str) -> Counter:
    result = run(
        [
            *PYTHON,
            "-m",
            "flake8",
            f"--select={FLAKE8_SELECT}",
            "--format=%(code)s",
            path,
        ],
        root,
    )
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
    cmd = [*PYTHON, "-m", "bandit", "-q", "-f", "json"]
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
        number = item.get("line_number") or 0
        source = lines[number - 1].strip() if 0 < number <= len(lines) else ""
        findings[f"{item.get('test_id')}:{item.get('issue_severity')}:{source}"] += 1
    if payload.get("errors"):
        # Bandit could not scan the file (usually a syntax error): debt.
        findings["scan_error"] += 1
    return findings


def debt(tool: str, root: Path, path: str) -> Counter:
    if tool in ("black", "isort"):
        return formatting_debt(tool, root, path)
    if tool == "flake8":
        return flake8_debt(root, path)
    return bandit_debt(root, path)


def ratchet(base: str, tools: tuple[str, ...]) -> dict:
    require_tools(tools)
    configs = changed_config_files(base)
    paths = changed_python_files(base)
    report = {
        "schema": "abacus-pr-debt-ratchet/1.3.0",
        "base": base,
        "tools": list(tools),
        "changed_config_files": configs,
        "changed_python_files": list(paths),
        "renamed_from": {new: old for new, old in paths.items() if old and new != old},
    }
    if configs:
        return {**report, "rows": [], "added_debt": [], "status": "FULL_SCAN_REQUIRED"}
    rows = []
    with tempfile.TemporaryDirectory() as scratch:
        base_root = Path(scratch)
        at_base = set(base_snapshot(base, paths, base_root))
        # Config is unchanged here (a change returns FULL_SCAN_REQUIRED), so
        # copy every tracked config file to its own directory: tools find
        # nested configs (e.g. pkg/pyproject.toml) the same way on both sides.
        for name in tracked_config_files():
            if (ROOT / name).is_file():
                destination = base_root / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((ROOT / name).read_bytes())
        for path in paths:
            for tool in tools:
                head = debt(tool, ROOT, path)
                # The base side is scanned at its own path, so a rename keeps
                # its original directory's config and test-file status: a
                # test moved into production code loses its B101 exemption.
                at_base_debt = (
                    debt(tool, base_root, paths[path]) if path in at_base else Counter()
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
    added = [row for row in rows if row["added"]]
    return {
        **report,
        "rows": rows,
        "added_debt": added,
        "status": "FAIL" if added else "PASS",
    }


def summary(report: dict) -> str:
    lines = [
        "### PR new-debt ratchet",
        "",
        f"- tools: {', '.join(report['tools'])}",
        f"- changed Python files: **{len(report['changed_python_files'])}**",
        f"- files/tools with added debt: **{len(report['added_debt'])}**",
        f"- status: **{report['status']}**",
    ]
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
    parser.add_argument("--out", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args(argv)

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
    if report["changed_config_files"]:
        return 3
    return 1 if report["added_debt"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
