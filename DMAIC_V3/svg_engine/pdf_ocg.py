"""Layered PDF builders with real Optional Content Groups (OCGs).

``build_nested_ocg_pdf`` (W2) gives true parent semantics: every paint run is wrapped in nested
``/OC /L_<id> BDC ... EMC`` marked content, one level per native layer on its ancestor chain. Under ISO 32000
8.11.3.2, nested optional content is visible only when every enclosing group is ON, which is exactly Inkscape's
``display:none`` inheritance. Each OCG defaults to the layer's *own* source style, so switching a parent back
ON restores each child's own state. The Layers panel (``/Order``) is a nested tree mirroring the source.

Why not OCMD: MuPDF ignores ``/OCMD`` (``/P /AllOn`` and ``/VE``) on form XObjects, so an OCMD-based hierarchy
silently degrades to flat switches in that viewer.

``build_flat_ocg_pdf`` (W1) is the flat baseline (one OCG per layer, default = ancestor-combined visibility,
no cascade). It is kept as the regression reference for "no default-visibility leakage".

Page presets reproduce authored multi-page exports of one SVG: per page, ``skip_subtrees`` are not drawn and
``force_on`` roots are drawn without their switch. Every other switch stays live on every page.
"""

from __future__ import annotations

import time
from pathlib import Path

from ._env import bootstrap
from .ingress import layer_items, sha, sha_file
from .paint_runs import ROOT_OWNER, isolated_svg, paint_atoms

DEFAULT_PRESETS = {1: {"title": "As authored", "skip_subtrees": [], "force_on": []}}


def _deps():
    bootstrap()
    import cairosvg
    import fitz
    from lxml import etree

    return cairosvg, fitz, etree


def chain_of(layer_id, byid):
    """Native layer ids from the root layer down to ``layer_id``."""
    out = []
    while layer_id:
        out.insert(0, layer_id)
        layer_id = byid[layer_id]["parent_id"]
    return out


def order_array(layers, ocg):
    """PDF ``/Order`` array: a nested tree of OCG references mirroring the native layer hierarchy."""
    kids = {}
    for layer in layers:
        kids.setdefault(layer["parent_id"], []).append(layer["id"])

    def node(lid):
        s = f"{ocg[lid]} 0 R"
        if lid in kids:
            s += " [ " + " ".join(node(c) for c in kids[lid]) + " ]"
        return s

    return "[ " + " ".join(node(r) for r in kids.get(None, [])) + " ]"


def preset_overrides(preset):
    """Source-display overrides equivalent to a page preset (for an SVG oracle of that page)."""
    out = {lid: False for lid in preset.get("skip_subtrees", [])}
    out.update({lid: True for lid in preset.get("force_on", [])})
    return out


def _validate_presets(presets, byid):
    unknown = sorted(
        {
            lid
            for p in presets.values()
            for lid in [*p.get("skip_subtrees", []), *p.get("force_on", [])]
        }
        - set(byid)
    )
    if unknown:
        raise ValueError(f"PRESET_UNKNOWN_LAYER_IDS:{unknown}")


def _page_size(root):
    cairosvg, fitz, etree = _deps()
    base = cairosvg.svg2pdf(bytestring=etree.tostring(root, encoding="utf-8"))
    with fitz.open(stream=base, filetype="pdf") as r:
        return r[0].rect.width, r[0].rect.height, base


def save_previews(pdf_path, out_dir, stem=None, dpi=50):
    """Write one PNG preview per page; returns the file names."""
    _, fitz, _ = _deps()
    pdf_path, out_dir = Path(pdf_path), Path(out_dir)
    stem = stem or pdf_path.stem
    names = []
    with fitz.open(pdf_path) as final:
        for i in range(len(final)):
            name = f"{stem}_p{i + 1}_preview.png"
            final[i].get_pixmap(dpi=dpi, alpha=False).save(out_dir / name)
            names.append(name)
    return names


