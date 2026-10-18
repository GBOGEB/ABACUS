"""W31 hysteretic convergence: negative/reverse/reuse and full terminal fixtures."""
from __future__ import annotations

import copy
import pytest
import wave_convergence as m


def row(i: int, covered: int, *, queue=50.0):
    return {
        'wave': i, 'run_id': 42000 + i, 'run_attempt': 1,
        'source_sha': f'{100 + i:040x}', 'artifact_digest': f'{200 + i:064x}',
        'configuration_digest': 'a' * 64, 'cohort_digest': 'b' * 64,
        'source_slice': f'W29-negative-{i}', 'eligible': 346, 'covered': covered,
        'job_expected': 2, 'job_success': 2, 'test_passed': 128,
        'test_failed': 0, 'test_skipped': 0, 'cases_added': 1,
        'terminal': True, 'head_stable': True, 'first_red_signatures': [],
        'root_dispositions_complete': False, 'queue_p95_seconds': queue,
        'attempted_new_behavior': True,
    }


def test_empty_history_is_unknown_not_zero():
    a=m.evaluate([])
    assert a['state']=='AWAIT_FIRST_TERMINAL_OBSERVATION'
    assert a['governed_merge_credit'] is None
    assert a['stop_engineering_wave'] is False


def test_three_zero_delta_transitions_require_four_unique_terminal_waves():
    for length in (1, 2, 3):
        r=m.evaluate([row(i, 90) for i in range(1, length+1)])
        assert r['state']!='COHORT_PLATEAU_CONFIRMED'
        assert r['no_change_streak']==length-1
    r=m.evaluate([row(i, 90) for i in range(1, 5)])
    assert r['state']=='COHORT_PLATEAU_CONFIRMED'
    assert r['stop_this_source_slice'] is True
    assert r['stop_entire_program'] is False
    assert r['governed_merge_credit'] is None


def test_progress_resets_stability_streak_and_keeps_source_wave_active():
    r=m.evaluate([row(1, 90), row(2, 90), row(3, 94), row(4, 94)])
    assert r['no_change_streak']==1
    assert r['delta_covered_by_wave']==[0, 4, 0]
    assert r['state']=='NOT_YET_CONVERGED'


def test_target_reached_moves_to_new_cohort_without_claiming_merger():
    r=m.evaluate([row(1, 100), row(2, 335)], target_pct=95)
    assert r['state']=='SOURCE_TARGET_REACHED'
    assert r['stop_this_source_slice'] is True
    assert r['stop_entire_program'] is False


def test_genuine_regression_has_priority_over_plateau():
    r=m.evaluate([row(1, 100), row(2, 101), row(3, 99)])
    assert r['state']=='COVERAGE_REGRESSION'
    assert r['no_change_streak']==0


def test_first_red_prevents_stability_credit():
    data=[row(i, 90) for i in range(1,5)]
    data[-1]['first_red_signatures']=['native.coverage.no-data']
    r=m.evaluate(data)
    assert r['state']=='FIRST_RED_UNRESOLVED'
    assert r['stop_this_source_slice'] is False


@pytest.mark.parametrize('bad_field,bad_value', [
    ('terminal',False), ('head_stable',None), ('job_success',1),
    ('test_failed',1), ('test_skipped',1), ('test_passed',0),
    ('artifact_digest',None), ('source_sha','short'), ('run_id',0),
    ('run_attempt',False), ('configuration_digest','short'),
    ('covered',347), ('eligible',0), ('attempted_new_behavior',False),
    ('first_red_signatures',None), ('root_dispositions_complete',None),
    ('queue_p95_seconds',-1),('queue_p95_seconds',float('nan')),
    ('job_expected',0), ('cases_added',-1),
])
def test_incomplete_or_forged_wave_is_blocked(bad_field, bad_value):
    r=row(1, 90)
    r[bad_field]=bad_value
    doc=m.evaluate([r])
    assert doc['state']=='EVIDENCE_BLOCKED'
    assert doc['governed_merge_credit'] is None


@pytest.mark.parametrize('field', ['run_id','source_sha','artifact_digest','source_slice'])
def test_reused_identity_cannot_count_as_new_wave(field):
    a=row(1, 90)
    b=row(2, 90)
    b[field]=a[field]
    with pytest.raises(m.ConvergenceProofError,match='reused '+field):
        m.evaluate([a,b])


def test_missing_wave_ids_do_not_silently_count_as_stability():
    with pytest.raises(m.ConvergenceProofError,match='consecutively'):
        m.evaluate([row(1,90),row(3,90)])


@pytest.mark.parametrize('drift', ['configuration_digest','cohort_digest','eligible'])
def test_population_and_scan_drift_require_rebaseline(drift):
    d=[row(1,90),row(2,90)]
    d[1][drift]='c'*64 if drift.endswith('digest') else 346+1
    r=m.evaluate(d)
    assert r['state']=='INCOMPARABLE_COHORT'
    assert r['cohort_difference']==drift
    assert r['stop_engineering_wave'] is False


def test_queue_unknown_is_not_zero_and_withholds_acceleration():
    r=m.evaluate([row(1,90,queue=None),row(2,94,queue=None)])
    assert r['state']=='QUEUE_PROOF_UNKNOWN'
    assert r['queue_qualified'] is False
    assert r['suggested_readonly_lanes']==1


def test_actual_queue_p95_above_limit_decelerates():
    r=m.evaluate([row(1,90),row(2,94,queue=1200)])
    assert r['state']=='CAPACITY_PRESSURE'
    assert r['suggested_readonly_lanes']==1


def test_verified_progress_is_not_program_convergence():
    r=m.evaluate([row(1,90),row(2,110)])
    assert r['state']=='MEASURABLE_PROGRESS'
    assert r['delta_covered_by_wave']==[20]
    assert r['suggested_readonly_lanes']==3
    assert r['governed_merge_credit'] is None
    assert r['root_dispositions_complete'] is False


def test_unknown_roots_never_zero_or_close():
    r=m.evaluate([row(1,90)])
    assert r['accepted_root_closures'] is None
    assert r['authenticated_crew_launches'] is None


def test_negative_or_overlarge_targets_rejected():
    with pytest.raises(m.ConvergenceProofError): m.evaluate([],target_pct=101)
    with pytest.raises(m.ConvergenceProofError): m.evaluate([],target_pct=0)
    with pytest.raises(m.ConvergenceProofError): m.evaluate([],consecutive_no_change=0)
    with pytest.raises(m.ConvergenceProofError): m.evaluate([],queue_limit=float('inf'))


def test_nonobject_row_is_blocked():
    assert m.evaluate([None])['state']=='EVIDENCE_BLOCKED'


@pytest.mark.parametrize('bad', ['', ' ', None, 7])
def test_empty_or_nonstring_source_slice_is_blocked(bad):
    doc=row(1,90)
    doc['source_slice']=bad
    assert m.evaluate([doc])['state']=='EVIDENCE_BLOCKED'


def test_duplicate_first_red_signature_is_rejected():
    doc=row(1,90)
    doc['first_red_signatures']=['cov.no-data', 'cov.no-data']
    assert m.evaluate([doc])['state']=='EVIDENCE_BLOCKED'


def test_nonlist_history_is_rejected():
    with pytest.raises(m.ConvergenceProofError,match='history must be list'):
        m.evaluate({'not': 'a sequence'})
