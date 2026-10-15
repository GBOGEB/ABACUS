"""MIP statistical eligibility: descriptive screening, never approval."""

from __future__ import annotations

import math
import re

SHA = re.compile(r"^[0-9a-f]{40}$")


def _valid_sha(value):
    return isinstance(value, str) and bool(SHA.fullmatch(value))


def _reply(model, reasons, **data):
    return dict(
        schema="abacus.everred.model-readiness.v1",
        model=model,
        decision="NOT_QUALIFIED" if reasons else "FIT_ELIGIBLE_NOT_FITTED",
        reasons=sorted(set(reasons)),
        fitted=False,
        merge_authorized=False,
        authority_transfer=False,
        **data,
    )


def pca_readiness(payload):
    """Process heuristic n >= max(30, 5p); not statistical acceptance."""
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != "abacus.everred.pca.panel.v1"
    ):
        return _reply("PCA", ["INVALID_SCHEMA"])
    reasons = [] if _valid_sha(payload.get("source_sha")) else ["EXACT_SHA_UNKNOWN"]
    rows, columns = payload.get("rows"), payload.get("columns")
    if (
        not isinstance(columns, list)
        or len(columns) < 2
        or len(set(columns)) != len(columns)
    ):
        return _reply("PCA", reasons + ["INVALID_VARIABLES"])
    if not isinstance(rows, list):
        return _reply("PCA", reasons + ["ROWS_MISSING"])
    n, p = len(rows), len(columns)
    ids, matrix = [], []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(
            row.get("independent_unit"), str
        ):
            return _reply("PCA", reasons + ["UNIT_ID_MISSING"], n=n, p=p)
        values = row.get("values")
        if (
            not isinstance(values, list)
            or len(values) != p
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in values)
        ):
            return _reply("PCA", reasons + ["NONFINITE_OR_INCOMPLETE"], n=n, p=p)
        ids.append(row["independent_unit"])
        matrix.append(values)
    if len(set(ids)) != n or "" in ids:
        reasons.append("DEPENDENT_OR_DUPLICATED_UNITS")
    if n < max(30, 5 * p):
        reasons.append("INSUFFICIENT_INDEPENDENT_UNITS")
    if n:
        for j in range(p):
            if max(r[j] for r in matrix) == min(r[j] for r in matrix):
                reasons.append("CONSTANT_VARIABLE")
    # Rank, covariance stability, eigengap and held-out calibration belong
    # to the independently tested fitting provider, not this screening gate.
    return _reply("PCA", reasons, n=n, p=p)


def _reach(node, edges):
    seen, todo = {node}, [node]
    while todo:
        for nxt in edges[todo.pop()]:
            if nxt not in seen:
                seen.add(nxt)
                todo.append(nxt)
    return seen


def bt_readiness(payload):
    """Finite unpenalized BT estimates require a strongly connected win graph."""
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != "abacus.everred.bt.pairs.v1"
    ):
        return _reply("BRADLEY_TERRY", ["INVALID_SCHEMA"])
    reasons = [] if _valid_sha(payload.get("source_sha")) else ["EXACT_SHA_UNKNOWN"]
    names, comparisons = payload.get("items"), payload.get("comparisons")
    if not isinstance(names, list) or len(names) < 2 or len(set(names)) != len(names):
        return _reply("BRADLEY_TERRY", reasons + ["INVALID_ITEMS"])
    if not isinstance(comparisons, list):
        return _reply("BRADLEY_TERRY", reasons + ["PAIRS_MISSING"])
    graph = {x: set() for x in names}
    units = set()
    for pair in comparisons:
        if not isinstance(pair, dict):
            return _reply("BRADLEY_TERRY", reasons + ["INVALID_PAIR"])
        winner, loser = pair.get("winner"), pair.get("loser")
        unit = pair.get("independent_unit")
        if winner not in graph or loser not in graph or winner == loser:
            return _reply("BRADLEY_TERRY", reasons + ["INVALID_PAIR"])
        graph[winner].add(loser)
        if not isinstance(unit, str) or not unit or unit in units:
            reasons.append("NONINDEPENDENT_PAIRS")
        units.add(unit)
    if len(comparisons) < 30:
        reasons.append("SMALL_PAIR_SAMPLE")
    if any(len(_reach(x, graph)) != len(names) for x in names):
        reasons.append("WIN_GRAPH_NOT_STRONGLY_CONNECTED")
    return _reply(
        "BRADLEY_TERRY", reasons, n=len(comparisons), independent_units=len(units)
    )


def reverse_pressure(payload):
    """Directed prerequisite reachability; not hydraulic pressure/probability."""
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != "abacus.everred.blocking-dag.v1"
    ):
        return _reply("REVERSE_PRESSURE", ["INVALID_SCHEMA"])
    reasons = [] if _valid_sha(payload.get("source_sha")) else ["EXACT_SHA_UNKNOWN"]
    nodes, edges = payload.get("nodes"), payload.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return _reply("REVERSE_PRESSURE", reasons + ["GRAPH_MISSING"])
    if any(not isinstance(x, dict) or not isinstance(x.get("id"), str) for x in nodes):
        return _reply("REVERSE_PRESSURE", reasons + ["INVALID_NODE"])
    lookup = {x["id"]: x for x in nodes}
    if len(lookup) != len(nodes):
        return _reply("REVERSE_PRESSURE", reasons + ["DUPLICATED_NODE"])
    adj = {x: set() for x in lookup}
    for edge in edges:
        if (
            not isinstance(edge, dict)
            or edge.get("from") not in adj
            or edge.get("to") not in adj
            or edge.get("from") == edge.get("to")
            or edge.get("causally_supported") is not True
        ):
            return _reply("REVERSE_PRESSURE", reasons + ["UNVERIFIED_EDGE"])
        adj[edge["from"]].add(edge["to"])
    active, finished = set(), set()

    def acyclic(node):
        if node in active:
            return False
        if node in finished:
            return True
        active.add(node)
        if not all(acyclic(child) for child in adj[node]):
            return False
        active.remove(node)
        finished.add(node)
        return True

    if not all(acyclic(x) for x in adj):
        return _reply("REVERSE_PRESSURE", reasons + ["CYCLE"])
    gates = {
        key
        for key, val in lookup.items()
        if val.get("type") == "gate" and val.get("mandatory") is True
    }
    impacts = [
        {"root_id": key, "reachable_mandatory_gates": sorted(_reach(key, adj) & gates)}
        for key, val in lookup.items()
        if val.get("type") == "root" and val.get("causal_status") == "CONFIRMED"
    ]
    impacts.sort(key=lambda x: (-len(x["reachable_mandatory_gates"]), x["root_id"]))
    result = _reply("REVERSE_PRESSURE", reasons, root_impacts=impacts)
    if not reasons:
        result["decision"] = "STRUCTURAL_DIAGNOSTIC_ONLY"
    return result
