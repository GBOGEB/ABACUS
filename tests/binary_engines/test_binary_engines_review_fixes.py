"""Regression tests for the #2746 review threads (estate_probe, estate_inventory, estate_moveplan)."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.binary_engines import _env


class SheetState(unittest.TestCase):
    def test_hidden_state_is_read_in_any_attribute_order(self):
        probe = _env.engine("estate_probe")
        wb = (
            '<workbook><sheets><sheet name="Visible" sheetId="1" r:id="rId1"/>'
            '<sheet name="Hid" sheetId="2" state="hidden" r:id="rId2"/>'
            '<sheet state="veryHidden" name="Deep" sheetId="3" r:id="rId3"/></sheets></workbook>'
        )
        self.assertEqual(
            probe._sheet_entries(wb),
            [("Visible", ""), ("Hid", "hidden"), ("Deep", "veryHidden")],
        )


if __name__ == "__main__":
    unittest.main()
