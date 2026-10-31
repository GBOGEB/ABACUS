"""Fail-closed, native zero-network census and dashboard verification."""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest
import zipfile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import census
import render

SHA_A = 'a'*40
SHA_B = 'b'*40


class FakeClient:
    def __init__(self, change_head=False, reject_review=False, missing_counts=False):
        self.token = ''
        self.calls = []
        self.change_head = change_head
        self.reject_review = reject_review
        self.missing_counts = missing_counts
        self.head_reads = 0

    def get(self, path: str, allow_list=False):
        self.calls.append(path)
        if path.endswith('/git/ref/heads/main'):
            self.head_reads += 1
            return {'object': {'sha': SHA_B if self.change_head and self.head_reads > 1 else SHA_A}}
        if path.endswith('/issues/1860'):
            return {'body': '- [x] completed\n- [ ] pending\n- [ ] blocked'}
        if path.endswith('/issues/977'):
            return {'body': '- [ ] pending\n- [ ] blocked'}
        if path.endswith('/issues/1929'):
            return {'state': 'open'}
        if '/contents/tools/' in path:
            front=json.loads((ROOT/'source_frontier.json').read_text())
            found=next((x for x in front['candidates'] if x['paths'][0] in path),None)
            return {'sha':found['blob_sha'] if found else 'unmatched'}
        if '/search/issues' in path:
            if self.missing_counts and 'closed' in path:
                raise census.CensusError('simulated rate limit')
            return {'total_count': 38 if 'open' in path else 267}
        if '/rulesets/24494381' in path:
            return {'rules':[{'type':'pull_request','parameters':{'required_approving_review_count':0,
                      'require_last_push_approval':False,'required_review_thread_resolution':False}}],
                    'bypass_actors':[{}]*6}
        if '/pulls/' in path and '/reviews' in path:
            if self.reject_review:
                raise census.CensusError('review permission denied')
            return [{'state':'COMMENTED','user':{'login':'security-bot'}}]
        if '/pulls/' in path:
            number=int(path.rsplit('/',1)[1])
            return {'merged_at':'2026-10-18T15:25:00Z','head':{'sha':SHA_A},
                    'merge_commit_sha':SHA_B,'html_url':f'https://github.com/GBOGEB/ABACUS/pull/{number}'}
        if path.endswith('/actions/workflows?per_page=100'):
            return {'workflows':[{'name':census.PRIMARY['b0'],'id':1711},
                                 {'name':census.PRIMARY['a10'],'id':1777}]}
        if '/actions/workflows/1711/runs?' in path:
            return {'workflow_runs':[{'id':1811,'head_sha':SHA_A,'status':'completed','conclusion':'success',
                    'html_url':'https://github.com/GBOGEB/ABACUS/actions/runs/1811','created_at':'2026-10-18T15:55:00Z','run_attempt':1},
                    {'id':1810,'head_sha':SHA_B,'status':'completed','conclusion':'success','created_at':'2026-10-18T16:00:00Z'}]}
        if '/actions/workflows/1777/runs?' in path:
            return {'workflow_runs':[{'id':1855,'head_sha':SHA_A,'status':'queued','conclusion':None,
                    'html_url':'https://github.com/GBOGEB/ABACUS/actions/runs/1855','created_at':'2026-10-18T15:56:00Z'}]}
        if '/actions/runs/1811/jobs?' in path:
            return {'jobs':[{'name':'B0 producer','conclusion':'success','status':'completed'},
                            {'name':'DAB proposal worker A','conclusion':'success','status':'completed'}]}
        if '/actions/runs/1811/artifacts?' in path:
            return {'artifacts':[]}
        raise census.CensusError('Unexpected path: '+path)


class CensusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline=json.loads((ROOT/'evidence.json').read_text(encoding='utf-8'))

    def test_renderer_cli_can_build_source_bound_offline_html(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            baseline=Path(directory)/'snap.json'
            output=Path(directory)/'dashboard.html'
            baseline.write_text(json.dumps(self.baseline), encoding='utf-8')
            render.main(['--snapshot',str(baseline), '--template',str(ROOT/'index.template.html'), '--output',str(output)])
            content=output.read_text(encoding='utf-8')
            self.assertIn('adaptive-wave',content)
            self.assertIn('"wave_metrics"',content)
            self.assertIn('NO MAIN SCALE PROMOTION',content)

    def test_live_collect_adds_source_bound_wave_metrics(self):
        doc=census.collect(FakeClient(),self.baseline)
        wave=doc['wave_metrics']
        self.assertEqual(wave['historical_focus']['remaining_uncovered_opportunities'],0)
        self.assertEqual(wave['historical_focus']['gain_rate_trend'],'DECELERATING_GAIN')
        self.assertEqual(wave['scale_policy']['read_only_parallel_lanes_max'],1)
        self.assertIsNone(wave['scale_policy']['governed_merge_credit'])

    def test_source_scout_does_not_infer_current_coverage(self):
        d=census.collect(FakeClient(),self.baseline)
        rows=d['source_frontier']['candidates']
        self.assertEqual(len(rows),3)
        self.assertTrue(all(r['status']=='UNCHANGED_SOURCE_BLOB_ONLY_COVERAGE_STALE' for r in rows))
        self.assertTrue(all(r['coverage_current_main_accepted'] is None for r in rows))

    def test_scout_rank_has_three_independent_paths(self):
        import wave_metrics
        doc=json.loads((ROOT/'source_frontier.json').read_text())
        p=wave_metrics.rank_source_slices(doc['candidates'])
        self.assertEqual(len(p['qualified_readonly_candidates']),3)
        self.assertEqual(sum(x['uncovered'] for x in p['qualified_readonly_candidates']),374)
        self.assertFalse(p['source_write_permitted'])

    def test_valid_sha_requires_exact_full_hash(self):
        self.assertEqual(census.check_sha(SHA_A),SHA_A)
        for sha in [None,'123','z'*40,'A'*40]:
            with self.subTest(sha=sha),self.assertRaises(census.CensusError):
                census.check_sha(sha)

    def test_checklist_missing_not_zero(self):
        self.assertEqual(census.checklist(None),(None,None))
        self.assertEqual(census.checklist('- [x] yes\n- [ ] no'),(1,2))
        self.assertEqual(census.checklist('- [ ] one\n- [ ] two'),(0,2))

    def test_ratio_validates_denominator(self):
        self.assertEqual(census.ratio(52,208),25)
        self.assertIsNone(census.ratio(0,0))
        with self.assertRaises(census.CensusError):census.ratio(209,208)

    def test_live_census_does_not_promote_old_coverage(self):
        d=census.collect(FakeClient(),self.baseline,now='2026-10-18T18:00:00Z')
        self.assertEqual(d['main']['sha'],SHA_A)
        self.assertTrue(d['main']['head_stable'])
        self.assertEqual(d['coverage']['measured']['sha'],self.baseline['coverage']['measured']['sha'])
        self.assertEqual(d['coverage']['measured']['status'],'MEASURED_OLDER_MAIN_SHA')
        self.assertEqual(d['workflows']['b0']['id'],1811)
        self.assertEqual(d['workflows']['a10']['conclusion'],None)
        self.assertEqual(d['workers']['native_b0_proposal_jobs'],1)
        self.assertIsNone(d['workers']['authenticated_dispatch_ids'])
        self.assertIsNone(d['issues']['accepted_roots_closed'])
        self.assertIsNone(d['governance']['first_correctly_admitted_pr'])
        self.assertEqual(d['governance']['merge_admission'],'HOLD')

    def test_old_other_head_run_not_accepted(self):
        d=census.collect(FakeClient(),self.baseline)
        self.assertEqual(d['workflows']['b0']['id'],1811)
        self.assertEqual(d['workflows']['b0']['sha'],SHA_A)

    def test_a_b_a_detects_main_mutation(self):
        d=census.collect(FakeClient(change_head=True),self.baseline)
        self.assertFalse(d['main']['head_stable'])
        self.assertEqual(d['main']['sha_after'],SHA_B)
        self.assertIn('HEAD_MOVED_DURING_CENSUS',json.dumps(d['census_errors']))
        self.assertEqual(d['coverage']['measured']['status'],'STALE_OR_UNQUALIFIED_HEAD_MOVE')
        self.assertEqual(d['governance']['merge_admission'],'HOLD')

    def test_missing_issue_count_is_not_zero(self):
        d=census.collect(FakeClient(missing_counts=True),self.baseline)
        self.assertIsNone(d['issues']['closed'])
        self.assertIsNone(d['issues']['total'])
        self.assertEqual(d['census_quality'],'PARTIAL_OR_UNVERIFIED_READBACK')

    def test_missing_review_is_unknown_not_approval(self):
        d=census.collect(FakeClient(reject_review=True),self.baseline)
        self.assertIsNone(d['prs'][0]['approvals'])
        self.assertIsNone(d['governance']['first_correctly_admitted_pr'])

    def test_commented_review_cannot_become_approval(self):
        d=census.collect(FakeClient(),self.baseline)
        self.assertEqual(d['prs'][0]['approvals'],0)
        self.assertEqual(d['governance']['required_approvals'],0)
        self.assertEqual(d['governance']['required_check_rules'],0)

    def test_canonical_artifact_rejects_mismatched_sha(self):
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('canonical-contexts.json',
                '{"meta":{"branch_coverage": true},"files":{},"totals":{"num_statements": 8,"covered_lines": 7,"num_branches":2,"covered_branches":1}}')
            z.writestr('canonical-test-evidence.json',json.dumps({'exact_sha':SHA_B,'ratchet_status':'PASS','outcomes':{'pass':3,'skip':0}}))
            z.writestr('canonical-junit.xml','<testsuites/>')
        with self.assertRaisesRegex(census.CensusError,'SHA mismatches'):
            census.native_artifact_metrics(buffer.getvalue(),SHA_A,None)

    def test_canonical_artifact_reads_fixed_totals(self):
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('canonical-contexts.json',
                '{"meta":{"branch_coverage": true},"files":{},"totals":{"num_statements": 8,"covered_lines": 7,"num_branches":2,"covered_branches":1}}')
            z.writestr('canonical-test-evidence.json',json.dumps({'exact_sha':SHA_A,'ratchet_status':'PASS','outcomes':{'pass':3,'skip':0}}))
            z.writestr('canonical-junit.xml','<testsuites/>')
        raw=buffer.getvalue(); sha=hashlib.sha256(raw).hexdigest()
        got=census.native_artifact_metrics(raw,SHA_A,'sha256:'+sha)
        self.assertEqual(got['percent'],80.0)
        self.assertEqual(got['covered_opportunities'],8)
        self.assertEqual(got['total_opportunities'],10)

    def test_zip_digest_mismatch_fails(self):
        with self.assertRaisesRegex(census.CensusError,'SHA-256 mismatch'):
            census.native_artifact_metrics(b'abc',SHA_A,'sha256:'+'0'*64)

    def test_template_is_self_contained_and_non_executable_json(self):
        t=(ROOT/'index.template.html').read_text(encoding='utf-8')
        baseline=dict(self.baseline,main={'sha':SHA_A}, dangerous='</script><script>alert(1)</script>')
        html=render.render(baseline,t)
        self.assertNotIn('</script><script>alert(1)',html)
        self.assertIn('\\u003c/script\\u003e',html)
        self.assertIn('id="coverageChart"',html)
        self.assertIn('id="refreshBtn"',html)
        self.assertIn('index.template',str(ROOT/'index.template.html'))

    def test_source_shas_do_not_confuse_main_with_measurement(self):
        self.assertNotEqual(self.baseline['main']['sha'],self.baseline['coverage']['measured']['sha'])
        self.assertIsNone(self.baseline['issues']['accepted_roots_closed'])
        self.assertIsNone(self.baseline['coverage']['historical']['accepted_uplift_pp'])
        self.assertIsNone(self.baseline['governance']['negative_canary_rejected'])

    def test_lanes_have_nonoverlapping_authority_classes(self):
        lanes=self.baseline['next_wave']['lanes']
        ids=[x['id'] for x in lanes]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertEqual(sum(x['parallel_group']=='ADMIN_ONLY' for x in lanes),1)
        self.assertEqual(sum(x['parallel_group']=='NO_REMOTE_MUTATION' for x in lanes),1)
        self.assertTrue(all(x['evidence'].startswith('https://github.com/') for x in lanes))

if __name__=='__main__':unittest.main()
