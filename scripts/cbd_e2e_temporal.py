"""Strict E2E job temporal joins, censored durations and noncausal overlap links.

Created-to-latest-attempt-start is NOT runner queue waiting. Native timestamps
are only joined by exact run ID, native job ID, attempt and source identity.
"""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime
from pathlib import Path


def require(value, reason):
    if not value:
        raise ValueError(reason)


def milliseconds(iso):
    if not isinstance(iso, str):
        return None
    try:
        value = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        require(value.utcoffset() is not None, "naive UTC timestamp")
        return int(value.timestamp() * 1000)
    except (TypeError, ValueError, OverflowError):
        return None


def quantile_nearest(values, probability):
    """Nearest-rank quantile with explicit uncensored observation denominator."""
    require(type(probability) in (float, int) and 0 < probability <= 1,
            "invalid probability")
    if not values:
        return None
    require(all(type(v) in (float, int) and v >= 0 for v in values),
            "invalid measured duration")
    rank = max(0, -(-len(values) * probability // 1) - 1)
    return sorted(values)[int(rank)]


def augment(graph, timeline_documents):
    """Enrich exact matching native nodes without mutating source evidence."""
    require(graph.get("schema") == "cbd.e2e.evidence_multigraph.v1",
            "unsupported graph schema")
    require(len(timeline_documents) == 2, "expected two temporal snapshots")
    result = copy.deepcopy(graph)
    nodes = {n["id"]: n for n in result["nodes"]}
    run_seen, job_seen, sample = set(), set(), []
    inverted_timestamps = 0
    inverted_job_ids = []
    for document in timeline_documents:
        require(document.get("schema") == "cbd.e2e.native_temporal_snapshot.v1",
                "invalid temporal schema")
        require(document.get("authority", {}).get("merge_admission") == "HOLD"
                and document["authority"].get("security_waiver") is False,
                "temporal authority promotion")
        for run in document.get("runs", []):
            rid = run.get("run_id")
            require(type(rid) is int and rid not in run_seen,
                    "duplicate temporal run")
            run_seen.add(rid)
            rnode = nodes.get(f"run:{rid}")
            require(rnode is not None, "unattributed temporal run ID")
            sha = run.get("source_head_sha")
            require(
                f"head:{run.get('pr')}:{sha}" in nodes,
                "temporal run changed exact PR head",
            )
            require(run.get("run_head_sha") == sha, "native run head drift")
            attempt = run.get("run_attempt_current")
            require(type(attempt) is int and attempt > 0,
                    "missing native run attempt")
            require(
                run.get("actual_runner_queue_wait_ms") is None,
                "queue-wait cannot be inferred from run created-at",
            )
            rnode["attributes"]["run_attempt_latest"] = attempt
            rnode["attributes"]["creation_to_latest_attempt_start_ms"] = (
                run.get("creation_to_current_attempt_start_ms"))
            rnode["attributes"]["actual_runner_queue_wait_ms"] = None
            group = []
            for job in run.get("jobs", []):
                jid = job.get("job_id")
                require(type(jid) is int and jid not in job_seen,
                        "duplicate temporal job")
                job_seen.add(jid)
                key = f"job:{jid}"
                need = nodes.get(key)
                require(need is not None, "unknown native job")
                require(
                    job.get("temporal_identity_matched") is True
                    and job.get("head_sha") == sha
                    and job.get("attempt") == need["attributes"].get("run_attempt")
                    and job.get("status") == need["attributes"].get("status")
                    and job.get("conclusion") == need["attributes"].get("conclusion"),
                    "job identity/outcome mismatch",
                )
                start = milliseconds(job.get("started_at"))
                end = milliseconds(job.get("completed_at"))
                dur = job.get("runtime_ms")
                if dur is not None:
                    require(type(dur) is int and start is not None
                            and end is not None and end >= start
                            and dur == end - start,
                            "invalid executed job duration")
                else:
                    require(not (start is not None and end is not None
                                and end >= start),
                            "uncensored duration omitted")
                    if start is not None and end is not None and end < start:
                        inverted_timestamps += 1
                        inverted_job_ids.append(jid)
                need["attributes"]["started_at"] = job.get("started_at")
                need["attributes"]["completed_at"] = job.get("completed_at")
                need["attributes"]["runtime_ms"] = dur
                need["attributes"]["start_lag_from_run_start_ms"] = (
                    job.get("start_lag_from_run_start_ms"))
                group.append((jid, start, end, job.get("conclusion")))
                sample.append(job)
            # Two failed jobs running simultaneously only prove concurrency.
            failures = [(jid, start, end) for jid, start, end, status in group
                        if status == "failure" and start is not None and end is not None]
            failures.sort()
            for i, (left, a0, a1) in enumerate(failures):
                for right, b0, b1 in failures[i + 1:]:
                    overlap = max(0, min(a1, b1) - max(a0, b0))
                    if overlap > 0:
                        result["edges"].append({
                            "source": f"job:{left}", "target": f"job:{right}",
                            "relationship": "observed_failed_job_time_overlap",
                            "evidence": "TEMPORAL_ASSOCIATION",
                            "support": 1, "overlap_ms": overlap,
                            "jaccard": None, "causal_confirmed": False,
                        })
    if inverted_job_ids:
        anomaly = {
            "id": "anomaly:skipped-job-inverted-clock",
            "kind": "temporal_anomaly",
            "label": "Skipped job completion before start",
            "rank": 8,
            "attributes": {
                "observed_count": len(inverted_job_ids),
                "causal_root_id": None,
                "classification": "NATIVE_TIMESTAMP_INCONSISTENCY",
            },
            "degree": len(inverted_job_ids),
            "observed_weighted_degree": len(inverted_job_ids),
        }
        result["nodes"].append(anomaly)
        for jid in sorted(inverted_job_ids):
            job_node = nodes[f"job:{jid}"]
            job_node["degree"] += 1
            job_node["observed_weighted_degree"] += 1
            result["edges"].append({
                "source": f"job:{jid}",
                "target": anomaly["id"],
                "relationship": "skipped_job_clock_inversion_observed",
                "evidence": "OBSERVED",
                "support": 1,
                "jaccard": None,
                "causal_confirmed": False,
            })
        result["metrics"]["node_count"] = len(result["nodes"])
        result["metrics"]["node_types"]["temporal_anomaly"] = 1
        result["metrics"]["edge_evidence_classes"]["OBSERVED"] += len(inverted_job_ids)
    require(len(run_seen) == result["metrics"]["native_run_count"],
            "temporal run denominator missing")
    require(len(job_seen) == result["metrics"]["native_job_count"],
            "temporal job denominator missing")
    durations = [j["runtime_ms"] for j in sample if j["runtime_ms"] is not None]
    result["metrics"]["temporal"] = {
        "native_jobs_source_matched": len(sample),
        "measured_completed_job_durations": len(durations),
        "censored_or_unmeasured_jobs": len(sample) - len(durations),
        "inverted_timestamp_jobs": inverted_timestamps,
        "duration_p50_ms_nearest_rank": quantile_nearest(durations, 0.5),
        "duration_p95_ms_nearest_rank": quantile_nearest(durations, 0.95),
        "rerun_attempt_run_count": sum(
            nodes[f"run:{rid}"]["attributes"]["run_attempt_latest"] > 1
            for rid in run_seen
        ),
        "actual_runner_queue_wait_ms": None,
        "cross_host_clock_drift_ms": None,
        "matched_local_to_github_pre_push": None,
        "timestamp_measurement_method": "native started_at to completed_at",
        "quantile_estimator": "nearest-rank of non-null job durations",
    }
    result["metrics"]["edge_count"] = len(result["edges"])
    result["metrics"]["edge_evidence_classes"]["TEMPORAL_ASSOCIATION"] = sum(
        e["evidence"] == "TEMPORAL_ASSOCIATION" for e in result["edges"])
    result["edges"].sort(key=lambda e: (
        e["source"], e["target"], e["relationship"]))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--timeline", type=Path, nargs=2, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    data = lambda p: json.loads(p.read_text(encoding="utf-8"))
    result = augment(data(args.graph), [data(x) for x in args.timeline])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result["metrics"]["temporal"], sort_keys=True))


if __name__ == "__main__":
    main()
