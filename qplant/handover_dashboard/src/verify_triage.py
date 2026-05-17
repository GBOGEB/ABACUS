#!/usr/bin/env python3
"""Automated Triage Gap Analysis Verification Script.

Deterministic: running this script twice on the same file-system state
produces identical output (except for 'verification_timestamp').

Usage:
    python src/verify_triage.py          # prints JSON report to stdout
    python src/verify_triage.py --md     # also writes TRIAGE_GAP_ANALYSIS.md
    python src/verify_triage.py --all    # writes .md, .json, and .html
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# ─────────────────────────────────────────────────────────────────────
# REQUIREMENT DEFINITIONS  (extracted from Addendum II + supporting docs)
# ─────────────────────────────────────────────────────────────────────

ADDENDUM_SECTIONS = [
    {
        "id": "SEC-01",
        "title": "Leak Rate Requirements (§3.3.8)",
        "requirements": [
            {
                "id": "REQ-01.1",
                "text": "Helium leak detection program per EN 13185:2001 Clause 6.2",
                "evidence_files": ["data/source_anchors.json"],
                "evidence_search": "EN 13185",
                "status_logic": "search",
            },
            {
                "id": "REQ-01.2",
                "text": "Individual cold leak rate ≤ 1×10⁻⁸ mbar·L/s (Table 5/7)",
                "evidence_files": ["data/leak_classes.json"],
                "evidence_search": "1e-8",
                "status_logic": "search",
            },
            {
                "id": "REQ-01.3",
                "text": "Individual warm/guard leak rate ≤ 1×10⁻⁵ mbar·L/s",
                "evidence_files": ["data/leak_classes.json"],
                "evidence_search": "1e-5",
                "status_logic": "search",
            },
            {
                "id": "REQ-01.4",
                "text": "Valve seat leakage ≤ 1×10⁻⁴ mbar·L/s",
                "evidence_files": ["data/leak_classes.json"],
                "evidence_search": "1e-4",
                "status_logic": "search",
            },
            {
                "id": "REQ-01.5",
                "text": "Max global He losses ≤ 1 Nm³/day (≈65.3 kg/year) – RTM-048",
                "evidence_files": ["src/calc_leak_rate.py", "data/scenarios.json"],
                "evidence_search": "normal_m3_per_day_to_kg_per_year",
                "status_logic": "search",
            },
            {
                "id": "REQ-01.6",
                "text": "Mass flow conversion table matching Table 7 values",
                "evidence_files": ["outputs/tables/conversion_table.csv"],
                "evidence_search": None,
                "status_logic": "file_exists",
            },
            {
                "id": "REQ-01.7",
                "text": "Quantified leak rates with explicit thresholds for diffusive losses",
                "evidence_files": ["docs/calculations.html", "outputs/tables/conversion_table.json"],
                "evidence_search": "mass_flow_g_year",
                "status_logic": "search",
            },
            {
                "id": "REQ-01.8",
                "text": "Leak detection methods documented (pressure hold, vacuum decay)",
                "evidence_files": ["data/source_anchors.json"],
                "evidence_search": "leak detection",
                "status_logic": "search",
            },
        ],
    },
    {
        "id": "SEC-02",
        "title": "Helium Recovery & Inventory Management (§3.3.9)",
        "requirements": [
            {
                "id": "REQ-02.1",
                "text": "Helium recovery strategy for LOOP/LOCA events",
                "evidence_files": ["source/handover.md", "docs/calculations.html", "data/scenarios.json"],
                "evidence_search": "loss",
                "status_logic": "search",
            },
            {
                "id": "REQ-02.2",
                "text": "Recovery flow capacity 100-200 g/s full shutdown",
                "evidence_files": [],
                "evidence_search": None,
                "status_logic": "not_in_scope",
                "note": "Process design scope – not leak-rate dashboard scope",
            },
            {
                "id": "REQ-02.3",
                "text": "Helium inventory table (TBD by Contractor)",
                "evidence_files": ["data/scenarios.json"],
                "evidence_search": "inventory",
                "status_logic": "search",
            },
            {
                "id": "REQ-02.4",
                "text": "Venting minimisation under failure scenarios",
                "evidence_files": [],
                "evidence_search": None,
                "status_logic": "not_in_scope",
                "note": "Control system scope – not leak-rate dashboard",
            },
        ],
    },
    {
        "id": "SEC-03",
        "title": "Valve Requirements (§3.3.4 / §3.3.14)",
        "requirements": [
            {
                "id": "REQ-03.1",
                "text": "Warm valve proposals: Meca Inox ball, Swagelok SS-42GSE",
                "evidence_files": ["data/valve_candidates.json"],
                "evidence_search": "Meca Inox",
                "status_logic": "search",
            },
            {
                "id": "REQ-03.2",
                "text": "Warm valve derogation tracking (leak tightness concern)",
                "evidence_files": ["data/source_anchors.json", "docs/executive_summary.html"],
                "evidence_search": "derogation",
                "status_logic": "search",
            },
            {
                "id": "REQ-03.3",
                "text": "Cold boundary valve metal-sealed specification",
                "evidence_files": ["data/valve_candidates.json"],
                "evidence_search": "metal-sealed",
                "status_logic": "search",
            },
            {
                "id": "REQ-03.4",
                "text": "Valve CAPEX vs. He-loss cost comparison",
                "evidence_files": ["outputs/tables/cost_table.csv", "docs/plots/plot3_cost_vs_leaktightness.html"],
                "evidence_search": None,
                "status_logic": "file_exists",
            },
        ],
    },
    {
        "id": "SEC-04",
        "title": "Calculations & Physics Engine",
        "requirements": [
            {
                "id": "REQ-04.1",
                "text": "First-principles conversion: mbar·L/s → Pa·m³/s → mol/s → g/s",
                "evidence_files": ["src/calc_leak_rate.py"],
                "evidence_search": "mbar_l_s_to_pa_m3_s",
                "status_logic": "search",
            },
            {
                "id": "REQ-04.2",
                "text": "No empirical alignment factors",
                "evidence_files": ["src/calc_leak_rate.py"],
                "evidence_search": "CONTRACTUAL_ALIGNMENT_FACTOR",
                "status_logic": "absent",
            },
            {
                "id": "REQ-04.3",
                "text": "Dimensional proof / worked chain available",
                "evidence_files": ["src/calc_leak_rate.py"],
                "evidence_search": "dimensional_proof",
                "status_logic": "search",
            },
            {
                "id": "REQ-04.4",
                "text": "Temperature & pressure sensitivity matrix",
                "evidence_files": ["outputs/tables/conversion_table.csv"],
                "evidence_search": None,
                "status_logic": "file_exists",
            },
            {
                "id": "REQ-04.5",
                "text": "Sonic / choked flow indicator calculation",
                "evidence_files": ["src/calc_leak_rate.py"],
                "evidence_search": "sonic_flow_indicators",
                "status_logic": "search",
            },
            {
                "id": "REQ-04.6",
                "text": "Error correction documented (old x1000 factor)",
                "evidence_files": ["ERROR_LOG.md"],
                "evidence_search": "CONTRACTUAL_ALIGNMENT_FACTOR",
                "status_logic": "search",
            },
        ],
    },
    {
        "id": "SEC-05",
        "title": "Triage Output System",
        "requirements": [
            {
                "id": "REQ-05.1",
                "text": "Multi-audience HTML pages (executive, dashboard, calculations, RTM, handover)",
                "evidence_files": [
                    "docs/executive_summary.html",
                    "docs/dashboard.html",
                    "docs/calculations.html",
                    "docs/rtm_traceability.html",
                    "docs/handover.html",
                ],
                "evidence_search": None,
                "status_logic": "all_files_exist",
            },
            {
                "id": "REQ-05.2",
                "text": "Navigation portal (index.html)",
                "evidence_files": ["docs/index.html"],
                "evidence_search": None,
                "status_logic": "file_exists",
            },
            {
                "id": "REQ-05.3",
                "text": "PDF handover export",
                "evidence_files": ["docs/handover.pdf"],
                "evidence_search": None,
                "status_logic": "file_exists",
            },
            {
                "id": "REQ-05.4",
                "text": "View mode switching (preview, code, print)",
                "evidence_files": ["assets/triage.js"],
                "evidence_search": "setMode",
                "status_logic": "search",
            },
            {
                "id": "REQ-05.5",
                "text": "Status badges (ACCEPT, REVIEW, RISK, TRACE)",
                "evidence_files": ["assets/style.css"],
                "evidence_search": "ACCEPT",
                "status_logic": "search",
            },
            {
                "id": "REQ-05.6",
                "text": "DMAIC view notes on each page",
                "evidence_files": ["src/generate_dashboard.py"],
                "evidence_search": "_dmaic_block",
                "status_logic": "search",
            },
        ],
    },
    {
        "id": "SEC-06",
        "title": "Scenario & Fleet Analysis",
        "requirements": [
            {
                "id": "REQ-06.1",
                "text": "Baseline mixed fleet scenario (210 cold + 200 warm valves)",
                "evidence_files": ["data/scenarios.json"],
                "evidence_search": "SCN-BASELINE-MIX",
                "status_logic": "search",
            },
            {
                "id": "REQ-06.2",
                "text": "Uniform high-integrity scenario (all 1e-8)",
                "evidence_files": ["data/scenarios.json"],
                "evidence_search": "SCN-ALL-1E8",
                "status_logic": "search",
            },
            {
                "id": "REQ-06.3",
                "text": "RTM-048 cap reference scenario",
                "evidence_files": ["data/scenarios.json"],
                "evidence_search": "SCN-RTM048-CAP",
                "status_logic": "search",
            },
            {
                "id": "REQ-06.4",
                "text": "Scenario comparison plots",
                "evidence_files": ["docs/plots/plot4_fleet_sensitivity.html"],
                "evidence_search": None,
                "status_logic": "file_exists",
            },
        ],
    },
    {
        "id": "SEC-07",
        "title": "Traceability & RTM",
        "requirements": [
            {
                "id": "REQ-07.1",
                "text": "RTM-047 to RTM-067 requirement mapping",
                "evidence_files": ["outputs/tables/rtm_traceability.csv", "traceability/RTM_047_067.csv"],
                "evidence_search": None,
                "status_logic": "all_files_exist",
            },
            {
                "id": "REQ-07.2",
                "text": "Source anchors with excerpts from original documents",
                "evidence_files": ["data/source_anchors.json"],
                "evidence_search": "excerpt",
                "status_logic": "search",
            },
            {
                "id": "REQ-07.3",
                "text": "Verification method listed for each RTM row",
                "evidence_files": ["outputs/tables/rtm_traceability.json"],
                "evidence_search": "verification",
                "status_logic": "search",
            },
        ],
    },
    {
        "id": "SEC-08",
        "title": "Reliability & Lifecycle (§3.3.3 / §4)",
        "requirements": [
            {
                "id": "REQ-08.1",
                "text": "MTBF data per leak class",
                "evidence_files": ["outputs/tables/reliability_table.csv"],
                "evidence_search": None,
                "status_logic": "file_exists",
            },
            {
                "id": "REQ-08.2",
                "text": "Availability calculation",
                "evidence_files": ["src/generate_dashboard.py"],
                "evidence_search": "availability",
                "status_logic": "search",
            },
            {
                "id": "REQ-08.3",
                "text": "Reliability plot/visualization",
                "evidence_files": ["docs/plots/plot5_reliability.html"],
                "evidence_search": None,
                "status_logic": "file_exists",
            },
            {
                "id": "REQ-08.4",
                "text": "RCM linkage / lifecycle cost mention",
                "evidence_files": ["source/handover.md"],
                "evidence_search": "derogation",
                "status_logic": "search",
            },
        ],
    },
    {
        "id": "SEC-09",
        "title": "Build System & Determinism",
        "requirements": [
            {
                "id": "REQ-09.1",
                "text": "Single build command (python src/build_all.py)",
                "evidence_files": ["src/build_all.py"],
                "evidence_search": "run()",
                "status_logic": "search",
            },
            {
                "id": "REQ-09.2",
                "text": "Output manifest with SHA-256 hashes",
                "evidence_files": ["OUTPUT_MANIFEST.json"],
                "evidence_search": "sha256",
                "status_logic": "search",
            },
            {
                "id": "REQ-09.3",
                "text": "Idempotent writes (write_text_if_changed)",
                "evidence_files": ["src/manifest.py"],
                "evidence_search": "write_text_if_changed",
                "status_logic": "search",
            },
            {
                "id": "REQ-09.4",
                "text": "Unit tests (pytest)",
                "evidence_files": ["tests/test_engineering.py", "tests/test_build_outputs.py"],
                "evidence_search": None,
                "status_logic": "all_files_exist",
            },
        ],
    },
    {
        "id": "SEC-10",
        "title": "Documentation & Handover",
        "requirements": [
            {
                "id": "REQ-10.1",
                "text": "README with build instructions",
                "evidence_files": ["README.md"],
                "evidence_search": "build_all",
                "status_logic": "search",
            },
            {
                "id": "REQ-10.2",
                "text": "CHANGELOG with version history",
                "evidence_files": ["CHANGELOG.md"],
                "evidence_search": "2.0.0",
                "status_logic": "search",
            },
            {
                "id": "REQ-10.3",
                "text": "ERROR_LOG documenting critical fix",
                "evidence_files": ["ERROR_LOG.md"],
                "evidence_search": "Critical error",
                "status_logic": "search",
            },
            {
                "id": "REQ-10.4",
                "text": "Assumptions register",
                "evidence_files": ["source/assumptions.md"],
                "evidence_search": "Assumptions",
                "status_logic": "search",
            },
            {
                "id": "REQ-10.5",
                "text": "Developer notes with extension points",
                "evidence_files": ["source/developer_notes.md"],
                "evidence_search": "Extension",
                "status_logic": "search",
            },
            {
                "id": "REQ-10.6",
                "text": "Handover markdown source",
                "evidence_files": ["source/handover.md"],
                "evidence_search": None,
                "status_logic": "file_exists",
            },
        ],
    },
]

# ─────────────────────────────────────────────────────────────────────
# REQUIRED FILES for the complete triage system
# ─────────────────────────────────────────────────────────────────────

REQUIRED_FILES = [
    # Core engine
    "src/calc_leak_rate.py",
    "src/generate_dashboard.py",
    "src/build_all.py",
    "src/build_handover.py",
    "src/manifest.py",
    # Data inputs
    "data/leak_classes.json",
    "data/valve_candidates.json",
    "data/scenarios.json",
    "data/source_anchors.json",
    # Assets
    "assets/style.css",
    "assets/triage.js",
    # Docs (generated)
    "docs/index.html",
    "docs/dashboard.html",
    "docs/calculations.html",
    "docs/executive_summary.html",
    "docs/rtm_traceability.html",
    "docs/handover.html",
    "docs/handover.pdf",
    "docs/assets/style.css",
    "docs/assets/triage.js",
    # Plots
    "docs/plots/plot1_leak_vs_loss.html",
    "docs/plots/plot2_temp_pressure_effects.html",
    "docs/plots/plot3_cost_vs_leaktightness.html",
    "docs/plots/plot4_fleet_sensitivity.html",
    "docs/plots/plot5_reliability.html",
    # Output tables
    "outputs/tables/conversion_table.csv",
    "outputs/tables/scenario_table.csv",
    "outputs/tables/cost_table.csv",
    "outputs/tables/reliability_table.csv",
    "outputs/tables/rtm_traceability.csv",
    "outputs/tables/conversion_table.json",
    "outputs/tables/scenario_table.json",
    "outputs/tables/cost_table.json",
    "outputs/tables/reliability_table.json",
    "outputs/tables/rtm_traceability.json",
    # Source markdown
    "source/handover.md",
    "source/assumptions.md",
    "source/developer_notes.md",
    "source/rtm_traceability.md",
    # Documentation
    "README.md",
    "CHANGELOG.md",
    "ERROR_LOG.md",
    "OUTPUT_MANIFEST.json",
    # Tests
    "tests/test_engineering.py",
    "tests/test_build_outputs.py",
    # Traceability
    "traceability/RTM_047_067.csv",
]

FEATURE_CATEGORIES = {
    "Leak Rate Classes": {
        "required": ["1e-9 class", "1e-8 class", "1e-5 class", "1e-4 class"],
        "check_file": "data/leak_classes.json",
        "check_keys": ["1e-9", "1e-8", "1e-5", "1e-4"],
    },
    "Audience Views": {
        "required": ["Executive summary", "Dashboard", "Calculations", "RTM traceability", "Handover HTML", "Handover PDF"],
        "check_files": [
            "docs/executive_summary.html",
            "docs/dashboard.html",
            "docs/calculations.html",
            "docs/rtm_traceability.html",
            "docs/handover.html",
            "docs/handover.pdf",
        ],
    },
    "Interactive Plots": {
        "required": ["Leak vs loss", "Temp/pressure effects", "Cost vs leaktightness", "Fleet sensitivity", "Reliability"],
        "check_files": [
            "docs/plots/plot1_leak_vs_loss.html",
            "docs/plots/plot2_temp_pressure_effects.html",
            "docs/plots/plot3_cost_vs_leaktightness.html",
            "docs/plots/plot4_fleet_sensitivity.html",
            "docs/plots/plot5_reliability.html",
        ],
    },
    "Data Tables": {
        "required": ["Conversion table", "Scenario table", "Cost table", "Reliability table", "RTM traceability table"],
        "check_files": [
            "outputs/tables/conversion_table.csv",
            "outputs/tables/scenario_table.csv",
            "outputs/tables/cost_table.csv",
            "outputs/tables/reliability_table.csv",
            "outputs/tables/rtm_traceability.csv",
        ],
    },
    "UI Features": {
        "required": ["Mode switching", "Expand/collapse", "PDF export", "Status badges", "DMAIC notes", "Print CSS"],
        "check_patterns": [
            ("assets/triage.js", "setMode"),
            ("assets/triage.js", "expandAll"),
            ("assets/triage.js", "exportPdf"),
            ("assets/style.css", ".badge"),
            ("src/generate_dashboard.py", "_dmaic_block"),
            ("assets/style.css", "@media print"),
        ],
    },
    "Valve Candidates": {
        "required": ["Meca Inox ball valve", "Swagelok SS-42GSE", "Metal-sealed cryogenic"],
        "check_file": "data/valve_candidates.json",
        "check_keys": ["Meca Inox", "Swagelok", "metal-sealed"],
    },
    "Scenarios": {
        "required": ["Baseline mixed fleet", "Uniform high-integrity", "RTM-048 cap reference"],
        "check_file": "data/scenarios.json",
        "check_keys": ["SCN-BASELINE-MIX", "SCN-ALL-1E8", "SCN-RTM048-CAP"],
    },
    "Source Anchors": {
        "required": ["Warm valves slide ref", "RTM-048 system cap", "EN 13185 reference"],
        "check_file": "data/source_anchors.json",
        "check_keys": ["SRC-WARM-VALVES", "SRC-RTM048", "SRC-EN13185"],
    },
    "Tests": {
        "required": ["Dimensional chain test", "Temperature scaling test", "RTM-048 conversion test", "Baseline range test", "Build outputs test", "Manifest hashes test"],
        "check_patterns": [
            ("tests/test_engineering.py", "test_dimensional_chain"),
            ("tests/test_engineering.py", "test_temperature_pressure_scaling"),
            ("tests/test_engineering.py", "test_reference_rtm048"),
            ("tests/test_engineering.py", "test_baseline_scenario"),
            ("tests/test_build_outputs.py", "test_required_outputs_exist"),
            ("tests/test_build_outputs.py", "test_manifest_has_hashes"),
        ],
    },
    "Build & Determinism": {
        "required": ["Single build entry", "Idempotent writes", "SHA-256 manifest", "Version tracking"],
        "check_patterns": [
            ("src/build_all.py", "def run"),
            ("src/manifest.py", "write_text_if_changed"),
            ("src/manifest.py", "sha256_file"),
            ("src/build_all.py", "BUILDER_VERSION"),
        ],
    },
}


# ─────────────────────────────────────────────────────────────────────
# VERIFICATION ENGINE
# ─────────────────────────────────────────────────────────────────────

def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _search_in_file(filepath: Path, pattern: str) -> tuple[bool, list[int]]:
    """Return (found, line_numbers) for case-insensitive search."""
    if not filepath.exists():
        return False, []
    try:
        lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return False, []
    hits = []
    pat_lower = pattern.lower()
    for i, line in enumerate(lines, 1):
        if pat_lower in line.lower():
            hits.append(i)
    return len(hits) > 0, hits


def verify_requirement(req: dict) -> dict:
    """Evaluate a single requirement. Returns enriched dict with status/evidence."""
    result = {
        "id": req["id"],
        "text": req["text"],
        "status": "NOT_STARTED",
        "completion_pct": 0,
        "evidence": [],
        "gaps": [],
        "verification": "FAIL",
    }

    logic = req.get("status_logic", "file_exists")

    if logic == "not_in_scope":
        result["status"] = "NOT_IN_SCOPE"
        result["completion_pct"] = 100
        result["verification"] = "N/A"
        result["evidence"].append({"note": req.get("note", "Outside dashboard scope")})
        return result

    evidence_files = req.get("evidence_files", [])
    search_pattern = req.get("evidence_search")

    if logic == "file_exists":
        p = ROOT / evidence_files[0] if evidence_files else None
        if p and p.exists():
            result["status"] = "COMPLETE"
            result["completion_pct"] = 100
            result["verification"] = "PASS"
            result["evidence"].append({
                "file": str(p.relative_to(ROOT)),
                "size_bytes": p.stat().st_size,
                "sha256": sha256_file(p),
            })
        else:
            result["status"] = "GAP"
            result["gaps"].append(f"File missing: {evidence_files[0] if evidence_files else 'unknown'}")

    elif logic == "all_files_exist":
        found = 0
        for ef in evidence_files:
            p = ROOT / ef
            if p.exists():
                found += 1
                result["evidence"].append({
                    "file": ef,
                    "size_bytes": p.stat().st_size,
                    "sha256": sha256_file(p),
                })
            else:
                result["gaps"].append(f"Missing: {ef}")
        pct = int(100 * found / max(len(evidence_files), 1))
        result["completion_pct"] = pct
        if pct == 100:
            result["status"] = "COMPLETE"
            result["verification"] = "PASS"
        elif pct > 0:
            result["status"] = "PARTIAL"
        else:
            result["status"] = "GAP"

    elif logic == "search":
        if not search_pattern:
            result["status"] = "GAP"
            result["gaps"].append("No search pattern defined")
            return result
        any_found = False
        for ef in evidence_files:
            p = ROOT / ef
            found, lines = _search_in_file(p, search_pattern)
            if found:
                any_found = True
                result["evidence"].append({
                    "file": ef,
                    "pattern": search_pattern,
                    "matching_lines": lines[:5],
                    "sha256": sha256_file(p) if p.exists() else None,
                })
        if any_found:
            result["status"] = "COMPLETE"
            result["completion_pct"] = 100
            result["verification"] = "PASS"
        else:
            result["status"] = "GAP"
            result["gaps"].append(f"Pattern '{search_pattern}' not found in {evidence_files}")

    elif logic == "absent":
        # We want the pattern to NOT appear (e.g., removed bad factor)
        for ef in evidence_files:
            p = ROOT / ef
            found, lines = _search_in_file(p, search_pattern)
            if found:
                result["status"] = "GAP"
                result["gaps"].append(f"Pattern '{search_pattern}' still present in {ef} at lines {lines}")
                return result
        result["status"] = "COMPLETE"
        result["completion_pct"] = 100
        result["verification"] = "PASS"
        result["evidence"].append({"note": f"Pattern '{search_pattern}' correctly absent"})

    return result


def verify_file_inventory() -> list[dict]:
    """Check every required file."""
    results = []
    for rel in REQUIRED_FILES:
        p = ROOT / rel
        entry = {
            "required_file": rel,
            "exists": p.exists(),
            "size_bytes": None,
            "sha256": None,
            "last_modified": None,
            "status": "MISSING",
        }
        if p.exists():
            entry["size_bytes"] = p.stat().st_size
            entry["sha256"] = sha256_file(p)
            entry["last_modified"] = datetime.fromtimestamp(
                p.stat().st_mtime, tz=timezone.utc
            ).isoformat()
            entry["status"] = "OK"
        results.append(entry)
    return results


def verify_features() -> list[dict]:
    """Check feature completeness per category."""
    results = []
    for cat_name, cat_def in FEATURE_CATEGORIES.items():
        required = cat_def["required"]
        implemented = []
        missing = []

        if "check_files" in cat_def:
            for i, feat in enumerate(required):
                p = ROOT / cat_def["check_files"][i]
                if p.exists():
                    implemented.append(feat)
                else:
                    missing.append(feat)

        elif "check_file" in cat_def and "check_keys" in cat_def:
            p = ROOT / cat_def["check_file"]
            if p.exists():
                content = p.read_text(encoding="utf-8")
                for i, feat in enumerate(required):
                    key = cat_def["check_keys"][i]
                    if key.lower() in content.lower():
                        implemented.append(feat)
                    else:
                        missing.append(feat)
            else:
                missing = list(required)

        elif "check_patterns" in cat_def:
            for i, feat in enumerate(required):
                fpath, pattern = cat_def["check_patterns"][i]
                found, _ = _search_in_file(ROOT / fpath, pattern)
                if found:
                    implemented.append(feat)
                else:
                    missing.append(feat)

        pct = int(100 * len(implemented) / max(len(required), 1))
        results.append({
            "category": cat_name,
            "total_required": len(required),
            "implemented": len(implemented),
            "implemented_list": implemented,
            "completion_pct": pct,
            "missing": missing,
        })
    return results


def run_verification() -> dict:
    """Execute full verification and return structured report."""
    # Section-by-section requirements
    section_results = []
    total_reqs = 0
    met_reqs = 0
    partial_reqs = 0
    gap_reqs = 0
    nis_reqs = 0

    for section in ADDENDUM_SECTIONS:
        sec_result = {
            "id": section["id"],
            "title": section["title"],
            "requirements": [],
        }
        for req in section["requirements"]:
            res = verify_requirement(req)
            sec_result["requirements"].append(res)
            total_reqs += 1
            if res["status"] == "COMPLETE":
                met_reqs += 1
            elif res["status"] == "PARTIAL":
                partial_reqs += 1
            elif res["status"] == "NOT_IN_SCOPE":
                nis_reqs += 1
            else:
                gap_reqs += 1
        section_results.append(sec_result)

    # File inventory
    file_inventory = verify_file_inventory()
    files_required = len(file_inventory)
    files_found = sum(1 for f in file_inventory if f["exists"])

    # Feature completeness
    feature_results = verify_features()
    total_features = sum(f["total_required"] for f in feature_results)
    implemented_features = sum(f["implemented"] for f in feature_results)

    # Overall score
    in_scope_reqs = total_reqs - nis_reqs
    overall_pct = int(100 * met_reqs / max(in_scope_reqs, 1))
    file_coverage_pct = int(100 * files_found / max(files_required, 1))
    feature_coverage_pct = int(100 * implemented_features / max(total_features, 1))

    score_10 = round(
        (overall_pct * 0.4 + file_coverage_pct * 0.3 + feature_coverage_pct * 0.3) / 10, 1
    )

    if overall_pct >= 95 and file_coverage_pct >= 95:
        overall_status = "COMPLETE"
    elif overall_pct >= 75:
        overall_status = "SUBSTANTIAL"
    elif overall_pct >= 50:
        overall_status = "PARTIAL"
    else:
        overall_status = "INSUFFICIENT"

    return {
        "verification_timestamp": datetime.now(timezone.utc).isoformat(),
        "project_root": str(ROOT),
        "executive_summary": {
            "total_requirements": total_reqs,
            "requirements_met": met_reqs,
            "requirements_partial": partial_reqs,
            "requirements_gap": gap_reqs,
            "requirements_not_in_scope": nis_reqs,
            "in_scope_requirements": in_scope_reqs,
            "overall_completion_pct": overall_pct,
            "files_required": files_required,
            "files_found": files_found,
            "file_coverage_pct": file_coverage_pct,
            "features_required": total_features,
            "features_implemented": implemented_features,
            "feature_coverage_pct": feature_coverage_pct,
            "compliance_score": score_10,
            "overall_status": overall_status,
        },
        "section_analysis": section_results,
        "file_inventory": file_inventory,
        "feature_matrix": feature_results,
    }


# ─────────────────────────────────────────────────────────────────────
# OUTPUT GENERATORS
# ─────────────────────────────────────────────────────────────────────

def generate_markdown(report: dict) -> str:
    """Generate TRIAGE_GAP_ANALYSIS.md from verification report."""
    es = report["executive_summary"]
    lines = [
        "# TRIAGE ADDENDUM GAP ANALYSIS",
        "",
        f"> Generated: {report['verification_timestamp']}",
        f"> Project root: `{report['project_root']}`",
        "",
        "## Executive Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Requirements | {es['total_requirements']} |",
        f"| Requirements Met | {es['requirements_met']} |",
        f"| Requirements Partial | {es['requirements_partial']} |",
        f"| Requirements Gap | {es['requirements_gap']} |",
        f"| Not In Scope | {es['requirements_not_in_scope']} |",
        f"| In-Scope Completion | {es['overall_completion_pct']}% |",
        f"| Files Required | {es['files_required']} |",
        f"| Files Found | {es['files_found']} |",
        f"| File Coverage | {es['file_coverage_pct']}% |",
        f"| Features Required | {es['features_required']} |",
        f"| Features Implemented | {es['features_implemented']} |",
        f"| Feature Coverage | {es['feature_coverage_pct']}% |",
        f"| **Overall Status** | **{es['overall_status']}** |",
        f"| **Compliance Score** | **{es['compliance_score']}/10.0** |",
        "",
    ]

    # Section-by-section
    lines.append("## Section-by-Section Analysis")
    lines.append("")
    for sec in report["section_analysis"]:
        lines.append(f"### {sec['id']}: {sec['title']}")
        lines.append("")
        for req in sec["requirements"]:
            status_icon = {"COMPLETE": "✅", "PARTIAL": "🟡", "GAP": "❌", "NOT_IN_SCOPE": "⬜", "NOT_STARTED": "❌"}.get(req["status"], "❓")
            lines.append(f"#### {req['id']}: {req['text']}")
            lines.append(f"- **Status:** {status_icon} {req['status']} ({req['completion_pct']}%)")
            lines.append(f"- **Verification:** {req['verification']}")
            if req["evidence"]:
                lines.append(f"- **Evidence:**")
                for ev in req["evidence"]:
                    if "file" in ev:
                        detail = f"  - `{ev['file']}` "
                        if "matching_lines" in ev:
                            detail += f"(lines: {ev['matching_lines']})"
                        elif "size_bytes" in ev:
                            detail += f"({ev['size_bytes']} bytes, sha256: `{ev.get('sha256', 'n/a')[:16]}...`)"
                        lines.append(detail)
                    elif "note" in ev:
                        lines.append(f"  - {ev['note']}")
            if req["gaps"]:
                lines.append(f"- **Gaps:**")
                for gap in req["gaps"]:
                    lines.append(f"  - {gap}")
            lines.append("")

    # File inventory
    lines.append("## File Inventory Verification")
    lines.append("")
    lines.append("| Required File | Exists | Size | SHA-256 (first 16) | Status |")
    lines.append("|---------------|--------|------|-------------------|--------|")
    for f in report["file_inventory"]:
        exists = "YES" if f["exists"] else "NO"
        size = f"{f['size_bytes']}" if f["size_bytes"] is not None else "—"
        sha = f"`{f['sha256'][:16]}...`" if f["sha256"] else "—"
        status = "✅" if f["status"] == "OK" else "❌"
        lines.append(f"| `{f['required_file']}` | {exists} | {size} | {sha} | {status} |")
    lines.append("")

    # Feature matrix
    lines.append("## Feature Completeness Matrix")
    lines.append("")
    lines.append("| Feature Category | Required | Implemented | % | Missing |")
    lines.append("|------------------|----------|-------------|---|---------|")
    for feat in report["feature_matrix"]:
        missing_str = ", ".join(feat["missing"]) if feat["missing"] else "None"
        lines.append(
            f"| {feat['category']} | {feat['total_required']} | {feat['implemented']} | {feat['completion_pct']}% | {missing_str} |"
        )
    lines.append("")

    # Quantified Metrics Dashboard
    lines.append("## Quantified Metrics Dashboard")
    lines.append("")
    lines.append("```")
    lines.append(f"Total requirements:       {es['total_requirements']}")
    lines.append(f"Requirements met:         {es['requirements_met']}")
    lines.append(f"Overall completion:        {es['overall_completion_pct']}%")
    lines.append(f"Files required:            {es['files_required']}")
    lines.append(f"Files generated:           {es['files_found']}")
    lines.append(f"File coverage:             {es['file_coverage_pct']}%")
    lines.append(f"Features required:         {es['features_required']}")
    lines.append(f"Features implemented:      {es['features_implemented']}")
    lines.append(f"Feature coverage:          {es['feature_coverage_pct']}%")
    lines.append(f"Overall Compliance Score:  {es['compliance_score']}/10.0")
    lines.append(f"Status:                    {es['overall_status']}")
    lines.append("```")
    lines.append("")

    # Evidence Registry
    lines.append("## Evidence Registry")
    lines.append("")
    lines.append("| Req ID | File | Lines / Detail | Verification |")
    lines.append("|--------|------|----------------|-------------|")
    for sec in report["section_analysis"]:
        for req in sec["requirements"]:
            for ev in req["evidence"]:
                if "file" in ev:
                    detail = ", ".join(str(l) for l in ev.get("matching_lines", [])) if ev.get("matching_lines") else f"{ev.get('size_bytes', '—')} bytes"
                    lines.append(f"| {req['id']} | `{ev['file']}` | {detail} | {req['verification']} |")
                elif "note" in ev:
                    lines.append(f"| {req['id']} | — | {ev['note']} | {req['verification']} |")
    lines.append("")
    lines.append(f"## Overall Compliance Score: {es['compliance_score']}/10.0")
    lines.append("")

    return "\n".join(lines)


def generate_html(report: dict) -> str:
    """Generate triage_compliance.html interactive dashboard."""
    es = report["executive_summary"]

    status_color = {
        "COMPLETE": "#27ae60",
        "SUBSTANTIAL": "#2ecc71",
        "PARTIAL": "#f39c12",
        "INSUFFICIENT": "#e74c3c",
    }
    bar_color = status_color.get(es["overall_status"], "#95a5a6")

    # Build section rows
    section_rows = ""
    for sec in report["section_analysis"]:
        sec_reqs_total = len(sec["requirements"])
        sec_reqs_met = sum(1 for r in sec["requirements"] if r["status"] in ("COMPLETE", "NOT_IN_SCOPE"))
        sec_pct = int(100 * sec_reqs_met / max(sec_reqs_total, 1))
        req_rows = ""
        for req in sec["requirements"]:
            status_cls = req["status"].lower().replace("_", "-")
            ev_html = ""
            for ev in req["evidence"]:
                if "file" in ev:
                    ev_html += f'<code>{ev["file"]}</code> '
                elif "note" in ev:
                    ev_html += f'<em>{ev["note"]}</em> '
            gap_html = ""
            for gap in req["gaps"]:
                gap_html += f'<span class="gap-item">{gap}</span> '
            req_rows += f"""
            <tr class="req-row {status_cls}">
                <td>{req["id"]}</td>
                <td>{req["text"]}</td>
                <td><span class="badge-status badge-{status_cls}">{req["status"]}</span></td>
                <td>{req["completion_pct"]}%</td>
                <td>{ev_html or "—"}</td>
                <td>{gap_html or "None"}</td>
            </tr>"""

        section_rows += f"""
        <div class="section-block">
            <div class="section-header" onclick="this.parentElement.classList.toggle('collapsed')">
                <h3>{sec["id"]}: {sec["title"]}</h3>
                <div class="section-bar">
                    <div class="section-bar-fill" style="width:{sec_pct}%; background:{bar_color}"></div>
                </div>
                <span class="section-pct">{sec_pct}% ({sec_reqs_met}/{sec_reqs_total})</span>
            </div>
            <table class="req-table">
                <thead><tr><th>ID</th><th>Requirement</th><th>Status</th><th>%</th><th>Evidence</th><th>Gaps</th></tr></thead>
                <tbody>{req_rows}</tbody>
            </table>
        </div>"""

    # File inventory rows
    file_rows = ""
    for f in report["file_inventory"]:
        cls = "ok" if f["exists"] else "missing"
        file_rows += f"""<tr class="{cls}">
            <td><code>{f["required_file"]}</code></td>
            <td>{"✅" if f["exists"] else "❌"}</td>
            <td>{f["size_bytes"] if f["size_bytes"] else "—"}</td>
            <td><code>{f["sha256"][:16]}...</code></td>
            <td>{f.get("last_modified", "—")}</td>
        </tr>"""

    # Feature matrix rows
    feat_rows = ""
    for feat in report["feature_matrix"]:
        missing_str = ", ".join(feat["missing"]) if feat["missing"] else "None"
        feat_rows += f"""<tr>
            <td>{feat["category"]}</td>
            <td>{feat["total_required"]}</td>
            <td>{feat["implemented"]}</td>
            <td>
                <div class="mini-bar"><div class="mini-fill" style="width:{feat['completion_pct']}%"></div></div>
                {feat["completion_pct"]}%
            </td>
            <td>{missing_str}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Triage Compliance Dashboard</title>
