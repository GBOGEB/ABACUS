from __future__ import annotations

import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "w74_paired", Path("tools/w74_paired_pressure.py")
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_ranks_average_ties():
    assert MODULE.ranks([2.0, 1.0, 1.0, 4.0]) == [3.0, 1.5, 1.5, 4.0]


def test_pearson_identity():
    value = MODULE.pearson([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
    assert value is not None
    assert round(value, 6) == 1.0


def test_pearson_constant_withheld():
    assert MODULE.pearson([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]) is None
