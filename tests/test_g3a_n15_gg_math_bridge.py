"""Fail-closed G3A gg_MATH contract tests; provider runtime is separate."""
import copy
import unittest
from MIP.statistics.gg_math_g3a_consumer import transform, GG_MATH_SHA

SAMPLE = {
 "schema": "code-purple.mip.g3a.statistical-control.v1",
 "lineage": {
   "n13_sha": "b16ba5c6ff3d4106db9ac5cfb3d3164b3206cb52",
   "n13_run": 39040416656,
   "n14_sha": "1446d78a6e93a455d9bed71f070a6b460dc6e86d",
   "n14_run": 39046868554,
   "coverage_version": "7.16.2",
   "source_bytes_frozen": True,
   "exact_arcs_rejoined": True},
 "aggregate": {"eligible": 446, "n13_covered": 115, "n14_covered": 200,
               "six_sigma": "NOT_ASSESSED_FROM_BRANCH_COVERAGE"},
 "controls": {"merge_admission": "HOLD"},
 "modules": [
   {"path": "DMAIC_V3/debug_pipeline.py", "eligible": 116,
    "n13": 17, "n14": 94, "gained": 77, "lost": 0},
   {"path": "DMAIC_V3/phases/phase4_improve.py", "eligible": 134,
    "n13": 45, "n14": 53, "gained": 8, "lost": 0},
   {"path": "DMAIC_V3/phases/phase8_todo_management.py", "eligible": 118,
    "n13": 30, "n14": 30, "gained": 0, "lost": 0},
   {"path": "cicd_github_orchestrator.py", "eligible": 78,
    "n13": 23, "n14": 23, "gained": 0, "lost": 0}
 ]
}

class NativeToGGMathTests(unittest.TestCase):
 def test_typed_native_source_bound_bridge(self):
    result=transform(copy.deepcopy(SAMPLE))
    self.assertEqual(result["schema"], "gg_math.convergence_input.v1")
    self.assertEqual([r["k"] for r in result["observations"]],[115,200])
    self.assertEqual(result["federation"]["math_provider_sha"],GG_MATH_SHA)
    self.assertFalse(result["authority_transfer"])
    self.assertEqual(result["federation"]["merge_admission"], "HOLD")
 def test_denom_drift_rejected(self):
    x=copy.deepcopy(SAMPLE);x["aggregate"]["eligible"]=447
    with self.assertRaisesRegex(ValueError,"denominator"):transform(x)
 def test_source_drift_rejected(self):
    x=copy.deepcopy(SAMPLE);x["lineage"]["source_bytes_frozen"]=False
    with self.assertRaisesRegex(ValueError,"source"):transform(x)
 def test_module_scope_drift_rejected(self):
    x=copy.deepcopy(SAMPLE);x["modules"][0]["eligible"]=500
    with self.assertRaisesRegex(ValueError,"scope"):transform(x)
 def test_arc_identity_inconsistent_rejected(self):
    x=copy.deepcopy(SAMPLE);x["modules"][0]["gained"]=76
    with self.assertRaisesRegex(ValueError,"arc gain"):transform(x)
 def test_invalid_run_identity_rejected(self):
    x=copy.deepcopy(SAMPLE);x["lineage"]["n14_run"]=0
    with self.assertRaisesRegex(ValueError,"run ID"):transform(x)
 def test_no_sigma_from_coverage(self):
    x=copy.deepcopy(SAMPLE);x["aggregate"]["six_sigma"]="ACHIEVED"
    with self.assertRaisesRegex(ValueError,"Six Sigma"):transform(x)
 def test_no_admission_promotion(self):
    x=copy.deepcopy(SAMPLE);x["controls"]["merge_admission"]="PASS"
    with self.assertRaisesRegex(ValueError,"admission"):transform(x)
 def test_n14_not_equivalent_or_asymptotic(self):
    z=transform(copy.deepcopy(SAMPLE))
    self.assertFalse(z["defect_opportunities"]["independent"])
    self.assertNotIn("bradley_terry",z)
    self.assertNotIn("pca",z)

if __name__=="__main__":
 unittest.main()
