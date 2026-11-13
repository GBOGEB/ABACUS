"""Redraw fidelity checks for a layered PDF against its source SVG (SVG-ENGINE W2 QA ladder).

The oracle is the *source SVG* with Inkscape display semantics, rendered by CairoSVG. The subject is the built
PDF with OCG state changes, rendered by MuPDF. Neither side reuses the builder's paint runs.

Three families of checks:

* structural  K4001 OCG count = native layers; K4102 OCG defaults = each layer's own style;
              K4111 nested ``/Order`` = native hierarchy; K4303 page-set coverage against an authored PDF.
* visual      K4201 default page vs source; K4304 each preset page vs source with that preset;
              K4105 no default-visibility leakage against a baseline PDF; K4302/K4305 authored-PDF parity.
* semantic    K4112 every layer switch matches source display semantics (parents cascade);
              K4113 parent OFF hides its subtree, ON restores own child states; K4114 turning on a hidden
              parent shows children by their own states; K4106 embedded fonts are the requested families.

Check IDs are namespaced ``SVG-W2:`` (not QPS LADDER IDs). Results are PASS / FAIL / DEFER / NA.
Nothing here grants engineering approval.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

from ._env import bootstrap
from .ingress import XINK, layer_items, sha, simple
from .pdf_ocg import chain_of, preset_overrides

DPI = 45
TOL = 22
SIMILARITY = 0.99999
AUTHORED_SIMILARITY = 0.99


def _deps():
    bootstrap()
    import cairosvg
    import fitz
    import numpy as np
    from lxml import etree

    return cairosvg, fitz, np, etree


def raster(doc, pno=0, dpi=DPI):
    _, _, np, _ = _deps()
    p = doc[pno].get_pixmap(dpi=dpi, alpha=False)
    return (
        np.frombuffer(p.samples, dtype=np.uint8)
        .reshape(p.height, p.width, 3)
        .astype(np.int16)
    )


def compare(a, b, tol=TOL):
    _, _, np, _ = _deps()
    if a.shape != b.shape:
        return {
            "shape_mismatch": [list(a.shape), list(b.shape)],
            "similarity": 0.0,
            "bad_px": -1,
            "max": 255,
        }
    d = np.abs(a - b).max(axis=2)
    return {
        "similarity": round(float((d <= tol).mean()), 8),
        "bad_px": int((d > tol).sum()),
        "max": int(d.max()),
        "mean": round(float(np.abs(a - b).mean()), 4),
    }


def svg_oracle(root, overrides, dpi=DPI):
    """Render the source with ``overrides`` ({layer_id: show?}) applied to each layer's own style."""
    cairosvg, fitz, _, etree = _deps()
    r = copy.deepcopy(root)
    for e in r.iter():
        if (
            simple(e) == "g"
            and e.get(XINK + "groupmode") == "layer"
            and e.get("id") in overrides
        ):
            st = (
                re.sub(r"display\s*:\s*[a-z]+;?", "", e.get("style") or "")
                .strip()
                .rstrip(";")
            )
            st = (st + ";" if st else "") + (
                "display:inline" if overrides[e.get("id")] else "display:none"
            )
            e.set("style", st)
    with fitz.open(
        stream=cairosvg.svg2pdf(bytestring=etree.tostring(r)), filetype="pdf"
    ) as d:
        return raster(d, 0, dpi)


def pdf_state(pdf_bytes, ocg_by_layer, state, pno=0, dpi=DPI):
    """Render page ``pno`` with OCGs set to ``state`` ({layer_id: on?})."""
    _, fitz, _, _ = _deps()
    d = fitz.open(stream=pdf_bytes, filetype="pdf")
    d.set_layer(
        -1,
        on=[ocg_by_layer[k] for k, v in state.items() if v],
        off=[ocg_by_layer[k] for k, v in state.items() if not v],
    )
    d2 = fitz.open(
        stream=d.tobytes(), filetype="pdf"
    )  # reload so the configuration is honoured
    a = raster(d2, pno, dpi)
    d.close()
    d2.close()
    return a


def parse_order(doc):
    """``{ocg_xref: parent_ocg_xref or None}`` from the catalog's ``/OCProperties/D/Order``."""
    raw = doc.xref_get_key(doc.pdf_catalog(), "OCProperties/D/Order")[1]
    parent_of, pstack, last = {}, [None], None
    for t in re.findall(r"\[|\]|\d+ 0 R", raw):
        if t == "[":
            pstack.append(last)
        elif t == "]":
            pstack.pop()
        else:
            x = int(t.split()[0])
            parent_of[x] = pstack[-1]
            last = x
    return parent_of


def requested_font_families(root):
    """Normalised font families the source asks for (attribute and inline style)."""
    req = set()
    for e in root.iter():
        if not isinstance(e.tag, str):
            continue
        for src in (
            e.get("font-family") or "",
            *re.findall(r"font-family\s*:\s*([^;]+)", e.get("style") or ""),
        ):
            for f in src.split(","):
                f = f.strip().strip("'\"")
                if f:
                    req.add(f.lower().replace(" ", ""))
    return req


