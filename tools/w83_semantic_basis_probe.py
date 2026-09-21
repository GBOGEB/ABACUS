#!/usr/bin/env python3
"""W83 deterministic semantic-basis diversity probe."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import w72_semantic_census as w72

SCHEMA = "MC2-W83-SEMANTIC-BASIS-PROBE-0.1.0"


def canonical_sha256(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def parse_records(path: Path, key: str, fields: tuple[str, ...]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    pattern = re.compile(rf"^\s*-\s+{re.escape(key)}:\s*(.+?)\s*$")
    field_patterns = {
        field: re.compile(rf"^\s+{re.escape(field)}:\s*(.+?)\s*$")
        for field in fields
    }
    for raw in w72.read_text(path).splitlines():
        match = pattern.match(raw)
        if match:
            if current is not None:
                records.append(current)
            current = {key: match.group(1).strip().strip('"').strip("'")}
            continue
        if current is None:
            continue
        for field, field_pattern in field_patterns.items():
            match = field_pattern.match(raw)
            if match:
                current[field] = match.group(1).strip().strip('"').strip("'")
                break
    if current is not None:
        records.append(current)
    return records


def count_values(rows: list[dict[str, str]], field: str) -> Counter[str]:
    return Counter(row.get(field, "MISSING") for row in rows)


def workflow_features(root: Path) -> dict[str, int]:
    path = root / "ci/governance/workflow_policy.json"
    if not path.exists():
        return {
            "policy_present": 0,
            "rule_count": 0,
            "cluster_count": 0,
            "keep_rules": 0,
            "canonical_rules": 0,
            "retire_rules": 0,
            "pr_fast_rules": 0,
            "pr_domain_rules": 0,
            "post_merge_rules": 0,
            "scheduled_rules": 0,
        }
    try:
        data = json.loads(w72.read_text(path) or "{}")
    except json.JSONDecodeError:
        data = {}
    rules = [row for row in data.get("rules", []) if isinstance(row, dict)]
    return {
        "policy_present": 1,
        "rule_count": len(rules),
        "cluster_count": len({str(row.get("cluster", "")) for row in rules}),
        "keep_rules": sum(row.get("disposition") == "keep" for row in rules),
        "canonical_rules": sum(row.get("disposition") == "canonical" for row in rules),
        "retire_rules": sum(row.get("disposition") == "retire" for row in rules),
        "pr_fast_rules": sum(row.get("lifecycle") == "pr_fast" for row in rules),
        "pr_domain_rules": sum(row.get("lifecycle") == "pr_domain" for row in rules),
        "post_merge_rules": sum(row.get("lifecycle") == "post_merge" for row in rules),
        "scheduled_rules": sum(row.get("lifecycle") == "scheduled" for row in rules),
    }


def semantic_fanout(root: Path) -> tuple[int, int, int]:
    text = w72.read_text(root / "ssot/semantic_traceability.yaml")
    question_count = 0
    gap_links = 0
    max_gap_fanout = 0
    for raw in text.splitlines():
        if re.match(r"^\s{2}[^\s#][^:]*:\s*$", raw):
            question_count += 1
        match = re.match(r"^\s+gaps:\s*\[([^\]]*)\]", raw)
        if match:
            count = len([x for x in match.group(1).split(",") if x.strip()])
            gap_links += count
            max_gap_fanout = max(max_gap_fanout, count)
    return question_count, gap_links, max_gap_fanout


def probe(root: Path, source_sha: str, label: str) -> dict:
    manifest = w72.manifest_bindings(root)
    indexed = w72.indexed_bindings(root)
    domain_rows = parse_records(
        root / "ssot/ssot_items.yaml", "id", ("owner", "status", "source")
    )
    gap_rows = parse_records(
        root / "ssot/contractual_gap_register.yaml",
        "id",
        ("severity", "status", "owner", "review_gate", "ssot_id"),
    )
    manifest_rows = parse_records(
        root / "ssot/manifest.yaml",
        "logical_id",
        ("path", "state", "migration"),
    )
    refs = w72.semantic_refs(root)
    domain = {
        row["id"]: row.get("source")
        for row in domain_rows
        if row.get("id")
    }
    gaps = {
        row["id"]: "ssot/contractual_gap_register.yaml"
        for row in gap_rows
        if row.get("id")
    }

    authority_ids = set(manifest) | set(indexed)
    domain_ids = set(domain) | set(gaps)
    known = authority_ids | domain_ids

    lineage_paths: dict[str, str] = {}
    lineage_paths.update(indexed)
    for logical_id, path in domain.items():
        if path:
            lineage_paths[logical_id] = w72.strip_anchor(path)
    lineage_paths.update(gaps)

    consumer_bindings = {key: lineage_paths.get(key, "") for key in known}
    hits = w72.consumer_hits(root, consumer_bindings)
    hit_counts = [len(values) for values in hits.values()]

    edges: list[tuple[str, str]] = []
    for logical_id, path in lineage_paths.items():
        edges.append((logical_id, f"path:{path}"))
    for ref in refs:
        if ref in known:
            edges.append(("semantic", ref))
    nodes = set(known) | set(refs) | {node for edge in edges for node in edge}
    degrees = {node: 0 for node in nodes}
    for left, right in edges:
        degrees[left] = degrees.get(left, 0) + 1
        degrees[right] = degrees.get(right, 0) + 1

    gap_severity = count_values(gap_rows, "severity")
    gap_status = count_values(gap_rows, "status")
    gap_gate = count_values(gap_rows, "review_gate")
    domain_status = count_values(domain_rows, "status")
    manifest_state = count_values(manifest_rows, "state")
    question_count, gap_links, max_gap_fanout = semantic_fanout(root)

    semantic_composition = {
        "authority_ids": len(authority_ids),
        "domain_item_ids": len(domain_rows),
        "gap_ids": len(gap_rows),
        "known_ids": len(known),
        "semantic_ref_ids": len(refs),
        "lineage_bound_ids": len(lineage_paths),
        "manifest_bindings": len(manifest),
        "indexed_bindings": len(indexed),
        "manifest_index_symmetric_diff": len(set(manifest) ^ set(indexed)),
        "domain_draft_review": domain_status["draft-review"],
        "gap_open": gap_status["open"],
        "gap_high": gap_severity["high"],
        "gap_critical": gap_severity["critical"],
        "gap_contract_review": gap_gate["Contract Review"],
        "gap_technical_review": gap_gate["Technical Review"],
        "gap_procurement_review": gap_gate["Procurement Review"],
        "manifest_authoritative_candidate": manifest_state["AUTHORITATIVE_CANDIDATE"],
        "manifest_registry_candidate": manifest_state["REGISTRY_CANDIDATE"],
        "manifest_style_candidate": manifest_state["AUTHORITATIVE_STYLE_CANDIDATE"],
        "traceability_question_count": question_count,
        "traceability_gap_links": gap_links,
        "traceability_max_gap_fanout": max_gap_fanout,
    }

    consumer_graph_distribution = {
        "consumer_entities": len(hit_counts),
        "consumer_entities_with_hits": sum(count > 0 for count in hit_counts),
        "consumer_entities_exactly_one_file": sum(count == 1 for count in hit_counts),
        "consumer_entities_multi_file": sum(count >= 2 for count in hit_counts),
        "consumer_entities_five_plus_files": sum(count >= 5 for count in hit_counts),
        "consumer_file_relations": sum(hit_counts),
        "consumer_file_relations_sq_sum": sum(count * count for count in hit_counts),
        "max_consumer_files_per_entity": max(hit_counts, default=0),
        "graph_nodes": len(nodes),
        "graph_edges": len(edges),
        "graph_isolated_nodes": sum(degree == 0 for degree in degrees.values()),
        "graph_nonisolated_nodes": sum(degree > 0 for degree in degrees.values()),
        "graph_max_degree": max(degrees.values(), default=0),
        "graph_degree_sum": sum(degrees.values()),
        "graph_degree_sq_sum": sum(value * value for value in degrees.values()),
    }

    blocks = {
        "semantic_composition": semantic_composition,
        "consumer_graph_distribution": consumer_graph_distribution,
        "workflow_governance_composition": workflow_features(root),
    }
    flattened = {
        f"{block}.{name}": int(value)
        for block, values in blocks.items()
        for name, value in values.items()
    }
    return {
        "schema_version": SCHEMA,
        "repository": "GBOGEB/ABACUS",
        "source_sha": source_sha,
        "matrix_label": label,
        "measurement_basis": "typed_semantic_composition_and_distribution",
        "blocks": blocks,
        "block_sha256": {
            name: canonical_sha256(values) for name, values in blocks.items()
        },
        "feature_vector": flattened,
        "feature_vector_sha256": canonical_sha256(flattened),
        "pca_fit_performed": False,
        "pairwise_outcome_accumulation_permitted": False,
        "bt_status": "WITHHELD",
        "authority_transfer": False,
        "global_allocation_authority": False,
        "engineering_compliance_release_authority": False,
        "formal_credit_delta": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--matrix-label", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = probe(Path(args.root).resolve(), args.source_sha, args.matrix_label)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
