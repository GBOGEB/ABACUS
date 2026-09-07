#!/usr/bin/env python3
"""W64 total repository census P1 scanner.

This scanner is intentionally conservative. It enumerates tracked files from the
current checkout and assigns each file a category plus an initial evidence-based
classification. It does not delete, migrate, or promote any asset.

Usage:
    python tools/w64_total_repo_census.py --root . --out architecture/w64/receipts/W64_TOTAL_REPO_CENSUS_P1.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Iterable

GENERATED_DIR_HINTS = (
    "dist/",
    "build/",
    "exports/",
    "generated/",
    "__pycache__/",
    ".pytest_cache/",
)

DORMANT_HINTS = (
    "archive/",
    "legacy/",
    "old/",
    "deprecated/",
    "stale/",
    "abacus-v0",
    "abacus-v1",
    "abacus-v2",
    "abacus-v3",
)

BINARY_SUFFIXES = {".xlsx", ".xlsm", ".pptx", ".pdf", ".png", ".jpg", ".jpeg", ".zip", ".tar", ".gz"}
SCHEMA_SUFFIXES = {".json", ".yaml", ".yml", ".toml"}
SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".sh", ".ps1"}
DOC_SUFFIXES = {".md", ".rst", ".txt"}


def tracked_files(root: Path) -> list[Path]:
    """Return git-tracked files relative to root, falling back to a safe walk."""
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=root,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return [Path(line) for line in result.stdout.splitlines() if line.strip()]
    except (OSError, subprocess.CalledProcessError):
        files: list[Path] = []
        for path in root.rglob("*"):
            if path.is_file() and ".git" not in path.parts:
                files.append(path.relative_to(root))
        return sorted(files)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def category_for(path: Path) -> str:
    text = path.as_posix().lower()
    suffix = path.suffix.lower()
    if text.startswith(".github/workflows/"):
        return "workflow"
    if "/ssot/" in f"/{text}" or text.startswith("ssot/"):
        return "ssot"
    if suffix in BINARY_SUFFIXES:
        return "binary_or_rendered_output"
    if suffix in SOURCE_SUFFIXES:
        return "source_or_script"
    if suffix in SCHEMA_SUFFIXES:
        return "schema_or_config"
    if suffix in DOC_SUFFIXES:
        return "documentation"
    return "other"


def classification_for(path: Path, category: str) -> str:
    text = path.as_posix().lower()
    if any(hint in text for hint in GENERATED_DIR_HINTS):
        return "generated"
    if any(hint in text for hint in DORMANT_HINTS):
        return "dormant"
    if category in {"source_or_script", "workflow", "ssot", "schema_or_config"}:
        return "active_candidate"
    if category == "binary_or_rendered_output":
        return "requires_lineage"
    return "unknown"


def duplicate_key(path: Path) -> str:
    stem = path.stem.lower()
    for token in ("_copy", "-copy", " copy", "_old", "-old", "_backup", "-backup"):
        stem = stem.replace(token, "")
    return stem


def build_census(root: Path) -> dict[str, object]:
    files = tracked_files(root)
    assets: list[dict[str, object]] = []
    duplicate_counter: Counter[str] = Counter()

    for rel in files:
        category = category_for(rel)
        classification = classification_for(rel, category)
        duplicate_counter[duplicate_key(rel)] += 1
        full = root / rel
        assets.append(
            {
                "path": rel.as_posix(),
                "category": category,
                "classification": classification,
                "sha256": sha256_file(full) if full.exists() and full.is_file() else None,
                "evidence_basis": "git_tracked_path_and_suffix_heuristic",
            }
        )

    for asset in assets:
        if duplicate_counter[duplicate_key(Path(str(asset["path"]))) ] > 1 and asset["classification"] not in {"generated", "dormant"}:
            asset["duplicate_family_candidate"] = duplicate_key(Path(str(asset["path"])))

    by_category = Counter(str(asset["category"]) for asset in assets)
    by_classification = Counter(str(asset["classification"]) for asset in assets)
    duplicate_families = sorted(k for k, v in duplicate_counter.items() if v > 1)

    return {
        "schema_version": "W64-CENSUS-P1-1.0.0",
        "purpose": "Executable P1 repository census; no migration or release credit.",
        "asset_count": len(assets),
        "by_category": dict(sorted(by_category.items())),
        "by_classification": dict(sorted(by_classification.items())),
        "duplicate_family_candidate_count": len(duplicate_families),
        "duplicate_family_candidates": duplicate_families[:250],
        "assets": assets,
        "non_claims": [
            "Does not delete or migrate assets.",
            "Does not promote generated outputs to authority.",
            "Does not claim W64 DoV; P2 reverse-pressure and P3 receipt remain required.",
        ],
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)

    root = Path(args.root).resolve()
    out = Path(args.out)
    if not out.is_absolute():
        out = root / out
    out.parent.mkdir(parents=True, exist_ok=True)
    census = build_census(root)
    out.write_text(json.dumps(census, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"asset_count": census["asset_count"], "out": str(out)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
