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


class EqualTimestamps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _env.require_kernels()

    def test_equal_mtime_relatives_go_to_cycle_review(self):
        inv = _env.engine("estate_inventory")
        zips = [
            {
                "name": n,
                "mtime": 1000.0,
                "family": "bundle",
                "zip": {"names_sig": []},
                "age_days": 1,
            }
            for n in ("bundle_v1.zip", "bundle_v2.zip")
        ]
        inv.reverse_kahn(zips)
        self.assertEqual([z["kahn_layer"] for z in zips], [-1, -1])

    def test_strictly_older_is_still_superseded(self):
        inv = _env.engine("estate_inventory")
        zips = [
            {
                "name": "a.zip",
                "mtime": 1000.0,
                "family": "f",
                "zip": {"names_sig": []},
                "age_days": 1,
            },
            {
                "name": "b.zip",
                "mtime": 2000.0,
                "family": "f",
                "zip": {"names_sig": []},
                "age_days": 1,
            },
        ]
        inv.reverse_kahn(zips)
        self.assertEqual(
            {z["name"]: z["kahn_layer"] for z in zips}, {"a.zip": 1, "b.zip": 0}
        )


if __name__ == "__main__":
    unittest.main()
