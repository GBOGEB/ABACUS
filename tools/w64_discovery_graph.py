#!/usr/bin/env python3
"""Build a conservative W64 discovery graph and missing-ID receipt.

The graph is derived evidence only. It links known SSOT logical IDs, source paths,
linked artifacts and semantic references so unresolved identifiers become visible
without promoting any candidate to authority.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

ID_RE = re.compile(r"^[A-Z][A-Z0-9_-]{1,80}$")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def parse_ssot_items(text: str) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    in_artifacts = False
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if stripped.startswith("- id:"):
            if current:
                items.append(current)
            current = {"id": stripped.split(":", 1)[1].strip(), "linked_artifacts": []}
            in_artifacts = False
        elif current is not None and stripped.startswith("name:"):
            current["name"] = stripped.split(":", 1)[1].strip()
            in_artifacts = False
        elif current is not None and stripped.startswith("source:"):
            current["source"] = stripped.split(":", 1)[1].strip()
            in_artifacts = False
        elif current is not None and stripped.startswith("status:"):
            current["status"] = stripped.split(":", 1)[1].strip()
            in_artifacts = False
        elif current is not None and stripped == "linked_artifacts:":
            in_artifacts = True
        elif current is not None and in_artifacts and stripped.startswith("- "):
            artifacts = current.setdefault("linked_artifacts", [])
            assert isinstance(artifacts, list)
            artifacts.append(stripped[2:].strip())
        elif stripped and not stripped.startswith("#"):
            in_artifacts = False
    if current:
        items.append(current)
    return items


def parse_semantic_traceability(text: str) -> list[tuple[str, str, str]]:
    edges: list[tuple[str, str, str]] = []
    current_q: str | None = None
    for raw in text.splitlines():
        stripped = raw.strip()
        if re.match(r"^Q\d+:$", stripped):
            current_q = stripped[:-1]
        elif current_q and stripped.startswith("ssot:"):
            edges.append((current_q, "resolves_to", stripped.split(":", 1)[1].strip()))
        elif current_q and stripped.startswith("gaps:"):
            body = stripped.split(":", 1)[1].strip().strip("[]")
            for value in [x.strip() for x in body.split(",") if x.strip()]:
                edges.append((current_q, "has_gap", value))
    return edges


def add_node(nodes: dict[str, dict[str, object]], node_id: str, kind: str, **attrs: object) -> None:
    node = nodes.setdefault(node_id, {"id": node_id, "kind": kind})
    for key, value in attrs.items():
        if value not in (None, "", []):
            node[key] = value


def build(root: Path) -> dict[str, object]:
    index = json.loads(read_text(root / "ssot/index.json") or "{}")
    authorities = index.get("authorities", []) if isinstance(index, dict) else []
    if not isinstance(authorities, list):
        authorities = []
    items = parse_ssot_items(read_text(root / "ssot/ssot_items.yaml"))
    semantic = parse_semantic_traceability(read_text(root / "ssot/semantic_traceability.yaml"))

    nodes: dict[str, dict[str, object]] = {}
    edges: list[dict[str, str]] = []
    atoms: list[dict[str, object]] = []

    indexed_ids: set[str] = set()
    declared_ids: set[str] = set()
    referenced_ids: set[str] = set()

    for authority in authorities:
        if not isinstance(authority, dict):
            continue
        logical_id = str(authority.get("logical_id", "")).strip()
        path = str(authority.get("path", "")).strip()
        if not logical_id:
            continue
        indexed_ids.add(logical_id)
        add_node(nodes, logical_id, "logical_id", state=authority.get("state"))
        if path:
            path_id = f"path:{path}"
            add_node(nodes, path_id, "path", path=path)
            edges.append({"from": logical_id, "type": "indexed_at", "to": path_id})

    for item in items:
        logical_id = str(item.get("id", "")).strip()
        if not logical_id:
            continue
        declared_ids.add(logical_id)
        add_node(nodes, logical_id, "logical_id", name=item.get("name"), status=item.get("status"))
        source = str(item.get("source", "")).strip()
        if source:
            source_id = f"path:{source}"
            add_node(nodes, source_id, "path", path=source)
            edges.append({"from": logical_id, "type": "source", "to": source_id})
        artifacts = item.get("linked_artifacts", [])
        if isinstance(artifacts, list):
            for artifact in artifacts:
                artifact_path = str(artifact)
                artifact_id = f"path:{artifact_path}"
                add_node(nodes, artifact_id, "artifact", path=artifact_path)
                edges.append({"from": logical_id, "type": "links_artifact", "to": artifact_id})

    for source, relation, target in semantic:
        referenced_ids.add(target)
        add_node(nodes, source, "question")
        add_node(nodes, target, "logical_or_gap_ref")
        edges.append({"from": source, "type": relation, "to": target})

    known_ids = indexed_ids | declared_ids
    unresolved_refs = sorted(x for x in referenced_ids if x not in known_ids and ID_RE.match(x))
    declared_not_indexed = sorted(declared_ids - indexed_ids)
    indexed_not_declared = sorted(indexed_ids - declared_ids)

    for logical_id in declared_not_indexed:
        atoms.append({
            "atom": "declared_not_indexed",
            "id": logical_id,
            "severity": "action",
            "claim_guard": "Registry mismatch only; no authority promotion implied.",
        })
    for logical_id in unresolved_refs:
        atoms.append({
            "atom": "unresolved_reference",
            "id": logical_id,
            "severity": "discovery",
            "claim_guard": "Reference exists but no matching indexed/declared logical ID was found.",
        })

    return {
        "schema_version": "W64-DISCOVERY-GRAPH-1.0.0",
        "state": "DERIVED_DISCOVERY_ONLY",
        "summary": {
            "indexed_logical_ids": len(indexed_ids),
            "declared_ssot_ids": len(declared_ids),
            "declared_not_indexed": len(declared_not_indexed),
            "indexed_not_declared": len(indexed_not_declared),
            "unresolved_referenced_ids": len(unresolved_refs),
            "nodes": len(nodes),
            "edges": len(edges),
            "atoms": len(atoms),
        },
        "missing_ids": {
            "declared_not_indexed": declared_not_indexed,
            "indexed_not_declared": indexed_not_declared,
            "unresolved_referenced_ids": unresolved_refs,
        },
        "nodes": sorted(nodes.values(), key=lambda x: str(x["id"])),
        "edges": sorted(edges, key=lambda x: (x["from"], x["type"], x["to"])),
        "atoms": atoms,
        "non_claims": [
            "Does not promote any logical ID to authority.",
            "Does not delete aliases or legacy paths.",
            "Does not award release, engineering, compliance or negotiation credit.",
        ],
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    root = Path(args.root).resolve()
    out = Path(args.out)
    if not out.is_absolute():
        out = root / out
    out.parent.mkdir(parents=True, exist_ok=True)
    report = build(root)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
