"""
================================================================================
 Module : cli.py
 Purpose: Command-line entry point for the colour-line-first P&ID pipeline.
          Loads the real QCELL/RFCELL SVGs, runs colour extraction +
          clustering, writes the colour inventory + line model + per-colour
          files, and prints a runtime banner with the wave status and the
          five mandatory success-criteria numbers.
 Current Wave : W002 - Colour Line Decomposition & Validation
 Status : ACTIVE
 Inputs  : data/svg/*.svg
 Outputs : data/model/colour_inventory.json
           data/model/line_model.json
           data/model/lines/*.json
 Notes   : Pure standard library. W003 (layer engine) and W004 (geometry /
           arrow tracing / sequential ordering) are intentionally NOT run.
================================================================================
"""

from __future__ import annotations

import json
import os
import sys

# allow running both as module and as script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from abacus_svg_pid import parser as P

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SVG_DIR = os.path.join(PROJECT_ROOT, "data", "svg")
PDF_DIR = os.path.join(PROJECT_ROOT, "data", "pdf")
MODEL_DIR = os.path.join(PROJECT_ROOT, "data", "model")
LINES_DIR = os.path.join(MODEL_DIR, "lines")


def _banner(svg_files, blocking):
    bar = "=" * 78
    print(bar)
    print(" MINERVA QCELL P&ID  |  COLOUR-LINE-FIRST PIPELINE")
    print(bar)
    print(" Current Wave : W002 - Colour Line Decomposition & Validation")
    print(" Status       : ACTIVE")
    print(" Inputs found : {} SVG file(s) in data/svg/".format(len(svg_files)))
    for f in svg_files:
        print("                - {}".format(f))
    pdfs = os.listdir(PDF_DIR) if os.path.isdir(PDF_DIR) else []
    print("                - {} PDF reference(s) in data/pdf/".format(len(pdfs)))
    print(" Deferred     : W003 layer engine, W004 geometry/arrow tracing")
    if blocking:
        print(" BLOCKING     :")
        for b in blocking:
            print("                ! {}".format(b))
    else:
        print(" BLOCKING     : none")
    print(bar)


def run():
    svg_files = sorted(f for f in os.listdir(SVG_DIR)
                       if f.lower().endswith(".svg")) if os.path.isdir(SVG_DIR) else []

    blocking = []
    if len(svg_files) < 2:
        blocking.append("Fewer than 2 SVG files in data/svg/ - STOP gate.")

    _banner(svg_files, blocking)

    if len(svg_files) < 2:
        print("\nABORT: STOP gate not satisfied (need >= 2 SVG files).")
        return 1

    os.makedirs(LINES_DIR, exist_ok=True)

    all_elements = []
    per_file_text_counts = {}
    per_file_element_counts = {}
    all_texts = []

    for fname in svg_files:
        path = os.path.join(SVG_DIR, fname)
        elements, texts = P.extract_elements(path)
        all_elements.extend(elements)
        all_texts.extend(texts)
        per_file_text_counts[fname] = len(texts)
        per_file_element_counts[fname] = len(elements)

    # --- colour inventory ---
    inventory = P.build_colour_inventory(all_elements)
    with open(os.path.join(MODEL_DIR, "colour_inventory.json"), "w") as fh:
        json.dump({"unique_pairs": len(inventory), "inventory": inventory},
                  fh, indent=2)

    # --- line model ---
    line_records = P.build_line_model(all_elements, all_texts,
                                      per_file_element_counts)
    with open(os.path.join(MODEL_DIR, "line_model.json"), "w") as fh:
        json.dump({"line_count": len(line_records), "lines": line_records},
                  fh, indent=2)

    # --- per-colour files ---
    written = P.write_per_colour_files(line_records, LINES_DIR)

    # --- boundaries ---
    boundaries = P.detect_boundaries(all_texts)

    # --- success-criteria numbers ---
    unique_strokes = {el["stroke"] for el in all_elements
                      if el["stroke"] and el["stroke"].startswith("#")}
    paths_per_code = {}
    for rec in line_records:
        paths_per_code[rec["process_code"]] = rec["element_count"]

    # distinct hex colours that fall in the "unresolved_other" family
    # (truly outside the canonical mapping, e.g. magenta) vs the black
    # structure family which is expected/known.
    unmapped_hexes = {}
    structure_hexes = {}
    for el in all_elements:
        eff = el["effective_colour"]
        if not eff:
            continue
        cls = P.classify_colour(eff)
        if cls.get("family") == "unresolved_other":
            unmapped_hexes[eff] = unmapped_hexes.get(eff, 0) + 1
        elif cls.get("family") == "structure":
            structure_hexes[eff] = structure_hexes.get(eff, 0) + 1
    unmapped = sorted(unmapped_hexes.keys())

    summary = {
        "svg_files_loaded": len(svg_files),
        "svg_file_names": svg_files,
        "unique_stroke_colours": len(unique_strokes),
        "path_elements_per_process_code": paths_per_code,
        "text_nodes_per_file": per_file_text_counts,
        "colours_unmapped": unmapped,
        "colours_unmapped_counts": unmapped_hexes,
        "structure_black_family_counts": structure_hexes,
        "boundaries_detected": boundaries,
        "colour_inventory_pairs": len(inventory),
        "line_records": len(line_records),
        "per_colour_files": written,
    }
    with open(os.path.join(MODEL_DIR, "run_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)

    # --- navigation.json (wave status + real runtime numbers) ---
    reports_dir = os.path.join(PROJECT_ROOT, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    navigation = {
        "current_wave": "W002",
        "current_wave_name": "Colour Line Decomposition & Validation",
        "next_wave": "W003",
        "next_wave_name": "Layer / Mechanical-Section Engine",
        "status": "active",
        "svg_files_found": svg_files,
        "svg_files_found_count": len(svg_files),
        "unique_stroke_colours": len(unique_strokes),
        "process_codes_detected": sorted(paths_per_code.keys()),
        "colours_unmapped_other": unmapped,
        "blocking_items": blocking if blocking else [],
    }
    with open(os.path.join(reports_dir, "navigation.json"), "w") as fh:
        json.dump(navigation, fh, indent=2)

    # --- print success criteria ---
    print("\nSUCCESS CRITERIA (runtime counts):")
    print("  1. SVG files loaded           : {}".format(summary["svg_files_loaded"]))
    print("  2. Unique stroke colours      : {}".format(summary["unique_stroke_colours"]))
    print("  3. Path elements per code     :")
    for code, n in sorted(paths_per_code.items(), key=lambda kv: -kv[1]):
        print("       {:>10} : {}".format(code, n))
    print("  4. Text nodes per file        :")
    for f, n in per_file_text_counts.items():
        print("       {} : {}".format(f, n))
    print("  5. Colours unmapped (other)   : {}".format(
        ", ".join("{} (x{})".format(h, unmapped_hexes[h]) for h in unmapped)
        if unmapped else "none"))
    print("     black structure family     : {}".format(
        ", ".join(sorted(structure_hexes.keys())) if structure_hexes else "none"))
    print("\nBoundaries detected: {}".format(
        ", ".join(boundaries.keys()) if boundaries else "none via text scan"))
    print("Model written to data/model/  (inventory, line_model, {} line files)".format(len(written)))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
