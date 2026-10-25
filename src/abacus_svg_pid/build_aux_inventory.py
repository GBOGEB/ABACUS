#!/usr/bin/env python3
"""
build_aux_inventory.py  --  AD_01 Auxiliary Building & Support Systems assimilation
===================================================================================

Inventories the AD_01 auxiliary-building drawing package that was uploaded as a
(doubly-nested) zip and extracted to data/aux_building/pdfs/. For every PDF it
records type, byte size, page count, embedded Title/drawing-number metadata, and
— where the PDF carries a text layer — the extracted text, the ISA-style tag-like
tokens and the pipe-line (BR####-size-class) tokens.

It then **honestly** cross-checks the extracted instrument tags against the
existing MINERVA design register (the 97 QCELL design tags) and the W005/W006
as-drawn tag set (the 141 real as-drawn tags), reporting the overlap exactly as
measured. The AD_01 PCW / Instrument-Air systems use a different tag namespace
(AA####, pipe-line BR####) from the QCELL cryo register (CV001/TT514…), so a
small or zero overlap is the expected, truthful result — this script never
fabricates matches.

Dependencies : Python stdlib + poppler system tools (pdfinfo, pdftotext) which
               are detected at runtime; if poppler is absent the script still
               produces the file-level inventory and records text extraction as
               unavailable (honest degradation). No pip-only PDF library is used.

Inputs  : data/aux_building/pdfs/*.pdf
          data/crossmap/design_to_asdrawn.json      (W006 — design tag universe)
          data/crossmap/crossmap_confidence.json    (W006 — unmapped design tags)
          data/excel/catalog_register.json          (W005 — as-drawn real tags)
Outputs : reports/aux_building_inventory.json
          reports/aux_building_inventory.md
"""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PDF_DIR = os.path.join(ROOT, "data", "aux_building", "pdfs")
CROSSMAP = os.path.join(ROOT, "data", "crossmap", "design_to_asdrawn.json")
CONFIDENCE = os.path.join(ROOT, "data", "crossmap", "crossmap_confidence.json")
CATALOG = os.path.join(ROOT, "data", "excel", "catalog_register.json")
OUT_JSON = os.path.join(ROOT, "reports", "aux_building_inventory.json")
OUT_MD = os.path.join(ROOT, "reports", "aux_building_inventory.md")

# ISA-style instrument tag: 2-3 letters + 2-4 digits (CV001, TT514, AA7021).
# Anchored so we do not catch pipe-line fragments like PAC3.
TAG_RE = re.compile(r"\b([A-Z]{2,3})(\d{2,4})\b")
# Pipe-line number as used on the aux drawings: BR4017-1"-PAC3-BA etc.
LINE_RE = re.compile(r"\b([A-Z]{2}\d{3,4}-[^\s]+)")
# Terminal-point / system codes like =NA.PS01, PS01.PAB12, PS05.QFB10
SYS_RE = re.compile(r"\b((?:=?[A-Z]{2}\.)?P[SV]\d{2}[._][A-Z]{3}\d{2})\b")

# Tag prefixes that are genuine instruments/final-elements (filter out noise like
# "NC", "DN", units). Kept broad but letters-only, number-bearing already enforced.
# BR is the leading fragment of a pipe-line number (BR4017-1"-PAC3-BA) and is
# already captured separately by LINE_RE, so it is not an instrument tag.
# PID is a false hit from the "P&ID" header text.
_NOISE_PREFIX = {"DN", "PN", "NC", "NO", "BR", "PID"}


def _load_json(path):
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return json.load(fh)


def _have(tool):
    return shutil.which(tool) is not None


def _pdfinfo(path):
    """Return dict with pages and title from poppler pdfinfo (best-effort)."""
    info = {"pages": None, "title": None}
    if not _have("pdfinfo"):
        return info
    try:
        out = subprocess.run(["pdfinfo", path], capture_output=True, text=True,
                             timeout=60)
        for line in out.stdout.splitlines():
            if line.startswith("Pages:"):
                try:
                    info["pages"] = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif line.startswith("Title:"):
                t = line.split(":", 1)[1].strip()
                info["title"] = t or None
    except Exception:
        pass
    return info


