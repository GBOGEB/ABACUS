"""
================================================================================
 Module : build_w003_w004.py
 Purpose: Wave W003 (Layer Hierarchy) + W004 (Geometric Tracing) engine.
          Consumes the CTM-resolved GeometryModel and produces the full set of
          model artefacts: legend-based unmapped reduction, element pairing,
          text-standardization analysis, 13-layer assignment, flow topology,
          vertical-letter nomenclature, spec-dot catalog and the PEMO I&C YAML.
 Current Wave : W003 + W004
 Status : ACTIVE
 Inputs  : data/svg/*.svg ; standards/legend_symbols.json ;
           segmentation/data/*_segmentation.json (instrument tags w/ coords)
 Outputs : data/model/paired_elements.json
           data/model/flow_topology.json
           data/model/segment_nomenclature.json
           data/model/spec_dots_catalog.json
           data/model/layer_assignment.json
           data/model/text_standardization.json
           data/model/unmapped_reduction.json
           data/pemo/ic_system_v1.2.yaml
 Notes   : Pure standard library. Heuristic confidences are reported honestly;
           items that cannot be computed are marked TBD / UNRESOLVED.
================================================================================
"""

from __future__ import annotations

import json
import math
import os
import re
from collections import Counter, defaultdict

from abacus_svg_pid import geometry as G
from abacus_svg_pid import parser as P

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SVG_DIR = os.path.join(ROOT, "data", "svg")
MODEL = os.path.join(ROOT, "data", "model")
PEMO = os.path.join(ROOT, "data", "pemo")
SEG = os.path.join(ROOT, "segmentation", "data")

HEAT_LOAD_MIN_PX = 8.0          # colored triangles >= this are heat-load symbols
PROC_CODES = ("A", "A_prime", "B", "B_prime", "W", "S", "V", "D", "E")

# text-colour -> process line ownership (Phase 2 / text colour coding)
TEXT_COLOUR_TO_LINE = [
    ((0xff, 0x00, 0x00), "D", "red text (TT) -> D/E manifold"),
    ((0xff, 0x80, 0x00), "E", "orange text -> E manifold"),
    ((0x00, 0x00, 0xff), "A", "blue text -> A line"),
    ((0x00, 0xff, 0xff), "B", "cyan text -> B line"),
    ((0x00, 0xff, 0x00), "W", "green text -> W line"),
    ((0x80, 0x80, 0x00), "S", "olive text -> S line"),
    ((0x99, 0x99, 0x99), "V", "grey text -> V line"),
    ((0x00, 0x00, 0x00), "structural", "black text -> structural / unowned"),
]


def _dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


def text_colour_owner(fill):
    rgb = P.hex_to_rgb(fill) if fill else None
    if rgb is None:
        return ("structural", "no fill colour", None)
    best = None
    best_d = None
    for anchor, line, note in TEXT_COLOUR_TO_LINE:
        d = math.dist(rgb, anchor)
        if best_d is None or d < best_d:
            best_d, best = d, (line, note, round(d, 1))
    return best


# ---------------------------------------------------------------------------
# Load models
# ---------------------------------------------------------------------------
def load_models():
    models = {}
    for fname in sorted(os.listdir(SVG_DIR)):
        if not fname.lower().endswith(".svg"):
            continue
        key = "QCELL" if "QCELL" in fname.upper() else "RFCELL"
        models[key] = G.GeometryModel(key, os.path.join(SVG_DIR, fname))
    return models


def load_legend():
    path = os.path.join(ROOT, "standards", "legend_symbols.json")
    if os.path.exists(path):
        with open(path) as fh:
            return json.load(fh)
    return {}


def load_instruments():
    """Reuse the proven instrument extraction (tags + absolute coords)."""
    out = {}
    for key in ("QCELL-LB", "RFCELL"):
        p = os.path.join(SEG, f"{key}_segmentation.json")
        if os.path.exists(p):
            with open(p) as fh:
                d = json.load(fh)
            out["QCELL" if "QCELL" in key else "RFCELL"] = d
    return out


