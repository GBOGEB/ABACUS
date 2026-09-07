"""ABACUS product-version access.

The product release version is authoritative in the root ``pyproject.toml``.
DMAIC_V3 keeps its independent engine-generation/API version.
"""

from __future__ import annotations

from pathlib import Path
import tomllib


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def get_product_version() -> str:
    data = tomllib.loads((_root() / "pyproject.toml").read_text(encoding="utf-8"))
    version = data.get("project", {}).get("version")
    if not isinstance(version, str) or not version.strip():
        raise RuntimeError("pyproject.toml [project].version is missing")
    return version


ABACUS_VERSION = get_product_version()

__all__ = ["ABACUS_VERSION", "get_product_version"]
