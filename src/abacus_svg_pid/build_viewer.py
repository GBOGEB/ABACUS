#!/usr/bin/env python3
"""
build_viewer.py  --  Wave W008  *** FULL INTERACTIVE VIEWER ***
================================================================

STATUS: W008 upgrades the W006 scaffold into a full-featured, single-file,
        offline interactive cross-map viewer. No external CDN / npm / bundler
        dependencies -- everything (SVG, data, JS, CSS) is inlined so the file
        works by double-clicking it.

Feature set delivered by W008 (all real, honest -- see honesty notes below):
  * Tag -> SVG element highlighting: every as-drawn tag that appears as text in
    the embedded atlas is annotated at build time with a data-pidtag attribute;
    clicking a table row (or searching) highlights the element(s), draws a
    bounding box and zooms/pans the viewBox to frame it, with a pulse animation.
  * Confidence-based triage workflow: filter by ALL / MAPPED / MEDIUM / LOW /
    UNMAPPED (HIGH is present in the UI but the real W006 data has 0 HIGH pairs);
    per-row Confirm / Reject / Suggest-alt controls persisted to localStorage
    and exportable as a validation JSON.
  * Export controls: cross-map CSV, cross-map JSON (incl. validation states),
    current-view PNG (SVG serialised to canvas, offline), and Print / Save-as-PDF
    via the browser print pipeline (honest -- no bundled PDF engine).
  * Side-by-side comparison: QCELL (cross-mapped) vs RFCELL (visual reference)
    with synchronised zoom/pan. NOTE: the W006 cross-map covers QCELL only, so
    RFCELL is shown for visual comparison, not as a mapped target -- labelled
    as such in the UI.
  * Enhanced search & navigation: dual-tag search (design + as-drawn), type
    filter, jump-to-row, selection breadcrumb.
  * UI/UX polish: loading overlay, missing-data error states, keyboard shortcuts
    (Ctrl+F search, Esc clear, Ctrl+E export, Ctrl+L layers, +/- zoom, 0 reset),
    tooltips.

HONESTY NOTES (project mandate -- no fabricated data):
  * All counts shown in the UI are derived from the real W006 artefacts. The
    authoritative distribution is read from reports/W006_crossmap_statistics.json
    (97 design tags, 141 as-drawn real, 43 mapped = 0 HIGH / 39 MEDIUM / 4 LOW,
    54 unmapped). Row-derived counts are cross-checked against it at build time.
  * PDF export uses the browser's native print -> PDF (labelled honestly); no
    PDF library is bundled because that would require a CDN/npm dependency.
  * RFCELL has no cross-map (QCELL-only in W006); the compare pane is labelled
    "visual reference only".

Inputs : data/crossmap/design_to_asdrawn.json   (from build_w006_crossmap)
         data/crossmap/crossmap_confidence.json  (from build_w006_crossmap)
         reports/W006_crossmap_statistics.json   (authoritative counts)
         data/excel/catalog_register.json        (from build_w005, optional)
         output_v6/QCELL/*_13layers.svg           (from build_atlas_v6)
         output_v6/RFCELL/*_13layers.svg          (from build_atlas_v6, optional)
Output : publish/interactive_viewer.html
"""
from __future__ import annotations

import glob
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CROSSMAP = os.path.join(ROOT, "data", "crossmap", "design_to_asdrawn.json")
CONFIDENCE = os.path.join(ROOT, "data", "crossmap", "crossmap_confidence.json")
STATS_JSON = os.path.join(ROOT, "reports", "W006_crossmap_statistics.json")
CATALOG = os.path.join(ROOT, "data", "excel", "catalog_register.json")
QCELL_DIR = os.path.join(ROOT, "output_v6", "QCELL")
RFCELL_DIR = os.path.join(ROOT, "output_v6", "RFCELL")
PUBLISH = os.path.join(ROOT, "publish")

TIER_COLOUR = {
    "HIGH": "#1b9e77",
    "MEDIUM": "#d9a300",
    "LOW": "#d95f02",
    "UNMAPPED": "#888888",
}


def _load_json(path):
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return json.load(fh)


def _read_svg(directory):
    """Return (svg_text, viewBox) for the first *_13layers.svg in directory."""
    cands = sorted(glob.glob(os.path.join(directory, "*_13layers.svg")))
    if not cands:
        return None, None
    with open(cands[0]) as fh:
        svg = fh.read()
    svg = re.sub(r"<\?xml[^>]*\?>", "", svg).strip()
    vb = re.search(r'viewBox="([^"]+)"', svg)
    return svg, (vb.group(1) if vb else "0 0 1527.2727 1080")


