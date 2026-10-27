"""Load repository modules by file path for lane-B coverage tests.

Loading by path sidesteps package shadowing (for example an unrelated
``scripts`` distribution in site-packages) and avoids executing heavy package
``__init__`` modules that are not under test.
"""

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def load(rel_path, name=None):
    path = REPO_ROOT / rel_path
    mod_name = name or "l2_" + rel_path.replace("/", "_").replace(".", "_").replace(
        "-", "_"
    )
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module
