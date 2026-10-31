"""Typed federation acceptance DAG, SIPOC, and non-causal blocker fan-out."""

from __future__ import annotations

from collections import Counter, defaultdict

from .core import REPOS, canonical, digest, require

REPO_PLANES = {
    "GBOGEB/ABACUS": "runtime_evidence_and_BD_authority",
    "GBOGEB/CODEX": "mission_control_governance_consumer",
    "GBOGEB/cryoplant-project": "QPS_engineering_consumer",
}


def graph_projection(projection):
    require(
        projection.get("schema") == "codepurple.acceptance.projection.v1",
        "invalid source projection",
    )
    requirements = projection["obligations"]
    by_id = {item["id"]: item for item in requirements}
    require(len(by_id) == len(requirements), "duplicate graph obligation")
    nodes, edges = {}, set()

    def node(node_id, kind, **details):
        require(node_id not in nodes, "duplicate typed graph node")
        nodes[node_id] = {"id": node_id, "kind": kind, **details}

    def edge(a, b, kind):
        edges.add((a, b, kind))

    for repo in REPOS:
        root = "repo:" + repo
        context = projection["source_contexts"][repo]
        node(root, "REPOSITORY", repo=repo, authority=REPO_PLANES[repo])
        context_id = "context:" + repo
        node(
            context_id,
            "EXACT_HEAD_CONTEXT",
            source_sha=context["head_sha"],
            base_sha=context["base_sha"],
            policy_sha=context["policy_sha"],
            epoch=context["epoch"],
            ref=context["ref"],
        )
        edge(root, context_id, "SOURCE_CONTEXT")

    for item in requirements:
        key = "obligation:" + item["id"]
        node(
            key,
            "ACCEPTANCE_OBLIGATION",
            repo=item["repo"],
            title=item["title"],
            evidence_state=item["evidence_state"],
            admission_state="HOLD",
            observed=item["evidence_checked"],
        )
        edge("context:" + item["repo"], key, "CONTEXTUALIZES")
        for required_id in item["depends_on"]:
            require(required_id in by_id, "missing required graph atom")
            edge("obligation:" + required_id, key, "DEPENDS_ON")
        obs_id = item["latest_observation_id"]
        if obs_id:
            obs_key = "observation:" + obs_id
            require(obs_key not in nodes, "observation ID reused across obligations")
            node(
                obs_key,
                "EVIDENCE_OBSERVATION",
                source_sha=item["latest_subject_sha"],
                epoch=item["latest_epoch"],
                authenticated=False,
                evidence_state=item["evidence_state"],
            )
            edge(obs_key, key, "OBSERVES_NOT_AUTHORIZES")

    sorted_edges = [{"from": a, "to": b, "kind": k} for a, b, k in sorted(edges)]
    forward = defaultdict(set)
    for a, b, kind in edges:
        if kind == "DEPENDS_ON":
            forward[a].add(b)

    def descendants(atom):
        found = set()
        stack = list(forward[atom])
        while stack:
            v = stack.pop()
            if v not in found:
                found.add(v)
                stack.extend(forward[v])
        return found

    reach = {}
    for item in requirements:
        key = "obligation:" + item["id"]
        reach[item["id"]] = len(descendants(key))
    # This is downstream dependency reach, NOT estimated probability of fixing reds.
    blocking = sorted(
        (
            {
                "id": item["id"],
                "repo": item["repo"],
                "observed_state": item["evidence_state"],
                "downstream_dependency_reach": reach[item["id"]],
                "shared_causal_root_confirmed": None,
            }
            for item in requirements
            if not item["evidence_checked"]
        ),
        key=lambda row: (-row["downstream_dependency_reach"], row["id"]),
    )
    counts = Counter(n["kind"] for n in nodes.values())
    result = {
        "schema": "codepurple.acceptance.graph.v1",
        "source_projection_sha256": digest(
            {k: v for k, v in projection.items() if k != "ledger"}
        ),
        "nodes": [nodes[k] for k in sorted(nodes)],
        "edges": sorted_edges,
        "metrics": {
            "nodes": len(nodes),
            "edges": len(edges),
            "repo_nodes": counts["REPOSITORY"],
            "context_nodes": counts["EXACT_HEAD_CONTEXT"],
            "obligation_nodes": counts["ACCEPTANCE_OBLIGATION"],
            "observation_nodes": counts["EVIDENCE_OBSERVATION"],
            "dependency_edges": sum(e["kind"] == "DEPENDS_ON" for e in sorted_edges),
            "cross_repo_dependencies": sum(
                1
                for e in sorted_edges
                if e["kind"] == "DEPENDS_ON"
                and by_id[e["from"].split(":", 1)[1]]["repo"]
                != by_id[e["to"].split(":", 1)[1]]["repo"]
            ),
            "canonical_roots_closed": None,
        },
        "blocked_frontier": blocking,
        "safety": {
            "graph_edges_are_not_causal_proof": True,
            "owner_authority_transfer": False,
            "main_admission": "HOLD",
        },
    }
    require(
        len(result["nodes"]) == len({x["id"] for x in result["nodes"]}),
        "duplicate graph atom",
    )
    return result


def sipoc(projection):
    require(projection.get("admission") == "HOLD", "cannot elevate release")
    steps = [
        "N0: observe immutable contract, source/base/policy/epoch contexts",
        "N1: ingest path-disjoint contributor receipts and reject collisions",
        "N2: project evidence debt, root-candidate edges and authority boundaries",
        "N3: run positive, negative, reverse, A-B-A and stability tests",
        "N4: obtain independent native/owner attestation; remain HOLD otherwise",
        "N5: after separately authorized merge, recheck protected main and REX",
    ]
    mapping = {}
    for repo in REPOS:
        mapping[repo] = {
            "plane": REPO_PLANES[repo],
            "supplier": "GitHub repository-native evidence, not reader claims",
            "input": "Exact source SHA, base SHA, policy SHA, monotone epoch, evidence digest",
            "process": steps,
            "output": "Source-bound observation proposals, human debt checklist and graph",
            "consumer": (
                "BD-LDAB #1929, ABACUS admission #1860"
                if repo.endswith("ABACUS")
                else (
                    "Mission Control #977"
                    if repo.endswith("CODEX")
                    else "QPS engineering owner; no runtime approval authority"
                )
            ),
            "authority_transfer": False,
        }
    return {
        "schema": "codepurple.acceptance.sipoc.v1",
        "sources": mapping,
        "read_only": True,
        "ledger_is_canonical": False,
        "admission": "HOLD",
    }


def check_graph_acyclic(graph):
    by_id = {n["id"] for n in graph["nodes"]}
    outgoing = defaultdict(set)
    for edge in graph["edges"]:
        require(edge["from"] in by_id and edge["to"] in by_id, "dangling graph edge")
        outgoing[edge["from"]].add(edge["to"])
    color = {}

    def visit(n):
        require(color.get(n) != 1, "cycle in typed acceptance graph")
        if color.get(n) == 2:
            return
        color[n] = 1
        for m in sorted(outgoing[n]):
            visit(m)
        color[n] = 2

    for key in sorted(by_id):
        visit(key)
    return True
