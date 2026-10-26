"""
GBOGEB MCP Server — Model Context Protocol for dual-repository context sharing.

Bridges GBOGEB/ABACUS (GBA) and GBOGEB/CODEX (GBC) through a unified
MCP interface.  Exposes seven tools for AI assistants to query knowledge
topologies, engineering data, asset lineage, and physics validation.

Usage:
    # Run directly
    python -m gbogeb_mcp.server

    # Or via the installed entry point
    gbogeb-mcp

    # Claude Desktop / VS Code MCP config
    See README.md for integration instructions.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import __version__
from .tools import (
    get_asset_lineage,
    get_test_status,
    get_topology,
    list_assets,
    query_node,
    search_engineering_data,
    validate_physics,
)

# ============================================================================
# Server initialisation
# ============================================================================

mcp = FastMCP("GBOGEB MCP Server")


# ============================================================================
# Tool registrations
# ============================================================================

@mcp.tool()
def tool_get_topology() -> dict:
    """
    Get the full merged knowledge topology across GBA and GBC repositories.

    Returns a comprehensive overview including:
    - Statistics: total nodes, edges, per-repo counts, category breakdown
    - All nodes grouped by repository (GBA / GBC)
    - All edges including cross-repo dependency links
    - Category definitions with color codes and icons
    - Repository metadata and URLs

    The topology maps 20+ GBA nodes (governance engines, CI/CD, lineage,
    web hub) and 7+ GBC nodes (SVG assets, validators, galleries) with
    cross-repo edges for asset flow, theme sync, and layout blueprints.
    """
    return get_topology()


@mcp.tool()
def tool_query_node(node_id: str) -> dict:
    """
    Query detailed information about a specific topology node.

    Provides the node's full metadata, file path and preview, upstream
    and downstream connections, and all incoming/outgoing edges.

    Args:
        node_id: Unique node identifier, e.g. "GBA-GOV-001", "GBC-ASSET-001",
                 "GBA-LIN-001". Use get_topology() to discover all node IDs.

    Examples:
        tool_query_node("GBA-GOV-001")  → Render Rules Engine details
        tool_query_node("GBC-ASSET-001") → Cryomodule Schematic asset info
        tool_query_node("GBA-EX-001")   → Multi-View Engineering Tool
    """
    return query_node(node_id)


@mcp.tool()
def tool_search_engineering_data(query: str) -> dict:
    """
    Full-text search across all engineering data in both repositories.

    Searches knowledge topology nodes, engineering_data.yaml (cryogenic
    parameters, heat loads, mass balance), visual_data.yaml (asset catalog,
    SVG metadata), stakeholder registry, and lineage manifest.

    Args:
        query: Search term (e.g. "cryomodule", "heat load", "SRF",
               "valve", "lineage", "WCAG", "contrast").

    Returns matches grouped by data source with line numbers and snippets.
    """
    return search_engineering_data(query)


@mcp.tool()
def tool_get_asset_lineage(asset_id: str) -> dict:
    """
    Retrieve full lineage and provenance for a tracked visual asset.

    Returns SHA256 hash, processing status, file size, GBA consumers,
    cross-repo references, and visual registry metadata for the asset.

    Args:
        asset_id: Asset identifier (e.g. "GBC-ASSET-001") or filename
                  (e.g. "cryomodule_schematic.svg").

    Use list_assets() first to discover available asset IDs and filenames.
    """
    return get_asset_lineage(asset_id)


@mcp.tool()
def tool_validate_physics(data: dict | None = None) -> dict:
    """
    Run Helium-4 thermodynamic physics validation.

    Without arguments, validates the full engineering_data.yaml including
    enthalpy calculations, mass balance (ṁ = Q/Δh), and lambda-point
    phase detection.

    With arguments, validates custom cryogenic parameters.

    Args:
        data: Optional dict with keys like:
              - temperature_K: Supply temperature (default 2.0)
              - pressure_bar: Supply pressure (default 1.2)
              - return_temperature_K: Return temperature (default 4.5)
              - Q_static_W: Static heat load in watts
              - Q_dynamic_W: Dynamic heat load in watts

    Examples:
        tool_validate_physics()  → validate default engineering data
        tool_validate_physics({"temperature_K": 2.0, "Q_static_W": 24.5, "Q_dynamic_W": 47.8})
    """
    return validate_physics(data)


@mcp.tool()
def tool_list_assets() -> dict:
    """
    List all tracked binary and SVG assets across both repositories.

    Returns a complete asset inventory from the GBC lineage manifest and
    visual data registry, including filenames, SHA256 hashes, processing
    status, categories, dimensions, and file presence checks.

    Assets include engineering diagrams (cryomodule schematics, facility
    layouts, P&ID diagrams, electrical distribution, thermal flow).
    """
    return list_assets()


@mcp.tool()
def tool_get_test_status() -> dict:
    """
    Run test suites for both GBA and GBC repositories and report results.

    Executes pytest in each repository, returning pass/fail/error counts,
    individual test results, and summary lines. GBA typically has ~79 tests
    covering governance engines; GBC has ~68 tests for asset validation.
    """
    return get_test_status()


# ============================================================================
# Entry point
# ============================================================================

def main() -> None:
    """Run the GBOGEB MCP server (stdio transport)."""
    mcp.run()


if __name__ == "__main__":
    main()
