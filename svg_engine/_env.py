"""Optional dependency bootstrap so the engine also runs under ``python -I`` on a workstation.

SVG_ENGINE_DEPS       extra site dir holding CairoSVG (for example a ``pip install --target`` folder)
SVG_ENGINE_CAIRO_BIN  directory holding libcairo-2.dll on Windows (for example Inkscape's ``bin``)

Both are optional; on Linux CI CairoSVG finds the system libcairo.
"""
import os
import sys

_p = os.environ.get("SVG_ENGINE_DEPS")
if _p and _p not in sys.path:
    sys.path.insert(0, _p)
_bin = os.environ.get("SVG_ENGINE_CAIRO_BIN")
if _bin:
    os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + _bin  # appended: never shadow python.exe
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(_bin)
