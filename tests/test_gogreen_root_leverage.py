import unittest

from scripts.gogreen_root_leverage import analyze


class RootLeverageTests(unittest.TestCase):
    def test_matching_job_labels_do_not_infer_shared_root(self):
        rows = [{"pr": p, "head_sha": str(p), "run_id": p, "job_id": p,
                 "job": "Security Scanning", "status": "failure"}
                for p in (2070, 2077)]
        result = analyze(rows)
        self.assertEqual(result["failed_category_overlap"][0]["count"], 2)
        self.assertEqual(result["proven_root_leverage"], [])
        self.assertEqual(result["unknown_root_prs"], [2070, 2077])

    def test_source_bound_root_and_deduplication(self):
        row = {"pr": 2070, "head_sha": "abc", "run_id": 1, "job_id": 2,
               "job": "Black", "status": "failure", "root_id": "R1",
               "root_evidence": "https://example.test/receipt",
               "first_red_signature": "black check"}
        result = analyze([row, row, dict(row, pr=2077, job_id=3)])
        self.assertEqual(result["observation_count_deduplicated"], 2)
        self.assertEqual(result["proven_root_leverage"][0]["blocked_prs"], 2)
        self.assertEqual(result["potential_unique_prs_released"], 2)

    def test_root_without_evidence_is_unknown(self):
        result = analyze([{"pr": 1, "status": "failure", "job": "Black",
                           "root_id": "R1", "first_red_signature": "x"}])
        self.assertEqual(result["proven_root_leverage"], [])
        self.assertEqual(result["unknown_root_prs"], [1])


if __name__ == "__main__":
    unittest.main()
