"""
MCP Tool Implementations — GBOGEB Dual-Repository Context Sharing.

Seven tools exposing the unified knowledge graph, engineering data,
asset lineage, and physics validation across GBA + GBC repositories.

Tools:
  1. get_topology()          — Full topology overview with statistics
  2. query_node(node_id)     — Detailed node info with edges
  3. search_engineering_data(query) — Full-text search across all data
  4. get_asset_lineage(asset_id)    — Asset provenance and hash chain
  5. validate_physics(data)  — He-4 thermodynamic validation
  6. list_assets()           — All tracked binary/SVG assets
  7. get_test_status()       — Test suite results for both repos
"""

from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from .topology import TopologyNavigator


# ============================================================================
# Repository root paths (configurable via environment variables)
# ============================================================================

GBA_ROOT = os.environ.get("GBOGEB_GBA_ROOT", "/home/ubuntu/gbogeb_abacus")
GBC_ROOT = os.environ.get("GBOGEB_GBC_ROOT", "/home/ubuntu/gbogeb_codex")


def _get_navigator() -> TopologyNavigator:
    """Create and load a TopologyNavigator instance."""
    nav = TopologyNavigator(gba_root=GBA_ROOT, gbc_root=GBC_ROOT)
    nav.load()
    return nav


def _load_yaml(path: str | Path) -> dict[str, Any]:
    """Safely load a YAML file, returning empty dict on error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _load_json(path: str | Path) -> dict[str, Any]:
    """Safely load a JSON file, returning empty dict on error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# ============================================================================
# Tool 1: get_topology
# ============================================================================

def get_topology() -> dict[str, Any]:
    """
    Return the full merged knowledge topology with statistics.

    Provides:
      - Summary statistics (node/edge counts, repo breakdown)
      - All nodes grouped by repository
      - All edges with cross-repo annotations
      - Category definitions and color coding
      - Repository metadata

    Returns:
        Complete topology overview as a structured dictionary.
    """
    nav = _get_navigator()
    stats = nav.get_statistics()

    # Group nodes by repo
    gba_nodes = [n.to_dict() for n in nav.get_nodes_by_repo("GBA")]
    gbc_nodes = [n.to_dict() for n in nav.get_nodes_by_repo("GBC")]

    # All edges
    edges = [e.to_dict() for e in nav.edges]
    cross_repo = [e.to_dict() for e in nav.get_cross_repo_edges()]

    return {
        "statistics": stats,
        "repositories": nav.repositories,
        "nodes": {
            "GBA": gba_nodes,
            "GBC": gbc_nodes,
        },
        "edges": edges,
        "cross_repo_edges": cross_repo,
        "categories": nav.categories,
    }


# ============================================================================
# Tool 2: query_node
# ============================================================================

def query_node(node_id: str) -> dict[str, Any]:
    """
    Query detailed information about a specific topology node.

    Args:
        node_id: The unique node identifier (e.g., "GBA-GOV-001", "GBC-ASSET-001").

    Returns:
        Node details including metadata, upstream/downstream connections,
        edges, and the file content preview if the referenced file exists.
    """
    nav = _get_navigator()
    node = nav.get_node(node_id)

    if node is None:
        # Try case-insensitive search
        for nid, n in nav.nodes.items():
            if nid.lower() == node_id.lower():
                node = n
                break

    if node is None:
        return {
            "error": f"Node '{node_id}' not found",
            "available_nodes": sorted(nav.nodes.keys()),
        }

    # Resolve file path
    repo_root = GBA_ROOT if node.repo == "GBA" else GBC_ROOT
    file_path = Path(repo_root) / node.path
    file_exists = file_path.exists()
    file_preview = ""
    if file_exists and file_path.is_file():
        try:
            content = file_path.read_text(encoding="utf-8")
            # Truncate preview to first 80 lines
            lines = content.splitlines()
            file_preview = "\n".join(lines[:80])
            if len(lines) > 80:
                file_preview += f"\n... ({len(lines) - 80} more lines)"
        except Exception:
            file_preview = "(binary or unreadable file)"

    # Upstream / downstream
    upstream = [n.to_dict() for n in nav.get_upstream(node_id)]
    downstream = [n.to_dict() for n in nav.get_downstream(node_id)]
    outgoing_edges = [e.to_dict() for e in nav.get_edges_from(node_id)]
    incoming_edges = [e.to_dict() for e in nav.get_edges_to(node_id)]

    return {
        "node": node.to_dict(),
        "file_path": str(file_path),
        "file_exists": file_exists,
        "file_preview": file_preview,
        "upstream": upstream,
        "downstream": downstream,
        "outgoing_edges": outgoing_edges,
        "incoming_edges": incoming_edges,
    }


