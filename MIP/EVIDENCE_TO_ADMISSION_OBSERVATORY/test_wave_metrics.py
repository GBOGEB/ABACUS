"""MIP negative, reverse, fault-injection and scaling policy tests."""
from __future__ import annotations
import copy
import importlib.util
import json
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('wave_metrics', ROOT/'wave_metrics.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class WaveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.history = json.loads((ROOT/'wave_history.json').read_text())
        cls.snapshot = json.loads((ROOT/'evidence.json').read_text())

    def test_history_real_contract(self):
        got=m.matched_progress(self.history['observations'])
        self.assertEqual(len(got['observations']),3)
        self.assertEqual([p['native_test_executions'] for p in got['observations']],[120,244,252])
        self.assertEqual([p['covered'] for p in got['observations']],[192,206,208])
        self.assertEqual([p['uncovered'] for p in got['observations']],[16,2,0])
        self.assertEqual(got['gain_rate_trend'],'DECELERATING_GAIN')
        self.assertTrue(got['ceiling_reached'])
        self.assertEqual(got['observations'][1]['wave_span'],2)
        self.assertEqual(got['observations'][2]['wave_span'],1)
        self.assertAlmostEqual(got['observations'][1]['gain_pp_per_wave'],3.365385,places=5)
        self.assertAlmostEqual(got['observations'][2]['gain_pp_per_wave'],0.961538,places=5)
        self.assertIsNone(got['repository_main_coverage_uplift'])

    def test_policy_current_stale_conservative(self):
        p=m.adaptive_slice_policy(self.snapshot,m.matched_progress(self.history['observations']))
        self.assertEqual(p['read_only_parallel_lanes_max'],1)
        self.assertFalse(p['source_mutation_enabled'])
        self.assertEqual(p['merge_admission'],'HOLD')
        self.assertIn('CURRENT_MAIN_COVERAGE_ARTIFACT_MISSING',p['measurement_blockers'])
        self.assertIn('OWNER_GITHUB_RULES_NOT_ENFORCED',p['admission_blockers'])
        self.assertEqual(p['next_slice'],'NEXT_DISTINCT_SOURCE_FAMILY_OR_DIFF_COHORT')
        self.assertIsNone(p['predicted_coverage_pp'])

    def test_policy_three_readonly_lanes_when_source_evidence_complete(self):
        doc=copy.deepcopy(self.snapshot)
        doc['main']['head_stable']=True
        doc['workflows']['b0']['sha']=doc['main']['sha']
        doc['workflows']['b0']['status']='completed'
        doc['workflows']['b0']['conclusion']='success'
        doc['coverage']['measured']['sha']=doc['main']['sha']
        doc['coverage']['measured']['status']='MEASURED_ON_EXACT_MAIN_SHA'
        doc['census_errors']=[]
        doc['workflows']['b0']['queue_p95_seconds']=120
        policy=m.adaptive_slice_policy(doc,m.matched_progress(self.history['observations']))
        self.assertEqual(policy['read_only_parallel_lanes_max'],3)
        self.assertEqual(policy['merge_admission'],'HOLD')
        self.assertFalse(policy['source_mutation_enabled'])

    def test_stable_main_unknown_disallowed(self):
        d=copy.deepcopy(self.snapshot);d['main']['head_stable']=None
        p=m.adaptive_slice_policy(d,m.matched_progress(self.history['observations']))
        self.assertIn('A_B_A_MAIN_UNVERIFIED',p['measurement_blockers'])

    def test_queue_high_decellerates_parallel_scouts(self):
        d=copy.deepcopy(self.snapshot)
        d['main']['head_stable']=True
        d['workflows']['b0'].update(sha=d['main']['sha'],status='completed',conclusion='success',queue_p95_seconds=1200)
        d['coverage']['measured'].update(sha=d['main']['sha'],status='MEASURED_ON_EXACT_MAIN_SHA')
        d['census_errors']=[]
        p=m.adaptive_slice_policy(d,m.matched_progress(self.history['observations']))
        self.assertEqual(p['read_only_parallel_lanes_max'],1)
        self.assertIn('RUNNER_QUEUE_P95_ABOVE_900_SECONDS',p['measurement_blockers'])

    def test_queue_unknown_does_not_fake_headroom(self):
        d=copy.deepcopy(self.snapshot)
        d['main']['head_stable']=True
        d['workflows']['b0'].update(sha=d['main']['sha'],status='completed',conclusion='success')
        d['workflows']['b0'].pop('queue_p95_seconds',None)
        d['coverage']['measured'].update(sha=d['main']['sha'],status='MEASURED_ON_EXACT_MAIN_SHA')
        d['census_errors']=[]
        p=m.adaptive_slice_policy(d,m.matched_progress(self.history['observations']))
        self.assertEqual(p['read_only_parallel_lanes_max'],1)
        self.assertIn('RUNNER_QUEUE_P95_UNKNOWN',p['measurement_blockers'])

    def test_rank_disjoint_scoped_candidates(self):
        base={'eligible':90,'source_sha':'a'*40}
        rows=[dict(base,family='A',paths=['a.py'],uncovered=70,first_red=True),
              dict(base,family='B',paths=['b.py','c.py'],uncovered=50),
              dict(base,family='C',paths=['d.py'],uncovered=0)]
        d=m.rank_source_slices(rows)
        self.assertEqual([r['family'] for r in d['qualified_readonly_candidates']],['A','B'])
        self.assertEqual(d['max_disjoint_candidates'],2)
        self.assertFalse(d['source_write_permitted'])
        self.assertEqual(d['withheld'][0]['reason'],'MEASURED_COHORT_AT_CEILING')

    def test_overlap_and_missing_candidates_withheld(self):
        a={'eligible':10,'uncovered':7,'source_sha':'a'*40}
        rows=[dict(a,family='ONE',paths=['same.py']),dict(a,family='TWO',paths=['same.py']),
              dict(a,family='THREE',paths=['other.py'],eligible=None)]
        d=m.rank_source_slices(rows)
        self.assertEqual([x['reason'] for x in d['withheld']],['OVERLAPPING_SOURCE_LEASE','MISSING_COMPARABLE_SOURCE_METRIC'])

    def test_traversal_and_wide_lease_not_qualified(self):
        x={'eligible':10,'uncovered':8,'source_sha':'a'*40}
        d=m.rank_source_slices([dict(x,family='BAD',paths=['../outside.py']),
                                dict(x,family='WIDE',paths=['x.py','y.py','z.py'])])
        self.assertEqual(d['qualified_readonly_candidates'],[])
        self.assertEqual(len(d['withheld']),2)

    def test_invalid_candidate_rejected(self):
        for sample in [None,3,{}]:
            with self.subTest(sample=sample):
                with self.assertRaises(m.ProofError):m.rank_source_slices([sample])

    def test_no_candidate_not_zero_roots(self):
        got=m.rank_source_slices([])
        self.assertEqual(got['max_disjoint_candidates'],0)
        self.assertIsNone(got['remote_worker_launches'])

    def test_zero_root_closed_is_not_inferred(self):
        p=m.adaptive_slice_policy(self.snapshot,m.matched_progress(self.history['observations']))
        self.assertIsNone(p['accepted_causal_root_closed'])

    def test_wave_command_line_writes_deterministic_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp=Path(directory)
            b=tmp/'baseline.json';h=tmp/'history.json';out=tmp/'out.json'
            b.write_text(json.dumps(self.snapshot));h.write_text(json.dumps(self.history))
            self.assertEqual(m.main(['--snapshot',str(b),'--history',str(h),'--out',str(out)]),0)
            r=json.loads(out.read_text())
            self.assertEqual(r['historical_focus']['remaining_uncovered_opportunities'],0)
            self.assertEqual(r['scale_policy']['read_only_parallel_lanes_max'],1)
            self.assertFalse(r['scale_policy']['source_mutation_enabled'])

    def test_source_slice_accepts_first_red_even_if_less_opportunity_density(self):
        sample={'eligible':100,'source_sha':'a'*40}
        r=m.rank_source_slices([dict(sample,family='RISK',uncovered=2,paths=['root.py'],first_red=True),
                               dict(sample,family='COVERAGE',uncovered=90,paths=['wide.py'])])
        self.assertEqual([x['family'] for x in r['qualified_readonly_candidates']],['RISK','COVERAGE'])

    def test_invalid_candidate_scope_bounds(self):
        with self.assertRaisesRegex(m.ProofError,'max_source_paths'):
            m.rank_source_slices([],0)
        with self.assertRaisesRegex(m.ProofError,'Candidates'):
            m.rank_source_slices(None)

    def test_full_receipt_build(self):
        result=m.build_wave_receipt(self.snapshot,self.history)
        self.assertEqual(result['main_sha'],self.snapshot['main']['sha'])
        self.assertIn('/1929',result['root_census_owner'])
        self.assertEqual(result['scale_policy']['measurement_frontier_qualified'],False)

    def test_single_pulse_no_fake_trend(self):
        d=m.matched_progress(self.history['observations'][:1])
        self.assertEqual(d['gain_rate_trend'],'INSUFFICIENT_MATCHED_PULSES')
        self.assertIsNone(d['rate_change_pp_per_wave'])

    def test_reverse_pressure_negative_gain_is_reported_not_hidden(self):
        h=copy.deepcopy(self.history['observations'])
        h[2]['covered_opportunities']=180
        d=m.matched_progress(h)
        self.assertLess(d['observations'][-1]['delta_pp'],0)
        self.assertEqual(d['gain_rate_trend'],'DECELERATING_GAIN')

    def test_incomplete_three_cell_matrix_is_rejected(self):
        h=copy.deepcopy(self.history['observations'])
        h[2]['jobs'].pop()
        with self.assertRaisesRegex(m.ProofError,'nonterminal'):
            m.matched_progress(h)

    def test_cancelled_job_fails_comparison(self):
        h=copy.deepcopy(self.history['observations'])
        h[2]['jobs'][0]['conclusion']='cancelled'
        with self.assertRaisesRegex(m.ProofError,'nonterminal'):
            m.matched_progress(h)

    def test_missing_artifact_rejects_success(self):
        h=copy.deepcopy(self.history['observations'])
        del h[2]['jobs'][0]['artifact_sha256']
        with self.assertRaisesRegex(m.ProofError,'artifact SHA-256'):
            m.matched_progress(h)

    def test_zero_run_id_is_not_execution(self):
        h=copy.deepcopy(self.history['observations'])
        h[1]['run_id']=0
        with self.assertRaisesRegex(m.ProofError,'run_id'):
            m.matched_progress(h)

    def test_nonmatching_job_head_rejected(self):
        h=copy.deepcopy(self.history['observations'])
        h[1]['jobs'][1]['head_sha']='a'*40
        with self.assertRaisesRegex(m.ProofError,'not pinned'):
            m.matched_progress(h)

    def test_duplicate_job_rejected(self):
        h=copy.deepcopy(self.history['observations'])
        h[1]['jobs'][1]['job_id']=h[1]['jobs'][0]['job_id']
        with self.assertRaisesRegex(m.ProofError,'Duplicate'):
            m.matched_progress(h)

    def test_fake_artifact_digest_rejected(self):
        h=copy.deepcopy(self.history['observations'])
        h[1]['jobs'][1]['artifact_sha256']='bad'
        with self.assertRaisesRegex(m.ProofError,'artifact SHA-256'):
            m.matched_progress(h)

    def test_mixed_denominator_rejected(self):
        h=copy.deepcopy(self.history['observations'])
        h[1]['eligible_opportunities']=209
        with self.assertRaisesRegex(m.ProofError,'denominator'):
            m.matched_progress(h)

    def test_mixed_config_rejected(self):
        h=copy.deepcopy(self.history['observations'])
        h[1]['configuration_id']='different'
        with self.assertRaisesRegex(m.ProofError,'config'):
            m.matched_progress(h)

    def test_mixed_cohort_rejected(self):
        h=copy.deepcopy(self.history['observations'])
        h[1]['cohort_id']='another'
        with self.assertRaisesRegex(m.ProofError,'Cohort'):
            m.matched_progress(h)

    def test_over_100_percent_rejected(self):
        h=copy.deepcopy(self.history['observations'])
        h[1]['covered_opportunities']=209
        with self.assertRaisesRegex(m.ProofError,'exceed'):
            m.matched_progress(h)

    def test_missing_sha_rejected(self):
        h=copy.deepcopy(self.history['observations'])
        h[1]['head_sha']=None
        with self.assertRaisesRegex(m.ProofError,'40-character'):
            m.matched_progress(h)

    def test_duplicate_wave_rejected(self):
        h=copy.deepcopy(self.history['observations'])
        h[1]['wave']=1
        with self.assertRaisesRegex(m.ProofError,'order'):
            m.matched_progress(h)

    def test_reordered_waves_rejected(self):
        h=list(reversed(copy.deepcopy(self.history['observations'])))
        with self.assertRaisesRegex(m.ProofError,'order'):
            m.matched_progress(h)

    def test_false_job_success_not_truthy(self):
        h=copy.deepcopy(self.history['observations'])
        h[2]['jobs'][0]['conclusion']=True
        with self.assertRaisesRegex(m.ProofError,'Unexpected job conclusion'):
            m.matched_progress(h)

    def test_failing_receipt_returns_no_executions(self):
        h=copy.deepcopy(self.history['observations'][0])
        h['jobs'][0]['conclusion']='failure'
        result=m.qualify_observation(h)
        self.assertFalse(result['fully_qualified'])
        self.assertIsNone(result['execution_count'])

    def test_unchanged_case_population_zero_yield_without_divide_by_zero(self):
        h=copy.deepcopy(self.history['observations'])
        h[2]['cases_per_job']=h[1]['cases_per_job']
        result=m.matched_progress(h)
        self.assertIsNone(result['observations'][-1]['new_covered_per_added_case'])

    def test_bad_types_rejected(self):
        for value in (False,1.0,'63',None):
            with self.subTest(value=value):
                h=copy.deepcopy(self.history['observations']);h[2]['cases_per_job']=value
                with self.assertRaises(m.ProofError):m.matched_progress(h)

    def test_missing_current_governance_not_approval(self):
        doc=copy.deepcopy(self.snapshot)
        doc['governance']['required_approvals']=None
        policy=m.adaptive_slice_policy(doc,m.matched_progress(self.history['observations']))
        self.assertIn('OWNER_GITHUB_RULES_NOT_ENFORCED',policy['admission_blockers'])


if __name__=='__main__':unittest.main()