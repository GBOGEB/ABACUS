#!/usr/bin/env python3
"""Census files that are not visibly linked to a governing anchor.

The scanner is intentionally path-first and dependency-free.  It does not
claim semantic orphan status; it produces a conservative triage queue for the
next evidence-linking pulse.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

ENGINE_RE = re.compile(
    r"(engine|orchestrator|pipeline|runner|agent|mcp|dmaic|sprint|"
    r"federation|bridge|runtime|health|census|selector|burndown|pca|"
    r"manifest|ssot|trace|lineage|workflow|deploy|integration)",
    re.IGNORECASE,
)
DEFAULT_EXCLUDES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
}


def iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(root).parts
        if any(part in DEFAULT_EXCLUDES for part in rel_parts):
            continue
        yield path.relative_to(root)


def linked_by_path(path: str, anchor: str) -> bool:
    lower = path.lower()
    anchor = anchor.lower()
    return (
        anchor in lower
        or lower.startswith("triage/")
        or lower.startswith("federation/")
        or lower.startswith("architecture/")
        or lower.startswith("contracts/")
    )


def classify_path(path: str) -> str:
    lower = path.lower()
    if "workflows-pending/" in lower or "workflows-to-install/" in lower:
        return "staged_workflow"
    if re.search(r"(^|/)(dmaic_v3|abacus-unified|abacus-v[0-9]|tools_v|tracking_v)(/|$)", lower):
        return "embedded_version_or_subrepo"
    if re.search(r"(^|/)(local_mcp|agents|runtime|engine_dow|src/keb)(/|$)", lower):
        return "runtime_agent_surface"
    if re.search(r"(handover|complete|status|deployment|integration|quick|report|plan)", lower):
        return "legacy_status_or_handover"
    return "engine_like_unlinked"


def build_report(root: Path, repo: str, anchor: str) -> dict:
    files = sorted(str(path) for path in iter_files(root))
    anchor_named = [path for path in files if anchor.lower() in path.lower()]
    engine_like = [path for path in files if ENGINE_RE.search(path)]
    linked_engine_like = [path for path in engine_like if linked_by_path(path, anchor)]
    floating = [path for path in engine_like if path not in set(linked_engine_like)]

    buckets: dict[str, list[str]] = {}
    for path in floating:
        buckets.setdefault(classify_path(path), []).append(path)

    roots: dict[str, int] = {}
    for path in files:
        roots[path.split("/", 1)[0]] = roots.get(path.split("/", 1)[0], 0) + 1

    return {
        "schema": "gbo.floating-anchor-census/1.0",
        "repo": repo,
        "anchor": anchor.upper(),
        "method": "path-first conservative census; requires follow-up semantic linking before disposition",
        "totals": {
            "files": len(files),
            "anchor_named_files": len(anchor_named),
            "engine_like_files": len(engine_like),
            "linked_engine_like_files": len(linked_engine_like),
            "floating_engine_like_files": len(floating),
        },
        "top_roots": sorted(roots.items(), key=lambda item: (-item[1], item[0]))[:20],
        "floating_buckets": {key: {"count": len(value), "examples": value[:40]} for key, value in sorted(buckets.items())},
        "anchor_examples": anchor_named[:60],
        "control": {
            "engineering_credit": False,
            "compliance_credit": False,
            "negotiation_credit": False,
            "next_gate": "review highest-count floating buckets and bind each retained feature to anchor receipt, deprecate list, or subrepo classification",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--anchor", required=True, help="governing anchor such as KEB or DOW")
    parser.add_argument("--out")
    args = parser.parse_args()

    report = build_report(Path(args.root).resolve(), args.repo, args.anchor)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
