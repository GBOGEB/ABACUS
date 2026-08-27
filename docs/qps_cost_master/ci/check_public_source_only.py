#!/usr/bin/env python3
"""Fail when the public QPS bridge contains binaries or private offer data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORBIDDEN_EXTENSIONS = {
    ".pptx", ".ppsx", ".xlsx", ".xlsm", ".docx", ".pdf",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".tif", ".tiff",
    ".zip", ".tar", ".gz", ".tgz", ".7z", ".rar", ".bundle",
    ".db", ".sqlite", ".parquet", ".h5", ".hdf5",
}
PRIVATE_MARKERS = [
    "50.79163567", "29.243", "21.54863567",
    "LKT - Offer 1", "ALAT - Offer 1",
]
TEXT_EXTENSIONS = {
    ".md", ".txt", ".json", ".yaml", ".yml", ".py", ".js", ".ts",
    ".html", ".css", ".svg", ".toml", ".ini", ".cfg", ".sh", ".ps1",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = args.root.resolve()
    findings: list[dict[str, object]] = []
    files = [p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]
    for path in files:
        rel = path.relative_to(root).as_posix()
        suffixes = "".join(path.suffixes).lower()
        ext = path.suffix.lower()
        if ext in FORBIDDEN_EXTENSIONS or suffixes.endswith((".tar.gz", ".git.bundle")):
            findings.append({"path": rel, "rule": "forbidden_binary_or_archive"})
            continue
        if path.stat().st_size > 2_000_000:
            findings.append({"path": rel, "rule": "public_source_file_over_2MB", "size_bytes": path.stat().st_size})
        if path.name == "check_public_source_only.py":
            continue
        if ext in TEXT_EXTENSIONS and path.stat().st_size < 2_000_000:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for marker in PRIVATE_MARKERS:
                if marker in text:
                    findings.append({"path": rel, "rule": "private_data_marker", "marker": marker})

    result = {
        "schema": "qps-cost-master.public-source-policy.v1",
        "root": str(root),
        "files_scanned": len(files),
        "passed": not findings,
        "findings": findings,
    }
    payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0 if not findings else 3


if __name__ == "__main__":
    raise SystemExit(main())
