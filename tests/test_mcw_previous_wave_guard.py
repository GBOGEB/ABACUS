"""Prevent forged previous-wave coverage from earning a false DoV gain."""
from __future__ import annotations

import unittest

from tools.mcw_federation_rollup import rollup


class PreviousWaveGuardTests(unittest.TestCase):
    def setUp(self):
        self.previous = {
            "schema": "mcw.federation.rollup.v1",
            "nodes": [{
                "id": "A", "repository": "GBOGEB/ABACUS",
                "source_sha": "a" * 40, "family": "MCL",
                "proof": {"coverage": {
                    "scope_id": "MCL", "config_sha256": "b" * 64,
                    "files": ["x.py"], "covered_lines": 6,
                    "total_lines": 10, "covered_branches": 3,
                    "total_branches": 5, "line_percent": 60.0,
                    "branch_percent": 60.0,
                }},
            }],
        }
        self.input = {
            "schema": "mcw.federation.input.v1",
            "wave_id": "W-Guard", "nodes": [], "edges": [],
        }

    def test_valid_previous_report_is_accepted(self):
        outcome = rollup(self.input, ".", self.previous)
        self.assertEqual("HOLD", outcome["merge_admission"])

    def test_tampered_previous_percentage_rejected(self):
        self.previous["nodes"][0]["proof"]["coverage"]["line_percent"] = -10000
        with self.assertRaisesRegex(ValueError, "tampered previous coverage"):
            rollup(self.input, ".", self.previous)

    def test_inconsistent_previous_numerator_rejected(self):
        self.previous["nodes"][0]["proof"]["coverage"]["covered_lines"] = 20
        with self.assertRaises(ValueError):
            rollup(self.input, ".", self.previous)

    def test_duplicate_previous_identity_rejected(self):
        self.previous["nodes"].append(self.previous["nodes"][0].copy())
        with self.assertRaises(ValueError):
            rollup(self.input, ".", self.previous)

    def test_previous_source_sha_required(self):
        self.previous["nodes"][0]["source_sha"] = "wrong"
        with self.assertRaises(ValueError):
            rollup(self.input, ".", self.previous)


if __name__ == "__main__":
    unittest.main()
