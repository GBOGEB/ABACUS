"""Adversarial tests for source-bound B0 scope separation."""
import copy
import json
from pathlib import Path
import zipfile
import pytest

from scripts.cbd_b0_scope_comparison import compare, stats, suite_summary, TARGETS

A = 'a'*40
ID = {'head_sha': A, 'run_id': 7, 'attempt': 1, 'canonical_job_id': 12,
      'report_job_id': 13, 'canonical_artifact_id': 21, 'report_artifact_id': 22}


def cov(lines=(163,104), branches=(50,37), timestamp='2026-10-17T10:10:51Z'):
    return {'meta':{'timestamp':timestamp,'branch_coverage':True},'files':{
        p:{'summary':{'covered_lines':lines[i], 'num_statements':(165,104)[i],
                      'covered_branches':branches[i], 'num_branches':(56,38)[i]}}
        for i,p in enumerate(TARGETS)}}


def junit(n='2'):
    return (f'<testsuites><testsuite tests="{n}" time="1" '
            'timestamp="2026-10-17T10:10:49Z"><testcase/>'
            '<testcase/></testsuite></testsuites>')


def receipt(c=None,r=None,j=None,identity=None):
    return compare(c if c is not None else cov(),
                   r if r is not None else cov((0,0),(0,0),'2026-10-17T10:06:20Z'),
                   j if j is not None else junit(),
                   identity if identity is not None else ID)


def test_canonical_not_report_is_authority_for_observed_coverage():
    x=receipt()
    assert x['canonical_scope']['combined']==[354,363]
    assert x['canonical_scope']['statements']==[267,269]
    assert x['canonical_scope']['branches']==[87,94]
    assert x['report_only_scope']['statements']==[0,269]
    assert x['contrast_is_not_time_series'] is True
    assert x['accepted_temporal_coverage_delta'] is None
    assert x['merge_admission']=='HOLD'


def test_different_job_same_run_both_bound_by_declared_identity():
    x=receipt()
    assert x['canonical_scope']['job_id'] != x['report_only_scope']['job_id']
    assert x['native_refs_are_caller_declared'] is True


def test_stale_canonical_scope_holds_even_when_report_only_is_earlier():
    x=receipt(c=cov(timestamp='2026-10-17T10:10:45Z'))
    assert x['measurement_state']=='HOLD_CANONICAL_EVIDENCE_STALE'


def test_cross_scope_not_temporal_even_if_canonical_is_greater():
    x=receipt()
    assert x['cross_scope_statement_contrast']==267
    assert x['cross_scope_branch_contrast']==87
    assert x['accepted_temporal_coverage_delta'] is None


@pytest.mark.parametrize('bad', [True,-1,166,'1',None])
def test_invalid_numerators_fail(bad):
    c=cov()
    c['files'][TARGETS[0]]['summary']['covered_lines']=bad
    with pytest.raises(ValueError):receipt(c=c)


def test_changed_denominators_rejected():
    r=cov((0,0),(0,0))
    r['files'][TARGETS[0]]['summary']['num_statements']=166
    with pytest.raises(ValueError, match='denominators'):receipt(r=r)


@pytest.mark.parametrize('field,bad', [
    ('run_id',True),('attempt',0),('canonical_job_id',None),('report_artifact_id','21'),
])
def test_bad_run_identity_rejected(field,bad):
    identity=dict(ID,**{field:bad})
    with pytest.raises(ValueError):receipt(identity=identity)


def test_identical_job_ids_rejected():
    with pytest.raises(ValueError,match='distinct job'):
        receipt(identity=dict(ID,report_job_id=12))


def test_junit_header_mismatch_is_reported_not_fabricated():
    x=receipt(j=junit(n='14'))
    assert x['junit']['header_minus_elements']==12
    assert x['junit']['count_integrity']=='MISMATCH'
    assert x['merge_admission']=='HOLD'


def test_missing_file_is_error():
    c=cov()
    c['files'].pop(TARGETS[0])
    with pytest.raises(ValueError):receipt(c=c)


def test_junit_bad_duration_rejected():
    with pytest.raises(ValueError):
        receipt(j=junit().replace('time="1"','time="nan"'))


def test_real_native_artifacts_replay_if_supplied():
    canonical=Path('/mnt/data/b0-canonical-89dc0989.zip')
    report=Path('/mnt/data/b0-admission-89dc0989.zip')
    if not canonical.exists() or not report.exists():
        pytest.skip('native artifact copies not locally available')
    with zipfile.ZipFile(canonical) as z:
        c=json.loads(z.read('canonical-contexts.json'))
        j=z.read('canonical-junit.xml').decode()
    with zipfile.ZipFile(report) as z:
        rr=json.loads(z.read('b0/coverage-contexts.json'))
    x=receipt(c=c,r=rr,j=j)
    assert x['canonical_scope']['combined']==[354,363]
    assert x['junit']['header_minus_elements']==12
    assert x['measurement_state']=='SCOPED_CANONICAL_AFTER_TEST'
