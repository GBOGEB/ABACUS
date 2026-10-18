"""Negative/reverse and shared-denominator W35 evidence tests."""
import copy
import json
from pathlib import Path
import pytest
from tools.recovery import w35_census_rollup as m

BASE=Path(__file__).resolve().parent/'fixtures'

def sample():
    return json.loads((BASE/'w35_ledger_synthetic.json').read_text(encoding='utf-8'))


def cov(**kwargs):
    z={'scope_sha256':'a'*64,'instrumentor_version':'7.16.2',
       'config_sha256':'b'*64,'source_blob_sha256':'c'*64,
       'eligible_statements':100,'eligible_branches':50,
       'covered_statements':60,'covered_branches':15}
    z.update(kwargs)
    return z


def test_rollup_separates_repeated_cases_from_source_roots():
    r=m.rollup(sample())
    assert r['historical_w34_b0']['numerator']==11
    assert r['historical_w34_b0']['denominator']==13
    assert r['root_census']['manifestations']==11
    assert r['root_census']['source_classified_roots']==2
    assert r['root_census']['unknown_root_groups']==1
    assert r['root_census']['formal_closures'] is None
    assert r['merge_admission']=='HOLD'


def test_w27_reused_denominators_do_not_become_main():
    r=m.rollup(sample())
    assert r['historical_w27_cell_delta_pp']==[46,46,46,46]
    assert r['w27_whole_repo_delta'] is None
    assert r['current_main_coverage'] is None


def test_local_synthetic_not_promoted_to_native():
    r=m.rollup(sample())
    assert r['local_synthetic']=={'numerator':18,'denominator':18,'native_qualification':None}
    assert r['native_qualified_lanes']['numerator']==0


def test_matching_coverage_scope_positive_delta():
    before=cov();after=cov(covered_statements=75,covered_branches=20)
    r=m.qualified_coverage_delta(before,after)
    assert r['covered_delta']==20
    assert r['delta_pp']==round(20/150*100,6)
    assert r['main_coverage_claim'] is False


@pytest.mark.parametrize('field,bad',[
('scope_sha256','d'*64),('instrumentor_version','7.17'),
('config_sha256','e'*64),('source_blob_sha256','f'*64),
('eligible_statements',101),('eligible_branches',60)])
def test_comparison_rejects_unmatched_causal_denominator(field,bad):
    with pytest.raises(ValueError,match='unmatched'):
        m.qualified_coverage_delta(cov(),cov(**{field:bad}))


def test_impossible_coverage_rejected():
    with pytest.raises(ValueError,match='invalid coverage'):
        m.qualified_coverage_delta(cov(),cov(covered_statements=101))


def test_no_forecast_can_claim_approval_when_rules_unproven():
    v=m.decision([],10,False)
    assert v['state']=='HOLD_GOVERNANCE'
    assert v['max_new_native_cells']==0


def test_high_queue_pressure_blocks_even_with_rule_configuration():
    assert m.decision([],13,True)['state']=='HOLD_QUEUE_UNKNOWN_OR_ACTIVE'
    assert m.decision([],None,True)['state']=='HOLD_QUEUE_UNKNOWN_OR_ACTIVE'


def test_insufficient_receipts_not_stability():
    assert m.decision([],0,True)['state']=='HOLD_NO_TERMINAL_PROOF'


def wave(i,gain=0,scope='R'):
    return {'wave_id':'W'+str(i),'head_sha':f'{i:040x}',
            'terminal':True,'bytes_verified':True,'scope_id':scope,
            'marginal_covered_delta':gain}


def test_four_independent_comparable_zero_gain_waves_only_plateau_candidate():
    rows=[wave(i) for i in (1,2,3,4)]
    r=m.decision(rows,0,True)
    assert r['state']=='STOP_LOCAL_PLATEAU_CANDIDATE'
    assert r['stable'] is False
    assert r['six_sigma_capability_qualified'] is False


