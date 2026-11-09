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
Findings elsewhere are inherited only when the PR leaves tool configuration
alone. If it changes a file that steers the tools (``pyproject.toml``,
``setup.cfg``, the workflow, ...), every finding may be new, so attribution
is reported as ``indeterminate`` instead.
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
# Files that can change Black/isort/Flake8/Bandit results repo-wide.
CONFIG_FILES = frozenset(
    {
        "pyproject.toml",
        "setup.cfg",
        "tox.ini",
        ".flake8",
        ".isort.cfg",
        ".bandit",
        "bandit.yaml",
        "bandit.yml",
        ".github/workflows/ci-cd-tests.yml",
    }
)
CONFIG_PREFIXES = ("requirements",)
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


def changed_files(root: Path, base: str | None) -> list[str] | None:
    """List every path changed between ``base`` and ``HEAD``.

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
        [git, "diff", "--name-only", base, "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if diff.returncode != 0:
        return None
    return sorted({line.strip() for line in diff.stdout.splitlines() if line.strip()})


def changed_python_files(root: Path, base: str | None) -> list[str] | None:
    """Changed ``.py``/``.pyi`` files that still exist at ``HEAD``."""
    paths = changed_files(root, base)
    if paths is None:
        return None
    return [
        path
        for path in paths
        if path.endswith((".py", ".pyi")) and (root / path).is_file()
    ]


def config_changes(paths: list[str]) -> list[str]:
    """Changed files that can alter tool results across the whole repo."""
    return [
        path
        for path in paths
        if path in CONFIG_FILES or Path(path).name.startswith(CONFIG_PREFIXES)
    ]


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
    """Touched findings, counting parse failures as findings too."""
    if "findings_on_touched" in tool:
        count = len(tool["findings_on_touched"])
    else:
        count = len(tool.get("files_on_touched", []))
    return count + len(tool.get("parse_errors", {}).get("files_on_touched", []))


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root)
    all_changed = changed_files(root, args.base)
    changed_list = changed_python_files(root, args.base)
    changed = set(changed_list) if changed_list is not None else None
    configs = config_changes(all_changed) if all_changed is not None else []
    if changed is None:
        attribution = "no_pr_context"
    elif configs:
        attribution = "indeterminate"
    else:
        attribution = "attributable"
    tools: dict[str, Any] = {}
    if args.black_log is not None:
        tools["black"] = census_black(_read(args.black_log), root, changed)
    if args.isort_log is not None:
        tools["isort"] = census_isort(_read(args.isort_log), root, changed)
    if args.flake8_log is not None:
        tools["flake8_critical"] = census_flake8(_read(args.flake8_log), root, changed)
    if args.bandit_json is not None:
        tools["bandit"] = census_bandit(_read(args.bandit_json), root, changed)

    # Missing PR context, a global tool-config change or an unreadable log
    # cannot establish a touched-file bound. A numeric zero in those cases
    # falsely looks like a verified absence of new findings. This is still
    # input qualification only, never scanner-exit or independent CI proof.
    incomplete_tools = sorted(
        name for name, receipt in tools.items() if receipt.get("status") != "parsed"
    )
    if changed is None:
        qualification = "NO_PR_CONTEXT"
    elif configs:
        qualification = "INDETERMINATE_CONFIG_CHANGE"
    elif not tools:
        qualification = "NO_SCANNERS_SELECTED"
    elif incomplete_tools:
        qualification = "INCOMPLETE_SCANNER_INPUTS"
    else:
        qualification = "QUALIFIED_INPUTS_ONLY"
    touched_upper_bound = (
        sum(touched_count(tool) for tool in tools.values())
        if qualification == "QUALIFIED_INPUTS_ONLY"
        else None
    )
    return {
        "schema": SCHEMA,
        "lane": args.lane,
        "pr_context": changed is not None,
        "base": args.base if changed is not None else None,
        "changed_python_files": changed_list or [],
        "config_changes": configs,
        "attribution": attribution,
        "tools": tools,
        "touched_findings_upper_bound": touched_upper_bound,
        "touched_findings_qualification": qualification,
        "incomplete_tools": incomplete_tools,
        "qualification_scope": "local source/log inputs; not CI scanner-exit or root closure",
        "verdict_effect": "none: evidence only, enforcement steps unchanged",
    }


def _row(name: str, part: dict[str, Any], pr_context: bool) -> str:
    total = part.get("findings_total", part.get("files_total", 0))
    elsewhere = part.get("findings_elsewhere", part.get("files_elsewhere", 0))
    if "findings_on_touched" in part:
        touched = len(part["findings_on_touched"])
    else:
        touched = len(part.get("files_on_touched", []))
    shown = touched if pr_context else "–"
    return f"| {name} | {total} | {shown} | {elsewhere} |"


def summary_markdown(payload: dict[str, Any]) -> str:
    lines = [f"### Red-root delta census — {payload['lane']}", ""]
    attribution = payload.get("attribution", "no_pr_context")
    if attribution == "no_pr_context":
        lines.append(
            "_No pull-request base available; all findings are whole-repo totals._"
        )
    else:
        count = len(payload["changed_python_files"])
        lines.append(f"PR-changed Python files: **{count}**")
    if attribution == "indeterminate":
        changed = ", ".join(f"`{path}`" for path in payload["config_changes"])
        lines.append("")
        lines.append(
            f"**Attribution indeterminate:** this PR changes {changed}, which "
            "can alter results for every file, so findings elsewhere are not "
            "proven inherited."
        )
    lines.append("")
    label = "Elsewhere (inherited)" if attribution == "attributable" else "Elsewhere"
    lines.append(f"| Tool | Total | On PR-touched files | {label} |")
    lines.append("|---|---:|---:|---:|")
    pr_context = attribution != "no_pr_context"
    for name, tool in payload["tools"].items():
        if tool.get("status") != "parsed":
            lines.append(f"| {name} | {tool.get('status')} | – | – |")
            continue
        lines.append(_row(name, tool, pr_context))
        if "parse_errors" in tool:
            lines.append(_row(f"{name} parse errors", tool["parse_errors"], pr_context))
    lines.append("")
    qualified_bound = payload.get("touched_findings_upper_bound")
    qualification = payload.get("touched_findings_qualification", "UNKNOWN")
    label = str(qualified_bound) if qualified_bound is not None else "UNKNOWN"
    lines.append(f"Qualified touched-file bound: **{label}** ({qualification}).")
    lines.append(
        "Bound qualification checks available input/log populations only; "
        "it never attests native scanner exit, approval or root closure."
    )
    lines.append("")
    lines.append(
        "Touched-file counts (parse errors included) are an upper bound on "
        "PR-introduced findings. This census does not change the enforcement "
        "verdict."
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