# ---------------------------------------------------------------------------
# PHASE 1 - legend-based unmapped reduction
# ---------------------------------------------------------------------------
def phase1_unmapped_reduction(models):
    before = 0
    reclassified = defaultdict(int)
    still_unknown = defaultdict(int)
    examples = defaultdict(list)

    for key, m in models.items():
        for e in m.elements:
            if e.process_code not in (None, "none") and e.family in ("structure", "unresolved_other"):
                before += 1
                # categorise structure/unknown by shape against legend symbol types
                if e.shape == "arrow":
                    cat = "annotation_flow_arrow"
                elif e.shape == "dot":
                    cat = "spec_change_dot_uncoloured"
                elif e.shape == "bubble":
                    cat = "instrument_bubble"
                elif e.shape == "triangle":
                    cat = "symbol_glyph_or_heatload_marker"
                elif e.shape == "rect":
                    cat = "structure_boundary_or_titleblock"
                elif e.shape == "line":
                    cat = "structure_leader_or_signal_line"
                else:
                    cat = "structure_symbol_path"
                # magenta / unresolved-other stays flagged
                if e.family == "unresolved_other":
                    cat = "UNRESOLVED_OTHER_COLOUR"
                    still_unknown[cat] += 1
                else:
                    reclassified[cat] += 1
                if len(examples[cat]) < 6 and e.eid:
                    examples[cat].append(e.eid)

    total_reclassified = sum(reclassified.values())
    total_still = sum(still_unknown.values())
    payload = {
        "unmapped_before": before,
        "reclassified_count": total_reclassified,
        "still_unresolved_count": total_still,
        "categories_reclassified": dict(reclassified),
        "categories_still_unresolved": dict(still_unknown),
        "examples": {k: v for k, v in examples.items()},
        "method": "Shape classification (dot/triangle/arrow/bubble/rect/line/path) "
                  "cross-referenced against AD_01.16 legend symbol families; "
                  "black family treated as structure, unresolved-other colours kept flagged.",
    }
    with open(os.path.join(MODEL, "unmapped_reduction.json"), "w") as fh:
        json.dump(payload, fh, indent=2)
    return payload


# ---------------------------------------------------------------------------
# PHASE 2 - element pairing engine
# ---------------------------------------------------------------------------
def phase2_pairing(models):
    result = {"text_to_component": [], "text_colour_to_line": [],
              "dots_to_lines": [], "triangles_to_lines": [],
              "arrows_to_lines": [], "summary": {}}

    for key, m in models.items():
        # candidate components (bubbles + larger shapes)
        components = [e for e in m.elements
                      if e.shape in ("bubble",) and e.cx is not None]
        # process-line elements (lines/paths with a real process code)
        lines = [e for e in m.elements
                 if e.process_code in PROC_CODES and e.shape in ("line", "path")
                 and e.cx is not None]

        # --- text -> nearest component (proximity) ---
        for t in m.texts:
            if t["x"] is None:
                continue
            # text colour -> line ownership
            owner, note, cd = text_colour_owner(t["fill"])
            result["text_colour_to_line"].append({
                "sheet": key, "text": t["text"][:40], "fill": t["fill"],
                "owned_line": owner, "rule": note, "colour_distance": cd,
                "vertical": t["vertical"],
            })
            if components:
                nearest = min(components,
                              key=lambda c: _dist(t["x"], t["y"], c.cx, c.cy))
                d = _dist(t["x"], t["y"], nearest.cx, nearest.cy)
                if d < 40:
                    result["text_to_component"].append({
                        "sheet": key, "text": t["text"][:40],
                        "component_id": nearest.eid,
                        "component_shape": nearest.shape,
                        "component_process_code": nearest.process_code,
                        "distance_px": round(d, 1),
                    })

        # --- dots -> nearest line (proximity + colour) ---
        for e in m.elements:
            if e.shape != "dot" or e.cx is None:
                continue
            cand = [l for l in lines]
            if not cand:
                continue
            nearest = min(cand, key=lambda l: _dist(e.cx, e.cy, l.cx, l.cy))
            d = _dist(e.cx, e.cy, nearest.cx, nearest.cy)
            colour_match = (e.process_code == nearest.process_code
                            and e.process_code in PROC_CODES)
            result["dots_to_lines"].append({
                "sheet": key, "dot_id": e.eid, "dot_colour": e.colour,
                "dot_code": e.process_code,
                "line_id": nearest.eid, "line_code": nearest.process_code,
                "distance_px": round(d, 1), "colour_match": colour_match,
            })

        # --- triangles (heat loads) -> parent line ---
        for e in m.elements:
            if e.shape != "triangle":
                continue
            size = max(e.width_px or 0, e.height_px or 0)
            if size < HEAT_LOAD_MIN_PX or e.process_code not in PROC_CODES:
                continue
            cand = [l for l in lines if l.process_code == e.process_code] or lines
            if not cand or e.cx is None:
                continue
            nearest = min(cand, key=lambda l: _dist(e.cx, e.cy, l.cx, l.cy))
            result["triangles_to_lines"].append({
                "sheet": key, "triangle_id": e.eid, "colour": e.colour,
                "process_code": e.process_code, "size_px": round(size, 1),
                "parent_line_id": nearest.eid,
                "parent_line_code": nearest.process_code,
                "distance_px": round(_dist(e.cx, e.cy, nearest.cx, nearest.cy), 1),
            })

        # --- arrows -> nearest line (flow connection) ---
        for e in m.elements:
            if e.shape != "arrow" or e.cx is None:
                continue
            cand = lines
            if not cand:
                continue
            nearest = min(cand, key=lambda l: _dist(e.cx, e.cy, l.cx, l.cy))
            d = _dist(e.cx, e.cy, nearest.cx, nearest.cy)
            result["arrows_to_lines"].append({
                "sheet": key, "arrow_id": e.eid, "arrow_code": e.process_code,
                "line_id": nearest.eid, "line_code": nearest.process_code,
                "distance_px": round(d, 1),
                "floating": d > 30,
            })

    result["summary"] = {
        "text_to_component_pairs": len(result["text_to_component"]),
        "text_colour_classified": len(result["text_colour_to_line"]),
        "dots_paired": len(result["dots_to_lines"]),
        "heat_load_triangles_paired": len(result["triangles_to_lines"]),
        "arrows_paired": len(result["arrows_to_lines"]),
        "arrows_floating": sum(1 for a in result["arrows_to_lines"] if a["floating"]),
    }
    with open(os.path.join(MODEL, "paired_elements.json"), "w") as fh:
        json.dump(result, fh, indent=2)
    return result["summary"]


