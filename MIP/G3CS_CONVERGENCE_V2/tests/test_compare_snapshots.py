"""Positive and adversarial native-run telemetry matching tests."""
from __future__ import annotations
import copy
import importlib.util
import unittest
from pathlib import Path

path=Path(__file__).resolve().parents[1]/'tools/compare_snapshots.py'
spec=importlib.util.spec_from_file_location('g3cs_matcher',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
SHA='a'*40;HASH='b'*64

def fixture():
    return {'schema':module.SCHEMA,'repository':'GBOGEB/ABACUS',
       'source_sha':SHA,'source_clock':'EXACT_PR_HEAD','selection_sha256':HASH,
       'observed_at_utc':'2026-10-18T10:00:00Z','admission':'HOLD','authority_transfer':False,
       'runs':[{'run_id':123,'attempt':1,'source_sha':SHA,'status':'queued','conclusion':None,
           'jobs':[{'job_id':99,'source_sha':SHA,'status':'queued','conclusion':None,
            'created_at':'2026-10-18T09:58:00Z','started_at':None,'completed_at':None}]}]}

class NativeComparatorTests(unittest.TestCase):
    def test_valid_nonterminal_no_zero_inference(self):
        x=module.stats(fixture());self.assertEqual(x['nonterminal'],1)
        self.assertIsNone(x['queue_p95_seconds']);self.assertIsNone(x['terminal_success_pct'])
    def test_same_run_identity_transition_counts(self):
        old=fixture();new=copy.deepcopy(old)
        new['observed_at_utc']='2026-10-18T10:01:00Z'
        new['runs'][0].update(status='completed',conclusion='success')
        new['runs'][0]['jobs'][0].update(status='completed',conclusion='success',
               started_at='2026-10-18T10:00:00Z',completed_at='2026-10-18T10:00:11Z')
        r=module.compare(old,new);self.assertTrue(r['comparable']);self.assertEqual(r['successful_run_delta'],1)
        self.assertEqual(r['blocked_to_success_run_ids'],[123]);self.assertEqual(r['after']['queue_p95_seconds'],120)
        self.assertEqual(r['after']['runtime_p95_seconds'],11)
        self.assertEqual(r['causal_root_closure_credit'],0)
    def test_different_population_not_comparable(self):
        b=fixture();a=copy.deepcopy(b);a['observed_at_utc']='2026-10-18T10:05:00Z'
        a['runs'][0]['run_id']=124
        r=module.compare(b,a);self.assertFalse(r['comparable'])
        self.assertIsNone(r['successful_run_delta'])
    def test_changed_selection_hash_rejected(self):
        b=fixture();a=copy.deepcopy(b);a['observed_at_utc']='2026-10-18T10:05:00Z';a['selection_sha256']='c'*64
        r=module.compare(b,a);self.assertIn('DIFFERENT_SOURCE_OR_SELECTION_CONTEXT',r['reasons'])
    def test_nonmonotone_clock_rejected(self):
        r=module.compare(fixture(),fixture());self.assertFalse(r['comparable'])
    def test_cross_sha_job_rejected(self):
        x=fixture();x['runs'][0]['jobs'][0]['source_sha']='f'*40
        with self.assertRaisesRegex(ValueError,'job has wrong source'):module.validate(x)
    def test_terminal_job_requires_outcome(self):
        x=fixture();x['runs'][0]['jobs'][0].update(status='completed',conclusion=None)
        with self.assertRaisesRegex(ValueError,'job outcome'):module.validate(x)
    def test_pending_run_cannot_have_green_conclusion(self):
        x=fixture();x['runs'][0]['conclusion']='success'
        with self.assertRaisesRegex(ValueError,'terminal status'):module.validate(x)
    def test_repeated_attempt_identity_fails(self):
        x=fixture();x['runs'].append(copy.deepcopy(x['runs'][0]))
        with self.assertRaisesRegex(ValueError,'duplicate run'):module.validate(x)
    def test_clock_negative_duration_fails(self):
        x=fixture();j=x['runs'][0]['jobs'][0];j['started_at']='2026-10-18T09:57:00Z'
        with self.assertRaisesRegex(ValueError,'negative queue'):module.validate(x)
    def test_failed_job_does_not_create_root_closure(self):
        x=fixture();x['runs'][0]['jobs'][0].update(status='completed',conclusion='failure',
            started_at='2026-10-18T10:00:00Z',completed_at='2026-10-18T10:00:02Z')
        m=module.stats(x);self.assertEqual(m['failed_jobs'],1)
        self.assertIsNone(m['causal_roots_closed'])

if __name__=='__main__':unittest.main()
