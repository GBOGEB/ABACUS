"""Optional dependency bootstrap so the engine also runs under ``python -I`` on a workstation.

SVG_ENGINE_DEPS       extra site dir holding CairoSVG (for example a ``pip install --target`` folder)
SVG_ENGINE_CAIRO_BIN  directory holding libcairo-2.dll on Windows (for example Inkscape's ``bin``)

Both are optional; on Linux CI CairoSVG finds the system libcairo. ``bootstrap()`` is idempotent and is
called before the heavy dependencies are imported.
"""

import functools
import os
import sys


@functools.cache
def bootstrap():
    """Idempotent: ``functools.cache`` runs the body once per process."""
    deps = os.environ.get("SVG_ENGINE_DEPS")
    if deps and deps not in sys.path:
        sys.path.insert(0, deps)
    cairo_bin = os.environ.get("SVG_ENGINE_CAIRO_BIN")
    if cairo_bin:
        # Appended, never prepended: must not shadow python.exe.
        os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + cairo_bin
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(cairo_bin)
