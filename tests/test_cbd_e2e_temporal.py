"""Temporal atom tests: exact-head joins, inverted clocks, quantiles, no queue claims."""

import copy
import json
from pathlib import Path

import pytest

from scripts import cbd_e2e_temporal as temporal

ROOT = Path(__file__).resolve().parents[1] / "docs" / "ci"
GRAPH = ROOT / "CBD_E2E_EVIDENCE_GRAPH_ATLAS_20261017.json"
A = ROOT / "CBD_E2E_NATIVE_TIMELINE_A_20261017.json"
B = ROOT / "CBD_E2E_NATIVE_TIMELINE_B_20261017.json"


@pytest.fixture
def data():
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    timelines = [json.loads(p.read_text(encoding="utf-8")) for p in (A, B)]
    return graph, timelines


def test_303_native_temporal_identity_matches_and_censorship(data):
    result = temporal.augment(*data)
    m = result["metrics"]["temporal"]
    assert m["native_jobs_source_matched"] == 303
    assert m["measured_completed_job_durations"] == 293
    assert m["censored_or_unmeasured_jobs"] == 10
    assert m["inverted_timestamp_jobs"] == 10
    assert m["duration_p50_ms_nearest_rank"] == 121000
    assert m["duration_p95_ms_nearest_rank"] == 267000
    assert m["rerun_attempt_run_count"] == 5
    assert m["actual_runner_queue_wait_ms"] is None


def test_no_graph_ownership_or_causal_mutation(data):
    previous = copy.deepcopy(data)
    result = temporal.augment(*data)
    assert data == previous
    assert result["authority"]["merge_admission"] == "HOLD"
    assert result["metrics"]["confirmed_causal_root_edges"] == 0
    assert result["metrics"]["matched_coverage_delta"] is None
    assert all(not item["causal_confirmed"] for item in result["edges"])


def test_2026_fourth_attempt_is_not_first_run_queue_time(data):
    report = temporal.augment(*data)
    run = next(x for x in report["nodes"] if x["id"] == "run:38958986407")
    assert run["attributes"]["run_attempt_latest"] == 4
    assert run["attributes"]["actual_runner_queue_wait_ms"] is None
    assert run["attributes"]["creation_to_latest_attempt_start_ms"] > 0


def test_inverted_skip_timestamp_does_not_go_negative(data):
    result = temporal.augment(*data)
    job = next(x for x in result["nodes"] if x["id"] == "job:117364114795")
    assert job["attributes"]["runtime_ms"] is None
    assert job["attributes"]["started_at"] > job["attributes"]["completed_at"]


def test_skipped_clock_anomaly_is_one_cluster_ten_manifestations(data):
    result = temporal.augment(*data)
    nodes = [x for x in result["nodes"] if x["kind"] == "temporal_anomaly"]
    assert len(nodes) == 1
    assert nodes[0]["attributes"]["observed_count"] == 10
    links = [
        e
        for e in result["edges"]
        if e["relationship"] == "skipped_job_clock_inversion_observed"
    ]
    assert len(links) == 10
    assert len({e["source"] for e in links}) == 10
    assert all(e["evidence"] == "OBSERVED" and not e["causal_confirmed"] for e in links)
    assert result["metrics"]["node_count"] == 499


def test_second_enrichment_is_identical_and_no_duplicate_atoms(data):
    first = temporal.augment(*data)
    second = temporal.augment(first, data[1])
    third = temporal.augment(second, data[1])
    assert first == second == third
    assert first["metrics"]["node_count"] == 499
    assert first["metrics"]["edge_count"] == 697
    assert first["metrics"]["edge_evidence_classes"]["OBSERVED"] == 494
    assert first["metrics"]["edge_evidence_classes"]["TEMPORAL_ASSOCIATION"] == 6


def test_partial_preexisting_anomaly_rejected(data):
    graph, timelines = data
    graph["edges"] = [
        e
        for e in graph["edges"]
        if e["relationship"] != "skipped_job_clock_inversion_observed"
    ]
    with pytest.raises(ValueError, match="temporal anomaly denominator"):
        temporal.augment(graph, timelines)


def test_duplicate_derived_evidence_rejected(data):
    graph, timelines = data
    edge = next(
        e
        for e in graph["edges"]
        if e["relationship"] == "skipped_job_clock_inversion_observed"
    )
    graph["edges"].append(copy.deepcopy(edge))
    with pytest.raises(ValueError, match="duplicated temporal evidence"):
        temporal.augment(graph, timelines)


def test_duplicate_anomaly_node_rejected(data):
    graph, timelines = data
    graph["nodes"].append(
        copy.deepcopy(
            next(n for n in graph["nodes"] if n["kind"] == "temporal_anomaly")
        )
    )
    with pytest.raises(ValueError, match="duplicate graph node identity"):
        temporal.augment(graph, timelines)


def test_wrong_head_for_native_run_rejected(data):
    graph, timeline = data
    timeline[0]["runs"][0]["source_head_sha"] = "f" * 40
    with pytest.raises(ValueError, match="temporal run changed exact PR head"):
        temporal.augment(graph, timeline)


def test_wrong_attempt_for_job_rejected(data):
    graph, timeline = data
    timeline[0]["runs"][0]["jobs"][0]["attempt"] += 1
    with pytest.raises(ValueError, match="identity"):
        temporal.augment(graph, timeline)


def test_unmatched_job_id_rejected(data):
    graph, timeline = data
    timeline[0]["runs"][0]["jobs"][0]["job_id"] = 999999999999
    with pytest.raises(ValueError, match="unknown native job"):
        temporal.augment(graph, timeline)


def test_missing_job_denominator_rejected(data):
    graph, timeline = data
    timeline[0]["runs"][0]["jobs"].pop()
    with pytest.raises(ValueError, match="temporal job denominator"):
        temporal.augment(graph, timeline)


def test_forged_queue_wait_rejected(data):
    graph, timeline = data
    timeline[0]["runs"][0]["actual_runner_queue_wait_ms"] = 48984000
    with pytest.raises(ValueError, match="queue-wait"):
        temporal.augment(graph, timeline)


def test_forged_security_waiver_rejected(data):
    graph, timeline = data
    timeline[0]["authority"]["security_waiver"] = True
    with pytest.raises(ValueError, match="authority"):
        temporal.augment(graph, timeline)


@pytest.mark.parametrize(
    "values,probability,expected",
    [
        ([10, 20, 30], 0.5, 20),
        ([10, 20, 30], 0.95, 30),
        ([10], 0.95, 10),
        ([], 0.95, None),
    ],
)
def test_nearest_rank_declared_estimator(values, probability, expected):
    assert temporal.quantile_nearest(values, probability) == expected


@pytest.mark.parametrize("probability", [0, -1, 1.1])
def test_invalid_quantile_probability_rejected(probability):
    with pytest.raises(ValueError):
        temporal.quantile_nearest([1, 2], probability)
