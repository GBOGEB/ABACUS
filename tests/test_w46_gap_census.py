"""Fail-closed synthetic negative/reverse tests for disjoint gap census."""
from __future__ import annotations
import pytest
from copy import deepcopy
from tools.recovery.w46_gap_census import compare_zero_frontier, family, rollup

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


# W51 source-matched first-touch / 100%-where-reachable controls.
def _w51_coverage():
    result = sample()
    result["meta"]["version"] = "7.16.2"
    return result


def _w51_blobs(source):
    return {path: "b" * 40 for path in source["files"]}


def _w51_compare(before, after, **overrides):
    params = {
        "before_head": SHA, "after_head": "c" * 40,
        "before_source_blobs": _w51_blobs(before),
        "after_source_blobs": _w51_blobs(after),
        "before_config_sha256": "a" * 64,
        "after_config_sha256": "a" * 64,
    }
    params.update(overrides)
    return compare_zero_frontier(before, after, **params)


def test_w51_first_touch_is_a_zero_file_reduction_not_root_closure():
    before = _w51_coverage()
    after = deepcopy(before)
    b = after["files"]["mission_control_lite/b.py"]["summary"]
    b["covered_lines"], b["missing_lines"] = 3, 7
    b["covered_branches"], b["missing_branches"] = 1, 5
    outcome = _w51_compare(before, after)
    assert outcome["comparison"] == "STRUCTURAL_MATCH_NATIVE_ATTESTATION_PENDING"
    assert (outcome["before_zero"], outcome["after_zero"]) == (1, 0)
    assert outcome["zero_count_delta"] == -1
    assert outcome["covered_opportunities_delta"] == 4
    assert outcome["newly_touched"] == ["mission_control_lite/b.py"]
    assert outcome["regressed_to_zero"] == []
    assert outcome["coverage_improvement_qualified"] is False
    assert outcome["native_run_job_artifact_verified"] is None
    assert outcome["accepted_root_closure"] is None
    assert outcome["merge_admission"] == "HOLD"


def test_w51_saturation_is_counted_only_for_positive_eligible_assets():
    before = _w51_coverage()
    after = deepcopy(before)
    for obj in after["files"].values():
        x = obj["summary"]
        x["covered_lines"], x["missing_lines"] = x["num_statements"], 0
        x["covered_branches"], x["missing_branches"] = x["num_branches"], 0
    after["files"]["README/__init__.py"] = {
        "summary": dict(num_statements=0, covered_lines=0, missing_lines=0,
                        num_branches=0, covered_branches=0, missing_branches=0)
    }
    before["files"]["README/__init__.py"] = deepcopy(
        after["files"]["README/__init__.py"]
    )
    outcome = _w51_compare(before, after)
    assert outcome["after_full_count"] == 3
    assert len(outcome["newly_full"]) == 3
    assert outcome["after_zero"] == 0
    assert outcome["covered_opportunities_delta"] == 26
    assert outcome["first_touch_queue"] == []


def test_w51_regression_to_zero_blocks_a_one_way_success_story():
    before = _w51_coverage()
    after = deepcopy(before)
    a = after["files"]["DMAIC_V3/a.py"]["summary"]
    a["covered_lines"], a["missing_lines"] = 0, 8
    a["covered_branches"], a["missing_branches"] = 0, 4
    outcome = _w51_compare(before, after)
    assert outcome["zero_count_delta"] == 1
    assert outcome["covered_opportunities_delta"] == -4
    assert outcome["regressed_to_zero"] == ["DMAIC_V3/a.py"]
    assert outcome["newly_touched"] == []


@pytest.mark.parametrize("alter", ["missing_file", "extra_file", "denominator"])
def test_w51_changed_source_population_or_denominator_is_incomparable(alter):
    before = _w51_coverage()
    after = deepcopy(before)
    if alter == "missing_file":
        after["files"].pop("DMAIC_V3/c.py")
    elif alter == "extra_file":
        after["files"]["new/new.py"] = deepcopy(after["files"]["DMAIC_V3/c.py"])
    else:
        item = after["files"]["mission_control_lite/b.py"]["summary"]
        item["num_statements"] += 1
        item["missing_lines"] += 1
    outcome = _w51_compare(before, after)
    assert outcome["comparison"].startswith("INCOMPARABLE_FILE_")
    assert outcome["zero_count_delta"] is None
    assert outcome["newly_touched"] is None


def test_w51_no_blobs_no_coverage_delta_not_a_zero_value():
    before = _w51_coverage()
    output = compare_zero_frontier(before, deepcopy(before),
                                   before_head=SHA, after_head="c" * 40)
    assert output["comparison"] == "UNKNOWN_SOURCE_OR_CONFIG_IDENTITY"
    assert output["before_zero"] == output["after_zero"] == 1
    assert output["zero_count_delta"] is None


@pytest.mark.parametrize("fault", ["wrong_config", "changed_source",
                                   "no_instrumentation", "version_change"])
def test_w51_mismatched_identifiers_fail_closed(fault):
    before = _w51_coverage()
    after = deepcopy(before)
    extra = {}
    if fault == "wrong_config":
        extra["after_config_sha256"] = "f" * 64
    elif fault == "changed_source":
        other = _w51_blobs(after)
        other["DMAIC_V3/a.py"] = "f" * 40
        extra["after_source_blobs"] = other
    elif fault == "no_instrumentation":
        before["meta"].pop("version")
    else:
        after["meta"]["version"] = "9.0.0"
    outcome = _w51_compare(before, after, **extra)
    assert outcome["comparison"] in {
        "INCOMPARABLE_COVERAGE_CONFIG", "INCOMPARABLE_SOURCE_BLOBS",
        "UNKNOWN_INSTRUMENTATION_VERSION",
        "INCOMPARABLE_INSTRUMENTATION_VERSION",
    }
    assert outcome["covered_opportunities_delta"] is None


@pytest.mark.parametrize("identity", ["bad_config", "bad_blob", "missing_path"])
def test_w51_forged_identity_is_an_error_not_a_green_outcome(identity):
    before = _w51_coverage()
    after = deepcopy(before)
    bad = {}
    if identity == "bad_config":
        bad["before_config_sha256"] = "not-a-sha"
    else:
        blobs = _w51_blobs(after)
        if identity == "bad_blob":
            blobs["DMAIC_V3/a.py"] = "bad"
        else:
            del blobs["DMAIC_V3/a.py"]
        bad["after_source_blobs"] = blobs
    with pytest.raises(ValueError, match="SHA256|blob"):
        _w51_compare(before, after, **bad)


def test_w51_remaining_zero_queue_is_disjoint_and_gain_is_unpredicted():
    before = _w51_coverage()
    outcome = _w51_compare(before, deepcopy(before))
    assert outcome["after_zero"] == 1
    assert outcome["zero_count_delta"] == 0
    assert outcome["first_touch_queue"] == [{
        "path": "mission_control_lite/b.py",
        "owner_candidate": "MISSION_CONTROL_LITE",
        "missed_opportunities": 16,
        "predicted_coverage_gain": None,
    }]
    assert outcome["newly_touched"] == []
    assert outcome["newly_full"] == []
