"""Static regression tests for interpreter-specific Matplotlib requirements.

Native dependency installs across all supported CI lanes remain the source
of truth. These tests cannot establish wheel availability or security.
"""

import re
import unittest
from pathlib import Path

REQUIREMENTS = Path(__file__).resolve().parents[1] / "DMAIC_V3" / "requirements.txt"


def matplotlib_lines(text):
    """Select active Matplotlib requirements, ignoring comments."""
    return [
        line.strip()
        for line in text.splitlines()
        if re.match(r"^matplotlib[<>=!]", line.strip())
    ]


def pytest_asyncio_lines(text):
    """Select active pytest-asyncio requirements, ignoring comments."""
    return [
        line.strip()
        for line in text.splitlines()
        if re.match(r"^pytest-asyncio[<>=!]", line.strip())
    ]


def pylint_lines(text):
    """Select active Pylint requirements, ignoring comments."""
    return [
        line.strip()
        for line in text.splitlines()
        if re.match(r"^pylint[<>=!]", line.strip())
    ]


def classify(lines, minor):
    """Apply fail-closed Python-version markers for a minor version."""
    matches = []
    for line in lines:
        dependency, separator, marker = line.partition(";")
        if not separator:
            matches.append(dependency.strip())
            continue
        applies = True
        for clause in marker.strip().split(" and "):
            parsed = re.fullmatch(r"python_version (>=|<) '3\.(\d+)'", clause.strip())
            if parsed is None:
                raise ValueError("unsupported Python marker")
            bound = int(parsed.group(2))
            if parsed.group(1) == "<":
                applies = applies and minor < bound
            else:
                applies = applies and minor >= bound
        if applies:
            matches.append(dependency.strip())
    return matches


class MatplotlibCompatibilityRegression(unittest.TestCase):
    """Reject regressions across Python 3.8 to 3.12 markers."""

    def test_one_explicit_requirement_for_each_ci_runtime(self):
        """Select exactly one requirement for each Python lane."""
        lines = matplotlib_lines(REQUIREMENTS.read_text(encoding="utf-8"))
        self.assertEqual(4, len(lines))
        for minor in (8, 9, 10, 11, 12):
            with self.subTest(python=f"3.{minor}"):
                self.assertEqual(1, len(classify(lines, minor)))

    def test_matplotlib_range_by_python_minor(self):
        """Guard each interpreter's Matplotlib compatibility boundary."""
        lines = matplotlib_lines(REQUIREMENTS.read_text(encoding="utf-8"))
        expected = {
            8: "matplotlib>=3.7.5,<3.8.0",
            9: "matplotlib>=3.9.4,<3.10.0",
            10: "matplotlib>=3.10.8,<3.11.0",
            11: "matplotlib>=3.11.2,<4.0.0",
            12: "matplotlib>=3.11.2,<4.0.0",
        }
        for minor, requirement in expected.items():
            with self.subTest(python=f"3.{minor}"):
                self.assertEqual([requirement], classify(lines, minor))

    def test_pytest_asyncio_range_by_python_minor(self):
        """Prevent incompatible pytest-asyncio floors on old CI lanes."""
        lines = pytest_asyncio_lines(REQUIREMENTS.read_text(encoding="utf-8"))
        expected = {
            8: "pytest-asyncio>=0.23.8,<0.24",
            9: "pytest-asyncio>=1.2.0,<1.3",
            10: "pytest-asyncio>=1.4.0,<1.5",
            11: "pytest-asyncio>=1.4.0,<1.5",
            12: "pytest-asyncio>=1.4.0,<1.5",
        }
        self.assertEqual(3, len(lines))
        for minor, requirement in expected.items():
            with self.subTest(python=f"3.{minor}"):
                self.assertEqual([requirement], classify(lines, minor))
        self.assertNotIn("pytest-asyncio>=1.4.0,<1.5", lines)

    def test_pylint_range_by_python_minor(self):
        """Guard interpreter requirements against incompatible Pylint floors."""
        lines = pylint_lines(REQUIREMENTS.read_text(encoding="utf-8"))
        expected = {
            8: "pylint>=3.2.6,<3.3.0",
            9: "pylint>=3.3.9,<4.0.0",
            10: "pylint>=4.1.3,<5.0.0",
            11: "pylint>=4.1.3,<5.0.0",
            12: "pylint>=4.1.3,<5.0.0",
        }
        self.assertEqual(3, len(lines))
        for minor, requirement in expected.items():
            with self.subTest(python=f"3.{minor}"):
                self.assertEqual([requirement], classify(lines, minor))
        self.assertNotIn("pylint>=4.1.3,<5.0.0", lines)

    def test_negative_control_rejects_unconditional_regression(self):
        """Keep the pre-repair unconditional pin absent from source."""
        bad = ["matplotlib>=3.11.2,<4.0.0"]
        for minor in (8, 9, 10):
            self.assertEqual(bad, classify(bad, minor))
        self.assertNotIn(
            "matplotlib>=3.11.2,<4.0.0",
            matplotlib_lines(REQUIREMENTS.read_text(encoding="utf-8")),
        )

    def test_negative_control_detects_duplicate_active_pin(self):
        """A malformed extra pin must break the one-active-pin invariant."""
        lines = matplotlib_lines(REQUIREMENTS.read_text(encoding="utf-8"))
        duplicated = lines + ["matplotlib>=3.11.2,<4.0.0"]
        for minor in (10, 11, 12):
            with self.subTest(python=f"3.{minor}"):
                self.assertNotEqual(1, len(classify(duplicated, minor)))

    def test_reverse_boundary_marker_mutation_changes_lane_selection(self):
        """An inverted boundary must not silently match the canonical lanes."""
        lines = matplotlib_lines(REQUIREMENTS.read_text(encoding="utf-8"))
        altered = [
            line.replace("python_version >= '3.11'", "python_version < '3.11'")
            for line in lines
        ]
        self.assertNotEqual(1, len(classify(altered, 10)))
        self.assertEqual([], classify(altered, 11))

    def test_unrecognized_version_marker_fails_closed(self):
        """Do not mistake an unknown marker for a positive match."""
        with self.assertRaisesRegex(ValueError, "unsupported Python marker"):
            classify(["matplotlib>=3.11; platform_system == 'Linux'"], 11)


if __name__ == "__main__":
    unittest.main()
