"""OOXML structural inventory and review bridge (SVG-ENGINE W1).

``enhanced_pptx``: native object identity, local geometry and image relationships of a deck. It deliberately
does not resolve effective fonts or nested group transforms; ``ooxml_geometry.analyse`` does that (W2).
``review_bridge``: out-of-slide and overlap *candidates* for reviewer disposition, never automatic defects.
``tag_crosswalk``: exact lexical tag matches between deck text and source SVG text, not engineering identity.
``reconcile_layers``: additive source-layer CSV vs native SVG layers; the supplied CSV is never rewritten.
"""

from __future__ import annotations

import collections
import csv
import posixpath
import re
from zipfile import ZipFile

from lxml import etree

from .ingress import sha, simple

EMU_MM = 36000
NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
# ISA-5.1-style instrument tag letters followed by a three-digit loop number (generic, overridable).
DEFAULT_TAG_PATTERN = r"\b(?:TT|PT|FT|LT|CV|HV|SV|LS|EH|HX|HL|PL)\s*[-]?\s*\d{3}\b"


def enhanced_pptx(path):
    """Pure OOXML structural ingress: native element identity, local geometry and image relationships."""
    allslides, pictures, media, counters = [], [], [], collections.Counter()
    with ZipFile(path) as z:
        names = z.namelist()
        for n in names:
            if n.startswith("ppt/media/") and not n.endswith("/"):
                media.append(
                    {
                        "part": n,
                        "sha256": sha(z.read(n)),
                        "size_bytes": z.getinfo(n).file_size,
                    }
                )
        slidexml = sorted(
            [n for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)],
            key=lambda n: int(re.search(r"\d+", n).group()),
        )
        for n in slidexml:
            num = int(re.search(r"slide(\d+)\.xml", n).group(1))
            relpart = "ppt/slides/_rels/" + n.split("/")[-1] + ".rels"
            rels = {}
            if relpart in names:
                for r in etree.fromstring(z.read(relpart)):
                    rels[r.get("Id")] = {
                        "target": r.get("Target"),
                        "type": r.get("Type"),
                        "mode": r.get("TargetMode"),
                    }
            x = etree.fromstring(z.read(n))
            sp_tree = x.find(".//p:spTree", NS)
            shapes = []

            def walk(shape, parent_stack=()):
                tag = simple(shape)
                if tag in ("nvGrpSpPr", "grpSpPr", ""):
                    return
                nv = shape.xpath(
                    "./p:nvSpPr/p:cNvPr|./p:nvPicPr/p:cNvPr|./p:nvCxnSpPr/p:cNvPr|./p:nvGrpSpPr/p:cNvPr",
                    namespaces=NS,
                )
                objid = nv[0].get("id") if nv else None
                name = nv[0].get("name") if nv else None
                xfrm = shape.xpath(
                    "./p:spPr/a:xfrm|./p:grpSpPr/a:xfrm|./p:xfrm", namespaces=NS
                )
                geom = {}
                if xfrm:
                    for c in xfrm[0]:
                        if simple(c) in ("off", "ext", "chOff", "chExt"):
                            geom[simple(c)] = {
                                k: int(v) if v.lstrip("-").isdigit() else v
                                for k, v in c.attrib.items()
                            }
                    geom["rotation_60000deg"] = xfrm[0].get("rot")
                    geom["flipV"] = xfrm[0].get("flipV")
                    geom["flipH"] = xfrm[0].get("flipH")
                txt = " ".join(
                    t.text or "" for t in shape.xpath(".//a:t", namespaces=NS)
                )
                crop = shape.xpath(".//a:srcRect", namespaces=NS)
                links = []
                for rid in [
                    b.get("{" + NS["r"] + "}embed")
                    for b in shape.xpath(".//a:blip", namespaces=NS)
                ]:
                    target = rels.get(rid, {}).get("target") or ""
                    part = (
                        target.lstrip("/")
                        if target.startswith("/")
                        else posixpath.normpath(
                            posixpath.join(posixpath.dirname(n), target)
                        )
                    )
                    links.append(
                        {
                            "rid": rid,
                            "target": target,
                            "part": part,
                            "source_media_sha256": next(
                                (m["sha256"] for m in media if m["part"] == part), None
                            ),
                        }
                    )
                record = {
                    "slide": num,
                    "type": tag,
                    "native_id": objid,
                    "name": name,
                    "parent_group_ids": list(parent_stack),
                    "geometry_emu": geom,
                    "text": txt,
                    "media_refs": links,
                    "crop": dict(crop[0].attrib) if crop else None,
                    "effective_font": "UNRESOLVED",
                    "effective_colour": "UNRESOLVED",
                }
                for k in ("off", "ext"):
                    if k in geom:
                        record["geometry_mm_" + k] = {
                            kk: round(v / EMU_MM, 4)
                            for kk, v in geom[k].items()
                            if kk in ("x", "y", "cx", "cy")
                        }
                if tag in ("sp", "pic", "cxnSp", "grpSp"):
                    shapes.append(record)
                    counters[tag] += 1
                    if tag == "pic":
                        pictures.append(record)
                if tag == "grpSp":
                    for child in shape:
                        if simple(child) not in ("nvGrpSpPr", "grpSpPr"):
                            walk(child, parent_stack + ((objid or name or "unknown"),))

            if sp_tree is not None:
                for child in sp_tree:
                    walk(child)
            allslides.append(
                {
                    "number": num,
                    "shapes": shapes,
                    "text": " ".join(s["text"] for s in shapes if s["text"]),
                    "native_shape_count": len(shapes),
                    "media_count": sum(bool(s["media_refs"]) for s in shapes),
                }
            )
    return {
        "slides": allslides,
        "media": media,
        "slide_count": len(allslides),
        "object_type_count": dict(counters),
        "native_group_count": counters["grpSp"],
        "picture_placement_count": counters["pic"],
        "media_asset_count": len(media),
        "image_relationships_resolved": sum(
            1
            for p in pictures
            if p["media_refs"] and p["media_refs"][0]["source_media_sha256"] is not None
        ),
    }


