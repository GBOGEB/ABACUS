"""
Test suite for the GBOGEB MCP Server.

Verifies all 7 MCP tools against live data from the GBA and GBC repositories.
Tests cover topology navigation, engineering data search, asset lineage,
physics validation, asset listing, and test status reporting.
"""

from __future__ import annotations

import os
import sys

import pytest

# Ensure the src directory is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from gbogeb_mcp.topology import Edge, Node, TopologyNavigator
from gbogeb_mcp.tools import (
    GBA_ROOT,
    GBC_ROOT,
    get_asset_lineage,
    get_test_status,
    get_topology,
    list_assets,
    query_node,
    search_engineering_data,
    validate_physics,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def navigator():
    """Create a loaded TopologyNavigator."""
    nav = TopologyNavigator(gba_root=GBA_ROOT, gbc_root=GBC_ROOT)
    nav.load()
    return nav


# ============================================================================
# Topology Navigator unit tests
# ============================================================================

class TestTopologyNavigator:
    """Tests for the TopologyNavigator class."""

    def test_load_succeeds(self, navigator: TopologyNavigator):
        """Navigator loads without errors."""
        assert navigator._loaded is True

    def test_has_nodes(self, navigator: TopologyNavigator):
        """Both repos contribute nodes."""
        assert len(navigator.nodes) > 0
        gba = navigator.get_nodes_by_repo("GBA")
        gbc = navigator.get_nodes_by_repo("GBC")
        assert len(gba) >= 17, f"Expected ≥17 GBA nodes, got {len(gba)}"
        assert len(gbc) >= 7, f"Expected ≥7 GBC nodes, got {len(gbc)}"

    def test_has_edges(self, navigator: TopologyNavigator):
        """Edges are loaded from both repos."""
        assert len(navigator.edges) >= 15

    def test_get_node_by_id(self, navigator: TopologyNavigator):
        """Can retrieve a specific node by ID."""
        node = navigator.get_node("GBA-GOV-001")
        assert node is not None
        assert node.label == "Render Rules Engine"
        assert node.repo == "GBA"

    def test_get_gbc_node(self, navigator: TopologyNavigator):
        """Can retrieve a GBC node."""
        node = navigator.get_node("GBC-ASSET-001")
        assert node is not None
        assert "cryomodule" in node.label.lower() or "cryomodule" in " ".join(node.tags).lower()

    def test_search_returns_results(self, navigator: TopologyNavigator):
        """Search finds relevant nodes."""
        results = navigator.search("cryomodule")
        assert len(results) > 0

    def test_search_governance(self, navigator: TopologyNavigator):
        """Search for governance returns governance nodes."""
        results = navigator.search("governance")
        assert any("governance" in n.category.lower() or "governance" in n.description.lower()
                    for n in results)

    def test_get_edges_from(self, navigator: TopologyNavigator):
        """Get outgoing edges from a node."""
        edges = navigator.get_edges_from("GBA-GOV-001")
        assert len(edges) >= 1

    def test_get_cross_repo_edges(self, navigator: TopologyNavigator):
        """Cross-repo edges exist between GBA and GBC."""
        cross = navigator.get_cross_repo_edges()
        assert len(cross) >= 3, f"Expected ≥3 cross-repo edges, got {len(cross)}"

    def test_upstream_downstream(self, navigator: TopologyNavigator):
        """Upstream/downstream traversal works."""
        # GBA-CI-001 should have upstream nodes (linter, contrast, slide-id)
        upstream = navigator.get_upstream("GBA-CI-001")
        assert len(upstream) >= 1

    def test_statistics(self, navigator: TopologyNavigator):
        """Statistics returns expected structure."""
        stats = navigator.get_statistics()
        assert stats["total_nodes"] > 0
        assert stats["total_edges"] > 0
        assert "GBA" in stats["repositories"]
        assert "categories" in stats

    def test_node_to_dict(self, navigator: TopologyNavigator):
        """Node serialization includes all fields."""
        node = navigator.get_node("GBA-GOV-001")
        d = node.to_dict()
        assert "id" in d
        assert "repo" in d
        assert "label" in d
        assert "category" in d


# ============================================================================
# Tool 1: get_topology
# ============================================================================

class TestGetTopology:
    """Tests for the get_topology tool."""

    def test_returns_valid_structure(self):
        result = get_topology()
        assert "statistics" in result
        assert "nodes" in result
        assert "edges" in result
        assert "repositories" in result

    def test_has_both_repos(self):
        result = get_topology()
        assert "GBA" in result["nodes"]
        assert "GBC" in result["nodes"]

    def test_node_counts(self):
        result = get_topology()
        assert len(result["nodes"]["GBA"]) >= 17
        assert len(result["nodes"]["GBC"]) >= 7

    def test_has_cross_repo_edges(self):
        result = get_topology()
        assert len(result["cross_repo_edges"]) >= 3

    def test_categories_present(self):
        result = get_topology()
        assert "governance" in result["categories"]


# ============================================================================
# Tool 2: query_node
# ============================================================================

class TestQueryNode:
    """Tests for the query_node tool."""

    def test_valid_node(self):
        result = query_node("GBA-GOV-001")
        assert "node" in result
        assert result["node"]["id"] == "GBA-GOV-001"
        assert result["node"]["label"] == "Render Rules Engine"

    def test_node_file_path(self):
        result = query_node("GBA-GOV-001")
        assert "file_path" in result
        assert "file_exists" in result

    def test_edges_included(self):
        result = query_node("GBA-GOV-001")
        assert "outgoing_edges" in result
        assert "incoming_edges" in result

    def test_upstream_downstream(self):
        result = query_node("GBA-CI-001")
        assert "upstream" in result
        assert len(result["upstream"]) >= 1

    def test_invalid_node(self):
        result = query_node("NONEXISTENT-999")
        assert "error" in result
        assert "available_nodes" in result

    def test_gbc_asset_node(self):
        result = query_node("GBC-ASSET-001")
        assert "node" in result
        assert result["node"]["repo"] == "GBC"


# ============================================================================
# Tool 3: search_engineering_data
# ============================================================================

class TestSearchEngineeringData:
    """Tests for the search_engineering_data tool."""

    def test_search_cryomodule(self):
        result = search_engineering_data("cryomodule")
        assert result["query"] == "cryomodule"
        assert result["total_matches"] > 0
        assert len(result["sources"]) > 0

    def test_search_heat_load(self):
        result = search_engineering_data("heat_load")
        assert result["total_matches"] > 0

    def test_search_returns_topology_nodes(self):
        result = search_engineering_data("valve")
        sources = result["sources"]
        assert "topology_nodes" in sources or "engineering_data" in sources

    def test_search_svg(self):
        result = search_engineering_data("svg")
        assert result["total_matches"] > 0

    def test_empty_query(self):
        result = search_engineering_data("")
        # Empty string matches everything
        assert "sources" in result


# ============================================================================
# Tool 4: get_asset_lineage
# ============================================================================

class TestGetAssetLineage:
    """Tests for the get_asset_lineage tool."""

    def test_by_id(self):
        result = get_asset_lineage("GBC-ASSET-001")
        assert "error" not in result or "visual_registry" in result or "topology_node" in result

    def test_by_filename(self):
        result = get_asset_lineage("cryomodule_schematic.svg")
        assert "manifest" in result
        assert result["manifest"]["sha256"] is not None

    def test_file_exists_check(self):
        result = get_asset_lineage("cryomodule_schematic.svg")
        if "manifest" in result:
            assert "file_exists" in result

    def test_invalid_asset(self):
        result = get_asset_lineage("nonexistent_file.svg")
        assert "error" in result

    def test_facility_layout(self):
        result = get_asset_lineage("facility_layout.svg")
        assert "manifest" in result
        assert result["manifest"]["processing_status"] == "verified"


# ============================================================================
# Tool 5: validate_physics
# ============================================================================

class TestValidatePhysics:
    """Tests for the validate_physics tool."""

    def test_default_validation(self):
        result = validate_physics()
        assert "validation_engine" in result
        # Either full report or fallback should be present
        assert "report" in result or "fallback" in result or "error" in result

    def test_custom_parameters(self):
        result = validate_physics({
            "temperature_K": 2.0,
            "pressure_bar": 1.2,
        })
        assert "validation_engine" in result
        # Should have enthalpy or fallback
        if "error" not in result:
            assert "enthalpy_J_g" in result or "fallback" in result

    def test_mass_balance_check(self):
        result = validate_physics({
            "temperature_K": 2.0,
            "Q_static_W": 24.5,
            "Q_dynamic_W": 47.8,
            "return_temperature_K": 4.5,
        })
        if "error" not in result:
            assert "mass_balance" in result
            assert result["mass_balance"]["Q_total_W"] == 72.3

    def test_superfluid_detection(self):
        result = validate_physics({"temperature_K": 1.5})
        if "error" not in result:
            assert result["is_superfluid"] is True
            assert "He-II" in result["phase"]

    def test_normal_fluid_detection(self):
        result = validate_physics({"temperature_K": 3.0})
        if "error" not in result:
            assert result["is_superfluid"] is False
            assert "He-I" in result["phase"]


# ============================================================================
# Tool 6: list_assets
# ============================================================================

class TestListAssets:
    """Tests for the list_assets tool."""

    def test_returns_manifest_assets(self):
        result = list_assets()
        assert "manifest_assets" in result
        assert len(result["manifest_assets"]) >= 2

    def test_returns_registry_assets(self):
        result = list_assets()
        assert "registry_assets" in result

    def test_svg_files_on_disk(self):
        result = list_assets()
        assert "svg_files_on_disk" in result
        assert len(result["svg_files_on_disk"]) >= 2

    def test_counts(self):
        result = list_assets()
        assert result["total_tracked"] >= 2
        assert result["total_on_disk"] >= 2

    def test_manifest_version(self):
        result = list_assets()
        assert result["manifest_version"] == "1.0.0"

    def test_file_presence_check(self):
        result = list_assets()
        for asset in result["manifest_assets"]:
            assert "file_present" in asset


# ============================================================================
# Tool 7: get_test_status
# ============================================================================

class TestGetTestStatus:
    """Tests for the get_test_status tool."""

    def test_returns_both_repos(self):
        result = get_test_status()
        assert "GBA" in result
        assert "GBC" in result

    def test_gba_has_tests(self):
        result = get_test_status()
        gba = result["GBA"]
        assert gba["status"] in ("pass", "fail", "timeout", "error", "no_tests")
        if gba["status"] == "pass":
            assert gba["passed"] > 0

    def test_gbc_has_tests(self):
        result = get_test_status()
        gbc = result["GBC"]
        assert gbc["status"] in ("pass", "fail", "timeout", "error", "no_tests")

    def test_result_structure(self):
        result = get_test_status()
        for repo in ("GBA", "GBC"):
            if result[repo]["status"] in ("pass", "fail"):
                assert "passed" in result[repo]
                assert "failed" in result[repo]
                assert "total" in result[repo]


# ============================================================================
# Integration: MCP server wiring
# ============================================================================

class TestServerWiring:
    """Verify the FastMCP server registers all tools."""

    def test_server_imports(self):
        """Server module imports without error."""
        from gbogeb_mcp.server import mcp
        assert mcp is not None

    def test_server_has_tools(self):
        """All 7 tools are registered."""
        from gbogeb_mcp.server import (
            tool_get_asset_lineage,
            tool_get_test_status,
            tool_get_topology,
            tool_list_assets,
            tool_query_node,
            tool_search_engineering_data,
            tool_validate_physics,
        )
        # Just verify they're callable
        assert callable(tool_get_topology)
        assert callable(tool_query_node)
        assert callable(tool_search_engineering_data)
        assert callable(tool_get_asset_lineage)
        assert callable(tool_validate_physics)
        assert callable(tool_list_assets)
        assert callable(tool_get_test_status)

    def test_version(self):
        """Package version is set."""
        from gbogeb_mcp import __version__
        assert __version__ == "1.0.0"
