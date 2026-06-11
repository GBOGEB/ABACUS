"""
QPLANT Configuration Loader — Single Source of Truth (SSoT)

Loads data/config.yaml and provides typed, dot-notation access to all
design parameters.  Every calculation module should import this instead
of hardcoding values.

Usage:
    from src.config_loader import ConfigLoader, cfg
    
    hp_count = cfg.get('compressor_specifications.hp_compressors.count')  # 3
    design_flow = cfg.get('flow_parameters.wcs_hp.design_flow_gs')       # 350
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import yaml


_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_CONFIG = _ROOT / "data" / "config.yaml"


class ConfigLoader:
    """Load and query the project's Single Source of Truth YAML config."""

    def __init__(self, config_path: str | Path | None = None):
        self.path = Path(config_path) if config_path else _DEFAULT_CONFIG
        self.config: dict = self._load_yaml(self.path)

    # ── core ────────────────────────────────────────────────────────
    @staticmethod
    def _load_yaml(path: Path) -> dict:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Retrieve a nested value using dot notation.

        >>> cfg.get('compressor_specifications.hp_compressors.count')
        3
        """
        keys = key_path.split(".")
        node: Any = self.config
        for k in keys:
            if isinstance(node, dict):
                node = node.get(k)
            else:
                return default
            if node is None:
                return default
        return node

    @property
    def version(self) -> str:
        return self.get("version", "0.0.0")

    # ── exports ─────────────────────────────────────────────────────
    def export_json(self, output_path: str | Path | None = None) -> Path:
        """Write config as machine-readable JSON."""
        out = Path(output_path) if output_path else _ROOT / "data" / "config.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, default=str)
        return out

    def export_markdown(self, output_path: str | Path | None = None) -> Path:
        """Write config as human-readable Markdown tables."""
        out = Path(output_path) if output_path else _ROOT / "data" / "config.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f"# QPLANT Configuration — v{self.version}",
            "",
            f"*Auto-generated from `data/config.yaml` — do not edit manually.*",
            "",
        ]
        self._dict_to_md(self.config, lines, depth=0)
        out.write_text("\n".join(lines), encoding="utf-8")
        return out

    # ── helpers ─────────────────────────────────────────────────────
    def _dict_to_md(self, d: dict, lines: list[str], depth: int) -> None:
        """Recursively render dict as Markdown tables / headers."""
        for key, val in d.items():
            if isinstance(val, dict):
                hdr = "#" * min(depth + 2, 6)
                lines.append(f"{hdr} {key.replace('_', ' ').title()}")
                lines.append("")
                # Check if it's a "leaf" dict (no nested dicts)
                if any(isinstance(v, dict) for v in val.values()):
                    self._dict_to_md(val, lines, depth + 1)
                else:
                    lines.append("| Parameter | Value |")
                    lines.append("|-----------|-------|")
                    for k2, v2 in val.items():
                        lines.append(f"| {k2} | {v2} |")
                    lines.append("")
            elif isinstance(val, list):
                lines.append(f"**{key}**: {', '.join(str(v) for v in val)}")
                lines.append("")

    def reload(self) -> None:
        """Re-read the YAML from disk."""
        self.config = self._load_yaml(self.path)

    def __repr__(self) -> str:
        return f"ConfigLoader(version={self.version!r}, path={self.path})"


# ── Module-level singleton ──────────────────────────────────────────
cfg = ConfigLoader()
