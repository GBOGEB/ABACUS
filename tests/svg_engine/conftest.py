"""Shared fixtures for the SVG-ENGINE tests.

The engine's third-party dependencies are optional for the repository-wide suite: each test module skips
cleanly when they are missing. The dedicated ``svg-engine`` workflow installs them and must run every test.
Set ``SVG_ENGINE_REQUIRE_DEPS=1`` to turn those skips into failures.
"""

from __future__ import annotations

import importlib
import os

import pytest


def require(*modules):
    """Import ``modules`` or skip the calling module. CairoSVG raises OSError when libcairo is missing."""
    import svg_engine._env  # noqa: F401  (honours SVG_ENGINE_DEPS / SVG_ENGINE_CAIRO_BIN on workstations)

    loaded = []
    for name in modules:
        try:
            loaded.append(importlib.import_module(name))
        except (
            ImportError,
            OSError,
        ) as exc:  # pragma: no cover - environment dependent
            if os.environ.get("SVG_ENGINE_REQUIRE_DEPS") == "1":
                raise
            # The state token lets scripts/test_evidence_census.py classify this skip.
            pytest.skip(
                f"TEST_BLOCKED_DEPENDENCY: svg_engine dependency unavailable: {name} ({exc})",
                allow_module_level=True,
            )
    return loaded


@pytest.fixture()
def synthetic_root():
    require("lxml")
    from svg_engine.fixtures import synthetic_layered_svg
    from svg_engine.ingress import parse_svg

    return parse_svg(synthetic_layered_svg())
