#!/usr/bin/env python3
"""Split CI red-root findings into PR-touched files versus inherited baseline.

The CI/CD Test Suite enforces repository-wide Black, isort, Flake8 and Bandit
roots. On a pull request those roots are red whenever ``main`` already carries
debt, so a correct fix reads exactly like a regression. This census does not
change any verdict. It reads the raw tool outputs the enforcement steps
already produce, intersects them with the files the pull request changed,
and writes JSON evidence plus a step-summary table.

Findings on touched files are an upper bound on what the pull request
introduced: they include pre-existing findings on lines the PR did not edit.
Findings elsewhere cannot have been introduced by the pull request.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess  # nosec B404 - fixed git argv, no shell, no user input
from pathlib import Path
from typing import Any

SCHEMA = "abacus-red-root-delta/1.0.0"
BLACK_REFORMAT = re.compile(r"^would reformat (?P<path>.+?)\s*$")
BLACK_ERROR = re.compile(r"^error: cannot format (?P<path>.+?): ")
ISORT_ERROR = re.compile(r"^ERROR: (?P<path>.+?) Imports are incorrectly sorted")
FLAKE8_ROW = re.compile(
    r"^(?P<path>[^:\s][^:]*\.pyi?):(?P<line>\d+):(?P<col>\d+): "
    r"(?P<code>[A-Z]+\d+) (?P<message>.*)$"
)


def normalise(path: str, root: Path) -> str:
    """Return a repo-relative POSIX path for absolute or ``./`` tool paths."""
    text = path.strip().replace("\\", "/")
    root_text = root.resolve().as_posix().rstrip("/") + "/"
    text = text.removeprefix(root_text)
    while text.startswith("./"):
        text = text[2:]
    return text


def changed_python_files(root: Path, base: str | None) -> list[str] | None:
    """List ``.py`` files changed between ``base`` and ``HEAD``.

    Returns ``None`` when there is no usable base (push, schedule, or a
    shallow checkout without the parent commit), so callers can report the
    absence of PR context instead of an empty and misleading delta.
    """
    if not base:
        return None
    git = shutil.which("git")
    if git is None:
        return None
    verify = subprocess.run(  # nosec B603 - fixed argv, shell=False
        [git, "rev-parse", "--quiet", "--verify", f"{base}^{{commit}}"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if verify.returncode != 0:
        return None
    diff = subprocess.run(  # nosec B603 - fixed argv, shell=False
        [git, "diff", "--name-only", "--diff-filter=ACMR", base, "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if diff.returncode != 0:
        return None
    return sorted(
        line.strip()
        for line in diff.stdout.splitlines()
        if line.strip().endswith((".py", ".pyi"))
    )


def _read(path: Path | None) -> str | None:
    if path is None or not path.is_file():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def _split(paths: set[str], changed: set[str] | None) -> dict[str, Any]:
    touched = sorted(paths & changed) if changed is not None else []
    return {
        "files_total": len(paths),
        "files_on_touched": touched,
        "files_elsewhere": len(paths) - len(touched),
    }


def census_black(text: str | None, root: Path, changed: set[str] | None):
    if text is None:
        return {"status": "not_run"}
    reformat: set[str] = set()
    errors: set[str] = set()
    for line in text.splitlines():
        if match := BLACK_REFORMAT.match(line):
            reformat.add(normalise(match["path"], root))
        elif match := BLACK_ERROR.match(line):
            errors.add(normalise(match["path"], root))
    result = {"status": "parsed", **_split(reformat, changed)}
    result["parse_errors"] = _split(errors, changed)
    return result


def census_isort(text: str | None, root: Path, changed: set[str] | None):
    if text is None:
        return {"status": "not_run"}
    paths = {
        normalise(match["path"], root)
        for line in text.splitlines()
        if (match := ISORT_ERROR.match(line))
    }
    return {"status": "parsed", **_split(paths, changed)}


def census_flake8(text: str | None, root: Path, changed: set[str] | None):
    if text is None:
        return {"status": "not_run"}
    rows = []
    for line in text.splitlines():
        if match := FLAKE8_ROW.match(line):
            rows.append(
                {
                    "path": normalise(match["path"], root),
                    "line": int(match["line"]),
                    "code": match["code"],
                }
            )
    touched = (
        [row for row in rows if row["path"] in changed] if changed is not None else []
    )
    return {
        "status": "parsed",
        "findings_total": len(rows),
        "findings_on_touched": touched,
        "findings_elsewhere": len(rows) - len(touched),
    }


def census_bandit(text: str | None, root: Path, changed: set[str] | None):
    if text is None:
        return {"status": "not_run"}
    try:
        report = json.loads(text)
    except json.JSONDecodeError:
        return {"status": "unparseable"}
    rows = [
        {
            "path": normalise(item.get("filename", ""), root),
            "line": item.get("line_number"),
            "test_id": item.get("test_id"),
            "severity": item.get("issue_severity"),
        }
        for item in report.get("results", [])
    ]
    errors = {
        normalise(item.get("filename", ""), root) for item in report.get("errors", [])
    }
    touched = (
        [row for row in rows if row["path"] in changed] if changed is not None else []
    )
    return {
        "status": "parsed",
        "findings_total": len(rows),
        "findings_on_touched": touched,
        "findings_elsewhere": len(rows) - len(touched),
        "parse_errors": _split(errors, changed),
    }


def touched_count(tool: dict[str, Any]) -> int:
    if "findings_on_touched" in tool:
        return len(tool["findings_on_touched"])
    if "files_on_touched" in tool:
        return len(tool["files_on_touched"])
    return 0


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root)
    changed_list = changed_python_files(root, args.base)
    changed = set(changed_list) if changed_list is not None else None
    tools: dict[str, Any] = {}
    if args.black_log is not None:
        tools["black"] = census_black(_read(args.black_log), root, changed)
    if args.isort_log is not None:
        tools["isort"] = census_isort(_read(args.isort_log), root, changed)
    if args.flake8_log is not None:
        tools["flake8_critical"] = census_flake8(_read(args.flake8_log), root, changed)
    if args.bandit_json is not None:
        tools["bandit"] = census_bandit(_read(args.bandit_json), root, changed)
    return {
        "schema": SCHEMA,
        "lane": args.lane,
        "pr_context": changed is not None,
        "base": args.base if changed is not None else None,
        "changed_python_files": changed_list or [],
        "tools": tools,
        "touched_findings_upper_bound": sum(touched_count(t) for t in tools.values()),
        "verdict_effect": "none: evidence only, enforcement steps unchanged",
    }


def summary_markdown(payload: dict[str, Any]) -> str:
    lines = [f"### Red-root delta census — {payload['lane']}", ""]
    if not payload["pr_context"]:
        lines.append(
            "_No pull-request base available; all findings are whole-repo totals._"
        )
        lines.append("")
    else:
        count = len(payload["changed_python_files"])
        lines.append(f"PR-changed Python files: **{count}**")
        lines.append("")
    lines.append("| Tool | Total | On PR-touched files | Elsewhere (inherited) |")
    lines.append("|---|---:|---:|---:|")
    for name, tool in payload["tools"].items():
        if tool.get("status") != "parsed":
            lines.append(f"| {name} | {tool.get('status')} | – | – |")
            continue
        total = tool.get("findings_total", tool.get("files_total", 0))
        elsewhere = tool.get("findings_elsewhere", tool.get("files_elsewhere", 0))
        touched = touched_count(tool) if payload["pr_context"] else "–"
        lines.append(f"| {name} | {total} | {touched} | {elsewhere} |")
    lines.append("")
    lines.append(
        "Touched-file counts are an upper bound on PR-introduced findings. "
        "This census does not change the enforcement verdict."
    )
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lane", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--base", help="Git revision the PR is compared against.")
    parser.add_argument("--black-log", type=Path)
    parser.add_argument("--isort-log", type=Path)
    parser.add_argument("--flake8-log", type=Path)
    parser.add_argument("--bandit-json", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_payload(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    markdown = summary_markdown(payload)
    if args.summary is not None:
        with args.summary.open("a", encoding="utf-8") as handle:
            handle.write(markdown)
    print(markdown, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