def _pdftext(path):
    """Extract text layer via poppler pdftotext -layout (best-effort)."""
    if not _have("pdftotext"):
        return None
    try:
        out = subprocess.run(["pdftotext", "-layout", path, "-"],
                             capture_output=True, text=True, timeout=120)
        return out.stdout
    except Exception:
        return None


def _drawing_number(fname, title):
    """Derive the AD_01.N drawing number from the filename, and the system code
    (=NA.PSxx / PSxx.yyy) from the title when present."""
    m = re.match(r"\s*(AD_\d+\.\d+)", fname)
    ad = m.group(1) if m else None
    sysm = SYS_RE.search(title or "") or SYS_RE.search(fname)
    return ad, (sysm.group(1) if sysm else None)


def _extract_tags(text):
    """Return (instrument_tags set, pipe_line_tags set) from a text blob."""
    tags, lines = set(), set()
    if not text:
        return tags, lines
    for pfx, num in TAG_RE.findall(text):
        if pfx in _NOISE_PREFIX:
            continue
        tags.add(pfx + num)
    for m in LINE_RE.findall(text):
        lines.add(m.rstrip('.,);'))
    return tags, lines


def _design_universe():
    """The 97 QCELL design tags: mapped design keys + unmapped design tags."""
    cm = _load_json(CROSSMAP) or {}
    conf = _load_json(CONFIDENCE) or {}
    tags = set(cm.get("design_to_asdrawn", {}).keys())
    for m in cm.get("mappings", []):
        tags.add(m["design_tag"])
    for u in conf.get("unmapped_design", []):
        dt = u.get("design_tag") if isinstance(u, dict) else u
        if dt:
            tags.add(dt)
    return tags


def _asdrawn_real():
    """The real as-drawn tag set from the W005 catalog register."""
    cat = _load_json(CATALOG) or {}
    out = set()
    for inst in cat.get("instruments", []):
        if isinstance(inst, dict):
            tag = inst.get("tag") or inst.get("norm_tag")
            if tag and not inst.get("template"):
                out.add(tag)
    return out


def build():
    pdfs = sorted(glob.glob(os.path.join(PDF_DIR, "*.pdf")))
    poppler = _have("pdfinfo") and _have("pdftotext")
    design = _design_universe()
    asdrawn = _asdrawn_real()

    docs = []
    all_tags = set()
    all_lines = set()
    for p in pdfs:
        fname = os.path.basename(p)
        size = os.path.getsize(p)
        info = _pdfinfo(p)
        ad, syscode = _drawing_number(fname, info.get("title"))
        text = _pdftext(p)
        tags, lines = _extract_tags(text)
        all_tags |= tags
        all_lines |= lines
        docs.append({
            "file": fname,
            "drawing_number": ad,
            "system_code": syscode,
            "title": info.get("title"),
            "size_bytes": size,
            "pages": info.get("pages"),
            "has_text_layer": bool(text and text.strip()),
            "n_instrument_tags": len(tags),
            "n_pipe_lines": len(lines),
            "instrument_tags": sorted(tags),
            "pipe_lines": sorted(lines)[:200],  # cap for report sanity
        })

    design_overlap = sorted(all_tags & design)
    asdrawn_overlap = sorted(all_tags & asdrawn)

    summary = {
        "source_zip": "[AD_01_Auxiliary Buildling and Support Systems.zip.zip (nested)",
        "pdf_count": len(pdfs),
        "poppler_available": poppler,
        "total_bytes": sum(d["size_bytes"] for d in docs),
        "total_pages": sum((d["pages"] or 0) for d in docs),
        "docs_with_text_layer": sum(1 for d in docs if d["has_text_layer"]),
        "unique_instrument_tags": len(all_tags),
        "unique_pipe_lines": len(all_lines),
        "design_register_size": len(design),
        "asdrawn_real_size": len(asdrawn),
        "overlap_with_design_register": design_overlap,
        "overlap_with_asdrawn_real": asdrawn_overlap,
        "overlap_design_count": len(design_overlap),
        "overlap_asdrawn_count": len(asdrawn_overlap),
    }

    out = {"summary": summary, "documents": docs,
           "all_instrument_tags": sorted(all_tags)}
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as fh:
        json.dump(out, fh, indent=2)

    _write_md(summary, docs)
    return out


