"""Read-only handover binder negative and positive tests."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

import binder

BASE = Path(__file__).resolve().parent


class TestCBDHandoverBinder(unittest.TestCase):
    def setUp(self):
        self.doc = binder.load(BASE / "BINDER.json")

    def test_binder_is_readonly(self):
        self.assertEqual(self.doc["control"]["merge_admission"], "HOLD")
        self.assertFalse(self.doc["control"]["security_waiver"])
        self.assertFalse(self.doc["control"]["authority_transfer"])

    def test_exact_source_repositories(self):
        self.assertEqual(len(self.doc["repositories"]), 5)
        self.assertEqual(len({r["repo"] for r in self.doc["repositories"]}), 5)

    def test_canonical_pr_refs_and_unknowns(self):
        text = binder.markdown(self.doc)
        for term in (
            "#1998",
            "#2045",
            "#2046",
            "#2027",
            "#2041",
            "PCA",
            "UNKNOWN",
            "41.31%",
        ):
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_merge_promotion_fails_closed(self):
        tampered = copy.deepcopy(self.doc)
        tampered["control"]["merge_admission"] = "PASS"
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.json"
            p.write_text(json.dumps(tampered))
            with self.assertRaisesRegex(ValueError, "tamper"):
                binder.load(p)

    def test_bad_repository_sha_fails(self):
        tampered = copy.deepcopy(self.doc)
        tampered["repositories"][0]["sha"] = "HEAD"
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.json"
            p.write_text(json.dumps(tampered))
            with self.assertRaisesRegex(ValueError, "bad repo"):
                binder.load(p)

    def test_unknown_security_credit_fails(self):
        tampered = copy.deepcopy(self.doc)
        tampered["metrics"]["matched_security_delta"] = 1
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.json"
            p.write_text(json.dumps(tampered))
            with self.assertRaisesRegex(ValueError, "scanner credit"):
                binder.load(p)

    def test_no_network_in_offline_renderer(self):
        self.assertIn("merge admission HOLD", binder.markdown(self.doc))

    def test_api_path_restriction(self):
        with self.assertRaisesRegex(ValueError, "restricted API"):
            binder.api_get("/users/anyone", "")


if __name__ == "__main__":
    unittest.main()
