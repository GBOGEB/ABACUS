#!/usr/bin/env python3
"""CBD W48 read-only, exact-SHA evidence/DAG/RECURSE projection.

Only validates explicitly supplied local JSON. Never accesses GitHub, executes
jobs, declares reviewer approval, or promotes a reported receipt to attestation.
"""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import re
from pathlib import Path, PurePosixPath

import yaml

SCHEMA = "cbd.recurse.input.v1"
OUTPUT_SCHEMA = "cbd.recurse.structural.v1"
SHA = re.compile(r"^[a-f0-9]{40}$")
DIGEST = re.compile(r"^[a-f0-9]{64}$")
IDENT = re.compile(r"^[A-Za-z0-9._:-]{1,90}$")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
STATES = {"queued", "in_progress", "completed", "staged", "unknown"}
CONCLUSIONS = {"success", "failure", "cancelled", "skipped", "timed_out"}
EDGE_KINDS = {"depends_on", "observes", "fanout", "lineage"}
NODE_KINDS = {"native", "local", "proposal"}
TASK_STATES = {"pending", "running", "blocked", "done"}
TASK_KINDS = {"read_only", "mutating", "approval"}
NODE_KEYS = {
    "id",
    "repository",
    "branch",
    "sha",
    "segment",
    "kind",
    "status",
    "conclusion",
    "run_id",
    "attempt",
    "job_id",
    "first_red",
    "coverage",
}
TASK_KEYS = {
    "id",
    "segment",
    "pool",
    "paths",
    "depends_on",
    "state",
    "kind",
    "approval_required",
    "evidence_node",
}
COVERAGE_KEYS = {
    "scope",
    "tool",
    "cell",
    "source_blob_sha",
    "statements",
    "branches",
    "artifact_url",
    "artifact_sha256",
}


def _exact(obj, expected, what):
    if not isinstance(obj, dict) or set(obj) != expected:
        raise ValueError(f"{what}: required keys or unapproved fields")


def _id(value):
    return isinstance(value, str) and bool(IDENT.fullmatch(value))


def _positive(value):
    return type(value) is int and value > 0


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _coverage(raw, node):
    if raw is None:
        return None
    _exact(raw, COVERAGE_KEYS, "coverage")
    if (
        node["kind"] != "native"
        or node["status"] != "completed"
        or node["conclusion"] != "success"
        or node["job_id"] is None
    ):
        raise ValueError("coverage requires successful native job identity")
    for name in ("scope", "tool", "cell"):
        if not _id(raw[name]):
            raise ValueError("invalid coverage scope/tool/cell")
    if not isinstance(raw["source_blob_sha"], str) or not SHA.fullmatch(
        raw["source_blob_sha"]
    ):
        raise ValueError("coverage must bind exact source blob")
    if not isinstance(raw["artifact_sha256"], str) or not DIGEST.fullmatch(
        raw["artifact_sha256"]
    ):
        raise ValueError("missing artifact digest")
    prefix = f'https://github.com/{node["repository"]}/actions/runs/{node["run_id"]}/artifacts/'
    if (
        not isinstance(raw["artifact_url"], str)
        or not raw["artifact_url"].startswith(prefix)
        or not raw["artifact_url"][len(prefix) :].isdigit()
    ):
        raise ValueError("artifact URL does not bind to native run")
    for kind in ("statements", "branches"):
        pair = raw[kind]
        _exact(pair, {"covered", "eligible"}, f"{kind} coverage")
        c, d = pair["covered"], pair["eligible"]
        if type(c) is not int or not _positive(d) or c < 0 or c > d:
            raise ValueError("invalid coverage numerator/denominator")
    return raw


