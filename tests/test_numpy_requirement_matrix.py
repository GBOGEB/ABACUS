"""Guard the per-Python NumPy requirement lanes restored by #1610.

Dependabot #1606 raised every NumPy floor to 2.5.3, which requires
Python >= 3.12, and broke the 3.10/3.11 install lanes. #1610 restored one
NumPy line per Python lane but added no regression test; this module is
that guard. It checks structure rather than exact pins so routine,
compatible bumps inside a lane still pass.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "DMAIC_V3" / "requirements.txt"
GENERATORS = ROOT / "DMAIC_V3" / "generators" / "requirements.txt"

EXPECTED_MARKERS = [
    "python_version < '3.9'",
    "python_version >= '3.9' and python_version < '3.10'",
    "python_version >= '3.10' and python_version < '3.11'",
    "python_version >= '3.11' and python_version < '3.12'",
    "python_version >= '3.12'",
]

# Minimum Python required by each NumPy feature release (Requires-Python).
NUMPY_MIN_PYTHON = {
    (1, 24): (3, 8),
    (1, 25): (3, 9),
    (1, 26): (3, 9),
    (2, 0): (3, 9),
    (2, 1): (3, 10),
    (2, 2): (3, 10),
    (2, 3): (3, 11),
    (2, 4): (3, 11),
    (2, 5): (3, 12),
}

LINE_RE = re.compile(
    r"^numpy>=(?P<floor>[\d.]+)(?:,<(?P<upper>[\d.]+))?;\s*(?P<marker>.+)$"
)


def _version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


def _numpy_lanes(path: Path) -> list[dict]:
    lanes = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("numpy>="):
            continue
        match = LINE_RE.match(line)
        assert match, f"unparseable NumPy requirement in {path.name}: {line}"
        lanes.append(match.groupdict())
    return lanes


def _lane_min_python(marker: str) -> tuple[int, int] | None:
    match = re.search(r"python_version >= '(\d+)\.(\d+)'", marker)
    return (int(match.group(1)), int(match.group(2))) if match else None


def test_canonical_and_generator_lanes_share_markers_and_floors():
    canonical = _numpy_lanes(CANONICAL)
    generators = _numpy_lanes(GENERATORS)

    assert [lane["marker"] for lane in canonical] == EXPECTED_MARKERS
    assert [lane["marker"] for lane in generators] == EXPECTED_MARKERS
    assert [lane["floor"] for lane in canonical] == [
        lane["floor"] for lane in generators
    ]


def test_canonical_lanes_are_capped_below_numpy_3():
    for lane in _numpy_lanes(CANONICAL):
        assert lane["upper"], f"uncapped NumPy lane: {lane['marker']}"
        assert _version(lane["floor"]) < _version(lane["upper"])
        assert _version(lane["upper"]) <= (3, 0, 0)


def test_no_lane_floor_requires_a_newer_python_than_the_lane():
    for lane in _numpy_lanes(CANONICAL):
        lane_min = _lane_min_python(lane["marker"])
        if lane_min is None:
            continue
        feature = _version(lane["floor"])[:2]
        if lane_min >= (3, 12) and feature not in NUMPY_MIN_PYTHON:
            # Newest lane: a newer NumPy feature release is acceptable.
            continue
        assert feature in NUMPY_MIN_PYTHON, (
            f"unknown NumPy {lane['floor']} in bounded lane "
            f"{lane['marker']}; add its Requires-Python to NUMPY_MIN_PYTHON"
        )
        assert NUMPY_MIN_PYTHON[feature] <= lane_min, (
            f"NumPy {lane['floor']} needs Python "
            f"{NUMPY_MIN_PYTHON[feature]}, lane is {lane['marker']}"
        )


def test_numpy_25_is_only_selected_for_python_312_and_newer():
    for lane in _numpy_lanes(CANONICAL):
        lane_min = _lane_min_python(lane["marker"]) or (0, 0)
        if lane_min >= (3, 12):
            continue
        assert _version(lane["floor"])[:2] < (2, 5), lane
        assert _version(lane["upper"]) <= (2, 5, 0), lane
