#!/usr/bin/env python3
"""Validate changed Markdown, YAML and JSON files for CI document checks."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Sequence

import yaml


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


def _is_real_sha(value: str) -> bool:
    return bool(value and value.strip("0"))


def _commit_exists(ref: str) -> bool:
    result = _run(["git", "cat-file", "-e", f"{ref}^{{commit}}"], check=False)
    return result.returncode == 0


def _fetch_ref(ref: str) -> None:
    _run(["git", "fetch", "--no-tags", "--depth=1", "origin", ref], check=False)


def _github_diff_ranges() -> List[List[str]]:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    base_ref = os.environ.get("GITHUB_BASE_REF", "")
    base_sha = os.environ.get("GITHUB_BASE_SHA", "")
    before = os.environ.get("GITHUB_EVENT_BEFORE", "") or os.environ.get(
        "GITHUB_SHA_BEFORE", ""
    )
    sha = os.environ.get("GITHUB_SHA", "HEAD")
    ranges: List[List[str]] = []

    # PRs must use their merge base, not the first available event range.
    # A base..synthetic-merge diff can include unrelated base-branch history.
    if event_name == "pull_request":
        if not _is_real_sha(base_sha):
            raise RuntimeError("PR document diff requires a valid base SHA")
        if not _commit_exists(base_sha):
            _fetch_ref(base_sha)
        if not _commit_exists(base_sha):
            raise RuntimeError("Cannot resolve PR base SHA; fail closed")
        merge_base = _run(["git", "merge-base", base_sha, "HEAD"], check=False)
        if merge_base.returncode != 0:
            raise RuntimeError("Cannot resolve PR merge base; fail closed")
        ancestor = merge_base.stdout.strip()
        if not ancestor or not _commit_exists(ancestor):
            raise RuntimeError("Invalid PR merge base; fail closed")
        return [[f"{ancestor}..HEAD"]]

    for candidate in (base_sha, before):
        if not _is_real_sha(candidate):
            continue
        if not _commit_exists(candidate):
            _fetch_ref(candidate)
        if _commit_exists(candidate):
            ranges.append([f"{candidate}..{sha}"])

    if event_name == "pull_request" and base_ref:
        _fetch_ref(base_ref)
        if _commit_exists(f"origin/{base_ref}"):
            ranges.append([f"origin/{base_ref}..HEAD"])
            ranges.append([f"origin/{base_ref}...HEAD"])

    if _commit_exists("HEAD~1"):
        ranges.append(["HEAD~1..HEAD"])

    return ranges or [["HEAD~1..HEAD"]]


def changed_files() -> List[Path]:
    result: subprocess.CompletedProcess[str] | None = None
    failed_ranges: List[str] = []
    for diff_range in _github_diff_ranges():
        result = _run(
            ["git", "diff", "--name-only", "--diff-filter=ACMRT", *diff_range],
            check=False,
        )
        if result.returncode == 0:
            break
        failed_ranges.append(" ".join(diff_range))
    else:
        print("Unable to determine changed files. Tried: " + ", ".join(failed_ranges))
        return []

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



def validate_yaml_structure(paths: Iterable[str]) -> int:
    """Parse changed YAML without constructing objects; reject duplicate keys."""
    failures = 0
    for name in paths:
        try:
            path = REPO_ROOT / name
            if path.stat().st_size > 8_000_000:
                raise ValueError("YAML document exceeds 8 MB")
            raw = path.read_text(encoding="utf-8")
            documents = list(yaml.compose_all(raw, Loader=yaml.BaseLoader))
            if not documents:
                raise ValueError("empty YAML document")
            if name.startswith(".github/workflows/") and len(documents) != 1:
                raise ValueError("GitHub Actions workflow requires one YAML document")
            visited: set[int] = set()

            def walk(node: yaml.Node) -> None:
                if id(node) in visited:
                    return
                visited.add(id(node))
                if isinstance(node, yaml.MappingNode):
                    seen: set[str] = set()
                    for key, value in node.value:
                        if not isinstance(key, yaml.ScalarNode):
                            raise ValueError("complex YAML mapping key")
                        if key.value in seen:
                            raise ValueError(
                                f"duplicate YAML key {key.value!r} "
                                f"at line {key.start_mark.line + 1}"
                            )
                        seen.add(key.value)
                        walk(value)
                elif isinstance(node, yaml.SequenceNode):
                    for value in node.value:
                        walk(value)

            for document in documents:
                walk(document)
        except (OSError, UnicodeError, yaml.YAMLError, ValueError) as exc:
            print(f"Invalid YAML structure: {name}: {exc}")
            failures += 1
    return failures


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
    try:
        paths = changed_files()
    except RuntimeError as exc:
        print(f"Changed-doc selection error: {exc}", file=sys.stderr)
        return 1
    markdown = _by_kind(paths, "markdown")
    yaml_paths = _by_kind(paths, "yaml")
    json_paths = _by_kind(paths, "json")

    failures = 0
    failures += run_optional("Markdown", ["markdownlint-cli2"], markdown)
    failures += run_optional("YAML", ["yamllint", "-s", "-d", YAMLLINT_CONFIG], yaml_paths)
    failures += validate_yaml_structure(yaml_paths)
    failures += validate_json(json_paths)
    if not json_paths:
        print("No changed JSON files.")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
