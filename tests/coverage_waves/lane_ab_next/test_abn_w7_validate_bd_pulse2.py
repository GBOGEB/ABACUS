"""Gap tests for triage/validate_bd_pulse2.py (fail-closed branches)."""

import copy
import json

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

mod = load("triage/validate_bd_pulse2.py", name="abn_w7_validate_bd_pulse2")

DATA = json.loads(
    (REPO_ROOT / "triage" / "ABACUS_BD_PULSE2_20261017.json").read_text(
        encoding="utf-8"
    )
)


def _doc():
    return copy.deepcopy(DATA)


def _expect(doc, message):
    with pytest.raises(ValueError, match=message):
        mod.validate(doc)


def test_baseline_document_validates():
    assert mod.validate(_doc())["merge_admission"] == "HOLD"


def test_unknown_schema():
    doc = _doc()
    doc["schema"] = "other"
    _expect(doc, "unrecognized BD census schema")


def test_non_integer_population():
    doc = _doc()
    doc["baseline"]["ABACUS_open_issues"] = "57"
    _expect(doc, "missing numeric issue population")


def test_incomplete_scoped_population():
    doc = _doc()
    doc["latest"]["scoped_repo_issue_open"]["GBOGEB/extra"] = 1
    _expect(doc, "incomplete or non-integer scoped population")


def test_four_repo_total_mismatch():
    doc = _doc()
    doc["latest"]["four_repo_total"] += 1
    _expect(doc, "four-repo population mismatch")


def test_global_total_rejected():
    doc = _doc()
    doc["latest"]["global_all_repo_total"] = 999
    _expect(doc, "cannot imply global completion")


def test_causal_root_counts_rejected():
    doc = _doc()
    doc["latest"]["canonical_engineering_roots_closed"] = 3
    _expect(doc, "cannot be certified causal roots")


def test_closure_class_count_mismatch():
    doc = _doc()
    doc["closure_evidence"]["six_other_completed_today"].pop()
    _expect(doc, "nonreconciling issue closure classes")


def test_duplicate_issue_in_proof():
    doc = _doc()
    closed = doc["closure_evidence"]
    closed["six_other_completed_today"][0]["issue"] = closed["nine_this_pulse"][0][
        "issue"
    ]
    _expect(doc, "duplicate issue in closure proof")


def test_false_duplicate_disposition():
    doc = _doc()
    doc["closure_evidence"]["nine_this_pulse"][0]["state_reason"] = "completed"
    _expect(doc, "false duplicate ticket disposition")


def test_unobserved_historical_regime():
    doc = _doc()
    doc["closure_evidence"]["nine_this_pulse"][0]["historical_broken_hrefs"] = 7
    _expect(doc, "unobserved historical scan regime")


def test_missing_run_identity():
    doc = _doc()
    doc["closure_evidence"]["nine_this_pulse"][0]["source_run_id"] = 0
    _expect(doc, "missing native run identity")


def test_source_run_url_mismatch():
    doc = _doc()
    doc["closure_evidence"]["nine_this_pulse"][0]["source_run_url"] = "https://x"
    _expect(doc, "source-run URL mismatch")


def test_lost_sixteen_link_regime():
    doc = _doc()
    for row in doc["closure_evidence"]["nine_this_pulse"]:
        row["historical_broken_hrefs"] = 52
    _expect(doc, "lost historical 16-link regime")


def test_completed_issue_promoted():
    doc = _doc()
    doc["closure_evidence"]["six_other_completed_today"][0][
        "proven_engineering_root_closure"
    ] = True
    _expect(doc, "completed issue promoted without RCA")


def test_issue_count_delta_mismatch():
    doc = _doc()
    doc["latest"]["ABACUS_issue_count_delta"] += 1
    _expect(doc, "issue-count change does not reconcile")


def test_ageing_cohort_mismatch():
    doc = _doc()
    ages = doc["latest"]["ABACUS_issue_ages"]
    first = next(iter(ages))
    ages[first] += 1
    _expect(doc, "ageing cohort denominator mismatch")


def test_unpinned_repair_sha():
    doc = _doc()
    doc["closure_evidence"]["source_repair_head"] = "ABC"
    _expect(doc, "source-repair SHA not pinned")


def test_unverified_repair_promoted():
    doc = _doc()
    doc["closure_evidence"]["source_repair_accepted"] = True
    _expect(doc, "unverified source repair promoted")