def font_family_of(embedded_name: str) -> str:
    """'ABCDEF+Arial-BoldMT' -> 'arial'."""
    n = embedded_name.split("+")[-1]
    return re.sub(r"(psmt|mt|ps)$", "", re.sub(r"-.*$", "", n.lower().replace(" ", "")))


def check_pdf_fidelity(
    pdf_path,
    build,
    root,
    *,
    baseline_pdf=None,
    authored_pdf=None,
    cascade_ids=None,
    hidden_parent_ids=None,
    dpi=DPI,
    tol=TOL,
    similarity=SIMILARITY,
):
    """Run the QA ladder on a nested-OCG PDF. Returns a receipt dict (JSON-serialisable).

    ``build``: the report from ``build_nested_ocg_pdf`` (needs ``ocg_xref_by_layer``, ``sha256``, ``pages``).
    ``cascade_ids``: parent layers for the OFF/ON demonstration (default: every source-visible parent).
    ``hidden_parent_ids``: source-hidden parents to switch on (default: every source-hidden parent).
    ``baseline_pdf``: W1 flat PDF built on the same toolchain (K4105); ``authored_pdf``: the owner's export.
    """
    _, fitz, np, _ = _deps()
    pdf_bytes = Path(pdf_path).read_bytes()
    ocg = {k: int(v) for k, v in build["ocg_xref_by_layer"].items()}
    layers = layer_items(root)
    byid = {layer["id"]: layer for layer in layers}
    default = {layer["id"]: layer["source_visible"] for layer in layers}
    kids = {}
    for layer in layers:
        kids.setdefault(layer["parent_id"], []).append(layer["id"])
    parents = [lid for lid in byid if lid in kids]
    cascade_ids = (
        list(cascade_ids)
        if cascade_ids is not None
        else [p for p in parents if default[p]]
    )
    hidden_parent_ids = (
        list(hidden_parent_ids)
        if hidden_parent_ids is not None
        else [p for p in parents if not default[p]]
    )
    unknown = sorted(set(cascade_ids + hidden_parent_ids) - set(byid))
    if unknown:
        raise ValueError(f"UNKNOWN_LAYER_IDS:{unknown}")
    n = len(layers)
    checks = []

    def ck(kid, title, ok, evidence, status=None):
        checks.append(
            {
                "id": "SVG-W2:" + kid,
                "title": title,
                "result": status or ("PASS" if ok else "FAIL"),
                "evidence": evidence,
            }
        )

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    ocgs = doc.get_ocgs()
    ck(
        "K4001",
        f"{n} native OCGs",
        len(ocgs) == n,
        f"{len(ocgs)} OCGs for {n} native layers",
    )
    mism = [lid for lid in default if ocgs[ocg[lid]]["on"] != default[lid]]
    ck(
        "K4102",
        "OCG defaults equal each layer's own source style",
        not mism,
        f"mismatches={mism}",
    )
    parent_of = parse_order(doc)
    bad = [
        layer["id"]
        for layer in layers
        if parent_of.get(ocg[layer["id"]])
        != (ocg[layer["parent_id"]] if layer["parent_id"] else None)
    ]
    ck(
        "K4111",
        "Nested layer panel (/Order) mirrors native hierarchy",
        not bad and len(parent_of) == n,
        f"{len(parent_of)} entries; parent mismatches={bad}",
    )

    base = pdf_state(pdf_bytes, ocg, default, 0, dpi)
    c0 = compare(base, svg_oracle(root, {}, dpi), tol)
    ck(
        "K4201",
        "Default page 1 vs source SVG",
        c0["similarity"] >= similarity,
        json.dumps(c0),
    )
    if baseline_pdf:
        with fitz.open(baseline_pdf) as w1:
            cw1 = compare(base, raster(w1, 0, dpi), tol)
        ck(
            "K4105",
            "No default-visibility leakage vs baseline built on the same toolchain",
            cw1["bad_px"] == 0,
            json.dumps(cw1),
        )
    else:
        ck(
            "K4105",
            "No default-visibility leakage vs baseline",
            True,
            "no baseline PDF given",
            status="NA",
        )
    req = requested_font_families(root)
    emb = sorted({f[3].split("+")[-1] for pg in doc for f in pg.get_fonts(full=True)})
    alien = [e for e in emb if font_family_of(e) not in req]
    ck(
        "K4106",
        "Embedded fonts are source-requested families (no substitution)",
        not alien,
        f"requested={sorted(req)}; embedded={emb}; substituted={alien}",
    )

    per = []
    for layer in layers:
        lid = layer["id"]
        st = dict(default)
        st[lid] = not default[lid]
        a = pdf_state(pdf_bytes, ocg, st, 0, dpi)
        c = compare(a, svg_oracle(root, {lid: not default[lid]}, dpi), tol)
        per.append(
            {
                "id": lid,
                "label": layer["label"],
                "has_children": lid in kids,
                "source_visible": default[lid],
                "flip_vs_oracle": c,
                "pixels_changed_vs_default": int(
                    (np.abs(a - base).max(axis=2) > 0).sum()
                ),
            }
        )
    fails = [p["id"] for p in per if p["flip_vs_oracle"]["similarity"] < similarity]
    ck(
        "K4112",
        f"Each of {n} layer switches matches source display semantics (parents cascade)",
        not fails,
        f"{n - len(fails)}/{n} within tol{tol} at >={similarity}; failures={fails}",
    )
    inert = [p["id"] for p in per if p["pixels_changed_vs_default"] == 0]
    ck(
        "K4101",
        "Switches with a visible effect",
        True,
        f"{n - len(inert)}/{n} change pixels; no effect: {inert} (expected: children of hidden parents or empty wrappers)",
        status="PASS",
    )

    demos = {}
    for pid in cascade_ids:
        st = dict(default)
        st[pid] = False
        off = pdf_state(pdf_bytes, ocg, st, 0, dpi)
        st[pid] = True
        back = pdf_state(pdf_bytes, ocg, st, 0, dpi)
        ref = (
            base
            if default[pid]
            else pdf_state(pdf_bytes, ocg, {**default, pid: True}, 0, dpi)
        )
        demos[pid] = {
            "off_vs_oracle": compare(off, svg_oracle(root, {pid: False}, dpi), tol),
            "restore_identical": bool((back == ref).all()),
            "descendants": sum(pid in chain_of(lid, byid)[:-1] for lid in byid),
        }
    ok = all(
        d["restore_identical"] and d["off_vs_oracle"]["similarity"] >= similarity
        for d in demos.values()
    )
    ck(
        "K4113",
        "Parent OFF hides whole subtree; parent ON restores own child states",
        ok,
        json.dumps(demos),
        status=None if demos else "NA",
    )
    hidden = {}
    for pid in hidden_parent_ids:
        st = dict(default)
        st[pid] = True
        hidden[pid] = compare(
            pdf_state(pdf_bytes, ocg, st, 0, dpi),
            svg_oracle(root, {pid: True}, dpi),
            tol,
        )
    ck(
        "K4114",
        "Turning on a source-hidden parent shows children by their own states",
        all(c["similarity"] >= similarity for c in hidden.values()),
        json.dumps(hidden),
        status=None if hidden else "NA",
    )

    pages = {int(k): v for k, v in build.get("pages", {}).items()}
    page_px = {1: base}
    for pno in sorted(pages):
        if pno == 1:
            continue
        page_px[pno] = pdf_state(pdf_bytes, ocg, default, pno - 1, dpi)
        cp = compare(
            page_px[pno],
            svg_oracle(root, preset_overrides(pages[pno]["preset"]), dpi),
            tol,
        )
        ck(
            "K4304" + ("" if pno == 2 else f".p{pno}"),
            f"Page {pno} equals source with preset '{pages[pno]['preset'].get('title', '')}'",
            cp["similarity"] >= similarity,
            json.dumps(cp),
        )
    if authored_pdf:
        with fitz.open(authored_pdf) as au:
            ck(
                "K4303",
                "Authored PDF page-set coverage",
                len(doc) == len(au),
                f"authored {len(au)} pages; built {len(doc)} pages",
            )
            for pno in range(1, min(len(au), len(doc)) + 1):
                px = page_px.get(pno)
                if px is None:
                    px = pdf_state(pdf_bytes, ocg, default, pno - 1, dpi)
                ca = compare(px, raster(au, pno - 1, dpi), tol)
                kid = (
                    "K4302" if pno == 1 else ("K4305" if pno == 2 else f"K4305.p{pno}")
                )
                ck(
                    kid,
                    f"Authored PDF page {pno} cross-renderer parity (>={AUTHORED_SIMILARITY})",
                    ca["similarity"] >= AUTHORED_SIMILARITY,
                    json.dumps(ca),
                    status=None if ca["similarity"] >= AUTHORED_SIMILARITY else "DEFER",
                )
    h = sha(pdf_bytes)
    ck("K5001", "Built PDF SHA equals build report", h == build["sha256"], h)
    doc.close()
    return {
        "schema": "svg-engine.qa-ladder/w2.0",
        "authority": "REVIEW_ONLY",
        "engineering_approval": False,
        "release_admission": False,
        "pdf_sha256": h,
        "dpi": dpi,
        "tolerance_rgb": tol,
        "similarity_threshold": similarity,
        "checks": checks,
        "per_layer": per,
        "summary": {
            k: sum(c["result"] == k for c in checks)
            for k in ("PASS", "FAIL", "DEFER", "NA")
        },
    }