def _nodes(rows, segments):
    if not isinstance(rows, list) or not rows or len(rows) > 256:
        raise ValueError("1..256 native/local nodes required")
    found, native = {}, set()
    for node in rows:
        _exact(node, NODE_KEYS, "node")
        name = node["id"]
        if not _id(name) or name in found:
            raise ValueError("duplicate or invalid node ID")
        if (
            node["segment"] not in segments
            or not _id(node["branch"])
            or not REPO.fullmatch(node["repository"])
        ):
            raise ValueError("invalid node segment/branch/repository")
        if not isinstance(node["sha"], str) or not SHA.fullmatch(node["sha"]):
            raise ValueError("node exact SHA required")
        if node["kind"] not in NODE_KINDS or node["status"] not in STATES:
            raise ValueError("invalid node kind/status")
        if node["status"] == "completed":
            if node["conclusion"] not in CONCLUSIONS:
                raise ValueError("terminal node must have conclusion")
        elif node["conclusion"] is not None:
            raise ValueError("nonterminal node cannot have conclusion")
        ids = (node["run_id"], node["attempt"], node["job_id"])
        if ids[0] is None:
            if any(x is not None for x in ids[1:]):
                raise ValueError("partial native run identity")
        elif (
            not _positive(ids[0])
            or not _positive(ids[1])
            or (ids[2] is not None and not _positive(ids[2]))
        ):
            raise ValueError("invalid native run/job/attempt identity")
        if (
            node["kind"] == "native"
            and node["status"] == "completed"
            and ids[0] is None
        ):
            raise ValueError("completed native observation requires run identity")
        if node["kind"] != "native" and any(x is not None for x in ids):
            raise ValueError("local/proposal nodes cannot claim hosted run identities")
        if ids[2] is not None:
            key = (node["repository"], *ids)
            if key in native:
                raise ValueError("duplicate native job/attempt")
            native.add(key)
        fp = node["first_red"]
        if fp is not None and (
            not _id(fp)
            or node["status"] != "completed"
            or node["conclusion"] != "failure"
        ):
            raise ValueError(
                "first-red requires terminal failure and stable identifier"
            )
        _coverage(node["coverage"], node)
        found[name] = node
    return dict(sorted(found.items()))


def _toposort(names, edges):
    downstream = {name: set() for name in names}
    degree = {name: 0 for name in names}
    for edge in edges:
        if edge["from"] not in downstream or edge["to"] not in downstream:
            raise ValueError("orphan DAG edge")
        if edge["to"] not in downstream[edge["from"]]:
            downstream[edge["from"]].add(edge["to"])
            degree[edge["to"]] += 1
    queue = [key for key, value in degree.items() if value == 0]
    heapq.heapify(queue)
    result = []
    while queue:
        name = heapq.heappop(queue)
        result.append(name)
        for next_name in sorted(downstream[name]):
            degree[next_name] -= 1
            if degree[next_name] == 0:
                heapq.heappush(queue, next_name)
    if len(result) != len(names):
        raise ValueError("cyclic DAG")
    return result, downstream


def _edges(raw, nodes):
    if not isinstance(raw, list) or len(raw) > 1024:
        raise ValueError("edge list exceeds bounded contract")
    seen, result = set(), []
    for edge in raw:
        _exact(edge, {"from", "to", "kind"}, "edge")
        if edge["kind"] not in EDGE_KINDS or edge["from"] == edge["to"]:
            raise ValueError("invalid edge kind/self edge")
        key = (edge["from"], edge["to"], edge["kind"])
        if key in seen:
            raise ValueError("duplicate typed edge")
        seen.add(key)
        result.append(edge)
    result.sort(key=lambda e: (e["from"], e["to"], e["kind"]))
    order, downstream = _toposort(nodes, result)
    return result, order, downstream


def _path(value):
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or value.startswith("/")
        or ":" in value
    ):
        return False
    p = PurePosixPath(value)
    return p.as_posix() == value and ".." not in p.parts and len(value) <= 220


