"""Native repository test-collection bridge for exact-run/attempt telemetry."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SOURCE = (
    Path(__file__).resolve().parents[1]
    / "MIP/G3CS_CONVERGENCE_V2/tests/test_compare_snapshots.py"
)
if not _SOURCE.is_file():
    raise RuntimeError("Missing G3C-S telemetry regression module: fail closed")
_spec = importlib.util.spec_from_file_location(
    "g3cs_native_snapshot_contracts", _SOURCE
)
_suite = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_suite)


class TestG3CSNativeSnapshotComparator(_suite.NativeComparatorTests):
    """Ensure 11 comparability/first-red/queue cases run in ABACUS CI."""
