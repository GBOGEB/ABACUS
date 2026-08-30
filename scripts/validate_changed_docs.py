#!/usr/bin/env python3
"""Validate changed Markdown, YAML and JSON files for CI document checks."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".json": "json",
}
IGNORED_PARTS = {".git", "node_modules"}
YAMLLINT_CONFIG = (
    "{extends: default, rules: {document-start: disable, truthy: disable}}"
)


def _run(args: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=REPO_ROOT,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def _github_diff_range() -> List[str]:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    base_ref = os.environ.get("GITHUB_BASE_REF", "")
    before = os.environ.get("GITHUB_EVENT_BEFORE", "") or os.environ.get("GITHUB_SHA_BEFORE", "")
    sha = os.environ.get("GITHUB_SHA", "HEAD")

    if event_name == "pull_request" and base_ref:
        _run(["git", "fetch", "--no-tags", "--depth=1", "origin", base_ref], check=False)
        return [f"origin/{base_ref}...HEAD"]

    if before and before.strip("0"):
        return [f"{before}..{sha}"]

    return ["HEAD~1..HEAD"]


def changed_files() -> List[Path]:
    diff_range = _github_diff_range()
    result = _run(["git", "diff", "--name-only", "--diff-filter=ACMRT", *diff_range])
    paths: List[Path] = []
    for line in result.stdout.splitlines():
        path = REPO_ROOT / line
        if path.is_file() and not (IGNORED_PARTS & set(path.parts)):
            paths.append(path.relative_to(REPO_ROOT))
    return paths


def _by_kind(paths: Iterable[Path], kind: str) -> List[str]:
    return [
        path.as_posix()
        for path in paths
        if TEXT_SUFFIXES.get(path.suffix.lower()) == kind
    ]


def validate_json(paths: Iterable[str]) -> int:
    failures = 0
    for path in paths:
        try:
            json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - exact parser message is enough
            print(f"Invalid JSON: {path}: {exc}")
            failures += 1
    return failures


def run_optional(label: str, command: Sequence[str], paths: List[str]) -> int:
    if not paths:
        print(f"No changed {label} files.")
        return 0

    print(f"Validating {len(paths)} changed {label} file(s).")
    result = _run([*command, *paths], check=False)
    if result.stdout:
        print(result.stdout, end="")
    return result.returncode


def main() -> int:
    paths = changed_files()
    markdown = _by_kind(paths, "markdown")
    yaml_paths = _by_kind(paths, "yaml")
    json_paths = _by_kind(paths, "json")

    failures = 0
    failures += run_optional("Markdown", ["markdownlint-cli2"], markdown)
    failures += run_optional("YAML", ["yamllint", "-s", "-d", YAMLLINT_CONFIG], yaml_paths)
    failures += validate_json(json_paths)
    if not json_paths:
        print("No changed JSON files.")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
