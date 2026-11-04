"""E2E atom graph denominators, evidence classes and negative controls."""

import copy
import json
from pathlib import Path

import pytest

from scripts import cbd_e2e_graph_atlas as atlas

ROOT = Path(__file__).resolve().parents[1] / "docs" / "ci"
COHORT = (
    "CBD_10PR_A_FAILED_RUN_OBSERVATIONS_20261017.json",
    "CBD_10PR_B_FAILED_RUN_OBSERVATIONS_20261017.json",
)
NATIVE = (
    "CBD_NATIVE_16SUITE_JOBS_A_20261017.json",
    "CBD_NATIVE_16SUITE_JOBS_B_20261017.json",
)


@pytest.fixture
def evidence():
    c = [json.loads((ROOT / name).read_text()) for name in COHORT]
    n = [json.loads((ROOT / name).read_text()) for name in NATIVE]
    return c, n


def test_20_pr_16_run_atom_denominators(evidence):
    cohorts, native = evidence
    graph = atlas.build(cohorts, native)
    measured = graph["metrics"]
    assert measured["cohort_pr_heads"] == 20
    assert measured["cohort_workflow_associations"] == 533
    assert measured["failed_workflow_associations"] == 66
    assert measured["native_run_count"] == 16
    assert measured["native_job_count"] == 303
    assert measured["native_failed_jobs"] == 40
    assert measured["native_failed_steps"] == 43
    assert measured["node_count"] == len(graph["nodes"])
    assert measured["edge_count"] == len(graph["edges"])


def test_cooccurrence_has_jaccard_and_no_causation(evidence):
    graph = atlas.build(*evidence)
    edges = [
        e for e in graph["edges"] if e["relationship"] == "same_PR_head_cooccurrence"
    ]
    assert len(edges) > 0
    assert all(e["evidence"] == "ASSOCIATION" for e in edges)
    assert all(e["causal_confirmed"] is False for e in edges)
    assert all(0 < e["jaccard"] <= 1 for e in edges)
    assert all(e["support"] >= 1 for e in edges)


def test_declared_stages_do_not_claim_native_or_local_execution(evidence):
    graph = atlas.build(*evidence)
    stage_edges = [
        e for e in graph["edges"] if e["relationship"] == "expected_stage_transition"
    ]
    assert len(stage_edges) == 6
    assert all(e["support"] == 0 and e["evidence"] == "DECLARED" for e in stage_edges)
    assert graph["metrics"]["developer_pre_push_proven"] is None


def test_no_causal_or_merge_credit_is_inferred(evidence):
    graph = atlas.build(*evidence)
    assert graph["authority"]["merge_admission"] == "HOLD"
    assert graph["metrics"]["confirmed_causal_root_edges"] == 0
    assert graph["metrics"]["matched_coverage_delta"] is None
    assert all(not edge["causal_confirmed"] for edge in graph["edges"])


def test_native_attempt_not_assumed_one(evidence):
    graph = atlas.build(*evidence)
    atoms = [node for node in graph["nodes"] if node["kind"] == "attempt"]
    assert any(atom["attributes"]["attempt"] == 2 for atom in atoms)
    assert all(atom["attributes"]["attempt"] > 0 for atom in atoms)


def test_head_drift_rejected(evidence):
    cohorts, native = evidence
    cohorts[0]["observations"][0]["sha"] = "a" * 40
    with pytest.raises(ValueError, match="head drift"):
        atlas.build(cohorts, native)


def test_conflicting_native_source_rejected(evidence):
    cohorts, native = evidence
    native[0]["runs"][0]["jobs"][0]["head_sha"] = "f" * 40
    with pytest.raises(ValueError, match="different source head"):
        atlas.build(cohorts, native)


def test_duplicate_native_job_rejected(evidence):
    cohorts, native = evidence
    run = native[0]["runs"][0]
    run["jobs"][1]["job_id"] = run["jobs"][0]["job_id"]
    with pytest.raises(ValueError, match="duplicate/invalid native job"):
        atlas.build(cohorts, native)


def test_zero_failure_pr_still_measured(evidence):
    graph = atlas.build(*evidence)
    numbers = {
        node["attributes"]["number"] for node in graph["nodes"] if node["kind"] == "pr"
    }
    assert 2033 in numbers
    assert graph["metrics"]["cohort_pr_heads"] == 20


def test_graph_build_is_deterministic(evidence):
    old = copy.deepcopy(evidence)
    result1 = atlas.build(*evidence)
    result2 = atlas.build(*evidence)
    assert evidence == old
    assert result1 == result2
    assert result1["input_digests"] == result2["input_digests"]


def test_unknown_stage_receipt_never_links_to_head(evidence):
    c, n = evidence
    receipt = {
        "schema": "abacus.cbd.e2e.stage.v1",
        "stage": "pre-push",
        "source": {"head_sha": None},
    }
    with pytest.raises(ValueError, match="without exact source"):
        atlas.build(c, n, [receipt])


def test_real_source_bound_stage_receipt_is_observed_not_merge(evidence):
    c, n = evidence
    sample = {
        "schema": "abacus.cbd.e2e.stage.v1",
        "stage": "checkout",
        "source": {"head_sha": "a" * 40},
        "status": "FAIL",
        "clock": {"elapsed_process_ms": 220.0},
    }
    graph = atlas.build(c, n, [sample])
    receipts = [x for x in graph["nodes"] if x["kind"] == "stage_receipt"]
    assert len(receipts) == 1
    assert receipts[0]["attributes"]["status"] == "FAIL"
    assert graph["authority"]["merge_admission"] == "HOLD"


def test_workflow_run_atom_is_joined_with_exact_head(evidence):
    graph = atlas.build(*evidence)
    run = next(x for x in graph["nodes"] if x["id"] == "run:38958524460")
    assert run["kind"] == "run"
    related = [x for x in graph["edges"] if x["target"] == run["id"]]
    assert any(x["relationship"] == "native_job_run" for x in related)


def test_positive_observation_weight_excludes_declared(evidence):
    graph = atlas.build(*evidence)
    stage = next(x for x in graph["nodes"] if x["id"] == "stage:E1")
    assert stage["degree"] > 0
    assert stage["observed_weighted_degree"] == 0
