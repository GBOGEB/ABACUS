#!/usr/bin/env python3
"""Build exact-SHA W73 semantic-topology rows from W72 C-lane receipts.

The W72 census establishes which semantic entities have real downstream
consumers. W73 derives bounded topology measures from that evidence without
changing W72 engineering/semantic truth:
- consumer_penetration_rate: entities with >=1 downstream consumer / entities
- consumer_edge_density: observed entity->consumer-file edges / possible edges
- consumer_degree_concentration: normalized HHI of downstream edge degree

All three features are in [0,1]. No missing values are zero-imputed.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

SHA40 = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_SCHEMA = "W72-SEMANTIC-CENSUS-2.0.0"


def fail(message: str) -> None:
    raise ValueError(message)


def bounded(value: float) -> float:
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        fail(f"feature outside [0,1]: {value}")
    return round(value, 6)


def topology_row(path: Path) -> dict:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("schema_version") != EXPECTED_SCHEMA:
        fail(f"{path}: incompatible schema")
    if receipt.get("lane") != "C_consumer_penetration":
        fail(f"{path}: not a C_consumer_penetration receipt")
    sha = str(receipt.get("source_sha", ""))
    if not SHA40.fullmatch(sha):
        fail(f"{path}: invalid source_sha")

    totals = receipt.get("totals") or {}
    entity_count = int(totals.get("total_population", 0))
    backlog_open = int(totals.get("backlog_open", 0))
    if entity_count <= 0 or not 0 <= backlog_open <= entity_count:
        fail(f"{path}: invalid population/backlog")

    evidence = (receipt.get("findings") or {}).get("consumer_evidence")
    if not isinstance(evidence, dict):
        fail(f"{path}: missing consumer_evidence")

    normalized: dict[str, set[str]] = {}
    for entity, consumers in evidence.items():
        if not isinstance(consumers, list):
            fail(f"{path}: consumer evidence must be lists")
        normalized[str(entity)] = {str(item) for item in consumers if str(item)}

    bound_entities = sum(1 for consumers in normalized.values() if consumers)
    expected_bound = entity_count - backlog_open
    if bound_entities != expected_bound:
        fail(
            f"{path}: consumer evidence coverage {bound_entities} != totals {expected_bound}"
        )

    degrees = [len(consumers) for consumers in normalized.values() if consumers]
    edge_count = sum(degrees)
    consumer_files = {item for consumers in normalized.values() for item in consumers}
    file_count = len(consumer_files)
    if edge_count <= 0 or file_count <= 0:
        fail(f"{path}: topology has no downstream evidence")

    penetration = bound_entities / entity_count
    density = edge_count / (entity_count * file_count)
    hhi = sum((degree / edge_count) ** 2 for degree in degrees)
    minimum_hhi = 1.0 / entity_count
    concentration = (hhi - minimum_hhi) / (1.0 - minimum_hhi)

    return {
        "row_id": f"SEM-W73-{sha[:12]}",
        "observation_class": "semantic_topology",
        "source_repo": "GBOGEB/ABACUS",
        "source_sha": sha,
        "evidence_reference": path.as_posix(),
        "authority_class": "derived_operational_analysis",
        "consumer_penetration_rate": bounded(penetration),
        "consumer_edge_density": bounded(density),
        "consumer_degree_concentration": bounded(concentration),
        "topology_counts": {
            "semantic_entities": entity_count,
            "bound_entities": bound_entities,
            "consumer_edges": edge_count,
            "consumer_files": file_count,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipts", nargs="+")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    rows = [topology_row(Path(path)) for path in args.receipts]
    shas = [row["source_sha"] for row in rows]
    if len(set(shas)) != len(shas):
        fail("duplicate source_sha")
    rows.sort(key=lambda row: row["source_sha"])
    Path(args.out).write_text(
        json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"rows": len(rows), "distinct_source_shas": len(set(shas))}))


if __name__ == "__main__":
    main()