def _annotate_svg(svg, tags):
    """Inject data-pidtag attributes onto tspan/text elements whose text content
    matches one or more known tags. Returns (annotated_svg, set_of_found_tags).

    This is what enables tag -> SVG element highlighting at runtime: no
    coordinate guessing -- we match the human-readable label already drawn in
    the atlas, then let the browser compute the element bbox via getBBox().
    """
    if not svg:
        return svg, set()
    tagset = set(tags)
    found = set()
    pat = re.compile(r'(<(?:tspan|text)\b[^>]*?)(>)([^<]*?)(</(?:tspan|text)>)')

    def repl(m):
        open_tag, gt, content, close = m.groups()
        toks = [t for t in re.split(r"\s+", content.strip()) if t]
        hit = [t for t in toks if t in tagset]
        if hit:
            found.update(hit)
            return f'{open_tag} data-pidtag="{" ".join(hit)}"{gt}{content}{close}'
        return m.group(0)

    return pat.sub(repl, svg), found


def _rows(crossmap):
    """Build the unified row list: mapped pairs + unmapped design tags."""
    mapped = {m["design_tag"]: m for m in crossmap.get("mappings", [])}
    d2a = crossmap.get("design_to_asdrawn", {})
    universe = set(d2a) | set(mapped)
    rows = []
    for m in crossmap.get("mappings", []):
        rows.append({
            "design": m["design_tag"],
            "asdrawn": m["asdrawn_tag"],
            "type": m.get("type", ""),
            "confidence": m.get("confidence", 0.0),
            "tier": m.get("tier", "UNMAPPED"),
            "reasons": m.get("reasons", []),
            "sheet": m.get("asdrawn_sheet", ""),
        })
    conf = _load_json(CONFIDENCE) or {}
    for u in conf.get("unmapped_design", []):
        dtag = u.get("design_tag") if isinstance(u, dict) else u
        if dtag and dtag not in universe:
            reason = (u.get("reason", "NO_CONFIDENT_MATCH")
                      if isinstance(u, dict) else "NO_CONFIDENT_MATCH")
            rows.append({
                "design": dtag, "asdrawn": "",
                "type": (u.get("type") if isinstance(u, dict) else dtag[:2]) or dtag[:2],
                "confidence": 0.0, "tier": "UNMAPPED",
                "reasons": [reason], "sheet": "",
            })
    rows.sort(key=lambda r: (r["tier"] != "HIGH", r["tier"] != "MEDIUM",
                             r["tier"] != "LOW", r["design"]))
    return rows


def _table_html(rows, found_tags):
    out = []
    for i, r in enumerate(rows):
        colour = TIER_COLOUR.get(r["tier"], "#888")
        reasons = html.escape("; ".join(r["reasons"]))
        # locatable = this as-drawn tag is annotated in the embedded SVG
        loc = "yes" if r["asdrawn"] and r["asdrawn"] in found_tags else "no"
        locmark = ("&#128269;" if loc == "yes" else "")  # magnifier glyph
        out.append(
            f'<tr class="row" data-design="{html.escape(r["design"])}" '
            f'data-asdrawn="{html.escape(r["asdrawn"])}" '
            f'data-type="{html.escape(r["type"])}" '
            f'data-tier="{r["tier"]}" data-loc="{loc}" data-i="{i}">'
            f'<td class="c-loc" title="locatable in atlas">{locmark}</td>'
            f'<td class="c-design">{html.escape(r["design"])}</td>'
            f'<td class="c-asdrawn">{html.escape(r["asdrawn"]) or "&mdash;"}</td>'
            f'<td>{html.escape(r["type"])}</td>'
            f'<td><span class="pill" style="background:{colour}">{r["tier"]}</span></td>'
            f'<td>{r["confidence"]:.2f}</td>'
            f'<td class="c-val" data-design="{html.escape(r["design"])}"></td>'
            f'<td class="reasons">{reasons}</td></tr>')
    return "\n".join(out)


