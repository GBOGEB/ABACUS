#!/usr/bin/env python3
"""Generate a MIP repo self-index receipt using only stdlib."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "MIP" / "receipts" / "repo_self_index.json"
IGNORED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
}


def run_git(args: list[str]) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), *args],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def iter_files() -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        base = Path(dirpath)
        for name in filenames:
            path = base / name
            rel = path.relative_to(ROOT)
            if any(part in IGNORED_DIRS for part in rel.parts):
                continue
            files.append(rel)
    return sorted(files, key=lambda p: p.as_posix())


def contains_any(path: Path, needles: tuple[str, ...]) -> bool:
    value = path.as_posix().lower()
    return any(needle in value for needle in needles)


def grep_count(files: list[Path], needles: tuple[str, ...]) -> int:
    total = 0
    text_exts = {
        ".py",
        ".md",
        ".yml",
        ".yaml",
        ".json",
        ".toml",
        ".txt",
        ".sh",
        ".ps1",
        ".ts",
        ".js",
    }
    for rel in files:
        if rel.suffix.lower() not in text_exts:
            continue
        try:
            text = (ROOT / rel).read_text(
                encoding="utf-8", errors="ignore"
            ).lower()
        except OSError:
            continue
        if any(needle in text for needle in needles):
            total += 1
    return total


def sample(paths: list[Path], limit: int = 20) -> list[str]:
    return [p.as_posix() for p in paths[:limit]]


def complete_skill_packages(files: list[Path]) -> list[Path]:
    file_set = {path.as_posix() for path in files}
    packages: list[Path] = []
    for entry in files:
        if entry.name != "SKILL.md":
            continue
        if entry.parts[:2] != (".codex", "skills"):
            continue
        root = entry.parent
        required = {
            (root / "agents" / "openai.yaml").as_posix(),
            (root / "scripts" / "validate_receipt.py").as_posix(),
            (root / "references" / "receipt-contract.md").as_posix(),
        }
        if required.issubset(file_set):
            packages.append(root)
    return sorted(packages, key=lambda path: path.as_posix())


def classify(files: list[Path]) -> dict:
    workflows = [p for p in files if p.parts[:2] == (".github", "workflows")]
    docker = [
        p
        for p in files
        if p.name.lower() == "dockerfile"
        or "docker-compose" in p.name.lower()
    ]
    runners = [
        p
        for p in files
        if contains_any(
            p,
            ("runner", "workflow", "ci/", ".github/workflows", "pytest", "test_"),
        )
    ]
    mcp = [p for p in files if contains_any(p, ("mcp", "agent", "orchestrat"))]
    skills = [
        p
        for p in files
        if contains_any(p, ("skill", ".codex/skills", "skill.md"))
    ]
    complete_skills = complete_skill_packages(files)
    debug = [
        p
        for p in files
        if contains_any(
            p,
            ("debug", "lldb", "dap", "trace", "diagnostic", "observability", "log"),
        )
    ]
    selfheal = [
        p
        for p in files
        if contains_any(
            p,
            ("selfheal", "self_heal", "repair", "recover", "autofix", "recursive"),
        )
    ]
    todo_hits = grep_count(files, ("todo", "fixme", "xxx", "hack", "stale"))

    if complete_skills:
        self_produce_status = "green"
        self_produce_next = "Execute the packaged skill validator on exact-SHA evidence."
    elif skills or mcp:
        self_produce_status = "amber"
        self_produce_next = (
            "Select one shareable core skill or one implantable agent/orchestrator candidate."
        )
    else:
        self_produce_status = "red"
        self_produce_next = "Create one complete reusable skill or orchestrator package."

    return {
        "repo_self_assess_debug_ldab": {
            "status": "green" if debug else "red",
            "signals": len(debug),
            "sample_paths": sample(debug),
            "next_action": (
                "Bind debug/LDAB signals to an executable diagnostic receipt."
                if debug
                else "Add minimal debug/LDAB diagnostic surface."
            ),
        },
        "repo_self_assess_runners_mcp": {
            "status": "green" if workflows or runners or mcp else "red",
            "workflow_count": len(workflows),
            "docker_count": len(docker),
            "runner_signal_count": len(runners),
            "mcp_orchestration_signal_count": len(mcp),
            "sample_paths": sample(workflows + docker + runners + mcp),
            "next_action": "Separate executable runners from dormant/config-only surfaces.",
        },
        "repo_self_assess_codz_health_selfheal": {
            "status": "amber" if todo_hits or selfheal else "red",
            "todo_like_file_count": todo_hits,
            "selfheal_signal_count": len(selfheal),
            "sample_paths": sample(selfheal),
            "next_action": "Recurse on the first observed failing health invariant.",
        },
        "repo_self_produce": {
            "status": self_produce_status,
            "skill_signal_count": len(skills),
            "complete_skill_count": len(complete_skills),
            "complete_skill_paths": sample(complete_skills),
            "agent_orchestration_signal_count": len(mcp),
            "candidate_paths": sample(skills + mcp),
            "next_action": self_produce_next,
        },
    }


def build_receipt() -> dict:
    files = iter_files()
    extensions = Counter(p.suffix.lower() or "<none>" for p in files)
    top_dirs = Counter(
        p.parts[0] if len(p.parts) > 1 else "<root>" for p in files
    )
    status_short = run_git(["status", "--short"]) or ""

    return {
        "schema_version": "0.1",
        "program": "MIP",
        "repo": {
            "root": str(ROOT),
            "remote": run_git(["remote", "get-url", "origin"]),
            "branch": run_git(["branch", "--show-current"])
            or run_git(["rev-parse", "--abbrev-ref", "HEAD"]),
            "sha": run_git(["rev-parse", "HEAD"]),
            "dirty_file_count": len(
                [line for line in status_short.splitlines() if line.strip()]
            ),
            "dirty_summary": status_short.splitlines()[:50],
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "census": {
            "file_count": len(files),
            "extension_counts": dict(extensions.most_common(30)),
            "top_directory_counts": dict(top_dirs.most_common(30)),
        },
        "assessments": classify(files),
        "next_victory_condition": (
            "Run the receipt on two more distinct SHAs, then package and execute "
            "the highest-confidence repo_self_produce candidate."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate MIP repo self-index receipt."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    receipt = build_receipt()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    try:
        output_display = args.output.relative_to(ROOT)
    except ValueError:
        output_display = args.output
    print(f"Wrote {output_display}")
    print(
        json.dumps(
            {
                "sha": receipt["repo"]["sha"],
                "files": receipt["census"]["file_count"],
                "dirty": receipt["repo"]["dirty_file_count"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