# ============================================================================
# Tool 3: search_engineering_data
# ============================================================================

def search_engineering_data(query: str) -> dict[str, Any]:
    """
    Full-text search across engineering data, topology, and configuration.

    Searches:
      - Knowledge topology nodes (both repos)
      - Engineering data YAML (GBA)
      - Visual data registry (GBC)
      - Stakeholder registry (GBA)
      - Asset lineage manifest (GBC)

    Args:
        query: Search query string (e.g., "cryomodule", "heat load", "SRF").

    Returns:
        Matching results grouped by source, with context snippets.
    """
    nav = _get_navigator()
    results: dict[str, Any] = {"query": query, "sources": {}}

    # 1. Topology node search
    matched_nodes = nav.search(query)
    if matched_nodes:
        results["sources"]["topology_nodes"] = [n.to_dict() for n in matched_nodes[:10]]

    # 2. Engineering data YAML (GBA)
    eng_path = Path(GBA_ROOT) / "examples/multi_view_workspace/output/context/engineering_data.yaml"
    eng_matches = _search_yaml_file(eng_path, query)
    if eng_matches:
        results["sources"]["engineering_data"] = eng_matches

    # 3. Visual data registry (GBC)
    vis_path = Path(GBC_ROOT) / "config/visual_data.yaml"
    vis_matches = _search_yaml_file(vis_path, query)
    if vis_matches:
        results["sources"]["visual_data_registry"] = vis_matches

    # 4. Stakeholder registry (GBA)
    for reg_name in ["stakeholder_registry.yaml"]:
        reg_path = Path(GBA_ROOT) / "config" / reg_name
        reg_matches = _search_yaml_file(reg_path, query)
        if reg_matches:
            results["sources"]["stakeholder_registry"] = reg_matches

    # 5. Asset manifest (GBC)
    manifest_path = Path(GBC_ROOT) / "lineage_manifest.json"
    manifest_matches = _search_json_file(manifest_path, query)
    if manifest_matches:
        results["sources"]["lineage_manifest"] = manifest_matches

    results["total_matches"] = sum(
        len(v) if isinstance(v, list) else 1
        for v in results["sources"].values()
    )

    return results


def _search_yaml_file(path: Path, query: str) -> list[dict[str, Any]]:
    """Search a YAML file for lines matching the query."""
    if not path.exists():
        return []
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return []

    query_lower = query.lower()
    matches = []
    for i, line in enumerate(content.splitlines(), 1):
        if query_lower in line.lower():
            matches.append({
                "file": str(path),
                "line": i,
                "content": line.strip(),
            })
    return matches[:20]  # Cap at 20 matches


def _search_json_file(path: Path, query: str) -> list[dict[str, Any]]:
    """Search a JSON file for string values matching the query."""
    if not path.exists():
        return []
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return []

    query_lower = query.lower()
    matches = []
    for i, line in enumerate(content.splitlines(), 1):
        if query_lower in line.lower():
            matches.append({
                "file": str(path),
                "line": i,
                "content": line.strip(),
            })
    return matches[:20]


# ============================================================================
# Tool 4: get_asset_lineage
# ============================================================================

def get_asset_lineage(asset_id: str) -> dict[str, Any]:
    """
    Retrieve full lineage and provenance for a tracked asset.

    Searches the GBC lineage manifest and visual data registry for the
    specified asset, returning SHA256 hash, processing status, consumers,
    and cross-repo references.

    Args:
        asset_id: Asset identifier (e.g., "GBC-ASSET-001") or filename
                  (e.g., "cryomodule_schematic.svg").

    Returns:
        Asset lineage details including hash, status, and dependency chain.
    """
    # Load manifest
    manifest = _load_json(Path(GBC_ROOT) / "lineage_manifest.json")
    visual_data = _load_yaml(Path(GBC_ROOT) / "config/visual_data.yaml")

    # Search by ID or filename in manifest
    manifest_entry = None
    for asset in manifest.get("assets", []):
        if (asset.get("filename", "").lower() == asset_id.lower()
                or asset_id.lower() in asset.get("canonical_path", "").lower()):
            manifest_entry = asset
            break

    # Search visual data registry
    visual_entry = None
    for asset in visual_data.get("assets", []):
        if (asset.get("id", "").lower() == asset_id.lower()
                or asset.get("filename", "").lower() == asset_id.lower()):
            visual_entry = asset
            break

    # Search topology for the node
    nav = _get_navigator()
    topo_node = nav.get_node(asset_id)

    # If searching by filename, try to find the topology node
    if topo_node is None and visual_entry:
        topo_node = nav.get_node(visual_entry.get("id", ""))

    if not manifest_entry and not visual_entry and not topo_node:
        return {
            "error": f"Asset '{asset_id}' not found in lineage manifest or visual registry",
            "hint": "Use list_assets() to see all tracked assets",
        }

    result: dict[str, Any] = {"asset_id": asset_id}

    if manifest_entry:
        result["manifest"] = manifest_entry
        # Verify file still exists on disk
        canonical = Path(GBC_ROOT) / manifest_entry.get("canonical_path", "")
        result["file_exists"] = canonical.exists()
        if canonical.exists():
            result["current_file_size"] = canonical.stat().st_size

    if visual_entry:
        result["visual_registry"] = visual_entry

    if topo_node:
        result["topology_node"] = topo_node.to_dict()
        # Get cross-repo consumers
        downstream = nav.get_downstream(topo_node.id)
        result["consumers"] = [n.to_dict() for n in downstream]

    return result