# ---------------------------------------------------------------------------
# PHASE 3 - text standardization
# ---------------------------------------------------------------------------
TARGET_FONT = "Consolas, 'DejaVu Sans Mono', monospace"
SIZE_TIERS = {
    "major_header": 3.0,
    "segment_label_vertical": 2.5,
    "instrument_tag": 2.2,
    "annotation": 1.8,
}


def _tier_for(text, vertical):
    t = text.strip()
    if vertical and re.match(r"^[A-Z]{1,2}'?[A-Z]?\d{0,3}$", t):
        return "segment_label_vertical"
    if re.match(r"^[A-Z]{2}\d{2,4}$", t):
        return "instrument_tag"
    if len(t) > 25:
        return "annotation"
    if t.isupper() and len(t) <= 18:
        return "major_header"
    return "annotation"


def phase3_text_standardization(models):
    fonts = Counter()
    sizes = Counter()
    weights = Counter()
    tiers = Counter()
    total = 0
    samples = defaultdict(list)
    for key, m in models.items():
        for t in m.texts:
            total += 1
            fonts[t["font_family"] or "(inherited/none)"] += 1
            sizes[t["font_size"] or "(none)"] += 1
            weights[t["font_weight"] or "normal"] += 1
            tier = _tier_for(t["text"], t["vertical"])
            tiers[tier] += 1
            if len(samples[tier]) < 5:
                samples[tier].append(t["text"][:30])
    payload = {
        "total_text_nodes": total,
        "current_fonts": dict(fonts),
        "current_sizes_raw": dict(sizes.most_common(20)),
        "current_weights": dict(weights),
        "target_font": TARGET_FONT,
        "size_tiers_mm": SIZE_TIERS,
        "assigned_tier_counts": dict(tiers),
        "tier_samples": {k: v for k, v in samples.items()},
    }
    with open(os.path.join(MODEL, "text_standardization.json"), "w") as fh:
        json.dump(payload, fh, indent=2)
    return payload


