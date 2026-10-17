"""Contract tests for source-owned CBD workflow manifestation planner."""
import copy
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import cbd_workflow_failure_waves as cbd
BASE=Path(__file__).resolve().parents[1]/"docs/ci/CBD_6PR_FAILED_RUN_OBSERVATIONS_20261017.json"

class CBDTest(unittest.TestCase):
    def setUp(self):self.data=json.loads(BASE.read_text())
    def test_native_sample_counts(self):
        o=cbd.produce(self.data)
        self.assertEqual(12,o["observed"]["run_attempt_count"])
        self.assertEqual(6,o["observed"]["pr_count"])
        self.assertEqual(12,o["observed"]["conclusions"]["failure"])
        self.assertIsNone(o["observed"]["confirmed_causal_root_count"])
    def test_deterministic_no_mutation(self):
        old=copy.deepcopy(self.data)
        self.assertEqual(cbd.produce(self.data),cbd.produce(self.data))
        self.assertEqual(old,self.data)
    def test_duplicate_attempt_rejected(self):
        self.data["observations"].append(copy.deepcopy(self.data["observations"][0]))
        with self.assertRaises(ValueError):cbd.produce(self.data)
    def test_short_sha_rejected(self):
        self.data["observations"][0]["sha"]="deadbeef"
        with self.assertRaises(ValueError):cbd.produce(self.data)
    def test_forged_merge_admission_rejected(self):
        self.data["authority"]["merge_admission"]="PASS"
        with self.assertRaises(ValueError):cbd.produce(self.data)
    def test_forged_security_waiver_rejected(self):
        self.data["authority"]["security_waiver"]=True
        with self.assertRaises(ValueError):cbd.produce(self.data)
    def test_forged_url_rejected(self):
        self.data["observations"][0]["url"]="https://evil.example/"
        with self.assertRaises(ValueError):cbd.produce(self.data)
    def test_shared_workflow_not_accepted_root(self):
        o=cbd.produce(self.data)
        root=next(x for x in o["candidate_families"] if x["candidate_family"]=="INTEGRATED_TEST_SUITE")
        self.assertEqual(5,root["unique_prs_affected"])
        self.assertFalse(root["root_confirmed"])
        self.assertFalse(root["first_red_confirmed"])
        self.assertFalse(root["independent_admission"])
    def test_path_collisions_serialized(self):
        o=cbd.produce(self.data)
        rows=[x for x in o["candidate_disjoint_waves"] if x["candidate_family"] in ("MATRIX_COMPATIBILITY","LEGACY_PIPELINE")]
        self.assertEqual(2,len(rows))
        self.assertTrue(all(x["source_mutation_authorized"] is False for x in rows))
    def test_unknown_workflow_reader_only(self):
        self.data["observations"][0]["workflow"]="NEW_UNKNOWN_GATE"
        o=cbd.produce(self.data)
        x=next(x for x in o["candidate_disjoint_waves"] if x["candidate_family"]=="UNCLASSIFIED_WORKFLOW")
        self.assertEqual("READER",x["worker_type"])
    def test_no_workflow_success_inferred_from_missing(self):
        self.assertEqual(0,cbd.produce(self.data)["observed"]["conclusions"]["success"])
        self.assertIsNone(cbd.produce(self.data)["observed"]["matched_coverage_delta"])

if __name__=="__main__":unittest.main()