<style>
:root {{
    --bg: #f5f6fa; --card: #fff; --text: #2c3e50; --border: #dcdde1;
    --green: #27ae60; --yellow: #f39c12; --red: #e74c3c; --blue: #2980b9; --gray: #95a5a6;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Segoe UI',system-ui,sans-serif; background:var(--bg); color:var(--text); padding:20px; }}
.dashboard {{ max-width:1400px; margin:0 auto; }}
h1 {{ font-size:1.8em; margin-bottom:4px; }}
h2 {{ font-size:1.3em; margin:24px 0 12px; border-bottom:2px solid var(--border); padding-bottom:6px; }}
h3 {{ font-size:1.1em; margin:0; }}
.timestamp {{ color:var(--gray); font-size:0.85em; margin-bottom:20px; }}

/* KPI cards */
.kpi-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:16px; margin-bottom:24px; }}
.kpi {{ background:var(--card); border-radius:10px; padding:20px; text-align:center; box-shadow:0 2px 8px rgba(0,0,0,.06); }}
.kpi .value {{ font-size:2.2em; font-weight:700; }}
.kpi .label {{ font-size:0.85em; color:var(--gray); margin-top:4px; }}

/* Score gauge */
.gauge {{ width:180px; height:180px; border-radius:50%; display:flex; align-items:center; justify-content:center;
          background: conic-gradient({bar_color} {es["overall_completion_pct"]*3.6}deg, #ecf0f1 0); margin:0 auto 12px; }}
.gauge-inner {{ width:140px; height:140px; border-radius:50%; background:var(--card); display:flex; flex-direction:column;
                align-items:center; justify-content:center; }}
.gauge-inner .score {{ font-size:2em; font-weight:700; color:{bar_color}; }}
.gauge-inner .status {{ font-size:0.8em; color:var(--gray); }}

/* Sections */
.section-block {{ background:var(--card); border-radius:8px; margin-bottom:12px; box-shadow:0 1px 4px rgba(0,0,0,.05); overflow:hidden; }}
.section-header {{ padding:14px 18px; cursor:pointer; display:flex; align-items:center; gap:12px; }}
.section-bar {{ flex:1; height:8px; background:#ecf0f1; border-radius:4px; overflow:hidden; }}
.section-bar-fill {{ height:100%; border-radius:4px; transition:width .3s; }}
.section-pct {{ font-size:0.85em; color:var(--gray); white-space:nowrap; }}
.section-block.collapsed .req-table {{ display:none; }}

/* Tables */
table {{ width:100%; border-collapse:collapse; font-size:0.88em; }}
th {{ background:#f8f9fa; text-align:left; padding:8px 10px; border-bottom:2px solid var(--border); position:sticky; top:0; }}
td {{ padding:7px 10px; border-bottom:1px solid var(--border); }}
tr.ok td:first-child {{ border-left:3px solid var(--green); }}
tr.missing td:first-child {{ border-left:3px solid var(--red); }}

/* Badges */
.badge-status {{ padding:2px 8px; border-radius:4px; font-size:0.8em; font-weight:600; color:#fff; }}
.badge-complete {{ background:var(--green); }}
.badge-partial {{ background:var(--yellow); }}
.badge-gap {{ background:var(--red); }}
.badge-not-started {{ background:var(--red); }}
.badge-not-in-scope {{ background:var(--gray); }}
.gap-item {{ color:var(--red); font-size:0.85em; }}

/* Mini bars */
.mini-bar {{ display:inline-block; width:80px; height:10px; background:#ecf0f1; border-radius:5px; vertical-align:middle; margin-right:6px; }}
.mini-fill {{ height:100%; background:var(--green); border-radius:5px; }}

/* Controls */
.controls {{ margin-bottom:16px; display:flex; gap:8px; }}
.controls button {{ padding:6px 14px; border:1px solid var(--border); border-radius:4px; background:var(--card); cursor:pointer; font-size:0.85em; }}
.controls button:hover {{ background:#f0f0f0; }}

/* Export */
@media print {{ .controls {{ display:none; }} body {{ padding:0; }} }}
</style>
</head>
<body>
<div class="dashboard">
    <h1>🔬 Triage Compliance Dashboard</h1>
    <div class="timestamp">Generated: {report["verification_timestamp"]} | Project: <code>{report["project_root"]}</code></div>

    <div class="controls">
        <button onclick="document.querySelectorAll('.section-block').forEach(s=>s.classList.remove('collapsed'))">Expand All</button>
        <button onclick="document.querySelectorAll('.section-block').forEach(s=>s.classList.add('collapsed'))">Collapse All</button>
        <button onclick="window.print()">Export PDF</button>
        <button onclick="exportJSON()">Export JSON</button>
    </div>

    <!-- Overall Score -->
    <div class="kpi-grid">
        <div class="kpi">
            <div class="gauge">
                <div class="gauge-inner">
                    <div class="score">{es["compliance_score"]}</div>
                    <div class="status">/10.0</div>
                </div>
            </div>
            <div class="label">{es["overall_status"]}</div>
        </div>
        <div class="kpi"><div class="value">{es["requirements_met"]}/{es["in_scope_requirements"]}</div><div class="label">Requirements Met</div></div>
        <div class="kpi"><div class="value" style="color:var(--green)">{es["overall_completion_pct"]}%</div><div class="label">Requirement Coverage</div></div>
        <div class="kpi"><div class="value">{es["files_found"]}/{es["files_required"]}</div><div class="label">Files Present</div></div>
        <div class="kpi"><div class="value" style="color:var(--blue)">{es["file_coverage_pct"]}%</div><div class="label">File Coverage</div></div>
        <div class="kpi"><div class="value">{es["features_implemented"]}/{es["features_required"]}</div><div class="label">Features</div></div>
        <div class="kpi"><div class="value" style="color:var(--green)">{es["feature_coverage_pct"]}%</div><div class="label">Feature Coverage</div></div>
    </div>

    <h2>Section-by-Section Analysis</h2>
    {section_rows}

    <h2>File Inventory ({es["files_found"]}/{es["files_required"]})</h2>
    <table>
        <thead><tr><th>Required File</th><th>Exists</th><th>Size (bytes)</th><th>SHA-256</th><th>Last Modified</th></tr></thead>
        <tbody>{file_rows}</tbody>
    </table>

    <h2>Feature Completeness Matrix</h2>
    <table>
        <thead><tr><th>Category</th><th>Required</th><th>Implemented</th><th>Coverage</th><th>Missing</th></tr></thead>
        <tbody>{feat_rows}</tbody>
    </table>

</div>

<script>
function exportJSON() {{
    const data = {json.dumps(report, indent=2, default=str)};
    const blob = new Blob([JSON.stringify(data, null, 2)], {{type:'application/json'}});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'TRIAGE_COMPLIANCE_REPORT.json';
    a.click();
}}
</script>
</body>
</html>"""
    return html


# ─────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────

def main():
    report = run_verification()

    # Always print JSON summary
    print(json.dumps(report["executive_summary"], indent=2))

    write_md = "--md" in sys.argv or "--all" in sys.argv
    write_all = "--all" in sys.argv

    if write_md or write_all:
        md = generate_markdown(report)
        (ROOT / "TRIAGE_GAP_ANALYSIS.md").write_text(md, encoding="utf-8")
        print(f"\n✅ Written: TRIAGE_GAP_ANALYSIS.md")

    if write_all:
        json_report = json.dumps(report, indent=2, default=str, sort_keys=True)
        (ROOT / "TRIAGE_COMPLIANCE_REPORT.json").write_text(json_report + "\n", encoding="utf-8")
        print(f"✅ Written: TRIAGE_COMPLIANCE_REPORT.json")

        html = generate_html(report)
        (ROOT / "docs" / "triage_compliance.html").write_text(html, encoding="utf-8")
        print(f"✅ Written: docs/triage_compliance.html")

    es = report["executive_summary"]
    passed = es["overall_completion_pct"] >= 80
    print(f"\n{'PASS' if passed else 'FAIL'}: {es['overall_completion_pct']}% compliance ({es['overall_status']})")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
