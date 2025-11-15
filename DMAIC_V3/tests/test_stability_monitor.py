"""
DMAIC V3 Test Suite - Stability Monitor Tests
Version: 3.2.0
Created: 2025-11-12T04:50:00Z
Updated: 2025-11-12T05:00:00Z
"""

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from DMAIC_V3.convergence.stability_monitor import StabilityMonitor


class TestStabilityMonitor(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(__file__).parent.parent.parent
        self.monitor = StabilityMonitor(self.workspace)

    def test_initialization(self):
        self.assertIsNotNone(self.monitor)
        self.assertEqual(self.monitor.iteration, 0)

    def test_file_tracking(self):
        test_file = Path(__file__)
        hash1 = self.monitor._calculate_file_hash(test_file)
        self.assertIsNotNone(hash1)
        self.assertEqual(len(hash1), 64)

        hash2 = self.monitor._calculate_file_hash(test_file)
        self.assertEqual(hash1, hash2)

    def test_file_snapshot(self):
        test_file = Path(__file__)
        snapshot = self.monitor.snapshot_file(test_file)
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.path, str(test_file))
        self.assertGreater(snapshot.size, 0)

    def test_scan_workspace(self):
        changes = self.monitor.scan_workspace()
        self.assertIsInstance(changes, int)
        self.assertGreaterEqual(changes, 0)

    def test_generate_report(self):
        self.monitor.scan_workspace()
        report = self.monitor.generate_report()
        self.assertIsNotNone(report)
        self.assertGreaterEqual(report.overall_stability, 0)
        self.assertLessEqual(report.overall_stability, 100)


if __name__ == '__main__':
    unittest.main()