def _tasks(raw, nodes, segments, pools, wave_limit):
    if not isinstance(raw, list) or len(raw) > 256:
        raise ValueError("task population exceeds bound")
    tasks = {}
    for task in raw:
        _exact(task, TASK_KEYS, "task")
        name = task["id"]
        if not _id(name) or name in tasks:
            raise ValueError("duplicate or invalid task")
        if task["segment"] not in segments or task["pool"] not in pools:
            raise ValueError("invalid task segment/pool")
        if (
            task["state"] not in TASK_STATES
            or task["kind"] not in TASK_KINDS
            or type(task["approval_required"]) is not bool
        ):
            raise ValueError("invalid task state/kind/approval")
        paths = task["paths"]
        if (
            not isinstance(paths, list)
            or not paths
            or len(paths) > 16
            or any(not _path(p) for p in paths)
            or len(set(paths)) != len(paths)
        ):
            raise ValueError("invalid or overlapping task paths")
        deps = task["depends_on"]
        if (
            not isinstance(deps, list)
            or len(deps) > 64
            or len(set(deps)) != len(deps)
            or any(not _id(d) for d in deps)
        ):
            raise ValueError("invalid task dependencies")
        evidence = task["evidence_node"]
        if task["state"] == "done":
            if (
                evidence not in nodes
                or nodes[evidence]["kind"] != "native"
                or nodes[evidence]["conclusion"] != "success"
                or nodes[evidence]["job_id"] is None
            ):
                raise ValueError("done task requires successful native job observation")
        elif evidence is not None:
            raise ValueError("unfinished task cannot cite terminal evidence as done")
        tasks[name] = task
    dependency_edges = []
    for task in tasks.values():
        for dep in task["depends_on"]:
            dependency_edges.append(
                {"from": dep, "to": task["id"], "kind": "depends_on"}
            )
    _toposort(tasks, dependency_edges)
    selected, reasons, uses = [], {}, {key: 0 for key in pools}
    locked = []
    for name, task in sorted(tasks.items(), key=lambda kv: kv[0]):
        if task["state"] != "pending":
            reasons[name] = "NOT_PENDING"
        elif task["kind"] != "read_only" or task["approval_required"]:
            reasons[name] = "MANUAL_OR_MUTATING_HELD"
        elif any(tasks[d]["state"] != "done" for d in task["depends_on"]):
            reasons[name] = "UPSTREAM_NOT_VERIFIED"
        elif len(selected) >= wave_limit:
            reasons[name] = "WAVE_CAP"
        elif uses[task["pool"]] >= pools[task["pool"]]:
            reasons[name] = "POOL_CAP"
        elif any(
            a == b or a.startswith(b + "/") or b.startswith(a + "/")
            for a in task["paths"]
            for b in locked
        ):
            reasons[name] = "PATH_LOCK"
        else:
            selected.append(name)
            uses[task["pool"]] += 1
            locked.extend(task["paths"])
            reasons[name] = "READY_READ_ONLY_NOT_LAUNCHED"
    return dict(sorted(tasks.items())), {
        "candidates": selected,
        "decisions": reasons,
        "pool_slots_selected": uses,
        "execution_performed": False,
    }


def _comparisons(rows, nodes):
    if not isinstance(rows, list) or len(rows) > 128:
        raise ValueError("too many matched comparisons")
    matches = []
    seen = set()
    for row in rows:
        _exact(row, {"before", "after"}, "comparison")
        identity = (row["before"], row["after"])
        if (
            identity in seen
            or any(key not in nodes for key in identity)
            or identity[0] == identity[1]
        ):
            raise ValueError("duplicate, identical or orphan comparison")
        seen.add(identity)
        a, b = (nodes[key] for key in identity)
        if a["coverage"] is None or b["coverage"] is None:
            raise ValueError("matched comparison requires native coverage receipts")
        x, y = a["coverage"], b["coverage"]
        if (
            a["repository"] != b["repository"]
            or a["segment"] != b["segment"]
            or x["source_blob_sha"] != y["source_blob_sha"]
            or x["scope"] != y["scope"]
            or x["tool"] != y["tool"]
            or x["cell"] != y["cell"]
            or any(
                x[k]["eligible"] != y[k]["eligible"] for k in ("statements", "branches")
            )
        ):
            raise ValueError("not matched: source blob, tool, cell or denominator")
        pairs = {
            name: {
                "before": x[name]["covered"],
                "after": y[name]["covered"],
                "eligible": x[name]["eligible"],
                "delta": y[name]["covered"] - x[name]["covered"],
            }
            for name in ("statements", "branches")
        }
        matches.append(
            {
                "before": a["id"],
                "after": b["id"],
                "scope": x["scope"],
                "source_blob_sha": x["source_blob_sha"],
                "measures": pairs,
                "acceptance": "CANDIDATE_LOCAL_VALIDATION_ONLY",
            }
        )
    return sorted(matches, key=lambda x: (x["before"], x["after"]))


