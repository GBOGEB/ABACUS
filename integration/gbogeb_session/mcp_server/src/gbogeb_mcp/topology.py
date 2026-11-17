"""
Knowledge Topology Navigator — Unified graph across GBA + GBC repositories.

Loads knowledge_topology.json from both GBOGEB/ABACUS and GBOGEB/CODEX,
merges nodes and edges into a single queryable graph, and provides:
  • Node lookup by ID, label, category, repo, or tags
  • Full-text search across node metadata
  • Edge traversal (upstream / downstream)
  • Cross-repo dependency analysis
  • Topology statistics and health checks
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ============================================================================
# Data classes
# ============================================================================


@dataclass
class Node:
    """A single node in the knowledge topology."""

    id: str
    repo: str
    label: str
    category: str
    path: str
    description: str = ""
    outputs: list[str] = field(default_factory=list)
    cross_repo_deps: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    domain: str = ""
    node_type: str = ""  # 'type' field from GBC topology
    links_to: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "repo": self.repo,
            "label": self.label,
            "category": self.category,
            "path": self.path,
            "description": self.description,
            "outputs": self.outputs,
            "cross_repo_deps": self.cross_repo_deps,
            "tags": self.tags,
            "domain": self.domain,
            "type": self.node_type,
            "links_to": self.links_to,
        }


@dataclass
class Edge:
    """A directed edge in the knowledge topology."""

    source: str
    target: str
    edge_type: str  # "cross_repo", "internal", or GBC relation types
    label: str = ""
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "from": self.source,
            "to": self.target,
            "type": self.edge_type,
            "label": self.label,
            "description": self.description,
        }


# ============================================================================
# Topology Navigator
# ============================================================================


class TopologyNavigator:
    """
    Unified knowledge-graph navigator merging GBA and GBC topologies.

    Usage:
        nav = TopologyNavigator(gba_root="/path/to/gbogeb_abacus",
                                gbc_root="/path/to/gbogeb_codex")
        nav.load()
        node = nav.get_node("GBA-GOV-001")
        results = nav.search("cryomodule")
    """

    def __init__(self, gba_root: str, gbc_root: str) -> None:
        self.gba_root = Path(gba_root)
        self.gbc_root = Path(gbc_root)
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        self.categories: dict[str, dict[str, str]] = {}
        self.repositories: dict[str, dict[str, str]] = {}
        self._loaded = False

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load and merge topologies from both repositories."""
        self._load_gba_topology()
        self._load_gbc_topology()
        self._loaded = True

    def _load_gba_topology(self) -> None:
        """Load GBOGEB/ABACUS topology (primary, richer schema)."""
        topo_path = self.gba_root / "config" / "knowledge_topology.json"
        if not topo_path.exists():
            raise FileNotFoundError(f"GBA topology not found: {topo_path}")

        data = json.loads(topo_path.read_text(encoding="utf-8"))

        # Repositories metadata
        for key, val in data.get("repositories", {}).items():
            self.repositories[key] = val

        # Categories
        self.categories = data.get("categories", {})

        # Nodes
        for n in data.get("nodes", []):
            node = Node(
                id=n["id"],
                repo=n.get("repo", "GBA"),
                label=n["label"],
                category=n.get("category", ""),
                path=n.get("path", ""),
                description=n.get("description", ""),
                outputs=n.get("outputs", []),
                cross_repo_deps=n.get("cross_repo_deps", []),
            )
            self.nodes[node.id] = node

        # Edges
        for e in data.get("edges", []):
            self.edges.append(
                Edge(
                    source=e["from"],
                    target=e["to"],
                    edge_type=e.get("type", "unknown"),
                    label=e.get("label", ""),
                )
            )

    def _load_gbc_topology(self) -> None:
        """Load GBOGEB/CODEX topology (visual-asset-centric schema)."""
        topo_path = self.gbc_root / "config" / "knowledge_topology.json"
        if not topo_path.exists():
            raise FileNotFoundError(f"GBC topology not found: {topo_path}")

        data = json.loads(topo_path.read_text(encoding="utf-8"))

        # Repository metadata
        for key, val in data.get("repositories", {}).items():
            if key not in self.repositories:
                self.repositories[key] = val

        # GBC nodes
        for n in data.get("nodes", []):
            node_id = n["id"]
            # If already loaded from GBA, merge extra fields
            if node_id in self.nodes:
                existing = self.nodes[node_id]
                existing.tags = n.get("tags", existing.tags)
                existing.domain = n.get("domain", existing.domain)
                existing.node_type = n.get("type", existing.node_type)
                existing.links_to = n.get("links_to", existing.links_to)
            else:
                node = Node(
                    id=node_id,
                    repo=n.get("repository", "GBC"),
                    label=n["label"],
                    category=n.get("type", ""),
                    path=n.get("path", ""),
                    description="",
                    tags=n.get("tags", []),
                    domain=n.get("domain", ""),
                    node_type=n.get("type", ""),
                    links_to=n.get("links_to", []),
                )
                self.nodes[node_id] = node

        # GBA reference nodes (add as stubs if not already present)
        for ref in data.get("gba_references", []):
            ref_id = ref["id"]
            if ref_id not in self.nodes:
                self.nodes[ref_id] = Node(
                    id=ref_id,
                    repo=ref.get("repository", "GBA"),
                    label=ref.get("label", ref_id),
                    category="reference",
                    path=ref.get("path", ""),
                    description=f"GBA reference node: {ref.get('label', '')}",
                )

        # GBC edges
        for e in data.get("edges", []):
            self.edges.append(
                Edge(
                    source=e["from"],
                    target=e["to"],
                    edge_type=e.get("relation", "unknown"),
                    label=e.get("relation", ""),
                    description=e.get("description", ""),
                )
            )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_node(self, node_id: str) -> Node | None:
        """Retrieve a node by its exact ID."""
        self._ensure_loaded()
        return self.nodes.get(node_id)

    def get_nodes_by_repo(self, repo: str) -> list[Node]:
        """Get all nodes belonging to a repository (GBA or GBC)."""
        self._ensure_loaded()
        return [n for n in self.nodes.values() if n.repo == repo]

    def get_nodes_by_category(self, category: str) -> list[Node]:
        """Get all nodes of a given category."""
        self._ensure_loaded()
        return [n for n in self.nodes.values() if n.category == category]

    def search(self, query: str) -> list[Node]:
        """
        Full-text search across node labels, descriptions, tags, and domains.
        Returns nodes ranked by relevance (number of field matches).
        """
        self._ensure_loaded()
        query_lower = query.lower()
        tokens = query_lower.split()
        scored: list[tuple[int, Node]] = []

        for node in self.nodes.values():
            score = 0
            searchable = " ".join(
                [
                    node.label,
                    node.description,
                    node.category,
                    node.domain,
                    node.node_type,
                    " ".join(node.tags),
                    node.id,
                ]
            ).lower()

            for token in tokens:
                if token in searchable:
                    score += 1
                # Bonus for exact ID match
                if token == node.id.lower():
                    score += 5

            if score > 0:
                scored.append((score, node))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [node for _, node in scored]

    def get_edges_from(self, node_id: str) -> list[Edge]:
        """Get all outgoing edges from a node."""
        self._ensure_loaded()
        return [e for e in self.edges if e.source == node_id]

    def get_edges_to(self, node_id: str) -> list[Edge]:
        """Get all incoming edges to a node."""
        self._ensure_loaded()
        return [e for e in self.edges if e.target == node_id]

    def get_cross_repo_edges(self) -> list[Edge]:
        """Get all edges that cross repository boundaries."""
        self._ensure_loaded()
        return [
            e
            for e in self.edges
            if e.edge_type == "cross_repo" or self._is_cross_repo_edge(e)
        ]

    def get_upstream(self, node_id: str) -> list[Node]:
        """Get all nodes that feed into the given node."""
        self._ensure_loaded()
        incoming = self.get_edges_to(node_id)
        return [self.nodes[e.source] for e in incoming if e.source in self.nodes]

    def get_downstream(self, node_id: str) -> list[Node]:
        """Get all nodes that the given node feeds into."""
        self._ensure_loaded()
        outgoing = self.get_edges_from(node_id)
        return [self.nodes[e.target] for e in outgoing if e.target in self.nodes]

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_statistics(self) -> dict[str, Any]:
        """Return topology summary statistics."""
        self._ensure_loaded()
        gba_nodes = [n for n in self.nodes.values() if n.repo == "GBA"]
        gbc_nodes = [n for n in self.nodes.values() if n.repo == "GBC"]
        cross_edges = self.get_cross_repo_edges()

        # Category breakdown
        cat_counts: dict[str, int] = {}
        for node in self.nodes.values():
            cat = node.category or "uncategorized"
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "gba_nodes": len(gba_nodes),
            "gbc_nodes": len(gbc_nodes),
            "cross_repo_edges": len(cross_edges),
            "categories": cat_counts,
            "repositories": list(self.repositories.keys()),
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    def _is_cross_repo_edge(self, edge: Edge) -> bool:
        """Check if an edge crosses repo boundaries based on node repos."""
        src = self.nodes.get(edge.source)
        tgt = self.nodes.get(edge.target)
        if src and tgt:
            return src.repo != tgt.repo
        return False
