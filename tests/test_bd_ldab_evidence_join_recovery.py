import unittest

from tools.recovery.bd_ldab_evidence_join import join


class BDLDABJoinTests(unittest.TestCase):
    def test_untrusted_evidence_no_closure(self):
        r = join(
            {"roots": [{"root_id": "R-1"}]},
            {"observations": [{"root_id": "R-1", "fingerprint": "x"}]},
        )
        self.assertFalse(r["observations"][0]["evidence_attached"])
        self.assertIsNone(r["root_closures"])

    def test_attributable_evidence_still_not_closure(self):
        o = {
            "root_id": "R-1",
            "fingerprint": "x",
            "commit_sha": "a" * 40,
            "run_id": 1,
            "job_id": 2,
            "evidence_uri": "https://github.com/example",
            "causal_link_verified": True,
        }
        r = join({"roots": [{"root_id": "R-1"}]}, {"observations": [o]})
        self.assertTrue(r["observations"][0]["evidence_attached"])
        self.assertFalse(r["observations"][0]["closure_credit"])


if __name__ == "__main__":
    unittest.main()
