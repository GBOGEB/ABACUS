"""
DMAIC V3 Test Suite - Maturity Tracker Tests
Version: 3.2.0
Created: 2025-11-12T04:50:00Z
"""

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from DMAIC_V3.convergence.maturity_tracker import (  # noqa: E402
    MaturityAssessment,
    MaturityTracker,
)


class TestMaturityTracker(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self._tmp_dir.name)
        self.tracker = MaturityTracker(self.workspace)

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_initialization(self):
        self.assertIsNotNone(self.tracker)
        self.assertIsNotNone(self.tracker.workspace_path)

    def test_generate_report(self):
        report = self.tracker.generate_report()
        self.assertIsNotNone(report)
        self.assertIsInstance(report, MaturityAssessment)
        self.assertGreaterEqual(report.convergence_score, 0)
        self.assertLessEqual(report.convergence_score, 100)

    def test_maturity_levels(self):
        report = self.tracker.generate_report()
        self.assertGreaterEqual(len(report.levels), 1)
        for level in report.levels:
            self.assertGreaterEqual(level.completion_percentage, 0)
            self.assertLessEqual(level.completion_percentage, 100)


if __name__ == '__main__':
    unittest.main()