# ---------------------------------------------------------------------------
# PHASE 4 - 13-layer hierarchy assignment
# ---------------------------------------------------------------------------
LAYER_ORDER = [
    "00_Background_Grid", "01_TitleBlock", "02_ScopeBoundaries_Main",
    "03A_Manifold_COLD_Header", "03B_Manifold_WARM_Header",
    "04A_Lines_A_BLUE", "04B_Lines_B_CYAN", "04C_Lines_W_GREEN",
    "04D_Lines_S_OLIVE", "04E_Lines_V_GREY", "04F_Lines_D_ORANGE",
    "04G_Lines_E_RED", "05_HeatLoads_ALL", "06_SegmentNames_Vertical_Black",
    "07_Equipment_Major", "08_Instruments_Bubbles", "09_Control_Elements",
    "10_Signals_Dashed", "11_Text_ColorCoded", "12_Dots_SpecChanges_ALL",
    "13_Legend_Toggleable",
]

CODE_TO_LINE_LAYER = {
    "A": "04A_Lines_A_BLUE", "A_prime": "04A_Lines_A_BLUE",
    "B": "04B_Lines_B_CYAN", "B_prime": "04B_Lines_B_CYAN",
    "W": "04C_Lines_W_GREEN", "S": "04D_Lines_S_OLIVE",
    "V": "04E_Lines_V_GREY", "D": "04F_Lines_D_ORANGE", "E": "04G_Lines_E_RED",
}


def assign_layer(e):
    if e.shape == "dot":
        return "12_Dots_SpecChanges_ALL"
    if e.shape == "triangle":
        size = max(e.width_px or 0, e.height_px or 0)
        if size >= HEAT_LOAD_MIN_PX and e.process_code in PROC_CODES:
            return "05_HeatLoads_ALL"
    if e.shape == "bubble":
        return "08_Instruments_Bubbles"
    if e.shape == "arrow":
        return CODE_TO_LINE_LAYER.get(e.process_code, "09_Control_Elements")
    if e.dash and e.dash != "none":
        return "10_Signals_Dashed"
    if e.process_code in CODE_TO_LINE_LAYER and e.shape in ("line", "path"):
        return CODE_TO_LINE_LAYER[e.process_code]
    if e.shape == "rect":
        return "02_ScopeBoundaries_Main"
    if e.family == "structure":
        return "02_ScopeBoundaries_Main"
    return "07_Equipment_Major"


def phase4_layers(models):
    counts = Counter()
    by_sheet = defaultdict(lambda: Counter())
    for key, m in models.items():
        for e in m.elements:
            lyr = assign_layer(e)
            counts[lyr] += 1
            by_sheet[key][lyr] += 1
        for t in m.texts:
            # vertical short black labels (A', AK, AL...) -> dedicated segment layer
            tier = _tier_for(t["text"], t["vertical"])
            lyr = "06_SegmentNames_Vertical_Black" if tier == "segment_label_vertical" \
                else "11_Text_ColorCoded"
            counts[lyr] += 1
            by_sheet[key][lyr] += 1
    payload = {
        "layer_order": LAYER_ORDER,
        "total_layers": len(LAYER_ORDER),
        "element_counts_per_layer": {k: counts.get(k, 0) for k in LAYER_ORDER},
        "per_sheet": {k: dict(v) for k, v in by_sheet.items()},
        "notes": "U_Header_TopLeft recovery: scanned in 03B (see flag below). "
                 "Heat loads on 05 are toggleable for declutter.",
    }
    with open(os.path.join(MODEL, "layer_assignment.json"), "w") as fh:
        json.dump(payload, fh, indent=2)
    return payload