def slide_size_emu(path):
    with ZipFile(path) as z:
        sz = etree.fromstring(z.read("ppt/presentation.xml")).find("p:sldSz", NS)
    return (int(sz.get("cx")), int(sz.get("cy"))) if sz is not None else (None, None)


def review_bridge(
    deck,
    slide_size,
    *,
    overlap_ratio=0.15,
    edge_tolerance_emu=10000,
    anchor_patterns=None,
):
    """Out-of-slide and overlap candidates from ``enhanced_pptx`` output (top-level local geometry).

    ``slide_size``: ``(cx, cy)`` in EMU. ``anchor_patterns``: optional ``{hint: regex}`` searched in slide text;
    matches are review anchors only (evidence class: source review text, not engineering authority).
    """
    w, h = slide_size
    geometry, out_of_bounds, overlap = [], [], []
    for slide in deck["slides"]:
        rects = []
        for shape in slide["shapes"]:
            g = shape["geometry_emu"]
            pos, dim = g.get("off", {}), g.get("ext", {})
            if not (
                all(k in pos for k in ("x", "y"))
                and all(k in dim for k in ("cx", "cy"))
            ):
                continue
            x, y, cx, cy = pos["x"], pos["y"], dim["cx"], dim["cy"]
            if cx <= 0 or cy <= 0:
                continue
            r = {
                "slide": slide["number"],
                "native_id": shape["native_id"],
                "type": shape["type"],
                "rect_mm": [round(u / EMU_MM, 3) for u in (x, y, cx, cy)],
            }
            rects.append((r, (x, y, x + cx, y + cy)))
            geometry.append(r)
            if (
                w
                and h
                and (
                    x < 0
                    or y < 0
                    or x + cx > w + edge_tolerance_emu
                    or y + cy > h + edge_tolerance_emu
                )
            ):
                out_of_bounds.append(r)
        for i, (a, ra) in enumerate(rects):
            for b, rb in rects[i + 1 :]:
                iw = max(0, min(ra[2], rb[2]) - max(ra[0], rb[0]))
                ih = max(0, min(ra[3], rb[3]) - max(ra[1], rb[1]))
                if iw and ih:
                    ratio = (iw * ih) / min(
                        max(1, (ra[2] - ra[0]) * (ra[3] - ra[1])),
                        max(1, (rb[2] - rb[0]) * (rb[3] - rb[1])),
                    )
                    if ratio >= overlap_ratio:
                        overlap.append(
                            {
                                "slide": slide["number"],
                                "native_ids": [a["native_id"], b["native_id"]],
                                "types": [a["type"], b["type"]],
                                "smaller_object_covered_fraction": round(ratio, 4),
                                "classification": "REVIEW_REQUIRED_NOT_AUTOMATIC_DEFECT",
                            }
                        )
    anchors = [
        {
            "semantic_hint": key,
            "native_annotation_slides": [
                s["number"] for s in deck["slides"] if re.search(pat, s["text"], re.I)
            ],
            "evidence_class": "SOURCE_REVIEW_TEXT_NOT_ENGINEERING_AUTHORITY",
        }
        for key, pat in (anchor_patterns or {}).items()
    ]
    return {
        "schema": "svg-engine/review-bridge-w1.0",
        "slide_dimensions": (
            {"width_mm": round(w / EMU_MM, 4), "height_mm": round(h / EMU_MM, 4)}
            if w and h
            else {}
        ),
        "slide_count": len(deck["slides"]),
        "native_object_positions": len(geometry),
        "position_out_of_bounds_candidates": out_of_bounds,
        "intended_or_unintended_overlap_candidates": overlap,
        "overlap_count": len(overlap),
        "anchors": anchors,
    }


