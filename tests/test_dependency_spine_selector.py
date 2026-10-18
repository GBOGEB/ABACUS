"""ABACUS owner scheduler stage-only selector no-promotion controls."""
import importlib.util
import unittest
from pathlib import Path
FILE=Path(__file__).resolve().parents[1]/"runtime"/"execution"/"dependency_spine_readonly_selector.py"
spec=importlib.util.spec_from_file_location("dep_spine_selector",FILE)
assert spec and spec.loader
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
HEAD="a"*40
CODEX="b"*40

def fixture():
    r={"schema":"codex.mycelium.dependency_spine.stage.v1",
       "consumer_repo":"GBOGEB/CODEX","consumer_head_sha":CODEX,
       "source_head_sha":"c"*40,"source_receipt_sha256":"d"*64,
       "child_disposition":"DEFER","merge_admission":"HOLD","formal_credit_delta":0,
       "authenticated_remote_execution":False,"native_producer_run_job_attempt_bound":False,
       "mutation_enabled":False,"dispatch_authorized":False,"authority_transfer":False,
       "stage_status":"STAGE_ONLY_VALIDATED_NO_AUTHENTICATED_CONSUMER_PROOF"}
    r["stage_digest_sha256"]=mod.checksum(mod.encode(r))
    return r

class SelectorTests(unittest.TestCase):
    def test_missing_input_defaults_defer(self):
        r=mod.select(HEAD,None)
        mod.verify(r)
        self.assertEqual(r["selector_state"],"DEFER_NO_CODEX_RECEIPT")
    def test_staged_source_is_not_execution(self):
        r=mod.select(HEAD,fixture(),CODEX);mod.verify(r)
        self.assertEqual(r["selector_state"],"PROPOSAL_NOT_DISPATCHED")
        self.assertEqual(r["observed_dispatches"],0)
        self.assertIsNone(r["successful_worker_returns"])
    def test_wrong_consumer_head(self):
        with self.assertRaisesRegex(ValueError,"CODEX_STAGE_HEAD_MISMATCH"):
            mod.select(HEAD,fixture(),"e"*40)
    def test_bad_consumer_digest(self):
        r=fixture();r["source_head_sha"]="0"*40
        with self.assertRaisesRegex(ValueError,"CODEX_STAGE_DIGEST_BAD"):
            mod.select(HEAD,r,CODEX)
    def test_forged_authority(self):
        r=fixture();r["dispatch_authorized"]=True
        r["stage_digest_sha256"]=mod.checksum(mod.encode({k:v for k,v in r.items() if k!="stage_digest_sha256"}))
        with self.assertRaisesRegex(ValueError,"CODEX_AUTHORITY_ESCALATION"):
            mod.select(HEAD,r,CODEX)
    def test_missing_head_ref(self):
        with self.assertRaisesRegex(ValueError,"CODEX_HEAD_REQUIRED"):
            mod.select(HEAD,fixture())
    def test_bad_owner_head(self):
        with self.assertRaisesRegex(ValueError,"ABACUS_HEAD_INVALID"):
            mod.select("branch",None)
    def test_no_promotion_even_if_return_rehashed(self):
        r=mod.select(HEAD,None)
        r["observed_dispatches"]=1
        r["return_sha256"]=mod.checksum(mod.encode({k:v for k,v in r.items() if k!="return_sha256"}))
        with self.assertRaisesRegex(ValueError,"SCHEDULER_FALSE_DISPATCH"):
            mod.verify(r)
    def test_value_preservation(self):
        r=mod.select(HEAD,fixture(),CODEX)
        self.assertEqual(r["source_qps_head_sha"],"c"*40)
        self.assertEqual(r["source_codex_head_sha"],CODEX)
        self.assertEqual(r["domain"],"reconciliation_execution")
    def test_priority_is_explicit(self):
        r=mod.select(HEAD,None)
        self.assertEqual([x["priority"] for x in r["planned_actions"]],[0,1,1])
