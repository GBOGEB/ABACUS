"""Negative tests for W+1 measured cohort consistency."""
import copy
import json
import unittest
from pathlib import Path
from tools.everred_v3.scripts.code_purple_w1_growth import validate

G=Path("docs/code-purple-w1/growth-ledger.json")
P=Path("docs/code-purple-w1/pulse_telemetry.json")
class TestGrowthContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g=json.loads(G.read_text())
        cls.p=json.loads(P.read_text())
    def test_valid_replay(self):
        self.assertEqual(validate(self.g,self.p)["status"],"PASS_CONSISTENCY_ONLY")
    def test_source_sha_change(self):
        x=copy.deepcopy(self.g);x["cohorts"][1]["source_sha"]="f"*40
        with self.assertRaises(ValueError):validate(x,self.p)
    def test_denominator_forgery(self):
        x=copy.deepcopy(self.g);x["cohorts"][1]["changed_lines"]["eligible"]=626
        with self.assertRaises(ValueError):validate(x,self.p)
    def test_run_accounting(self):
        x=copy.deepcopy(self.g);x["cohorts"][0]["run_total"]=22
        with self.assertRaises(ValueError):validate(x,self.p)
    def test_admission_promotion(self):
        x=copy.deepcopy(self.g);x["merge_authorized"]=True
        with self.assertRaises(ValueError):validate(x,self.p)
    def test_false_growth(self):
        x=copy.deepcopy(self.g);x["matched_native_changes"]["coverage_covered"]=247
        with self.assertRaises(ValueError):validate(x,self.p)
if __name__=="__main__":unittest.main()