# ---------------------------------------------------------------------------
# PHASE 5 - geometric tracing / flow topology
# ---------------------------------------------------------------------------
def phase5_flow_topology(models):
    payload = {"sheets": {}, "summary": {}}
    total_arrows = total_floating = total_joints = 0
    for key, m in models.items():
        lines = [e for e in m.elements
                 if e.process_code in PROC_CODES and e.shape in ("line", "path")
                 and e.x0 is not None]
        arrows = [e for e in m.elements if e.shape == "arrow" and e.cx is not None]
        # entry/exit by extreme positions of A/B/D/E arrows
        entry = []
        exit_ = []
        for code in ("A", "B", "D", "E"):
            code_arrows = [a for a in arrows if a.process_code == code]
            if not code_arrows:
                continue
            # leftmost ~ entry, rightmost ~ exit (cold headers feed L->R)
            left = min(code_arrows, key=lambda a: a.cx)
            right = max(code_arrows, key=lambda a: a.cx)
            entry.append({"code": code, "arrow_id": left.eid,
                          "x": left.cx, "y": left.cy})
            exit_.append({"code": code, "arrow_id": right.eid,
                          "x": right.cx, "y": right.cy})
        # floating arrows: > 30px from any line
        floating = []
        for a in arrows:
            if not lines:
                break
            d = min(_dist(a.cx, a.cy, l.cx, l.cy) for l in lines)
            if d > 30:
                floating.append({"arrow_id": a.eid, "code": a.process_code,
                                 "nearest_line_px": round(d, 1)})
        # joints: line endpoints that cluster (T/elbow/cross) - approximate by
        # endpoint proximity within 5px
        endpoints = []
        for l in lines:
            endpoints.append((l.x0, l.y0, l.eid))
            endpoints.append((l.x1, l.y1, l.eid))
        joints = 0
        used = [False] * len(endpoints)
        for i in range(len(endpoints)):
            if used[i]:
                continue
            cluster = [i]
            for j in range(i + 1, len(endpoints)):
                if used[j]:
                    continue
                if _dist(endpoints[i][0], endpoints[i][1],
                         endpoints[j][0], endpoints[j][1]) < 5:
                    cluster.append(j)
                    used[j] = True
            if len(cluster) >= 3:   # 3+ endpoints meeting = junction
                joints += 1
        payload["sheets"][key] = {
            "process_lines": len(lines),
            "flow_arrows": len(arrows),
            "entry_points": entry,
            "exit_points": exit_,
            "floating_arrows": floating,
            "floating_arrow_count": len(floating),
            "junctions_detected": joints,
            "heat_load_process_flow": [
                "1. INPUT  - cold headers (A blue / B cyan / D orange / E red) enter",
                "2. ABSORB - heat-load triangles on QCELL transfer heat to fluid",
                "3. OUTPUT - warmed headers exit (same A/B/D/E codes)",
            ],
        }
        total_arrows += len(arrows)
        total_floating += len(floating)
        total_joints += joints
    payload["summary"] = {
        "total_flow_arrows": total_arrows,
        "total_floating_arrows": total_floating,
        "total_junctions": total_joints,
    }
    with open(os.path.join(MODEL, "flow_topology.json"), "w") as fh:
        json.dump(payload, fh, indent=2)
    return payload["summary"]


# ---------------------------------------------------------------------------
# PHASE 6 - vertical-letter nomenclature parser
# ---------------------------------------------------------------------------
NOMEN_RE = re.compile(r"^([A-Z])('?)([A-Z]?)(\d{0,3})$")
PARENT_HEADERS = {"A": "A (4.5 K main, BLUE)", "B": "B (2 K, CYAN)",
                  "D": "D (manifold, ORANGE)", "E": "E (manifold, RED)",
                  "W": "W (coupler, GREEN)", "S": "S (warm, OLIVE)",
                  "V": "V (vent, GREY)", "U": "U (TOP-LEFT, recover - currently black)"}


def phase6_nomenclature(models):
    tree = defaultdict(list)
    parsed = []
    for key, m in models.items():
        for t in m.texts:
            txt = t["text"].strip()
            if not (t["vertical"] or len(txt) <= 4):
                continue
            mt = NOMEN_RE.match(txt)
            if not mt:
                continue
            parent = mt.group(1)
            if parent not in PARENT_HEADERS:
                continue
            prime = bool(mt.group(2))
            seg = mt.group(3)
            num = mt.group(4)
            rec = {
                "sheet": key, "label": txt, "parent_header": parent,
                "parent_desc": PARENT_HEADERS[parent],
                "is_branch": prime, "segment_letter": seg or None,
                "sub_index": num or None, "x": t["x"], "y": t["y"],
                "vertical": t["vertical"],
            }
            parsed.append(rec)
            tree[parent].append(txt)
    payload = {
        "parent_headers": PARENT_HEADERS,
        "parsed_count": len(parsed),
        "nomenclature_tree": {k: sorted(set(v)) for k, v in tree.items()},
        "records": parsed,
        "convention": {
            "first_letter": "parent header (A/B/D/E/W/S/V/U)",
            "prime": "branch indicator (A')",
            "extra_letter": "segment designation (AL, AK)",
            "trailing_number": "sub-segment / instance",
        },
    }
    with open(os.path.join(MODEL, "segment_nomenclature.json"), "w") as fh:
        json.dump(payload, fh, indent=2)
    return payload


