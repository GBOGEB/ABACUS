"""Wave metrics: evidence reach without causal, merge or fake coverage credit."""
import copy
import json
from pathlib import Path

import pytest

from scripts import cbd_e2e_wave_effectiveness as wave

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "docs/ci/CBD_E2E_EVIDENCE_GRAPH_ATLAS_20261017.json"
)


@pytest.fixture
def graph():
    return json.loads(SOURCE.read_text(encoding="utf-8"))


def test_exact_graph_and_native_denominators(graph):
    result = wave.project(graph)
    obs = result["observed"]
    assert obs["pr_heads"] == 20
    assert obs["workflow_associations"] == 533
    assert obs["failed_workflow_associations"] == 66
    assert obs["native_runs"] == 16
    assert obs["native_jobs"] == 303
    assert obs["failed_native_jobs"] == 40
    assert obs["failed_native_steps"] == 43
    assert obs["upstream_failed_job_manifestations"] == 26
    assert obs["downstream_failed_job_manifestations"] == 14
    assert obs["cooccurrence_edges"] == 89
    assert obs["temporal_noncausal_edges"] == 6
    assert obs["declared_unexecuted_stage_edges"] == 6


def test_source_bound_family_reach_and_dependency_order(graph):
    result = wave.project(graph)
    rows = {r["family"]: r for r in result["candidate_job_families"]}
    assert rows["SECURITY"]["priority"] == "P0"
    assert rows["SECURITY"]["unique_prs_affected"] == 15
    assert rows["SECURITY"]["failed_job_manifestations"] == 15
    assert rows["QUALITY"]["failed_job_manifestations"] == 10
    assert rows["COVERAGE"]["failed_job_manifestations"] == 1
    assert rows["DOWNSTREAM_SUMMARY"]["failed_job_manifestations"] == 14
    assert rows["DOWNSTREAM_SUMMARY"]["priority"] == "DEPENDENT"
    assert rows["DOWNSTREAM_SUMMARY"]["potential_unblock_pr_upper_bound"] is None
    assert rows["SECURITY"]["actual_unblocked_prs"] is None
    assert all(not r["owner_mutation_authorized"] for r in rows.values())


def test_native_job_duration_is_cost_evidence_not_saved_walltime(graph):
    result = wave.project(graph)
    rows = {r["family"]: r for r in result["candidate_job_families"]}
    assert rows["SECURITY"]["measured_runtime_jobs"] == 15
    assert rows["COVERAGE"]["measured_runtime_jobs"] == 1
    assert rows["SECURITY"]["sum_measured_job_runtime_ms"] > 0
    assert result["observed"]["job_runtime_p50_ms"] == 121000
    assert result["observed"]["job_runtime_p95_ms"] == 267000
    assert result["observed"]["actual_runner_queue_wait_ms"] is None


def test_cooccurrence_support_and_jaccard_are_not_causal(graph):
    result = wave.project(graph)
    pair = next(r for r in result["top_cooccurrence_edges"]
                if {r["workflow_a"], r["workflow_b"]} ==
                {"CI Workflow Governance", "CI/CD Test Suite"})
    assert pair["shared_prs"] == 9
    assert pair["jaccard"] == 0.5
    assert pair["confirmed_common_cause"] is None


def test_no_unearned_coverage_population_inference_or_merge(graph):
    result = wave.project(graph)
    assert result["observed"]["matched_changed_line_coverage"] is None
    assert result["observed"]["matched_main_coverage"] is None
    assert result["observed"]["total_verified_causal_roots"] is None
    assert result["observed"]["total_verified_pr_unblocks"] is None
    assert result["authority"]["merge_admission"] == "HOLD"
    assert result["metrics_policy"][
        "nonrandom_pr_cohort_cannot_yield_fleet_confidence_interval"
    ] is True


def test_read_only_projection_is_deterministic(graph):
    prior = copy.deepcopy(graph)
    assert wave.project(graph) == wave.project(graph)
    assert graph == prior


def test_invalid_or_duplicate_node_rejected(graph):
    graph["nodes"].append(copy.deepcopy(graph["nodes"][0]))
    with pytest.raises(ValueError, match="duplicate or missing node"):
        wave.project(graph)


def test_dangling_edge_rejected(graph):
    graph["edges"][0]["target"] = "nonexistent:atom"
    with pytest.raises(ValueError, match="dangling graph edge"):
        wave.project(graph)


def test_wrong_observed_denominator_rejected(graph):
    graph["metrics"]["edge_evidence_classes"]["OBSERVED"] -= 1
    with pytest.raises(ValueError, match="evidence denominator mismatch"):
        wave.project(graph)


def test_declared_stage_cannot_claim_observation(graph):
    stage = next(e for e in graph["edges"]
                 if e["evidence"] == "DECLARED")
    stage["support"] = 1
    with pytest.raises(ValueError, match="declared edge"):
        wave.project(graph)


def test_association_cannot_claim_root(graph):
    assoc = next(e for e in graph["edges"]
                 if e["evidence"] == "ASSOCIATION")
    assoc["causal_confirmed"] = True
    with pytest.raises(ValueError, match="unproven causal edge"):
        wave.project(graph)


def test_forged_admission_denied(graph):
    graph["authority"]["merge_admission"] = "PASS"
    with pytest.raises(ValueError, match="authority promoted"):
        wave.project(graph)


def test_identical_topology_yields_only_evidence_delta(graph):
    other = copy.deepcopy(graph)
    res = wave.comparable_delta(graph, other)
    assert res["matched_native_topology"] is True
    assert res["new_observed_edges"] == 0
    assert res["new_source_bound_edges"] == 0
    assert res["coverage_percentage_delta"] is None
    assert res["causal_root_closure_delta"] is None
    assert res["merge_admission"] == "HOLD"


def test_changed_attempt_prevents_invalid_n_delta(graph):
    other = copy.deepcopy(graph)
    attempt = next(n for n in other["nodes"] if n["kind"] == "job")
    attempt["attributes"]["run_attempt"] += 1
    res = wave.comparable_delta(graph, other)
    assert res["matched_native_topology"] is False
    assert res["new_observed_edges"] is None
    assert res["status"] == "HOLD_HEAD_OR_ATTEMPT_DRIFT"


def test_missing_job_symptom_or_duplicate_family_edge_halts(graph):
    other = copy.deepcopy(graph)
    e = next(edge for edge in other["edges"]
             if edge["relationship"] == "failed_job_symptom")
    other["edges"].append(copy.deepcopy(e))
    other["metrics"]["edge_count"] += 1
    other["metrics"]["edge_evidence_classes"][e["evidence"]] += 1
    with pytest.raises(ValueError, match="duplicate failed-job"):
        wave.project(other)