# ============================================================================
# Tool 5: validate_physics
# ============================================================================

def validate_physics(data: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Run He-4 thermodynamic physics validation.

    If no data is provided, validates the default engineering_data.yaml.
    Otherwise, validates the supplied cryogenic parameters.

    Args:
        data: Optional dict with keys like 'temperature_K', 'pressure_bar',
              'mass_flow_rate_g_s', etc. If None, loads from engineering_data.yaml.

    Returns:
        Validation results including enthalpy calculations, mass balance check,
        lambda-point status, and any physics violations.
    """
    # Try to import the physics validator from GBA
    physics_validator_dir = str(
        Path(GBA_ROOT) / "examples/multi_view_workspace/output/context"
    )
    eng_data_path = Path(GBA_ROOT) / "examples/multi_view_workspace/output/context/engineering_data.yaml"

    results: dict[str, Any] = {"validation_engine": "HeliumPropertyEngine (GBA)"}

    try:
        # Add GBA physics validator to path
        if physics_validator_dir not in sys.path:
            sys.path.insert(0, physics_validator_dir)

        from physics_validator import (  # type: ignore[import-not-found]
            HeliumPropertyEngine,
            validate_from_yaml,
        )

        if data is None:
            # Validate from engineering_data.yaml
            if eng_data_path.exists():
                report = validate_from_yaml(str(eng_data_path))
                results["source"] = str(eng_data_path)
                results["report"] = report
            else:
                results["error"] = f"Engineering data not found: {eng_data_path}"
        else:
            # Validate supplied parameters
            engine = HeliumPropertyEngine()
            temp_k = data.get("temperature_K", 2.0)
            pressure_bar = data.get("pressure_bar", 1.2)

            results["input"] = data
            results["enthalpy_J_g"] = engine.enthalpy(temp_k)
            results["density_kg_m3"] = engine.density(temp_k)
            results["viscosity_Pa_s"] = engine.viscosity(temp_k)
            results["is_superfluid"] = engine.is_superfluid(temp_k)
            results["phase"] = "He-II (superfluid)" if engine.is_superfluid(temp_k) else "He-I (normal)"

            # Mass balance if Q values provided
            q_static = data.get("Q_static_W")
            q_dynamic = data.get("Q_dynamic_W")
            t_return = data.get("return_temperature_K", 4.5)
            if q_static is not None and q_dynamic is not None:
                h_supply = engine.enthalpy(temp_k)
                h_return = engine.enthalpy(t_return)
                delta_h = h_return - h_supply
                if delta_h > 0:
                    m_dot = (q_static + q_dynamic) / delta_h
                    results["mass_balance"] = {
                        "h_supply_J_g": h_supply,
                        "h_return_J_g": h_return,
                        "delta_h_J_g": delta_h,
                        "m_dot_calculated_g_s": round(m_dot, 4),
                        "Q_total_W": q_static + q_dynamic,
                    }

    except ImportError:
        results["error"] = "Physics validator module not available"
        results["fallback"] = _fallback_physics_check(data)
    except Exception as exc:
        results["error"] = f"Validation failed: {str(exc)}"
        results["fallback"] = _fallback_physics_check(data)

    return results


def _fallback_physics_check(data: dict[str, Any] | None) -> dict[str, Any]:
    """Basic physics sanity check without the full engine."""
    if data is None:
        # Load engineering data directly
        eng_path = Path(GBA_ROOT) / "examples/multi_view_workspace/output/context/engineering_data.yaml"
        if eng_path.exists():
            eng = _load_yaml(eng_path)
            cryo = eng.get("cryogenic", {})
            metrics = eng.get("engineering_metrics", {})
            mass_balance = metrics.get("mass_balance", {})
            return {
                "source": str(eng_path),
                "coolant": cryo.get("coolant"),
                "supply_temperature_K": cryo.get("supply_temperature_K"),
                "return_temperature_K": cryo.get("return_temperature_K"),
                "lambda_point_K": cryo.get("lambda_point_K"),
                "is_below_lambda": cryo.get("supply_temperature_K", 0) < cryo.get("lambda_point_K", 2.1768),
                "Q_total_W": metrics.get("heat_loads", {}).get("summary", {}).get("Q_total_W"),
                "mass_balance_check": mass_balance.get("balance_check"),
                "m_dot_design_g_s": mass_balance.get("m_dot_design_g_s"),
            }
    return {"note": "No data provided and fallback could not load defaults"}


# ============================================================================
# Tool 6: list_assets
# ============================================================================

def list_assets() -> dict[str, Any]:
    """
    List all tracked binary and SVG assets across both repositories.

    Returns:
        Asset inventory with filenames, SHA256 hashes, processing status,
        categories, and file sizes for all assets in GBC lineage manifest
        and visual data registry.
    """
    manifest = _load_json(Path(GBC_ROOT) / "lineage_manifest.json")
    visual_data = _load_yaml(Path(GBC_ROOT) / "config/visual_data.yaml")

    # Assets from manifest
    manifest_assets = manifest.get("assets", [])

    # Assets from visual registry
    registry_assets = visual_data.get("assets", [])

    # Check file existence
    for asset in manifest_assets:
        canonical = Path(GBC_ROOT) / asset.get("canonical_path", "")
        asset["file_present"] = canonical.exists()

    # SVG files on disk
    svg_dir = Path(GBC_ROOT) / "assets" / "canonical"
    svg_files = []
    if svg_dir.exists():
        for f in sorted(svg_dir.iterdir()):
            if f.suffix == ".svg":
                svg_files.append({
                    "filename": f.name,
                    "size_bytes": f.stat().st_size,
                    "path": str(f.relative_to(GBC_ROOT)),
                })

    return {
        "manifest_version": manifest.get("version", "unknown"),
        "last_updated": manifest.get("last_updated", "unknown"),
        "repository": manifest.get("repository", "GBOGEB/CODEX"),
        "manifest_assets": manifest_assets,
        "registry_assets": [
            {
                "id": a.get("id"),
                "filename": a.get("filename"),
                "title": a.get("title"),
                "category": a.get("category"),
                "domain": a.get("domain"),
                "dimensions": a.get("dimensions"),
            }
            for a in registry_assets
        ],
        "svg_files_on_disk": svg_files,
        "total_tracked": len(manifest_assets),
        "total_on_disk": len(svg_files),
    }


# ============================================================================
# Tool 7: get_test_status
# ============================================================================

def get_test_status() -> dict[str, Any]:
    """
    Run and report test suite status for both GBA and GBC repositories.

    Executes pytest in each repository and returns pass/fail counts,
    test names, and any failure details.

    Returns:
        Test results for GBA and GBC including counts and details.
    """
    results: dict[str, Any] = {}

    for repo_name, repo_root in [("GBA", GBA_ROOT), ("GBC", GBC_ROOT)]:
        repo_path = Path(repo_root)
        test_dir = repo_path / "tests"

        if not test_dir.exists():
            results[repo_name] = {
                "status": "no_tests",
                "message": f"No tests/ directory found in {repo_root}",
            }
            continue

        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", str(test_dir), "-v", "--tb=short", "--no-header"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(repo_path),
            )

            output = proc.stdout + proc.stderr
            lines = output.splitlines()

            # Parse results
            passed = 0
            failed = 0
            errors = 0
            test_details: list[dict[str, str]] = []

            for line in lines:
                if "PASSED" in line:
                    passed += 1
                    test_name = line.split("::")[1].split(" ")[0] if "::" in line else line.strip()
                    test_details.append({"test": test_name, "status": "PASSED"})
                elif "FAILED" in line:
                    failed += 1
                    test_name = line.split("::")[1].split(" ")[0] if "::" in line else line.strip()
                    test_details.append({"test": test_name, "status": "FAILED"})
                elif "ERROR" in line and "::" in line:
                    errors += 1
                    test_details.append({"test": line.strip(), "status": "ERROR"})

            # Extract summary line
            summary_line = ""
            for line in reversed(lines):
                if "passed" in line or "failed" in line or "error" in line:
                    summary_line = line.strip()
                    break

            results[repo_name] = {
                "status": "pass" if proc.returncode == 0 else "fail",
                "return_code": proc.returncode,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "total": passed + failed + errors,
                "summary": summary_line,
                "tests": test_details[:50],  # Cap output
            }

        except subprocess.TimeoutExpired:
            results[repo_name] = {
                "status": "timeout",
                "message": "Test execution timed out after 120s",
            }
        except Exception as exc:
            results[repo_name] = {
                "status": "error",
                "message": str(exc),
            }

    return results
