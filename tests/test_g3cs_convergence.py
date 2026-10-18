"""Repository-level native pytest/unittest bridge for the G3C-S provider.

The existing pytest.ini searches tests/; the provider retains all source and
negative cases in its own disjoint MIP folder. Do not silently lose them from
CI collection just because the source package is outside tests/.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_SOURCE = (
    Path(__file__).resolve().parents[1]
    / 'MIP/G3CS_CONVERGENCE_V2/tests/test_converge.py'
)
if not _SOURCE.is_file():
    raise RuntimeError('Missing G3CS native test source; do not silently skip')
_spec = importlib.util.spec_from_file_location('g3cs_native_contracts', _SOURCE)
_contracts = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_contracts)


class TestG3CSConvergence(_contracts.ConvergenceContract):
    """Run all provider contracts in the native repository test population."""

