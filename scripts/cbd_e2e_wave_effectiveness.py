"""Read-only CBD symptom reach, evidence completeness, cost and parity metrics.

This module does not transform co-occurrence into causes, forecast merges,
or interpret repeated PR/job observations as independent statistical trials.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

FAMILY_PRIORITY = {
    "SECURITY": ("P0", "SECURITY_READER"),
    "QUALITY": ("P1", "QUALITY_OWNER"),
    "COVERAGE": ("P1", "COVERAGE_OWNER"),
    "DOWNSTREAM_SUMMARY": ("DEPENDENT", "NO_SOURCE_LEASE"),
}
OBSERVED = {"OBSERVED", "SOURCE_BOUND"}


def require(test, reason):
    if not test:
        raise ValueError(reason)


def check_graph(g):
    """Validate graph-level source and denominator facts before scoring."""
    require(isinstance(g, dict)
            and g.get("schema") == "cbd.e2e.evidence_multigraph.v1",
            "invalid graph schema")
    auth = g.get("authority", {})
    require(auth.get("merge_admission") == "HOLD"
            and auth.get("security_waiver") is False
            and auth.get("causal_root_promoted") is False,
            "graph authority promoted")
    nodes = g.get("nodes")
    edges = g.get("edges")
    require(isinstance(nodes, list) and isinstance(edges, list),
            "missing graph atoms")
    ids = [n.get("id") for n in nodes]
    require(all(isinstance(x, str) and x for x in ids)
            and len(ids) == len(set(ids)), "duplicate or missing node")
    keys = set(ids)
    evidence = Counter()
    for e in edges:
        require(e.get("source") in keys and e.get("target") in keys,
                "dangling graph edge")
        require(e.get("causal_confirmed") is False,
                "unproven causal edge promoted")
        kind = e.get("evidence")
        require(kind in ("OBSERVED", "SOURCE_BOUND", "ASSOCIATION",
                         "TEMPORAL_ASSOCIATION", "DECLARED"),
                "unrecognized edge evidence")
        require(type(e.get("support")) is int and e["support"] >= 0,
                "invalid edge support")
        if kind == "DECLARED":
            require(e["support"] == 0, "declared edge claimed observation")
        if kind == "ASSOCIATION":
            j = e.get("jaccard")
            require(type(j) in (float, int) and 0 < j <= 1,
                    "invalid association overlap")
        evidence[kind] += 1
    m = g.get("metrics", {})
    require(m.get("node_count") == len(nodes)
            and m.get("edge_count") == len(edges),
            "graph length mismatch")
    require(evidence == Counter(m.get("edge_evidence_classes")),
            "graph evidence denominator mismatch")
    require(m.get("confirmed_causal_root_edges") == 0
            and m.get("matched_coverage_delta") is None,
            "unearned causal/coverage credit")
    return {n["id"]: n for n in nodes}


def project(g):
    """Compute linked symptom reach, noncausal concentrations and runtime costs."""
    nodes = check_graph(g)
    edges = g["edges"]
    attempts = {}
    native_runs = {}
    job_prs = {}
    job_attempts = {}
    for e in edges:
        rel = e["relationship"]
        if rel == "native_attempt":
            attempts[e["target"]] = e["source"]
        elif rel == "executed_job":
            job_attempts[e["target"]] = e["source"]
        elif rel == "native_job_run":
            native_runs[e["target"]] = e["source"]
    for job, attempt in job_attempts.items():
        run = attempts.get(attempt)
        require(run is not None and run in native_runs,
                "job loses native run provenance")
        head = native_runs[run]
        require(head.startswith("head:"), "non-head run owner")
        pr = nodes[head]["attributes"].get("pr")
        require(type(pr) is int, "missing native PR source identity")
        job_prs[job] = (pr, run)
    groups = defaultdict(lambda: {
        "prs": set(), "runs": set(), "job_ids": set(), "jobs": 0,
        "measured_jobs": 0, "duration_sum_ms": 0, "missing_ms": 0,
        "failed_step_edges": 0,
    })
    upstream = Counter()
    for e in edges:
        if e["relationship"] != "failed_job_symptom":
            continue
        j, family_key = e["source"], e["target"]
        require(j in job_prs and family_key.startswith("jobfamily:"),
                "orphaned failed job")
        name = family_key.split(":", 1)[1]
        require(name in FAMILY_PRIORITY, "unclassified family needs reader")
        pr, run = job_prs[j]
        rec = groups[name]
        rec["prs"].add(pr)
        rec["runs"].add(run)
        require(j not in rec["job_ids"], "duplicate failed-job root edge")
        rec["job_ids"].add(j)
        rec["jobs"] += 1
        runtime = nodes[j]["attributes"].get("runtime_ms")
        if runtime is None:
            rec["missing_ms"] += 1
        else:
            require(type(runtime) is int and runtime >= 0,
                    "invalid job run duration")
            rec["measured_jobs"] += 1
            rec["duration_sum_ms"] += runtime
        if name != "DOWNSTREAM_SUMMARY":
            upstream[pr] += 1
    require(sum(x["jobs"] for x in groups.values()) ==
            g["metrics"]["native_failed_jobs"],
            "failed-job denominator inconsistent with native graph")
    for e in edges:
        if e["relationship"] == "failed_at_step":
            job = e["source"]
            for name, group in groups.items():
                if job in group["job_ids"]:
                    group["failed_step_edges"] += 1
                    break
    require(sum(x["failed_step_edges"] for x in groups.values()) ==
            g["metrics"]["native_failed_steps"],
            "failed-step denominator inconsistent with native graph")
    families = []
    for name, entry in groups.items():
        priority, owner = FAMILY_PRIORITY[name]
        families.append({
            "family": name, "priority": priority,
            "candidate_reader_lease": owner,
            "affected_prs": sorted(entry["prs"]),
            "unique_prs_affected": len(entry["prs"]),
            "failed_job_manifestations": entry["jobs"],
            "failed_steps_observed": entry["failed_step_edges"],
            "native_runs_affected": len(entry["runs"]),
            "measured_runtime_jobs": entry["measured_jobs"],
            "runtime_unmeasured_jobs": entry["missing_ms"],
            "sum_measured_job_runtime_ms": entry["duration_sum_ms"],
            "potential_unblock_pr_upper_bound": len(entry["prs"]) if name !=
            "DOWNSTREAM_SUMMARY" else None,
            "actual_unblocked_prs": None,
            "confirmed_root_count": None,
            "owner_mutation_authorized": False,
        })
    families.sort(key=lambda f: (
        {"P0": 0, "P1": 1, "DEPENDENT": 2}[f["priority"]],
        -f["unique_prs_affected"], f["family"],
    ))
    overlaps = []
    for e in edges:
        if e["relationship"] == "same_PR_head_cooccurrence":
            overlaps.append({
                "workflow_a": nodes[e["source"]]["label"],
                "workflow_b": nodes[e["target"]]["label"],
                "shared_prs": e["support"],
                "jaccard": e["jaccard"],
                "confirmed_common_cause": None,
            })
    overlaps.sort(key=lambda x: (
        -x["shared_prs"], -x["jaccard"],
        x["workflow_a"], x["workflow_b"],
    ))
    m = g["metrics"]
    return {
        "schema": "cbd.e2e.wave_effectiveness.v1",
        "scope": g.get("scope"),
        "authority": {
            "merge_admission": "HOLD", "security_waiver": False,
            "worker_dispatch": "NOT_AUTHORIZED_BY_METRICS",
        },
        "observed": {
            "pr_heads": m["cohort_pr_heads"],
            "workflow_associations": m["cohort_workflow_associations"],
            "failed_workflow_associations": m["failed_workflow_associations"],
            "native_runs": m["native_run_count"],
            "native_jobs": m["native_job_count"],
            "failed_native_jobs": m["native_failed_jobs"],
            "failed_native_steps": m["native_failed_steps"],
            "upstream_failed_job_prs": len(upstream),
            "upstream_failed_job_manifestations": sum(
                f["failed_job_manifestations"] for f in families
                if f["priority"] != "DEPENDENT"),
            "downstream_failed_job_manifestations": sum(
                f["failed_job_manifestations"] for f in families
                if f["priority"] == "DEPENDENT"),
            "source_bound_edges": m["edge_evidence_classes"].get("SOURCE_BOUND", 0),
            "native_observed_edges": m["edge_evidence_classes"].get("OBSERVED", 0),
            "cooccurrence_edges": len(overlaps),
            "temporal_noncausal_edges": m["edge_evidence_classes"].get(
                "TEMPORAL_ASSOCIATION", 0),
            "declared_unexecuted_stage_edges": m["edge_evidence_classes"].get(
                "DECLARED", 0),
            "job_runtime_p50_ms": m.get("temporal", {}).get(
                "duration_p50_ms_nearest_rank"),
            "job_runtime_p95_ms": m.get("temporal", {}).get(
                "duration_p95_ms_nearest_rank"),
            "matched_changed_line_coverage": None,
            "matched_main_coverage": None,
            "total_verified_causal_roots": None,
            "total_verified_pr_unblocks": None,
            "actual_runner_queue_wait_ms": None,
        },
        "candidate_job_families": families,
        "top_cooccurrence_edges": overlaps[:12],
        "metrics_policy": {
            "observed_job_runtime_is_not_ci_walltime": True,
            "affected_pr_count_is_upper_bound_not_unblock_forecast": True,
            "cooccurrence_is_noncausal": True,
            "nonrandom_pr_cohort_cannot_yield_fleet_confidence_interval": True,
            "covered_lines_and_branches_unknown": True,
        },
    }


def comparable_delta(a, b):
    """Compare evidence only when exact source/job/attempt topology is matched."""
    check_graph(a)
    check_graph(b)
    def identity(g):
        return sorted((
            n["id"], n["attributes"].get("sha"),
            n["attributes"].get("run_attempt"),
            n["attributes"].get("conclusion"))
            for n in g["nodes"] if n["kind"] in (
                "head", "run", "attempt", "job"))
    matched = identity(a) == identity(b)
    return {
        "schema": "cbd.e2e.matched_wave_delta.v1",
        "matched_native_topology": matched,
        "status": "EVIDENCE_COMPARABLE" if matched else "HOLD_HEAD_OR_ATTEMPT_DRIFT",
        "new_source_bound_edges": (
            b["metrics"]["edge_evidence_classes"].get("SOURCE_BOUND", 0) -
            a["metrics"]["edge_evidence_classes"].get("SOURCE_BOUND", 0)
            if matched else None),
        "new_observed_edges": (
            b["metrics"]["edge_evidence_classes"].get("OBSERVED", 0) -
            a["metrics"]["edge_evidence_classes"].get("OBSERVED", 0)
            if matched else None),
        "coverage_percentage_delta": None,
        "causal_root_closure_delta": None,
        "merge_admission": "HOLD",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("graph", type=Path)
    parser.add_argument("--before", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    after = load(args.graph)
    result = project(after)
    if args.before:
        result["matched_wave_delta"] = comparable_delta(
            load(args.before), after)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result["observed"], sort_keys=True))


if __name__ == "__main__":
    main()
