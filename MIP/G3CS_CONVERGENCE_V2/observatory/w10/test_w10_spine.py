"""Local negative tests; do not assert authenticated GitHub execution."""
import hashlib, json, unittest, importlib.util
import pytest
from pathlib import Path
from zipfile import ZipFile
import io
from tempfile import TemporaryDirectory
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parent

def _sibling_module(name):
    path=ROOT / (name + '.py')
    spec=importlib.util.spec_from_file_location('g3cs_w10_' + name, path)
    if spec is None or spec.loader is None:
        raise ImportError('Required W10 sibling source missing: ' + name)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

render=_sibling_module('build_global_spine_w10')
refresh=_sibling_module('refresh_w10_spine')
SHA='2b68462d6578fd435a6f22e750b4d4e7855c2195'
class GlobalSpineW10Tests(unittest.TestCase):
 def setUp(self):self.h=json.loads((ROOT/'W10_FROZEN_HISTORY.json').read_text())
 def test_issue_reconciliation(self):
  h=render.checked_history(self.h)
  x=h['clocks']['issues'][-1]
  self.assertEqual((x['total_closed'],x['total_open'],x['total_issues']),(373,105,478))
 def test_false_issue_closure_rejected(self):
  self.h['clocks']['issues'][-1]['repos'][0]['issue_open']=37
  with self.assertRaisesRegex(ValueError,'issue counts'):render.checked_history(self.h)
 def test_workflow_population_conservation(self):
  d=render.checked_history(self.h)
  for x in d['clocks']['main_ci']:self.assertEqual(sum(x[k] for k in ('success','failure','cancelled','other')),x['total'])
 def test_workflow_forgery_rejected(self):
  self.h['clocks']['main_ci'][-1]['success']=25
  with self.assertRaisesRegex(ValueError,'workflow'):render.checked_history(self.h)
 def test_missing_current_main_coverage_is_null(self):
  self.assertIsNone(self.h['clocks']['main_coverage'][-1]['covered'])
 def test_earlier_uncovered_exact_integer_axis(self):
  html=render.chart_svg()
  self.assertIn('17,036',html);self.assertIn('17,046',html);self.assertIn('17,025',html)
  self.assertNotIn('17k',html)
  self.assertIn('256',html) # first point safely inset from y-axis at x=112
 def test_future_is_explicit_hypothetical(self):
  self.assertIn('HYPOTHETICAL_TARGET_NOT_STATISTICAL_FORECAST',json.dumps(self.h))
 def test_three_repo_source_ownership_distinct(self):
  self.assertEqual(set(x['repo'] for x in self.h['source_registry']),set(refresh.REPOS))
 def test_no_authentication_claim(self):
  self.assertEqual(self.h['governance']['merge_admission'],'HOLD')
  self.assertFalse(self.h['governance']['authority_transfer'])
 def test_ci_duplicate_native_run_rejected(self):
  x={'head_sha':SHA,'event':'push','id':12,'run_attempt':1,'status':'completed','conclusion':'success'}
  with self.assertRaisesRegex(refresh.EvidenceError,'duplicated'):refresh.complete_ci_runs([x,x],SHA)
 def test_ci_unfinished_unknown_not_green(self):
  x={'head_sha':SHA,'event':'push','id':12,'run_attempt':1,'status':'in_progress','conclusion':None}
  with self.assertRaisesRegex(refresh.EvidenceError,'nonterminal'):refresh.complete_ci_runs([x],SHA)
 def test_ci_terminal_ratios(self):
  x=[{'head_sha':SHA,'event':'push','id':i,'run_attempt':1,'status':'completed','conclusion':v} for i,v in ((1,'success'),(2,'failure'),(3,'cancelled'))]
  d=refresh.complete_ci_runs(x,SHA)
  self.assertEqual((d['success'],d['failure'],d['cancelled'],d['total']),(1,1,1,3))
 def test_negative_denominator_rejected(self):
  with self.assertRaises(refresh.EvidenceError):refresh.count_pair(-1,30)
 def test_wrong_hash_of_canonical_archive_rejected(self):
  with self.assertRaisesRegex(refresh.EvidenceError,'SHA256'):refresh.parse_canonical_zip(b'not a zip',SHA,42,123,'sha256:'+'0'*64)
 @pytest.mark.TEST_BLOCKED_SOURCE_MISSING
 def test_native_zip_success_and_sha_guard(self):
  archive=ROOT/'b0-pr2239.zip'
  if not archive.exists():self.skipTest("TEST_BLOCKED_SOURCE_MISSING: historical GitHub B0 ZIP is not in source checkout; synthetic parser invariant tests remain active")
  zipbytes=archive.read_bytes()
  digest='sha256:'+hashlib.sha256(zipbytes).hexdigest()
  d=refresh.parse_canonical_zip(zipbytes,SHA,12142769026,39144589287,digest)
  self.assertEqual((d['covered'],d['eligible'],d['uncovered']),(35183,52221,17038))
  with self.assertRaisesRegex(refresh.EvidenceError,'another source'):refresh.parse_canonical_zip(zipbytes,'a'*40,12142769026,39144589287,digest)
 def test_positive_native_zip_from_synthetic_receipt(self):
  sha='2b68462d6578fd435a6f22e750b4d4e7855c2195'
  payload=io.BytesIO()
  contexts={'totals':{'covered_lines':4,'num_statements':7,'covered_branches':1,'num_branches':4}}
  evidence={'exact_sha':sha,'outcomes':{'pass':3,'skip':1}}
  with ZipFile(payload,'w') as z:
   z.writestr('canonical-contexts.json',json.dumps(contexts))
   z.writestr('canonical-test-evidence.json',json.dumps(evidence))
  archive=payload.getvalue()
  digest='sha256:'+hashlib.sha256(archive).hexdigest()
  result=refresh.parse_canonical_zip(archive,sha,42,123,digest)
  self.assertEqual((result['covered'],result['eligible'],result['uncovered']),(5,11,6))
  self.assertEqual(result['test_passed'],3)
  with self.assertRaisesRegex(refresh.EvidenceError,'SHA256 differs'):
   refresh.parse_canonical_zip(archive,sha,42,123,'sha256:'+'0'*64)
  with self.assertRaisesRegex(refresh.EvidenceError,'another source'):
   refresh.parse_canonical_zip(archive,'a'*40,42,123,digest)
 def test_no_fake_reset_from_browser_import(self):
  text=(ROOT/'index.html').read_text(encoding='utf8')
  self.assertIn('source-reported/unverified',text)
  self.assertIn('verified_browser_imports:false',text)
  self.assertIn('codepurple.spine.w10.snapshot.v1',text)
 def test_immutable_green_main_comparison(self):
  c=self.h['clocks']['main_coverage']
  self.assertEqual((c[0]['uncovered'],c[1]['uncovered']),(17036,17046))
  self.assertEqual(c[1]['covered']-c[0]['covered'],636)

 def test_new_main_epoch_append_only(self):
  html=render.w11_native_main_panel(self.h)
  self.assertIn('67.758%',html)
  self.assertIn('67.345%',html)
  self.assertIn('16,926',html)
  self.assertIn('N+1 conditional',html)
  self.assertIn('Governed admission HOLD',html)
 def _bad_native_epoch(self,mutate,phrase):
  from unittest import mock
  import tempfile
  with tempfile.TemporaryDirectory() as folder:
   old=json.loads((ROOT/'W11_OBSERVED_MAIN_EPOCH.json').read_text())
   mutate(old)
   Path(folder,'W11_OBSERVED_MAIN_EPOCH.json').write_text(json.dumps(old))
   with mock.patch.object(render,'BASE',Path(folder)):
    with self.assertRaisesRegex(ValueError,phrase):render.w11_native_main_panel(self.h)
 def test_epoch_rejects_fake_admission(self):
  self._bad_native_epoch(lambda x:x['governance'].update(merge_admission='PASS'),'governance')
 def test_epoch_rejects_falsified_scope_denominator(self):
  self._bad_native_epoch(lambda x:x['measurements'][1]['combined'].update(eligible=50000),'inconsistent')
 def test_epoch_rejects_fake_covered_delta(self):
  self._bad_native_epoch(lambda x:x['comparison'].update(covered_delta=999),'conservation')
 def test_epoch_rejects_statistical_prediction(self):
  self._bad_native_epoch(lambda x:x['next_conditional'].update(classification='PREDICTED'),'conditional')

if __name__=='__main__':unittest.main()