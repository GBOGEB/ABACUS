#!/usr/bin/env python3
"""Generate a MIP self-index receipt for the codespace_jyperter surface."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


SURFACE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SURFACE_ROOT.parents[1]
DEFAULT_OUTPUT = SURFACE_ROOT / "MIP" / "receipts" / "surface_self_index.json"
IGNORED_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".venv", "venv"}
TEXT_EXTS = {".py", ".md", ".yaml", ".yml", ".json", ".toml", ".txt", ".sh", ".ps1", ".bat"}


def run_git(args: list[str]) -> str | None:
    try:
        return subprocess.check_output(["git", "-C", str(REPO_ROOT), *args], stderr=subprocess.DEVNULL, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def iter_files() -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(SURFACE_ROOT):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        base = Path(dirpath)
        for name in filenames:
            rel = (base / name).relative_to(SURFACE_ROOT)
            if not any(part in IGNORED_DIRS for part in rel.parts):
                files.append(rel)
    return sorted(files, key=lambda p: p.as_posix())


def contains_any(path: Path, needles: tuple[str, ...]) -> bool:
    value = path.as_posix().lower()
    return any(needle in value for needle in needles)


def grep_count(files: list[Path], needles: tuple[str, ...]) -> int:
    total = 0
    for rel in files:
        if rel.suffix.lower() not in TEXT_EXTS:
            continue
        try:
            text = (SURFACE_ROOT / rel).read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        if any(needle in text for needle in needles):
            total += 1
    return total


def sample(paths: list[Path], limit: int = 12) -> list[str]:
    return [p.as_posix() for p in paths[:limit]]


def classify(files: list[Path]) -> dict:
    contract = [p for p in files if "contract" in p.as_posix().lower()]
    manifest = [p for p in files if "manifest" in p.as_posix().lower()]
    tests = [p for p in files if "test" in p.as_posix().lower()]
    runners = [p for p in files if contains_any(p, ("runner", "smoke", "parser", "federation"))]
    debug = [p for p in files if contains_any(p, ("debug", "ldab", "lldb", "dap", "trace", "diagnostic", "log"))]
    selfheal = [p for p in files if contains_any(p, ("selfheal", "self_heal", "repair", "recover", "fix"))]
    produce = [p for p in files if contains_any(p, ("federation", "notebook", "parser", "contract", "manifest", "src/"))]
    todo_hits = grep_count(files, ("todo", "fixme", "xxx", "hack", "stale"))

    return {
        "repo_self_assess_debug_ldab": {
            "status": "green" if debug else "red",
            "signals": len(debug),
            "sample_paths": sample(debug),
            "next_action": "Add a tiny parser/federation diagnostic receipt if no debug path exists." if not debug else "Bind diagnostics to the smoke test receipt.",
        },
        "repo_self_assess_runners_mcp": {
            "status": "green" if tests and manifest and contract else "amber",
            "contract_count": len(contract),
            "manifest_count": len(manifest),
            "test_count": len(tests),
            "runner_signal_count": len(runners),
            "sample_paths": sample(contract + manifest + tests + runners),
            "next_action": "Run the smoke test and bind its output to this surface receipt.",
        },
        "repo_self_assess_codz_health_selfheal": {
            "status": "amber" if todo_hits or selfheal else "green",
            "todo_like_file_count": todo_hits,
            "selfheal_signal_count": len(selfheal),
            "sample_paths": sample(selfheal),
            "next_action": "Recurse on first failing smoke/parser invariant if one appears.",
        },
        "repo_self_produce": {
            "status": "amber" if produce else "red",
            "candidate_count": len(produce),
            "candidate_paths": sample(produce),
            "next_action": "Decide whether notebook_parser + federation manifest becomes an implantable skill or stays ABACUS-local.",
        },
    }


def build_receipt() -> dict:
    files = iter_files()
    status_short = run_git(["status", "--short", "--", str(SURFACE_ROOT.relative_to(REPO_ROOT))]) or ""
    return {
        "schema_version": "0.1",
        "program": "MIP",
        "surface": {
            "path": str(SURFACE_ROOT.relative_to(REPO_ROOT)),
            "type": "nested_integration",
            "parent_repo_root": str(REPO_ROOT),
            "parent_remote": run_git(["remote", "get-url", "origin"]),
            "parent_branch": run_git(["branch", "--show-current"]) or run_git(["rev-parse", "--abbrev-ref", "HEAD"]),
            "parent_sha": run_git(["rev-parse", "HEAD"]),
            "dirty_file_count": len([line for line in status_short.splitlines() if line.strip()]),
            "dirty_summary": status_short.splitlines()[:40],
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "census": {
            "file_count": len(files),
            "extension_counts": dict(Counter(p.suffix.lower() or "<none>" for p in files).most_common(20)),
            "top_directory_counts": dict(Counter(p.parts[0] if len(p.parts) > 1 else "<root>" for p in files).most_common(20)),
        },
        "assessments": classify(files),
        "next_victory_condition": "Run tests for integration/codespace_jyperter, then bind smoke-test PASS/FAIL to the same parent SHA as this receipt.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate CODESPACE/Jupyter surface MIP receipt.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    receipt = build_receipt()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        display_output = args.output.relative_to(REPO_ROOT)
    except ValueError:
        display_output = args.output
    print(f"Wrote {display_output}")
    print(json.dumps({"parent_sha": receipt["surface"]["parent_sha"], "files": receipt["census"]["file_count"], "dirty": receipt["surface"]["dirty_file_count"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
