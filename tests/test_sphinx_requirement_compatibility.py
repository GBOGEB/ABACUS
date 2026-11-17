"""Regression contract for Sphinx markers across supported Python cohorts.

This static marker test is not a substitute for native pip resolution.
"""

import unittest
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import Requirement

REQUIREMENTS = Path(__file__).resolve().parents[1] / "DMAIC_V3" / "requirements.txt"


def active_sphinx_for(version: str, text: str):
    """Evaluate only active Sphinx requirements, excluding sphinx-* packages."""
    parsed = [
        Requirement(line.split(" #", 1)[0].strip())
        for line in text.splitlines()
        if line.lstrip().startswith("sphinx>") or line.lstrip().startswith("sphinx=")
    ]
    env = default_environment()
    env["python_version"] = version
    return [r for r in parsed if r.marker is None or r.marker.evaluate(environment=env)]


class SphinxMarkerCompatibility(unittest.TestCase):
    def test_one_exclusive_sphinx_requirement_per_python_lane(self):
        text = REQUIREMENTS.read_text(encoding="utf-8")
        expected = {
            "3.9": ("7.4.7", "8.0.0"),
            "3.10": ("8.1.0", "9.0.0"),
            "3.11": ("8.1.0", "9.0.0"),
            "3.12": ("9.1.1", "9.2.0"),
            "3.13": ("9.2.0", "10.0.0"),
        }
        for python, (accepted, rejected) in expected.items():
            with self.subTest(python=python):
                active = active_sphinx_for(python, text)
                self.assertEqual(len(active), 1, f"{python} has {active!r}")
                self.assertTrue(active[0].specifier.contains(accepted), python)
                self.assertFalse(active[0].specifier.contains(rejected), python)

    def test_py312_9_2_floor_regression_is_rejected(self):
        text = REQUIREMENTS.read_text(encoding="utf-8")
        broken = text.replace(
            "sphinx>=9.1.1,<9.2.0; python_version >= '3.12' and python_version < '3.13'",
            "sphinx>=9.2.0,<10.0.0; python_version >= '3.12' and python_version < '3.13'",
        )
        self.assertNotEqual(
            broken, text, "negative-control fixture did not mutate policy"
        )
        active = active_sphinx_for("3.12", broken)
        self.assertEqual(len(active), 1)
        self.assertFalse(active[0].specifier.contains("9.1.1"))


if __name__ == "__main__":
    unittest.main()
