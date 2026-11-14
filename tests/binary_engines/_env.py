"""Shared environment for the binary-engine tests.

Import this module before any engine module: the engines read ESTATE_HOME and ESTATE_CONFIG once, at import.

* ESTATE_HOME is a fresh folder outside the repository (``<base>/home``); ``<base>`` is the MI root of the neutral
  example configuration, so tests place root files there. BINARY_ENGINES_TEST_HOME keeps ``<base>`` for a later
  workflow step (the PowerShell dry run); otherwise it is a temporary folder removed at exit.
* ESTATE_CONFIG is ``estate_config.example.yaml``: the tests never read a private configuration.
* Missing third-party modules or gg_MATH kernels skip a test locally. With BINARY_ENGINES_REQUIRE_DEPS=1 (the
  dedicated workflow) they fail instead, so the CI run can never pass on skipped tests.
"""

from __future__ import annotations

import atexit
import contextlib
import importlib
import importlib.util
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CODE = REPO / "DMAIC_V3" / "binary_engines"
EXAMPLE_CONFIG = CODE / "estate_config.example.yaml"
REQUIRE = os.environ.get("BINARY_ENGINES_REQUIRE_DEPS") == "1"

_keep = os.environ.get("BINARY_ENGINES_TEST_HOME")
if _keep:
    BASE = Path(_keep).resolve()
    BASE.mkdir(parents=True, exist_ok=True)
else:
    BASE = Path(tempfile.mkdtemp(prefix="binary_engines_")).resolve()
    atexit.register(shutil.rmtree, BASE, ignore_errors=True)
HOME = BASE / "home"
os.environ["ESTATE_HOME"] = str(HOME)
os.environ["ESTATE_CONFIG"] = str(EXAMPLE_CONFIG)
os.environ.pop("ESTATE_LEGEND_REGISTRY", None)
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

DEPS = ("yaml", "lxml", "docx", "pptx", "openpyxl", "fitz", "PIL")


def _gate(message: str) -> None:
    if REQUIRE:
        raise AssertionError(message + " (BINARY_ENGINES_REQUIRE_DEPS=1)")
    raise unittest.SkipTest(message)


def require(*modules: str) -> None:
    """Skip, or fail under BINARY_ENGINES_REQUIRE_DEPS=1, when a third-party module is missing."""
    missing = [m for m in modules if importlib.util.find_spec(m) is None]
    if missing:
        _gate(
            f"missing {', '.join(missing)}: pip install -r requirements-binary-engines.txt"
        )


def require_kernels() -> None:
    """Skip, or fail, when the pinned gg_MATH kernels are not reachable (GG_MATH_HOME or the cache)."""
    require("yaml")
    import ggmath_bridge

    for name in ggmath_bridge.PINS:
        try:
            ggmath_bridge.kernel_bytes(name)
        except ggmath_bridge.KernelPinError as exc:
            _gate(str(exc))


def engine(name: str):
    """Import an engine module by name (they are scripts in CODE that import each other by bare name)."""
    return importlib.import_module(name)


def run_main(module_name: str, *args: str) -> tuple[int, str]:
    """Run an engine's main() in this process with the given arguments; returns (exit code, stdout)."""
    module = engine(module_name)
    out = io.StringIO()
    old = sys.argv
    sys.argv = [f"{module_name}.py", *args]
    try:
        with contextlib.redirect_stdout(out):
            try:
                code = module.main()
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 1
    finally:
        sys.argv = old
    return int(code or 0), out.getvalue()
