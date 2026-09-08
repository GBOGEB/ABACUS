"""ABACUS product-version access.

The source-tree release version is authoritative in the root ``pyproject.toml``.
Installed wheels obtain the same version from package metadata because the root
project file is intentionally not present inside ``site-packages``.
DMAIC_V3 keeps its independent engine-generation/API version.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
import tomllib


PACKAGE_DISTRIBUTION = "abacus-dow"


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def get_product_version() -> str:
    project_file = _root() / "pyproject.toml"
    if project_file.is_file():
        data = tomllib.loads(project_file.read_text(encoding="utf-8"))
        value = data.get("project", {}).get("version")
        if isinstance(value, str) and value.strip():
            return value
        raise RuntimeError("pyproject.toml [project].version is missing")

    try:
        value = package_version(PACKAGE_DISTRIBUTION)
    except PackageNotFoundError as exc:
        raise RuntimeError(
            "ABACUS product version unavailable from source or installed metadata"
        ) from exc
    if not value.strip():
        raise RuntimeError("installed ABACUS package version is empty")
    return value


ABACUS_VERSION = get_product_version()

__all__ = ["ABACUS_VERSION", "get_product_version"]