def build_nested_ocg_pdf(
    root,
    dest,
    *,
    page_presets=None,
    order_name="SVG-ENGINE source hierarchy",
    source_bytes=None,
):
    """Build the nested-OCG PDF of ``root`` at ``dest``. Returns a build report (JSON-serialisable).

    ``page_presets``: ``{page_no: {"title", "skip_subtrees": [layer ids], "force_on": [layer ids]}}``.
    ``source_bytes``: the raw source SVG, hashed into the report for provenance.
    """
    cairosvg, fitz, _etree = _deps()
    t0 = time.monotonic()
    dest = Path(dest)
    presets = {int(k): v for k, v in (page_presets or DEFAULT_PRESETS).items()}
    layers = layer_items(root)
    byid = {layer["id"]: layer for layer in layers}
    _validate_presets(presets, byid)
    atoms, runs = paint_atoms(root)
    if any(r["owner"] == ROOT_OWNER for r in runs):
        raise ValueError(
            "PAINT_OUTSIDE_LAYERS: source has paint content outside every native layer"
        )
    w, h, _ = _page_size(root)

    pdf = fitz.open()
    # OCG default = the layer's OWN source visibility; ancestors are enforced by nesting.
    ocg = {
        layer["id"]: pdf.add_ocg(
            f"{layer['label']} [{layer['id']}]", on=layer["source_visible"]
        )
        for layer in layers
    }
    run_pdfs = [cairosvg.svg2pdf(bytestring=isolated_svg(root, run)) for run in runs]
    page_report = {}
    for pno in sorted(presets):
        preset = presets[pno]
        page = pdf.new_page(width=w, height=h)
        segments, props = [], {}
        drawn = skipped = 0
        for i, run in enumerate(runs):
            chain = chain_of(run["owner"], byid)
            if any(s in chain for s in preset.get("skip_subtrees", [])):
                skipped += 1
                continue
            chain = [c for c in chain if c not in preset.get("force_on", [])]
            with fitz.open(stream=run_pdfs[i], filetype="pdf") as src:
                xo = page.show_pdf_page(
                    page.rect, src, 0, keep_proportion=False, overlay=True
                )
            segments.append((f"R{i}", xo, chain))
            for c in chain:
                props[f"L_{c}"] = ocg[c]
            drawn += 1
        # Rewrite the page content: one nested BDC stack per paint run, in exact source paint order.
        lines = []
        for name, _xo, chain in segments:
            lines += [f"/OC /L_{c} BDC" for c in chain]
            lines += ["q", f"/{name} Do", "Q"]
            lines += ["EMC"] * len(chain)
        xobjs = " ".join(f"/{n} {x} 0 R" for n, x, _ in segments)
        propd = " ".join(f"/{k} {v} 0 R" for k, v in sorted(props.items()))
        res_xref = pdf.get_new_xref()
        pdf.update_object(
            res_xref, f"<< /XObject << {xobjs} >> /Properties << {propd} >> >>"
        )
        pdf.xref_set_key(page.xref, "Resources", f"{res_xref} 0 R")
        cx = pdf.get_new_xref()
        pdf.update_object(cx, "<< >>")
        pdf.update_stream(cx, ("\n".join(lines) + "\n").encode("ascii"))
        pdf.xref_set_key(page.xref, "Contents", f"{cx} 0 R")
        page_report[pno] = {
            "preset": preset,
            "runs_drawn": drawn,
            "runs_skipped": skipped,
            "max_nesting_depth": max((len(c) for _, _, c in segments), default=0),
        }

    cat = pdf.pdf_catalog()
    pdf.xref_set_key(cat, "OCProperties/D/Order", order_array(layers, ocg))
    pdf.xref_set_key(
        cat,
        "OCProperties/D/Name",
        "(" + order_name.replace("(", "").replace(")", "") + ")",
    )
    pdf.xref_set_key(cat, "PageMode", "/UseOC")
    dest.parent.mkdir(parents=True, exist_ok=True)
    pdf.save(dest, garbage=4, deflate=True, no_new_id=True)
    pdf.close()
    return {
        "schema": "svg-engine/nested-ocg-build-w2.0",
        "file": dest.name,
        "sha256": sha_file(dest),
        "source_svg_sha256": sha(source_bytes) if source_bytes is not None else None,
        "ocg_count": len(ocg),
        "paint_atoms": len(atoms),
        "paint_runs": len(runs),
        "pages": page_report,
        "ocg_default_policy": "OWN_SOURCE_STYLE; ancestors enforced by nested BDC (ISO 32000 8.11.3.2)",
        "order": "nested /Order mirrors native layer hierarchy",
        "elapsed_seconds": round(time.monotonic() - t0, 2),
        "ocg_xref_by_layer": ocg,
    }


def build_flat_ocg_pdf(root, dest, *, source_bytes=None):
    """W1 baseline: one page, one flat OCG per native layer, default = ancestor-combined visibility.

    A parent switch here does not cascade to children; use ``build_nested_ocg_pdf`` for that.
    """
    cairosvg, fitz, _etree = _deps()
    t0 = time.monotonic()
    dest = Path(dest)
    layers = layer_items(root)
    byid = {layer["id"]: layer for layer in layers}
    atoms, runs = paint_atoms(root)
    if any(r["owner"] == ROOT_OWNER for r in runs):
        raise ValueError(
            "PAINT_OUTSIDE_LAYERS: source has paint content outside every native layer"
        )
    w, h, _ = _page_size(root)
    pdf = fitz.open()
    page = pdf.new_page(width=w, height=h)
    groups = {}
    for layer in layers:
        effective = all(byid[a]["source_visible"] for a in chain_of(layer["id"], byid))
        groups[layer["id"]] = pdf.add_ocg(
            "/".join(layer["path"]) + " [" + layer["id"] + "]", on=effective
        )
    for run in runs:
        with fitz.open(
            stream=cairosvg.svg2pdf(bytestring=isolated_svg(root, run)), filetype="pdf"
        ) as src:
            page.show_pdf_page(
                page.rect,
                src,
                0,
                keep_proportion=False,
                overlay=True,
                oc=groups[run["owner"]],
            )
    pdf.xref_set_key(pdf.pdf_catalog(), "PageMode", "/UseOC")
    dest.parent.mkdir(parents=True, exist_ok=True)
    pdf.save(dest, garbage=3, deflate=True, no_new_id=True)
    pdf.close()
    return {
        "schema": "svg-engine/flat-ocg-build-w1.0",
        "file": dest.name,
        "sha256": sha_file(dest),
        "source_svg_sha256": sha(source_bytes) if source_bytes is not None else None,
        "ocg_count": len(groups),
        "paint_atoms": len(atoms),
        "paint_runs": len(runs),
        "root_layer_count": sum(layer["level"] == 0 for layer in layers),
        "default_hidden_root_ids": [
            x["id"] for x in layers if x["level"] == 0 and not x["source_visible"]
        ],
        "limitation": "Flat OCGs; a parent switch does not cascade to children",
        "elapsed_seconds": round(time.monotonic() - t0, 2),
        "ocg_xref_by_layer": groups,
    }
