from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

TOOLS = Path("tools").resolve()
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

SPEC = importlib.util.spec_from_file_location(
    "w75_stability", Path("tools/w75_stability_diagnostic.py")
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def stable_rows(field: str = "value") -> list[dict]:
    rows = []
    for repeat in (1, 2, 3):
        for index in range(5):
            rows.append(
                {
                    "source_sha": f"{index:040x}",
                    "repeat": repeat,
                    field: float(index + 1),
                }
            )
    return rows


def test_icc_identical_repeats_is_one():
    value = MODULE.icc_one_way(stable_rows(), "value")
    assert value is not None
    assert round(value, 6) == 1.0


def test_rank_stability_identical_repeats_is_one():
    result = MODULE.pairwise_rank_stability(stable_rows(), "value")
    assert result["median_spearman_rho"] is not None
    assert round(result["median_spearman_rho"], 6) == 1.0


def test_declared_thresholds_are_bounded():
    assert 0.0 < MODULE.ICC_THRESHOLD <= 1.0
    assert 0.0 < MODULE.RANK_THRESHOLD <= 1.0