def compile_snapshot(payload, manifest):
    _exact(
        payload, {"schema", "control", "nodes", "edges", "matches", "tasks"}, "input"
    )
    if payload["schema"] != SCHEMA:
        raise ValueError("unsupported input schema")
    _exact(
        manifest, {"schema", "segments", "pool_capacities", "wave_limit"}, "manifest"
    )
    if manifest["schema"] != "cbd.recurse.local-manifest.v1":
        raise ValueError("manifest schema mismatch")
    segments = manifest["segments"]
    pools = manifest["pool_capacities"]
    wave_limit = manifest["wave_limit"]
    if (
        not isinstance(segments, list)
        or not segments
        or len(set(segments)) != len(segments)
        or any(not _id(x) for x in segments)
    ):
        raise ValueError("invalid manifest segments")
    if (
        not isinstance(pools, dict)
        or not pools
        or any(not _id(k) or not _positive(v) or v > 8 for k, v in pools.items())
        or not _positive(wave_limit)
        or wave_limit > 8
    ):
        raise ValueError("invalid bounded local pool configuration")
    control = payload["control"]
    _exact(control, {"repository", "head_sha", "origin"}, "control")
    if (
        not REPO.fullmatch(control["repository"])
        or not isinstance(control["head_sha"], str)
        or not SHA.fullmatch(control["head_sha"])
    ):
        raise ValueError("invalid control authority identity")
    if control["origin"] not in {"SYNTHETIC", "READ_ONLY_EXPORT"}:
        raise ValueError("unapproved input origin")
    nodes = _nodes(payload["nodes"], segments)
    edges, order, downstream = _edges(payload["edges"], nodes)
    comparisons = _comparisons(payload["matches"], nodes)
    tasks, scheduler = _tasks(payload["tasks"], nodes, segments, pools, wave_limit)
    observations = []
    for key in order:
        node = nodes[key]
        frontier = list(downstream[key])
        found = set()
        while frontier:
            downstream_id = frontier.pop()
            if downstream_id in found:
                continue
            found.add(downstream_id)
            frontier.extend(downstream[downstream_id] - found)
        observations.append(
            {
                "id": key,
                "segment": node["segment"],
                "branch": node["branch"],
                "source_sha": node["sha"],
                "kind": node["kind"],
                "status": node["status"],
                "conclusion": node["conclusion"],
                "first_red_fingerprint": node["first_red"],
                "native_job_identity_present": node["job_id"] is not None,
                "direct_outdegree": len(downstream[key]),
                "reachable_nodes": len(found),
                "reached_segments": sorted(
                    {nodes[other]["segment"] for other in found}
                ),
                "reached_branches": sorted({nodes[other]["branch"] for other in found}),
                "reach_is_causal_proof": False,
            }
        )
    edge_pairs = {}
    branch_pairs = {}
    for edge in edges:
        upstream, downstream_node = (nodes[edge[key]] for key in ("from", "to"))
        sg = (upstream["segment"], downstream_node["segment"])
        br = (
            upstream["repository"] + ":" + upstream["branch"],
            downstream_node["repository"] + ":" + downstream_node["branch"],
        )
        edge_pairs[sg] = edge_pairs.get(sg, 0) + 1
        branch_pairs[br] = branch_pairs.get(br, 0) + 1
    graph_visibility = {
        "segment_flows": [
            {"upstream": a, "downstream": b, "edges": count}
            for (a, b), count in sorted(edge_pairs.items())
        ],
        "branch_flows": [
            {"upstream": a, "downstream": b, "edges": count}
            for (a, b), count in sorted(branch_pairs.items())
        ],
        "cross_segment_edges": sum(
            count for (a, b), count in edge_pairs.items() if a != b
        ),
        "cross_branch_edges": sum(
            count for (a, b), count in branch_pairs.items() if a != b
        ),
        "observed_segment_count": len({n["segment"] for n in nodes.values()}),
        "expected_segment_count": len(segments),
        "penetration_is_native_acceptance": False,
    }
    groups = []
    for segment in sorted(segments):
        selected = [n for n in nodes.values() if n["segment"] == segment]
        groups.append(
            {
                "segment": segment,
                "observed_nodes": len(selected),
                "git_branches": sorted({n["branch"] for n in selected}),
                "distinct_run_attempts": len(
                    {
                        (n["repository"], n["run_id"], n["attempt"])
                        for n in selected
                        if n["run_id"] is not None
                    }
                ),
                "terminal_success_observations": sum(
                    n["kind"] == "native"
                    and n["status"] == "completed"
                    and n["conclusion"] == "success"
                    for n in selected
                ),
                "terminal_failure_observations": sum(
                    n["kind"] == "native"
                    and n["status"] == "completed"
                    and n["conclusion"] == "failure"
                    for n in selected
                ),
                "native_job_receipts_present": sum(
                    n["job_id"] is not None for n in selected
                ),
            }
        )
    first_reds = sorted(
        {n["first_red"] for n in nodes.values() if n["first_red"] is not None}
    )
    result = {
        "schema": OUTPUT_SCHEMA,
        "control": control,
        "dmaic": {
            "DEFINE": "typed cross-stack scope; read-only; branch-specific",
            "MEASURE": {
                "observations": len(nodes),
                "typed_edges": len(edges),
                "distinct_git_branches": len(
                    {(n["repository"], n["branch"]) for n in nodes.values()}
                ),
                "native_job_identities_present": sum(
                    n["job_id"] is not None for n in nodes.values()
                ),
                "candidate_matched_comparisons": len(comparisons),
            },
            "ANALYZE": {
                "candidate_first_red_fingerprints": first_reds,
                "deduplicated_engineering_root_count": None,
            },
            "IMPROVE": scheduler,
            "CONTROL": {
                "admission": "HOLD",
                "authenticated_crew_launch": None,
                "accepted_root_open": None,
                "accepted_root_closed": None,
                "accepted_main_coverage_delta": None,
                "independent_approval": None,
                "execution_performed": False,
            },
        },
        "segments": groups,
        "graph": {
            "topological_order": order,
            "edges": edges,
            "observations": observations,
            "visibility": graph_visibility,
        },
        "matched_coverage_candidates": comparisons,
        "tasks": [
            {
                "id": t["id"],
                "segment": t["segment"],
                "state": t["state"],
                "kind": t["kind"],
                "approval_required": t["approval_required"],
            }
            for t in sorted(tasks.values(), key=lambda x: x["id"])
        ],
        "authority": "READ_ONLY_LOCAL_STRUCTURAL_PROJECTION",
    }
    result["receipt_sha256"] = hashlib.sha256(
        _canonical(result).encode("utf-8")
    ).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = json.loads(
        args.input.read_text(encoding="utf-8"),
        object_pairs_hook=_unique_pairs,
        parse_constant=lambda constant: (_ for _ in ()).throw(
            ValueError("nonfinite JSON constants prohibited")
        ),
    )
    manifest = yaml.safe_load(args.manifest.read_text(encoding="utf-8"))
    result = compile_snapshot(payload, manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(
        "CBD W48: local structural evidence PASS; never native admission",
        result["receipt_sha256"],
    )


if __name__ == "__main__":
    main()
