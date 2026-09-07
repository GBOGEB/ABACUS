"""Manifest-backed SSOT authority resolver.

The YAML manifest remains the human-maintained authority map. ``ssot/index.json`` is
its normalized runtime view. Resolution fails closed when a logical ID is absent or
has more than one authority candidate.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class AuthorityResolutionError(RuntimeError):
    pass


def load_index(root: Path) -> dict[str, Any]:
    path = Path(root) / "ssot" / "index.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("source") != "ssot/manifest.yaml":
        raise AuthorityResolutionError("SSOT index is not bound to ssot/manifest.yaml")
    authorities = data.get("authorities")
    if not isinstance(authorities, list):
        raise AuthorityResolutionError("SSOT index authorities must be a list")
    return data


def duplicate_authorities(index: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in index.get("authorities", []):
        logical_id = entry.get("logical_id")
        if not logical_id:
            raise AuthorityResolutionError("authority entry missing logical_id")
        grouped.setdefault(logical_id, []).append(entry)
    return {logical_id: entries for logical_id, entries in grouped.items() if len(entries) > 1}


def validate_index(index: dict[str, Any]) -> None:
    duplicates = duplicate_authorities(index)
    if duplicates:
        raise AuthorityResolutionError(
            "competing SSOT authorities: " + ", ".join(sorted(duplicates))
        )


def resolve_ssot(root: Path, logical_id: str) -> Path:
    index = load_index(root)
    validate_index(index)
    matches = [e for e in index["authorities"] if e["logical_id"] == logical_id]
    if len(matches) != 1:
        raise AuthorityResolutionError(
            f"expected exactly one authority for {logical_id}, found {len(matches)}"
        )
    path = Path(root) / matches[0]["path"]
    if not path.exists():
        raise AuthorityResolutionError(f"authority path does not exist: {matches[0]['path']}")
    return path
