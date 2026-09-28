"""Compatibility surface for the canonical DMAIC V3 configuration.

The authoritative implementation lives in DMAIC_V3.config. This module
intentionally contains no independent runtime configuration logic. It preserves
the historical src.dmaic.config mapping API while adapting canonical DMAIC V3
configuration objects for legacy callers.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from DMAIC_V3.config import (  # noqa: F401
    CORE_PRINCIPLES,
    DEFAULT_CONFIG,
    VERSION,
    DMAICConfig,
    ExecutionMode,
    IdempotencyConfig,
    KnowledgeConfig,
    LoggingConfig,
    MetricsConfig,
    PathConfig,
    Phase0Config,
    PhaseConfig,
    get_development_config,
    get_production_config,
    get_testing_config,
    load_config as _canonical_load_config,
)

_LEGACY_CONVERGENCE_THRESHOLD = 0.01
_LEGACY_PHASE_NAMES = {
    1: "phase1_define",
    2: "phase2_measure",
    3: "phase3_analyze",
    4: "phase4_improve",
    5: "phase5_control",
}


def _legacy_mapping(config: DMAICConfig) -> Dict[str, Any]:
    """Adapt canonical configuration to the historical mapping contract."""
    return {
        "workspace_root": config.workspace_root,
        "output_root": str(config.paths.output_root),
        "max_iterations": config.max_iterations,
        "convergence_threshold": _LEGACY_CONVERGENCE_THRESHOLD,
        "phases": {
            name: {"enabled": config.get_phase_config(number).enabled}
            for number, name in _LEGACY_PHASE_NAMES.items()
        },
    }


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load canonical defaults and return the historical mapping contract.

    Legacy callers expect a dictionary and may use subscription or get().
    Unknown legacy JSON keys are preserved by overlaying the raw mapping after
    canonical loading. Invalid or unreadable files retain fail-soft defaults.
    """
    path = Path(config_path) if config_path is not None else None

    try:
        canonical = _canonical_load_config(path)
    except (json.JSONDecodeError, IOError, OSError):
        canonical = _canonical_load_config()

    legacy = _legacy_mapping(canonical)

    if path is not None and path.exists():
        try:
            with path.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
            if isinstance(raw, dict):
                legacy.update(raw)
        except (json.JSONDecodeError, IOError, OSError):
            pass

    return legacy


def save_config(config: Dict[str, Any], config_path: Path) -> None:
    """Persist the historical mapping contract as JSON."""
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)


__all__ = [
    "CORE_PRINCIPLES",
    "DEFAULT_CONFIG",
    "VERSION",
    "DMAICConfig",
    "ExecutionMode",
    "IdempotencyConfig",
    "KnowledgeConfig",
    "LoggingConfig",
    "MetricsConfig",
    "PathConfig",
    "Phase0Config",
    "PhaseConfig",
    "get_development_config",
    "get_production_config",
    "get_testing_config",
    "load_config",
    "save_config",
]