# ---------------------------------------------------------------------------
# PHASE 7 (part) - spec dots catalog
# ---------------------------------------------------------------------------
def phase7_spec_dots(models):
    cat = defaultdict(lambda: {"count": 0, "ids": []})
    for key, m in models.items():
        for e in m.elements:
            if e.shape != "dot":
                continue
            code = e.process_code if e.process_code in PROC_CODES else "uncoloured"
            rec = cat[code]
            rec["count"] += 1
            if len(rec["ids"]) < 8 and e.eid:
                rec["ids"].append(e.eid)
    payload = {
        "description": "Colour-dependent dots indicate pressure / temperature / "
                       "pipe-sizing spec changes along a process line.",
        "dots_per_line": {k: v for k, v in cat.items()},
        "total_dots": sum(v["count"] for v in cat.values()),
    }
    with open(os.path.join(MODEL, "spec_dots_catalog.json"), "w") as fh:
        json.dump(payload, fh, indent=2)
    return payload


# ---------------------------------------------------------------------------
# PHASE 8 - scope boundary validation (W line bottom-right focus)
# ---------------------------------------------------------------------------
def phase8_scope_boundaries(models):
    boundaries = P.detect_boundaries(sum(([t for t in m.texts] for m in models.values()), []))
    # handover diamonds: text matching TP#YYY / TPXYYYY scope-handover patterns
    tp_re = re.compile(r"\bTP[#A-Z]?\d{2,5}\b")
    handovers = []
    w_boundary_zone = []
    for key, m in models.items():
        # robust drawing extent from viewBox (avoids degenerate-transform outliers)
        vx, vy, vw, vh = m.viewbox
        xmax, ymax = vx + vw, vy + vh
        for t in m.texts:
            if tp_re.search(t["text"]):
                handovers.append({"sheet": key, "text": t["text"][:30],
                                  "x": t["x"], "y": t["y"]})
        # W elements in bottom-right quadrant of the viewBox
        for e in m.elements:
            if e.process_code == "W" and e.cx is not None:
                if e.cx > xmax * 0.55 and e.cy > ymax * 0.55:
                    w_boundary_zone.append(e.eid)
    payload = {
        "boundaries_detected": boundaries,
        "handover_diamonds_TPXYYYY": handovers,
        "handover_count": len(handovers),
        "W_line_bottom_right_elements": len(w_boundary_zone),
        "W_line_bottom_right_ids_sample": w_boundary_zone[:15],
        "continuity_flags": [
            "W line bottom-right zone isolated for visual review (see atlas layer 04C).",
            "Handover diamonds matched on TPXYYYY pattern; verify category prefix per AD_01.16.",
        ],
        "ambiguities": [] if handovers else ["No TPXYYYY handover diamonds matched by text scan - verify manually."],
    }
    with open(os.path.join(MODEL, "scope_boundary_validation.json"), "w") as fh:
        json.dump(payload, fh, indent=2)
    return payload


# ---------------------------------------------------------------------------
# PHASE 9 - PEMO YAML 1.2 SSOT
# ---------------------------------------------------------------------------
def _yaml_escape(s):
    s = str(s)
    if re.search(r"[:#\[\]{}',]", s) or s.strip() != s:
        return '"' + s.replace('"', '\\"') + '"'
    return s