def test_unequal_scope_or_missing_proof_does_not_claim_plateau():
    rows=[wave(i) for i in (1,2,3,4)];rows[-1]['scope_id']='OTHER'
    assert m.decision(rows,0,True)['state']=='RESET_UNMATCHED_SCOPE'
    rows[-1]['scope_id']='R';rows[-1]['bytes_verified']=False
    assert m.decision(rows,0,True)['state']=='HOLD_NO_TERMINAL_PROOF'


def test_one_wave_with_gain_is_not_asymptotic_convergence():
    rows=[wave(1),wave(2),wave(3,gain=2),wave(4)]
    assert m.decision(rows,0,True)['state']=='ALLOW_BOUNDED_SOURCE_DISJOINT_PROBE'


@pytest.mark.parametrize('mutate,match',[
 (lambda z: z.update(schema='other'),'unsupported ledger'),
 (lambda z: z.update(merge_admission='PASS'),'cannot confer merge'),
 (lambda z: z.update(main_sha='bad'),'invalid main SHA'),
 (lambda z: z['repositories'].pop(),'invalid repo census'),
 (lambda z: z['repositories'][0].update(sha='bad'),'unknown repository'),
 (lambda z: z['repositories'][0].update(level='QPS_ACCEPTED'),'foreign repo authority'),
 (lambda z: z['governance'].update(security_waiver=True),'unauthorized security'),
 (lambda z: z['cohorts']['w34_canonical_b0_jobs'].update(failed=3),'B0 job population'),
 (lambda z: z['cohorts']['w34_canonical_b0_jobs'].update(source_sha='d'*40),'B0 exact run'),
 (lambda z: z['cohorts']['w34_canonical_pytest'].update(total=3859),'pytest case population'),
 (lambda z: z['cohorts']['w34_staged_lanes'].update(native_qualified=4),'unqualified native'),
 (lambda z: z['root_families'].append(copy.deepcopy(z['root_families'][0])),'duplicate root ID'),
 (lambda z: z['cohorts']['w27_matched_testpilot'].update(code_global_coverage=95),'false global W27'),
 (lambda z: z['cohorts']['w27_matched_testpilot'].update(before=[106]),'W27 cohort size'),
])
def test_untrusted_mutants_fail_closed(mutate,match):
    payload=sample();mutate(payload)
    with pytest.raises(ValueError,match=match):m.rollup(payload)


def test_duplicate_temporal_wave_identity_denied():
    rows=[wave(1),wave(1),wave(3),wave(4)]
    with pytest.raises(ValueError,match='wave identity'):m.decision(rows,0,True)


def test_false_numeric_denominators_denied():
    p=sample();p['cohorts']['w34_canonical_b0_jobs']['passed']=True
    with pytest.raises(ValueError,match='invalid pair'):m.rollup(p)


def test_w38_focus_matched_four_family_sum_no_main_credit():
    r=m.rollup(sample())
    c=r['w38_focused']
    assert c['covered']==707 and c['eligible']==723
    assert c['before_covered']==660
    assert c['delta_pp']==round(47/723*100,6)
    assert c['native_passed']==203 and c['tested_python']=='3.12'
    assert c['artifact_bytes_verified'] is None
    assert c['broad_main_coverage'] is None


def test_main_now_differs_from_historical_w34_native_run():
    r=m.rollup(sample())
    assert r['exact_main']=='2246c7bd3a9bda6a3d43b9a9116cb7088cfbcc88'
    assert r['historical_w34_b0']['source_sha']=='994ad6e73c748923841d92b12651e92d41b2d4ff'
    assert r['current_main_b0']['numerator'] is None


def test_w38_wrong_family_sum_denied():
    d=sample();d['cohorts']['w38_focused']['families'][0]['covered']+=1
    with pytest.raises(ValueError,match='W38 scope'):
        m.rollup(d)


def test_w38_duplicate_family_denied():
    d=sample();d['cohorts']['w38_focused']['families'][1]['family']='W75'
    with pytest.raises(ValueError,match='duplicate or incomplete W38'):
        m.rollup(d)


def test_w38_other_interpreter_without_proof_denied():
    d=sample();d['cohorts']['w38_focused']['interpreter']='3.9'
    with pytest.raises(ValueError,match='unqualified W38'):
        m.rollup(d)
