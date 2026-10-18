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
        self.assertEqual((g["source_workflow_count"],g["baseline_unclassified"],g["candidate_unclassified"]),(201,3,0))
        self.assertEqual(g["previous_native_run"]["status"],"FAIL")
        self.assertIsNone(g["qualification_run"])
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
        self.assertEqual((sum(r["prs_open"] for r in repos),sum(r["prs_closed_unmerged"] for r in repos),sum(r["prs_merged"] for r in repos)),(18,314,4532))

    def test_no_deleted_branch_or_truncated_git_source_link(self):
        self.assertNotIn("code-purple/w38-global-dov-hub-20261018",self.html)
        for route in self.data["routes"]:
            self.assertRegex(route["url"],r"^https://github[.]com/GBOGEB/[^/]+/(blob|tree)/[a-f0-9]{40}/")
        self.assertIn("ccc07c76a506a66fc20cbe821ef0ec4c0a3fe064",
                      next(x["url"] for x in self.data["routes"] if x["id"]=="w38"))
    def test_github_metadata_cannot_become_admission(self):
        self.assertIn("historical.head_sha",self.html)
        self.assertIn("HEAD MISMATCH",self.html)
        self.assertIn("metadata only",self.html)
        self.assertNotIn("setInterval(",self.html)
    def test_reject_spoofed_publication_and_broken_source_ref(self):
        bad=json.loads(json.dumps(self.data))
        bad["routes"][0]["url"]="https://github.com/GBOGEB/ABACUS/blob/not-a-sha/file"
        with self.assertRaises(ValueError):render(bad,self.template)
        bad=json.loads(json.dumps(self.data))
        bad["presentation"]["pages_deployment_verified"]=True
        with self.assertRaises(ValueError):render(bad,self.template)
    def test_evidence_type_table_is_scrolled_locally_at_laptop_width(self):
        self.assertIn('<h3>Evidence-type qualification</h3>\\n<div class="tablewrap"><table>'.replace('\\n','\n'), self.html)
        self.assertIn('</tbody></table></div><p class="detail">Evidence available',self.html)

    def test_explicit_four_pulse_trajectory_is_not_main_b0(self):
        c=self.data["focused_coverage"]
        self.assertEqual([r["covered"] for r in c["trajectory"]],[660,697,707,707])
        self.assertTrue(all(r["eligible"]==723 for r in c["trajectory"]))
        self.assertIsNone(c["canonical_main_credit"])
if __name__=="__main__":unittest.main()
