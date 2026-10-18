"""CBD! W38 routing-yield guards; added native branch coverage, no waiver."""
from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

HOME = Path(__file__).resolve().parents[1]
PATH = HOME / "feedback_route_yield_w38.py"
SPEC = importlib.util.spec_from_file_location("feedback_route_yield_w38", PATH)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def upstream(conclusion="success"):
    return {"workflow_run":{
        "id":451, "run_attempt":1, "status":"completed",
        "conclusion":conclusion, "name":"MIP B0 Test Admission and Coverage Evidence",
        "head_sha":"b"*40}}


def sample(**kw):
    args = dict(event=upstream(), route_output="[120, 118]",
                event_name="workflow_run", repository=mod.REPOSITORY,
                main_sha="a"*40, gate_run_id=900, gate_attempt=1,
                observed_utc="2026-10-19T00:02:14Z")
    args.update(kw)
    return args


class FeedbackRouteW38(unittest.TestCase):
    def test_native_two_route_success(self):
        receipt=mod.build(**sample())
        mod.verify(receipt)
        self.assertEqual(receipt["routed_pr_numbers"],[118,120])
        self.assertEqual(receipt["routed_unique_pr_count"],2)
        self.assertFalse(receipt["eligible_suppression"])
        self.assertFalse(receipt["remote_dispatch"])
    def test_upstream_red_still_requires_gate(self):
        r=mod.build(**sample(event=upstream("failure")))
        self.assertEqual(r["upstream"]["conclusion"],"failure")
        self.assertEqual(r["merge_admission"],"HOLD")
    def test_empty_route_is_observation_not_skip(self):
        r=mod.build(**sample(route_output="[]"))
        self.assertTrue(r["zero_route_observed"])
        self.assertIsNone(r["rerun_reduction_verified"])
        self.assertFalse(r["eligible_suppression"])
    def test_direct_review_event_not_suppressible(self):
        r=mod.build(**sample(event={},event_name="pull_request_review",route_output="[]"))
        self.assertTrue(r["zero_route_observed"])
        self.assertIsNone(r["upstream"])
        self.assertFalse(r["eligible_suppression"])
    def test_direct_tracking_issue_event_not_suppressible(self):
        for name in mod.DIRECT_EVENTS:
            with self.subTest(name=name):
                r=mod.build(**sample(event={"action":"edited"},event_name=name,route_output="[]"))
                self.assertEqual(r["merge_admission"],"HOLD")
    def test_duplicate_pr_rejected(self):
        with self.assertRaisesRegex(ValueError,"DUPLICATE_ROUTED_PR"):
            mod.build(**sample(route_output="[10,10]"))
    def test_boolean_pr_rejected(self):
        with self.assertRaisesRegex(ValueError,"ROUTED_PR_POSITIVE_INT"):
            mod.build(**sample(route_output="[true]"))
    def test_zero_and_negative_pr_rejected(self):
        for candidate in ("[0]","[-2]","[null]"):
            with self.subTest(candidate=candidate):
                with self.assertRaisesRegex(ValueError,"ROUTED_PR_POSITIVE_INT"):
                    mod.build(**sample(route_output=candidate))
    def test_malformed_routes_rejected(self):
        for candidate in ("", "1,2", '{"pr":123}', "[1,]"):
            with self.subTest(candidate=candidate):
                with self.assertRaises(ValueError):
                    mod.build(**sample(route_output=candidate))
    def test_route_size_rejected(self):
        with self.assertRaisesRegex(ValueError,"ROUTE_OUTPUT_SIZE"):
            mod.build(**sample(route_output=" "*16385))
    def test_route_cardinality_rejected(self):
        with self.assertRaisesRegex(ValueError,"ROUTE_OUTPUT_ARRAY"):
            mod.build(**sample(route_output=str(list(range(1,302)))))
    def test_wrong_repository_rejected(self):
        with self.assertRaisesRegex(ValueError,"OWNER_BOUNDARY"):
            mod.build(**sample(repository="GBOGEB/CODEX"))
    def test_bad_main_sha_rejected(self):
        with self.assertRaisesRegex(ValueError,"FEEDBACK_HEAD_EXACT_SHA"):
            mod.build(**sample(main_sha="abcdef"))
    def test_event_type_not_subscribed(self):
        with self.assertRaisesRegex(ValueError,"EVENT_NOT_SUBSCRIBED"):
            mod.build(**sample(event_name="release"))
    def test_event_without_payload(self):
        with self.assertRaisesRegex(ValueError,"EVENT_PAYLOAD_REQUIRED"):
            mod.build(**sample(event=None))
    def test_nonterminal_upstream_not_accepted(self):
        event=upstream()
        event["workflow_run"]["status"]="in_progress"
        with self.assertRaisesRegex(ValueError,"UPSTREAM_TERMINAL_REQUIRED"):
            mod.build(**sample(event=event))
    def test_missing_upstream_is_not_route(self):
        with self.assertRaisesRegex(ValueError,"UPSTREAM_RUN_REQUIRED"):
            mod.build(**sample(event={}))
    def test_missing_upstream_sha_rejected(self):
        event=upstream()
        del event["workflow_run"]["head_sha"]
        with self.assertRaisesRegex(ValueError,"UPSTREAM_HEAD_EXACT_SHA"):
            mod.build(**sample(event=event))
    def test_fake_bool_gate_identity_rejected(self):
        with self.assertRaisesRegex(ValueError,"GATE_RUN_ID_POSITIVE_INT"):
            mod.build(**sample(gate_run_id=True))
    def test_invalid_attempt_rejected(self):
        with self.assertRaisesRegex(ValueError,"GATE_ATTEMPT_POSITIVE_INT"):
            mod.build(**sample(gate_attempt=0))
    def test_negative_upstream_attempt_rejected(self):
        event=upstream()
        event["workflow_run"]["run_attempt"]=-1
        with self.assertRaisesRegex(ValueError,"UPSTREAM_ATTEMPT_POSITIVE_INT"):
            mod.build(**sample(event=event))
    def test_utc_timestamp_guard(self):
        for stamp in ("2026-10-19T01:10:00+01:00","2026-13-19T00:00:00Z","today",None):
            with self.subTest(stamp=stamp):
                with self.assertRaisesRegex(ValueError,"UTC_SOURCE_TIMESTAMP"):
                    mod.build(**sample(observed_utc=stamp))
    def test_direct_event_with_upstream_ambiguous(self):
        with self.assertRaisesRegex(ValueError,"AMBIGUOUS_EVENT_CLASS"):
            mod.build(**sample(event_name="issue_comment"))
    def test_stable_receipt_order_and_exact_idempotence(self):
        left=mod.build(**sample(route_output="[120,118]"))
        right=mod.build(**sample(route_output="[118,120]"))
        self.assertEqual(left["receipt_sha256"],right["receipt_sha256"])
        self.assertEqual(left,right)
    def test_tampered_route_fails_hash(self):
        r=mod.build(**sample())
        r["routed_pr_numbers"]=[44]
        with self.assertRaisesRegex(ValueError,"RECEIPT_DRIFT"):
            mod.verify(r)
    def test_authority_promotion_fails(self):
        for key,bad in (("merge_admission","PASS"),("security_waiver",True),
                        ("eligible_suppression",True),("remote_dispatch",True),
                        ("authority_transfer",True),("formal_root_closures",0)):
            with self.subTest(key=key):
                r=mod.build(**sample())
                r[key]=bad
                r["receipt_sha256"]=__import__("hashlib").sha256(
                    mod.canonical({k:v for k,v in r.items() if k!="receipt_sha256"})).hexdigest()
                with self.assertRaisesRegex(ValueError,"AUTHORITY_PROMOTION"):
                    mod.verify(r)
    def test_event_sha_is_not_main_attestation(self):
        result=mod.build(**sample(event_name="pull_request",event={},route_output="[]"))
        self.assertEqual(result["github_event_sha"],"a"*40)
        self.assertIs(result["main_head_verified"],False)
        self.assertNotIn("feedback_main_sha",result)
        mod.verify(result)
    def test_route_only_cannot_claim_completed_evaluation(self):
        for field,bad in (("evaluated_pr_count",2),("published_check_count",2),
                          ("rerun_reduction_verified",0.5),("route_stage","EVALUATED"),
                          ("source_coverage_delta",0.25)):
            with self.subTest(field=field):
                result=mod.build(**sample())
                result[field]=bad
                result["receipt_sha256"]=__import__("hashlib").sha256(
                    mod.canonical({k:v for k,v in result.items() if k!="receipt_sha256"})
                ).hexdigest()
                with self.assertRaisesRegex(ValueError,"ROUTE_NOT_EVALUATION_PROOF"):
                    mod.verify(result)
    def test_signed_duplicate_routes_rejected_even_with_consistent_count(self):
        result=mod.build(**sample())
        result["routed_pr_numbers"]=[118,118]
        result["receipt_sha256"]=__import__("hashlib").sha256(
            mod.canonical({k:v for k,v in result.items() if k!="receipt_sha256"})
        ).hexdigest()
        with self.assertRaisesRegex(ValueError,"RECEIPT_DUPLICATE_OR_UNORDERED"):
            mod.verify(result)
    def test_signed_wrong_event_sha_is_not_a_valid_receipt(self):
        result=mod.build(**sample())
        result["github_event_sha"]="short"
        result["receipt_sha256"]=__import__("hashlib").sha256(
            mod.canonical({k:v for k,v in result.items() if k!="receipt_sha256"})
        ).hexdigest()
        with self.assertRaisesRegex(ValueError,"EVENT_SHA_NOT_MAIN_ATTESTATION"):
            mod.verify(result)
    def test_signed_forged_upstream_ref_rejected(self):
        result=mod.build(**sample())
        result["upstream"]["head_sha"]="not-a-head"
        result["receipt_sha256"]=__import__("hashlib").sha256(
            mod.canonical({k:v for k,v in result.items() if k!="receipt_sha256"})
        ).hexdigest()
        with self.assertRaisesRegex(ValueError,"UPSTREAM_HEAD_EXACT_SHA"):
            mod.verify(result)
    def test_workflow_publishes_event_sha_not_false_main_head(self):
        workflow=(HOME.parents[1]/".github/workflows/pr-feedback-gate.yml").read_text()
        self.assertIn('--event-sha "$GITHUB_SHA"',workflow)
        self.assertNotIn('--main-sha "$GITHUB_SHA"',workflow)
    def test_missing_hash_rejected(self):
        r=mod.build(**sample())
        r["receipt_sha256"]=None
        with self.assertRaisesRegex(ValueError,"RECEIPT_HASH"):
            mod.verify(r)
    def test_workflow_preserves_direct_gate_and_terminal_fanin(self):
        text=(HOME.parents[1]/".github/workflows/pr-feedback-gate.yml").read_text()
        for trigger in ("  issue_comment:","  issues:","  pull_request_review:",
                        "  pull_request_review_comment:","  pull_request:",
                        "  workflow_dispatch:","  workflow_run:","  schedule:"):
            self.assertIn(trigger,text)
        section=text.split("  workflow_run:",1)[1].split("  schedule:",1)[0]
        self.assertIn("    types: [completed]",section)
        self.assertIn("--mark-failure-only",text)
        self.assertIn("cancel-in-progress: false",text)
        self.assertIn("continue-on-error: true",text)
        self.assertIn("Emit read-only routing yield",text)
    def test_noncritical_receipt_keeps_feedback_gate_first_red(self):
        text=(HOME.parents[1]/".github/workflows/pr-feedback-gate.yml").read_text()
        self.assertIn("  invalidate:",text)
        self.assertIn("  evaluate:",text)
        self.assertIn("    needs: [route, invalidate]",text)
        self.assertIn("python ci/governance/pr_feedback_gate.py",text)
        self.assertNotIn("cancel-in-progress: true",text)


if __name__=="__main__":
    unittest.main()
