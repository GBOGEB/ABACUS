"""Fail-closed W38 global ledger and HTML projection invariants."""
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from render_global import render

class GlobalLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((ROOT/"ledger.json").read_text(encoding="utf-8"))
        cls.template=(ROOT/"index.template.html").read_text(encoding="utf-8")
        cls.html=(ROOT/"index.html").read_text(encoding="utf-8")
    def test_exact_template_parity(self):
        self.assertEqual(render(self.data,self.template),self.html)
    def test_fixed_local_denominator_and_pulse(self):
        c=self.data["focused_coverage"]
        self.assertEqual((c["previous_covered"],c["eligible"],c["covered"]),(660,723,707))
        self.assertEqual((c["cases_pass"],c["cases_fail"],c["cases_skip"]),(203,0,0))
        self.assertEqual(sum(x["covered"] for x in c["families"]),707)
        self.assertEqual(sum(x["eligible"] for x in c["families"]),723)
    def test_stop_is_not_global_promotion(self):
        self.assertEqual(self.data["governed_admission"],"HOLD")
        self.assertIsNone(self.data["accepted_causal_roots_remaining"])
        self.assertFalse(self.data["global_control"])
        self.assertFalse(self.data["six_sigma_claim"])
        self.assertIsNone(self.data["focused_coverage"]["canonical_main_credit"])
        self.assertTrue(all(100*x["covered"]/x["eligible"]>=95 for x in self.data["focused_coverage"]["families"]))
    def test_governance_remains_source_only(self):
        g=self.data["governance"]
        self.assertEqual((g["source_workflow_count"],g["baseline_unclassified"],g["candidate_unclassified"]),(198,7,0))
        self.assertIsNone(g["policy_native_acceptance"])
        self.assertFalse(g["red_canary_verified"])
    def test_three_distinct_authorities(self):
        self.assertEqual([r["role"] for r in self.data["repos"]],[
            "EVIDENCE_AND_ADMISSION_AUTHORITY","FEDERATION_CONSUMER","ENGINEERING_DOMAIN_AUTHORITY"])
        for r in self.data["repos"]:
            self.assertEqual(len(r["main_sha"]),40)
    def test_dov_withheld_independent_attestation(self):
        self.assertEqual(len(self.data["dov"]["responsibilities"]),5)
        self.assertTrue(all(x["status"] in ("UNVERIFIED","DEFER") for x in self.data["dov"]["responsibilities"]))
    def test_public_refresh_remains_read_only(self):
        self.assertIn("Refresh heads",self.html)
        self.assertIn("api.github.com",self.html)
        self.assertNotIn("PRIVATE-TOKEN",self.html)
        self.assertNotIn("authorization:",self.html.lower())
        self.assertIn("UNKNOWN",self.html)
    def test_reject_fabricated_credit_and_denominator(self):
        bad=json.loads(json.dumps(self.data))
        bad["focused_coverage"]["covered"]+=1
        with self.assertRaises(ValueError):render(bad,self.template)
        bad=json.loads(json.dumps(self.data));bad["governed_admission"]="PASS"
        with self.assertRaises(ValueError):render(bad,self.template)
    def test_repo_population_totals(self):
        repos=self.data["repos"]
        self.assertEqual((sum(r["issues_open"] for r in repos),sum(r["issues_closed"] for r in repos)),(106,373))
        self.assertEqual((sum(r["prs_open"] for r in repos),sum(r["prs_closed_unmerged"] for r in repos),sum(r["prs_merged"] for r in repos)),(19,314,4518))
if __name__=="__main__":unittest.main()