def _write_md(summary, docs):
    L = []
    L.append("# AD_01 Auxiliary Building & Support Systems — Inventory\n")
    L.append("Generated by `src/abacus_svg_pid/build_aux_inventory.py` "
             "(stdlib + poppler). Raw PDFs live under "
             "`data/aux_building/pdfs/` and are git-ignored (input binaries).\n")
    L.append("## Summary\n")
    L.append(f"- PDFs: **{summary['pdf_count']}**")
    L.append(f"- Total size: **{summary['total_bytes']/1e6:.1f} MB** · "
             f"total pages: **{summary['total_pages']}**")
    L.append(f"- poppler (pdfinfo/pdftotext) available: "
             f"**{summary['poppler_available']}**")
    L.append(f"- Docs with an extractable text layer: "
             f"**{summary['docs_with_text_layer']} / {summary['pdf_count']}**")
    L.append(f"- Unique instrument-style tags extracted: "
             f"**{summary['unique_instrument_tags']}**")
    L.append(f"- Unique pipe-line numbers extracted: "
             f"**{summary['unique_pipe_lines']}**\n")
    L.append("## Tag cross-check (honest)\n")
    L.append(f"- MINERVA design register size: "
             f"**{summary['design_register_size']}** (QCELL design tags)")
    L.append(f"- W005/W006 as-drawn real set size: "
             f"**{summary['asdrawn_real_size']}**")
    L.append(f"- Overlap of AD_01 tags with **design register**: "
             f"**{summary['overlap_design_count']}** "
             f"{summary['overlap_with_design_register'] or '— none'}")
    L.append(f"- Overlap of AD_01 tags with **as-drawn real**: "
             f"**{summary['overlap_asdrawn_count']}** "
             f"{summary['overlap_with_asdrawn_real'] or '— none'}")
    L.append("")
    L.append("> The AD_01 PCW (Process Cooling Water / adiabatic cooling) and "
             "Instrument-Air systems use their own tag namespace (AA####, "
             "pipe-line `BR####-size-class`, system codes `=NA.PSxx`). These are "
             "**different subsystems** from the QCELL cryogenic register "
             "(CV001/TT514…), so a small or zero tag overlap is the expected, "
             "truthful result. No matches are fabricated.\n")
    L.append("## Documents\n")
    L.append("| Drawing | File | Pages | Size (KB) | Text? | Tags | Lines | System |")
    L.append("|---|---|---:|---:|:--:|---:|---:|---|")
    for d in docs:
        L.append(f"| {d['drawing_number'] or '—'} | {d['file']} | "
                 f"{d['pages'] or '—'} | {d['size_bytes']//1024} | "
                 f"{'yes' if d['has_text_layer'] else 'no'} | "
                 f"{d['n_instrument_tags']} | {d['n_pipe_lines']} | "
                 f"{d['system_code'] or '—'} |")
    L.append("")
    # Per-doc tag detail for the P&ID sheets that carry instrument tags
    L.append("## Instrument tags per document (where present)\n")
    for d in docs:
        if d["instrument_tags"]:
            preview = ", ".join(d["instrument_tags"][:40])
            more = "" if len(d["instrument_tags"]) <= 40 else \
                f" … (+{len(d['instrument_tags'])-40} more)"
            L.append(f"- **{d['drawing_number'] or d['file']}** "
                     f"({d['n_instrument_tags']} tags): {preview}{more}")
    L.append("")
    with open(OUT_MD, "w") as fh:
        fh.write("\n".join(L))


def main():
    out = build()
    s = out["summary"]
    print(">>> AD_01 aux-building inventory written")
    print(f"    {OUT_JSON}")
    print(f"    {OUT_MD}")
    print(f"    pdfs={s['pdf_count']} pages={s['total_pages']} "
          f"tags={s['unique_instrument_tags']} lines={s['unique_pipe_lines']} "
          f"design_overlap={s['overlap_design_count']} "
          f"asdrawn_overlap={s['overlap_asdrawn_count']}")
    return out


if __name__ == "__main__":
    main()
