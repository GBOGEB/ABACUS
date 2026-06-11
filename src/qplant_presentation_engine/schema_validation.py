"""Canonical scientific visualization schema resolution and validation helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_SCHEMA_DIR = REPO_ROOT / "patterns" / "scientific_visualization"


def canonical_schema_paths() -> Dict[str, Path]:
    """Return canonical scientific visualization schema artifact paths."""
    return {
        "schema_yaml": CANONICAL_SCHEMA_DIR / "schema.yaml",
        "schema_json": CANONICAL_SCHEMA_DIR / "schema.json",
        "validation_rules": CANONICAL_SCHEMA_DIR / "validation_rules.yaml",
        "readme": CANONICAL_SCHEMA_DIR / "README.md",
    }


def canonical_schema_path(fmt: str = "yaml") -> Path:
    """Resolve the canonical scientific visualization schema path by format."""
    paths = canonical_schema_paths()
    normalized = fmt.strip().lower()
    if normalized in {"yaml", "yml"}:
        return paths["schema_yaml"]
    if normalized == "json":
        return paths["schema_json"]
    raise ValueError(f"unsupported schema format: {fmt}")


def _load_yaml(path: Path) -> Dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def validate_canonical_schema() -> Dict[str, bool]:
    """Validate canonical schema artifact existence and YAML/JSON consistency."""
    paths = canonical_schema_paths()
    files_present = all(path.exists() for path in paths.values())
    if not files_present:
        return {
            "schema_files_present": False,
            "schema_yaml_json_equivalent": False,
        }

    schema_yaml = _load_yaml(paths["schema_yaml"])
    schema_json = _load_json(paths["schema_json"])
    return {
        "schema_files_present": True,
        "schema_yaml_json_equivalent": schema_yaml == schema_json,
    }
