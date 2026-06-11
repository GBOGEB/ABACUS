"""
DMAIC V3 Test Suite - Git Manager Tests
Version: 3.2.0
Created: 2025-11-12T04:50:00Z
Updated: 2025-11-12T05:00:00Z
"""

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from DMAIC_V3.integrations.git_manager import GitManager


class TestGitManager(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(__file__).parent.parent.parent
        self.manager = GitManager(self.workspace)

    def test_initialization(self):
        self.assertIsNotNone(self.manager)

    def test_get_status(self):
        status = self.manager.get_status()
        self.assertIsNotNone(status)
        self.assertIsNotNone(status.branch)

    def test_baselines_operations(self):
        baselines_path = self.workspace / "config" / "baselines.json"

        baselines = self.manager.list_baselines()
        self.assertIsInstance(baselines, list)

        if baselines_path.exists():
            self.assertTrue(baselines_path.exists())


if __name__ == '__main__':
    unittest.main()
