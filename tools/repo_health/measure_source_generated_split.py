#!/usr/bin/env python3
"""Measure ABACUS source/generated split from a repository checkout.

This script is intentionally conservative: it classifies files by path and
extension into broad governance categories, emits machine-readable JSON, and
never grants engineering or child-compliance credit.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
}

BINARY_EXTENSIONS = {
    ".7z",
    ".bin",
    ".bmp",
    ".doc",
    ".docx",
    ".gif",
    ".gz",
    ".ico",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".tar",
    ".tif",
    ".tiff",
    ".webp",
    ".xls",
    ".xlsm",
    ".xlsx",
    ".zip",
}

SOURCE_EXTENSIONS = {
    ".bash",
    ".bat",
    ".cmd",
    ".css",
    ".html",
    ".js",
    ".json",
    ".jsx",
    ".mjs",
    ".ps1",
    ".py",
    ".sh",
    ".ts",
    ".tsx",
    ".toml",
    ".yaml",
    ".yml",
}

GENERATED_PATH_MARKERS = (
    "/generated/",
    "/dist/",
    "/build/",
    "/outputs/",
    "/output/",
    "/artifacts/",
    "/reports/",
    "/dashboards/",
    "/coverage/",
    "/htmlcov/",
)

DASHBOARD_MARKERS = (
    "dashboard",
    "metrics",
    "telemetry",
    "monitoring",
)

FIXTURE_MARKERS = (
    "/fixtures/",
    "/fixture/",
    "/testdata/",
    "/test_data/",
    "/samples/",
    "/sample_data/",
)

GOVERNANCE_MARKERS = (
    "/governance/",
    "/controls/",
    "/evidence/",
    "/receipts/",
    "/release/",
)


@dataclass(frozen=True)
class FileRecord:
    path: str
    size: int
    category: str


def iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def classify(path: Path, root: Path) -> str:
    rel = path.relative_to(root).as_posix()
    normalized = f"/{rel.lower()}"
    suffix = path.suffix.lower()

    if suffix in BINARY_EXTENSIONS:
        return "binary_or_office_artifact"
    if any(marker in normalized for marker in GENERATED_PATH_MARKERS):
        return "generated_or_output"
    if any(marker in normalized for marker in FIXTURE_MARKERS):
        return "fixture_or_sample"
    if any(marker in normalized for marker in GOVERNANCE_MARKERS):
        return "governance_control"
    if any(marker in normalized for marker in DASHBOARD_MARKERS):
        return "dashboard_or_metrics"
    if normalized.startswith("/.github/"):
        return "ci_or_repository_control"
    if suffix in SOURCE_EXTENSIONS:
        return "source_or_config"
    return "unclassified_text_or_other"


def measure(root: Path) -> dict:
    records: list[FileRecord] = []
    for file_path in iter_files(root):
        try:
            size = file_path.stat().st_size
        except OSError:
            size = 0
        records.append(FileRecord(file_path.relative_to(root).as_posix(), size, classify(file_path, root)))

    by_category = Counter(record.category for record in records)
    bytes_by_category: defaultdict[str, int] = defaultdict(int)
    examples: defaultdict[str, list[str]] = defaultdict(list)

    for record in records:
        bytes_by_category[record.category] += record.size
        if len(examples[record.category]) < 10:
            examples[record.category].append(record.path)

    return {
        "schema_version": "0.1",
        "document_id": "ABACUS_SOURCE_GENERATED_SPLIT_MEASUREMENT",
        "status": "MEASURED_FROM_LOCAL_CHECKOUT",
        "root": str(root),
        "total_files": len(records),
        "total_bytes": sum(record.size for record in records),
        "file_count_by_category": dict(sorted(by_category.items())),
        "bytes_by_category": dict(sorted(bytes_by_category.items())),
        "examples_by_category": dict(sorted(examples.items())),
        "credit_boundary": {
            "qps_engineering_closure_credit": 0,
            "qps_negotiation_credit": 0,
            "child_compliance_credit": 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="Repository checkout root")
    parser.add_argument("--output", "-o", help="Optional JSON output path")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    result = measure(root)
    payload = json.dumps(result, indent=2, sort_keys=True)

    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
