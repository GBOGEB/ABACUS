"""Compatibility surface for the canonical DMAIC V3 configuration.

The authoritative implementation lives in :mod:`DMAIC_V3.config`.  This
module intentionally contains no independent configuration defaults or
business logic; keeping a thin import shim prevents the historical
``src/dmaic`` package from drifting into a second runtime implementation.
"""

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
    load_config,
)

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
]
