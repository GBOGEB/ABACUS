#!/usr/bin/env python3
"""MIP V3 advisory frontier: hard DAG, reverse pressure, and eligible BT.

This is a read-only experimental policy comparator, not a replacement for the
canonical CBD selector, MIP wave governor, CI or release admission.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict
from pathlib import Path

SCHEMA = "codepurple.mip.frontier.v3"
SHA = re.compile(r"^[0-9a-f]{40}$")
STATES = {"pending", "done", "blocked", "running"}
KINDS = {"read_only", "mutation", "approval"}
CRITICAL = {"P0", "P1", "P2"}
RISK = {"LOW", "MEDIUM", "HIGH", "UNKNOWN"}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def count(value, name, minimum=0):
    require(type(value) is int and value >= minimum, "invalid " + name)
    return value


def scalar(value, name, *, positive=False):
    require(
        type(value) in (int, float)
        and math.isfinite(value)
        and (value > 0 if positive else value >= 0),
        "invalid " + name,
    )
    return float(value)


def path_safe(path):
    return (
        isinstance(path, str)
        and bool(path)
        and not path.startswith("/")
        and "\\" not in path
        and ":" not in path
        and not any(ord(c) < 32 or ord(c) == 127 for c in path)
        and all(part not in ("", ".", "..") for part in path.split("/"))
    )


def path_overlap(a, b):
    """Cross-platform conservative lexical leases; not realpath/ACL proof."""
    left, right = a.casefold(), b.casefold()
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


def validate(doc):
    require(isinstance(doc, dict) and doc.get("schema") == SCHEMA, "frontier schema")
    require(
        isinstance(doc.get("source_sha"), str) and SHA.fullmatch(doc["source_sha"]),
        "exact source SHA",
    )
    cap = doc.get("capacity")
    require(isinstance(cap, dict), "capacity required")
    count(cap.get("max_workers"), "max_workers", 1)
    scalar(cap.get("budget_minutes"), "budget", positive=True)
    slots = cap.get("pool_slots")
    require(isinstance(slots, dict) and bool(slots), "pool_slots required")
    for key, value in slots.items():
        require(isinstance(key, str) and bool(key), "invalid pool")
        count(value, "pool capacity")
    rows = doc.get("tasks")
    require(isinstance(rows, list) and 0 < len(rows) <= 256, "bounded tasks")
    tasks = {}
    for row in rows:
        require(isinstance(row, dict), "task object")
        name = row.get("id")
        require(isinstance(name, str) and bool(name) and name not in tasks, "task id")
        require(row.get("state") in STATES, "task state")
        require(row.get("kind") in KINDS, "task kind")
        require(row.get("pool") in slots, "unavailable pool")
        require(row.get("risk") in RISK, "risk class missing")
        deps = row.get("depends_on")
        require(isinstance(deps, list) and len(deps) == len(set(deps)), "task deps")
        paths = row.get("paths")
        require(isinstance(paths, list) and bool(paths), "path claim")
        require(all(path_safe(p) for p in paths), "unsafe path claim")
        require(len(paths) == len(set(paths)), "duplicate path claim")
        cost = row.get("cost_minutes")
        if cost is not None:
            scalar(cost, "cost_minutes", positive=True)
        predicted = row.get("expected_gain")
        if predicted is not None:
            scalar(predicted, "expected_gain")
        missing = row.get("missing_opportunities")
        if missing is not None:
            count(missing, "missing opportunities")
        require(
            row.get("evidence_ref") is None or isinstance(row["evidence_ref"], str),
            "evidence reference",
        )
        tasks[name] = row
    for name, row in tasks.items():
        deps = row["depends_on"]
        require(all(d in tasks and d != name for d in deps), "unresolved predecessor")
        if row["state"] == "done":
            require(all(tasks[d]["state"] == "done" for d in deps), "inconsistent done")
    order = topological(tasks)
    gates = doc.get("gates")
    require(isinstance(gates, list), "gates array")
    ids = set()
    for gate in gates:
        require(isinstance(gate, dict), "gate object")
        name = gate.get("id")
        require(isinstance(name, str) and bool(name) and name not in ids, "gate id")
        ids.add(name)
        require(gate.get("criticality") in CRITICAL, "gate criticality")
        prereqs = gate.get("requires")
        require(
            isinstance(prereqs, list)
            and bool(prereqs)
            and len(prereqs) == len(set(prereqs)),
            "gate prerequisites",
        )
        require(all(p in tasks for p in prereqs), "orphan gate prerequisite")
    comparisons = doc.get("comparisons", [])
    require(isinstance(comparisons, list), "comparison array")
    seen = set()
    for pair in comparisons:
        require(isinstance(pair, dict), "comparison object")
        winner, loser = pair.get("winner"), pair.get("loser")
        require(
            winner in tasks and loser in tasks and winner != loser, "pair endpoints"
        )
        require(pair.get("status") == "NATIVE_MATCHED", "unqualified BT input")
        pair_id = pair.get("pair_id")
        require(
            isinstance(pair_id, str) and bool(pair_id) and pair_id not in seen,
            "pair id",
        )
        seen.add(pair_id)
        require(
            isinstance(pair.get("metric_id"), str) and bool(pair["metric_id"]),
            "metric id",
        )
        require(
            isinstance(pair.get("cohort_id"), str) and bool(pair["cohort_id"]),
            "cohort id",
        )
    return tasks, gates, comparisons, order


def topological(tasks):
    degree = {key: len(row["depends_on"]) for key, row in tasks.items()}
    edges = defaultdict(list)
    for key, row in tasks.items():
        for before in row["depends_on"]:
            edges[before].append(key)
    frontier = sorted(k for k, degree_value in degree.items() if not degree_value)
    ordered = []
    while frontier:
        name = frontier.pop(0)
        ordered.append(name)
        for after in sorted(edges[name]):
            degree[after] -= 1
            if degree[after] == 0:
                frontier.append(after)
                frontier.sort()
    require(len(ordered) == len(tasks), "cyclic hard dependency graph")
    return ordered


def strongly_connected(nodes, pairs):
    def visit(edges, seed):
        seen, stack = set(), [seed]
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            stack.extend(edges.get(node, []))
        return seen

    forward, backward = defaultdict(set), defaultdict(set)
    for pair in pairs:
        forward[pair["winner"]].add(pair["loser"])
        backward[pair["loser"]].add(pair["winner"])
    seed = next(iter(nodes))
    return visit(forward, seed) == nodes and visit(backward, seed) == nodes


def fit_bt(ready, comparisons):
    """Finite Bradley-Terry MLE only on a fully comparable connected panel."""
    nodes = set(ready)
    if len(nodes) < 3 or len(comparisons) < 6:
        return {"status": "BT_INSUFFICIENT_PAIRS", "strengths": None}
    selected = [
        pair
        for pair in comparisons
        if pair["winner"] in nodes and pair["loser"] in nodes
    ]
    contexts = {(p["cohort_id"], p["metric_id"]) for p in selected}
    if len(selected) < 6 or len(contexts) != 1:
        return {"status": "BT_MIXED_OR_MISSING_CONTEXT", "strengths": None}
    if set(p["winner"] for p in selected) | set(p["loser"] for p in selected) != nodes:
        return {"status": "BT_PARTIAL_FRONTIER", "strengths": None}
    if not strongly_connected(nodes, selected):
        return {"status": "BT_UNIDENTIFIABLE_SEPARATION", "strengths": None}
    ids = sorted(nodes)
    wins = {k: 0 for k in ids}
    games = defaultdict(int)
    for pair in selected:
        a, b = pair["winner"], pair["loser"]
        wins[a] += 1
        games[tuple(sorted((a, b)))] += 1
    strengths = {k: 1.0 for k in ids}
    converged = False
    for _ in range(2000):
        proposed = {}
        for name in ids:
            denominator = sum(
                total / (strengths[a] + strengths[b])
                for (a, b), total in games.items()
                if name in (a, b)
            )
            require(denominator > 0, "BT disconnected game")
            proposed[name] = wins[name] / denominator
        if any(value <= 0 for value in proposed.values()):
            return {"status": "BT_NONFINITE_MLE", "strengths": None}
        mean_log = sum(math.log(value) for value in proposed.values()) / len(ids)
        updated = {name: math.exp(math.log(proposed[name]) - mean_log) for name in ids}
        distance = max(abs(math.log(updated[name] / strengths[name])) for name in ids)
        strengths = updated
        if distance < 1e-9:
            converged = True
            break
    if not converged:
        return {"status": "BT_NOT_CONVERGED", "strengths": None}
    return {
        "status": "BT_FITTED_DESCRIPTIVE_NOT_AUTHENTICATED",
        "strengths": {name: round(math.log(strengths[name]), 6) for name in ids},
        "pair_count": len(selected),
        "metric_context": list(contexts)[0],
    }


def pressure(name, tasks, gates):
    immediate = {"P0": 0, "P1": 0, "P2": 0}
    partial = {"P0": 0, "P1": 0, "P2": 0}
    for gate in gates:
        remaining = {p for p in gate["requires"] if tasks[p]["state"] != "done"}
        if name not in remaining:
            continue
        if len(remaining) == 1:
            immediate[gate["criticality"]] += 1
        else:
            partial[gate["criticality"]] += 1
    return {"immediate": immediate, "partial": partial}


def reverse_key(name, scores):
    x = scores[name]
    imm = x["immediate"]
    partial = x["partial"]
    return (
        -imm["P0"],
        -imm["P1"],
        -imm["P2"],
        -partial["P0"],
        -partial["P1"],
        -partial["P2"],
        -x["efficiency"] if x["efficiency"] is not None else float("inf"),
        name,
    )


def reserve(order, tasks, capacity):
    selected, reasons, locked = [], {}, []
    spent = 0.0
    per_pool = {key: 0 for key in capacity["pool_slots"]}
    for name in order:
        row = tasks[name]
        if row["cost_minutes"] is None:
            reasons[name] = "DEFER_UNKNOWN_COST"
        elif len(selected) >= capacity["max_workers"]:
            reasons[name] = "WORKER_SLOT_CAP"
        elif spent + row["cost_minutes"] > capacity["budget_minutes"] + 1e-9:
            reasons[name] = "TIME_BUDGET_CAP"
        elif per_pool[row["pool"]] >= capacity["pool_slots"][row["pool"]]:
            reasons[name] = "POOL_CAP"
        elif any(path_overlap(p, h) for p in row["paths"] for h in locked):
            reasons[name] = "DISJOINT_LEASE_CONFLICT"
        else:
            selected.append(name)
            spent += float(row["cost_minutes"])
            per_pool[row["pool"]] += 1
            locked.extend(row["paths"])
            reasons[name] = "STAGED_READ_ONLY_NOT_DISPATCHED"
    return {
        "selected": selected,
        "reasons": reasons,
        "estimated_minutes": round(spent, 4),
        "dispatch_performed": False,
    }


def plan(doc):
    tasks, gates, pairs, topo = validate(doc)
    reasons = {}
    ready = []
    for name in topo:
        row = tasks[name]
        if row["state"] != "pending":
            reasons[name] = "NOT_PENDING"
        elif row["kind"] != "read_only":
            reasons[name] = "MUTATION_OR_APPROVAL_HELD"
        elif any(tasks[d]["state"] != "done" for d in row["depends_on"]):
            reasons[name] = "UPSTREAM_UNVERIFIED"
        else:
            ready.append(name)
    scores = {}
    for name in ready:
        row = tasks[name]
        values = pressure(name, tasks, gates)
        if row["cost_minutes"] is None or row["expected_gain"] is None:
            efficiency = None
        else:
            efficiency = row["expected_gain"] / row["cost_minutes"]
        scores[name] = {
            **values,
            "efficiency": efficiency,
            "missing_opportunities": row["missing_opportunities"],
            "risk": row["risk"],
            "evidence_ref": row.get("evidence_ref"),
        }
    ranks = sorted(ready, key=lambda key: reverse_key(key, scores))
    size = sorted(
        ready,
        key=lambda key: (
            (
                -scores[key]["missing_opportunities"]
                if scores[key]["missing_opportunities"] is not None
                else float("inf")
            ),
            key,
        ),
    )
    bt = fit_bt(ready, pairs)
    bt_order = None
    if bt["strengths"] is not None:
        bt_order = sorted(ready, key=lambda key: (-bt["strengths"][key], key))
    return {
        "schema": "codepurple.mip.frontier-result.v3",
        "source_sha": doc["source_sha"],
        "topological_order": topo,
        "ready_frontier": ready,
        "not_ready_reasons": reasons,
        "reverse_pressure_scores": scores,
        "bt": bt,
        "rankings": {
            "reverse_pressure": ranks,
            "size_cap_only": size,
            "bt": bt_order,
        },
        "selected_read_only_proposals": reserve(ranks, tasks, doc["capacity"]),
        "ablation_status": "PENDING_MEASURED_OUTCOMES",
        "advisory_only": True,
        "path_lease_model": "CASEFOLDED_LEXICAL_PLAN_NOT_AUTHENTICATED",
        "dispatch_authorized": False,
        "mutation_authorized": False,
        "merge_admission": "HOLD",
        "authority_transfer": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    source = json.loads(args.input.read_text(encoding="utf-8"))
    report = plan(source)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
