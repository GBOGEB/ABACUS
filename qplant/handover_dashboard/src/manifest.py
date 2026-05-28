from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_text_if_changed(path: Path, content: str) -> bool:
    """Idempotent write helper.

    Returns True if file content changed, False otherwise.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def write_json_if_changed(path: Path, payload: Any) -> bool:
    content = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    return write_text_if_changed(path, content + "\n")


def build_output_manifest(
    root: Path,
    files: list[Path],
    source_inputs: list[str],
    classifications: dict[str, dict[str, str]],
    builder_version: str,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for file in sorted(files, key=lambda p: str(p)):
        rel = str(file.relative_to(root))
        stat = file.stat()
        entry = {
            "path": rel,
            "sha256": sha256_file(file),
            "size_bytes": stat.st_size,
            "modified_timestamp": stat.st_mtime,
            "source_inputs": source_inputs,
            "builder_version": builder_version,
        }
        entry.update(classifications.get(rel, {}))
        records.append(entry)

    return {
        "builder_version": builder_version,
        "file_count": len(records),
        "files": records,
    }
