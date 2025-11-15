"""
DMAIC V3 Test Suite - Version Manager Tests
Version: 3.2.0
Created: 2025-11-12T04:50:00Z
Updated: 2025-11-12T05:00:00Z
"""

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from DMAIC_V3.integrations.version_manager import VersionManager, BumpType, VersionInfo


class TestVersionManager(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(__file__).parent.parent.parent
        self.manager = VersionManager(self.workspace)

    def test_initialization(self):
        self.assertIsNotNone(self.manager)

    def test_get_current_version(self):
        version = self.manager.get_current_version()
        self.assertIsNotNone(version)
        self.assertIsInstance(version, VersionInfo)
        self.assertGreaterEqual(version.major, 0)
        self.assertGreaterEqual(version.minor, 0)
        self.assertGreaterEqual(version.patch, 0)

    def test_version_comparison(self):
        v1 = VersionInfo(3, 0, 0)
        v2 = VersionInfo(3, 1, 0)
        v3 = VersionInfo(4, 0, 0)

        self.assertLess(v1, v2)
        self.assertLess(v2, v3)
        self.assertEqual(v1, VersionInfo(3, 0, 0))

    def test_version_string(self):
        version = VersionInfo(3, 2, 1)
        self.assertEqual(str(version), "3.2.1")


if __name__ == '__main__':
    unittest.main()
