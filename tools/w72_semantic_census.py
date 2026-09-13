#!/usr/bin/env python3
"""W72 versioned semantic census.

Separates authority-object IDs from domain/gap IDs, binds each ID to a real
source path, excludes generated measurement evidence from consumer counts, and
emits the same MC-2 semantic feature keys under a new measurement schema.

Consumer evidence is path-aware: a downstream file may consume a logical
entity by its logical ID or by its canonical bound path. The entity's own
source file is never counted as its downstream consumer.

This tool is intentionally stdlib-only so it can be copied into an exact-SHA
checkout and used to remeasure historical repository states without changing
those historical trees.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
from pathlib import Path

SCHEMA_VERSION = "W72-SEMANTIC-CENSUS-2.0.0"
TEXT_SUFFIXES = {
    ".py", ".yml", ".yaml", ".json", ".md", ".toml", ".txt", ".ini",
    ".cfg", ".html", ".js", ".ts", ".tsx", ".jsx", ".ps1", ".sh",
}
ID_RE = re.compile(r"\b[A-Z][A-Z0-9_-]{1,80}\b")
SKIP_PARTS = {
    ".git", ".venv", "venv", "node_modules", "dist", "build",
    ".pytest_cache", "__pycache__",
}
SKIP_PREFIXES = (
    "architecture/w66/receipts/",
    "architecture/w70/receipts/",
    "architecture/mc2/",
    "fixtures/",
    "tests/",
)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def strip_anchor(value: str) -> str:
    return value.split("#", 1)[0].strip()


def parse_id_records(path: Path, path_key: str | None = None) -> dict[str, str | None]:
    """Parse YAML list records with ``- id:`` and an optional path/source key."""
    records: dict[str, str | None] = {}
    current: str | None = None
    for line in read_text(path).splitlines():
        match = re.match(r"^\s*-\s+id:\s*([^\s#]+)", line)
        if match:
            current = match.group(1).strip()
            records[current] = None
            continue
        if current and path_key:
            match = re.match(
                rf"^\s+{re.escape(path_key)}:\s*([^\s#]+(?:#[^\s#]+)?)", line
            )
            if match:
                records[current] = strip_anchor(match.group(1))
    return records


def manifest_bindings(root: Path) -> dict[str, str]:
    bindings: dict[str, str] = {}
    current: str | None = None
    for line in read_text(root / "ssot/manifest.yaml").splitlines():
        match = re.match(r"^\s*-\s+logical_id:\s*([^\s#]+)", line)
        if match:
            current = match.group(1).strip()
            continue
        if current:
            match = re.match(r"^\s+path:\s*([^\s#]+)", line)
            if match:
                bindings[current] = strip_anchor(match.group(1))
                current = None
    return bindings


def indexed_bindings(root: Path) -> dict[str, str]:
    try:
        data = json.loads(read_text(root / "ssot/index.json") or "{}")
    except Exception:
        data = {}
    bindings: dict[str, str] = {}
    rows = data.get("authorities", []) if isinstance(data, dict) else []
    for row in rows:
        if not isinstance(row, dict) or not row.get("logical_id"):
            continue
        logical_id = str(row["logical_id"])
        path = row.get("path")
        if path:
            bindings[logical_id] = strip_anchor(str(path))
    return bindings


def gap_bindings(root: Path) -> dict[str, str]:
    gaps = parse_id_records(root / "ssot/contractual_gap_register.yaml")
    return {gap_id: "ssot/contractual_gap_register.yaml" for gap_id in gaps}


def semantic_refs(root: Path) -> set[str]:
    text = read_text(root / "ssot/semantic_traceability.yaml")
    out: set[str] = set()
    for match in re.finditer(
        r"\b(?:ssot|gaps):\s*(?:\[([^\]]*)\]|([^\s#]+))", text
    ):
        raw = match.group(1) or match.group(2) or ""
        out.update(value.strip() for value in raw.split(",") if value.strip())
    return out


def consumer_hits(root: Path, bindings: dict[str, str]) -> dict[str, set[str]]:
    """Find downstream consumers by logical ID or canonical bound path."""
    hits = {key: set() for key in bindings}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith("ssot/") or any(rel.startswith(prefix) for prefix in SKIP_PREFIXES):
            continue
        text = read_text(path)
        for key, bound_path in bindings.items():
            # The authority/domain source itself is lineage, not a downstream consumer.
            if bound_path and rel == bound_path:
                continue
            if key in text or (bound_path and bound_path in text):
                hits[key].add(rel)
    return hits


def pct(done: int, total: int) -> float:
    return round(100.0 * done / total, 2) if total else 100.0


def finite_rate(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("non-finite semantic rate")
    return round(value, 6)


def measure(root: Path, source_sha: str) -> tuple[dict[str, dict], dict]:
    manifest = manifest_bindings(root)
    indexed = indexed_bindings(root)
    domain = {
        key: value
        for key, value in parse_id_records(root / "ssot/ssot_items.yaml", "source").items()
    }
    gaps = gap_bindings(root)

    authority_ids = set(manifest) | set(indexed)
    domain_ids = set(domain) | set(gaps)
    known = authority_ids | domain_ids
    refs = semantic_refs(root)

    registry_findings = sorted(set(manifest) ^ set(indexed))
    registry_total = len(authority_ids)
    registry_open = len(registry_findings)

    unresolved = sorted(ref for ref in refs if ref not in known and ID_RE.fullmatch(ref))
    reference_total = len(refs)
    reference_open = len(unresolved)

    lineage_paths: dict[str, str] = {}
    lineage_paths.update(indexed)
    for logical_id, path in domain.items():
        if path:
            lineage_paths[logical_id] = strip_anchor(path)
    lineage_paths.update(gaps)

    # Every known entity is represented even if it has no current path binding.
    consumer_bindings = {key: lineage_paths.get(key, "") for key in known}
    hits = consumer_hits(root, consumer_bindings)
    unbound = sorted(key for key, values in hits.items() if not values)
    consumer_total = len(known)
    consumer_open = len(unbound)
    consumer_evidence = {
        key: sorted(values) for key, values in sorted(hits.items()) if values
    }

    edges: list[tuple[str, str]] = []
    for logical_id, path in lineage_paths.items():
        edges.append((logical_id, f"path:{path}"))
    for ref in refs:
        if ref in known:
            edges.append(("semantic", ref))

    nodes = set(known) | set(refs) | {node for edge in edges for node in edge}
    degree = {node: 0 for node in nodes}
    for left, right in edges:
        degree[left] = degree.get(left, 0) + 1
        degree[right] = degree.get(right, 0) + 1
    isolated = sorted(node for node, degree_value in degree.items() if degree_value == 0)
    graph_total = len(nodes)
    graph_open = len(isolated)

    unlineaged = sorted(
        logical_id
        for logical_id in known
        if not lineage_paths.get(logical_id)
        or not (root / lineage_paths[logical_id]).exists()
    )
    lineage_total = len(known)
    lineage_open = len(unlineaged)

    lane_defs = {
        "A_registry_gap": (
            registry_total,
            registry_open,
            {
                "authority_registry_mismatches": registry_findings,
                "manifest_authority_ids": sorted(manifest),
                "index_authority_ids": sorted(indexed),
            },
        ),
        "B_reference_gap": (
            reference_total,
            reference_open,
            {"unresolved_references": unresolved},
        ),
        "C_consumer_penetration": (
            consumer_total,
            consumer_open,
            {
                "unbound_consumers": unbound,
                "consumer_evidence": consumer_evidence,
            },
        ),
        "D_graph_orphan_drop": (
            graph_total,
            graph_open,
            {"isolated_nodes": isolated},
        ),
        "E_lineage_evidence": (
            lineage_total,
            lineage_open,
            {"unlineaged_ids": unlineaged},
        ),
    }

    receipts: dict[str, dict] = {}
    for lane, (total, open_count, findings) in lane_defs.items():
        closed = max(0, total - open_count)
        receipts[lane] = {
            "schema_version": SCHEMA_VERSION,
            "repository": "GBOGEB/ABACUS",
            "source_sha": source_sha,
            "lane": lane,
            "state": "MEASURED",
            "totals": {
                "total_population": total,
                "backlog_open": open_count,
                "backlog_closed": closed,
                "completion_pct": pct(closed, total),
            },
            "findings": findings,
        }

    feature_row = {
        "measurement_schema": SCHEMA_VERSION,
        "source_sha": source_sha,
        "registry_gap_rate": finite_rate(registry_open / max(registry_total, 1)),
        "unresolved_reference_rate": finite_rate(reference_open / max(reference_total, 1)),
        "consumer_penetration_rate": finite_rate(
            (consumer_total - consumer_open) / max(consumer_total, 1)
        ),
        "graph_drop_rate": finite_rate(graph_open / max(graph_total, 1)),
        "lineage_gap_rate": finite_rate(lineage_open / max(lineage_total, 1)),
        "total_population": sum(values[0] for values in lane_defs.values()),
        "total_open_backlog": sum(values[1] for values in lane_defs.values()),
    }
    return receipts, feature_row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", required=True)
    parser.add_argument("--source-sha")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out = Path(args.out)
    if not out.is_absolute():
        out = Path.cwd() / out
    out.mkdir(parents=True, exist_ok=True)
    source_sha = args.source_sha or os.getenv("SOURCE_SHA") or os.getenv(
        "GITHUB_SHA", "LOCAL"
    )

    receipts, row = measure(root, source_sha)
    for lane, receipt in receipts.items():
        (out / f"{lane}.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    (out / "FEATURE_ROW.json").write_text(
        json.dumps(row, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(row, sort_keys=True))


if __name__ == "__main__":
    main()