def tag_crosswalk(deck, root, tag_pattern=DEFAULT_TAG_PATTERN):
    """Exact lexical tag matches between deck text and source SVG ``<text>``. Not engineering identity."""
    pat = re.compile(tag_pattern, re.I)
    norm = lambda s: re.sub(r"[-\s]", "", s).upper()  # noqa: E731
    tags = {
        norm(m)
        for e in root.iter()
        if simple(e) == "text"
        for m in pat.findall("".join(e.itertext()))
    }
    rows = []
    for slide in deck["slides"]:
        words = sorted({norm(m) for m in pat.findall(slide["text"])})
        rows.append(
            {
                "slide": slide["number"],
                "review_text_tags": words,
                "tags_exactly_present_in_svg": sorted(set(words) & tags),
                "tags_without_svg_text_match": sorted(set(words) - tags),
                "native_picture_count": sum(
                    x["type"] == "pic" for x in slide["shapes"]
                ),
            }
        )
    return {
        "contract": "EXACT_LEXICAL_ONLY_NOT_ENGINEERING_APPROVAL",
        "source_native_svg_unique_tags": len(tags),
        "review_deck_tag_tokens": sum(len(r["review_text_tags"]) for r in rows),
        "crosswalk": rows,
        "guardrail": "COLOUR_DOES_NOT_DEFINE_FLUID_OR_VALVE_STATE",
    }


def reconcile_layers(layers, source_csv_path, out_csv_path=None):
    """Compare a supplied layer CSV (column ``id``, optional ``text_count``) with the native SVG layers.

    The supplied CSV is never modified; a reconciled copy is written to ``out_csv_path`` when given.
    Rows missing from the CSV are marked ``SVG_XML_RECOVERED``.
    """
    with open(source_csv_path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    byid = {x["id"]: x for x in rows}
    rec = []
    for layer in layers:
        e = byid.get(layer["id"])
        rec.append(
            {
                "id": layer["id"],
                "label": layer["label"],
                "source_parent_id": layer["parent_id"] or "",
                "source_depth": layer["level"] + 1,
                "csv_present": bool(e),
                "evidence": "SVG_XML_AND_CSV" if e else "SVG_XML_RECOVERED",
                "csv_text_count": e.get("text_count", "") if e else "",
            }
        )
    if out_csv_path and rec:
        with open(out_csv_path, "w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(f, fieldnames=list(rec[0]))
            wr.writeheader()
            wr.writerows(rec)
    return {
        "source_csv_count": len(rows),
        "source_svg_layer_count": len(layers),
        "reconciled_count": len(rec),
        "missing_csv": [
            {k: x[k] for k in ("id", "label", "source_parent_id", "source_depth")}
            for x in rec
            if not x["csv_present"]
        ],
        "csv_only": sorted(set(byid) - {layer["id"] for layer in layers}),
        "rows": rec,
    }
