import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from ingest_bd_ldab_join import to_event

from everred import InvalidEvidence

A = "a" * 40


class JoinedCensusAdapter(unittest.TestCase):
    def template(self):
        return {
            "schema": "bd.ldab.joined.census.v1",
            "scope": {
                "repository": "GBOGEB/ABACUS",
                "head_sha": A,
                "run_id": 3,
                "job_id": 4,
                "evidence_url": "https://github.com/GBOGEB/ABACUS/actions/runs/3",
            },
            "metrics": {"full_bandit_unique": 2, "debug_receipts": None},
            "roots": [{"root_id": "BD-1"}, {"root_id": "CI-2"}],
            "unlinked_debug_receipts": [],
            "merge_admission": "HOLD",
            "authority_transfer": False,
            "security_waiver": False,
        }

    def test_candidate_only(self):
        e = to_event(self.template())
        self.assertEqual(e["kind"], "note")
        self.assertEqual(e["evidence"]["root_causality"], "UNCONFIRMED")

    def test_stable_id(self):
        self.assertEqual(
            to_event(self.template())["id"], to_event(self.template())["id"]
        )

    def test_no_authority_transfer(self):
        o = self.template()
        o["authority_transfer"] = True
        with self.assertRaises(InvalidEvidence):
            to_event(o)

    def test_no_fake_admission(self):
        o = self.template()
        o["merge_admission"] = "PASS"
        with self.assertRaises(InvalidEvidence):
            to_event(o)

    def test_sha_bound(self):
        o = self.template()
        o["scope"]["head_sha"] = "HEAD"
        with self.assertRaises(InvalidEvidence):
            to_event(o)

    def test_malformed_id(self):
        o = self.template()
        o["roots"][0]["root_id"] = "ABACUS-RC-confirmed"
        with self.assertRaises(InvalidEvidence):
            to_event(o)


if __name__ == "__main__":
    unittest.main()
