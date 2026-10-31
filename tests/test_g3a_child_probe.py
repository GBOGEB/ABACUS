"""Tracked and persistent subprocess probe, not a temporary source file."""
import unittest


class G3AChildProbe(unittest.TestCase):
    def test_child_can_execute(self):
        self.assertEqual(2 + 2, 4)
