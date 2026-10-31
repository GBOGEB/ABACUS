"""Fail-closed read-only validator for historical CBD E2E evidence multigraph v1.

Does not infer causality, native source authentication, DoD/DoV credit or
protected-branch merge status. Complements the 14 graph-atlas tests.
"""

from __future__ import annotations

import math
import re
from collections import Counter

SHA = re.compile(r"[0-9a-f]{40}\Z")
KINDS = {"DECLARED", "OBSERVED", "SOURCE_BOUND", "ASSOCIATION", "TEMPORAL_ASSOCIATION"}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def audit(graph):
    require(
        isinstance(graph, dict)
        and graph.get("schema") == "cbd.e2e.evidence_multigraph.v1",
        "invalid graph schema",
    )
    require(graph.get("repository") == "GBOGEB/ABACUS", "invalid graph repository")
    auth = graph.get("authority") or {}
    require(
        auth.get("merge_admission") == "HOLD"
        and auth.get("security_waiver") is False
        and auth.get("causal_root_promoted") is False,
        "graph authority escalation",
    )
    nodes, edges, metrics = graph.get("nodes"), graph.get("edges"), graph.get("metrics")
    require(
        isinstance(nodes, list)
        and isinstance(edges, list)
        and isinstance(metrics, dict),
        "invalid graph population",
    )
    identities = set()
    kinds = Counter()
    for node in nodes:
        require(
            isinstance(node, dict)
            and isinstance(node.get("id"), str)
            and node["id"]
            and node["id"] not in identities,
            "duplicate or invalid graph node identity",
        )
        identities.add(node["id"])
        require(
            isinstance(node.get("kind"), str)
            and node["kind"]
            and isinstance(node.get("label"), str),
            "invalid graph node",
        )
        require(
            type(node.get("rank")) is int and node["rank"] >= 0, "invalid node rank"
        )
        require(isinstance(node.get("attributes"), dict), "invalid node attributes")
        require(
            type(node.get("degree")) is int and node["degree"] >= 0,
            "invalid node degree",
        )
        require(
            type(node.get("observed_weighted_degree")) is int
            and node["observed_weighted_degree"] >= 0,
            "invalid weighted degree",
        )
        if node["kind"] == "head":
            require(
                isinstance(node["attributes"].get("sha"), str)
                and SHA.fullmatch(node["attributes"]["sha"]),
                "invalid exact-head SHA",
            )
        if node["kind"] == "job":
            require(
                type(node["attributes"].get("run_attempt")) is int
                and node["attributes"]["run_attempt"] >= 1,
                "invalid job attempt",
            )
        kinds[node["kind"]] += 1
    seen_edges = set()
    evidence = Counter()
    for edge in edges:
        require(
            isinstance(edge, dict)
            and edge.get("source") in identities
            and edge.get("target") in identities,
            "dangling graph edge",
        )
        relationship = edge.get("relationship")
        cls = edge.get("evidence")
        require(
            isinstance(relationship, str) and relationship and cls in KINDS,
            "invalid graph edge class",
        )
        key = (edge["source"], edge["target"], relationship, cls)
        require(key not in seen_edges, "duplicate graph edge")
        seen_edges.add(key)
        require(
            type(edge.get("support")) is int and edge["support"] >= 0,
            "invalid edge support",
        )
        require(edge.get("causal_confirmed") is False, "unproven causal edge promotion")
        if cls == "DECLARED":
            require(edge["support"] == 0, "declared edge falsely counted as observed")
        else:
            require(edge["support"] > 0, "unsupported observed edge")
        j = edge.get("jaccard")
        if cls == "ASSOCIATION":
            require(
                isinstance(j, (int, float))
                and not isinstance(j, bool)
                and math.isfinite(j)
                and 0 < j <= 1,
                "invalid association Jaccard",
            )
        else:
            require(j is None, "Jaccard attached to non-association edge")
        if cls == "TEMPORAL_ASSOCIATION":
            gap = edge.get("overlap_ms")
            require(type(gap) is int and gap >= 0, "invalid temporal overlap duration")
        evidence[cls] += 1
    require(
        metrics.get("node_count") == len(nodes)
        and type(metrics.get("node_count")) is int,
        "graph node denominator mismatch",
    )
    require(
        metrics.get("edge_count") == len(edges)
        and type(metrics.get("edge_count")) is int,
        "graph edge denominator mismatch",
    )
    require(metrics.get("node_types") == dict(kinds), "graph node-kind census mismatch")
    require(
        metrics.get("edge_evidence_classes") == dict(evidence),
        "graph evidence census mismatch",
    )
    require(
        metrics.get("confirmed_causal_root_edges") == 0, "causal-root count promotion"
    )
    temporal = metrics.get("temporal")
    if temporal is not None:
        require(isinstance(temporal, dict), "invalid temporal evidence")
        total = temporal.get("native_jobs_source_matched")
        measured = temporal.get("measured_completed_job_durations")
        censored = temporal.get("censored_or_unmeasured_jobs")
        require(
            all(type(x) is int and x >= 0 for x in (total, measured, censored))
            and measured + censored == total,
            "temporal job denominator mismatch",
        )
        p50, p95 = temporal.get("duration_p50_ms_nearest_rank"), temporal.get(
            "duration_p95_ms_nearest_rank"
        )
        require(
            all(type(x) is int and x >= 0 for x in (p50, p95)) and p95 >= p50,
            "invalid temporal duration quantiles",
        )
        require(
            temporal.get("actual_runner_queue_wait_ms") is None,
            "unverified runner queue promoted",
        )
    return {
        "schema": "cbd.e2e.graph_snapshot_audit.v1",
        "node_count": len(nodes),
        "edge_count": len(edges),
        "association_edges": evidence["ASSOCIATION"],
        "temporal_associations": evidence["TEMPORAL_ASSOCIATION"],
        "causal_root_credit": 0,
        "merge_admission": "HOLD",
        "authority_transfer": False,
    }
