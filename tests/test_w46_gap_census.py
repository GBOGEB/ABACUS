"""Fail-closed synthetic negative/reverse tests for disjoint gap census."""
from __future__ import annotations
import pytest
from tools.recovery.w46_gap_census import family, rollup

SHA = 'a' * 40


def sample():
    return {'meta': {'branch_coverage': True}, 'files': {
        'DMAIC_V3/a.py': {'summary': {'num_statements': 8, 'covered_lines': 3,
                                     'missing_lines': 5, 'num_branches': 4,
                                     'covered_branches': 1, 'missing_branches': 3}},
        'mission_control_lite/b.py': {'summary': {'num_statements': 10,
                                     'covered_lines': 0, 'missing_lines': 10,
                                     'num_branches': 6, 'covered_branches': 0,
                                     'missing_branches': 6}},
        'DMAIC_V3/c.py': {'summary': {'num_statements': 4, 'covered_lines': 2,
                                     'missing_lines': 2, 'num_branches': 0,
                                     'covered_branches': 0, 'missing_branches': 0}}}}


def test_exact_covered_eligible_and_root_family_no_double_count():
    x = rollup(sample(), head_sha=SHA)
    assert (x['covered'], x['eligible'], x['missing']) == (6, 32, 26)
    assert x['file_count'] == 3 and x['zero_coverage_file_count'] == 1
    assert x['owner_families']['DMAIC_V3']['files'] == 2
    assert len(x['proposed_source_disjoint_lanes']) == 2
    assert not x['source_overlap_in_proposals']
    assert x['merge_admission'] == 'HOLD'


def test_expected_source_totals_must_match():
    x = rollup(sample(), head_sha=SHA)
    correct = {'covered_lines':5,'num_statements':22,'missing_lines':17,
               'covered_branches':1,'num_branches':10,'missing_branches':9}
    assert rollup(sample(), head_sha=SHA, expected_totals=correct)['eligible'] == 32
    wrong = dict(correct, num_statements=23)
    with pytest.raises(ValueError, match='scope / full measurement'):
        rollup(sample(), head_sha=SHA, expected_totals=wrong)


@pytest.mark.parametrize('key,new_value', [('covered_lines',9),('missing_lines',2),
                                            ('num_branches',-1),('covered_branches',True),
                                            ('missing_branches','0')])
def test_tampered_counters_refused(key,new_value):
    x=sample();x['files']['DMAIC_V3/a.py']['summary'][key]=new_value
    with pytest.raises(ValueError, match='counters|population'):
        rollup(x,head_sha=SHA)


@pytest.mark.parametrize('new_path', ['../private.py', 'dir\\inject.py', 'not_code.txt', ''])
def test_foreign_or_unsafe_source_path_refused(new_path):
    x=sample();x['files'][new_path]=x['files'].pop('DMAIC_V3/a.py')
    with pytest.raises(ValueError, match='unsafe or foreign'):
        rollup(x,head_sha=SHA)


def test_missing_branch_mode_rejected():
    x=sample();x['meta']['branch_coverage']=False
    with pytest.raises(ValueError,match='branch coverage'):
        rollup(x,head_sha=SHA)


def test_no_files_is_unknown_not_zero():
    x=sample();x['files']={}
    with pytest.raises(ValueError,match='missing measured'):
        rollup(x,head_sha=SHA)


def test_wrong_head_rejected():
    with pytest.raises(ValueError,match='invalid exact'):
        rollup(sample(),head_sha='z'*40)


def test_no_more_than_proposal_cap():
    x=rollup(sample(),head_sha=SHA,max_lanes=1)
    assert len(x['proposed_source_disjoint_lanes']) == 1
    with pytest.raises(ValueError,match='bounded lane cap'):
        rollup(sample(),head_sha=SHA,max_lanes=11)


def test_namespaces_are_explicit():
    assert family('models/qps_line_s/closure_contract.py') == 'QPS_LINE_S'
    assert family('mission_control_lite/coverage_pulse.py') == 'MISSION_CONTROL_LITE'
    assert family('.github/workflows/thing.py') == 'GITHUB_CI'
    assert family('script.py') == 'ROOT_EXECUTION'
