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


def _project_min_python() -> tuple[int, int]:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^requires-python\s*=\s*">=\s*(\d+)\.(\d+)', text, re.MULTILINE)
    assert match, "pyproject.toml must declare requires-python >= X.Y"
    return int(match.group(1)), int(match.group(2))


def _lane_min_python(marker: str) -> tuple[int, int]:
    """Lowest Python a lane serves.

    An explicit ``>=`` bound wins. A lane with only an upper bound starts at
    the project floor (``requires-python``). If the project floor is already
    above the lane, as for the legacy ``< '3.9'`` lane while
    ``requires-python`` is ``>=3.11``, the lane serves only interpreters below
    the floor, so take its newest one (upper bound minus one minor). The floor
    must then install on at least that interpreter. The check is never
    skipped.
    """
    lower = re.search(r"python_version >= '(\d+)\.(\d+)'", marker)
    if lower:
        return int(lower.group(1)), int(lower.group(2))
    upper = re.search(r"python_version < '(\d+)\.(\d+)'", marker)
    assert upper, f"lane marker has no Python bound: {marker}"
    upper_bound = (int(upper.group(1)), int(upper.group(2)))
    floor = _project_min_python()
    if floor < upper_bound:
        return floor
    return upper_bound[0], upper_bound[1] - 1


def _lane_floor_violations(lanes: list[dict]) -> list[str]:
    errors = []
    for lane in lanes:
        lane_min = _lane_min_python(lane["marker"])
        feature = _version(lane["floor"])[:2]
        if lane_min >= (3, 12) and feature not in NUMPY_MIN_PYTHON:
            # Newest lane: a newer NumPy feature release is acceptable.
            continue
        if feature not in NUMPY_MIN_PYTHON:
            errors.append(
                f"unknown NumPy {lane['floor']} in bounded lane "
                f"{lane['marker']}; add its Requires-Python to NUMPY_MIN_PYTHON"
            )
        elif NUMPY_MIN_PYTHON[feature] > lane_min:
            errors.append(
                f"NumPy {lane['floor']} needs Python "
                f"{NUMPY_MIN_PYTHON[feature]}, lane is {lane['marker']}"
            )
    return errors


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
    assert _lane_floor_violations(_numpy_lanes(CANONICAL)) == []


def test_every_lane_resolves_a_lowest_python():
    resolved = [_lane_min_python(marker) for marker in EXPECTED_MARKERS]
    assert resolved == [(3, 8), (3, 9), (3, 10), (3, 11), (3, 12)]


def test_legacy_lane_rejects_floor_needing_newer_python():
    lanes = _numpy_lanes(CANONICAL)
    lanes[0] = {**lanes[0], "floor": "2.0.2", "upper": "2.1.0"}
    errors = _lane_floor_violations(lanes)
    assert errors == ["NumPy 2.0.2 needs Python (3, 9), lane is python_version < '3.9'"]


def test_numpy_25_is_only_selected_for_python_312_and_newer():
    for lane in _numpy_lanes(CANONICAL):
        lane_min = _lane_min_python(lane["marker"])
        if lane_min >= (3, 12):
            continue
        assert _version(lane["floor"])[:2] < (2, 5), lane
        assert _version(lane["upper"]) <= (2, 5, 0), lane
