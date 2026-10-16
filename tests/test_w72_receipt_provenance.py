"""Negative and positive provenance controls: source SHA != PR synthetic SHA."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.w72_receipt_provenance import (
    canonical, checkout_sha, receipt, resolved_head, run, strict_sha,
)
from tools.w72_testcase_telemetry import parse_junit

HEAD = "a" * 40
MERGE = "b" * 40
OTHER = "c" * 40
JUNIT = b'<testsuite tests="2"><testcase classname="a" name="ok" time="0.02"/><testcase classname="b" name="skipped" time="0"><skipped message="requires docker"/></testcase></testsuite>'


def fixture(**kwargs):
    row = dict(observed_sha=HEAD,event_name="pull_request",
               payload={"pull_request":{"head":{"sha":HEAD}}},
               context_sha=MERGE,run_id=101,run_attempt=1,job_id="clean-clone",
               junit=parse_junit(JUNIT),junit_bytes=JUNIT)
    row.update(kwargs)
    return row


class W72ReceiptTests(unittest.TestCase):
    def test_pr_head_not_synthetic_merge(self):
        r=receipt(**fixture())
        self.assertEqual(r["source_sha"], HEAD)
        self.assertNotEqual(r["source_sha"], r["event_context_sha"])
        self.assertTrue(r["source_checkout_matched"])
        self.assertEqual(r["test_counts"]["skipped"],1)
        self.assertIsNone(r["root_closures"])

    def test_direct_dispatch_uses_head(self):
        r=receipt(**fixture(event_name="workflow_dispatch",payload={},context_sha=HEAD))
        self.assertFalse(r["context_sha_may_be_synthetic_merge"])

    def test_push_uses_head(self):
        self.assertEqual(resolved_head("push",{},HEAD),HEAD)

    def test_pr_mismatched_checkout_rejected(self):
        with self.assertRaisesRegex(ValueError, "checkout mismatch"):
            receipt(**fixture(observed_sha=OTHER))

    def test_pr_context_identity_not_substituted(self):
        with self.assertRaises(ValueError):
            receipt(**fixture(observed_sha=MERGE))

    def test_dispatch_context_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            receipt(**fixture(event_name="workflow_dispatch",payload={},context_sha=OTHER))

    def test_missing_event_payload_rejected(self):
        with self.assertRaises(ValueError):
            receipt(**fixture(payload={}))

    def test_missing_head_rejected(self):
        with self.assertRaises(ValueError):
            receipt(**fixture(payload={"pull_request":{"head":{}}}))

    def test_foreign_event_rejected(self):
        with self.assertRaises(ValueError):
            receipt(**fixture(event_name="pull_request_target"))

    def test_invalid_sha_length_rejected(self):
        for bad in ("", "a"*39, "a"*41, "A"*40, None):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                strict_sha(bad,"input")

    def test_github_run_zero_rejected(self):
        for bad in (0,-1,True,None):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                receipt(**fixture(run_id=bad))

    def test_run_attempt_zero_rejected(self):
        for bad in (0,-1,True,None):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                receipt(**fixture(run_attempt=bad))

    def test_invalid_job_key_rejected(self):
        for bad in ("", "hi space", "a"*101):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                receipt(**fixture(job_id=bad))

    def test_failed_junit_cannot_pass(self):
        fail=parse_junit(b'<testsuite tests="1"><testcase classname="a" name="broken"><failure/></testcase></testsuite>')
        with self.assertRaisesRegex(ValueError,"non-green"):
            receipt(**fixture(junit=fail))

    def test_missing_junit_denominator_rejected(self):
        p=parse_junit(JUNIT);p['counts']['collected']=3
        with self.assertRaises(ValueError):
            receipt(**fixture(junit=p))

    def test_no_forged_root_and_security_credit(self):
        r=receipt(**fixture())
        for key in ("merge_authorized","security_waiver","authority_transfer"):
            self.assertFalse(r[key])
        self.assertIsNone(r['crew_launch_authenticated'])
        self.assertIsNone(r['rex_accepted'])

    def test_deterministic_receipt_serialization(self):
        a=canonical(receipt(**fixture()))
        b=canonical(receipt(**fixture()))
        self.assertEqual(a,b)

    def test_run_reads_real_git_head(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            (base/'event.json').write_text(json.dumps({'pull_request':{'head':{'sha':HEAD}}}))
            (base/'junit.xml').write_bytes(JUNIT)
            env={'GITHUB_EVENT_NAME':'pull_request','GITHUB_SHA':MERGE,
                 'GITHUB_RUN_ID':'12','GITHUB_RUN_ATTEMPT':'1','GITHUB_JOB':'clean-clone'}
            with patch('tools.w72_receipt_provenance.checkout_sha',return_value=HEAD):
                r=run(root=base,event_file=base/'event.json',junit_file=base/'junit.xml',
                      output=base/'receipt.json',cases_output=base/'cases.json',environment=env)
            self.assertEqual(r['source_sha'],HEAD)
            self.assertTrue((base/'cases.json').is_file())
            self.assertEqual(json.loads((base/'receipt.json').read_text())['source_sha'],HEAD)

    def test_run_rejects_stale_real_checkout(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            (base/'event.json').write_text(json.dumps({'pull_request':{'head':{'sha':HEAD}}}))
            (base/'junit.xml').write_bytes(JUNIT)
            env={'GITHUB_EVENT_NAME':'pull_request','GITHUB_SHA':MERGE,
                 'GITHUB_RUN_ID':'12','GITHUB_RUN_ATTEMPT':'1','GITHUB_JOB':'clean-clone'}
            with patch('tools.w72_receipt_provenance.checkout_sha',return_value=OTHER):
                with self.assertRaises(ValueError):
                    run(root=base,event_file=base/'event.json',junit_file=base/'junit.xml',
                        output=base/'receipt.json',cases_output=base/'cases.json',environment=env)
            self.assertFalse((base/'receipt.json').exists())

    def test_missing_git_proof_rejected(self):
        with patch('subprocess.check_output',return_value='not-a-sha'):
            with self.assertRaises(ValueError):
                checkout_sha(Path('.'))

if __name__=='__main__':
    unittest.main()
