"""Fail-closed PyGithub dependency marker regression across native matrix lanes.

This proves marker selection only. Native pip resolution and functional test
results are independent admission evidence.
"""

from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import Requirement

REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements.txt"
PYTHON_LANES = ("3.9", "3.10", "3.11", "3.12")


def _pygithub_requirements():
    lines = [
        line.strip()
        for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines()
        if line.strip().lower().startswith("pygithub")
    ]
    assert len(lines) == 2, "exactly two disjoint PyGithub constraint owners"
    requirements = [Requirement(line) for line in lines]
    assert all(
        r.name.lower() == "pygithub" and r.marker is not None and r.url is None
        for r in requirements
    )
    return requirements


def test_each_supported_python_lane_selects_one_compatible_constraint():
    constraints = _pygithub_requirements()
    for lane in PYTHON_LANES:
        environment = default_environment()
        environment["python_version"] = lane
        environment["python_full_version"] = lane + ".0"
        selected = [
            r for r in constraints if r.marker.evaluate(environment=environment)
        ]
        assert len(selected) == 1, (lane, [str(r) for r in selected])
        version = selected[0].specifier
        if lane == "3.9":
            assert version.contains("2.9.1")
            assert not version.contains("2.10.0")
            assert not version.contains("3.0.0")
        else:
            assert version.contains("2.10.0")
            assert not version.contains("2.9.1")
            assert not version.contains("3.0.0")


def test_constraints_deny_unmarked_or_unbounded_pygithub():
    constraints = _pygithub_requirements()
    assert all(str(r.specifier) and r.marker is not None for r in constraints)