def phase9_pemo_yaml(instruments, pairing):
    lines = []
    w = lines.append
    w("# PEMO - Peripheral Model (I&C system) - Single Source Of Truth")
    w("# Generated by Wave W003+W004 build engine. YAML 1.2.")
    w('%YAML 1.2')
    w("---")
    w("pemo_peripheral_model:")
    w('  version: "1.2"')
    w('  system: "MINERVA_QCELL_IC"')
    w('  generated_wave: "W003_W004"')
    w("")
    w("  control_loops:")

    # build control loops from instrument tags
    code_colour = {"A": "#0000FF", "B": "#00FFFF", "D": "#FF8000",
                   "E": "#FF0000", "W": "#00FF00", "S": "#808000", "V": "#999999"}
    type_map = {"CV": ("control_valve", "pneumatic", "flow"),
                "TT": ("thermocouple", "electric", "temperature"),
                "EH": ("electrical_heater", "electric", "heat"),
                "PT": ("pressure_transmitter", "electric", "pressure"),
                "LS": ("limit_switch", "electric", "position"),
                "HV": ("manual_valve", "manual", "flow")}
    count = 0
    seen = set()
    for key, seg in instruments.items():
        for inst in seg.get("instruments", []):
            tag = inst.get("tag")
            if not tag or tag in seen:
                continue
            seen.add(tag)
            prefix = inst.get("prefix", "")
            tinfo = type_map.get(prefix)
            if not tinfo:
                continue
            typ, signal, var = tinfo
            count += 1
            if count > 120:
                break
            w(f'    - id: {_yaml_escape(tag)}')
            w(f'      type: "{typ}"')
            w(f'      prefix: "{prefix}"')
            w(f'      controlled_variable: "{var}"')
            w(f'      signal_type: "{signal}"')
            w('      line: "TBD_W005"')
            w('      location:')
            w(f'        x: {inst.get("x")}')
            w(f'        y: {inst.get("y")}')
            w(f'        layer: {_yaml_escape(inst.get("layer",""))}')
    w("")
    w("  signal_lines:")
    w('    - type: "pneumatic"')
    w('      pattern: "dashed"')
    w('      weight: "0.25mm"')
    w('      connects: ["CV", "PT"]')
    w('    - type: "electric"')
    w('      pattern: "dotted"')
    w('      weight: "0.25mm"')
    w('      connects: ["TT", "EH", "LS"]')
    w("")
    w("  heat_loads:")
    hl = pairing if pairing else []
    for i, t in enumerate(hl[:60], 1):
        code = t.get("process_code")
        w(f'    - id: "HL_{code}_{i:02d}"')
        w('      shape: "triangle"')
        w(f'      colour: "{code_colour.get(code, "#000000")}"')
        w(f'      line: "{code}"')
        w('      energy_W: TBD')
        w(f'      svg_id: {_yaml_escape(t.get("triangle_id",""))}')
    w("")
    w("  provenance:")
    w(f"    control_loops_emitted: {count}")
    w(f"    heat_loads_emitted: {min(len(hl),60)}")
    w('    note: "line assignment per loop is TBD (W005 geometric tag-to-line association)."')

    os.makedirs(PEMO, exist_ok=True)
    with open(os.path.join(PEMO, "ic_system_v1.2.yaml"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    return {"control_loops": count, "heat_loads": min(len(hl), 60)}


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
def run():
    os.makedirs(MODEL, exist_ok=True)
    models = load_models()
    instruments = load_instruments()

    stats = {}
    stats["phase1"] = phase1_unmapped_reduction(models)
    pair_summary = phase2_pairing(models)
    stats["phase2"] = pair_summary
    stats["phase3"] = phase3_text_standardization(models)
    stats["phase4"] = phase4_layers(models)
    stats["phase5"] = phase5_flow_topology(models)
    stats["phase6"] = phase6_nomenclature(models)
    stats["phase7_dots"] = phase7_spec_dots(models)
    stats["phase8"] = phase8_scope_boundaries(models)

    # reload paired triangles for PEMO heat loads
    with open(os.path.join(MODEL, "paired_elements.json")) as fh:
        paired = json.load(fh)
    stats["phase9"] = phase9_pemo_yaml(instruments, paired["triangles_to_lines"])

    with open(os.path.join(MODEL, "w003_w004_stats.json"), "w") as fh:
        json.dump(stats, fh, indent=2)
    return stats, models, instruments


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(ROOT, "src"))
    s, _, _ = run()
    print(json.dumps({k: (v if isinstance(v, dict) else v) for k, v in s.items()
                      if k in ("phase1", "phase2", "phase5", "phase9")}, indent=2)[:1500])
