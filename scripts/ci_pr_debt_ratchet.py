#!/usr/bin/env python3
"""PR admission ratchet for repository-wide static-analysis debt.

The full-red jobs in ``ci-cd-tests.yml`` scan the whole repository, so on a
pull request they report debt the PR did not create. This script compares
the PR's changed Python files at the PR base and at the checked-out head and
fails only if the PR adds debt:

* ``black`` / ``isort``: a file that was clean at the base must stay clean,
  and a new file must be clean. Files that were already unformatted at the
  base may stay unformatted.
* ``flake8``: the critical selection (E9, F63, F7, F82) finding count per
  changed file must not increase.
* ``bandit``: the finding count per changed file must not increase. In
  test files B101 (``assert`` use) is not counted, since that is how pytest
  tests assert.

The full-repository scans still run and are still enforced on main pushes,
schedules and manual runs; see docs/ci/DAB_FULL_RED_GATES_AND_PROOF_GROWTH.md.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess  # nosec B404
import sys
import tempfile
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
)


def git(*args: str) -> str:
    return subprocess.run(  # nosec B603 B607
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout


def changed_python_files(base: str) -> dict[str, str]:
    """Map each changed head path to the path it had at the base.

    A renamed file maps to its original path, so it is compared with its own
    base content rather than treated as new.
    """
    output = git(
        "diff", "--name-status", "-z", "-M", "--diff-filter=ACMR", base, "HEAD", "--"
    )
    fields = output.split("\0")
    changed = {}
    index = 0
    while index < len(fields) and fields[index]:
        status = fields[index]
        if status[0] in "RC":
            old, new = fields[index + 1], fields[index + 2]
            if status[0] == "C":
                # A copy is a new file: its debt is the PR's.
                old = new
            index += 3
        else:
            old = new = fields[index + 1]
            index += 2
        if new.endswith(".py"):
            changed[new] = old
    return dict(sorted(changed.items()))


def base_snapshot(base: str, paths: dict[str, str], target: Path) -> list[str]:
    """Write each path's base content into target, under its head path."""
    existing = []
    for path, base_path in paths.items():
        result = subprocess.run(  # nosec B603 B607
            ["git", "show", f"{base}:{base_path}"],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            continue
        destination = target / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(result.stdout)
        existing.append(path)
    return existing


class ToolError(RuntimeError):
    """A lint tool could not produce a result; the ratchet fails closed."""


def require_tools(tools: tuple[str, ...]) -> None:
    missing = [tool for tool in tools if importlib.util.find_spec(tool) is None]
    if missing:
        raise ToolError(f"not installed: {', '.join(missing)}")


def tool_error(tool: str, path: str, result: subprocess.CompletedProcess) -> ToolError:
    detail = (result.stderr or result.stdout or "").strip().splitlines()
    tail = detail[-1] if detail else "no output"
    return ToolError(f"{tool} exited {result.returncode} on {path}: {tail}")


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    # Lint tools run through sys.executable with fixed arguments.
    return subprocess.run(  # nosec B603
        cmd, cwd=cwd, capture_output=True, text=True, check=False
    )


def formatting_debt(tool: str, root: Path, path: str) -> int:
    """1 if the formatter would change the file, else 0."""
    if tool == "black":
        cmd = [sys.executable, "-m", "black", "--check", "--quiet", path]
    else:
        # --src keeps first-party import detection tied to the repository,
        # so the base snapshot sorts imports the same way the head does.
        cmd = [
            sys.executable,
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
        return 1
    if result.returncode not in (0, 1):
        raise tool_error(tool, path, result)
    return result.returncode


def flake8_debt(root: Path, path: str) -> int:
    result = run(
        [
            sys.executable,
            "-m",
            "flake8",
            f"--select={FLAKE8_SELECT}",
            "--format=%(path)s",
            path,
        ],
        root,
    )
    findings = [line for line in result.stdout.splitlines() if line.strip()]
    # Flake8 exits 1 with findings; any other non-zero exit, or 1 with no
    # findings printed, means it did not run (bad config, crash).
    if result.returncode not in (0, 1) or (result.returncode == 1 and not findings):
        raise tool_error("flake8", path, result)
    return len(findings)


def is_test_file(path: str) -> bool:
    name = Path(path).name
    return (
        "/tests/" in f"/{path}"
        or name.startswith("test_")
        or name.endswith("_test.py")
        or name == "conftest.py"
    )


def bandit_debt(root: Path, path: str) -> int:
    cmd = [sys.executable, "-m", "bandit", "-q", "-f", "json"]
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
    results = payload.get("results", [])
    if payload.get("errors"):
        # Bandit could not scan the file (usually a syntax error): debt.
        return len(results) + 1
    return len(results)


def debt(tool: str, root: Path, path: str) -> int:
    if tool in ("black", "isort"):
        return formatting_debt(tool, root, path)
    if tool == "flake8":
        return flake8_debt(root, path)
    return bandit_debt(root, path)


def ratchet(base: str, tools: tuple[str, ...]) -> dict:
    require_tools(tools)
    paths = changed_python_files(base)
    rows = []
    with tempfile.TemporaryDirectory() as scratch:
        base_root = Path(scratch)
        at_base = set(base_snapshot(base, paths, base_root))
        for name in CONFIG_FILES:
            if (ROOT / name).is_file():
                (base_root / name).write_bytes((ROOT / name).read_bytes())
        for path in paths:
            for tool in tools:
                head_count = debt(tool, ROOT, path)
                base_count = debt(tool, base_root, path) if path in at_base else 0
                rows.append(
                    {
                        "path": path,
                        "tool": tool,
                        "base": base_count,
                        "head": head_count,
                        "added": max(0, head_count - base_count),
                    }
                )
    added = [row for row in rows if row["added"]]
    return {
        "schema": "abacus-pr-debt-ratchet/1.0.0",
        "base": base,
        "tools": list(tools),
        "changed_python_files": list(paths),
        "renamed_from": {new: old for new, old in paths.items() if new != old},
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
    ]
    for row in report["added_debt"]:
        lines.append(
            f"  - `{row['path']}` {row['tool']}: "
            f"{row['base']} at base -> {row['head']} at head"
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
    return 1 if report["added_debt"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
