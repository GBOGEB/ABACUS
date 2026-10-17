"""Regression tests for observational BD/LDAB taxonomy labels."""

import copy
import unittest

from scripts.mip_root_taxonomy import (
    CLASSES,
    annotate_join,
    canonical_bytes,
    classify,
)


class TaxonomyTests(unittest.TestCase):
    def setUp(self):
        self.report = {
            "schema": "bd.ldab.joined.census.v1",
            "roots": [
                {"root_id": "CI-222", "category": "CI", "observations": []},
                {"root_id": "CI-111", "category": "CI", "observations": []},
            ],
            "merge_admission": "HOLD",
            "authority_transfer": False,
            "security_waiver": False,
        }

    def test_every_class_has_an_explicit_code(self):
        self.assertEqual(len(CLASSES), 10)
        from scripts.mip_root_taxonomy import CODES

        self.assertEqual(set(CODES.values()), set(CLASSES) - {"UNKNOWN"})

    def test_unknown_fails_closed_to_unknown(self):
        self.assertEqual(classify("not-an-approved-diagnostic"), "UNKNOWN")

    def test_deterministic_and_preserves_canonical_input(self):
        before = copy.deepcopy(self.report)
        a = annotate_join(self.report, {"CI-111": "STALE_WORKFLOW_INVENTORY"})
        b = annotate_join(self.report, {"CI-111": "STALE_WORKFLOW_INVENTORY"})
        self.assertEqual(canonical_bytes(a), canonical_bytes(b))
        self.assertEqual(self.report, before)
        self.assertEqual(a["annotations"][0]["secondary_class"], "GOVERNANCE")
        self.assertEqual(a["annotations"][1]["secondary_class"], "UNKNOWN")
        self.assertIsNone(a["annotations"][0]["causal_root_confirmed"])
        self.assertEqual(a["merge_admission"], "HOLD")

    def test_reject_duplicate_roots(self):
        self.report["roots"].append(self.report["roots"][0])
        with self.assertRaises(ValueError):
            annotate_join(self.report, {})

    def test_reject_unbound_root(self):
        with self.assertRaises(ValueError):
            annotate_join(self.report, {"CI-999": "YAML_LINE_LENGTH"})

    def test_reject_authority_transfer(self):
        self.report["authority_transfer"] = True
        with self.assertRaises(ValueError):
            annotate_join(self.report, {})

    def test_reject_security_waiver(self):
        self.report["security_waiver"] = True
        with self.assertRaises(ValueError):
            annotate_join(self.report, {})

    def test_reject_invalid_code_type(self):
        with self.assertRaises(ValueError):
            annotate_join(self.report, {"CI-111": 123})


if __name__ == "__main__":
    unittest.main()