def build_html():
    crossmap = _load_json(CROSSMAP)
    if not crossmap:
        raise SystemExit("W006 crossmap not found -- run build_w006_crossmap first.")
    rows = _rows(crossmap)
    asdrawn_tags = [r["asdrawn"] for r in rows if r["asdrawn"]]

    q_svg, q_vb = _read_svg(QCELL_DIR)
    r_svg, r_vb = _read_svg(RFCELL_DIR)
    q_svg, q_found = _annotate_svg(q_svg, asdrawn_tags)
    has_q = q_svg is not None
    has_r = r_svg is not None

    rows_json = json.dumps(rows)
    found_json = json.dumps(sorted(q_found))

    # Authoritative counts from the real W006 statistics artefact.
    auth = _load_json(STATS_JSON) or {}
    # Row-derived cross-check (must agree with the authoritative file).
    derived = {
        "total": len(rows),
        "mapped": sum(1 for r in rows if r["asdrawn"]),
        "high": sum(1 for r in rows if r["tier"] == "HIGH"),
        "medium": sum(1 for r in rows if r["tier"] == "MEDIUM"),
        "low": sum(1 for r in rows if r["tier"] == "LOW"),
        "unmapped": sum(1 for r in rows if not r["asdrawn"]),
    }
    stats = {
        "design_tags": auth.get("total_design_tags", derived["total"]),
        "asdrawn_real": auth.get("total_asdrawn_real_tags", 0),
        "mapped": auth.get("mapped", derived["mapped"]),
        "high": auth.get("high_confidence", derived["high"]),
        "medium": auth.get("medium_confidence", derived["medium"]),
        "low": auth.get("low_confidence", derived["low"]),
        "unmapped": auth.get("unmapped_design", derived["unmapped"]),
        "asdrawn_unclaimed": auth.get("asdrawn_unclaimed", 0),
        "locatable": len([r for r in rows if r["asdrawn"] and r["asdrawn"] in q_found]),
    }

    table_rows = _table_html(rows, q_found)

    # ---- assemble SVG panes -------------------------------------------------
    if has_q:
        q_pane = (f'<div class="pane" id="paneQ"><div class="pane-label">'
                  f'QCELL &mdash; cross-mapped</div>{q_svg}</div>')
    else:
        q_pane = ('<div class="pane empty" id="paneQ">QCELL atlas SVG not found.<br/>'
                  'Run <code>./make.sh</code> (build_atlas_v6) to embed it.</div>')
    if has_r:
        r_pane = (f'<div class="pane" id="paneR"><div class="pane-label">RFCELL &mdash; '
                  f'visual reference only (no W006 cross-map)</div>{r_svg}</div>')
    else:
        r_pane = ('<div class="pane empty" id="paneR">RFCELL atlas SVG not found.</div>')

    repl = {
        "__ROWS_JSON__": rows_json,
        "__FOUND_JSON__": found_json,
        "__TABLE_ROWS__": table_rows,
        "__Q_PANE__": q_pane,
        "__R_PANE__": r_pane,
        "__HAS_R__": ("true" if has_r else "false"),
        "__Q_VB__": q_vb or "0 0 1527.2727 1080",
        "__R_VB__": r_vb or "0 0 1527.2727 1080",
        "__S_DESIGN__": str(stats["design_tags"]),
        "__S_ASDRAWN__": str(stats["asdrawn_real"]),
        "__S_MAPPED__": str(stats["mapped"]),
        "__S_HIGH__": str(stats["high"]),
        "__S_MEDIUM__": str(stats["medium"]),
        "__S_LOW__": str(stats["low"]),
        "__S_UNMAPPED__": str(stats["unmapped"]),
        "__S_UNCLAIMED__": str(stats["asdrawn_unclaimed"]),
        "__S_LOCATABLE__": str(stats["locatable"]),
        "__TC_HIGH__": TIER_COLOUR["HIGH"],
        "__TC_MEDIUM__": TIER_COLOUR["MEDIUM"],
        "__TC_LOW__": TIER_COLOUR["LOW"],
        "__TC_UNMAPPED__": TIER_COLOUR["UNMAPPED"],
    }
    doc = _PAGE
    for k, v in repl.items():
        doc = doc.replace(k, v)

    os.makedirs(PUBLISH, exist_ok=True)
    out = os.path.join(PUBLISH, "interactive_viewer.html")
    with open(out, "w") as fh:
        fh.write(doc)
    return out, stats, derived


# The big HTML/CSS/JS template lives in build_viewer_template.py to keep this
# module readable; it is imported lazily so the module still works standalone.
from abacus_svg_pid.build_viewer_template import PAGE as _PAGE  # noqa: E402


def main():
    out, stats, derived = build_html()
    print(">>> W008 interactive viewer written")
    print(f"    {out}")
    print(f"    design_tags={stats['design_tags']} mapped={stats['mapped']} "
          f"HIGH={stats['high']} MEDIUM={stats['medium']} LOW={stats['low']} "
          f"unmapped={stats['unmapped']} locatable={stats['locatable']}")
    # Honesty cross-check: row-derived counts must agree with authoritative file.
    assert derived["mapped"] == stats["mapped"], "mapped count mismatch"
    assert derived["medium"] == stats["medium"], "medium count mismatch"
    assert derived["low"] == stats["low"], "low count mismatch"
    assert derived["unmapped"] == stats["unmapped"], "unmapped count mismatch"
    return out


if __name__ == "__main__":
    main()
