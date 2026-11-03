#!/usr/bin/env python3
"""Validate changed Markdown, YAML and JSON files for CI document checks."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

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
LINT_LINE = re.compile(r"^(.+?):\d+(?::\d+)?\s+(?:error\s+|warning\s+)?(MD\d{3})\b")
YAMLLINT_CONFIG = (
    "{extends: default, rules: {document-start: disable, truthy: disable}}"
)


def _run(
    args: Sequence[str], *, check: bool = True
) -> subprocess.CompletedProcess[str]:
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
        # base.sha is frozen at the event; once the base branch moves it is
        # an ancestor of the synthetic merge's first parent, and diffing from
        # it would charge later base-branch commits to the PR. The first
        # parent is the base tip the PR actually merges into.
        if _commit_exists("HEAD^2"):
            return [["HEAD^1..HEAD"]]
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
        # A failed Git comparison is not evidence of zero changed documents.
        # Propagate the failure to main() so CI cannot report a false green.
        raise RuntimeError(
            "Unable to determine changed files. Tried: " + ", ".join(failed_ranges)
        )

    paths: List[Path] = []
    for line in result.stdout.splitlines():
        path = REPO_ROOT / line
        if path.is_file() and not (IGNORED_PARTS & set(path.parts)):
            paths.append(path.relative_to(REPO_ROOT))
    return paths


def rename_origins() -> Tuple[Set[str], Dict[str, Tuple[str, str]]]:
    """Classify changed files that already existed on the base side of the diff.

    Returns (unchanged, origins): `unchanged` are pure 100% renames (identical
    content already validated on the base branch, e.g. a root refactor move);
    `origins` maps every modified or edited-and-renamed head path to
    (base revision, base path). If no range resolves, both are empty, so every
    changed file is validated in full (stricter, never looser).
    """
    for diff_range in _github_diff_ranges():
        spec = diff_range[0]
        result = _run(
            ["git", "diff", "--name-status", "-M", "--diff-filter=MR", spec],
            check=False,
        )
        if result.returncode != 0:
            continue
        base = spec.split("...")[0] if "..." in spec else spec.split("..")[0]
        unchanged: Set[str] = set()
        origins: Dict[str, Tuple[str, str]] = {}
        for line in result.stdout.splitlines():
            parts = line.split("\t")
            if parts[0] == "R100" and len(parts) == 3:
                unchanged.add(parts[2])
            elif parts[0].startswith("R") and len(parts) == 3:
                origins[parts[2]] = (base, parts[1])
            elif parts[0] == "M" and len(parts) == 2:
                origins[parts[1]] = (base, parts[1])
        return unchanged, origins
    return set(), {}


def _git_blob(rev: str, path: str) -> Tuple[int, bytes]:
    """Content of `rev:path` as UTF-8 bytes (Markdown here is UTF-8)."""
    result = _run(["git", "show", f"{rev}:{path}"], check=False)
    return result.returncode, result.stdout.encode("utf-8")


def markdown_rule_counts(output: str) -> Dict[str, Counter]:
    """Per-file markdownlint rule counts from `file:line[:col] MDxxx/alias ...` lines."""
    counts: Dict[str, Counter] = {}
    for line in output.splitlines():
        match = LINT_LINE.match(line)
        if match:
            counts.setdefault(match.group(1).replace("\\", "/"), Counter())[
                match.group(2)
            ] += 1
    return counts


def ratchet_markdown(paths: List[str], origins: Dict[str, Tuple[str, str]]) -> int:
    """Lint edited Markdown that existed on the base; fail only on findings it adds.

    Legacy documents carry lint debt that a one-line link fix did not create.
    Each file is compared rule by rule with its own base version: a rule whose
    count grows fails, so new problems are still caught and old ones never hide new ones.
    """
    if not paths:
        print("No edited pre-existing Markdown files.")
        return 0
    print(
        f"Ratcheting {len(paths)} edited pre-existing Markdown file(s) against their base."
    )
    # Base copies live in a scratch folder under the repository root and are linted
    # by relative path, exactly like the head files: markdownlint-cli2 globs
    # absolute Windows paths to nothing, and tempfile's owner-only ACL (Python
    # 3.12.4+ on Windows) hides files from it. The folder is removed afterwards.
    scratch = f"changed-docs-base-{uuid.uuid4().hex[:12]}"
    tmp = REPO_ROOT / scratch
    tmp.mkdir()
    try:
        strict: List[str] = []
        for path in paths:
            rev, old = origins[path]
            code, content = _git_blob(rev, old)
            if code != 0:
                strict.append(path)  # base unreadable: validate in full
                continue
            target = tmp / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        failures = run_optional(
            "Markdown (base unreadable)", ["markdownlint-cli2"], strict
        )
        compared = [p for p in paths if p not in strict]
        if not compared:
            return failures
        head = markdown_rule_counts(
            _run(["markdownlint-cli2", *compared], check=False).stdout
        )
        base_out = _run(
            ["markdownlint-cli2", *[f"{scratch}/{p}" for p in compared]], check=False
        ).stdout
        prefix = f"{scratch}/"
        base = {
            k[len(prefix) :] if k.startswith(prefix) else k: v
            for k, v in markdown_rule_counts(base_out).items()
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for path in compared:
        grown = {
            rule: (base.get(path, Counter())[rule], n)
            for rule, n in head.get(path, Counter()).items()
            if n > base.get(path, Counter())[rule]
        }
        for rule, (was, now) in sorted(grown.items()):
            print(f"New Markdown lint findings: {path}: {rule} {was} -> {now}")
            failures += 1
    return failures


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
    unchanged, origins = rename_origins()
    if unchanged:
        print(f"Skipping {len(unchanged)} pure rename(s) with unchanged content.")
    paths = [p for p in paths if p.as_posix() not in unchanged]
    markdown = _by_kind(paths, "markdown")
    yaml_paths = _by_kind(paths, "yaml")
    json_paths = _by_kind(paths, "json")

    failures = 0
    failures += run_optional(
        "Markdown", ["markdownlint-cli2"], [m for m in markdown if m not in origins]
    )
    failures += ratchet_markdown([m for m in markdown if m in origins], origins)
    failures += run_optional(
        "YAML", ["yamllint", "-s", "-d", YAMLLINT_CONFIG], yaml_paths
    )
    failures += validate_yaml_structure(yaml_paths)
    failures += validate_json(json_paths)
    if not json_paths:
        print("No changed JSON files.")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
