#!/usr/bin/env python3
"""Cross-Link Registry Validator

Validates all artifact paths and dependency links in cross_link_registry.json.
Detects broken references, orphaned artifacts, and circular dependencies.

Usage:
    python validate_cross_links.py           # Full validation
    python validate_cross_links.py --fix     # Fix broken paths (if possible)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

REGISTRY_PATH = Path("/home/ubuntu/cross_link_registry.json")
PROJECT_ROOT = Path("/home/ubuntu")


def load_registry() -> Dict[str, Any]:
    """Load the cross-link registry."""
    return json.loads(REGISTRY_PATH.read_text())


def validate_paths(registry: Dict) -> Tuple[List[str], List[str]]:
    """Validate all artifact paths exist on disk."""
    found = []
    missing = []

    for artifact_id, artifact in registry["artifact_index"].items():
        path = PROJECT_ROOT / artifact["path"]
        if path.exists():
            found.append(artifact_id)
        else:
            missing.append(f"{artifact_id}: {artifact['path']}")

    return found, missing


def validate_edges(registry: Dict) -> Tuple[List[str], List[str]]:
    """Validate all dependency edges reference existing artifacts."""
    valid_ids = set(registry["artifact_index"].keys())
    valid_edges = []
    broken_edges = []

    for source, target in registry["dependency_graph"]["edges"]:
        if source in valid_ids and target in valid_ids:
            valid_edges.append(f"{source} → {target}")
        else:
            missing = []
            if source not in valid_ids:
                missing.append(f"source '{source}'")
            if target not in valid_ids:
                missing.append(f"target '{target}'")
            broken_edges.append(f"{source} → {target} (missing: {', '.join(missing)})")

    return valid_edges, broken_edges


def find_orphans(registry: Dict) -> List[str]:
    """Find artifacts that are not referenced by any edge."""
    all_ids = set(registry["artifact_index"].keys())
    referenced = set()

    for source, target in registry["dependency_graph"]["edges"]:
        referenced.add(source)
        referenced.add(target)

    return sorted(all_ids - referenced)


def detect_cycles(registry: Dict) -> List[List[str]]:
    """Detect circular dependencies using DFS."""
    graph: Dict[str, Set[str]] = {}
    for source, target in registry["dependency_graph"]["edges"]:
        graph.setdefault(source, set()).add(target)

    visited: Set[str] = set()
    path: List[str] = []
    path_set: Set[str] = set()
    cycles: List[List[str]] = []

    def dfs(node: str):
        if node in path_set:
            cycle_start = path.index(node)
            cycles.append(path[cycle_start:] + [node])
            return
        if node in visited:
            return
        visited.add(node)
        path.append(node)
        path_set.add(node)
        for neighbor in graph.get(node, set()):
            dfs(neighbor)
        path.pop()
        path_set.discard(node)

    for node in graph:
        if node not in visited:
            dfs(node)

    return cycles


def main():
    """Run full validation."""
    print("🔗 Cross-Link Registry Validation")
    print("=" * 50)

    registry = load_registry()
    total_artifacts = len(registry["artifact_index"])
    total_edges = len(registry["dependency_graph"]["edges"])

    print(f"   Artifacts: {total_artifacts}")
    print(f"   Edges: {total_edges}")
    print()

    # Path validation
    found, missing = validate_paths(registry)
    print(f"📁 Path Validation: {len(found)}/{total_artifacts} found")
    if missing:
        for m in missing:
            print(f"   ❌ Missing: {m}")
    else:
        print("   ✅ All artifact paths valid")
    print()

    # Edge validation
    valid_edges, broken_edges = validate_edges(registry)
    print(f"🔗 Edge Validation: {len(valid_edges)}/{total_edges} valid")
    if broken_edges:
        for b in broken_edges:
            print(f"   ❌ Broken: {b}")
    else:
        print("   ✅ All edges reference valid artifacts")
    print()

    # Orphan detection
    orphans = find_orphans(registry)
    print(f"🏝️  Orphan Detection: {len(orphans)} orphaned artifacts")
    if orphans:
        for o in orphans:
            print(f"   ⚠️  {o}")
    else:
        print("   ✅ No orphans found")
    print()

    # Cycle detection
    cycles = detect_cycles(registry)
    print(f"🔄 Cycle Detection: {len(cycles)} cycles found")
    if cycles:
        for c in cycles:
            print(f"   ⚠️  {' → '.join(c)}")
    else:
        print("   ✅ No circular dependencies")
    print()

    # Update validation results in registry
    registry["link_validation"] = {
        "total_artifacts": total_artifacts,
        "total_edges": total_edges,
        "paths_found": len(found),
        "paths_missing": len(missing),
        "edges_valid": len(valid_edges),
        "edges_broken": len(broken_edges),
        "orphans": orphans,
        "cycles": len(cycles),
        "broken_links": missing + broken_edges,
        "last_validated": datetime.now(timezone.utc).isoformat(),
    }
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2))

    # Summary
    issues = len(missing) + len(broken_edges) + len(cycles)
    status = "✅ VALID" if issues == 0 else f"⚠️ {issues} ISSUE(S)"
    print(f"{'=' * 50}")
    print(f"Result: {status}")

    return 0 if issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
