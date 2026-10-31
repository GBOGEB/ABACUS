"""Make ``tools/everred_v3`` importable for the acceptance tests.

The ``acceptance`` package documents ``python -m acceptance.cli`` from
``tools/everred_v3``. Under pytest from the repo root that directory is not on
``sys.path``, so five test modules failed collection with
``ModuleNotFoundError: No module named 'acceptance'``.
"""

import sys
from pathlib import Path

EVERRED_ROOT = str(Path(__file__).resolve().parents[1])
if EVERRED_ROOT not in sys.path:
    sys.path.insert(0, EVERRED_ROOT)
