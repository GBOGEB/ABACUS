"""Load a production module by repository-relative path for lane A tests.

Many modules under top-level directories are scripts, not packages (their
directory names contain dashes or version dots). Loading by path keeps the
production files untouched and gives each module a unique import name.
"""

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def load(relpath, name=None, extra_paths=()):
    """Import ``relpath`` (relative to the repo root) and return the module.

    The module's own directory and any ``extra_paths`` are put on
    ``sys.path`` so sibling imports inside the module resolve.
    """
    path = REPO / relpath
    name = name or "l1_" + relpath.replace("/", "_").replace("-", "_").replace(".", "_")
    for extra in (path.parent, *[REPO / p for p in extra_paths]):
        if str(extra) not in sys.path:
            sys.path.insert(0, str(extra))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
